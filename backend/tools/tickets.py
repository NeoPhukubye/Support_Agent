import re

from langchain_core.tools import tool

from config import settings
from database import create_ticket, get_ticket, list_tickets
from logging_config import log_agent_action

_VALID_CATEGORIES = {"billing", "technical", "account", "feature_request", "other", "escalation"}
_VALID_PRIORITIES = {"low", "medium", "high", "critical"}
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SUBJECT_MAX_LEN = 200
_DESCRIPTION_MAX_LEN = 5000


def _validate_email(email: str) -> str:
    if not _EMAIL_RE.match(email):
        raise ValueError(f"Invalid email address: {email}")
    return email.lower().strip()


def _validate_category(category: str) -> str:
    if category not in _VALID_CATEGORIES:
        raise ValueError(
            f"Invalid category '{category}'. Must be one of: "
            f"{', '.join(sorted(_VALID_CATEGORIES))}"
        )
    return category


def _validate_priority(priority: str) -> str:
    if priority not in _VALID_PRIORITIES:
        raise ValueError(
            f"Invalid priority '{priority}'. Must be one of: "
            f"{', '.join(sorted(_VALID_PRIORITIES))}"
        )
    return priority


def _validate_subject(subject: str) -> str:
    subject = subject.strip()
    if not subject:
        raise ValueError("Subject cannot be empty")
    if len(subject) > _SUBJECT_MAX_LEN:
        raise ValueError(f"Subject too long (max {_SUBJECT_MAX_LEN} characters)")
    return subject


def _validate_description(description: str) -> str:
    description = description.strip()
    if not description:
        raise ValueError("Description cannot be empty")
    if len(description) > _DESCRIPTION_MAX_LEN:
        raise ValueError(f"Description too long (max {_DESCRIPTION_MAX_LEN} characters)")
    return description


@tool
def create_support_ticket(
    email: str,
    category: str,
    subject: str,
    description: str,
    priority: str = "medium",
) -> str:
    """Create a support ticket for a customer issue that cannot be resolved
    immediately. Use when the knowledge base doesn't have an answer or the
    issue needs human attention.

    category: one of 'billing', 'technical', 'account', 'feature_request', 'other'
    priority: one of 'low', 'medium', 'high', 'critical'
    """
    email = _validate_email(email)
    category = _validate_category(category)
    priority = _validate_priority(priority)
    subject = _validate_subject(subject)
    description = _validate_description(description)

    ticket = create_ticket(
        email=email,
        category=category,
        subject=subject,
        description=description,
        priority=priority,
    )
    log_agent_action("ticket_created_via_tool", ticket_id=ticket["id"], category=category, priority=priority)
    return (
        f"Ticket created successfully!\n"
        f"Ticket ID: {ticket['id']}\n"
        f"Category: {ticket['category']}\n"
        f"Priority: {ticket['priority']}\n"
        f"Status: {ticket['status']}\n"
        f"Our team will respond within 24 hours. "
        f"Reference your ticket ID: {ticket['id']}"
    )


@tool
def get_ticket_status(ticket_id: str) -> str:
    """Look up the status of an existing support ticket by its ticket ID."""
    ticket_id = ticket_id.strip().upper()
    if not ticket_id:
        return "Please provide a valid ticket ID."

    ticket = get_ticket(ticket_id)
    if not ticket:
        return (
            f"No ticket found with ID '{ticket_id}'. "
            f"Please check the ID and try again."
        )
    log_agent_action("ticket_status_checked", ticket_id=ticket_id)
    return (
        f"Ticket #{ticket['id']}\n"
        f"Subject: {ticket['subject']}\n"
        f"Category: {ticket['category']}\n"
        f"Priority: {ticket['priority']}\n"
        f"Status: {ticket['status']}\n"
        f"Created: {ticket['created_at']}\n"
        f"Resolution: {ticket['resolution'] or 'Pending — our team is working on it.'}"
    )


@tool
def list_my_tickets(email: str) -> str:
    """List all support tickets for a given customer email address."""
    email = _validate_email(email)
    tickets = list_tickets(email=email)
    items = tickets.get("items", [])
    if not items:
        return f"No tickets found for {email}."
    log_agent_action("tickets_listed", email=email, count=len(items))
    lines = [f"Found {len(items)} ticket(s) for {email}:\n"]
    for t in items:
        lines.append(
            f"  • #{t['id']} [{t['status'].upper()}] {t['subject']} ({t['category']})"
        )
    return "\n".join(lines)