from langchain_core.tools import tool
from database import create_ticket


@tool
def escalate_to_human(email: str, issue_summary: str, urgency: str = "normal") -> str:
    """Escalate a complex or sensitive issue to a human support agent.
    Use for: legal complaints, security incidents, account compromise, highly frustrated customers,
    or issues that require human judgment.

    urgency: 'normal' or 'urgent'
    """
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
