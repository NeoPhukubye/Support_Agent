import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from config import settings
from logging_config import logger, log_agent_action

# ---------------------------------------------------------------------------
# DynamoDB client
# ---------------------------------------------------------------------------
_endpoint = settings.dynamodb_endpoint
_region = settings.aws_region
TABLE_NAME = settings.dynamodb_table

_dynamodb = boto3.resource(
    "dynamodb",
    region_name=_region,
    endpoint_url=_endpoint,
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
)


def _get_table():
    return _dynamodb.Table(TABLE_NAME)


def _ensure_table_exists():
    """Create the table if it doesn't already exist (idempotent)."""
    client = _dynamodb.meta.client
    existing = client.list_tables().get("TableNames", [])
    if TABLE_NAME in existing:
        return
    client.create_table(
        TableName=TABLE_NAME,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    _dynamodb.meta.client.get_waiter("table_exists").wait(TableName=TABLE_NAME)
    log_agent_action("dynamodb_table_created", table_name=TABLE_NAME)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_ticket(
    email: str,
    category: str,
    subject: str,
    description: str,
    priority: str = "medium",
) -> dict:
    ticket_id = str(uuid.uuid4())[:8].upper()
    now = datetime.now(timezone.utc).isoformat()
    item = {
        "id": ticket_id,
        "email": email,
        "category": category,
        "subject": subject,
        "description": description,
        "priority": priority,
        "status": "open",
        "resolution": None,
        "created_at": now,
        "updated_at": now,
    }
    try:
        _get_table().put_item(Item=item)
        log_agent_action("ticket_created", ticket_id=ticket_id, category=category, priority=priority)
    except ClientError as exc:
        logger.exception("Failed to create ticket: %s", exc.response.get("Error", {}).get("Message"))
        raise
    return item


def get_ticket(ticket_id: str) -> dict | None:
    try:
        response = _get_table().get_item(Key={"id": ticket_id.upper()})
        return response.get("Item")
    except ClientError as exc:
        logger.exception("Failed to get ticket %s: %s", ticket_id, exc.response.get("Error", {}).get("Message"))
        raise


def list_tickets(email: str | None = None, limit: int = 10, next_token: str | None = None) -> dict:
    """List tickets, optionally filtered by email, with pagination support.

    Args:
        email: If provided, only tickets matching this email are returned.
        limit: Maximum number of items to return.
        next_token: Opaque pagination token from a previous response.

    Returns:
        Dict with keys: items, next_token, count.
    """
    table = _get_table()
    scan_kwargs: dict = {"Limit": limit}
    if email:
        scan_kwargs["FilterExpression"] = (
            boto3.dynamodb.conditions.Attr("email").eq(email)
        )
    if next_token:
        scan_kwargs["ExclusiveStartKey"] = {"id": {"S": next_token}}
    try:
        response = table.scan(**scan_kwargs)
    except ClientError as exc:
        logger.exception("Failed to list tickets: %s", exc.response.get("Error", {}).get("Message"))
        raise
    items = response.get("Items", [])
    items.sort(key=lambda t: t.get("created_at", ""), reverse=True)
    last_key = response.get("LastEvaluatedKey")
    # Return only the id portion of the DynamoDB key as a string token
    next_token_value = None
    if last_key and "id" in last_key:
        next_token_value = last_key["id"].get("S")
    return {
        "items": items,
        "next_token": next_token_value,
        "count": len(items),
    }