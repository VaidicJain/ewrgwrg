from datetime import date, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.analysis import (
    AccuracyResponse,
    ComparisonResponse,
    ComparisonRowRead,
    CoverageRead,
    ErrorStatsRead,
    GroupStatsRead,
    SafetyBufferRead,
)
from app.services import analysis_service, metrics

router = APIRouter(prefix="/analysis", tags=["Analysis"])

MAX_RANGE_DAYS = 62

SessionDep = Annotated[Session, Depends(get_session)]

StartDate = Annotated[date, Query(description="First delivery date", examples=["2026-01-01"])]
EndDate = Annotated[date, Query(description="Last delivery date, inclusive", examples=["2026-01-31"])]
CutoffTime = Annotated[time, Query(description="Decision cutoff, UTC time of day", examples=["09:00"])]
DaysBefore = Annotated[int, Query(ge=0, le=7, description="Cutoff is this many days before delivery")]


def _validate_range(start_date: date, end_date: date) -> None:
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    if (end_date - start_date).days + 1 > MAX_RANGE_DAYS:
        raise HTTPException(status_code=422, detail=f"Date range cannot exceed {MAX_RANGE_DAYS} days")


@router.get("/forecast-vs-actual", response_model=ComparisonResponse)
def forecast_vs_actual(
    session: SessionDep,
    start_date: StartDate,
    end_date: EndDate,
    cutoff_time: CutoffTime = time(9, 0),
    days_before: DaysBefore = 1,
):
    """For every hour: the forecast available at the decision cutoff, the actual, and the error.

    Reads stored data only. Load it first with POST /fuelhh/sync and POST /windfor/sync.
    """
    _validate_range(start_date, end_date)
    result = analysis_service.compare_forecast_to_actual(
        session, start_date, end_date, cutoff_time, days_before
    )
    return ComparisonResponse(
        start_date=start_date,
        end_date=end_date,
        cutoff_time=cutoff_time.strftime("%H:%M"),
        days_before=days_before,
        coverage=CoverageRead.model_validate(result.coverage),
        warnings=analysis_service.coverage_warnings(result.coverage),
        rows=[ComparisonRowRead.model_validate(r) for r in result.rows],
    )


@router.get("/accuracy", response_model=AccuracyResponse)
def accuracy(
    session: SessionDep,
    start_date: StartDate,
    end_date: EndDate,
    cutoff_time: CutoffTime = time(9, 0),
    days_before: DaysBefore = 1,
    confidence: Annotated[
        float, Query(gt=0, lt=1, description="Coverage level for the safety buffer, e.g. 0.95")
    ] = 0.95,
    mape_floor_mw: Annotated[
        float, Query(ge=0, description="Hours with actual below this are skipped in the % error")
    ] = metrics.DEFAULT_MAPE_FLOOR_MW,
    horizon_bucket_hours: Annotated[int, Query(ge=1, le=24)] = 6,
):
    """How wrong the decision-time forecasts were, in numbers.

    error = forecast - actual, so a positive bias means forecasts ran high (the buyer under-buys).
    The safety buffer is the confidence-quantile of the signed error: hold this much extra supply
    to be covered against a wind shortfall in that share of hours.
    """
    _validate_range(start_date, end_date)
    result = analysis_service.compare_forecast_to_actual(
        session, start_date, end_date, cutoff_time, days_before
    )

    overall = metrics.compute_error_stats(result.rows, mape_floor_mw)
    buffer = metrics.safety_buffer(result.rows, confidence)

    return AccuracyResponse(
        start_date=start_date,
        end_date=end_date,
        cutoff_time=cutoff_time.strftime("%H:%M"),
        days_before=days_before,
        mape_floor_mw=mape_floor_mw,
        coverage=CoverageRead.model_validate(result.coverage),
        warnings=analysis_service.coverage_warnings(result.coverage),
        overall=ErrorStatsRead.model_validate(overall) if overall else None,
        safety_buffer=SafetyBufferRead.model_validate(buffer) if buffer else None,
        by_hour_of_day=[GroupStatsRead.model_validate(g) for g in metrics.by_hour_of_day(result.rows)],
        by_day=[GroupStatsRead.model_validate(g) for g in metrics.by_day(result.rows)],
        by_horizon=[
            GroupStatsRead.model_validate(g) for g in metrics.by_horizon(result.rows, horizon_bucket_hours)
        ],
    )
