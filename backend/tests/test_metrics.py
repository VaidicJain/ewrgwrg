from datetime import UTC, datetime
from math import sqrt

import pytest

from app.services.metrics import (
    by_day,
    by_horizon,
    by_hour_of_day,
    compute_error_stats,
    quantile,
    safety_buffer,
)
from app.services.selection import ComparisonRow


def row(
    start: str = "2026-01-02T00:00:00",
    actual: float | None = 1000.0,
    error: float | None = 0.0,
    horizon: float | None = 16.5,
) -> ComparisonRow:
    """Build a row from an actual and an error (forecast = actual + error)."""
    t = datetime.fromisoformat(start).replace(tzinfo=UTC)
    forecast = None if error is None or actual is None else actual + error
    return ComparisonRow(
        start_time=t,
        cutoff_time=t,
        actual_mw=actual,
        actual_halfhours=2 if actual is not None else 0,
        forecast_mw=forecast,
        forecast_publish_time=t,
        horizon_hours=horizon,
        error_mw=error if actual is not None and forecast is not None else None,
    )


def rows_with_errors(errors: list[float], actual: float = 10_000.0) -> list[ComparisonRow]:
    return [row(f"2026-01-02T{i:02d}:00:00", actual, e) for i, e in enumerate(errors)]


# ---------------------------------------------------------------- quantile


def test_quantile_interpolates_between_ranks():
    assert quantile([1, 2, 3, 4], 0.5) == 2.5
    assert quantile([1, 2, 3, 4], 0.0) == 1
    assert quantile([1, 2, 3, 4], 1.0) == 4
    assert quantile([4, 1, 3, 2], 0.5) == 2.5  # input order does not matter
    assert quantile([7], 0.9) == 7


def test_quantile_rejects_bad_input():
    with pytest.raises(ValueError):
        quantile([], 0.5)
    with pytest.raises(ValueError):
        quantile([1, 2], 1.5)


# ---------------------------------------------------------------- overall stats


def test_overall_stats_hand_computed():
    # errors +10, -10, +20, -20  ->  abs = 10, 10, 20, 20
    stats = compute_error_stats(rows_with_errors([10, -10, 20, -20]))
    assert stats.n == 4
    assert stats.mae_mw == 15
    assert stats.rmse_mw == pytest.approx(sqrt(250))  # (100+100+400+400)/4 = 250
    assert stats.bias_mw == 0
    assert stats.median_abs_error_mw == 15  # between 10 and 20
    assert stats.p90_abs_error_mw == 20
    assert stats.max_abs_error_mw == 20
    assert stats.mean_actual_mw == 10_000
    assert stats.mae_pct_of_mean_actual == pytest.approx(0.15)


def test_bias_is_positive_when_forecasts_run_high():
    stats = compute_error_stats(rows_with_errors([100, 200, 300]))
    assert stats.bias_mw == 200
    assert stats.mae_mw == 200


def test_rmse_is_never_below_mae_and_larger_with_outliers():
    stats = compute_error_stats(rows_with_errors([0, 0, 0, 400]))
    assert stats.mae_mw == 100
    assert stats.rmse_mw == 200  # sqrt(160000 / 4)
    assert stats.rmse_mw > stats.mae_mw


def test_hours_without_both_values_are_not_scored():
    rows = rows_with_errors([10, 20]) + [
        row("2026-01-02T05:00:00", actual=None, error=None),  # no actual
        row("2026-01-02T06:00:00", actual=1000, error=None),  # no forecast
    ]
    stats = compute_error_stats(rows)
    assert stats.n == 2
    assert stats.mae_mw == 15


def test_no_scored_rows_returns_none():
    assert compute_error_stats([]) is None
    assert compute_error_stats([row(actual=None, error=None)]) is None
    assert safety_buffer([]) is None


def test_mape_skips_actuals_below_the_floor():
    rows = [
        row("2026-01-02T00:00:00", actual=2000, error=200),  # 10 %
        row("2026-01-02T01:00:00", actual=4000, error=-200),  # 5 %
        row("2026-01-02T02:00:00", actual=500, error=250),  # below floor: ignored
    ]
    stats = compute_error_stats(rows, mape_floor_mw=1000)
    assert stats.mape_pct == pytest.approx(7.5)
    assert stats.n == 3  # still counted in the other metrics


def test_mape_is_none_when_every_actual_is_below_the_floor():
    stats = compute_error_stats([row(actual=100, error=10)], mape_floor_mw=1000)
    assert stats.mape_pct is None


# ---------------------------------------------------------------- safety buffer


def test_safety_buffer_uses_signed_error_quantiles():
    # sorted errors: -100, -50, 100, 200, 300
    buf = safety_buffer(rows_with_errors([100, 200, 300, -50, -100]), confidence=0.8)
    # q0.8: position 3.2 -> 200 + 0.2 * 100 = 220
    assert buf.shortfall_buffer_mw == pytest.approx(220)
    # q0.2: position 0.8 -> -100 + 0.8 * 50 = -60  ->  surplus margin 60
    assert buf.surplus_margin_mw == pytest.approx(60)
    assert buf.confidence == 0.8


def test_buffer_is_zero_when_forecasts_never_ran_high():
    buf = safety_buffer(rows_with_errors([-10, -20, -30]), confidence=0.95)
    assert buf.shortfall_buffer_mw == 0


def test_buffer_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        safety_buffer(rows_with_errors([1]), confidence=1.0)


# ---------------------------------------------------------------- groupings


def test_by_hour_of_day_groups_across_days():
    rows = [
        row("2026-01-02T00:00:00", error=100),
        row("2026-01-03T00:00:00", error=-300),
        row("2026-01-02T13:00:00", error=50),
    ]
    groups = by_hour_of_day(rows)
    assert [g.label for g in groups] == ["00:00", "13:00"]
    assert groups[0].n == 2
    assert groups[0].mae_mw == 200
    assert groups[0].bias_mw == -100
    assert groups[1].mae_mw == 50


def test_by_day_groups_and_orders_by_date():
    rows = [
        row("2026-01-03T05:00:00", error=10),
        row("2026-01-02T05:00:00", error=30),
        row("2026-01-02T06:00:00", error=-10),
    ]
    groups = by_day(rows)
    assert [g.label for g in groups] == ["2026-01-02", "2026-01-03"]
    assert groups[0].n == 2
    assert groups[0].mae_mw == 20


def test_by_horizon_buckets():
    rows = [
        row("2026-01-02T00:00:00", error=10, horizon=12.5),
        row("2026-01-02T01:00:00", error=20, horizon=17.5),
        row("2026-01-02T02:00:00", error=40, horizon=18.0),
        row("2026-01-02T03:00:00", error=60, horizon=30.5),
    ]
    groups = by_horizon(rows, bucket_hours=6)
    assert [g.label for g in groups] == ["12-18h", "18-24h", "30-36h"]
    assert [g.n for g in groups] == [2, 1, 1]
    assert groups[0].mae_mw == 15


def test_by_horizon_ignores_unscored_rows():
    rows = [row("2026-01-02T00:00:00", actual=None, error=None, horizon=12.5)]
    assert by_horizon(rows) == []
