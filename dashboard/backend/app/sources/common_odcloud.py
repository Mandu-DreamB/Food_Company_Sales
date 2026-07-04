import os
import requests
import pandas as pd
import xml.etree.ElementTree as ET


def fetch_odcloud_all(url: str, per_page: int = 1000) -> pd.DataFrame:
    """공공데이터포털 ODCLOUD API 공통 수집 함수 (JSON 페이지네이션)"""
    service_key = os.getenv("DATA_GO_KR_KEY", "").strip()
    all_rows: list[dict] = []
    page = 1

    while True:
        params = {
            "page": page,
            "perPage": per_page,
            "serviceKey": service_key,
            "returnType": "JSON",
        }
        res = requests.get(url, params=params, timeout=30)
        res.raise_for_status()
        data = res.json()

        rows = data.get("data", [])
        all_rows.extend(rows)

        total_count = data.get("totalCount", 0)
        if len(all_rows) >= total_count or not rows:
            break
        page += 1

    return pd.DataFrame(all_rows)


def fetch_xml_items(url: str, params: dict, timeout: int = 30) -> list[dict]:
    """공공데이터포털 XML 응답 공통 파서 (serviceKey는 params에 포함해서 전달)"""
    res = requests.get(url, params=params, timeout=timeout)
    res.raise_for_status()

    text = res.text.strip()
    if not text.startswith("<"):
        raise RuntimeError(f"XML이 아닌 응답입니다: {text[:300]}")

    root = ET.fromstring(text)

    for hdr_tag in ("header", "cmmMsgHeader"):
        header = root.find(f".//{hdr_tag}")
        if header is not None:
            code = header.findtext("resultCode") or header.findtext("returnReasonCode") or ""
            msg = header.findtext("resultMsg") or header.findtext("errMsg") or ""
            if code and code not in ("00", "0"):
                raise RuntimeError(f"API 오류 {code}: {msg}")

    return [{child.tag: (child.text or "").strip() for child in item} for item in root.findall(".//item")]
