import os
import time
from datetime import date
import requests
import pandas as pd
from dateutil.relativedelta import relativedelta
from .util import series_from_wide, series_from_long

REB_BASE = "https://www.reb.or.kr/r-one/openapi"


def _reb_rows(statbl_id: str, ym: str, cycle: str = "MM", p_size: int = 1000, max_pages: int = 20) -> list[dict]:
    api_key = os.getenv("REALTY_API_KEY", "").strip()
    all_rows: list[dict] = []

    for page in range(1, max_pages + 1):
        params = {
            "KEY": api_key, "Type": "json", "pIndex": page, "pSize": p_size,
            "STATBL_ID": statbl_id, "DTACYCLE_CD": cycle, "WRTTIME_IDTFR_ID": ym,
        }
        res = requests.get(f"{REB_BASE}/SttsApiTblData.do", params=params, timeout=30)
        if res.status_code != 200 or not res.text.strip().startswith("{"):
            break

        obj = res.json().get("SttsApiTblData", [])
        rows: list[dict] = []
        total_count = None
        for part in obj if isinstance(obj, list) else []:
            if isinstance(part, dict) and "row" in part:
                r = part["row"]
                rows.extend(r if isinstance(r, list) else [r])
            if isinstance(part, dict) and "head" in part:
                for h in part["head"]:
                    if isinstance(h, dict) and "list_total_count" in h:
                        total_count = int(h["list_total_count"])

        if not rows:
            break
        all_rows.extend(rows)
        if total_count and len(all_rows) >= total_count:
            break
        time.sleep(0.1)

    return all_rows


HOUSING_PRICE_STATBL = "A_2024_00016"
REGION_MAP = {"전국": "계", "수도권": "수도권", "기타지방": "기타"}


def fetch_housing_price_index() -> list[dict]:
    end = pd.Timestamp.today().normalize().replace(day=1) - pd.DateOffset(months=1)
    months = [d.strftime("%Y%m") for d in pd.date_range(end=end, periods=72, freq="MS")]

    rows = []
    for ym in months:
        rows.extend(_reb_rows(HOUSING_PRICE_STATBL, ym))

    df = pd.DataFrame(rows)
    if df.empty:
        return []

    mask_top = ~df["CLS_FULLNM"].str.contains(">", na=False)
    mask_itm = df["ITM_NM"] == "지수"
    mask_region = df["CLS_NM"].isin(REGION_MAP.keys())
    df = df[mask_top & mask_itm & mask_region].copy()

    df["region"] = df["CLS_NM"].map(REGION_MAP)
    df["value"] = pd.to_numeric(df["DTA_VAL"], errors="coerce")
    df["date"] = pd.to_datetime(df["WRTTIME_IDTFR_ID"], format="%Y%m")

    return series_from_long(df, "date", "region", "value")


HOUSE_TRADE_STATBL = "A_2024_00552"


def fetch_housing_trade_volume() -> list[dict]:
    cursor = date.today().replace(day=1)
    records, i = [], 0

    while len(records) < 72 and i < 90:
        ym = (cursor - relativedelta(months=i)).strftime("%Y%m")
        i += 1
        rows = _reb_rows(HOUSE_TRADE_STATBL, ym)
        if not rows:
            continue

        df = pd.DataFrame(rows)
        nat = df[(df["CLS_FULLNM"] == "전국") & (df["ITM_NM"].astype(str).str.contains("동", na=False))]
        if nat.empty:
            continue

        records.append({
            "date": pd.to_datetime(ym, format="%Y%m"),
            "주택매매거래량": pd.to_numeric(nat["DTA_VAL"].iloc[0], errors="coerce"),
        })
        time.sleep(0.1)

    if not records:
        return []

    return series_from_wide(pd.DataFrame(records), "date", ["주택매매거래량"])
