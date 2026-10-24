import pandas as pd
from app.core import latest_forecast_at_cutoff, metrics

def _f(rows):
    df = pd.DataFrame(rows, columns=["startTime", "publishTime", "forecast"])
    df["startTime"] = pd.to_datetime(df.startTime, utc=True)
    df["publishTime"] = pd.to_datetime(df.publishTime, utc=True)
    df["horizon_h"] = (df.startTime - df.publishTime).dt.total_seconds() / 3600
    return df

ROWS = [
    ("2026-01-10 12:00", "2026-01-08 08:00", 50),
    ("2026-01-10 12:00", "2026-01-09 08:00", 100),
    ("2026-01-10 12:00", "2026-01-09 09:25", 200),
    ("2026-01-10 12:00", "2026-01-10 02:00", 300),  # after cutoff
]

def test_picks_latest_before_cutoff():
    out = latest_forecast_at_cutoff(_f(ROWS), cutoff_hour_utc=9.0)
    assert len(out) == 1 and out.forecast.iloc[0] == 100

def test_later_cutoff_includes_newer_forecast():
    out = latest_forecast_at_cutoff(_f(ROWS), cutoff_hour_utc=10.0)
    assert out.forecast.iloc[0] == 200

def test_no_eligible_forecast_gives_no_row():
    out = latest_forecast_at_cutoff(_f(ROWS[3:]), cutoff_hour_utc=9.0)
    assert out.empty

def test_metrics():
    df = pd.DataFrame({"forecast": [110, 90], "actual": [100, 100]})
    m = metrics(df)
    assert m["mae"] == 10 and m["rmse"] == 10 and m["bias"] == 0