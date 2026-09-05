import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "SupportAI Agent"


def test_health():
    with patch("main._get_table") as mock_table, \
         patch.dict("sys.modules", {"chromadb": MagicMock(), "langchain_aws": MagicMock()}):
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