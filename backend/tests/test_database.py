"""Tests for the database module using a mocked DynamoDB resource."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import database


@pytest.fixture
def mock_table():
    """Return a mock DynamoDB table and patch _get_table to use it."""
    table = MagicMock()
    with patch.object(database, "_get_table", return_value=table):
        yield table


def test_create_ticket_returns_item(mock_table):
    mock_table.put_item.return_value = {}
    item = database.create_ticket(
        email="user@example.com",
        category="billing",
        subject="Charge issue",
        description="I was charged twice",
        priority="high",
    )
    assert item["id"]
    assert item["email"] == "user@example.com"
    assert item["category"] == "billing"
    assert item["status"] == "open"
    assert item["priority"] == "high"
    mock_table.put_item.assert_called_once()


def test_get_ticket_found(mock_table):
    mock_table.get_item.return_value = {
        "Item": {"id": "ABC123", "subject": "Test", "status": "open"}
    }
    ticket = database.get_ticket("abc123")
    assert ticket["id"] == "ABC123"
    # ID should be uppercased
    mock_table.get_item.assert_called_once_with(Key={"id": "ABC123"})


def test_get_ticket_not_found(mock_table):
    mock_table.get_item.return_value = {}
    assert database.get_ticket("MISSING") is None


def test_list_tickets_pagination(mock_table):
    """Pagination token should be returned as a string, not a DynamoDB key dict."""
    mock_table.scan.return_value = {
        "Items": [{"id": "1", "subject": "A"}],
        "LastEvaluatedKey": {"id": {"S": "NEXT"}},
    }
    result = database.list_tickets(limit=10)
    assert result["items"] == [{"id": "1", "subject": "A"}]
    assert result["next_token"] == "NEXT"
    assert result["count"] == 1


def test_list_tickets_no_more_pages(mock_table):
    mock_table.scan.return_value = {
        "Items": [{"id": "1", "subject": "A"}],
        "LastEvaluatedKey": None,
    }
    result = database.list_tickets(limit=10)
    assert result["next_token"] is None
    assert result["count"] == 1


def test_list_tickets_with_email_filter(mock_table):
    mock_table.scan.return_value = {
        "Items": [{"id": "1", "subject": "A", "email": "user@example.com"}],
        "LastEvaluatedKey": None,
    }
    result = database.list_tickets(email="user@example.com")
    assert result["count"] == 1
    # Verify filter expression was set
    _, kwargs = mock_table.scan.call_args
    assert "FilterExpression" in kwargs