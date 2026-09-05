import json
import os
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from config import settings
from tools import (
    search_kb,
    create_support_ticket,
    get_ticket_status,
    list_my_tickets,
    escalate_to_human,
)

# ── LLM ───────────────────────────────────────────────────────────────────────

llm = ChatBedrockConverse(
    model=settings.model_name,
    region_name=settings.aws_region,
    temperature=0.2,
    max_tokens=1024,
)

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
- Format your responses using Markdown: use **bold** for emphasis, bullet lists for steps, and `code` for error codes
- Always end with "Is there anything else I can help you with?"

## Tone: Professional, warm, solution-focused. Never robotic."""

# ── Agent ──────────────────────────────────────────────────────────────────────

tools = [search_kb, create_support_ticket, get_ticket_status, list_my_tickets, escalate_to_human]
agent = create_react_agent(llm, tools)


def _build_messages(message: str, history: list[dict]) -> list:
    """Convert history dicts into LangChain message objects."""
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for turn in history:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        elif turn["role"] == "assistant":
            messages.append(AIMessage(content=turn["content"]))
    messages.append(HumanMessage(content=message))
    return messages


def run_agent(message: str, history: list[dict]) -> dict:
    """Run the agent and return the full response + tools used."""
    messages = _build_messages(message, history)
    result = agent.invoke({"messages": messages})
    all_messages = result["messages"]

    # Deduplicated list of tool names used
    tool_calls_used = []
    for msg in all_messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_used.append(tc.get("name", ""))
        elif hasattr(msg, "name") and msg.name:
            tool_calls_used.append(msg.name)

    return {
        "response": all_messages[-1].content,
        "tools_used": list(dict.fromkeys(tool_calls_used)),
    }


def stream_agent(message: str, history: list[dict]):
    """
    Generator that yields Server-Sent Event strings.

    Event types:
      - data: {"type": "tool", "name": "<tool_name>"}   — tool call notification
      - data: {"type": "token", "content": "<chunk>"}   — streamed text token
      - data: {"type": "done", "tools_used": [...]}      — final event with full tool list
      - data: {"type": "error", "detail": "<msg>"}       — error event
    """
    messages = _build_messages(message, history)
    tool_calls_used: list[str] = []

    try:
        for event in agent.stream({"messages": messages}, stream_mode="messages"):
            # event is a tuple: (message_chunk, metadata)
            msg_chunk, _meta = event

            # Tool invocation notifications
            if hasattr(msg_chunk, "tool_calls") and msg_chunk.tool_calls:
                for tc in msg_chunk.tool_calls:
                    name = tc.get("name", "")
                    if name:
                        tool_calls_used.append(name)
                        yield f"data: {json.dumps({'type': 'tool', 'name': name})}\n\n"

            # ToolMessage (result of a tool call)
            if hasattr(msg_chunk, "name") and msg_chunk.name and not getattr(msg_chunk, "tool_calls", None):
                if msg_chunk.name not in tool_calls_used:
                    tool_calls_used.append(msg_chunk.name)

            # Streamed text tokens from the final AI response
            if hasattr(msg_chunk, "content") and isinstance(msg_chunk.content, str) and msg_chunk.content:
                # Only stream tokens from the final AI message (not tool result messages)
                if not getattr(msg_chunk, "name", None) and not getattr(msg_chunk, "tool_calls", None):
                    yield f"data: {json.dumps({'type': 'token', 'content': msg_chunk.content})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'tools_used': list(dict.fromkeys(tool_calls_used))})}\n\n"

    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"
