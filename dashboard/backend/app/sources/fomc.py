import os
from datetime import date
import requests
import pandas as pd
from dateutil.relativedelta import relativedelta
from .util import series_from_long

FRED_BASE = "https://api.stlouisfed.org/fred"
SEP_RELEASE_ID = 326


def _fred_get(endpoint: str, params: dict) -> dict:
    params = {**params, "api_key": os.getenv("FRED_API_KEY", "").strip(), "file_type": "json"}
    res = requests.get(f"{FRED_BASE}/{endpoint}", params=params, timeout=30)
    res.raise_for_status()
    return res.json()


def _get_sep_release_dates(years: int = 6) -> pd.DataFrame:
    end = date.today()
    start = end - relativedelta(years=years)
    data = _fred_get("release/dates", {
        "release_id": SEP_RELEASE_ID,
        "realtime_start": start.isoformat(),
        "realtime_end": end.isoformat(),
        "limit": 1000,
        "sort_order": "asc",
    })
    dates = pd.DataFrame(data.get("release_dates", []))
    dates["date"] = pd.to_datetime(dates["date"], errors="coerce")
    return dates.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


def _get_fed_rate_series() -> pd.DataFrame:
    rows, offset, limit = [], 0, 1000
    while True:
        data = _fred_get("release/series", {
            "release_id": SEP_RELEASE_ID, "limit": limit, "offset": offset,
            "order_by": "series_id", "sort_order": "asc",
        })
        rows.extend(data.get("seriess", []))
        count = int(data.get("count", len(rows)))
        if offset + limit >= count:
            break
        offset += limit

    df = pd.DataFrame(rows)
    return df[df["title"].str.contains("Fed Funds Rate", case=False, na=False)].copy()


def _parse_measure(title: str) -> str:
    title = str(title)
    if "Median" in title:
        return "median"
    return "other"


def fetch_fomc_dot_plot() -> list[dict]:
    sep_dates = _get_sep_release_dates(years=6)
    fed_rate_series = _get_fed_rate_series()
    fed_rate_series = fed_rate_series[fed_rate_series["title"].str.contains("Median", na=False)]

    rows = []
    for _, drow in sep_dates.iterrows():
        vintage_date = drow["date"].date().isoformat()
        vintage_year = drow["date"].year

        for _, srow in fed_rate_series.iterrows():
            data = _fred_get("series/observations", {
                "series_id": srow["id"],
                "vintage_dates": vintage_date,
                "sort_order": "asc",
            })
            obs = pd.DataFrame(data.get("observations", []))
            if obs.empty:
                continue

            obs["value"] = pd.to_numeric(obs["value"].replace(".", pd.NA), errors="coerce")
            obs["date"] = pd.to_datetime(obs["date"], errors="coerce")
            obs = obs.dropna(subset=["value"])

            is_longer_run = "Longer Run" in str(srow["title"])
            for _, orow in obs.iterrows():
                projection_period = "longer_run" if is_longer_run else str(orow["date"].year)
                if not is_longer_run and not (vintage_year <= int(projection_period) <= vintage_year + 4):
                    continue
                rows.append({
                    "fomc_release_date": pd.Timestamp(vintage_date),
                    "projection_period": projection_period,
                    "value": orow["value"],
                })

    if not rows:
        return []

    df = pd.DataFrame(rows).drop_duplicates(subset=["fomc_release_date", "projection_period"], keep="last")
    return series_from_long(df, "fomc_release_date", "projection_period", "value")
