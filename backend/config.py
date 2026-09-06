from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # AWS
    aws_access_key_id: str = "local"
    aws_secret_access_key: str = "local"
    aws_region: str = "us-east-1"

    # Bedrock
    model_name: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # DynamoDB
    dynamodb_endpoint: str | None = None
    dynamodb_table: str = "support_tickets"

    # Frontend / CORS
    frontend_origin: str = "http://localhost:5173"

    # App limits
    max_message_length: int = 2000
    max_history_turns: int = 20


settings = Settings()