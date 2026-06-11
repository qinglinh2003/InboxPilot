"""Authentication and rate-limiting middleware for the MailPilot API.

Provides an API-key verification dependency and a simple in-memory
per-minute rate limiter suitable for single-process deployments.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import get_settings

# ── API-key header scheme ─────────────────────────────────────────────

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(API_KEY_HEADER),
) -> str:
    """Validate the incoming API key against the configured token.

    Raises
    ------
    HTTPException 401
        If the header is missing or the key does not match
        ``settings.MAILPILOT_API_TOKEN``.
    """
    settings = get_settings()
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide it via the X-API-Key header.",
        )
    if api_key != settings.MAILPILOT_API_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
        )
    return api_key


# ── In-memory rate limiter ────────────────────────────────────────────


class RateLimiter:
    """Simple per-minute sliding-window rate limiter.

    Tracks request timestamps per *client_id* in memory.  Suitable for
    a single-process deployment; for multi-process production use switch
    to Redis-backed counters.

    Parameters
    ----------
    max_requests_per_minute:
        Maximum allowed requests within any rolling 60-second window.
    """

    def __init__(self, max_requests_per_minute: int | None = None) -> None:
        settings = get_settings()
        self.max_rpm: int = (
            max_requests_per_minute
            if max_requests_per_minute is not None
            else settings.RATE_LIMIT_PER_MINUTE
        )
        # client_id -> list of Unix timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check_rate_limit(self, client_id: str) -> None:
        """Allow the request or raise *HTTPException 429*.

        Prunes timestamps older than 60 seconds before counting.
        """
        now = time.monotonic()
        window_start = now - 60.0

        # Prune expired entries
        timestamps = self._requests[client_id]
        self._requests[client_id] = [
            ts for ts in timestamps if ts > window_start
        ]

        if len(self._requests[client_id]) >= self.max_rpm:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded. Maximum {self.max_rpm} "
                    f"requests per minute."
                ),
            )

        self._requests[client_id].append(now)
