"""
Configuration settings for IB API FastAPI wrapper.

All settings are loaded from environment variables.
Use Coolify UI or .env file to configure.
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ==========================================================================
    # IB Gateway Connection
    # ==========================================================================

    # Docker service name for IB Gateway (internal network)
    ib_gateway_host: str = "ib-gateway"

    # Trading mode determines which port to use
    # paper = 4004 (internal), live = 4003 (internal)
    trading_mode: Literal["paper", "live"] = "paper"

    # Client ID for IB Gateway connection (must be unique per connection)
    ib_client_id: int = 1

    # Connection timeout in seconds
    ib_connection_timeout: int = 10

    # ==========================================================================
    # JWT Authentication
    # ==========================================================================

    # Secret key for signing JWT tokens (REQUIRED - must be set in environment)
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
    jwt_secret: SecretStr

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret_length(cls, v: SecretStr) -> SecretStr:
        """Ensure JWT secret is at least 32 characters for security."""
        if len(v.get_secret_value()) < 32:
            raise ValueError(
                "JWT_SECRET must be at least 32 characters. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return v

    # JWT algorithm
    jwt_algorithm: str = "HS256"

    # Token expiration time in minutes
    jwt_expire_minutes: int = 30

    # ==========================================================================
    # API Credentials
    # ==========================================================================

    # Username for API authentication (REQUIRED)
    api_username: str

    # Password for API authentication (REQUIRED)
    api_password: SecretStr

    # ==========================================================================
    # Pydantic Settings Configuration
    # ==========================================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ==========================================================================
    # Computed Properties
    # ==========================================================================

    @property
    def ib_gateway_port(self) -> int:
        """
        Get the IB Gateway port based on trading mode.

        Note: These are the INTERNAL container ports, not the external mapped ports.
        - Paper trading: 4004 (internal)
        - Live trading: 4003 (internal)
        """
        return 4004 if self.trading_mode == "paper" else 4003


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance (singleton pattern).

    Settings are loaded once and cached for the lifetime of the process.
    """
    return Settings()
