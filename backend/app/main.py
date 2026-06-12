"""FastAPI application entry point for the MailPilot backend.

Configures middleware, wires up dependencies, and exposes the three
public endpoints:

- ``GET  /api/health``          -- liveness probe (no auth)
- ``GET  /api/categories``      -- taxonomy list  (no auth)
- ``POST /api/email/analyze``   -- email analysis (auth required)
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import RateLimiter, verify_api_key
from app.config import get_settings
from app.db.database import get_db, init_db
from app.db.models import EmailAnalysisCache, UsageLog
from app.email.cleaner import clean_email_body
from app.email.hashing import compute_content_hash
from app.email.taxonomy import get_categories, get_taxonomy_version
from app.llm.openai_client import MailPilotLLM, LLMError
from app.llm.prompts import should_escalate
from app.schemas import (
    CacheInfo,
    CategoryListResponse,
    CategoryRecommendation,
    Deadline,
    EmailAnalysisRequest,
    EmailAnalysisResponse,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
)

logger = logging.getLogger("mailpilot")

# ── Settings & globals ────────────────────────────────────────────────

settings = get_settings()

rate_limiter = RateLimiter()


# ── Application lifecycle ────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize database on startup."""
    await init_db()
    logger.info("MailPilot backend started — database initialized.")
    yield


# ── Application factory ──────────────────────────────────────────────

