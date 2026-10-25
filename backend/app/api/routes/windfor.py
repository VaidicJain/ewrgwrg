from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import get_elexon_client
from app.db.session import get_session
from app.schemas.windfor import (
    WindForecastListResponse,
    WindForecastRead,
    WindForecastSyncResponse,
    WindForElexonRecord,
)
from app.services import windfor_service
from app.services.elexon_client import ElexonClient, ElexonError

router = APIRouter(prefix="/windfor", tags=["WINDFOR (forecast generation)"])

MAX_RANGE_DAYS = 62
MAX_RAW_WINDOW_HOURS = 72

SessionDep = Annotated[Session, Depends(get_session)]
ClientDep = Annotated[ElexonClient, Depends(get_elexon_client)]

StartDate = Annotated[date, Query(description="First TARGET date (YYYY-MM-DD)", examples=["2026-01-01"])]
EndDate = Annotated[date, Query(description="Last TARGET date, inclusive", examples=["2026-01-31"])]


def _validate_range(start_date: date, end_date: date) -> None:
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    if (end_date - start_date).days + 1 > MAX_RANGE_DAYS:
        raise HTTPException(status_code=422, detail=f"Date range cannot exceed {MAX_RANGE_DAYS} days")


@router.get("/raw", response_model=list[WindForElexonRecord], response_model_by_alias=True)
async def get_windfor_raw(
    client: ClientDep,
    publish_from: Annotated[datetime, Query(examples=["2025-12-31T00:00:00Z"])],
    publish_to: Annotated[datetime, Query(examples=["2025-12-31T06:00:00Z"])],
):
    """Debug endpoint: pass-through to Elexon, nothing is stored. Keep the window small."""
    if publish_to <= publish_from:
        raise HTTPException(status_code=422, detail="publish_to must be after publish_from")
    if publish_to - publish_from > timedelta(hours=MAX_RAW_WINDOW_HOURS):
        raise HTTPException(status_code=422, detail=f"Window cannot exceed {MAX_RAW_WINDOW_HOURS} hours")
    try:
        return await client.fetch_windfor(publish_from, publish_to)
    except ElexonError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/sync", response_model=WindForecastSyncResponse)
async def sync_windfor(
    session: SessionDep,
    client: ClientDep,
    start_date: StartDate,
    end_date: EndDate,
    lookback_days: Annotated[
        int,
        Query(ge=0, le=14, description="How many days BEFORE start_date to include forecasts published"),
    ] = 3,
):
    """Fetch every forecast published from (start_date - lookback_days) until the end of end_date.

    Forecasts for a target day are created in the days before it, so the publish window has to
    start earlier than the target dates. Existing rows are skipped.
    """
    _validate_range(start_date, end_date)
    publish_from = windfor_service.day_start(start_date) - timedelta(days=lookback_days)
    publish_to = windfor_service.day_start(end_date) + timedelta(days=1)
    try:
        result = await windfor_service.sync_windfor(session, client, publish_from, publish_to)
    except ElexonError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return WindForecastSyncResponse(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        publish_from=publish_from,
        publish_to=publish_to,
        fetched=result.fetched,
        inserted=result.inserted,
        skipped_existing=result.skipped_existing,
    )


@router.get("", response_model=WindForecastListResponse)
def list_windfor(
    session: SessionDep,
    start_date: StartDate,
    end_date: EndDate,
    publish_before: Annotated[
        datetime | None,
        Query(description="Only forecasts published at or before this time (the decision cutoff)"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=50_000)] = 10_000,
):
    """Stored forecasts for target dates in the range. Run POST /sync first to load data."""
    _validate_range(start_date, end_date)
    rows, truncated = windfor_service.query_windfor(session, start_date, end_date, publish_before, limit)
    return WindForecastListResponse(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        publish_before=publish_before,
        count=len(rows),
        truncated=truncated,
        data=[WindForecastRead.model_validate(r) for r in rows],
    )
