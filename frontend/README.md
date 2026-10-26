# Frontend (Next.js + React + TypeScript)

Dashboard for the Wind Forecast Monitor. It talks to the FastAPI backend and never computes statistics
itself: all numbers come from the API, the frontend only presents them. See the [root README](../README.md)
for the full picture.

## Run locally

```powershell
cd frontend
npm install
copy .env.example .env.local        # macOS/Linux: cp .env.example .env.local
npm run dev
```
Open http://localhost:3000. The backend must be running (default http://localhost:8000).

| Script | Purpose |
|---|---|
| `npm run dev` | development server |
| `npm run build` / `npm start` | production build and server |
| `npm run lint` | ESLint |
| `npx tsc --noEmit` | type-check |

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL. Baked in at build time, so set it before building (Vercel environment variable, or Docker build arg). |

## Flow

```
app/page.tsx
  └─ Dashboard (client component, owns the applied filters)
       ├─ FiltersBar        draft filters -> onApply(filters); presets, validation (Jan 2026 only)
       ├─ useAnalysis(filters)
       │     └─ loadAnalysis  -> fetchComparison + fetchAccuracy (main cutoff) + fetchAccuracy (compare cutoff)
       │                         in parallel; stale requests are aborted; old data stays visible while loading
       ├─ DataNotices       backend `warnings` (missing forecasts / actuals)
       ├─ KpiCards          MAE, bias, p95 error, safety buffer
       ├─ InsightsCard      plain-English sentences from lib/insights.ts
       ├─ ForecastChartCard actual vs decision-time forecast + error area, brush to zoom
       ├─ BreakdownCard     error by hour of day / day / forecast age
       ├─ CutoffComparisonCard  main cutoff vs comparison cutoff
       └─ MethodologyCard   how the numbers are calculated
```

States handled: first load (skeleton), refresh (previous data dimmed), API error (message + retry),
no scorable hours (empty notice), partial data (warning notice).

## Structure

```
src/
  app/                    layout.tsx, page.tsx, globals.css (design tokens, light/dark)
  components/dashboard/   feature components listed above
  components/ui/          Button, Card, Input, Select, Badge, Alert, Skeleton, SegmentedControl, Label
  hooks/use-analysis.ts   fetching with cancellation
  lib/
    api.ts                typed fetch helpers, FastAPI error parsing
    types.ts              response shapes (mirror backend/app/schemas/analysis.py)
    config.ts             API URL, date limits, cutoff and confidence options, chart colours
    format.ts             number / date formatting (UTC, so server and browser agree)
    insights.ts           derives the takeaway sentences from the numbers
    chart-data.ts         reshapes rows for Recharts
```

## Docker
`docker build --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 -t gridbricks-frontend .`
Uses a multi-stage build and Next's `standalone` output. Normally started through `docker compose` at the root.

## Deploy on Vercel
Import the repository, set **Root Directory** to `frontend`, add `NEXT_PUBLIC_API_URL` pointing at the deployed
backend, then deploy. Full steps are in [../DEPLOYMENT.md](../DEPLOYMENT.md).
