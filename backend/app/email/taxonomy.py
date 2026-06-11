"""Category taxonomy management for email classification.

Provides the canonical list of email categories used by the
summarization pipeline and helpers to validate category labels.
"""

from __future__ import annotations

TAXONOMY_VERSION: str = "v1"

DEFAULT_CATEGORIES: list[str] = [
    "Action Required",
    "Follow Up",
    "School / NTU",
    "Research",
    "Conference",
    "Finance",
    "Receipt",
    "Travel",
    "Personal",
    "Administrative",
    "Low Priority",
    "Archive Later",
]

_CATEGORY_SET: set[str] = set(DEFAULT_CATEGORIES)


def get_categories() -> list[str]:
    """Return the full ordered list of default email categories."""
    return list(DEFAULT_CATEGORIES)


def is_valid_category(name: str) -> bool:
    """Check whether *name* is a recognised category label."""
    return name in _CATEGORY_SET


def validate_categories(names: list[str]) -> list[str]:
    """Filter *names* to only those present in the taxonomy."""
    return [n for n in names if n in _CATEGORY_SET]


def get_taxonomy_version() -> str:
    """Return the current taxonomy version string."""
    return TAXONOMY_VERSION
