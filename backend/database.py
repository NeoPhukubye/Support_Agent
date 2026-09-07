import uuid
from datetime import datetime, timezone

import boto3

from config import settings
from logging_config import logger

# ---------------------------------------------------------------------------
# DynamoDB client
# ---------------------------------------------------------------------------
_endpoint = settings.dynamodb_endpoint
_region   = settings.aws_region
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
    existing = [t["TableName"] for t in client.list_tables()["TableNames"]]
    if TABLE_NAME in existing:
        return
    client.create_table(
        TableName=TABLE_NAME,
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    _dynamodb.meta.client.get_waiter("table_exists").wait(TableName=TABLE_NAME)
    print(f"[DB] Created DynamoDB table '{TABLE_NAME}'")


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
        "id":          ticket_id,
        "email":       email,
        "category":    category,
        "subject":     subject,
        "description": description,
        "priority":    priority,
        "status":      "open",
        "resolution":  None,
        "created_at":  now,
        "updated_at":  now,
    }
    try:
        _get_table().put_item(Item=item)
        logger.info("Created ticket %s", ticket_id)
    except Exception:
        logger.exception("Failed to create ticket")
        raise
    return item


def get_ticket(ticket_id: str) -> dict | None:
    try:
        response = _get_table().get_item(Key={"id": ticket_id.upper()})
        return response.get("Item")
    except Exception:
        logger.exception("Failed to get ticket %s", ticket_id)
        raise


def list_tickets(email: str | None = None, limit: int = 10, next_token: str | None = None) -> dict:
    table = _get_table()
    scan_kwargs: dict = {}
    if email:
        scan_kwargs["FilterExpression"] = (
            boto3.dynamodb.conditions.Attr("email").eq(email)
        )
    if next_token:
        scan_kwargs["ExclusiveStartKey"] = {"id": {"S": next_token}}
    try:
        response = table.scan(**scan_kwargs)
    except Exception:
        logger.exception("Failed to list tickets")
        raise
    items = response.get("Items", [])
    items.sort(key=lambda t: t.get("created_at", ""), reverse=True)
    return {
        "items": items[:limit],
        "next_token": response.get("LastEvaluatedKey", {}).get("id"),
        "count": len(items),
    }
