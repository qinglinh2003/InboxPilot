"""Tests for app.email.hashing -- content hashing for cache keys."""

from __future__ import annotations

from app.email.hashing import compute_content_hash


_PROVIDER = "outlook"
_MSG_ID = "AAMkAGI2TG93AAA="
_BODY = "Please submit your verification report by 30 June 2026."
_TAXONOMY = "v1"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_hash_deterministic() -> None:
    h1 = compute_content_hash(_PROVIDER, _MSG_ID, _BODY, _TAXONOMY)
    h2 = compute_content_hash(_PROVIDER, _MSG_ID, _BODY, _TAXONOMY)
    assert h1 == h2
    assert isinstance(h1, str)
    assert len(h1) == 64  # SHA-256 hex digest


# ---------------------------------------------------------------------------
# Sensitivity to each input dimension
# ---------------------------------------------------------------------------

def test_hash_changes_with_body() -> None:
    h1 = compute_content_hash(_PROVIDER, _MSG_ID, _BODY, _TAXONOMY)
    h2 = compute_content_hash(_PROVIDER, _MSG_ID, "Different body content.", _TAXONOMY)
    assert h1 != h2


def test_hash_changes_with_provider() -> None:
    h1 = compute_content_hash("outlook", _MSG_ID, _BODY, _TAXONOMY)
    h2 = compute_content_hash("gmail", _MSG_ID, _BODY, _TAXONOMY)
    assert h1 != h2


def test_hash_changes_with_taxonomy_version() -> None:
    h1 = compute_content_hash(_PROVIDER, _MSG_ID, _BODY, "v1")
    h2 = compute_content_hash(_PROVIDER, _MSG_ID, _BODY, "v2")
    assert h1 != h2


# ---------------------------------------------------------------------------
# Body normalisation (whitespace invariance)
# ---------------------------------------------------------------------------

def test_body_normalization() -> None:
    body_a = "Hello   world,  this  is  a   test."
    body_b = "Hello world, this is a test."
    h1 = compute_content_hash(_PROVIDER, _MSG_ID, body_a, _TAXONOMY)
    h2 = compute_content_hash(_PROVIDER, _MSG_ID, body_b, _TAXONOMY)
    assert h1 == h2, "Whitespace-only differences should produce the same hash"
