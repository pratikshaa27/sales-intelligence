from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_name: str = "sales-intelligence-platform"
    api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sales_intelligence"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    cors_allowed_origins: list[str] = ["http://localhost:3000"]

    ai_provider: Literal["mock", "openai_compatible"] = "mock"
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = "mock-model"
    embedding_model: str = "mock-embedding"

    # Company discovery has no real data-provider integration configured (spec §30: mock/local
    # implementation until one is licensed); "mock" is the only option today.
    discovery_provider: Literal["mock"] = "mock"

    website_fetch_timeout_seconds: float = 10.0
    website_fetch_max_bytes: int = 2_000_000
    website_fetch_max_redirects: int = 5

    upload_dir: str = "/app/uploads"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "no-reply@example.com"

    log_level: str = "INFO"
    sentry_dsn: str = ""

    rate_limit_auth_per_minute: int = 10

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
