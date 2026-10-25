from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import get_elexon_client
from app.db.session import get_session
from app.schemas.fuelhh import (
    FuelHHElexonRecord,
    FuelHHListResponse,
    FuelHHRead,
    FuelHHSyncResponse,
)
from app.services import fuelhh_service
from app.services.elexon_client import ElexonClient, ElexonError

router = APIRouter(prefix="/fuelhh", tags=["FUELHH (actual generation)"])

MAX_RANGE_DAYS = 62

SessionDep = Annotated[Session, Depends(get_session)]
ClientDep = Annotated[ElexonClient, Depends(get_elexon_client)]

StartDate = Annotated[date, Query(description="First settlement date (YYYY-MM-DD)", examples=["2026-01-01"])]
EndDate = Annotated[date, Query(description="Last settlement date, inclusive", examples=["2026-01-31"])]
FuelType = Annotated[str, Query(description="Elexon fuel type, e.g. WIND")]


def _validate_range(start_date: date, end_date: date) -> None:
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    if (end_date - start_date).days + 1 > MAX_RANGE_DAYS:
        raise HTTPException(status_code=422, detail=f"Date range cannot exceed {MAX_RANGE_DAYS} days")


@router.get("/raw", response_model=list[FuelHHElexonRecord], response_model_by_alias=True)
async def get_fuelhh_raw(
    client: ClientDep,
    start_date: StartDate,
    end_date: EndDate,
    fuel_type: FuelType = "WIND",
):
    """Debug endpoint: pass-through to Elexon, nothing is stored."""
    _validate_range(start_date, end_date)
    try:
        return await client.fetch_fuelhh(start_date, end_date, [fuel_type.upper()])
    except ElexonError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/sync", response_model=FuelHHSyncResponse)
async def sync_fuelhh(
    session: SessionDep,
    client: ClientDep,
    start_date: StartDate,
    end_date: EndDate,
    fuel_type: FuelType = "WIND",
):
    """Fetch actuals from Elexon and upsert them into the local database."""
    _validate_range(start_date, end_date)
    fuel_type = fuel_type.upper()
    try:
        result = await fuelhh_service.sync_fuelhh(session, client, start_date, end_date, fuel_type)
    except ElexonError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return FuelHHSyncResponse(
        fuel_type=fuel_type,
        start_date=start_date,
        end_date=end_date,
        fetched=result.fetched,
        inserted=result.inserted,
        updated=result.updated,
    )


@router.get("", response_model=FuelHHListResponse)
async def list_fuelhh(
    session: SessionDep,
    client: ClientDep,
    start_date: StartDate,
    end_date: EndDate,
    fuel_type: FuelType = "WIND",
    refresh: Annotated[bool, Query(description="Force re-fetch from Elexon")] = False,
):
    """Return stored actuals. Fetches from Elexon first if nothing is stored for the range."""
    _validate_range(start_date, end_date)
    fuel_type = fuel_type.upper()

    rows = fuelhh_service.query_fuelhh(session, start_date, end_date, fuel_type)
    if refresh or not rows:
        try:
            await fuelhh_service.sync_fuelhh(session, client, start_date, end_date, fuel_type)
        except ElexonError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        rows = fuelhh_service.query_fuelhh(session, start_date, end_date, fuel_type)

    return FuelHHListResponse(
        fuel_type=fuel_type,
        start_date=start_date,
        end_date=end_date,
        count=len(rows),
        data=[FuelHHRead.model_validate(r) for r in rows],
    )
