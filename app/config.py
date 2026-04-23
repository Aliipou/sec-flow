from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    sec_user_agent: str = "sec-flow/1.0 contact@example.com"
    database_url: str = "sqlite+aiosqlite:///./secflow.db"
    secret_key: str = "change-me-32-chars-minimum-length"
    cache_ttl_seconds: int = 900          # 15 min — SEC updates filings every hour
    rate_limit_per_minute: int = 30       # SEC fair-access policy: max 10 req/s
    environment: str = "development"
    sentry_dsn: str = ""

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
    return Settings()
