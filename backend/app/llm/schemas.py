"""JSON schema for OpenAI structured output and result validation.

Defines the shape of the JSON the LLM must return and a post-hoc
validation function that enforces business rules before the result
is forwarded to the caller.
"""

from __future__ import annotations

from typing import Any

# ── JSON schema for OpenAI structured output ────────────────────────

LLM_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "A concise summary of the email.",
        },
        "priority": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "Estimated priority level.",
        },
        "recommended_categories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "reason": {"type": "string"},
                },
                "required": ["name", "confidence", "reason"],
            },
            "description": "Recommended category labels with confidence and rationale.",
        },
        "suggested_action": {
            "type": "string",
            "description": "A short suggested next action for the user.",
        },
        "needs_reply": {
            "type": "boolean",
            "description": "Whether the email likely requires a reply.",
        },
        "deadline": {
            "type": "object",
            "properties": {
                "exists": {"type": "boolean"},
                "date": {
                    "type": ["string", "null"],
                    "description": "ISO-8601 date or null if no deadline.",
                },
                "evidence": {
                    "type": ["string", "null"],
                    "description": "Quoted text from the email supporting the deadline.",
                },
            },
            "required": ["exists", "date", "evidence"],
            "description": "Extracted deadline information.",
        },
    },
    "required": [
        "summary",
        "priority",
        "recommended_categories",
        "suggested_action",
        "needs_reply",
        "deadline",
    ],
}

# ── Valid priority levels ───────────────────────────────────────────

_VALID_PRIORITIES: set[str] = {"high", "medium", "low"}


# ── Validation ──────────────────────────────────────────────────────


def validate_llm_output(
    output: dict[str, Any],
    allowed_categories: list[str],
    max_categories: int = 3,
) -> dict[str, Any]:
    """Validate and sanitise the raw LLM JSON output.

    Applies the following rules in order:

    a) Filter ``recommended_categories`` to only names present in
       *allowed_categories*.
    b) Limit the list to at most *max_categories* entries.
    c) Raise :class:`ValueError` if ``summary`` is empty.
    d) Raise :class:`ValueError` if ``deadline.exists`` is ``True`` but
       ``evidence`` is ``None``.
    e) Ensure ``priority`` is one of ``"high"``, ``"medium"``, ``"low"``.
    f) Return the validated / filtered dict.

    Parameters
    ----------
    output:
        Parsed JSON dict from the LLM response.
    allowed_categories:
        The canonical category taxonomy; any category not in this list
        is silently dropped.
    max_categories:
        Maximum number of categories to keep (default 3).

    Returns
    -------
    dict
        The cleaned output dict, safe to forward to the API response layer.

    Raises
    ------
    ValueError
        When the output violates an invariant that cannot be auto-fixed.
    """
    allowed_set = set(allowed_categories)

    # (a) Filter to allowed category names
    raw_cats: list[dict[str, Any]] = output.get("recommended_categories", [])
    filtered_cats = [c for c in raw_cats if c.get("name") in allowed_set]

    # (b) Enforce maximum
    output["recommended_categories"] = filtered_cats[:max_categories]

    # (c) Summary must not be empty
    summary = output.get("summary", "")
    if not summary or not summary.strip():
        raise ValueError("LLM output has an empty summary.")

    # (d) Deadline evidence required when deadline exists
    deadline: dict[str, Any] = output.get("deadline", {})
    if deadline.get("exists") is True and deadline.get("evidence") is None:
        raise ValueError(
            "Deadline is marked as existing but no evidence was provided."
        )

    # (e) Priority must be valid
    priority = output.get("priority", "")
    if priority not in _VALID_PRIORITIES:
        raise ValueError(
            f"Invalid priority '{priority}'; expected one of {sorted(_VALID_PRIORITIES)}."
        )

    return output
