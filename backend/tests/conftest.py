"""Shared pytest fixtures for the MailPilot test suite."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Sample email bodies
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_email_body() -> str:
    """Realistic NTU admissions email body."""
    return (
        "Dear Student,\n\n"
        "This is a follow-up from the NTU Office of Admissions regarding your "
        "graduate enrollment for the Fall 2026 semester.\n\n"
        "We kindly ask that you submit your official degree verification report "
        "no later than 30 June 2026. The report must be issued by your "
        "undergraduate institution and should include:\n\n"
        "  1. Your full legal name as it appears on your diploma\n"
        "  2. Degree conferred and date of conferral\n"
        "  3. Official institutional seal or digital verification link\n\n"
        "Please upload the document through the NTU Admissions Portal at "
        "https://admissions.ntu.edu.sg/verify. If you encounter any issues, "
        "contact the Admissions Help Desk at admissions@ntu.edu.sg.\n\n"
        "Failure to submit the report by the deadline may result in a hold "
        "on your enrollment.\n\n"
        "Best regards,\n"
        "NTU Office of Admissions"
    )


@pytest.fixture()
def sample_long_email() -> str:
    """Very long email body (>5000 chars) with signatures, quoted replies, and legal footers."""
    main_content = (
        "Dear Team,\n\n"
        "Please find below the detailed quarterly report for Q2 2026. "
        "This document covers all deliverables, milestones, and budget "
        "allocations across the three project workstreams.\n\n"
    )
    # Pad the body well past 5000 characters with realistic paragraphs
    for i in range(1, 31):
        main_content += (
            f"Section {i}: In this section we discuss the progress made on "
            f"deliverable {i}. The team completed approximately {60 + i}% of "
            f"the planned tasks for this phase. Key achievements include the "
            f"successful integration of module {i} with the upstream pipeline, "
            f"performance benchmarking against the baseline configuration, and "
            f"documentation of all API endpoints introduced in sprint {i}.\n\n"
        )

    # Email signature
    main_content += (
        "--\n"
        "Dr. Jane Smith\n"
        "Senior Research Fellow\n"
        "School of Computer Science and Engineering\n"
        "Nanyang Technological University\n"
        "Tel: +65 6790 1234\n\n"
    )

    # Quoted reply
    main_content += (
        "On Mon, 1 Jun 2026 at 09:15, John Doe <john.doe@ntu.edu.sg> wrote:\n"
        "> Thanks for the update, Jane.\n"
        "> I have reviewed the preliminary numbers and they look good.\n"
        "> Let me know if you need anything else.\n\n"
    )

    # Legal / confidentiality footer
    main_content += (
        "CONFIDENTIALITY NOTICE: This email and any attachments are for the "
        "exclusive and confidential use of the intended recipient. If you are "
        "not the intended recipient, please do not read, distribute, or take "
        "action based on this message. Any unauthorised use is strictly "
        "prohibited and may be unlawful.\n\n"
        "To unsubscribe from these notifications, visit "
        "https://mail.ntu.edu.sg/preferences/unsubscribe\n"
    )

    return main_content


@pytest.fixture()
def sample_html_email() -> str:
    """Email body containing HTML markup."""
    return (
        "<html><body>"
        "<p>Hi there,</p>"
        "<p>Your order <b>#12345</b> has been shipped.</p>"
        "<p>Track it <a href='https://track.example.com/12345'>here</a>.</p>"
        "<br/>"
        "<p>Thanks,<br/>The Shop Team</p>"
        "</body></html>"
    )


# ---------------------------------------------------------------------------
# Request / LLM-output fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_request_data() -> dict:
    """Dict matching the EmailAnalysisRequest schema."""
    return {
        "provider": "outlook",
        "message_id": "AAMkAGI2TG93AAA=",
        "conversation_id": "AAQkAGI2TG93BBB=",
        "subject": "Action Required: Submit Verification Report",
        "sender": {
            "name": "NTU Admissions",
            "email": "admissions@ntu.edu.sg",
        },
        "to": [
            {"name": "Qing Lin", "email": "qinglin@e.ntu.edu.sg"},
        ],
        "cc": [],
        "received_at": "2026-06-10T08:30:00Z",
        "body_text": (
            "Dear Student,\n\n"
            "Please submit your official degree verification report "
            "no later than 30 June 2026."
        ),
        "existing_categories": [],
        "user_context": None,
    }


@pytest.fixture()
def sample_llm_output() -> dict:
    """Dict matching the expected structured LLM output."""
    return {
        "summary": (
            "NTU Admissions requests submission of an official degree "
            "verification report by 30 June 2026 via the admissions portal."
        ),
        "priority": "high",
        "recommended_categories": [
            {
                "name": "School / NTU",
                "confidence": 0.95,
                "reason": "Email is from NTU Admissions regarding enrollment.",
            },
            {
                "name": "Action Required",
                "confidence": 0.92,
                "reason": "Student must upload a document before a deadline.",
            },
        ],
        "suggested_action": "Upload verification report to the NTU Admissions Portal before 30 June 2026.",
        "needs_reply": False,
        "deadline": {
            "exists": True,
            "date": "2026-06-30",
            "evidence": "no later than 30 June 2026",
        },
    }
