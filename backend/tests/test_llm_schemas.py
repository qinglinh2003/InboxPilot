"""Tests for app.llm.schemas -- LLM output validation.

These tests validate the structured output produced by the LLM before
it is returned to the client.  The ``validate_llm_output`` function is
expected to enforce category validity, field constraints, and limits.
"""

from __future__ import annotations

import pytest

from app.email.taxonomy import get_categories
from app.llm.schemas import validate_llm_output

# Use the real taxonomy as the allowed categories list.
ALLOWED_CATEGORIES = get_categories()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_output(**overrides) -> dict:
    """Return a minimal valid LLM output dict with optional overrides."""
    base = {
        "summary": "NTU Admissions requests a verification report by 30 June 2026.",
        "priority": "high",
        "recommended_categories": [
            {
                "name": "School / NTU",
                "confidence": 0.95,
                "reason": "From NTU Admissions.",
            },
            {
                "name": "Action Required",
                "confidence": 0.90,
                "reason": "Requires document upload.",
            },
        ],
        "suggested_action": "Upload verification report before deadline.",
        "needs_reply": False,
        "deadline": {
            "exists": True,
            "date": "2026-06-30",
            "evidence": "no later than 30 June 2026",
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_valid_output_passes() -> None:
    result = validate_llm_output(_base_output(), allowed_categories=ALLOWED_CATEGORIES)
    assert result["summary"]
    assert result["priority"] == "high"
    assert len(result["recommended_categories"]) == 2


# ---------------------------------------------------------------------------
# Category validation
# ---------------------------------------------------------------------------

def test_filters_invalid_categories() -> None:
    output = _base_output(
        recommended_categories=[
            {"name": "School / NTU", "confidence": 0.9, "reason": "Valid."},
            {"name": "Totally Fake", "confidence": 0.8, "reason": "Invalid."},
        ],
    )
    result = validate_llm_output(output, allowed_categories=ALLOWED_CATEGORIES)
    names = [c["name"] for c in result["recommended_categories"]]
    assert "School / NTU" in names
    assert "Totally Fake" not in names


def test_limits_max_categories() -> None:
    cats = [
        {"name": "Action Required", "confidence": 0.9, "reason": "r1"},
        {"name": "Follow Up", "confidence": 0.85, "reason": "r2"},
        {"name": "Research", "confidence": 0.80, "reason": "r3"},
        {"name": "Finance", "confidence": 0.75, "reason": "r4"},
        {"name": "Personal", "confidence": 0.70, "reason": "r5"},
    ]
    output = _base_output(recommended_categories=cats)
    result = validate_llm_output(output, allowed_categories=ALLOWED_CATEGORIES)
    assert len(result["recommended_categories"]) <= 3


# ---------------------------------------------------------------------------
# Field-level validation
# ---------------------------------------------------------------------------

def test_rejects_empty_summary() -> None:
    with pytest.raises(ValueError):
        validate_llm_output(_base_output(summary=""), allowed_categories=ALLOWED_CATEGORIES)


def test_rejects_deadline_without_evidence() -> None:
    bad_deadline = {"exists": True, "date": "2026-06-30", "evidence": None}
    with pytest.raises(ValueError):
        validate_llm_output(_base_output(deadline=bad_deadline), allowed_categories=ALLOWED_CATEGORIES)


def test_rejects_invalid_priority() -> None:
    with pytest.raises(ValueError):
        validate_llm_output(_base_output(priority="urgent"), allowed_categories=ALLOWED_CATEGORIES)
