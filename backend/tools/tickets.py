from langchain_core.tools import tool
from database import create_ticket, get_ticket, list_tickets
import re

_VALID_CATEGORIES = {"billing", "technical", "account", "feature_request", "other"}
_VALID_PRIORITIES = {"low", "medium", "high", "critical"}
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(email: str) -> str:
    if not _EMAIL_RE.match(email):
        raise ValueError(f"Invalid email address: {email}")
    return email


def _validate_category(category: str) -> str:
    if category not in _VALID_CATEGORIES:
        raise ValueError(f"Invalid category '{category}'. Must be one of: {', '.join(sorted(_VALID_CATEGORIES))}")
    return category


def _validate_priority(priority: str) -> str:
    if priority not in _VALID_PRIORITIES:
        raise ValueError(f"Invalid priority '{priority}'. Must be one of: {', '.join(sorted(_VALID_PRIORITIES))}")
    return priority


@tool
def create_support_ticket(
    email: str,
    category: str,
    subject: str,
    description: str,
    priority: str = "medium",
) -> str:
    """Create a support ticket for a customer issue that cannot be resolved immediately.
    Use when the knowledge base doesn't have an answer or the issue needs human attention.

    category: one of 'billing', 'technical', 'account', 'feature_request', 'other'
    priority: one of 'low', 'medium', 'high', 'critical'
    """
    _validate_email(email)
    _validate_category(category)
    _validate_priority(priority)

    ticket = create_ticket(
        email=email,
        category=category,
        subject=subject,
        description=description,
        priority=priority,
    )
    return (
        f"Ticket created successfully!\n"
        f"Ticket ID: {ticket['id']}\n"
        f"Category: {ticket['category']}\n"
        f"Priority: {ticket['priority']}\n"
        f"Status: {ticket['status']}\n"
        f"Our team will respond within 24 hours. Reference your ticket ID: {ticket['id']}"
    )


@tool
def get_ticket_status(ticket_id: str) -> str:
    """Look up the status of an existing support ticket by its ticket ID."""
    ticket = get_ticket(ticket_id)
    if not ticket:
        return f"No ticket found with ID '{ticket_id}'. Please check the ID and try again."
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
    tickets = list_tickets(email=email)
    if not tickets:
        return f"No tickets found for {email}."
    lines = [f"Found {len(tickets)} ticket(s) for {email}:\n"]
    for t in tickets:
        lines.append(
            f"  • #{t['id']} [{t['status'].upper()}] {t['subject']} ({t['category']})"
        )
    return "\n".join(lines)
