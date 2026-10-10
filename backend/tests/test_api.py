import os
import sys
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "SupportAI Agent"


def test_health():
    with patch("database._get_table") as mock_table, patch.dict(
        "sys.modules", {"chromadb": MagicMock(), "langchain_aws": MagicMock()}
    ):
        mock_table.return_value.table_status = "ACTIVE"
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


def test_chat_validation():
    r = client.post("/chat", json={"message": ""})
    assert r.status_code == 422


def test_chat_message_too_long():
    r = client.post("/chat", json={"message": "x" * 2001})
    assert r.status_code == 422


def test_chat_history_trimmed():
    """History beyond max_history_turns should be trimmed."""
    long_history = [{"role": "user", "content": f"msg-{i}"} for i in range(30)]
    with patch("agent.run_agent") as mock_run:
        mock_run.return_value = {"response": "ok", "tools_used": []}
        r = client.post("/chat", json={"message": "hi", "history": long_history})
        assert r.status_code == 200
        # The agent should receive at most max_history_turns (20) turns
        _, kwargs = mock_run.call_args
        assert len(kwargs.get("history", [])) <= 20


def test_chat_rate_limit_exceeded():
    """Repeated requests from the same client should be rate limited."""
    for _ in range(61):
        r = client.post("/chat", json={"message": "test"})
        if r.status_code == 429:
            return
    assert False, "Rate limit was not triggered after 61 requests"


def test_get_ticket_not_found():
    r = client.get("/tickets/DOESNOTEXIST")
    assert r.status_code == 404


def test_list_tickets_endpoint():
    with patch("main.list_tickets") as mock_list:
        mock_list.return_value = {"items": [], "next_token": None, "count": 0}
        r = client.get("/tickets")
        assert r.status_code == 200
        assert r.json()["items"] == []