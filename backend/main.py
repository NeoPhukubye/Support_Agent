from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from agent import run_agent
from database import get_ticket, list_tickets

app = FastAPI(title="SupportAI Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Schemas ────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[list[ChatMessage]] = []

class ChatResponse(BaseModel):
    response: str
    tools_used: list[str]

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "SupportAI Agent", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        history = [{"role": m.role, "content": m.content} for m in req.history]
        result = run_agent(req.message, history)
        return ChatResponse(
            response=result["response"],
            tools_used=result["tools_used"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tickets")
def get_all_tickets():
    return list_tickets()

@app.get("/tickets/{ticket_id}")
def get_ticket_by_id(ticket_id: str):
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
