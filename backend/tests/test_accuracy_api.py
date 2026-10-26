PARAMS = {"start_date": "2026-01-02", "end_date": "2026-01-02"}


def test_accuracy_with_nothing_loaded_returns_empty_metrics_and_warnings(client):
    body = client.get("/api/v1/analysis/accuracy", params=PARAMS).json()
    assert body["overall"] is None
    assert body["safety_buffer"] is None
    assert body["by_hour_of_day"] == []
    assert body["warnings"]


def test_accuracy_scores_stored_data(client):
    client.post("/api/v1/fuelhh/sync", params=PARAMS)
    client.post("/api/v1/windfor/sync", params=PARAMS)

    body = client.get("/api/v1/analysis/accuracy", params={**PARAMS, "cutoff_time": "09:00"}).json()

    # Fake data: actuals 1000 and 1050 for hour 00 -> hourly mean 1025.
    # Forecast available at 09:00 on Jan 1 is the 06:00 publish = 3000 -> error = +1975.
    assert body["coverage"]["compared"] == 1
    assert body["overall"]["n"] == 1
    assert body["overall"]["mae_mw"] == 1975
    assert body["overall"]["bias_mw"] == 1975
    assert body["safety_buffer"]["shortfall_buffer_mw"] == 1975
    assert body["by_hour_of_day"][0]["label"] == "00:00"
    assert body["by_horizon"][0]["label"] == "18-24h"  # published 18h before the target hour


def test_accuracy_rejects_invalid_confidence(client):
    response = client.get("/api/v1/analysis/accuracy", params={**PARAMS, "confidence": 1.5})
    assert response.status_code == 422
