import os
import time
import pandas as pd
from .common_odcloud import fetch_odcloud_all, fetch_xml_items
from .util import series_from_wide, series_from_long

STEEL_URL = (
    "https://api.odcloud.kr/api/3039951/v1/"
    "uddi:b6699de8-3b19-4ab7-8ed7-894636ad6c6d_202004071625"
)

STEEL_VALUE_COLS = [
    "철광석(달러_톤)",
    "유연탄(달러_톤)",
    "철스크랩(달러_톤)",
    "철근(천원_톤)",
    "열연(천원_톤)",
    "후판(천원_톤)",
    "냉연(천원_톤)",
]


def fetch_steel_prices() -> list[dict]:
    df = fetch_odcloud_all(STEEL_URL)
    df["기간"] = pd.to_datetime(df["기간"], format="%Y-%m", errors="coerce")

    for col in STEEL_VALUE_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    max_date = df["기간"].max()
    start_date = max_date - pd.DateOffset(years=6)
    df = df[(df["기간"] >= start_date) & (df["기간"] <= max_date)].copy()

    return series_from_wide(df, "기간", STEEL_VALUE_COLS)


ITEMTRADE_URL = "http://apis.data.go.kr/1220000/Itemtrade/getItemtradeList"
WOOD_HS_CODES = {
    "원목": "4403",
    "제재목": "4407",
    "PB": "4410",
    "MDF": "4411",
    "합판": "4412",
}


def _get_itemtrade_year(strt_yymm: str, end_yymm: str, hs_sgn: str) -> pd.DataFrame:
    items = fetch_xml_items(
        ITEMTRADE_URL,
        {
            "serviceKey": os.getenv("DATA_GO_KR_KEY", "").strip(),
            "strtYymm": strt_yymm,
            "endYymm": end_yymm,
            "hsSgn": hs_sgn,
        },
    )
    return pd.DataFrame(items)


def fetch_wood_import_prices(start_year: int = 2020) -> list[dict]:
    import datetime

    end_year = datetime.date.today().year
    frames = []

    for item_name, hs_code in WOOD_HS_CODES.items():
        yearly = []
        for year in range(start_year, end_year + 1):
            df_year = _get_itemtrade_year(f"{year}01", f"{year}12", hs_code)
            if not df_year.empty:
                yearly.append(df_year)
            time.sleep(0.2)

        if not yearly:
            continue

        df = pd.concat(yearly, ignore_index=True)
        df["impWgt"] = pd.to_numeric(df["impWgt"].astype(str).str.replace(",", "", regex=False), errors="coerce")
        df["impDlr"] = pd.to_numeric(df["impDlr"].astype(str).str.replace(",", "", regex=False), errors="coerce")
        df.loc[df["impWgt"] == 0, "impWgt"] = pd.NA
        df["date"] = pd.to_datetime(df["year"], format="%Y.%m", errors="coerce")

        monthly = df.groupby("date", as_index=False).agg(
            import_weight_kg=("impWgt", "sum"),
            import_value_usd=("impDlr", "sum"),
        )
        monthly["import_unit_price_usd_per_ton"] = (
            monthly["import_value_usd"] / monthly["import_weight_kg"] * 1000
        )
        monthly["item_name"] = item_name
        frames.append(monthly[["date", "item_name", "import_unit_price_usd_per_ton"]])

    long_df = pd.concat(frames, ignore_index=True)
    return series_from_long(long_df, "date", "item_name", "import_unit_price_usd_per_ton")
