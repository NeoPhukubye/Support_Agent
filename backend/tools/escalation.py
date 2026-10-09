import re

from langchain_core.tools import tool

from config import settings
from database import create_ticket
from logging_config import log_agent_action

_VALID_URGENCY = {"normal", "urgent"}
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ISSUE_SUMMARY_MAX_LEN = 2000


def _validate_email(email: str) -> str:
    if not _EMAIL_RE.match(email):
        raise ValueError(f"Invalid email address: {email}")
    return email.lower().strip()


def _validate_urgency(urgency: str) -> str:
    if urgency not in _VALID_URGENCY:
        raise ValueError(f"Invalid urgency '{urgency}'. Must be one of: normal, urgent")
    return urgency


def _validate_issue_summary(issue_summary: str) -> str:
    issue_summary = issue_summary.strip()
    if not issue_summary:
        raise ValueError("Issue summary cannot be empty")
    if len(issue_summary) > _ISSUE_SUMMARY_MAX_LEN:
        raise ValueError(f"Issue summary too long (max {_ISSUE_SUMMARY_MAX_LEN} characters)")
    return issue_summary


@tool
def escalate_to_human(email: str, issue_summary: str, urgency: str = "normal") -> str:
    """Escalate a complex or sensitive issue to a human support agent.
    Use for: legal complaints, security incidents, account compromise,
    highly frustrated customers, or issues that require human judgment.

    urgency: 'normal' or 'urgent'
    """
    email = _validate_email(email)
    urgency = _validate_urgency(urgency)
    issue_summary = _validate_issue_summary(issue_summary)

    ticket = create_ticket(
        email=email,
        category="escalation",
        subject=f"[ESCALATED] {issue_summary[:80]}",
        description=issue_summary,
        priority="high" if urgency == "urgent" else "medium",
    )
    log_agent_action("escalation_created", ticket_id=ticket["id"], urgency=urgency)
    return (
        f"I've escalated your case to our senior support team.\n"
        f"Escalation Ticket: #{ticket['id']}\n"
        f"Urgency: {urgency.upper()}\n"
        f"A human agent will contact you at {email} within "
        f"{'1 hour' if urgency == 'urgent' else '4 hours'}."
    )