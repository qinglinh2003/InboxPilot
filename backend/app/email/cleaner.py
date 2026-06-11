"""Email body cleaning utilities.

Strips HTML, signatures, quoted replies, unsubscribe blocks, legal
footers, tracking artifacts, and excessive whitespace so that the
downstream summarisation model receives a compact, meaningful text.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def clean_email_body(body: str, max_length: int = 5000) -> str:
    """Clean raw email body text for downstream processing.

    Pipeline order:
        1. Strip HTML tags
        2. Remove email signatures
        3. Remove quoted replies
        4. Remove noise blocks (unsubscribe, legal, tracking)
        5. Normalise whitespace
        6. Truncate to *max_length* if necessary
    """
    text = body
    text = _strip_html(text)
    text = _remove_signatures(text)
    text = _remove_quoted_replies(text)
    text = _remove_noise_blocks(text)
    text = _normalize_whitespace(text)
    text = _truncate(text, max_length)
    return text


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Precompiled patterns -------------------------------------------------------

_RE_HTML_TAG = re.compile(r"<[^>]+>")
_RE_HTML_ENTITY = re.compile(r"&\w+;")

_RE_SIGNATURE_LINE = re.compile(
    r"^(?:--|—|__)"           # common signature delimiters
    r"|^Sent from my "        # mobile client boilerplate
    r"|^Get Outlook for "     # Outlook mobile
    r"|^Sent via "            # generic mobile
    r"|^Sent with "
    r"|^Powered by ",
    re.IGNORECASE,
)

_RE_QUOTED_HEADER = re.compile(
    r"^On .+ wrote:\s*$"             # "On <date> <person> wrote:"
    r"|^From:\s.+Sent:\s"            # Outlook-style "From: ... Sent: ..."
    r"|^-{3,}\s*Original Message",   # "--- Original Message ---"
    re.IGNORECASE,
)
_RE_QUOTED_LINE = re.compile(r"^>")

_RE_UNSUBSCRIBE = re.compile(
    r"unsubscribe|opt[\s-]?out|manage\s+preferences|email\s+preferences"
    r"|update\s+your\s+preferences|stop\s+receiving",
    re.IGNORECASE,
)

_RE_LEGAL_FOOTER = re.compile(
    r"confidential|disclaimer|privileged|intended\s+recipient"
    r"|may\s+not\s+be\s+copied|legal\s+notice",
    re.IGNORECASE,
)

_RE_TRACKING_URL = re.compile(
    r"https?://[^\s]*(?:click\.|track\.|trk\.|open\.)[^\s]*",
    re.IGNORECASE,
)

_RE_BASE64_BLOB = re.compile(r"[A-Za-z0-9+/=]{80,}")

_RE_MULTI_NEWLINES = re.compile(r"\n{3,}")
_RE_MULTI_SPACES = re.compile(r"[ \t]{2,}")


def _strip_html(text: str) -> str:
    """Remove HTML tags and common entities."""
    text = _RE_HTML_TAG.sub("", text)
    text = _RE_HTML_ENTITY.sub(" ", text)
    return text


def _remove_signatures(text: str) -> str:
    """Remove email signature blocks.

    Once a signature delimiter is encountered, everything from that
    line onward is discarded.
    """
    lines: list[str] = text.splitlines()
    cleaned: list[str] = []
    for line in lines:
        if _RE_SIGNATURE_LINE.search(line.strip()):
            break
        cleaned.append(line)
    return "\n".join(cleaned)


def _remove_quoted_replies(text: str) -> str:
    """Remove quoted reply sections.

    Drops lines starting with ``>`` and common "On ... wrote:" /
    "From: ... Sent: ..." headers together with everything after them.
    """
    lines: list[str] = text.splitlines()
    cleaned: list[str] = []
    in_quote = False
    for line in lines:
        stripped = line.strip()
        if _RE_QUOTED_HEADER.search(stripped):
            in_quote = True
            continue
        if in_quote:
            continue
        if _RE_QUOTED_LINE.match(stripped):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def _remove_noise_blocks(text: str) -> str:
    """Remove unsubscribe blocks, legal footers, and tracking artifacts."""
    lines: list[str] = text.splitlines()
    cleaned: list[str] = []
    for line in lines:
        if _RE_UNSUBSCRIBE.search(line):
            continue
        if _RE_LEGAL_FOOTER.search(line):
            continue
        if _RE_TRACKING_URL.search(line):
            continue
        if _RE_BASE64_BLOB.search(line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def _normalize_whitespace(text: str) -> str:
    """Collapse excessive whitespace and blank lines."""
    text = _RE_MULTI_SPACES.sub(" ", text)
    text = _RE_MULTI_NEWLINES.sub("\n\n", text)
    return text.strip()


def _truncate(text: str, max_length: int) -> str:
    """Truncate *text* to *max_length*, keeping head and tail context.

    If the text is within the limit it is returned unchanged.  Otherwise
    the first 2500 characters and the last 1500 characters are kept,
    separated by a truncation marker.
    """
    if len(text) <= max_length:
        return text
    head = text[:2500]
    tail = text[-1500:]
    return head + "\n[...truncated...]\n" + tail
