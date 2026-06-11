"""Pydantic request / response schemas for the MailPilot API.

Every model here is a *data-transfer object* that lives at the API
boundary.  Internal domain logic should not depend on these directly.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── Shared components ────────────────────────────────────────────────


class EmailContact(BaseModel):
    """A single email participant (sender / recipient)."""

    name: str | None = None
    email: str | None = None


class UserContext(BaseModel):
    """Optional per-user preferences attached to an analysis request."""

    preferred_categories: list[str] = Field(default_factory=list)
    timezone: str = "America/Los_Angeles"


# ── Request ──────────────────────────────────────────────────────────


class EmailAnalysisRequest(BaseModel):
    """Payload sent by the Outlook add-in when requesting analysis."""

    provider: str
    message_id: str
    conversation_id: str | None = None
    subject: str
    sender: EmailContact
    to: list[EmailContact] = Field(default_factory=list)
    cc: list[EmailContact] = Field(default_factory=list)
    received_at: str
    body_text: str = ""
    existing_categories: list[str] = Field(default_factory=list)
    user_context: UserContext | None = None


# ── Response sub-models ──────────────────────────────────────────────


class CategoryRecommendation(BaseModel):
    """A single suggested category with confidence and rationale."""

    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class Deadline(BaseModel):
    """Extracted deadline information from the email body."""

    exists: bool
    date: str | None = None
    evidence: str | None = None


class CacheInfo(BaseModel):
    """Indicates whether the response was served from cache."""

    hit: bool
    content_hash: str


# ── Primary response ─────────────────────────────────────────────────


class EmailAnalysisResponse(BaseModel):
    """Full analysis result returned to the add-in."""

    message_id: str
    summary: str
    priority: Literal["high", "medium", "low"]
    recommended_categories: list[CategoryRecommendation]
    suggested_action: str
    needs_reply: bool
    deadline: Deadline
    cache: CacheInfo


# ── Error / health / utility ─────────────────────────────────────────


class ErrorDetail(BaseModel):
    """Machine-readable error descriptor."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard envelope returned on any 4xx / 5xx."""

    error: ErrorDetail


class HealthResponse(BaseModel):
    """Returned by GET /health."""

    status: str
    version: str


class CategoryListResponse(BaseModel):
    """Returned by GET /categories."""

    taxonomy_version: str
    categories: list[str]
