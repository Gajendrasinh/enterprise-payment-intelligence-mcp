"""Application configuration for custom-payment-mcp."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "custom-payment-mcp"
    app_version: str = "0.1.0"
    environment: str = "local"
    log_level: str = "INFO"

    # Default security identity for local execution
    default_user_id: str = "USR-OPERATOR-01"
    default_role: str = "ADMIN"

    # Transport settings (stdio or sse)
    mcp_transport: str = "stdio"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
