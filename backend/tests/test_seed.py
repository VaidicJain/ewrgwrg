import asyncio
from datetime import UTC, date, datetime

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.models import fuelhh, windfor  # noqa: F401  (registers the tables)
from app.scripts.seed import run_seed
from app.services.windfor_service import publish_window


def test_publish_window_starts_before_first_target_and_ends_after_last():
    start, end = publish_window(date(2026, 1, 1), date(2026, 1, 31), lookback_days=3)
    assert start == datetime(2025, 12, 29, tzinfo=UTC)
    assert end == datetime(2026, 2, 1, tzinfo=UTC)


def test_run_seed_loads_both_datasets_and_is_repeatable(fake_elexon):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    day = date(2026, 1, 2)

    with Session(engine) as session:
        actuals, forecasts = asyncio.run(run_seed(session, fake_elexon, day, day))
        assert (actuals.inserted, actuals.updated) == (2, 0)
        assert (forecasts.inserted, forecasts.skipped_existing) == (3, 0)

        actuals, forecasts = asyncio.run(run_seed(session, fake_elexon, day, day))
        assert (actuals.inserted, actuals.updated) == (0, 2)
        assert (forecasts.inserted, forecasts.skipped_existing) == (0, 3)
