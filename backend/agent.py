import json
from langchain_aws import ChatBedrockConverse
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from database import create_ticket, get_ticket, list_tickets
from knowledge_base.vector_store import search_knowledge_base
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatBedrockConverse(
    model=os.getenv("MODEL_NAME", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    temperature=0.2,
    max_tokens=1024,
)

# ── Tools ──────────────────────────────────────────────────────────────────────

@tool
def search_kb(query: str) -> str:
    """Search the support knowledge base for answers to customer questions about
    billing, technical issues, account management, features, policies, and troubleshooting."""
    results = search_knowledge_base(query)
    if not results:
        return "No relevant information found in the knowledge base."
    return "\n\n---\n".join(f"[{r['source']}]\n{r['content']}" for r in results)


@tool
def create_support_ticket(email: str, category: str, subject: str, description: str, priority: str = "medium") -> str:
    """Create a support ticket for a customer issue that cannot be resolved immediately.
    Use when the knowledge base doesn't have an answer or the issue needs human attention.
    
    category: one of 'billing', 'technical', 'account', 'feature_request', 'other'
    priority: one of 'low', 'medium', 'high', 'critical'
    """
    ticket = create_ticket(email=email, category=category, subject=subject,
                           description=description, priority=priority)
    return (f"Ticket created successfully!\n"
            f"Ticket ID: {ticket['id']}\n"
            f"Category: {ticket['category']}\n"
            f"Priority: {ticket['priority']}\n"
            f"Status: {ticket['status']}\n"
            f"Our team will respond within 24 hours. Reference your ticket ID: {ticket['id']}")


@tool
def get_ticket_status(ticket_id: str) -> str:
    """Look up the status of an existing support ticket by its ticket ID."""
    ticket = get_ticket(ticket_id)
    if not ticket:
        return f"No ticket found with ID '{ticket_id}'. Please check the ID and try again."
    return (f"Ticket #{ticket['id']}\n"
            f"Subject: {ticket['subject']}\n"
            f"Category: {ticket['category']}\n"
            f"Priority: {ticket['priority']}\n"
            f"Status: {ticket['status']}\n"
            f"Created: {ticket['created_at']}\n"
            f"Resolution: {ticket['resolution'] or 'Pending — our team is working on it.'}")


@tool
def list_my_tickets(email: str) -> str:
    """List all support tickets for a given customer email address."""
    tickets = list_tickets(email=email)
    if not tickets:
        return f"No tickets found for {email}."
    lines = [f"Found {len(tickets)} ticket(s) for {email}:\n"]
    for t in tickets:
        lines.append(f"  • #{t['id']} [{t['status'].upper()}] {t['subject']} ({t['category']})")
    return "\n".join(lines)


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
    return (f"I've escalated your case to our senior support team.\n"
            f"Escalation Ticket: #{ticket['id']}\n"
            f"Urgency: {urgency.upper()}\n"
            f"A human agent will contact you at {email} within "
            f"{'1 hour' if urgency == 'urgent' else '4 hours'}.")


# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Alex, an intelligent AI customer support agent for SupportAI — a SaaS platform.

Your goal is to resolve customer issues quickly, accurately, and empathetically.

## Your Capabilities:
1. **search_kb** — Search the knowledge base for answers to common questions
2. **create_support_ticket** — Create a ticket when an issue needs follow-up
3. **get_ticket_status** — Check the status of an existing ticket
4. **list_my_tickets** — Show all tickets for a customer
5. **escalate_to_human** — Escalate complex/urgent issues to a human agent

## Behavior Guidelines:
- Always greet the customer warmly and professionally
- Search the knowledge base FIRST before asking for more info
- If KB has a clear answer, provide it directly — do NOT create a ticket
- Create a ticket only when: the issue needs investigation, the KB has no answer, or the customer explicitly requests it
- Escalate when: the customer is very frustrated, the issue is security/legal, or you cannot resolve it
- Ask for the customer's email before creating tickets or escalating
- Be concise but thorough — bullet points work well for step-by-step instructions
- Always end with "Is there anything else I can help you with?"

## Tone: Professional, warm, solution-focused. Never robotic."""

# ── Agent ──────────────────────────────────────────────────────────────────────

tools = [search_kb, create_support_ticket, get_ticket_status, list_my_tickets, escalate_to_human]
agent = create_react_agent(llm, tools)


def run_agent(message: str, history: list[dict]) -> dict:
    """Run the agent with message history and return response + tool calls used."""
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    for turn in history:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        elif turn["role"] == "assistant":
            from langchain_core.messages import AIMessage
            messages.append(AIMessage(content=turn["content"]))

    messages.append(HumanMessage(content=message))

    result = agent.invoke({"messages": messages})
    all_messages = result["messages"]

    # Extract tool calls from intermediate steps
    tool_calls_used = []
    for msg in all_messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_used.append(tc.get("name", ""))
        elif hasattr(msg, "name") and msg.name:  # ToolMessage
            tool_calls_used.append(msg.name)

    final_response = all_messages[-1].content
    return {
        "response": final_response,
        "tools_used": list(dict.fromkeys(tool_calls_used)),  # deduplicated
    }
