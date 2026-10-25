from app.schemas.fuelhh import FuelHHElexonRecord

PARAMS = {"start_date": "2026-01-01", "end_date": "2026-01-01", "fuel_type": "WIND"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_elexon_record_parses_camel_case():
    record = FuelHHElexonRecord.model_validate(
        {
            "dataset": "FUELHH",
            "publishTime": "2026-01-01T00:30:00Z",
            "startTime": "2026-01-01T00:00:00Z",
            "settlementDate": "2026-01-01",
            "settlementPeriod": 1,
            "fuelType": "WIND",
            "generation": 4321,
        }
    )
    assert record.fuel_type == "WIND"
    assert record.generation == 4321.0
    assert record.start_time.tzinfo is not None


def test_sync_inserts_then_updates_without_duplicates(client, fake_elexon):
    first = client.post("/api/v1/fuelhh/sync", params=PARAMS).json()
    assert (first["fetched"], first["inserted"], first["updated"]) == (2, 2, 0)

    fake_elexon.generation = 2000.0
    second = client.post("/api/v1/fuelhh/sync", params=PARAMS).json()
    assert (second["inserted"], second["updated"]) == (0, 2)

    data = client.get("/api/v1/fuelhh", params=PARAMS).json()
    assert data["count"] == 2
    assert data["data"][0]["generation"] == 2000.0
    assert data["data"][0]["start_time"].startswith("2026-01-01T00:00:00")


def test_get_fetches_once_when_empty_then_uses_stored_data(client, fake_elexon):
    client.get("/api/v1/fuelhh", params=PARAMS)
    client.get("/api/v1/fuelhh", params=PARAMS)
    assert fake_elexon.calls == 1

    client.get("/api/v1/fuelhh", params={**PARAMS, "refresh": True})
    assert fake_elexon.calls == 2


def test_invalid_date_range_is_rejected(client):
    response = client.get(
        "/api/v1/fuelhh", params={"start_date": "2026-01-05", "end_date": "2026-01-01"}
    )
    assert response.status_code == 422
