import pandas as pd


def pick_numeric_column(df: pd.DataFrame, candidates: list[str], exclude: list[str] = ()) -> str:
    """candidates 중 실제 존재하고 숫자로 변환 가능한 값이 있는 첫 컬럼을 반환.
    후보가 하나도 안 맞으면 exclude를 제외한 컬럼 중 숫자 변환 비율이 가장 높은 컬럼을 사용."""
    for col in candidates:
        if col in df.columns:
            numeric = pd.to_numeric(df[col].astype(str).str.replace(",", "", regex=False), errors="coerce")
            if numeric.notna().any():
                return col

    best_col, best_ratio = None, 0.0
    for col in df.columns:
        if col in exclude:
            continue
        numeric = pd.to_numeric(df[col].astype(str).str.replace(",", "", regex=False), errors="coerce")
        ratio = numeric.notna().mean()
        if ratio > best_ratio:
            best_col, best_ratio = col, ratio

    if best_col is None or best_ratio == 0:
        raise ValueError(f"숫자 컬럼을 찾지 못했습니다. columns={list(df.columns)}")

    return best_col


def series_from_wide(df: pd.DataFrame, date_col: str, value_cols: list[str]) -> list[dict]:
    """date_col + 여러 값 컬럼 -> 컬럼마다 하나의 시리즈."""
    df = df.dropna(subset=[date_col]).sort_values(date_col)
    series = []
    for col in value_cols:
        if col not in df.columns:
            continue
        sub = df[[date_col, col]].dropna(subset=[col])
        series.append({
            "name": col,
            "points": [
                {"date": pd.Timestamp(d).strftime("%Y-%m-%d"), "value": float(v)}
                for d, v in zip(sub[date_col], sub[col])
            ],
        })
    return series


def series_from_long(df: pd.DataFrame, date_col: str, name_col: str, value_col: str) -> list[dict]:
    """date_col, name_col, value_col 형태의 long 포맷 -> name_col 값마다 하나의 시리즈."""
    df = df.dropna(subset=[date_col, value_col]).sort_values(date_col)
    series = []
    for name, sub in df.groupby(name_col):
        series.append({
            "name": str(name),
            "points": [
                {"date": pd.Timestamp(d).strftime("%Y-%m-%d"), "value": float(v)}
                for d, v in zip(sub[date_col], sub[value_col])
            ],
        })
    return series
