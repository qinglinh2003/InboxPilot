"""Content hashing for email classification cache.

Produces a deterministic SHA-256 digest from provider, message id,
body text, and taxonomy version so that classification results can
be cached and invalidated when any input changes.
"""

from __future__ import annotations

import hashlib
import re

_RE_WHITESPACE = re.compile(r"\s+")


def compute_content_hash(
    provider: str,
    message_id: str,
    body_text: str,
    taxonomy_version: str,
) -> str:
    """Return a hex SHA-256 digest uniquely identifying the classification input.

    The hash is built from the concatenation of *provider*, *message_id*,
    the normalised *body_text*, and *taxonomy_version*.  Normalisation
    ensures that trivial whitespace differences do not bust the cache.
    """
    normalised_body = _normalize_body(body_text)
    payload = provider + message_id + normalised_body + taxonomy_version
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_body(body: str) -> str:
    """Normalise body text for stable hashing.

    Lowercases, strips leading/trailing whitespace, and collapses all
    internal whitespace runs to a single space.
    """
    text = body.lower().strip()
    text = _RE_WHITESPACE.sub(" ", text)
    return text
