import importlib
import os
import signal
import sys
import time
from collections import defaultdict
from functools import wraps

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

sys.path.insert(0, os.path.dirname(__file__))

from agent import run_agent, stream_agent
from config import settings
from database import _ensure_table_exists, get_ticket, list_tickets
from logging_config import logger, log_agent_action

app = FastAPI(title="SupportAI Agent API", version="1.0.0")


# ── Rate Limiting ────────────────────────────────────────────────────────────────

_request_counts: dict[str, list[float]] = defaultdict(list)


def rate_limit(func):
    """Simple in-memory rate limiter."""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - settings.rate_limit_window

        # Clean old entries
        _request_counts[client_ip] = [
            t for t in _request_counts[client_ip] if t > window_start
        ]

        if len(_request_counts[client_ip]) >= settings.rate_limit_requests:
            log_agent_action("rate_limit_exceeded", client_ip=client_ip)
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {settings.rate_limit_requests} requests per {settings.rate_limit_window}s."
            )

        _request_counts[client_ip].append(now)
        return await func(request, *args, **kwargs)
    return wrapper


@app.on_event("startup")
def on_startup():
    log_agent_action("api_startup", version="1.0.0")
    _ensure_table_exists()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Constants ──────────────────────────────────────────────────────────────────

MAX_MESSAGE_LENGTH = settings.max_message_length
MAX_HISTORY_TURNS = settings.max_history_turns


# ── Schemas ────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    history: list[ChatMessage] | None = []

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message must not be blank.")
        return v.strip()

    @field_validator("history")
    @classmethod
    def trim_history(cls, v):
        return v[-MAX_HISTORY_TURNS:] if v else []


class ChatResponse(BaseModel):
    response: str
    tools_used: list[str]


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "SupportAI Agent", "version": "1.0.0"}


@app.get("/health")
def health():
    checks = {
        "status": "healthy",
        "version": "1.0.0",
        "dependencies": {},
    }
    try:
        from database import _get_table
        _ = _get_table().table_status
        checks["dependencies"]["dynamodb"] = "ok"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Health check DynamoDB failed")
        checks["dependencies"]["dynamodb"] = f"error: {exc}"
        checks["status"] = "degraded"

    try:
        importlib.import_module("chromadb")
        checks["dependencies"]["chromadb"] = "ok"
    except ImportError as exc:
        checks["dependencies"]["chromadb"] = f"error: {exc}"
        checks["status"] = "degraded"

    try:
        importlib.import_module("langchain_aws")
        checks["dependencies"]["bedrock"] = "ok"
    except ImportError as exc:
        checks["dependencies"]["bedrock"] = f"error: {exc}"
        checks["status"] = "degraded"

    return checks


@app.post("/chat", response_model=ChatResponse)
@rate_limit
async def chat(request: Request, req: ChatRequest):
    """Standard (non-streaming) chat endpoint."""
    log_agent_action("chat_request", message_preview=req.message[:50])
    try:
        history = [{"role": m.role, "content": m.content} for m in req.history]
        result = run_agent(req.message, history)
        return ChatResponse(
            response=result["response"],
            tools_used=result["tools_used"],
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("POST /chat failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
@rate_limit
async def chat_stream(request: Request, req: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).

    Each event is a JSON object on a `data:` line:
      {"type": "tool",  "name": "<tool_name>"}
      {"type": "token", "content": "<text_chunk>"}
      {"type": "done",  "tools_used": ["..."]}
      {"type": "error", "detail": "<message>"}
    """
    log_agent_action("chat_stream_request", message_preview=req.message[:50])
    history = [{"role": m.role, "content": m.content} for m in req.history]
    return StreamingResponse(
        stream_agent(req.message, history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/tickets")
@rate_limit
async def get_all_tickets(request: Request):
    log_agent_action("list_tickets_request")
    return list_tickets()


@app.get("/tickets/{ticket_id}")
@rate_limit
async def get_ticket_by_id(request: Request, ticket_id: str):
    log_agent_action("get_ticket_request", ticket_id=ticket_id)
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


if __name__ == "__main__":
    def handle_sigterm(*_):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)
    uvicorn.run("main:app", host="0.0.0.0", port=8000)