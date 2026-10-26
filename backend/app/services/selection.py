"""Pure forecast-selection logic: no database, no HTTP, easy to unit test.

Question answered: for each hour of the delivery period, which forecast did the buyer actually
have at decision time, and how did it compare with what was really generated?

Rules
- Forecast resolution is hourly (Elexon WINDFOR). Actuals are half-hourly (FUELHH), so an hourly
  actual is the mean of the two half-hours starting at HH:00 and HH:30.
- For a target hour on day D, the decision cutoff is (D - days_before) at `cutoff_time`, in UTC.
- The chosen forecast is the one with the latest publish_time that is <= the cutoff.
  A forecast published exactly at the cutoff counts as available.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from statistics import fmean


@dataclass(frozen=True)
class ForecastPoint:
    start_time: datetime
    publish_time: datetime
    generation: float


@dataclass(frozen=True)
class ActualPoint:
    start_time: datetime
    generation: float


@dataclass(frozen=True)
class ComparisonRow:
    start_time: datetime
    cutoff_time: datetime
    actual_mw: float | None
    actual_halfhours: int
    forecast_mw: float | None
    forecast_publish_time: datetime | None
    horizon_hours: float | None
    error_mw: float | None  # forecast - actual (positive = over-forecast)


@dataclass(frozen=True)
class Coverage:
    total_hours: int
    with_forecast: int
    with_actual: int
    compared: int

    @property
    def missing_forecast(self) -> int:
        return self.total_hours - self.with_forecast

    @property
    def missing_actual(self) -> int:
        return self.total_hours - self.with_actual


@dataclass(frozen=True)
class ComparisonResult:
    rows: list[ComparisonRow]
    coverage: Coverage


def to_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def decision_cutoff(target: datetime, cutoff_time: time, days_before: int) -> datetime:
    """The moment the purchase decision for `target` has to be made."""
    day = to_utc(target).date() - timedelta(days=days_before)
    return datetime.combine(day, cutoff_time.replace(tzinfo=None), tzinfo=UTC)


def hourly_actuals(actuals: Iterable[ActualPoint]) -> dict[datetime, tuple[float, int]]:
    """Group half-hourly actuals into hours. Returns {hour_start: (mean_mw, half_hours_present)}."""
    buckets: dict[datetime, list[float]] = defaultdict(list)
    for actual in actuals:
        hour = to_utc(actual.start_time).replace(minute=0, second=0, microsecond=0)
        buckets[hour].append(actual.generation)
    return {hour: (fmean(values), len(values)) for hour, values in buckets.items()}


def build_comparison(
    forecasts: Iterable[ForecastPoint],
    actuals: Iterable[ActualPoint],
    start_date: date,
    end_date: date,
    cutoff_time: time,
    days_before: int = 1,
) -> ComparisonResult:
    """One row per hour in [start_date, end_date], pairing the decision-time forecast with the actual."""
    by_slot: dict[datetime, list[ForecastPoint]] = defaultdict(list)
    for forecast in forecasts:
        by_slot[to_utc(forecast.start_time)].append(forecast)

    actual_by_hour = hourly_actuals(actuals)

    slot = datetime.combine(start_date, time.min, tzinfo=UTC)
    end = datetime.combine(end_date, time.min, tzinfo=UTC) + timedelta(days=1)

    rows: list[ComparisonRow] = []
    with_forecast = with_actual = compared = 0

    while slot < end:
        cutoff = decision_cutoff(slot, cutoff_time, days_before)

        eligible = [f for f in by_slot.get(slot, []) if to_utc(f.publish_time) <= cutoff]
        chosen = max(eligible, key=lambda f: to_utc(f.publish_time), default=None)

        mean_mw, halfhours = actual_by_hour.get(slot, (None, 0))
        actual_mw = mean_mw if halfhours == 2 else None  # an hour with a missing half is not trusted

        forecast_mw = chosen.generation if chosen else None
        publish_time = to_utc(chosen.publish_time) if chosen else None
        horizon = (slot - publish_time).total_seconds() / 3600 if publish_time else None
        error = forecast_mw - actual_mw if forecast_mw is not None and actual_mw is not None else None

        with_forecast += forecast_mw is not None
        with_actual += actual_mw is not None
        compared += error is not None

        rows.append(
            ComparisonRow(
                start_time=slot,
                cutoff_time=cutoff,
                actual_mw=actual_mw,
                actual_halfhours=halfhours,
                forecast_mw=forecast_mw,
                forecast_publish_time=publish_time,
                horizon_hours=horizon,
                error_mw=error,
            )
        )
        slot += timedelta(hours=1)

    coverage = Coverage(
        total_hours=len(rows), with_forecast=with_forecast, with_actual=with_actual, compared=compared
    )
    return ComparisonResult(rows=rows, coverage=coverage)
