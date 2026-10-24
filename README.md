# UK Day-Ahead Wind Forecast Monitor

A web app for a UK energy utility's day-ahead power buying team. It shows the
latest wind forecast available at decision time, and it quantifies how accurate
those forecasts have been, so buyers can account for the error when deciding
how much thermal power to procure.

**Live app (Vercel):** https://frontend-iota-three-7avnc1x118.vercel.app/
**API (Vercel), interactive docs:** https://backend-mxlp-rho.vercel.app/docs

## Scope

- National GB wind only, from Elexon: `FUELHH` (actuals, `fuelType = WIND`)
  and `WINDFOR` (forecasts).
- Purchase decisions for delivery days in **January 2026**.

## What the app does

1. **Decision view.** Pick a delivery day. The app shows the latest forecast
   published before the day-ahead cutoff (the day before), the actual
   generation for comparison, and a bias-adjusted planning line.
2. **Forecast accuracy.** For the whole month: MAE, RMSE, bias and MAPE, daily
   error, error by forecast lead time, and the distribution of errors.
3. **Cutoff selector.** The decision cutoff can be changed (06:00, 09:00,
   10:00, 12:00 UTC on the day before) to see how accuracy depends on how late
   the decision is made.

## Files and directories

```
.
├── backend/
│   ├── app/
│   │   ├── core.py          # data cleaning, forecast selection, metrics
│   │   ├── main.py          # FastAPI app and endpoints
│   │   ├── fetch_data.py    # downloads Elexon data to CSV
│   │   ├── explore.py       # data exploration script
│   │   ├── check.py         # end-to-end check of selection + metrics
│   │   └── diagnose.py      # bias diagnostics (time-shift, cutoff sensitivity)
│   ├── api/index.py         # Vercel entrypoint (exposes the FastAPI app)
│   ├── data/                # actuals.csv, forecasts.csv (Elexon extracts)
│   ├── tests/test_core.py   # pytest unit tests
│   ├── Dockerfile
│   ├── vercel.json
│   ├── requirements.txt         # runtime dependencies
│   └── requirements-dev.txt     # adds test and data-fetch dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # UI: decision view and accuracy view
│   │   ├── api.js           # fetch helper (reads VITE_API_URL)
│   │   ├── main.jsx         # React entry point
│   │   └── index.css        # styles
│   ├── Dockerfile           # multi-stage build, served by nginx
│   ├── nginx.conf           # serves the app and proxies /api to the backend
│   └── vite.config.js       # dev proxy for /api
├── docker-compose.yml
└── README.md
```

## How to start the application

### Option 1: Docker (recommended)

Requires Docker Desktop.

```bash
docker compose up --build
```

Open http://localhost:8080.

### Option 2: Run locally without Docker

Requires Python 3.10+ and Node 18+.

Backend:

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux:        source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Frontend (second terminal):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server proxies `/api` to the backend on
port 8000.

### Refreshing the data (optional)

The CSV files in `backend/data/` are already included, so the app does not call
the Elexon API at runtime. To re-download:

```bash
cd backend
python -m app.fetch_data
```

### Tests

```bash
cd backend
python -m pytest -q
```

## API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/forecast?day=YYYY-MM-DD&cutoff=9` | Hourly forecast selected at the cutoff, with actuals and error |
| `GET /api/accuracy?cutoff=9` | Summary metrics, daily error, and error list |
| `GET /api/accuracy/by-horizon?bin_h=4&max_h=48` | Error by forecast lead time |
| `GET /api/health` | Health check |

## Method

**Forecast selection.** For each target hour, the app takes the latest forecast
whose `publishTime` is at or before the cutoff on the day before delivery.
The cutoff defaults to 09:00 UTC (which equals UK time in January) and is
configurable in the UI. Selected forecasts have lead times of roughly 16 to 40
hours. All 744 January delivery hours have a forecast.

**Data cleaning.**
- Overlapping download windows created duplicate actual rows; these are
  removed, keeping the latest published value per half-hour.
- `WINDFOR` contains rows whose publish time is after the target time
  (negative lead time). These are not forecasts and are dropped.
- Forecast targets are hourly while actuals are half-hourly, so actuals are
  averaged to hourly before comparison.

**Metrics.** Error is forecast minus actual (positive means over-forecast).
- MAE: mean absolute error
- RMSE: root mean squared error (penalises large misses)
- Bias: mean error
- MAPE: mean absolute percentage error (hours with zero actual excluded)
- Error by lead time: errors grouped into 4-hour bins of
  (`startTime` - `publishTime`), shown up to 48 hours

## Key findings (January 2026, 09:00 UTC cutoff)

| Metric | Value |
|---|---|
| MAE | about 2,140 MW |
| RMSE | about 2,610 MW |
| Bias | about +1,850 MW (forecast too high) |
| MAPE | about 22% |

- The forecast over-predicts wind by about 16% of mean actual output, so a buyer
  relying on the raw forecast would systematically under-buy thermal power.
- Error grows with lead time (from about 1,800 MW MAE for the freshest
  forecasts to about 2,400 MW at two days out).
- A later cutoff improves accuracy (for example 12:00 UTC gives MAE of about
  2,020 MW), which shows the value of later information. 12:00 UTC is a
  what-if, since it is probably later than the real day-ahead decision point.

I checked that the bias is not caused by a time-alignment mistake: shifting
the actuals by up to 3 hours in either direction leaves the bias essentially
unchanged, and it is stable across cutoffs.


## Deployment

The frontend and backend are deployed as two separate Vercel projects from the
same repository (root directories `frontend` and `backend`). The frontend reads
the backend URL from the `VITE_API_URL` build-time environment variable.
Docker files are provided for local and containerised runs.

## Use of AI

I used AI tools (Claude, by Anthropic) to help plan the approach, write and
debug code, and draft documentation.
