"""Load Elexon data into the database in one go.

Usage (from the backend folder):
    uv run python -m app.scripts.seed                      # all of January 2026
    uv run python -m app.scripts.seed --start 2026-01-01 --end 2026-01-07

Safe to run repeatedly: existing rows are updated or skipped, never duplicated.
The deployed app ships with the resulting database file so it does not depend on Elexon being
reachable while it is being reviewed.
"""

import argparse
import asyncio
import logging
from datetime import date

from sqlmodel import Session

from app.core.config import get_settings
from app.db.session import engine, init_db
from app.services import fuelhh_service, windfor_service
from app.services.elexon_client import ElexonClient, build_elexon_client
from app.services.fuelhh_service import SyncResult
from app.services.windfor_service import WindForSyncResult

DEFAULT_START = date(2026, 1, 1)
DEFAULT_END = date(2026, 1, 31)
DEFAULT_LOOKBACK_DAYS = 3


async def run_seed(
    session: Session,
    client: ElexonClient,
    start_date: date,
    end_date: date,
    fuel_type: str = "WIND",
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> tuple[SyncResult, WindForSyncResult]:
    """Fetch actuals and forecasts for the date range and store them."""
    actuals = await fuelhh_service.sync_fuelhh(session, client, start_date, end_date, fuel_type)
    publish_from, publish_to = windfor_service.publish_window(start_date, end_date, lookback_days)
    forecasts = await windfor_service.sync_windfor(session, client, publish_from, publish_to)
    return actuals, forecasts


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the database with Elexon wind data.")
    parser.add_argument("--start", type=_parse_date, default=DEFAULT_START, help="first target date")
    parser.add_argument("--end", type=_parse_date, default=DEFAULT_END, help="last target date")
    parser.add_argument("--fuel-type", default="WIND")
    parser.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    args = parser.parse_args()

    if args.end < args.start:
        parser.error("--end must be on or after --start")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(f"Database: {get_settings().database_url}")
    print(f"Seeding {args.fuel_type} for {args.start} to {args.end} (this can take a minute or two)...")

    init_db()
    with Session(engine) as session:
        actuals, forecasts = asyncio.run(
            run_seed(
                session,
                build_elexon_client(),
                args.start,
                args.end,
                args.fuel_type.upper(),
                args.lookback_days,
            )
        )

    print(f"Actuals   (FUELHH): fetched {actuals.fetched}, inserted {actuals.inserted}, updated {actuals.updated}")
    print(
        f"Forecasts (WINDFOR): fetched {forecasts.fetched}, inserted {forecasts.inserted}, "
        f"skipped existing {forecasts.skipped_existing}"
    )
    print("Done.")


if __name__ == "__main__":
    main()
