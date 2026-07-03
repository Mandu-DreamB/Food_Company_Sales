import os
import time
import datetime
import pandas as pd
from .common_odcloud import fetch_xml_items
from .common_kosis import call_kosis_param, numeric
from .util import series_from_long, pick_numeric_column

LIVESTOCK_URL = "http://data.ekape.or.kr/openapi-data/service/user/grade/consumerPriceMonth"

JUDGE_KINDS = {
    "한우": "4301",
    "돼지": "4304",
    "닭": "9901",
    "계란": "9903",
    "우유": "9908",
}
ITEM_FILTER = {"계란": "특란"}


def _month_range(start_ym: str, end_ym: str):
    y, m = int(start_ym[:4]), int(start_ym[4:])
    ey, em = int(end_ym[:4]), int(end_ym[4:])
    while (y, m) <= (ey, em):
        yield f"{y}{m:02d}"
        m += 1
        if m > 12:
            m, y = 1, y + 1


def fetch_livestock_prices() -> list[dict]:
    today = datetime.date.today()
    end_ym = today.strftime("%Y%m")
    start_ym = f"{today.year - 6}{today.month:02d}"
    months = list(_month_range(start_ym, end_ym))

    rows: list[dict] = []
    for name, judge_kind in JUDGE_KINDS.items():
        item_filter = ITEM_FILTER.get(name)
        for ym in months:
            items = fetch_xml_items(
                LIVESTOCK_URL,
                {
                    "serviceKey": os.getenv("DATA_GO_KR_KEY", "").strip(),
                    "standYm": ym,
                    "judgeKind": judge_kind,
                    "numOfRows": "100",
                    "pageNo": "1",
                },
            )
            if item_filter:
                items = [r for r in items if item_filter in (r.get("itemNm") or "")]
            for r in items:
                r["standYm"] = ym
                r["category"] = name
            rows.extend(items)
            time.sleep(0.15)

    df = pd.DataFrame(rows)
    if df.empty:
        return []

    value_col = pick_numeric_column(df, candidates=["price"], exclude=["standYm", "category", "itemNm", "judgeKind"])
    df["value"] = pd.to_numeric(df[value_col].astype(str).str.replace(",", "", regex=False), errors="coerce")
    df["date"] = pd.to_datetime(df["standYm"], format="%Y%m", errors="coerce")

    monthly = df.groupby(["category", "date"], as_index=False)["value"].mean()
    return series_from_long(monthly, "date", "category", "value")


RICE_ORG_ID = "101"
RICE_TBL_ID = "DT_1EI10122"


def fetch_rice_price() -> list[dict]:
    raw = call_kosis_param({
        "orgId": RICE_ORG_ID,
        "tblId": RICE_TBL_ID,
        "itmId": "ALL",
        "objL1": "ALL",
        "prdSe": "M",
        "newEstPrdCnt": 72,
    })

    df = raw.copy()
    df["value"] = numeric(df["DT"])

    day_col = None
    for col in [c for c in df.columns if c.endswith("_NM") or c == "ITM_NM"]:
        if df[col].astype(str).str.match(r"^(5|15|25)일$").any():
            day_col = col
            break
    if day_col is None:
        raise ValueError("5일/15일/25일 기준일 컬럼을 찾지 못했습니다.")

    wide = df.pivot_table(index=["PRD_DE", day_col], columns="ITM_NM", values="value", aggfunc="first").reset_index()
    wide.columns.name = None

    ym = wide["PRD_DE"].astype(str).str.replace(r"\D", "", regex=True).str[:6]
    day_num = wide[day_col].astype(str).str.extract(r"(\d+)")[0].str.zfill(2)
    wide["date"] = pd.to_datetime(ym + day_num, format="%Y%m%d", errors="coerce")

    price_col = "금회가격(A)" if "금회가격(A)" in wide.columns else pick_numeric_column(
        wide, candidates=[], exclude=["PRD_DE", day_col, "date"]
    )
    wide["산지쌀가격"] = pd.to_numeric(wide[price_col], errors="coerce")
    wide["indicator"] = "산지쌀가격(원/20kg)"

    return series_from_long(wide, "date", "indicator", "산지쌀가격")
