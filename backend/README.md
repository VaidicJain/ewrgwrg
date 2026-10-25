# Backend (FastAPI)

Wind generation monitoring API built on Elexon BMRS data.

## Run locally (Windows PowerShell)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Tests

```powershell
python -m pytest
```

## Structure

```
app/
  main.py            FastAPI app, CORS, startup
  core/config.py     Settings from env / .env (pydantic-settings)
  db/session.py      SQLModel engine, session dependency, table creation
  models/            SQLModel tables (database)
  schemas/           Pydantic models (Elexon payloads, API responses)
  services/          Elexon HTTP client, business logic
  api/routes/        Routers (health, fuelhh)
tests/               pytest, Elexon is faked so tests never hit the network
```

## FUELHH endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/fuelhh/raw` | Pass-through to Elexon (debug, nothing stored) |
| POST | `/api/v1/fuelhh/sync` | Fetch from Elexon and upsert into the database |
| GET | `/api/v1/fuelhh` | Stored actuals; fetches first if empty, `refresh=true` forces a re-fetch |

Query params: `start_date`, `end_date` (YYYY-MM-DD, inclusive, max 62 days), `fuel_type` (default `WIND`).

Elexon quirk: `settlementDate*` and `publishDateTime*` filters cannot be combined (HTTP 400),
so actuals are always fetched by settlement date.
