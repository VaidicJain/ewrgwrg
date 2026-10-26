PARAMS = {"start_date": "2026-01-02", "end_date": "2026-01-02"}


def test_forecast_vs_actual_warns_when_nothing_is_loaded(client):
    body = client.get("/api/v1/analysis/forecast-vs-actual", params=PARAMS).json()
    assert body["cutoff_time"] == "09:00"
    assert body["coverage"]["total_hours"] == 24
    assert body["coverage"]["compared"] == 0
    assert len(body["rows"]) == 24
    assert any("windfor/sync" in w for w in body["warnings"])
    assert any("fuelhh/sync" in w for w in body["warnings"])


def test_forecast_vs_actual_uses_stored_data(client):
    # Fake client forecasts: two publishes (06:00, 18:00 on Jan 1) for 2026-01-02 00:00.
    client.post("/api/v1/windfor/sync", params=PARAMS)

    early = client.get(
        "/api/v1/analysis/forecast-vs-actual", params={**PARAMS, "cutoff_time": "09:00"}
    ).json()
    late = client.get(
        "/api/v1/analysis/forecast-vs-actual", params={**PARAMS, "cutoff_time": "20:00"}
    ).json()

    assert early["rows"][0]["forecast_mw"] == 3000  # only the 06:00 publish existed at 09:00
    assert late["rows"][0]["forecast_mw"] == 3500  # the 18:00 publish is available by 20:00


def test_forecast_vs_actual_validates_range(client):
    response = client.get(
        "/api/v1/analysis/forecast-vs-actual",
        params={"start_date": "2026-01-05", "end_date": "2026-01-01"},
    )
    assert response.status_code == 422
