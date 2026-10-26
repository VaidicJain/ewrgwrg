import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api.deps import get_elexon_client
from app.db.session import get_session
from app.main import app
from app.models import fuelhh, windfor  # noqa: F401  (registers the tables)
from app.schemas.fuelhh import FuelHHElexonRecord
from app.schemas.windfor import WindForElexonRecord


def make_record(start_time: str, generation: float, period: int, publish_time: str = "2026-01-01T01:00:00Z"):
    """Build a FUELHH record the same way Elexon's JSON would arrive (camelCase)."""
    return FuelHHElexonRecord.model_validate(
        {
            "dataset": "FUELHH",
            "publishTime": publish_time,
            "startTime": start_time,
            "settlementDate": start_time[:10],
            "settlementPeriod": period,
            "fuelType": "WIND",
            "generation": generation,
        }
    )


def make_windfor(start_time: str, publish_time: str, generation: float):
    return WindForElexonRecord.model_validate(
        {
            "dataset": "WINDFOR",
            "publishTime": publish_time,
            "startTime": start_time,
            "generation": generation,
        }
    )


class FakeElexonClient:
    def __init__(self) -> None:
        self.calls = 0
        self.windfor_calls = 0
        self.generation = 1000.0

    async def fetch_fuelhh(self, start_date, end_date, fuel_types):
        self.calls += 1
        day = start_date.isoformat()
        return [
            make_record(f"{day}T00:00:00Z", self.generation, 1),
            make_record(f"{day}T00:30:00Z", self.generation + 50, 2),
        ]

    async def fetch_windfor(self, publish_from, publish_to):
        """Two forecasts for the same target slot (early and late publish) plus one for another slot."""
        self.windfor_calls += 1
        return [
            make_windfor("2026-01-02T00:00:00Z", "2026-01-01T06:00:00Z", 3000),
            make_windfor("2026-01-02T00:00:00Z", "2026-01-01T18:00:00Z", 3500),
            make_windfor("2026-01-02T00:30:00Z", "2026-01-01T06:00:00Z", 3100),
        ]


@pytest.fixture
def fake_elexon() -> FakeElexonClient:
    return FakeElexonClient()


@pytest.fixture
def client(fake_elexon: FakeElexonClient):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_elexon_client] = lambda: fake_elexon
    # No `with` block: skips the lifespan so the real database file is never created.
    yield TestClient(app)
    app.dependency_overrides.clear()
