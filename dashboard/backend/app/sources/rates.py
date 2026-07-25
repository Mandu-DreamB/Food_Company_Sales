from datetime import date
import pandas as pd
from dateutil.relativedelta import relativedelta
from .common_ecos import fetch_ecos
from .util import series_from_long, series_from_wide

COUNTRY_KEYWORDS = {
    "한국": ["한국"],
    "미국": ["미국"],
    "중국": ["중국"],
    "일본": ["일본"],
    "유럽": ["유로지역"],
}


def _map_country(item_name: str) -> str | None:
    item_name = str(item_name)
    for country, keywords in COUNTRY_KEYWORDS.items():
        if any(kw in item_name for kw in keywords):
            return country
    return None


def fetch_policy_rates() -> list[dict]:
    end = date.today()
    start = end - relativedelta(years=6)
    df = fetch_ecos("902Y006", None, "M", start.strftime("%Y%m"), end.strftime("%Y%m"))

    df["date"] = pd.to_datetime(df["TIME"], format="%Y%m", errors="coerce")
    df["value"] = pd.to_numeric(df["DATA_VALUE"], errors="coerce")
    df["country"] = df["ITEM_NAME1"].apply(_map_country)
    df = df[df["country"].notna()]

    return series_from_long(df, "date", "country", "value")


def fetch_household_credit() -> list[dict]:
    end = date.today()
    start = end - relativedelta(years=6)
    df = fetch_ecos("151Y001", None, "Q", start.strftime("%Y") + "Q1", end.strftime("%Y") + "Q4")

    df["date"] = pd.PeriodIndex(df["TIME"], freq="Q").to_timestamp()
    df["value"] = pd.to_numeric(df["DATA_VALUE"], errors="coerce")

    # ECOS가 서로 다른 ITEM_CODE1에 동일한 ITEM_NAME1(예: "여신전문기관")을 붙여 내려줄 때가 있어
    # 이름만으로 묶으면 같은 날짜에 시리즈 이름이 충돌한다. 이름이 겹치는 항목만 코드를 붙여 구분한다.
    codes_per_name = df.groupby("ITEM_NAME1")["ITEM_CODE1"].transform("nunique")
    df["series_name"] = df["ITEM_NAME1"].where(
        codes_per_name <= 1, df["ITEM_NAME1"] + "(" + df["ITEM_CODE1"] + ")"
    )

    return series_from_long(df, "date", "series_name", "value")


MONTHLY_MACRO_SPECS = [
    ("국고채(3년)", "721Y001", "5020000"),
    ("국고채(10년)", "721Y001", "5050000"),
    ("경상수지(계)", "301Y013", "000000"),
    ("경상수지(상품)", "301Y013", "100000"),
    ("경상수지(서비스)", "301Y013", "200000"),
    ("소비자심리지수", "511Y002", "FME"),
]


def fetch_ecos_monthly_macro() -> list[dict]:
    today = date.today()
    start, end = f"{today.year - 7}01", f"{today.year}12"

    frames = []
    for label, code, item in MONTHLY_MACRO_SPECS:
        df = fetch_ecos(code, item, "M", start, end).sort_values("TIME").tail(72)
        df = df.assign(
            지표=label,
            value=pd.to_numeric(df["DATA_VALUE"], errors="coerce"),
            date=pd.to_datetime(df["TIME"], format="%Y%m"),
        )
        frames.append(df[["date", "지표", "value"]])

    return series_from_long(pd.concat(frames, ignore_index=True), "date", "지표", "value")


GDP_ITEMS = {
    "10601": "계",
    "1010110": "민간소비",
    "1020112": "설비투자",
    "1020111": "건설투자",
}


def fetch_ecos_gdp_growth() -> list[dict]:
    today = date.today()
    start, end = f"{today.year - 8}Q1", f"{today.year}Q4"

    frames = []
    for item, label in GDP_ITEMS.items():
        df = fetch_ecos("200Y108", item, "Q", start, end)
        df = df.assign(항목=label, level=pd.to_numeric(df["DATA_VALUE"], errors="coerce"))
        frames.append(df[["TIME", "항목", "level"]])

    gdp = pd.concat(frames, ignore_index=True)
    gdp["date"] = pd.PeriodIndex(gdp["TIME"], freq="Q").to_timestamp()
    gdp = gdp.sort_values(["항목", "TIME"])
    gdp["growth"] = gdp.groupby("항목")["level"].pct_change(1) * 100
    gdp = gdp.dropna(subset=["growth"]).groupby("항목", group_keys=False).tail(24)

    return series_from_long(gdp, "date", "항목", "growth")
