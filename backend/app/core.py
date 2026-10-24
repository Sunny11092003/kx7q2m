import pandas as pd

def prepare(actuals: pd.DataFrame, forecasts: pd.DataFrame):
    a = actuals[["startTime", "publishTime", "generation"]].copy()
    a["startTime"] = pd.to_datetime(a["startTime"], utc=True)
    a["publishTime"] = pd.to_datetime(a["publishTime"], utc=True)
    # keep the latest published value per half-hour, then average to hourly
    a = (a.sort_values("publishTime")
           .drop_duplicates("startTime", keep="last")
           .set_index("startTime")["generation"]
           .resample("1h").mean()
           .rename("actual")
           .reset_index())

    f = forecasts[["startTime", "publishTime", "generation"]].copy()
    f["startTime"] = pd.to_datetime(f["startTime"], utc=True)
    f["publishTime"] = pd.to_datetime(f["publishTime"], utc=True)
    f = f.rename(columns={"generation": "forecast"})
    f["horizon_h"] = (f.startTime - f.publishTime).dt.total_seconds() / 3600
    f = f[f.horizon_h >= 0].drop_duplicates(["startTime", "publishTime"], keep="last")
    return a, f

def decision_cutoff(target_start: pd.Series, cutoff_hour_utc: float = 9.0) -> pd.Series:
    """Cutoff for each target: the day before the delivery day at cutoff_hour_utc."""
    delivery_day = target_start.dt.floor("D")
    return delivery_day - pd.Timedelta(days=1) + pd.Timedelta(hours=cutoff_hour_utc)

def latest_forecast_at_cutoff(f: pd.DataFrame, cutoff_hour_utc: float = 9.0) -> pd.DataFrame:
    """For each target startTime, the latest forecast published at or before the D-1 cutoff."""
    f = f.copy()
    f["cutoff"] = decision_cutoff(f.startTime, cutoff_hour_utc)
    eligible = f[f.publishTime <= f.cutoff]
    return (eligible.sort_values("publishTime")
                    .groupby("startTime", as_index=False)
                    .tail(1)
                    .sort_values("startTime"))

def metrics(df: pd.DataFrame) -> dict:
    err = df.forecast - df.actual
    return {
        "n": int(len(df)),
        "mae": float(err.abs().mean()),
        "rmse": float((err ** 2).mean() ** 0.5),
        "bias": float(err.mean()),
        "mape": float((err.abs() / df.actual.where(df.actual > 0)).mean() * 100),
    }

def error_by_horizon(f: pd.DataFrame, a: pd.DataFrame, bin_h: int = 4) -> pd.DataFrame:
    m = f.merge(a, on="startTime")
    m["err"] = m.forecast - m.actual
    m["horizon_bin"] = (m.horizon_h // bin_h * bin_h).astype(int)
    return (m.groupby("horizon_bin")
             .agg(mae=("err", lambda s: s.abs().mean()),
                  rmse=("err", lambda s: (s ** 2).mean() ** 0.5),
                  bias=("err", "mean"), n=("err", "size"))
             .reset_index())