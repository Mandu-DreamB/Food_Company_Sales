import os
from datetime import date
import requests
import pandas as pd
from dateutil.relativedelta import relativedelta
from .util import series_from_long

EIA_BASE = "https://api.eia.gov/v2/seriesid"

OIL_GAS_SERIES = {
    "WTI": "PET.RWTC.D",
    "Brent": "PET.RBRTE.D",
    "Natural Gas": "NG.RNGWHHD.D",
}


def fetch_eia_oil_gas() -> list[dict]:
    api_key = os.getenv("EIA_API_KEY", "").strip()
    end = date.today()
    start = end - relativedelta(years=5)

    frames = []
    for name, series_id in OIL_GAS_SERIES.items():
        params = {
            "api_key": api_key,
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "length": 5000,
        }
        res = requests.get(f"{EIA_BASE}/{series_id}", params=params, timeout=30)
        res.raise_for_status()
        data = res.json()["response"]["data"]

        df = pd.DataFrame(data)
        if df.empty:
            continue

        df["indicator"] = name
        df["date"] = pd.to_datetime(df["period"], errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        frames.append(df[["date", "indicator", "value"]])

    long_df = pd.concat(frames, ignore_index=True)
    return series_from_long(long_df, "date", "indicator", "value")


def fetch_eia_oecd_stocks() -> list[dict]:
    api_key = os.getenv("EIA_API_KEY", "").strip()
    series_id = "INTL.5-5-OECD-MBBL.M"
    end = date.today()
    start = end - relativedelta(years=5)

    params = {
        "api_key": api_key,
        "start": start.strftime("%Y-%m"),
        "end": end.strftime("%Y-%m"),
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": 5000,
    }
    res = requests.get(f"{EIA_BASE}/{series_id}", params=params, timeout=30)
    res.raise_for_status()
    data = res.json()["response"]["data"]

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["period"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["indicator"] = "OECD 원유 재고"

    return series_from_long(df, "date", "indicator", "value")
