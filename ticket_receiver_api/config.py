"""Application configuration for TicketReceiverAPI."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings."""

    host: str = Field(default="0.0.0.0", description="Server bind host.")
    port: int = Field(default=8000, ge=1, le=65535, description="Server bind port.")
    log_level: str = Field(default="INFO", description="Python logging level.")
    log_file: Path = Field(default=Path("ticket_receiver_api.log"), description="Log file path.")
    cors_origins: str = Field(default="*", description="Comma-separated allowed CORS origins.")
    reload: bool = Field(default=False, description="Enable Uvicorn reload for local development.")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TICKET_RECEIVER_",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Normalize and validate the configured log level."""

        normalized = value.upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
        if normalized not in allowed:
            raise ValueError(f"log_level must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @property
    def cors_origin_list(self) -> list[str]:
        """Return configured CORS origins as a list."""

        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def cors_allow_credentials(self) -> bool:
        """Return whether credentialed CORS requests are safe for the origin policy."""

        return "*" not in self.cors_origin_list


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
