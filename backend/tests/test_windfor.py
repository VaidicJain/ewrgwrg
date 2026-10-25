from app.schemas.windfor import WindForElexonRecord

PARAMS = {"start_date": "2026-01-02", "end_date": "2026-01-02"}


def test_windfor_record_parses_camel_case():
    record = WindForElexonRecord.model_validate(
        {
            "dataset": "WINDFOR",
            "publishTime": "2026-01-01T06:00:00Z",
            "startTime": "2026-01-02T00:00:00Z",
            "generation": 3000,
        }
    )
    assert record.generation == 3000.0
    assert record.publish_time < record.start_time


def test_sync_keeps_every_publish_and_is_idempotent(client):
    first = client.post("/api/v1/windfor/sync", params=PARAMS).json()
    assert (first["fetched"], first["inserted"], first["skipped_existing"]) == (3, 3, 0)

    second = client.post("/api/v1/windfor/sync", params=PARAMS).json()
    assert (second["inserted"], second["skipped_existing"]) == (0, 3)

    data = client.get("/api/v1/windfor", params=PARAMS).json()
    assert data["count"] == 3
    assert data["truncated"] is False
    # Two different publishes for the same target slot are both kept, oldest first.
    first_slot = [r for r in data["data"] if r["start_time"].startswith("2026-01-02T00:00:00")]
    assert [r["generation"] for r in first_slot] == [3000.0, 3500.0]


def test_publish_before_filters_out_late_forecasts(client):
    client.post("/api/v1/windfor/sync", params=PARAMS)
    data = client.get(
        "/api/v1/windfor", params={**PARAMS, "publish_before": "2026-01-01T12:00:00Z"}
    ).json()
    assert data["count"] == 2
    assert {r["generation"] for r in data["data"]} == {3000.0, 3100.0}


def test_limit_marks_response_as_truncated(client):
    client.post("/api/v1/windfor/sync", params=PARAMS)
    data = client.get("/api/v1/windfor", params={**PARAMS, "limit": 2}).json()
    assert data["count"] == 2
    assert data["truncated"] is True


def test_raw_rejects_oversized_window(client):
    response = client.get(
        "/api/v1/windfor/raw",
        params={"publish_from": "2026-01-01T00:00:00Z", "publish_to": "2026-01-10T00:00:00Z"},
    )
    assert response.status_code == 422
