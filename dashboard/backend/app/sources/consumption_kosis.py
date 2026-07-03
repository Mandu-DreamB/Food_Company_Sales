import pandas as pd
from .common_kosis import call_kosis_param, numeric
from .util import series_from_long

RETAIL_TARGETS = {"A1": "백화점", "A2": "대형마트", "A3": "면세점"}


def fetch_retail_sales() -> list[dict]:
    df = call_kosis_param({
        "orgId": "101", "tblId": "DT_1K41013",
        "itmId": "T1", "objL1": "ALL",
        "prdSe": "M", "newEstPrdCnt": "72",
    })
    df = df[df["C1"].isin(RETAIL_TARGETS)].copy()
    df["업태"] = df["C1"].map(RETAIL_TARGETS)
    df["value"] = numeric(df["DT"])
    df["date"] = pd.to_datetime(df["PRD_DE"], format="%Y%m", errors="coerce")
    return series_from_long(df, "date", "업태", "value")


ONLINE_CAT = {"000": "전체", "005": "의복"}


def fetch_online_shopping() -> list[dict]:
    df = call_kosis_param({
        "orgId": "101", "tblId": "DT_1KE10041",
        "itmId": "T20", "objL1": "ALL", "objL2": "ALL",
        "prdSe": "M", "newEstPrdCnt": "72",
    })
    df = df[df["C1"].isin(ONLINE_CAT) & (df["C2"] == "00")].copy()
    df["상품군"] = df["C1"].map(ONLINE_CAT)
    df["value"] = numeric(df["DT"])
    df["date"] = pd.to_datetime(df["PRD_DE"], format="%Y%m", errors="coerce")
    return series_from_long(df, "date", "상품군", "value")


INCOME_ITEMS = {"A": "소득", "B4": "근로소득", "B5": "사업소득", "Y1": "처분가능소득"}


def fetch_household_income_growth() -> list[dict]:
    df = call_kosis_param({
        "orgId": "101", "tblId": "DT_1L9U121",
        "itmId": "T110", "objL1": "M0", "objL2": " ".join(INCOME_ITEMS),
        "prdSe": "Q", "newEstPrdCnt": "72",
    })
    df["소득항목"] = df["C2"].map(INCOME_ITEMS)
    df["실질금액"] = pd.to_numeric(df["DT"], errors="coerce")
    df["quarter"] = df["PRD_DE"].str[:4] + "Q" + df["PRD_DE"].str[4:].astype(int).astype(str)
    df["date"] = pd.PeriodIndex(df["quarter"], freq="Q").dt.to_timestamp()
    df = df.sort_values(["소득항목", "date"])
    df["실질증감률"] = df.groupby("소득항목")["실질금액"].pct_change(4) * 100
    df = df.dropna(subset=["실질증감률"])
    return series_from_long(df, "date", "소득항목", "실질증감률")


def fetch_cosmetics_sales() -> list[dict]:
    df = call_kosis_param({
        "orgId": "101", "tblId": "DT_1K41002",
        "itmId": "T1", "objL1": "G33",
        "prdSe": "M", "newEstPrdCnt": "72",
    })
    df["value"] = numeric(df["DT"])
    df["date"] = pd.to_datetime(df["PRD_DE"], format="%Y%m", errors="coerce")
    df["항목"] = "화장품 소매판매액"
    return series_from_long(df, "date", "항목", "value")


COSMETIC_IDX_LABELS = {"T1": "경상지수", "T2": "불변지수", "T3": "계절조정지수"}


def fetch_cosmetics_sales_index() -> list[dict]:
    df = call_kosis_param({
        "orgId": "101", "tblId": "DT_1K41012",
        "itmId": "T1 T2 T3", "objL1": "G33",
        "prdSe": "M", "newEstPrdCnt": "72",
    })
    df["항목"] = df["ITM_ID"].map(COSMETIC_IDX_LABELS)
    df["value"] = pd.to_numeric(df["DT"], errors="coerce")
    df["date"] = pd.to_datetime(df["PRD_DE"], format="%Y%m", errors="coerce")
    return series_from_long(df, "date", "항목", "value")
