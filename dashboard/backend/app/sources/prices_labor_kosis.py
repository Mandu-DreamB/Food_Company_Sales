import pandas as pd
from .common_kosis import call_kosis_param, numeric
from .util import series_from_long

KOR_CODE, USA_CODE = "1005", "2030"


def _recent_month_range(n_months: int = 72) -> tuple[str, str]:
    end = pd.Timestamp.today().normalize().replace(day=1) - pd.DateOffset(months=1)
    start = end - pd.DateOffset(months=n_months - 1)
    return start.strftime("%Y%m"), end.strftime("%Y%m")


def fetch_price_index() -> list[dict]:
    start_ym, end_ym = _recent_month_range(72)
    frames = []
    for code, name in [(KOR_CODE, "한국"), (USA_CODE, "미국")]:
        df = call_kosis_param({
            "orgId": "101", "tblId": "DT_2IFS002",
            "objL1": code, "itmId": "T001",
            "prdSe": "M", "startPrdDe": start_ym, "endPrdDe": end_ym,
        })
        df["country"] = name
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    df["value"] = numeric(df["DT"])
    df["date"] = pd.to_datetime(df["PRD_DE"], format="%Y%m", errors="coerce")
    return series_from_long(df, "date", "country", "value")


def _pick_code(df: pd.DataFrame, code_col: str, name_col: str, include: list[str], exclude: list[str] = ()) -> str:
    temp = df[[code_col, name_col]].drop_duplicates()
    norm = temp[name_col].astype(str).str.replace(" ", "")
    mask = pd.Series(True, index=temp.index)
    for kw in include:
        mask &= norm.str.contains(kw.replace(" ", ""), na=False)
    for kw in exclude:
        mask &= ~norm.str.contains(kw.replace(" ", ""), na=False)
    matched = temp[mask]
    if matched.empty:
        raise ValueError(f"{name_col}에서 {include} 조건을 찾지 못했습니다.")
    return matched.iloc[0][code_col]


def fetch_unemployment_rate() -> list[dict]:
    probe = call_kosis_param({
        "orgId": "101", "tblId": "INH_2OEEM3015", "itmId": "T001",
        "objL1": "ALL", "objL2": "ALL", "objL3": "ALL", "objL4": "ALL", "objL5": "ALL",
        "prdSe": "M", "newEstPrdCnt": 3,
    })

    adj_code = _pick_code(probe, "C2", "C2_NM", ["연간", "계절조정"], exclude=["하지않음"])
    sex_code = _pick_code(probe, "C3", "C3_NM", ["전체"])
    age_code = _pick_code(probe, "C4", "C4_NM", ["15세이상"])
    eco_code = _pick_code(probe, "C5", "C5_NM", ["분류미적용"])

    frames = []
    for code, name in [(KOR_CODE, "한국"), (USA_CODE, "미국")]:
        df = call_kosis_param({
            "orgId": "101", "tblId": "INH_2OEEM3015", "itmId": "T001",
            "objL1": code, "objL2": adj_code, "objL3": sex_code, "objL4": age_code, "objL5": eco_code,
            "prdSe": "M", "newEstPrdCnt": 72,
        })
        df["country"] = name
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    df["value"] = numeric(df["DT"])
    df["date"] = pd.to_datetime(df["PRD_DE"], format="%Y%m", errors="coerce")
    return series_from_long(df, "date", "country", "value")
