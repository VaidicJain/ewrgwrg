from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class FuelHHElexonRecord(BaseModel):
    """One row exactly as Elexon's FUELHH stream returns it (camelCase JSON)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    dataset: str
    publish_time: datetime
    start_time: datetime
    settlement_date: date
    settlement_period: int
    fuel_type: str
    generation: float


class FuelHHRead(BaseModel):
    """One row returned by our own API."""

    model_config = ConfigDict(from_attributes=True)

    fuel_type: str
    start_time: datetime
    settlement_date: date
    settlement_period: int
    publish_time: datetime
    generation: float = Field(description="Generation in MW")

    @field_validator("start_time", "publish_time", mode="after")
    @classmethod
    def _ensure_utc(cls, value: datetime) -> datetime:
        # SQLite returns naive datetimes; we always store UTC.
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class FuelHHListResponse(BaseModel):
    fuel_type: str
    start_date: date
    end_date: date
    count: int
    data: list[FuelHHRead]


class FuelHHSyncResponse(BaseModel):
    fuel_type: str
    start_date: date
    end_date: date
    fetched: int
    inserted: int
    updated: int
