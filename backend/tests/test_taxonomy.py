"""Tests for app.email.taxonomy -- category taxonomy helpers."""

from __future__ import annotations

from app.email.taxonomy import (
    DEFAULT_CATEGORIES,
    get_categories,
    is_valid_category,
    validate_categories,
)


def test_get_categories_returns_all() -> None:
    cats = get_categories()
    assert isinstance(cats, list)
    assert len(cats) == len(DEFAULT_CATEGORIES)
    # Must preserve order
    assert cats == DEFAULT_CATEGORIES
    # Must return a copy, not the original list
    cats.append("Spam")
    assert len(get_categories()) == len(DEFAULT_CATEGORIES)


def test_is_valid_category_true() -> None:
    assert is_valid_category("Action Required") is True
    assert is_valid_category("School / NTU") is True
    assert is_valid_category("Low Priority") is True


def test_is_valid_category_false() -> None:
    assert is_valid_category("Not A Real Category") is False
    assert is_valid_category("") is False
    assert is_valid_category("action required") is False  # case-sensitive


def test_validate_categories_filters_invalid() -> None:
    mixed = ["Action Required", "Bogus", "Research", "Also Bogus"]
    result = validate_categories(mixed)
    assert result == ["Action Required", "Research"]
