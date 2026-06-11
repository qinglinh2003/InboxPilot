"""Tests for the MailPilot FastAPI endpoints.

Uses ``httpx.AsyncClient`` with ``ASGITransport`` to test the app
without starting a real server.  The test env vars are set before
importing the app so that ``app.config.get_settings()`` does not
require a real ``.env`` file.
"""

from __future__ import annotations

import os

# Force test-specific env vars before importing the app.
# We use os.environ[] (not setdefault) so that tests always run with a
# known token, even if env.sh was already sourced into the shell.
TEST_API_KEY = "test-token-secret"
os.environ["OPENAI_API_KEY"] = "test-key-not-real"
os.environ["MAILPILOT_API_TOKEN"] = TEST_API_KEY

# Clear the cached settings singleton so pydantic-settings picks up
# the test env vars we just set.
from app.config import get_settings  # noqa: E402
get_settings.cache_clear()

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import app  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Health & categories (public endpoints)
# ---------------------------------------------------------------------------

async def test_health_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


async def test_categories_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/api/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert "categories" in data
    assert isinstance(data["categories"], list)
    assert len(data["categories"]) > 0
    assert "taxonomy_version" in data


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------

async def test_analyze_requires_auth(client: AsyncClient) -> None:
    """POST /api/email/analyze without an API key must return 401."""
    payload = {
        "provider": "outlook",
        "message_id": "test-id",
        "subject": "Test",
        "sender": {"name": "A", "email": "a@b.com"},
        "received_at": "2026-06-10T00:00:00Z",
        "body_text": "Hello.",
    }
    resp = await client.post("/api/email/analyze", json=payload)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Request size enforcement
# ---------------------------------------------------------------------------

async def test_analyze_rejects_large_body(client: AsyncClient) -> None:
    """Bodies exceeding REQUEST_SIZE_LIMIT should be rejected (413)."""
    oversized_body = "x" * 200_000  # well above 100 KB limit
    payload = {
        "provider": "outlook",
        "message_id": "test-id",
        "subject": "Test",
        "sender": {"name": "A", "email": "a@b.com"},
        "received_at": "2026-06-10T00:00:00Z",
        "body_text": oversized_body,
    }
    resp = await client.post(
        "/api/email/analyze",
        json=payload,
        headers={"X-API-Key": TEST_API_KEY},
    )
    assert resp.status_code == 413
    data = resp.json()
    assert data["error"]["code"] == "BODY_TOO_LARGE"
