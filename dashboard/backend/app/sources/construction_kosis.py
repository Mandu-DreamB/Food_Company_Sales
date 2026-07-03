import pandas as pd
from .common_kosis import call_kosis_param
from .util import series_from_long

APT_REGION_MAP = {"총계": "계", "수도권소계": "수도권", "지방소계": "기타"}
APT_SOURCES = [
    ("DT_MLTM_5387", "13102766969", "13103766969T1", "착공"),
    ("DT_MLTM_5373", "13102766973", "13103766973T1", "준공"),
]


def _fetch_apt(tbl: str, base: str, itm: str, label: str) -> pd.DataFrame:
    regions = " ".join([f"{base}A.0001", f"{base}A.0002", f"{base}A.0006"])
    df = call_kosis_param({
        "orgId": "116", "tblId": tbl, "itmId": itm,
        "objL1": regions, "objL2": f"{base}B.0006", "objL3": f"{base}C.0007", "objL4": f"{base}D.0008",
        "prdSe": "M", "newEstPrdCnt": "72",
    })
    df["구분"] = label
    df["지역"] = df["C1_NM"].map(APT_REGION_MAP)
    df["value"] = pd.to_numeric(df["DT"], errors="coerce")
    df["date"] = pd.to_datetime(df["PRD_DE"], format="%Y%m", errors="coerce")
    return df[["date", "구분", "지역", "value"]]


def fetch_apartment_construction() -> list[dict]:
    df = pd.concat([_fetch_apt(*s) for s in APT_SOURCES], ignore_index=True)
    df["series"] = df["구분"] + "_" + df["지역"]
    return series_from_long(df, "date", "series", "value")


def fetch_construction_cost_index() -> list[dict]:
    df = call_kosis_param({
        "orgId": "397", "tblId": "DT_39701_A003",
        "itmId": "16397AAA0", "objL1": "15397AA2AA",
        "prdSe": "M", "newEstPrdCnt": "72",
    })
    df["value"] = pd.to_numeric(df["DT"], errors="coerce")
    df["date"] = pd.to_datetime(df["PRD_DE"], format="%Y%m", errors="coerce")
    df["항목"] = "건설공사비지수"
    return series_from_long(df, "date", "항목", "value")


def fetch_electric_construction_cost_index() -> list[dict]:
    df = call_kosis_param({
        "orgId": "359", "tblId": "DT_370003_B000_1",
        "itmId": "T001", "objL1": "15359AA0AA_370",
        "prdSe": "M", "newEstPrdCnt": "72",
    })
    df["value"] = pd.to_numeric(df["DT"], errors="coerce")
    df["date"] = pd.to_datetime(df["PRD_DE"], format="%Y%m", errors="coerce")
    df["항목"] = "전기공사비지수"
    return series_from_long(df, "date", "항목", "value")
