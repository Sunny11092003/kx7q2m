# UK Day-Ahead Wind Forecast Monitor

A web app for a UK utility's day-ahead power buying team. It shows the latest
wind forecast available at decision time and quantifies how accurate those
forecasts have been, using national wind data from Elexon (January 2026).

- **Live app:** [frontend URL]
- **API:** [backend URL]/docs
- **Demo video:** [unlisted YouTube link]

## What it does
1. **Decision view:** for a chosen delivery day, shows the latest forecast
   published before the D-1 decision cutoff, with actuals overlaid and a
   bias-adjusted planning line.
2. **Forecast accuracy:** MAE, RMSE, bias and MAPE for the month, daily error,
   error by forecast lead time, and the error distribution.

## Data
- Actuals: Elexon `FUELHH`, `fuelType = WIND` (30-minute resolution).
- Forecasts: Elexon `WINDFOR` (hourly targets, multiple publishes per target).
- Fetched once with `backend/app/fetch_data.py` and stored as CSV in
  `backend/data/`, so the deployed app does not depend on the live API.

## Method and assumptions
- **Forecast selection:** for each target hour, take the latest forecast whose
  `publishTime` is at or before the cutoff on the previous day. Default cutoff
  is 09:00 UTC (= UK time in January); it is configurable in the UI.
  [State how you verified the day-ahead gate closure time.]
- **Alignment:** forecasts are hourly, actuals are half-hourly, so actuals are
  averaged to hourly.
- **Cleaning:** forecasts with negative lead time (published after the target
  time) are dropped; duplicate actuals from overlapping fetch windows are removed.
- **Scope:** only delivery days in January 2026.
- **Metrics:** error = forecast - actual. MAE, RMSE, bias (mean error), MAPE.
- **Bias adjustment:** uses the January mean bias, so it is in-sample and
  illustrative, not a validated correction.

## Key finding
At the 09:00 cutoff the forecast over-predicted wind by about 1,850 MW on
average (about 16% of mean output), and error grows with lead time.
[Note what you checked about whether WINDFOR and FUELHH cover the same scope.]

## Architecture
React (Vite, Recharts) -> FastAPI (pandas) -> CSV files.
- `backend/app/core.py`: selection logic and metrics (unit-tested)
- `backend/app/main.py`: API endpoints
- `backend/tests/`: pytest tests
- `frontend/src/`: UI

## Run locally
```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
# frontend
cd frontend && npm install && npm run dev
```
Or with Docker: `docker compose up --build`, then open http://localhost:8080.

## Tests
`cd backend && python -m pytest -q`

## Deployment
Frontend and backend are deployed as two Vercel projects. The frontend reads
the API URL from `VITE_API_URL`.

## Use of AI
I used Claude (Anthropic) to help plan the approach, write code and debug.
I reviewed the data checks and results myself, including investigating the
forecast bias before reporting it. [Add anything specific you did yourself.]

## Limitations and next steps
Single month, national level only, in-sample bias estimate, and no probabilistic
(interval) forecasts.
