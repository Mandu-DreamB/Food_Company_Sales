import requests
import pandas as pd
from bs4 import BeautifulSoup
from .common_kosis import call_kosis_param
from .util import series_from_long

CAR_ITM = {"T10": "전체", "T11": "승용차", "T12": "상용차"}


def fetch_auto_production_export() -> list[dict]:
    prod = call_kosis_param({
        "orgId": "101", "tblId": "DT_2KAA511",
        "itmId": "T10 T11 T12", "objL1": "1005",
        "prdSe": "Y", "newEstPrdCnt": "10",
    })
    prod["구분"] = "생산"
    prod["차종"] = prod["ITM_ID"].map(CAR_ITM)
    prod["date"] = pd.to_datetime(prod["PRD_DE"], format="%Y")
    prod["대수"] = pd.to_numeric(prod["DT"], errors="coerce")

    exp = call_kosis_param({
        "orgId": "101", "tblId": "DT_2KAA513",
        "itmId": "T11 T12", "objL1": "0",
        "prdSe": "Y", "newEstPrdCnt": "10",
    })
    exp["구분"] = "수출"
    exp["차종"] = exp["ITM_ID"].map({"T11": "승용차", "T12": "상용차"})
    exp["date"] = pd.to_datetime(exp["PRD_DE"], format="%Y")
    exp["대수"] = pd.to_numeric(exp["DT"], errors="coerce")

    exp_total = exp.groupby("date", as_index=False)["대수"].sum()
    exp_total["구분"], exp_total["차종"] = "수출", "전체"

    df = pd.concat([prod, exp, exp_total], ignore_index=True)
    df["series"] = df["구분"] + "_" + df["차종"]
    return series_from_long(df, "date", "series", "대수")


def fetch_auto_export_value() -> list[dict]:
    url = "https://www.index.go.kr/unity/openApi/stblUserShow.do"
    params = {"idntfcId": "6T62U03B013G0222", "ixCode": "1150", "statsCode": "115001"}

    res = requests.get(url, params=params, timeout=30)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.find("table", id="t_Table_115001")
    if table is None:
        raise RuntimeError("통계표(t_Table_115001)를 찾지 못했습니다.")

    years = [int(th.get_text(strip=True)) for th in table.find("thead").find_all("th")[1:]]
    row = table.find("th", attrs={"item-id": "T03"}).find_parent("tr")
    values = [float(td.get_text(strip=True).replace(",", "")) for td in row.find_all("td")]

    df = pd.DataFrame({"date": pd.to_datetime(years, format="%Y"), "수출액_억불": values})
    df["항목"] = "자동차 수출액(억불)"
    return series_from_long(df, "date", "항목", "수출액_억불")


def _fetch_industry_index(item_labels: dict[str, str]) -> list[dict]:
    df = call_kosis_param({
        "orgId": "101", "tblId": "DT_1F02001",
        "itmId": " ".join(item_labels), "objL1": "00", "objL2": "C30",
        "prdSe": "M", "newEstPrdCnt": "72",
    })
    df["항목"] = df["ITM_ID"].map(item_labels)
    df["value"] = pd.to_numeric(df["DT"], errors="coerce")
    df["date"] = pd.to_datetime(df["PRD_DE"], format="%Y%m", errors="coerce")
    return series_from_long(df, "date", "항목", "value")


def fetch_auto_production_index() -> list[dict]:
    return _fetch_industry_index({"T10": "생산지수(원지수)", "T20": "생산지수(계절조정)"})


def fetch_auto_inventory_index() -> list[dict]:
    return _fetch_industry_index({"T12": "재고지수(원지수)", "T22": "재고지수(계절조정)"})
