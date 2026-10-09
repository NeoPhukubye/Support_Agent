from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # AWS
    aws_access_key_id: str = Field(default="local", description="AWS access key ID")
    aws_secret_access_key: str = Field(default="local", description="AWS secret access key")
    aws_region: str = Field(default="us-east-1", description="AWS region")

    @field_validator("aws_region")
    @classmethod
    def validate_region(cls, v: str) -> str:
        valid_regions = {
            "us-east-1", "us-east-2", "us-west-1", "us-west-2",
            "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1",
            "ap-northeast-1", "ap-northeast-2", "ap-southeast-1", "ap-southeast-2",
            "ca-central-1", "sa-east-1"
        }
        if v not in valid_regions:
            raise ValueError(f"Invalid AWS region: {v}. Must be one of: {', '.join(sorted(valid_regions))}")
        return v

    # Bedrock
    model_name: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0",
        description="Bedrock model ID"
    )
    bedrock_max_tokens: int = Field(default=1024, ge=1, le=4096)
    bedrock_temperature: float = Field(default=0.2, ge=0.0, le=1.0)

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        valid_models = {
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "anthropic.claude-3-5-sonnet-20240620-v1:0",
            "anthropic.claude-3-haiku-20240307-v1:0",
            "anthropic.claude-3-opus-20240229-v1:0",
            "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "us.anthropic.claude-3-5-sonnet-20240620-v1:0",
            "us.anthropic.claude-3-haiku-20240307-v1:0",
            "us.anthropic.claude-3-opus-20240229-v1:0",
        }
        if v not in valid_models:
            raise ValueError(
                f"Invalid model name: {v}. Must be one of: {', '.join(sorted(valid_models))}"
            )
        return v

    # DynamoDB
    dynamodb_endpoint: str | None = Field(default=None, description="DynamoDB endpoint URL (for local dev)")
    dynamodb_table: str = Field(default="support_tickets", description="DynamoDB table name")

    # Frontend / CORS
    frontend_origin: str = Field(default="http://localhost:5173", description="Frontend origin for CORS")

    @field_validator("frontend_origin")
    @classmethod
    def validate_frontend_origin(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("frontend_origin must start with http:// or https://")
        return v

    # App limits
    max_message_length: int = Field(default=2000, ge=100, le=10000)
    max_history_turns: int = Field(default=20, ge=1, le=50)

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of: {', '.join(sorted(valid_levels))}")
        return upper

    # Rate limiting
    rate_limit_requests: int = Field(default=60, ge=1, le=1000, description="Requests per minute")
    rate_limit_window: int = Field(default=60, ge=1, le=3600, description="Rate limit window in seconds")

    # Knowledge base
    kb_search_results: int = Field(default=3, ge=1, le=10, description="Number of KB search results")
    kb_chunk_size: int = Field(default=500, ge=100, le=2000, description="KB document chunk size")
    kb_chunk_overlap: int = Field(default=50, ge=0, le=500, description="KB chunk overlap")


settings = Settings()