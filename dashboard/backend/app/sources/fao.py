import io
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .util import series_from_wide

FAO_PAGE = "https://www.fao.org/worldfoodsituation/foodpricesindex/en/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,application/csv,text/plain,*/*",
    "Referer": FAO_PAGE,
}

VALUE_COLS = ["Food Price Index", "Meat", "Dairy", "Cereals", "Oils", "Sugar"]


def _find_csv_url() -> str:
    res = requests.get(FAO_PAGE, headers=HEADERS, timeout=30)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    for a in soup.find_all("a", href=True):
        href, text = a["href"], a.get_text(" ", strip=True)
        if "food_price_indices_data.csv" in href.lower():
            return urljoin(FAO_PAGE, href)
        if "csv" in text.lower() and "nominal" in text.lower():
            return urljoin(FAO_PAGE, href)

    raise ValueError("FAO 페이지에서 CSV 링크를 찾지 못했습니다.")


def fetch_fao_food_price_index() -> list[dict]:
    csv_url = _find_csv_url()
    res = requests.get(csv_url, headers=HEADERS, timeout=60, allow_redirects=True)
    res.raise_for_status()

    if "<html" in res.text[:500].lower():
        raise ValueError("CSV가 아니라 HTML 페이지가 내려왔습니다.")

    raw = pd.read_csv(io.StringIO(res.content.decode("utf-8-sig")))

    fao = raw.iloc[2:, :7].copy()
    fao.columns = raw.iloc[1, :7].tolist()
    fao = fao.dropna(subset=["Date"]).reset_index(drop=True)
    fao["date"] = pd.to_datetime(fao["Date"], format="%Y-%m", errors="coerce")

    for col in VALUE_COLS:
        fao[col] = pd.to_numeric(fao[col], errors="coerce")

    return series_from_wide(fao, "date", VALUE_COLS)
