import logging
import shutil
from collections.abc import Iterator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

SQLITE_PREFIX = "sqlite:///"
# backend/app/db/session.py -> backend/gridbricks.db (the dataset that ships with the repo)
DEFAULT_SEED_DB = Path(__file__).resolve().parents[2] / "gridbricks.db"


def _sqlite_file(url: str) -> Path | None:
    """The file behind a sqlite URL, or None for in-memory / non-sqlite databases."""
    if not url.startswith(SQLITE_PREFIX):
        return None
    raw = url[len(SQLITE_PREFIX) :]
    return Path(raw) if raw and raw != ":memory:" else None


def seed_database_file() -> None:
    """Copy the shipped dataset to the configured path if nothing is there yet.

    Docker (a mounted volume) and Vercel (only /tmp is writable) both start with an empty location,
    so the very first start copies the pre-filled January 2026 database into place.
    """
    target = _sqlite_file(settings.database_url)
    seed = Path(settings.seed_db_path) if settings.seed_db_path else DEFAULT_SEED_DB
    if target is None or target.exists() or not seed.is_file():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(seed, target)
    logger.info("Seeded %s from %s", target, seed)


seed_database_file()

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=_connect_args)


def init_db() -> None:
    """Create tables. Models must be imported so they register on SQLModel.metadata."""
    from app.models import fuelhh, windfor  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
