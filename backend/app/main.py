import pandas as pd
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from app.core import prepare, latest_forecast_at_cutoff, metrics, error_by_horizon

DATA = Path(__file__).parent.parent / "data"
LO = pd.Timestamp("2026-01-01", tz="UTC")
HI = pd.Timestamp("2026-02-01", tz="UTC")

app = FastAPI(title="Wind forecast accuracy API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

A, F = prepare(pd.read_csv(DATA / "actuals.csv"),
               pd.read_csv(DATA / "forecasts.csv"))

def _jan(df):
    return df[(df.startTime >= LO) & (df.startTime < HI)]

def _selected(cutoff):
    return _jan(latest_forecast_at_cutoff(F, cutoff)).merge(A, on="startTime", how="left")

def _clean(df):
    return df.astype(object).where(df.notna(), None).to_dict("records")

@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/forecast")
def forecast(day: str = Query(..., description="YYYY-MM-DD, a January 2026 delivery day"),
             cutoff: float = 9.0):
    d = pd.Timestamp(day, tz="UTC")
    if not (LO <= d < HI):
        raise HTTPException(400, "day must be in January 2026")
    s = _selected(cutoff)
    s = s[(s.startTime >= d) & (s.startTime < d + pd.Timedelta(days=1))].copy()
    s["error"] = s.forecast - s.actual
    s["startTime"] = s.startTime.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    s["publishTime"] = s.publishTime.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"day": day, "cutoff_hour_utc": cutoff,
            "points": _clean(s[["startTime", "publishTime", "horizon_h", "forecast", "actual", "error"]])}

@app.get("/api/accuracy")
def accuracy(cutoff: float = 9.0):
    s = _selected(cutoff).dropna(subset=["actual"]).copy()
    s["day"] = s.startTime.dt.strftime("%Y-%m-%d")
    s["err"] = s.forecast - s.actual
    daily = (s.groupby("day")
              .agg(mae=("err", lambda x: x.abs().mean()),
                   bias=("err", "mean"),
                   mean_actual=("actual", "mean"))
              .reset_index())
    return {"cutoff_hour_utc": cutoff, "summary": metrics(s), "daily": _clean(daily),
            "errors": [round(float(e)) for e in s.err]}

@app.get("/api/accuracy/by-horizon")
def by_horizon(bin_h: int = 4, max_h: int = 48):
    fj = _jan(F)
    out = error_by_horizon(fj, A, bin_h)
    return _clean(out[out.horizon_bin < max_h])