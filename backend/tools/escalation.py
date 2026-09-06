import re

from database import create_ticket
from langchain_core.tools import tool

_VALID_URGENCY = {"normal", "urgent"}
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(email: str) -> str:
    if not _EMAIL_RE.match(email):
        raise ValueError(f"Invalid email address: {email}")
    return email


def _validate_urgency(urgency: str) -> str:
    if urgency not in _VALID_URGENCY:
        raise ValueError(f"Invalid urgency '{urgency}'. Must be one of: normal, urgent")
    return urgency


@tool
def escalate_to_human(email: str, issue_summary: str, urgency: str = "normal") -> str:
    """Escalate a complex or sensitive issue to a human support agent.
    Use for: legal complaints, security incidents, account compromise,
    highly frustrated customers, or issues that require human judgment.

    urgency: 'normal' or 'urgent'
    """
    _validate_email(email)
    _validate_urgency(urgency)

    ticket = create_ticket(
        email=email,
        category="escalation",
        subject=f"[ESCALATED] {issue_summary[:80]}",
        description=issue_summary,
        priority="high" if urgency == "urgent" else "medium",
    )
    return (
        f"I've escalated your case to our senior support team.\n"
        f"Escalation Ticket: #{ticket['id']}\n"
        f"Urgency: {urgency.upper()}\n"
        f"A human agent will contact you at {email} within "
        f"{'1 hour' if urgency == 'urgent' else '4 hours'}."
    )
