import os
import requests
import pandas as pd

ECOS_BASE = "https://ecos.bok.or.kr/api"


def fetch_ecos(stat_code: str, item_code: str | None, cycle: str, start: str, end: str) -> pd.DataFrame:
    """한국은행 ECOS StatisticSearch 호출 -> DataFrame (전체 페이지 수집)"""
    api_key = os.getenv("ECOS_API_KEY", "").strip()
    rows: list[dict] = []
    row_start = 1
    page_size = 1000

    while True:
        parts = [api_key, "json", "kr", row_start, row_start + page_size - 1, stat_code, cycle, start, end]
        if item_code:
            parts.append(item_code)

        url = f"{ECOS_BASE}/StatisticSearch/" + "/".join(map(str, parts))
        res = requests.get(url, timeout=30)
        res.raise_for_status()
        data = res.json()

        if "RESULT" in data:
            raise RuntimeError(f"ECOS API 오류: {data['RESULT']}")

        page_rows = data.get("StatisticSearch", {}).get("row", [])
        rows.extend(page_rows)

        total_count = int(data.get("StatisticSearch", {}).get("list_total_count", len(rows)))
        if len(rows) >= total_count or not page_rows:
            break
        row_start += page_size

    return pd.DataFrame(rows)
