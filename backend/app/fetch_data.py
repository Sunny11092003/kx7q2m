import httpx, pandas as pd
from pathlib import Path

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
DATA = Path(__file__).parent.parent / "data"

def get(endpoint: str, params: dict) -> list:
    r = httpx.get(f"{BASE}/{endpoint}/stream", params=params, timeout=180)
    if r.status_code != 200:
        print("FAILED:", r.status_code, r.url)
        print(r.text[:500])
        r.raise_for_status()
    return r.json()

def chunks(start: str, end: str, days: int = 7):
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    while s < e:
        n = min(s + pd.Timedelta(days=days), e)
        yield s, n
        s = n

def fetch_actuals(start: str, end: str) -> pd.DataFrame:
    rows = []
    for s, n in chunks(start, end):
        rows += get("FUELHH", {
            "settlementDateFrom": s.strftime("%Y-%m-%d"),
            "settlementDateTo": n.strftime("%Y-%m-%d"),
            "fuelType": "WIND",
        })
        print("actuals", s.date(), len(rows))
    return pd.DataFrame(rows)

def fetch_forecasts(start: str, end: str) -> pd.DataFrame:
    rows = []
    for s, n in chunks(start, end):
        rows += get("WINDFOR", {
            "publishDateTimeFrom": s.strftime("%Y-%m-%dT%H:%MZ"),
            "publishDateTimeTo": n.strftime("%Y-%m-%dT%H:%MZ"),
        })
        print("forecasts", s.date(), len(rows))
    return pd.DataFrame(rows)

if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    actuals = fetch_actuals("2025-12-31", "2026-02-01")
    fcst = fetch_forecasts("2025-12-24", "2026-02-01")
    actuals.to_parquet(DATA / "actuals.parquet")
    fcst.to_parquet(DATA / "forecasts.parquet")
    print(actuals.head(), fcst.head(), len(actuals), len(fcst), sep="\n")