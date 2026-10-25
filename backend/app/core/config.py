from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration. Values can be overridden via environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "GridBricks Wind Monitor API"
    api_prefix: str = "/api/v1"

    # Local default is SQLite; swap for Postgres by changing this URL only.
    database_url: str = "sqlite:///./gridbricks.db"

    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    elexon_timeout_seconds: float = 30.0
    elexon_max_retries: int = 3
    # Large date ranges are split into chunks per Elexon request.
    elexon_chunk_days: int = 7  # FUELHH, by settlement date
    elexon_windfor_chunk_days: int = 1  # WINDFOR, by publish time (many rows per day)

    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
