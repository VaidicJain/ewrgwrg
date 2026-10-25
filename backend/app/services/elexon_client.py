import asyncio
import logging
from datetime import UTC, date, datetime, timedelta

import httpx

from app.core.config import get_settings
from app.schemas.fuelhh import FuelHHElexonRecord
from app.schemas.windfor import WindForElexonRecord

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class ElexonError(Exception):
    """Raised when the Elexon API cannot give us usable data."""


def _iso_z(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class ElexonClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        chunk_days: int = 7,
        windfor_chunk_days: int = 1,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.chunk_days = max(1, chunk_days)
        self.windfor_chunk_days = max(1, windfor_chunk_days)

    async def _get_json(self, client: httpx.AsyncClient, path: str, params: dict) -> list[dict]:
        url = f"{self.base_url}{path}"
        last_error = "unknown error"

        for attempt in range(self.max_retries + 1):
            try:
                response = await client.get(url, params=params, headers={"Accept": "application/json"})
            except httpx.TransportError as exc:
                last_error = f"network error: {exc!r}"
            else:
                if response.status_code == 200:
                    payload = response.json()
                    # Stream endpoints return a bare JSON array; tolerate {"data": [...]} too.
                    if isinstance(payload, dict):
                        payload = payload.get("data", [])
                    return payload
                if response.status_code not in RETRYABLE_STATUS:
                    # 400 etc: our request is wrong, retrying will not help.
                    raise ElexonError(f"Elexon returned {response.status_code}: {response.text[:300]}")
                last_error = f"Elexon returned {response.status_code}"

            if attempt < self.max_retries:
                delay = 2**attempt
                logger.warning("Elexon call failed (%s); retrying in %ss", last_error, delay)
                await asyncio.sleep(delay)

        raise ElexonError(f"Elexon request failed after retries: {last_error}")

    # ---------------------------------------------------------------- FUELHH (actuals)

    def _date_chunks(self, start: date, end: date) -> list[tuple[date, date]]:
        chunks = []
        cursor = start
        while cursor <= end:
            chunk_end = min(cursor + timedelta(days=self.chunk_days - 1), end)
            chunks.append((cursor, chunk_end))
            cursor = chunk_end + timedelta(days=1)
        return chunks

    async def fetch_fuelhh(
        self, start_date: date, end_date: date, fuel_types: list[str]
    ) -> list[FuelHHElexonRecord]:
        """Fetch FUELHH actuals by settlement date.

        Note: Elexon rejects requests that mix settlementDate* with publishDateTime* (HTTP 400),
        so we only ever use settlement dates here.
        """
        records: dict[tuple[str, object], FuelHHElexonRecord] = {}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for chunk_start, chunk_end in self._date_chunks(start_date, end_date):
                params = {
                    "settlementDateFrom": chunk_start.isoformat(),
                    "settlementDateTo": chunk_end.isoformat(),
                    "fuelType": fuel_types,  # httpx repeats the key for lists
                }
                rows = await self._get_json(client, "/datasets/FUELHH/stream", params)
                for row in rows:
                    record = FuelHHElexonRecord.model_validate(row)
                    # De-duplicate; if a slot repeats, keep the most recently published row.
                    key = (record.fuel_type, record.start_time)
                    existing = records.get(key)
                    if existing is None or record.publish_time >= existing.publish_time:
                        records[key] = record

        return sorted(records.values(), key=lambda r: r.start_time)

    # ---------------------------------------------------------------- WINDFOR (forecasts)

    def _datetime_chunks(self, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
        chunks = []
        step = timedelta(days=self.windfor_chunk_days)
        cursor = start
        while cursor < end:
            chunk_end = min(cursor + step, end)
            chunks.append((cursor, chunk_end))
            cursor = chunk_end
        return chunks

    async def fetch_windfor(self, publish_from: datetime, publish_to: datetime) -> list[WindForElexonRecord]:
        """Fetch every WINDFOR forecast published inside [publish_from, publish_to].

        Without publish filters Elexon returns only the latest forecast, so a window is always sent.
        The same (startTime, publishTime) pair is never returned twice.
        """
        records: dict[tuple[datetime, datetime], WindForElexonRecord] = {}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for chunk_from, chunk_to in self._datetime_chunks(publish_from, publish_to):
                params = {
                    "publishDateTimeFrom": _iso_z(chunk_from),
                    "publishDateTimeTo": _iso_z(chunk_to),
                }
                rows = await self._get_json(client, "/datasets/WINDFOR/stream", params)
                for row in rows:
                    record = WindForElexonRecord.model_validate(row)
                    if record.generation is None:
                        continue
                    records[(record.start_time, record.publish_time)] = record

        return sorted(records.values(), key=lambda r: (r.start_time, r.publish_time))


def build_elexon_client() -> ElexonClient:
    s = get_settings()
    return ElexonClient(
        base_url=s.elexon_base_url,
        timeout=s.elexon_timeout_seconds,
        max_retries=s.elexon_max_retries,
        chunk_days=s.elexon_chunk_days,
        windfor_chunk_days=s.elexon_windfor_chunk_days,
    )
