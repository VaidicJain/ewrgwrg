# Backend (FastAPI)

Wind generation monitoring API built on Elexon BMRS data (FUELHH actuals, WINDFOR forecasts).
For the big picture see the [root README](../README.md).

## Run locally

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env              # macOS/Linux: cp .env.example .env
uvicorn app.main:app --reload
```

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

With Docker: `docker build -t gridbricks-backend . && docker run -p 8000:8000 gridbricks-backend`
(or `docker compose up` from the repository root).

## Configuration (environment variables / `.env`)

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./gridbricks.db` | SQLAlchemy URL. Any supported database works. |
| `SEED_DB_PATH` | `backend/gridbricks.db` | Dataset copied to the SQLite path on first start if that path is empty (Docker volume, Vercel `/tmp`). |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | JSON list of allowed browser origins. Add the deployed frontend URL. |
| `ELEXON_BASE_URL` | Elexon BMRS v1 | Upstream API. |
| `ELEXON_TIMEOUT_SECONDS`, `ELEXON_MAX_RETRIES` | `30`, `3` | Upstream call behaviour (retries use exponential back-off). |
| `ELEXON_CHUNK_DAYS`, `ELEXON_WINDFOR_CHUNK_DAYS` | `7`, `1` | How large date ranges are split per Elexon request. |

## Tests

```powershell
python -m pytest
```
Elexon is faked and the database is in memory, so tests never touch the network or the real data file.

## Structure

```
app/
  main.py              FastAPI app, CORS, startup (creates tables)
  core/config.py       Settings (pydantic-settings)
  db/session.py        Engine, session dependency, first-start database seeding
  models/              SQLModel tables
  schemas/             Pydantic models: Elexon payloads and API responses
  services/
    elexon_client.py   HTTP client: retries, chunked requests, de-duplication
    fuelhh_service.py  Sync + query actuals
    windfor_service.py Sync + query forecasts
    selection.py       PURE: which forecast was available at the decision cutoff
    metrics.py         PURE: MAE, RMSE, bias, percentiles, MAPE, safety buffer, breakdowns
    analysis_service.py Loads stored data and calls the pure logic
  api/routes/          health, fuelhh, windfor, analysis
  scripts/seed.py      Fetch January 2026 from Elexon into the database
tests/                 selection, metrics, API, sync and seed tests
```

## Endpoints (`/api/v1`)

### Actuals: FUELHH
| Method | Path | Purpose |
|---|---|---|
| GET | `/fuelhh/raw` | Pass-through to Elexon (debug, nothing stored) |
| POST | `/fuelhh/sync` | Fetch from Elexon and upsert into the database |
| GET | `/fuelhh` | Stored actuals; fetches first if empty, `refresh=true` forces a re-fetch |

Params: `start_date`, `end_date` (YYYY-MM-DD, inclusive, max 62 days), `fuel_type` (default `WIND`).

### Forecasts: WINDFOR
| Method | Path | Purpose |
|---|---|---|
| GET | `/windfor/raw` | Pass-through to Elexon for a publish-time window (max 72 h) |
| POST | `/windfor/sync` | Fetch all forecasts published from `start_date - lookback_days` to end of `end_date` |
| GET | `/windfor` | Stored forecasts for target dates; optional `publish_before` = decision cutoff |

### Analysis
| Method | Path | Purpose |
|---|---|---|
| GET | `/analysis/forecast-vs-actual` | One row per hour: forecast at cutoff, actual, error, forecast age |
| GET | `/analysis/accuracy` | Overall stats, safety buffer, and breakdowns by hour of day, day and forecast age |

Common params: `start_date`, `end_date`, `cutoff_time` (UTC, default `09:00`), `days_before` (default `1`).
`/accuracy` also takes `confidence` (default `0.95`), `mape_floor_mw` and `horizon_bucket_hours`.

Responses include `coverage` (hours with a forecast, an actual, both) and human-readable `warnings`.

## Method

- Forecast for target hour H on day D = the one with the latest `publishTime` **<=** the cutoff on `D - days_before`.
- Hourly actual = mean of the two half-hours; an hour missing one half is treated as having no actual.
- `error = forecast - actual`. Positive = over-forecast = the buyer would under-buy.
- Safety buffer = the `confidence` quantile of the signed error, floored at 0.
- Percentage error ignores hours whose actual is below `mape_floor_mw` (default 1000 MW).

## Elexon quirks handled

- `settlementDate*` and `publishDateTime*` filters cannot be combined (HTTP 400), so actuals are fetched by
  settlement date and forecasts by publish time.
- WINDFOR returns only the latest forecast unless a publish-time window is supplied; the client always sends one
  and splits long ranges into one-day chunks.
- Transient errors (429/5xx, network) are retried with exponential back-off; 4xx errors fail immediately.
