"""Async OpenAI client for email analysis.

Wraps the OpenAI chat-completions API with MailPilot-specific prompt
construction, model selection, and output validation.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI, APIConnectionError, APIStatusError, APITimeoutError

from app.llm.prompts import SYSTEM_PROMPT, build_user_prompt, should_escalate
from app.llm.schemas import LLM_OUTPUT_SCHEMA, validate_llm_output

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when the LLM call fails in a non-recoverable way."""


class MailPilotLLM:
    """Async wrapper around the OpenAI chat-completions API.

    Parameters
    ----------
    api_key:
        OpenAI API key.
    default_model:
        Model used for normal-priority emails (e.g. ``"gpt-4o-mini"``).
    escalation_model:
        More capable model used when escalation keywords are detected
        (e.g. ``"gpt-4o"``).
    """

    def __init__(
        self,
        api_key: str,
        default_model: str,
        escalation_model: str,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._default_model = default_model
        self._escalation_model = escalation_model

    # ── Public API ──────────────────────────────────────────────────

    async def analyze_email(
        self,
        subject: str,
        sender_name: str | None,
        sender_email: str | None,
        to_list: list,
        received_at: str | None,
        body_text: str,
        allowed_categories: list[str],
        existing_categories: list[str],
        escalate: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Analyse an email and return structured triage information.

        Parameters
        ----------
        subject, sender_name, sender_email, to_list, received_at, body_text:
            Core email fields forwarded to the prompt builder.
        allowed_categories:
            Canonical taxonomy of category labels the model may assign.
        existing_categories:
            Categories already applied to this email.
        escalate:
            If *True*, force use of the escalation model regardless of
            keyword detection.

        Returns
        -------
        tuple[dict, dict]
            ``(analysis_result, usage_info)`` where *analysis_result* is the
            validated JSON dict and *usage_info* contains ``model``,
            ``input_tokens``, and ``output_tokens``.

        Raises
        ------
        LLMError
            On any unrecoverable OpenAI or validation failure.
        ValueError
            When the LLM output fails post-hoc validation (propagated
            from :func:`~app.llm.schemas.validate_llm_output`).
        """
        # (a) Build prompts
        user_prompt = build_user_prompt(
            subject=subject,
            sender_name=sender_name,
            sender_email=sender_email,
            to_list=to_list,
            received_at=received_at,
            body_text=body_text,
            allowed_categories=allowed_categories,
            existing_categories=existing_categories,
        )

        # (b) Choose model
        use_escalation = escalate or should_escalate(subject, body_text)
        model = self._escalation_model if use_escalation else self._default_model

        # (c) Call OpenAI
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
        except APIConnectionError as exc:
            logger.error("OpenAI connection error: %s", exc)
            raise LLMError("Failed to connect to the OpenAI API.") from exc
        except APITimeoutError as exc:
            logger.error("OpenAI request timed out: %s", exc)
            raise LLMError("OpenAI API request timed out.") from exc
        except APIStatusError as exc:
            logger.error("OpenAI API error %s: %s", exc.status_code, exc.message)
            raise LLMError(
                f"OpenAI API returned status {exc.status_code}: {exc.message}"
            ) from exc

        # (d) Parse and validate
        raw_content = response.choices[0].message.content
        if raw_content is None:
            raise LLMError("OpenAI returned an empty response.")

        try:
            parsed: dict[str, Any] = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM JSON: %s", raw_content[:500])
            raise LLMError("LLM response is not valid JSON.") from exc

        analysis_result = validate_llm_output(
            parsed, allowed_categories=allowed_categories
        )

        # (e) Build usage info
        usage = response.usage
        usage_info: dict[str, Any] = {
            "model": model,
            "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
        }

        logger.info(
            "Analysis complete — model=%s, in=%d, out=%d",
            model,
            usage_info["input_tokens"],
            usage_info["output_tokens"],
        )

        return analysis_result, usage_info
