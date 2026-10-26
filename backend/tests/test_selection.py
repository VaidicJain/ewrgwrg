from datetime import UTC, date, datetime, time

from app.services.selection import (
    ActualPoint,
    ForecastPoint,
    build_comparison,
    decision_cutoff,
    hourly_actuals,
)

D = date(2026, 1, 2)  # delivery day under test
CUTOFF = time(9, 0)  # decision at 09:00 UTC on D-1 = 2026-01-01 09:00


def dt(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def fc(start: str, publish: str, mw: float) -> ForecastPoint:
    return ForecastPoint(dt(start), dt(publish), mw)


def act(start: str, mw: float) -> ActualPoint:
    return ActualPoint(dt(start), mw)


def first_row(forecasts, actuals):
    result = build_comparison(forecasts, actuals, D, D, CUTOFF)
    return result.rows[0], result


def full_hour_actuals(hour: str, mw: float):
    """Both half-hours of 2026-01-02 <hour>."""
    return [act(f"2026-01-02T{hour}:00:00", mw), act(f"2026-01-02T{hour}:30:00", mw)]


def test_decision_cutoff_is_day_before_at_cutoff_time():
    assert decision_cutoff(dt("2026-01-02T14:00:00"), CUTOFF, 1) == dt("2026-01-01T09:00:00")
    assert decision_cutoff(dt("2026-01-02T00:00:00"), CUTOFF, 0) == dt("2026-01-02T09:00:00")


def test_picks_latest_publish_before_cutoff():
    forecasts = [
        fc("2026-01-02T00:00:00", "2026-01-01T02:30:00", 100),
        fc("2026-01-02T00:00:00", "2026-01-01T07:30:00", 200),  # latest before 09:00
        fc("2026-01-02T00:00:00", "2026-01-01T09:30:00", 300),  # after cutoff: must be ignored
    ]
    row, _ = first_row(forecasts, full_hour_actuals("00", 150))
    assert row.forecast_mw == 200
    assert row.forecast_publish_time == dt("2026-01-01T07:30:00")


def test_forecast_published_exactly_at_cutoff_is_available():
    forecasts = [
        fc("2026-01-02T00:00:00", "2026-01-01T07:30:00", 200),
        fc("2026-01-02T00:00:00", "2026-01-01T09:00:00", 250),
    ]
    row, _ = first_row(forecasts, [])
    assert row.forecast_mw == 250


def test_forecast_published_after_cutoff_is_never_used():
    forecasts = [fc("2026-01-02T00:00:00", "2026-01-01T09:00:01", 999)]
    row, result = first_row(forecasts, full_hour_actuals("00", 100))
    assert row.forecast_mw is None
    assert row.error_mw is None
    assert result.coverage.missing_forecast == 24
    assert result.coverage.compared == 0


def test_error_and_horizon():
    forecasts = [fc("2026-01-02T06:00:00", "2026-01-01T07:30:00", 1200)]
    row_06 = build_comparison(forecasts, full_hour_actuals("06", 1000), D, D, CUTOFF).rows[6]
    assert row_06.start_time == dt("2026-01-02T06:00:00")
    assert row_06.horizon_hours == 22.5  # 07:30 on D-1 to 06:00 on D
    assert row_06.actual_mw == 1000
    assert row_06.error_mw == 200  # over-forecast is positive


def test_hourly_actual_is_mean_of_two_half_hours():
    actuals = [act("2026-01-02T05:00:00", 1000), act("2026-01-02T05:30:00", 1200)]
    assert hourly_actuals(actuals)[dt("2026-01-02T05:00:00")] == (1100.0, 2)


def test_hour_with_one_missing_half_hour_is_not_compared():
    actuals = [act("2026-01-02T05:00:00", 1000)]  # 05:30 missing
    forecasts = [fc("2026-01-02T05:00:00", "2026-01-01T07:30:00", 1100)]
    result = build_comparison(forecasts, actuals, D, D, CUTOFF)
    row = result.rows[5]
    assert row.actual_mw is None
    assert row.actual_halfhours == 1
    assert row.forecast_mw == 1100
    assert row.error_mw is None
    assert result.coverage.with_actual == 0


def test_each_delivery_day_uses_its_own_cutoff():
    forecasts = [
        fc("2026-01-02T00:00:00", "2026-01-01T07:30:00", 10),
        fc("2026-01-03T00:00:00", "2026-01-01T07:30:00", 20),  # eligible, but older
        fc("2026-01-03T00:00:00", "2026-01-02T07:30:00", 30),  # latest before Jan 3's cutoff (Jan 2 09:00)
    ]
    result = build_comparison(forecasts, [], date(2026, 1, 2), date(2026, 1, 3), CUTOFF)
    jan2_00 = result.rows[0]
    jan3_00 = result.rows[24]
    assert jan2_00.forecast_mw == 10
    assert jan3_00.forecast_mw == 30
    assert jan3_00.cutoff_time == dt("2026-01-02T09:00:00")


def test_rows_cover_every_hour_of_the_range_even_without_data():
    result = build_comparison([], [], date(2026, 1, 2), date(2026, 1, 4), CUTOFF)
    assert len(result.rows) == 72
    assert result.coverage.total_hours == 72
    assert result.coverage.with_forecast == 0
    assert result.coverage.with_actual == 0


def test_perfect_forecast_has_zero_error():
    forecasts = [fc("2026-01-02T10:00:00", "2026-01-01T07:30:00", 5000)]
    row = build_comparison(forecasts, full_hour_actuals("10", 5000), D, D, CUTOFF).rows[10]
    assert row.error_mw == 0
