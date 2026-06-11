"""Tests for app.email.cleaner -- email body cleaning pipeline."""

from __future__ import annotations

from app.email.cleaner import clean_email_body


# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------

def test_strip_html_tags(sample_html_email: str) -> None:
    result = clean_email_body(sample_html_email)
    assert "<p>" not in result
    assert "<b>" not in result
    assert "<a " not in result
    assert "</body>" not in result
    # Meaningful text should survive
    assert "order" in result.lower()
    assert "shipped" in result.lower()


# ---------------------------------------------------------------------------
# Signature removal
# ---------------------------------------------------------------------------

def test_remove_email_signature() -> None:
    body = (
        "Hi, please review the attached report.\n\n"
        "--\n"
        "Dr. Alice\n"
        "Department of CS\n"
        "NTU Singapore\n"
    )
    result = clean_email_body(body)
    assert "Dr. Alice" not in result
    assert "Department of CS" not in result
    assert "review the attached report" in result


# ---------------------------------------------------------------------------
# Quoted reply removal
# ---------------------------------------------------------------------------

def test_remove_quoted_replies() -> None:
    body = (
        "Sounds good, I will send it over.\n\n"
        "On Mon, 1 Jun 2026 at 10:00, Bob <bob@example.com> wrote:\n"
        "> Can you share the draft?\n"
        "> Thanks.\n"
    )
    result = clean_email_body(body)
    assert "I will send it over" in result
    assert "Can you share the draft" not in result
    assert "> Thanks." not in result


# ---------------------------------------------------------------------------
# Unsubscribe block removal
# ---------------------------------------------------------------------------

def test_remove_unsubscribe_blocks() -> None:
    body = (
        "Your weekly digest is ready.\n\n"
        "To unsubscribe from this mailing list click here.\n"
        "Manage your email preferences at https://example.com/prefs\n"
    )
    result = clean_email_body(body)
    assert "weekly digest is ready" in result
    assert "unsubscribe" not in result.lower()


# ---------------------------------------------------------------------------
# Legal footer removal
# ---------------------------------------------------------------------------

def test_remove_legal_footers() -> None:
    body = (
        "Meeting confirmed for Thursday.\n\n"
        "CONFIDENTIALITY NOTICE: This email is intended for the intended "
        "recipient only and may contain privileged information.\n"
    )
    result = clean_email_body(body)
    assert "Meeting confirmed" in result
    assert "confidentiality" not in result.lower()


# ---------------------------------------------------------------------------
# Whitespace normalisation
# ---------------------------------------------------------------------------

def test_normalize_whitespace() -> None:
    body = "Hello   world.\n\n\n\n\nSecond   paragraph."
    result = clean_email_body(body)
    # Multiple spaces collapsed to single space
    assert "Hello world." in result
    assert "Second paragraph." in result
    # No more than two consecutive newlines
    assert "\n\n\n" not in result


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------

def test_truncation_short_body() -> None:
    body = "Short email body that is well under the limit."
    result = clean_email_body(body, max_length=5000)
    assert result == body


def test_truncation_long_body(sample_long_email: str) -> None:
    result = clean_email_body(sample_long_email, max_length=5000)
    # The result must respect the max-length budget (head + marker + tail)
    assert "[...truncated...]" in result
    # Head portion (first 2500 chars of cleaned text) should be present
    assert result[:100]  # non-empty head
    # Tail portion should come from end of original cleaned text
    tail_after_marker = result.split("[...truncated...]")[1]
    assert len(tail_after_marker.strip()) > 0


# ---------------------------------------------------------------------------
# Integration: full pipeline
# ---------------------------------------------------------------------------

def test_clean_email_body_integration(sample_email_body: str) -> None:
    result = clean_email_body(sample_email_body)
    # Original meaningful content preserved
    assert "verification report" in result.lower()
    assert "NTU Office of Admissions" in result
    # Result is stripped of leading/trailing whitespace
    assert result == result.strip()
