# Wind Forecast Monitor

A web app that helps a UK power buyer decide how much electricity to buy on the **day-ahead market**.
It shows which wind-generation forecast was actually available at decision time, compares it with what
really happened, and turns the difference into numbers a buyer can plan around (average error, bias,
worst-case error and a "safety buffer").

Data: Elexon BMRS, national GB wind only, purchase decisions for **January 2026**.

| | |
|---|---|
| Live app | `<ADD VERCEL FRONTEND URL>` |
| Live API docs | `<ADD VERCEL BACKEND URL>/docs` |
| Demo video | `<ADD UNLISTED YOUTUBE URL>` |

## The problem in one paragraph

The buyer must commit to a day-ahead purchase one day before delivery. Whatever wind will not cover has to
be bought elsewhere (for example thermal plants). Wind output depends on weather, so the buyer relies on
Elexon's wind forecasts (WINDFOR). The question is not "how good are forecasts in general?" but
**"how good was the forecast I could actually see when I had to decide?"** Forecasts published after the
decision are useless for that decision, so they are ignored.

## Approach

1. **Collect** two Elexon datasets for January 2026 and store them locally:
   - `FUELHH` (actuals): half-hourly generation, filtered to `fuelType = WIND`.
   - `WINDFOR` (forecasts): for each target time there are many forecasts, each with its own `publishTime`.
2. **Pick the right forecast.** For a delivery hour on day D, the decision cutoff is a time of day on D-1
   (default 09:00 UTC, adjustable in the UI). The forecast used is the one with the **latest `publishTime`
   at or before that cutoff**.
3. **Put both on the same footing.** Forecasts and actuals are compared per hour; an hourly actual is the mean
   of its two half-hours. An hour with a missing half-hour is skipped rather than guessed.
