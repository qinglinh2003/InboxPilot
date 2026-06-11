"""Application configuration via environment variables.

Uses pydantic-settings to load values from .env and the process
environment.  Call ``get_settings()`` to obtain the singleton; the
result is cached so the .env file is read at most once.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All runtime knobs for the MailPilot backend."""

    # --- secrets / external credentials ---
    OPENAI_API_KEY: str
    MAILPILOT_API_TOKEN: str

    # --- CORS ---
    MAILPILOT_ALLOWED_ORIGIN: str = "https://localhost:3000"

    # --- persistence ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./mailpilot.db"

    # --- LLM defaults ---
    DEFAULT_MODEL: str = "gpt-4o-mini"
    ESCALATION_MODEL: str = "gpt-4o"

    # --- processing limits ---
    MAX_BODY_LENGTH: int = 5000
    MAX_CATEGORIES_PER_EMAIL: int = 3
    REQUEST_SIZE_LIMIT: int = 100_000
    RATE_LIMIT_PER_MINUTE: int = 30

    # --- taxonomy ---
    TAXONOMY_VERSION: str = "v1"

    # Reads from process environment first (set via `source env.sh`),
    # falls back to .env file if present (for IDE / pytest convenience).
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()  # type: ignore[call-arg]
