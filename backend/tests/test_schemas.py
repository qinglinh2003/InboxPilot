"""Tests for app.schemas -- Pydantic request / response models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import (
    CacheInfo,
    CategoryRecommendation,
    Deadline,
    EmailAnalysisRequest,
    EmailAnalysisResponse,
)


# ---------------------------------------------------------------------------
# EmailAnalysisRequest
# ---------------------------------------------------------------------------

def test_valid_analysis_request(sample_request_data: dict) -> None:
    req = EmailAnalysisRequest(**sample_request_data)
    assert req.provider == "outlook"
    assert req.message_id == "AAMkAGI2TG93AAA="
    assert req.subject == "Action Required: Submit Verification Report"
    assert req.sender.email == "admissions@ntu.edu.sg"
    assert req.body_text  # non-empty


def test_request_missing_required_field(sample_request_data: dict) -> None:
    # message_id is required and has no default
    incomplete = {k: v for k, v in sample_request_data.items() if k != "message_id"}
    with pytest.raises(ValidationError) as exc_info:
        EmailAnalysisRequest(**incomplete)
    errors = exc_info.value.errors()
    field_names = [e["loc"][-1] for e in errors]
    assert "message_id" in field_names


# ---------------------------------------------------------------------------
# EmailAnalysisResponse
# ---------------------------------------------------------------------------

def _build_response(**overrides) -> dict:
    """Return a minimal valid response dict, with optional overrides."""
    base = {
        "message_id": "AAMkAGI2TG93AAA=",
        "summary": "NTU Admissions requests a verification report.",
        "priority": "high",
        "recommended_categories": [
            {"name": "School / NTU", "confidence": 0.95, "reason": "From NTU."},
        ],
        "suggested_action": "Upload the report.",
        "needs_reply": False,
        "deadline": {"exists": True, "date": "2026-06-30", "evidence": "by 30 June"},
        "cache": {"hit": False, "content_hash": "abc123"},
    }
    base.update(overrides)
    return base


def test_valid_analysis_response() -> None:
    resp = EmailAnalysisResponse(**_build_response())
    assert resp.priority == "high"
    assert resp.deadline.exists is True
    assert len(resp.recommended_categories) == 1


def test_priority_validation() -> None:
    """Only 'high', 'medium', 'low' are accepted for priority."""
    # Valid values should pass
    for p in ("high", "medium", "low"):
        resp = EmailAnalysisResponse(**_build_response(priority=p))
        assert resp.priority == p

    # Invalid value must be rejected
    with pytest.raises(ValidationError):
        EmailAnalysisResponse(**_build_response(priority="critical"))
