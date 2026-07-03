import os
import time
from datetime import date
import requests
import pandas as pd
from dateutil.relativedelta import relativedelta
from .common_odcloud import fetch_xml_items
from .util import series_from_wide, series_from_long

INCHEON_BASE = "http://apis.data.go.kr/B551177/AviationStatsByCountry"


def _fetch_incheon(op: str, ym: str, tries: int = 5, sleep: float = 0.5) -> list[dict]:
    url = f"{INCHEON_BASE}/{op}"
    params = {
        "serviceKey": os.getenv("DATA_GO_KR_KEY", "").strip(),
        "from_month": ym, "to_month": ym, "type": "json",
    }
    for _ in range(tries):
        res = requests.get(url, params=params, timeout=30)
        if res.status_code == 200 and res.text.strip().startswith("{"):
            items = res.json()["response"]["body"].get("items", [])
            return items if isinstance(items, list) else [items]
        time.sleep(sleep)
    return []


def _num(x) -> float:
    return pd.to_numeric(str(x).replace(",", ""), errors="coerce")


def fetch_incheon_airport_stats() -> list[dict]:
    cursor = date.today().replace(day=1)
    records, i = [], 0

    while len(records) < 72 and i < 90:
        ym = (cursor - relativedelta(months=i)).strftime("%Y%m")
        i += 1
        flights = _fetch_incheon("getTotalNumberOfFlight", ym)
        if not flights:
            continue
        pax = _fetch_incheon("getTotalNumberOfPassenger", ym)
        cn_flight = next((r for r in flights if r.get("country") == "중국"), {})
        cn_pax = next((r for r in pax if r.get("country") == "중국"), {})

        records.append({
            "date": pd.to_datetime(ym, format="%Y%m"),
            "인바운드_여객수": sum(_num(r.get("arrPassenger")) for r in pax),
            "아웃바운드_여객수": sum(_num(r.get("depPassenger")) for r in pax),
            "인바운드_운항편수": sum(_num(r.get("arrFlight")) for r in flights),
            "아웃바운드_운항편수": sum(_num(r.get("depFlight")) for r in flights),
            "중국발_인바운드_여객수": _num(cn_pax.get("arrPassenger")),
            "중국발_인바운드_운항편수": _num(cn_flight.get("arrFlight")),
        })
        time.sleep(0.15)

    if not records:
        return []

    df = pd.DataFrame(records)
    value_cols = [c for c in df.columns if c != "date"]
    return series_from_wide(df, "date", value_cols)


CUSTOMS_BASE = "http://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList"
COUNTRY_MAP = {"중국": "CN", "미국": "US", "일본": "JP"}
ASEAN_CODES = ["VN", "TH", "ID", "MY", "PH", "SG", "MM", "KH", "LA", "BN"]


def _customs_fetch(strt: str, end: str, cnty_cd: str | None = None) -> list[dict]:
    params = {
        "serviceKey": os.getenv("DATA_GO_KR_KEY", "").strip(),
        "hsSgn": "33", "strtYymm": strt, "endYymm": end,
        "numOfRows": 1000, "pageNo": 1,
    }
    if cnty_cd:
        params["cntyCd"] = cnty_cd
    return fetch_xml_items(CUSTOMS_BASE, params)


def _prd(item: dict) -> str:
    return str(item.get("year") or item.get("strd") or item.get("period") or "").strip()


def _exp(item: dict) -> float:
    return pd.to_numeric(item.get("expDlr", 0), errors="coerce") or 0


def fetch_cosmetics_export() -> list[dict]:
    years = list(range(date.today().year - 6, date.today().year + 1))
    rows = []

    prd_groups: dict[str, float] = {}
    for yr in years:
        for it in _customs_fetch(f"{yr}01", f"{yr}12"):
            prd = _prd(it)[:6]
            if len(prd) >= 6:
                prd_groups[prd] = prd_groups.get(prd, 0) + _exp(it)
        time.sleep(0.2)
    for prd, val in prd_groups.items():
        rows.append({"PRD_DE": prd, "국가": "계", "수출액_달러": val})

    for label, code in COUNTRY_MAP.items():
        for yr in years:
            for it in _customs_fetch(f"{yr}01", f"{yr}12", cnty_cd=code):
                prd = _prd(it)[:6]
                if len(prd) >= 6:
                    rows.append({"PRD_DE": prd, "국가": label, "수출액_달러": _exp(it)})
            time.sleep(0.15)

    asean_buf: dict[str, float] = {}
    for code in ASEAN_CODES:
        for yr in years:
            for it in _customs_fetch(f"{yr}01", f"{yr}12", cnty_cd=code):
                prd = _prd(it)[:6]
                if len(prd) >= 6:
                    asean_buf[prd] = asean_buf.get(prd, 0) + _exp(it)
            time.sleep(0.1)
    for prd, val in asean_buf.items():
        rows.append({"PRD_DE": prd, "국가": "동남아(ASEAN)", "수출액_달러": val})

    df = pd.DataFrame(rows)
    df = df[df["PRD_DE"].str.match(r"^\d{6}$")]
    df["date"] = pd.to_datetime(df["PRD_DE"], format="%Y%m", errors="coerce")
    df = df.groupby(["date", "국가"], as_index=False)["수출액_달러"].sum()

    return series_from_long(df, "date", "국가", "수출액_달러")
