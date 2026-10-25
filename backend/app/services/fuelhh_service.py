from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlmodel import Session, select

from app.models.fuelhh import FuelHHActual
from app.services.elexon_client import ElexonClient


@dataclass
class SyncResult:
    fetched: int
    inserted: int
    updated: int


def _utc(value: datetime) -> datetime:
    """Normalise to timezone-aware UTC (some DB drivers hand back naive values)."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def query_fuelhh(session: Session, start_date: date, end_date: date, fuel_type: str) -> list[FuelHHActual]:
    statement = (
        select(FuelHHActual)
        .where(FuelHHActual.fuel_type == fuel_type)
        .where(FuelHHActual.settlement_date >= start_date)
        .where(FuelHHActual.settlement_date <= end_date)
        .order_by(FuelHHActual.start_time)
    )
    return list(session.exec(statement).all())


async def sync_fuelhh(
    session: Session,
    client: ElexonClient,
    start_date: date,
    end_date: date,
    fuel_type: str,
) -> SyncResult:
    """Fetch FUELHH rows from Elexon and upsert them into the database."""
    records = await client.fetch_fuelhh(start_date, end_date, [fuel_type])

    existing_rows = query_fuelhh(session, start_date, end_date, fuel_type)
    existing = {_utc(row.start_time): row for row in existing_rows}

    inserted = updated = 0
    for rec in records:
        start_time = _utc(rec.start_time)
        publish_time = _utc(rec.publish_time)

        row = existing.get(start_time)
        if row is None:
            session.add(
                FuelHHActual(
                    dataset=rec.dataset,
                    fuel_type=rec.fuel_type,
                    start_time=start_time,
                    settlement_date=rec.settlement_date,
                    settlement_period=rec.settlement_period,
                    publish_time=publish_time,
                    generation=rec.generation,
                )
            )
            inserted += 1
        else:
            row.generation = rec.generation
            row.publish_time = publish_time
            row.settlement_period = rec.settlement_period
            session.add(row)
            updated += 1

    session.commit()
    return SyncResult(fetched=len(records), inserted=inserted, updated=updated)
