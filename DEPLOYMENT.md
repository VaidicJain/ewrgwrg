# Deployment (Vercel)

Two Vercel projects from the same GitHub repository:

| Project | Root Directory | What it is |
|---|---|---|
| `<name>-api` | `backend` | FastAPI, served as a single Vercel Function |
| `<name>-web` | `frontend` | Next.js app |

Deploy the **backend first**, because the frontend needs its URL.

## 0. Before you start
- The code is pushed to GitHub. `backend/gridbricks.db` must be committed (check with
  `git ls-files backend/gridbricks.db`). GitHub rejects files over 100 MB, so check its size first.
- You have a Vercel account connected to GitHub.

## 1. Backend project
1. Vercel dashboard -> **Add New -> Project** -> import the repository.
2. **Root Directory:** `backend`. Framework preset: leave on auto-detected (FastAPI) or "Other".
   The entrypoint is declared in `backend/pyproject.toml` (`[tool.vercel] entrypoint = "app.main:app"`).
3. **Environment Variables** (Production):

   | Name | Value |
   |---|---|
   | `DATABASE_URL` | `sqlite:////tmp/gridbricks.db` |
   | `CORS_ORIGINS` | `["http://localhost:3000"]` for now (updated in step 3) |

   Vercel's filesystem is read-only except `/tmp`. On the first request the app copies the committed
   `gridbricks.db` into `/tmp` and uses it from there.
4. Deploy. Then verify in a browser:
   - `https://<backend-url>/health` -> `{"status":"ok"}`
   - `https://<backend-url>/docs` loads
   - `https://<backend-url>/api/v1/analysis/accuracy?start_date=2026-01-01&end_date=2026-01-31`
     returns numbers (not an empty `overall`). If `overall` is `null` or warnings say there are no
     forecasts, the database file was not bundled: see Troubleshooting.

## 2. Frontend project
1. **Add New -> Project** -> same repository again.
2. **Root Directory:** `frontend`. Framework: Next.js (auto-detected).
3. **Environment Variables:** `NEXT_PUBLIC_API_URL` = the backend URL, e.g. `https://<backend-url>`
   (no trailing slash needed).
4. Deploy and note the frontend URL.

## 3. Connect them (CORS)
1. Backend project -> Settings -> Environment Variables -> edit `CORS_ORIGINS` to
   `["https://<your-frontend>.vercel.app"]` (keep `"http://localhost:3000"` in the list if you still want local dev).
2. **Redeploy the backend** (env changes apply only to new deployments).
3. Open the frontend URL, apply a filter, and confirm charts load with no CORS error in the browser console.

If you later change `NEXT_PUBLIC_API_URL`, redeploy the frontend too: it is compiled into the build.

## 4. Final check (the brief asks for this)
Open the frontend URL, the backend `/docs` URL, the GitHub repo and the YouTube video in an **incognito window**
and confirm each works without logging in. Vercel "Deployment Protection" can put a login wall in front of
preview URLs; use the **production** domain (Settings -> Domains) and, if it asks for login, disable Deployment
Protection for the project (Settings -> Deployment Protection).

## Troubleshooting
| Symptom | Likely cause / fix |
|---|---|
| Frontend shows "Cannot reach the API" | Wrong `NEXT_PUBLIC_API_URL`, or frontend not redeployed after changing it. |
| Browser console: CORS error | Frontend origin missing in `CORS_ORIGINS`, or backend not redeployed after editing it. |
| API works but `overall` is null | `gridbricks.db` not in the deployment. Confirm it is committed and not git-ignored (`.gitignore` has an exception for it), and the backend Root Directory is `backend`. |
| 500 on first request | Open the function logs in Vercel (Deployments -> Functions/Logs) to see the traceback. |
| Backend build fails on dependencies | Vercel installs from `pyproject.toml`/`requirements.txt`; run `pip install -r requirements.txt` locally on Python 3.12 to reproduce. |
| Data changes disappear | Expected: `/tmp` is temporary on Vercel. The committed database is the source of truth. |
