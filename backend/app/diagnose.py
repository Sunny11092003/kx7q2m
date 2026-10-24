import pandas as pd
from pathlib import Path
from app.core import prepare, latest_forecast_at_cutoff, metrics

DATA = Path(__file__).parent.parent / "data"
a, f = prepare(pd.read_parquet(DATA / "actuals.parquet"),
               pd.read_parquet(DATA / "forecasts.parquet"))
lo, hi = pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2026-02-01", tz="UTC")

sel = latest_forecast_at_cutoff(f, 9.0)
sel = sel[(sel.startTime >= lo) & (sel.startTime < hi)]

print("== Alignment test: shift actuals by N hours ==")
for shift in [-3, -2, -1, -0.5, 0, 0.5, 1, 2, 3]:
    a2 = a.copy()
    a2["startTime"] = a2.startTime + pd.Timedelta(hours=shift)
    m = sel.merge(a2, on="startTime")
    r = metrics(m)
    print(f"shift {shift:+}h  n={r['n']}  mae={r['mae']:.0f}  bias={r['bias']:.0f}  corr={m.forecast.corr(m.actual):.3f}")

print("\n== Cutoff sensitivity (hour of D-1, UTC) ==")
for c in [6, 8, 9, 9.5, 10, 12]:
    s = latest_forecast_at_cutoff(f, c)
    s = s[(s.startTime >= lo) & (s.startTime < hi)].merge(a, on="startTime")
    r = metrics(s)
    print(f"cutoff {c:>4}  n={r['n']}  mae={r['mae']:.0f}  rmse={r['rmse']:.0f}  bias={r['bias']:.0f}")

m = sel.merge(a, on="startTime")
print("\nMean forecast:", round(m.forecast.mean()), " Mean actual:", round(m.actual.mean()))
print("Bias as % of mean actual:", round(100 * (m.forecast - m.actual).mean() / m.actual.mean(), 1))