"""SQLAlchemy ORM models for the MailPilot backend.

Tables
------
- **email_analysis_cache** -- stores LLM analysis results keyed by
  ``(provider, message_id, content_hash, taxonomy_version)`` so
  identical requests are served from the DB instead of calling the model
  again.
- **usage_log** -- append-only ledger of every LLM call (or cache hit)
  for cost tracking and rate-limit accounting.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class EmailAnalysisCache(Base):
    """Cached LLM analysis for a specific email + taxonomy snapshot."""

    __tablename__ = "email_analysis_cache"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "message_id",
            "content_hash",
            "taxonomy_version",
            name="uq_cache_lookup",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)

    # --- analysis payload ---
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    recommended_categories_json: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False)
    needs_reply: Mapped[bool] = mapped_column(Boolean, nullable=False)
    deadline_json: Mapped[str] = mapped_column(Text, nullable=False)

    # --- timestamps ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<EmailAnalysisCache id={self.id} "
            f"provider={self.provider!r} message_id={self.message_id!r}>"
        )


class UsageLog(Base):
    """Append-only record of every LLM invocation or cache hit."""

    __tablename__ = "usage_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<UsageLog id={self.id} "
            f"provider={self.provider!r} model={self.model!r} "
            f"cache_hit={self.cache_hit}>"
        )
