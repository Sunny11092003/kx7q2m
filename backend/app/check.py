import pandas as pd
from pathlib import Path
from app.core import prepare, latest_forecast_at_cutoff, metrics, error_by_horizon

DATA = Path(__file__).parent.parent / "data"
a, f = prepare(pd.read_parquet(DATA / "actuals.parquet"),
               pd.read_parquet(DATA / "forecasts.parquet"))

print("Forecast publish cadence (hours between publishes):")
pt = f.publishTime.drop_duplicates().sort_values()
print(pt.diff().dt.total_seconds().div(3600).value_counts().head())
print("Publish minutes-of-hour:", sorted(pt.dt.minute.unique()))
print("Publish hours-of-day:", sorted(pt.dt.hour.unique()))

jan = lambda s: (s >= "2026-01-01") & (s < "2026-02-01")
sel = latest_forecast_at_cutoff(f, cutoff_hour_utc=9.0)
sel = sel[jan(sel.startTime.dt.strftime("%Y-%m-%d"))]
print("\nJan delivery hours covered:", len(sel), "of expected", 31 * 24)
print("Horizon of selected forecasts (h):")
print(sel.horizon_h.describe())

m = sel.merge(a, on="startTime")
print("\nMetrics, D-1 09:00 cutoff:")
print(metrics(m))

print("\nError by horizon (all forecasts in Jan):")
fj = f[jan(f.startTime.dt.strftime("%Y-%m-%d"))]
print(error_by_horizon(fj, a))