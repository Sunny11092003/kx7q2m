import pandas as pd
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
a = pd.read_parquet(DATA / "actuals.parquet")
f = pd.read_parquet(DATA / "forecasts.parquet")

for name, df in [("ACTUALS", a), ("FORECASTS", f)]:
    print(f"\n=== {name} ===")
    print(df.dtypes)
    print(df.head(3))
    print("rows:", len(df))

a["startTime"] = pd.to_datetime(a["startTime"], utc=True)
f["startTime"] = pd.to_datetime(f["startTime"], utc=True)
f["publishTime"] = pd.to_datetime(f["publishTime"], utc=True)

print("\nActuals range:", a.startTime.min(), "->", a.startTime.max())
print("Actuals duplicate startTimes:", a.startTime.duplicated().sum())
print("Forecasts range:", f.startTime.min(), "->", f.startTime.max())

f["horizon_h"] = (f.startTime - f.publishTime).dt.total_seconds() / 3600
print("\nHorizon (hours) summary:")
print(f.horizon_h.describe())
print("\nForecasts per target startTime:")
print(f.groupby("startTime").size().describe())
print("\nMissing generation:", a.generation.isna().sum(), f.generation.isna().sum())