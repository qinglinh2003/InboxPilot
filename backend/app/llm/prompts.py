"""LLM prompt construction for email analysis.

Builds the system and user prompts sent to OpenAI, and provides
keyword-based escalation detection to decide which model tier to use.
"""

from __future__ import annotations

# ── System prompt ───────────────────────────────────────────────────

SYSTEM_PROMPT: str = (
    "You are MailPilot, a private email triage assistant.\n"
    "Your job is to summarize the email, estimate priority, "
    "recommend categories, and suggest the next action.\n\n"
    "IMPORTANT RULES:\n"
    "- You must only use the provided email content. Do not invent facts.\n"
    '- The "priority" field MUST be exactly one of: "high", "medium", "low".\n'
    "  Do NOT use any other value (e.g. 'Action Required', 'urgent', 'critical').\n"
    '- The "recommended_categories" array must only contain names from the '
    "allowed categories list provided in the user prompt.\n"
    "- Return structured JSON that matches the required schema."
)

# ── Escalation keywords ────────────────────────────────────────────

ESCALATION_KEYWORDS: list[str] = [
    "legal",
    "immigration",
    "tuition",
    "medical",
    "financial",
    "academic deadline",
    "court",
    "visa",
    "tax",
    "insurance",
]


def should_escalate(subject: str, body_text: str) -> bool:
    """Return *True* if any escalation keyword appears in the subject or body.

    Matching is case-insensitive so that ``"VISA"`` or ``"Legal"`` both
    trigger escalation.
    """
    combined = f"{subject} {body_text}".lower()
    return any(kw in combined for kw in ESCALATION_KEYWORDS)


# ── User prompt builder ────────────────────────────────────────────


def build_user_prompt(
    subject: str,
    sender_name: str | None,
    sender_email: str | None,
    to_list: list,
    received_at: str | None,
    body_text: str,
    allowed_categories: list[str],
    existing_categories: list[str],
) -> str:
    """Construct the user-role prompt that accompanies :data:`SYSTEM_PROMPT`.

    The prompt contains:
    1. The allowed category taxonomy as a bullet list.
    2. Email metadata (From, To, Subject, Received at).
    3. Existing categories already applied to the email (if any).
    4. The full email body.

    Parameters
    ----------
    subject:
        Email subject line.
    sender_name:
        Display name of the sender, may be *None*.
    sender_email:
        Email address of the sender, may be *None*.
    to_list:
        Recipient list; each element should have ``name`` / ``email`` attrs
        or be a plain string.
    received_at:
        ISO-8601 timestamp (or human-readable date) of reception.
    body_text:
        Plain-text body of the email.
    allowed_categories:
        The full taxonomy of categories the model may choose from.
    existing_categories:
        Categories already assigned to the email by the user or rules.

    Returns
    -------
    str
        The fully formatted user prompt.
    """

    # -- Allowed categories
    cat_bullets = "\n".join(f"- {cat}" for cat in allowed_categories)
    sections: list[str] = [
        "## Allowed categories",
        cat_bullets,
    ]

    # -- Email metadata
    sender_display = _format_contact(sender_name, sender_email)
    to_display = ", ".join(_format_recipient(r) for r in to_list) or "(unknown)"

    sections.append(
        "\n".join(
            [
                "## Email metadata",
                f"From: {sender_display}",
                f"To: {to_display}",
                f"Subject: {subject}",
                f"Received at: {received_at or '(unknown)'}",
            ]
        )
    )

    # -- Existing categories (optional)
    if existing_categories:
        existing_bullets = "\n".join(f"- {cat}" for cat in existing_categories)
        sections.append(
            "\n".join(
                [
                    "## Existing categories",
                    existing_bullets,
                ]
            )
        )

    # -- Email body
    sections.append(
        "\n".join(
            [
                "## Email body",
                body_text,
            ]
        )
    )

    return "\n\n".join(sections)


# ── Internal helpers ────────────────────────────────────────────────


def _format_contact(name: str | None, email: str | None) -> str:
    """Format a single contact as ``Name <email>`` or best available."""
    if name and email:
        return f"{name} <{email}>"
    return name or email or "(unknown)"


def _format_recipient(recipient: object) -> str:
    """Format a recipient that may be a Pydantic model, dict, or string."""
    if isinstance(recipient, str):
        return recipient
    name = getattr(recipient, "name", None) or (
        recipient.get("name") if isinstance(recipient, dict) else None
    )
    email = getattr(recipient, "email", None) or (
        recipient.get("email") if isinstance(recipient, dict) else None
    )
    return _format_contact(name, email)
