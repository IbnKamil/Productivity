from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Tunnel Tasks"
    environment: Literal["local", "test", "staging", "production"] = "local"
    api_prefix: str = ""
    database_url: str = "postgresql+psycopg://tunnel:tunnel@postgres:5432/tunnel"
    redis_url: str | None = "redis://redis:6379/0"
    jwt_secret: str = Field(default="change-me-in-production", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 30
    sentry_dsn: str | None = None
    cors_origins: list[AnyHttpUrl | str] = ["http://localhost:3000"]
    rate_limit_enabled: bool = True
    task_decomposer_mode: Literal["auto", "ai", "local"] = "auto"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    web_research_enabled: bool = True
    research_provider: Literal["auto", "tavily", "public", "none"] = "auto"
    tavily_api_key: str | None = None
    research_max_results: int = Field(default=5, ge=1, le=10)
    min_micro_tasks: int = Field(default=10, ge=1, le=150)
    max_micro_tasks: int = Field(default=150, ge=10, le=150)


@lru_cache
def get_settings() -> Settings:
    return Settings()
