import boto3
import os
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# DynamoDB client — points to DynamoDB Local when DYNAMODB_ENDPOINT is set,
# otherwise uses the real AWS endpoint (picked up via boto3 credential chain).
# ---------------------------------------------------------------------------
_endpoint = os.getenv("DYNAMODB_ENDPOINT")
_region   = os.getenv("AWS_REGION", "us-east-1")
TABLE_NAME = os.getenv("DYNAMODB_TABLE", "support_tickets")

_dynamodb = boto3.resource(
    "dynamodb",
    region_name=_region,
    endpoint_url=_endpoint,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "local"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "local"),
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
    _get_table().put_item(Item=item)
    return item


def get_ticket(ticket_id: str) -> dict | None:
    response = _get_table().get_item(Key={"id": ticket_id.upper()})
    return response.get("Item")


def list_tickets(email: str = None, limit: int = 10, next_token: str = None) -> dict:
    table = _get_table()
    scan_kwargs: dict = {}
    if email:
        scan_kwargs["FilterExpression"] = boto3.dynamodb.conditions.Attr("email").eq(email)
    if next_token:
        scan_kwargs["ExclusiveStartKey"] = {"id": {"S": next_token}}
    response = table.scan(**scan_kwargs)
    items = response.get("Items", [])
    items.sort(key=lambda t: t.get("created_at", ""), reverse=True)
    return {
        "items": items[:limit],
        "next_token": response.get("LastEvaluatedKey", {}).get("id"),
        "count": len(items),
    }