4. **Score it.** `error = forecast - actual`. Positive means the forecast was too high (the buyer under-buys).
   From the errors the backend computes MAE, RMSE, bias, median / p90 / p95 / max absolute error, MAPE (with
   a floor so near-zero hours don't distort it), a safety buffer at 90/95/99 % confidence, and breakdowns by
   hour of day, by day and by forecast age.
5. **Present it.** The React dashboard shows KPIs, plain-English takeaways, a forecast-vs-actual chart, an
   error chart, breakdowns, and a comparison of two different decision cutoffs ("does deciding later help?").

### Assumptions (also worth stating in the video)
- All times are UTC. Elexon `startTime` and `publishTime` are UTC.
- The default cutoff of 09:00 UTC on the day before delivery is an assumption; the brief doesn't give a
  gate-closure time, so it is a user-selectable filter (06:00-14:00).
- Safety buffer = the chosen percentile of the over-forecast error. It describes past performance, not a
  guarantee.

## How it works end to end

```
 Elexon BMRS API                      one-off seeding (app/scripts/seed.py)
 FUELHH / WINDFOR  ───────────────►  SQLite file  backend/gridbricks.db  (committed to the repo)
                                              │
                                              ▼
 Browser (React / Next.js)  ◄── JSON ──  FastAPI backend
   Filters bar ──► useAnalysis hook ──► GET /api/v1/analysis/forecast-vs-actual
   KPI cards, charts, insights          GET /api/v1/analysis/accuracy   (once per cutoff)
                                              │
                         selection.py (pick forecast) ─► metrics.py (score it)
```

**Request flow for one dashboard view**
1. The user picks a period, cutoff, comparison cutoff and confidence in `FiltersBar`.
2. `Dashboard` stores the applied filters; `useAnalysis` fires three requests in parallel (comparison rows,
   accuracy at the main cutoff, accuracy at the comparison cutoff) and cancels stale ones with `AbortController`.
3. FastAPI loads stored forecasts published before the latest cutoff and the stored actuals,
   `selection.build_comparison` pairs them per hour, and `metrics` computes the statistics.
4. The frontend renders KPIs, `buildInsights` turns the numbers into sentences, and Recharts draws the charts.
   Missing data comes back as `warnings` and is shown in a notice instead of being hidden.

**Why the data is stored locally.** Elexon's WINDFOR stream returns only the latest forecast unless a publish-time
window is given, and holding many forecasts per target time is exactly what the analysis needs. Loading it once
into SQLite makes every request fast and keeps the deployed demo independent of Elexon's availability. The
seeded database is committed (`backend/gridbricks.db`) for that reason.

## Repository layout

```
.
├── README.md                this file
├── docker-compose.yml       runs backend + frontend together
├── backend/                 FastAPI service (Python)
│   ├── Dockerfile
│   ├── pyproject.toml / requirements.txt / uv.lock
│   ├── gridbricks.db        seeded January 2026 dataset
│   ├── app/
│   │   ├── main.py          app factory, CORS, startup
│   │   ├── core/config.py   settings from environment / .env
│   │   ├── db/session.py    engine, session dependency, first-start DB seeding
│   │   ├── models/          SQLModel tables (FUELHH actuals, WINDFOR forecasts)
│   │   ├── schemas/         Pydantic models (Elexon payloads, API responses)
│   │   ├── services/
│   │   │   ├── elexon_client.py   HTTP client with retries and chunking
│   │   │   ├── fuelhh_service.py / windfor_service.py   sync + query
│   │   │   ├── selection.py       pure logic: which forecast was available at cutoff
│   │   │   ├── metrics.py         pure logic: error statistics
│   │   │   └── analysis_service.py glue between DB and the pure logic
│   │   ├── api/routes/      health, fuelhh, windfor, analysis
│   │   └── scripts/seed.py  load Elexon data into the DB
│   └── tests/               pytest; Elexon is faked, no network
└── frontend/                Next.js + React + TypeScript + Tailwind + Recharts
    ├── Dockerfile
    └── src/
        ├── app/             layout, page
        ├── components/dashboard/   dashboard, filters, KPI cards, charts, insights, notices, methodology
        ├── components/ui/          small shared UI primitives
        ├── hooks/use-analysis.ts   data loading with cancellation
        └── lib/                    api client, types, formatting, insight text, config
```

## Run it

### Option A: Docker (recommended)
Requires Docker Desktop.

```bash
docker compose up --build
```

- App: http://localhost:3000
- API docs: http://localhost:8000/docs

Stop with `Ctrl+C`; `docker compose down` removes containers (add `-v` to also reset the database volume).
The first start copies the shipped dataset into the `gridbricks-data` volume.

### Option B: without Docker

Backend (Python 3.11+):
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env              # macOS/Linux: cp .env.example .env
uvicorn app.main:app --reload
```

Frontend (Node 20+), in a second terminal:
```powershell
cd frontend
npm install
copy .env.example .env.local        # macOS/Linux: cp .env.example .env.local
npm run dev
```
Open http://localhost:3000.

### Re-fetching data from Elexon (optional)
```powershell
cd backend
python -m app.scripts.seed --start 2026-01-01 --end 2026-01-31
```
Safe to repeat; rows are updated or skipped, never duplicated.

## Tests
```powershell
cd backend && python -m pytest          # selection, metrics, API and sync behaviour
cd frontend && npm run lint && npx tsc --noEmit
```

## API summary
Base path `/api/v1`; interactive docs at `/docs`. See [backend/README.md](backend/README.md) for details.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness check |
| GET / POST | `/fuelhh`, `/fuelhh/sync`, `/fuelhh/raw` | actuals |
| GET / POST | `/windfor`, `/windfor/sync`, `/windfor/raw` | forecasts |
| GET | `/analysis/forecast-vs-actual` | per-hour forecast at cutoff, actual and error |
| GET | `/analysis/accuracy` | error statistics, safety buffer and breakdowns |

## Deployment
Frontend and backend are two separate Vercel projects from this one repository (root directories `frontend`
and `backend`). See [DEPLOYMENT.md](DEPLOYMENT.md).

## Key decisions
- **Pure logic is separated from I/O.** `selection.py` and `metrics.py` have no database or HTTP code, so they are
  tested directly with small hand-made cases.
- **Data is stored, not fetched per request.** Fast, repeatable, and independent of the upstream API.
- **Honest about gaps.** Hours without a forecast or a complete actual are excluded and reported, never filled.
- **SQLite by default, one URL to change.** `DATABASE_URL` can point to Postgres without code changes.

## Known limitations
- Hourly resolution only; forecasts or actuals at other granularity are aggregated to hours.
- SQLite on Vercel lives in `/tmp`, so any data synced at runtime is temporary; the committed dataset is what
  the live app serves.
- No authentication; the dataset is public.

## AI tools used
This project was built with the help of **Claude (Anthropic)** for planning, code generation and review. All code was
read, run and tested by the author, who is responsible for it.
