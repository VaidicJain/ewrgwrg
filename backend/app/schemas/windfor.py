from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class WindForElexonRecord(BaseModel):
    """One row exactly as Elexon's WINDFOR stream returns it (camelCase JSON)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    dataset: str = "WINDFOR"
    publish_time: datetime
    start_time: datetime
    generation: float | None = None


class WindForecastRead(BaseModel):
    """One forecast row returned by our own API."""

    model_config = ConfigDict(from_attributes=True)

    start_time: datetime = Field(description="Target half-hour the forecast is for")
    publish_time: datetime = Field(description="When the forecast was created")
    generation: float = Field(description="Forecast generation in MW")

    @field_validator("start_time", "publish_time", mode="after")
    @classmethod
    def _ensure_utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class WindForecastListResponse(BaseModel):
    start_date: str
    end_date: str
    publish_before: datetime | None
    count: int
    truncated: bool = Field(description="True if more rows matched than `limit` allowed")
    data: list[WindForecastRead]


class WindForecastSyncResponse(BaseModel):
    start_date: str
    end_date: str
    publish_from: datetime
    publish_to: datetime
    fetched: int
    inserted: int
    skipped_existing: int
