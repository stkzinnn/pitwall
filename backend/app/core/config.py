from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PitWall"
    environment: str = "development"
    debug: bool = True

    api_v1_prefix: str = "/api/v1"

    # Database (async SQLAlchemy engine — see app/db/session.py)
    database_url: str = "postgresql+asyncpg://pitwall:pitwall@localhost:5433/pitwall"

    # Data sources
    fastf1_cache_dir: str = ".cache/fastf1"
    jolpica_base_url: str = "https://api.jolpi.ca/ergast/f1"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
