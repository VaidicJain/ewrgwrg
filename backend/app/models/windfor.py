from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class WindForecast(SQLModel, table=True):
    """One wind forecast value: the forecast for `start_time`, created at `publish_time` (Elexon WINDFOR).

    Every publish is kept (not just the latest) because the analysis needs to know which forecast
    was available at a given decision time. Rows are immutable, so the key is the pair of times.
    Datetimes are timezone-aware UTC.
    """

    __tablename__ = "wind_forecast"
    __table_args__ = (UniqueConstraint("start_time", "publish_time", name="uq_windfor_start_publish"),)

    id: int | None = Field(default=None, primary_key=True)
    dataset: str
    start_time: datetime = Field(index=True)
    publish_time: datetime = Field(index=True)
    generation: float  # MW
