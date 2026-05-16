import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

logger = logging.getLogger(__name__)

_INSECURE_DEFAULT_KEY = "change-me-32-chars-minimum-length"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    sec_user_agent: str = "sec-flow/1.0 contact@example.com"
    database_url: str = "sqlite+aiosqlite:///./secflow.db"
    secret_key: str = _INSECURE_DEFAULT_KEY
    cache_ttl_seconds: int = 900          # 15 min -- SEC updates filings every hour
    rate_limit_per_minute: int = 30       # SEC fair-access policy: max 10 req/s
    environment: str = "development"
    sentry_dsn: str = ""
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.secret_key == _INSECURE_DEFAULT_KEY:
        if settings.environment == "production":
            raise ValueError(
                "SECRET_KEY must be set to a strong random value in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        logger.warning(
            "SECURITY: Running with insecure default SECRET_KEY -- "
            "set SECRET_KEY environment variable before deploying to production"
        )
    return settings
