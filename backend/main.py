from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import uvicorn
import sys
import os
import signal

sys.path.insert(0, os.path.dirname(__file__))

from config import settings
from logging_config import logger
from agent import run_agent, stream_agent
from database import get_ticket, list_tickets, _ensure_table_exists

app = FastAPI(title="SupportAI Agent API", version="1.0.0")


@app.on_event("startup")
def on_startup():
    logger.info("Starting SupportAI Agent API v%s", "1.0.0")
    _ensure_table_exists()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Constants ──────────────────────────────────────────────────────────────────

MAX_MESSAGE_LENGTH = settings.max_message_length   # characters
MAX_HISTORY_TURNS  = settings.max_history_turns    # message pairs kept


# ── Schemas ────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    history: Optional[list[ChatMessage]] = []

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message must not be blank.")
        return v.strip()

    @field_validator("history")
    @classmethod
    def trim_history(cls, v):
        # Keep only the most recent turns to avoid context overflow
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
        _get_table().table_status
        checks["dependencies"]["dynamodb"] = "ok"
    except Exception as exc:
        logger.exception("Health check DynamoDB failed")
        checks["dependencies"]["dynamodb"] = f"error: {exc}"
        checks["status"] = "degraded"

    try:
        import importlib
        importlib.import_module("chromadb")
        checks["dependencies"]["chromadb"] = "ok"
    except Exception as exc:
        checks["dependencies"]["chromadb"] = f"error: {exc}"
        checks["status"] = "degraded"

    try:
        import importlib
        importlib.import_module("langchain_aws")
        checks["dependencies"]["bedrock"] = "ok"
    except Exception as exc:
        checks["dependencies"]["bedrock"] = f"error: {exc}"
        checks["status"] = "degraded"

    return checks


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Standard (non-streaming) chat endpoint."""
    try:
        logger.info("POST /chat message=%s", req.message[:50])
        history = [{"role": m.role, "content": m.content} for m in req.history]
        result = run_agent(req.message, history)
        return ChatResponse(
            response=result["response"],
            tools_used=result["tools_used"],
        )
    except Exception as e:
        logger.exception("POST /chat failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).

    Each event is a JSON object on a `data:` line:
      {"type": "tool",  "name": "<tool_name>"}
      {"type": "token", "content": "<text_chunk>"}
      {"type": "done",  "tools_used": ["..."]}
      {"type": "error", "detail": "<message>"}
    """
    logger.info("POST /chat/stream message=%s", req.message[:50])
    history = [{"role": m.role, "content": m.content} for m in req.history]
    return StreamingResponse(
        stream_agent(req.message, history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering if behind a proxy
        },
    )


@app.get("/tickets")
def get_all_tickets():
    logger.info("GET /tickets")
    return list_tickets()


@app.get("/tickets/{ticket_id}")
def get_ticket_by_id(ticket_id: str):
    logger.info("GET /tickets/%s", ticket_id)
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
