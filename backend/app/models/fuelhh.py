from datetime import date, datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class FuelHHActual(SQLModel, table=True):
    """One half-hourly actual generation reading for a fuel type (Elexon FUELHH).

    Datetimes are stored as timezone-aware UTC. One row per (fuel_type, start_time);
    if Elexon republishes a slot, the row is updated in place.
    """

    __tablename__ = "fuelhh_actual"
    __table_args__ = (UniqueConstraint("fuel_type", "start_time", name="uq_fuelhh_fuel_start"),)

    id: int | None = Field(default=None, primary_key=True)
    dataset: str
    fuel_type: str = Field(index=True)
    start_time: datetime = Field(index=True)
    settlement_date: date = Field(index=True)
    settlement_period: int
    publish_time: datetime
    generation: float  # MW
