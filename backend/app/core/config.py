import json
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration. Values can be overridden via environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "GridBricks Wind Monitor API"
    api_prefix: str = "/api/v1"

    # Local default is SQLite; swap for Postgres by changing this URL only.
    database_url: str = "sqlite:///./gridbricks.db"
    # Optional: a pre-filled SQLite file copied to the database path on first start when that path
    # does not exist yet (needed on Vercel, where only /tmp is writable). Defaults to backend/gridbricks.db.
    seed_db_path: str | None = None

    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    elexon_timeout_seconds: float = 30.0
    elexon_max_retries: int = 3
    # Large date ranges are split into chunks per Elexon request.
    elexon_chunk_days: int = 7  # FUELHH, by settlement date
    elexon_windfor_chunk_days: int = 1  # WINDFOR, by publish time (many rows per day)

    # Read from the CORS_ORIGINS environment variable as plain text so that a badly formatted
    # value can never crash the whole app at start-up. Use the `cors_origins` property below.
    cors_origins_raw: str = Field(default='["http://localhost:3000"]', validation_alias="CORS_ORIGINS")

    @property
    def cors_origins(self) -> list[str]:
        """Allowed browser origins. Accepts a JSON list or a comma-separated string.

        Trailing slashes are removed because browsers never send them in the Origin header.
        """
        raw = self.cors_origins_raw.strip()
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except ValueError:
                parsed = []
            items = parsed if isinstance(parsed, list) else []
        else:
            items = raw.split(",")
        return [origin for origin in (str(item).strip().strip("\"'").rstrip("/") for item in items) if origin]


@lru_cache
def get_settings() -> Settings:
    return Settings()
