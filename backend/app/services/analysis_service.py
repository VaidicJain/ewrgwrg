import logging
from datetime import UTC, date, datetime, time

from sqlmodel import Session

from app.services import fuelhh_service, windfor_service
from app.services.selection import (
    ActualPoint,
    ComparisonResult,
    Coverage,
    ForecastPoint,
    build_comparison,
    decision_cutoff,
)

logger = logging.getLogger(__name__)

MAX_FORECAST_ROWS = 200_000


def compare_forecast_to_actual(
    session: Session,
    start_date: date,
    end_date: date,
    cutoff_time: time,
    days_before: int = 1,
    fuel_type: str = "WIND",
) -> ComparisonResult:
    """Load stored data and run the pure selection logic on it."""
    last_slot = datetime.combine(end_date, time.min, tzinfo=UTC)
    # Cutoffs only move forward with the day, so the last day's cutoff bounds every publish we need.
    latest_cutoff = decision_cutoff(last_slot, cutoff_time, days_before)

    forecast_rows, truncated = windfor_service.query_windfor(
        session, start_date, end_date, publish_before=latest_cutoff, limit=MAX_FORECAST_ROWS
    )
    if truncated:
        logger.warning("Forecast rows truncated at %s; results may be incomplete", MAX_FORECAST_ROWS)

    actual_rows = fuelhh_service.query_fuelhh(session, start_date, end_date, fuel_type)

    forecasts = [ForecastPoint(r.start_time, r.publish_time, r.generation) for r in forecast_rows]
    actuals = [ActualPoint(r.start_time, r.generation) for r in actual_rows]

    return build_comparison(forecasts, actuals, start_date, end_date, cutoff_time, days_before)


def coverage_warnings(cov: Coverage) -> list[str]:
    """Human-readable notes about missing data, shared by every analysis endpoint."""
    warnings: list[str] = []
    if cov.with_forecast == 0:
        warnings.append("No forecasts found before the cutoff. Run POST /api/v1/windfor/sync for this range.")
    elif cov.missing_forecast:
        warnings.append(f"{cov.missing_forecast} hour(s) have no forecast published before the cutoff.")
    if cov.with_actual == 0:
        warnings.append("No complete actuals found. Run POST /api/v1/fuelhh/sync for this range.")
    elif cov.missing_actual:
        warnings.append(f"{cov.missing_actual} hour(s) have no complete actual (a half-hour is missing).")
    return warnings
