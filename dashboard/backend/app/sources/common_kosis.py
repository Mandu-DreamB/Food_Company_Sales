import os
import requests
import pandas as pd

DATA_URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"


def call_kosis_param(params: dict, timeout: int = 30) -> pd.DataFrame:
    """KOSIS 파라미터 방식(getList) 호출 -> DataFrame"""
    base = {
        "method": "getList",
        "apiKey": os.getenv("KOSIS_API_KEY", "").strip(),
        "format": "json",
        "jsonVD": "Y",
    }
    res = requests.get(DATA_URL, params={**base, **params}, timeout=timeout)
    res.raise_for_status()
    data = res.json()

    if isinstance(data, dict) and ("err" in data or "errMsg" in data):
        raise RuntimeError(f"KOSIS API 오류: {data}")

    if isinstance(data, list) and data and isinstance(data[0], dict) and "err" in data[0]:
        raise RuntimeError(f"KOSIS API 오류: {data[0]}")

    return pd.DataFrame(data)


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    )
