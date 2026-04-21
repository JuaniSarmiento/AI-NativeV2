from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_env: str = "development"
    debug: bool = Field(default=False, alias="APP_DEBUG")
    secret_key: str = Field(..., alias="SECRET_KEY")

    # --- Database ---
    database_url: str = Field(..., alias="DATABASE_URL")

    # --- Redis ---
    redis_url: str = Field(default="redis://localhost:6380/0", alias="REDIS_URL")

    # --- Anthropic ---
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(
        default="claude-sonnet-4-20250514", alias="ANTHROPIC_MODEL"
    )
    anthropic_max_tokens: int = Field(default=1024, alias="ANTHROPIC_MAX_TOKENS")
    anthropic_timeout_seconds: int = Field(default=30, alias="ANTHROPIC_TIMEOUT_SECONDS")

    # --- Mistral ---
    mistral_api_key: str = Field(default="", alias="MISTRAL_API_KEY")
    mistral_model: str = Field(default="mistral-small-latest", alias="MISTRAL_MODEL")
    mistral_max_tokens: int = Field(default=1024, alias="MISTRAL_MAX_TOKENS")

    # --- Tutor ---
    tutor_llm_provider: str = Field(default="mistral", alias="TUTOR_LLM_PROVIDER")
    tutor_rate_limit_per_hour: int = Field(default=30, alias="TUTOR_RATE_LIMIT_PER_HOUR")
    tutor_llm_fallback: bool = Field(default=False, alias="TUTOR_LLM_FALLBACK")

    # --- Research / Pseudonymization ---
    pseudonymization_salt: str = Field(
        default="ai-native-default-salt", alias="PSEUDONYMIZATION_SALT"
    )

    # --- CORS ---
    cors_origins: list[str] = Field(
        default=["http://localhost:5174"], alias="CORS_ORIGINS"
    )

    # --- JWT ---
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=15, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )

    # --- Sandbox ---
    sandbox_timeout_seconds: int = Field(default=10, alias="SANDBOX_TIMEOUT_SECONDS")
    sandbox_memory_limit_mb: int = Field(
        default=128, alias="SANDBOX_MEMORY_LIMIT_MB"
    )
    sandbox_network_access: bool = Field(
        default=False, alias="SANDBOX_NETWORK_ACCESS"
    )

    # --- Logging ---
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    sql_echo: bool = Field(default=False, alias="SQL_ECHO")

    # --- Server ---
    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8001, alias="BACKEND_PORT")
    backend_workers: int = Field(default=1, alias="BACKEND_WORKERS")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(
        cls, v: str | list[str]
    ) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
