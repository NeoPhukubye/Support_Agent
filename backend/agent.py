import json

from config import settings
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from logging_config import logger
from tools import (
    create_support_ticket,
    escalate_to_human,
    get_ticket_status,
    list_my_tickets,
    search_kb,
)

# ── LLM ─────────────────────────────────────────────────────────────[...]

llm = ChatBedrockConverse(
    model=settings.model_name,
    region_name=settings.aws_region,
    temperature=0.2,
    max_tokens=1024,
)

# ── System prompt ───────────────────────────────────────────────────────────[...]

SYSTEM_PROMPT = (
    "You are Alex, an AI customer support agent for SupportAI.\n"
    "\n"
    "Your goal is to resolve customer issues quickly, accurately, and empathetically.\n"
    "\n"
    "## Your Capabilities:\n"
    "1. **search_kb** — Search the knowledge base for answers to common questions\n"
    "2. **create_support_ticket** — Create a ticket when an issue needs follow-up\n"
    "3. **get_ticket_status** — Check the status of an existing ticket\n"
    "4. **list_my_tickets** — Show all tickets for a customer\n"
    "5. **escalate_to_human** — Escalate complex/urgent issues to a human agent\n"
    "\n"
    "## Behavior Guidelines:\n"
    " - Always greet the customer warmly and professionally\n"
    " - Search the knowledge base FIRST before asking for more info\n"
    " - If KB has a clear answer, provide it directly — do NOT create a ticket\n"
    " - Create a ticket when: the issue needs investigation,\n"
    "   the KB has no answer, or the customer explicitly requests it\n"
    " - Escalate when: the customer is very frustrated, the issue is security/legal,\n"
    "   or you cannot resolve it\n"
    " - Ask for the customer's email before creating tickets or escalating\n"
    " - Be concise but thorough — bullet points work well for\n"
    "   step-by-step instructions\n"
    " - Format your responses using Markdown: use **bold** for emphasis,\n"
    "   bullet lists for steps, and `code` for error codes\n"
    " - Always end with \"Is there anything else I can help you with?\"\n"
    "\n"
    "## Tone: Professional, warm, solution-focused. Never robotic."
)

# ── Agent ─────────────────────────────────────────────────────────────[...]

tools = [
    search_kb,
    create_support_ticket,
    get_ticket_status,
    list_my_tickets,
    escalate_to_human,
]
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
    logger.info("run_agent message=%s history_len=%d", message[:50], len(history))
    messages = _build_messages(message, history)
    result = agent.invoke({"messages": messages})
    all_messages = result["messages"]

    tool_calls_used = []
    for msg in all_messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_used.append(tc.get("name", ""))
        elif hasattr(msg, "name") and msg.name:
            tool_calls_used.append(msg.name)

    logger.info("run_agent tools_used=%s", tool_calls_used)
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
      - data: {"type": "done", "tools_used": [...]}  — final event with full tool list
      - data: {"type": "error", "detail": "<msg>"}       — error event
    """
    messages = _build_messages(message, history)
    tool_calls_used: list[str] = []

    try:
        for event in agent.stream({"messages": messages}, stream_mode="messages"):
            msg_chunk, _ = event

            if hasattr(msg_chunk, "tool_calls") and msg_chunk.tool_calls:
                for tc in msg_chunk.tool_calls:
                    name = tc.get("name", "")
                    if name:
                        tool_calls_used.append(name)
                        logger.info("stream_agent tool=%s", name)
                        yield f"data: {json.dumps({'type': 'tool', 'name': name})}\n\n"

            if (
                hasattr(msg_chunk, "name")
                and msg_chunk.name
                and not getattr(msg_chunk, "tool_calls", None)
                and msg_chunk.name not in tool_calls_used
            ):
                tool_calls_used.append(msg_chunk.name)

            if (
                hasattr(msg_chunk, "content")
                and isinstance(msg_chunk.content, str)
                and msg_chunk.content
                and not getattr(msg_chunk, "name", None)
                and not getattr(msg_chunk, "tool_calls", None)
            ):
                payload = json.dumps(
                    {"type": "token", "content": msg_chunk.content}
                )
                yield f"data: {payload}\n\n"

        payload = json.dumps(
            {"type": "done", "tools_used": list(dict.fromkeys(tool_calls_used))}
        )
        yield f"data: {payload}\n\n"

    except Exception as exc:  # noqa: BLE001
        logger.exception("stream_agent failed")
        yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"
