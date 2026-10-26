from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlmodel import Session, select

from app.models.windfor import WindForecast
from app.services.elexon_client import ElexonClient


@dataclass
class WindForSyncResult:
    fetched: int
    inserted: int
    skipped_existing: int


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def day_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def publish_window(start_date: date, end_date: date, lookback_days: int = 3) -> tuple[datetime, datetime]:
    """Publish-time window that covers every forecast relevant to the given target dates.

    Forecasts for a day are created in the days before it, so the window starts `lookback_days`
    before start_date and ends at the end of end_date.
    """
    return day_start(start_date) - timedelta(days=lookback_days), day_start(end_date) + timedelta(days=1)


def query_windfor(
    session: Session,
    start_date: date,
    end_date: date,
    publish_before: datetime | None = None,
    limit: int = 10_000,
) -> tuple[list[WindForecast], bool]:
    """Forecasts whose target time falls in [start_date, end_date] (UTC days).

    Returns (rows, truncated). `truncated` is True when more rows matched than `limit`.
    """
    statement = (
        select(WindForecast)
        .where(WindForecast.start_time >= day_start(start_date))
        .where(WindForecast.start_time < day_start(end_date) + timedelta(days=1))
        .order_by(WindForecast.start_time, WindForecast.publish_time)
        .limit(limit + 1)
    )
    if publish_before is not None:
        statement = statement.where(WindForecast.publish_time <= _utc(publish_before))

    rows = list(session.exec(statement).all())
    return rows[:limit], len(rows) > limit


async def sync_windfor(
    session: Session,
    client: ElexonClient,
    publish_from: datetime,
    publish_to: datetime,
) -> WindForSyncResult:
    """Fetch forecasts published in the window and insert the ones we do not already have."""
    records = await client.fetch_windfor(publish_from, publish_to)

    existing_stmt = select(WindForecast.start_time, WindForecast.publish_time).where(
        WindForecast.publish_time >= _utc(publish_from),
        WindForecast.publish_time <= _utc(publish_to),
    )
    existing = {(_utc(s), _utc(p)) for s, p in session.exec(existing_stmt).all()}

    inserted = skipped = 0
    for rec in records:
        key = (_utc(rec.start_time), _utc(rec.publish_time))
        if key in existing:
            skipped += 1
            continue
        session.add(
            WindForecast(
                dataset=rec.dataset,
                start_time=key[0],
                publish_time=key[1],
                generation=rec.generation,
            )
        )
        existing.add(key)
        inserted += 1

    session.commit()
    return WindForSyncResult(fetched=len(records), inserted=inserted, skipped_existing=skipped)