app = FastAPI(
    title="MailPilot",
    version="0.1.0",
    description=(
        "Outlook email summarization and categorization assistant. "
        "Analyzes email content, suggests categories, priority, and actions."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.MAILPILOT_ALLOWED_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Singleton LLM instance (created once at import time)
llm = MailPilotLLM(
    api_key=settings.OPENAI_API_KEY,
    default_model=settings.DEFAULT_MODEL,
    escalation_model=settings.ESCALATION_MODEL,
)


# ── Utility helpers ───────────────────────────────────────────────────


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Build a JSON error envelope."""
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def _parse_categories(raw: Any = None) -> list[CategoryRecommendation]:
    """Safely parse LLM category output into schema objects."""
    if not raw or not isinstance(raw, list):
        return []
    results: list[CategoryRecommendation] = []
    for item in raw[: settings.MAX_CATEGORIES_PER_EMAIL]:
        if isinstance(item, dict):
            results.append(
                CategoryRecommendation(
                    name=item.get("name", "Unknown"),
                    confidence=max(0.0, min(1.0, float(item.get("confidence", 0.5)))),
                    reason=item.get("reason", ""),
                )
            )
        elif isinstance(item, str):
            # LLM sometimes returns plain strings like ["Finance", "Action Required"]
            results.append(
                CategoryRecommendation(
                    name=item, confidence=0.7, reason=""
                )
            )
    return results


def _parse_deadline(raw: Any = None) -> Deadline:
    """Safely parse LLM deadline output into the schema object."""
    if raw is None:
        return Deadline(exists=False)
    if isinstance(raw, dict):
        return Deadline(
            exists=bool(raw.get("exists", False)),
            date=raw.get("date"),
            evidence=raw.get("evidence"),
        )
    # If raw is a string (e.g., "2026-06-15"), treat as a date
    if isinstance(raw, str) and raw.strip():
        return Deadline(exists=True, date=raw.strip())
    return Deadline(exists=False)


# ── Endpoints ─────────────────────────────────────────────────────────


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe -- returns OK and the current API version."""
    return HealthResponse(status="ok", version="0.1.0")


@app.get("/api/categories", response_model=CategoryListResponse)
async def list_categories() -> CategoryListResponse:
    """Return the current email category taxonomy."""
    return CategoryListResponse(
        taxonomy_version=get_taxonomy_version(),
        categories=get_categories(),
    )


@app.post("/api/email/analyze")
async def analyze_email(
    request: Request,
    body: EmailAnalysisRequest,
    api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Analyze an email and return summary, categories, and actions.

    Requires a valid API key via the ``X-API-Key`` header.  Results are
    cached by ``(provider, message_id, content_hash, taxonomy_version)``
    so repeated identical requests are served instantly.
    """

    # -- Rate limiting (use API key as client identifier) ---------------
    try:
        rate_limiter.check_rate_limit(api_key)
    except Exception:
        return _error_response(429, "RATE_LIMITED", "Rate limit exceeded.")

    # -- Validate body size --------------------------------------------
    if len(body.body_text) > settings.REQUEST_SIZE_LIMIT:
        return _error_response(
            413,
            "BODY_TOO_LARGE",
            f"Email body exceeds the {settings.REQUEST_SIZE_LIMIT} "
            f"character limit.",
        )

    # -- Handle empty body gracefully ----------------------------------
    body_text = body.body_text.strip() or body.subject or "(empty email)"

    # -- Clean body and compute hash -----------------------------------
    taxonomy_version = get_taxonomy_version()
    cleaned_body = clean_email_body(body_text, max_length=settings.MAX_BODY_LENGTH)
    content_hash = compute_content_hash(
        provider=body.provider,
        message_id=body.message_id,
        body_text=cleaned_body,
        taxonomy_version=taxonomy_version,
    )

    # -- Cache lookup --------------------------------------------------
    try:
        stmt = select(EmailAnalysisCache).where(
            EmailAnalysisCache.provider == body.provider,
            EmailAnalysisCache.message_id == body.message_id,
            EmailAnalysisCache.content_hash == content_hash,
            EmailAnalysisCache.taxonomy_version == taxonomy_version,
        )
        result = await db.execute(stmt)
        cached = result.scalar_one_or_none()
    except Exception as exc:
        logger.exception("Cache lookup failed: %s", exc)
        return _error_response(500, "CACHE_ERROR", "Cache lookup failed.")

    # -- Cache hit: return stored result --------------------------------
    if cached is not None:
        try:
            categories_data = json.loads(cached.recommended_categories_json)
            deadline_data = json.loads(cached.deadline_json)
        except json.JSONDecodeError:
            categories_data = []
            deadline_data = {"exists": False}

        response = EmailAnalysisResponse(
            message_id=body.message_id,
            summary=cached.summary,
            priority=cached.priority,  # type: ignore[arg-type]
            recommended_categories=_parse_categories(categories_data),
            suggested_action=cached.suggested_action,
            needs_reply=cached.needs_reply,
            deadline=_parse_deadline(deadline_data),
            cache=CacheInfo(hit=True, content_hash=content_hash),
        )

        # Log the cache hit
        try:
            usage_entry = UsageLog(
                provider=body.provider,
                message_id=body.message_id,
                model=cached.model,
                input_tokens=0,
                output_tokens=0,
                estimated_cost_usd=0.0,
                cache_hit=True,
            )
            db.add(usage_entry)
            await db.flush()
        except Exception:
            logger.warning("Failed to log cache-hit usage entry.")

        return JSONResponse(
            status_code=200,
            content=response.model_dump(),
        )

    # -- Cache miss: call LLM ------------------------------------------
    escalate = should_escalate(body.subject, cleaned_body)
    allowed_categories = get_categories()

    try:
        llm_result, usage_info = await llm.analyze_email(
            subject=body.subject,
            sender_name=body.sender.name,
            sender_email=body.sender.email,
            to_list=body.to,
            received_at=body.received_at,
            body_text=cleaned_body,
            allowed_categories=allowed_categories,
            existing_categories=body.existing_categories,
            escalate=escalate,
        )
    except LLMError as exc:
        err_msg = str(exc).lower()
        if "timeout" in err_msg:
            return _error_response(
                504, "LLM_TIMEOUT", "The language model request timed out."
            )
        logger.error("LLM error: %s", exc)
        return _error_response(
            502, "OPENAI_ERROR", "Upstream language model service error."
        )
    except ValueError as exc:
        logger.error("LLM returned invalid output: %s", exc)
        return _error_response(
            502,
            "LLM_INVALID_OUTPUT",
            "The language model returned an invalid response.",
        )
    except Exception as exc:
        logger.exception("Unexpected LLM error: %s", exc)
        return _error_response(
            502, "OPENAI_ERROR", "Upstream language model service error."
        )

    # -- Build response ------------------------------------------------
    # Use .get() with defaults — LLM output may omit any field
    summary = llm_result.get("summary", "No summary available.")
    priority = llm_result.get("priority", "medium")
    suggested_action = llm_result.get("suggested_action", "Review this email.")
    needs_reply = llm_result.get("needs_reply", False)
    recommended = _parse_categories(llm_result.get("recommended_categories", []))
    deadline = _parse_deadline(llm_result.get("deadline"))

    response = EmailAnalysisResponse(
        message_id=body.message_id,
        summary=summary,
        priority=priority,
        recommended_categories=recommended,
        suggested_action=suggested_action,
        needs_reply=needs_reply,
        deadline=deadline,
        cache=CacheInfo(hit=False, content_hash=content_hash),
    )

    # -- Store in cache ------------------------------------------------
    try:
        cache_entry = EmailAnalysisCache(
            provider=body.provider,
            message_id=body.message_id,
            conversation_id=body.conversation_id,
            content_hash=content_hash,
            taxonomy_version=taxonomy_version,
            model=usage_info.get("model", "unknown"),
            summary=summary,
            priority=priority,
            recommended_categories_json=json.dumps(
                [c.model_dump() for c in recommended]
            ),
            suggested_action=suggested_action,
            needs_reply=needs_reply,
            deadline_json=json.dumps(deadline.model_dump() if deadline else None),
        )
        db.add(cache_entry)
        await db.flush()
    except Exception:
        logger.warning("Failed to store analysis in cache.")

    # -- Log usage -----------------------------------------------------
    try:
        usage_entry = UsageLog(
            provider=body.provider,
            message_id=body.message_id,
            model=usage_info.get("model", "unknown"),
            input_tokens=usage_info.get("input_tokens", 0),
            output_tokens=usage_info.get("output_tokens", 0),
            estimated_cost_usd=0.0,  # cost estimation can be added later
            cache_hit=False,
        )
        db.add(usage_entry)
        await db.flush()
    except Exception:
        logger.warning("Failed to log usage entry.")

    return JSONResponse(
        status_code=200,
        content=response.model_dump(),
    )


# ── Global exception handler ─────────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all handler ensuring every failure returns a JSON envelope."""
    logger.exception("Unhandled exception: %s", exc)
    return _error_response(
        500, "INTERNAL_ERROR", "An unexpected internal error occurred."
    )
