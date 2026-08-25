"""상관관계 분석 전 데이터 품질 점검 — 결측치/이상치 파악.

두 축을 같은 기준으로 본다:
  A. 매출 시계열 (screen_affiliates.py를 통과한 계열사)
  B. 경제지표 시계열 (indicator_points 테이블, DATABASE_URL 필요)

이상치 판정은 값 자체가 아니라 "전기 대비 변화량"에 MAD 기반 robust z를 쓴다. 지표 대부분이
추세를 가진 레벨 시계열이라 값에 z를 씌우면 추세 끝단이 통째로 이상치로 잡히기 때문이다.
API가 잘못 준 값(0, 단위 뒤바뀜, 튄 값)은 변화량에서 튄다.

사용법:
    python mandu/Eda/inspect_data.py           # 매출 + (DATABASE_URL 있으면) 지표
    python mandu/Eda/inspect_data.py --demo    # 자체 점검
"""
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "RAG"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

DART_DIR = ROOT / "RAG" / "data" / "dart_xml"

# screen_affiliates.py 통과 7곳 -> DART 표제 회사명. 삼양사 3개 카드(화학/식품/코스메틱)는
# 같은 법인이라 여기선 법인 단위로 한 번만 본다 (부문별 매출은 노트북에서 따로 뽑는다).
TARGETS = {
    "삼양사": {"(주)삼양사", "삼양사"},
    "삼양패키징": {"(주)삼양패키징", "삼양패키징"},
    "삼양엔씨켐": {"(주)삼양엔씨켐", "(주)엔씨켐"},
    "삼양이노켐": {"삼양이노켐주식회사", "삼양이노켐"},
    "삼양데이타시스템": {"삼양데이타시스템(주)", "삼양데이타시스템", "삼양데이타시스템 주식회사"},
}

MAD_Z_LIMIT = 5.0
_MAD_TO_SIGMA = 1.4826


def robust_z(values: pd.Series) -> pd.Series:
    """중앙값/MAD 기반 z.

    MAD가 0인 경우(값 대부분이 같은 값 — 예: 매달 정확히 같은 폭으로 늘던 시계열에 한 번 튄 값,
    또는 API가 같은 값을 반복해 준 구간)에는 나눗셈이 안 되지만, 그렇다고 판정 불가로 두면
    "한 점만 튀는" 가장 명백한 이상치를 통째로 놓친다. 그래서 중앙값과 다른 값은 전부 이상치로 본다."""
    med = values.median()
    mad = (values - med).abs().median()
    if mad == 0:
        return pd.Series(np.where(values == med, 0.0, np.inf * np.sign(values - med)),
                         index=values.index)
    return (values - med) / (mad * _MAD_TO_SIGMA)


def inspect_series(name: str, ser: pd.Series, expect_freq_days: float | None = None) -> dict:
    """시계열 하나의 결측/이상치 요약. ser는 DatetimeIndex(또는 date index)에 정렬돼 있어야 한다."""
    ser = ser.sort_index()
    dup = ser.index.duplicated().sum()
    nan = int(ser.isna().sum())
    clean = ser.dropna()

    # 간격은 달력일이 아니라 영업일로 잰다. 일별 시장지표(유가/환율/주가)는 주말·공휴일에
    # 값이 없는 게 정상인데 달력일로 재면 그 3일 공백이 전부 결측으로 잡혀 진짜 구멍이 묻힌다.
    gaps = []
    if len(clean) >= 3:
        dates = clean.index.values.astype("datetime64[D]")
        spacing = pd.Series(np.busday_count(dates[:-1], dates[1:]).astype(float))
        step = (expect_freq_days * 5 / 7) if expect_freq_days else spacing.median()
        limit = max(step * 1.8, 3)  # 일별 계열의 연휴(2~3영업일)까지 결측으로 세지 않도록
        for i, d in enumerate(spacing):
            if d > limit:
                gaps.append((clean.index[i].date(), clean.index[i + 1].date(), int(d)))

    spikes = []
    if len(clean) >= 5:
        z = robust_z(clean.diff().dropna())
        for ts, zv in z[z.abs() > MAD_Z_LIMIT].items():
            spikes.append((ts.date(), float(clean[ts]), round(float(zv), 1)))

    zero_or_neg = int((clean <= 0).sum())

    freq = ""
    if len(clean) >= 3:
        med = pd.Series(clean.index).diff().dt.days.median()
        freq = {True: "일", False: ""}[med <= 4] or ("월" if med <= 45 else "분기" if med <= 130 else "연")

    return {
        "name": name, "freq": freq, "n": len(clean), "nan": nan, "dup": int(dup),
        "start": clean.index.min().date() if len(clean) else None,
        "end": clean.index.max().date() if len(clean) else None,
        "gaps": gaps, "spikes": spikes, "zero_or_neg": zero_or_neg,
    }


def print_report(title: str, reports: list[dict]) -> None:
    print(f"\n{'=' * 84}\n{title}\n{'=' * 84}")
    print(f"{'시계열':<42}{'빈도':>4}{'n':>6}{'결측':>5}{'중복':>5}{'0/음수':>7}{'공백':>5}{'이상치':>6}")
    print("-" * 84)
    for r in sorted(reports, key=lambda r: (-len(r["spikes"]) - len(r["gaps"]), r["name"])):
        print(f"{r['name'][:41]:<42}{r['freq']:>4}{r['n']:>6}{r['nan']:>5}{r['dup']:>5}"
              f"{r['zero_or_neg']:>7}{len(r['gaps']):>5}{len(r['spikes']):>6}")
    for r in reports:
        if not (r["gaps"] or r["spikes"]):
            continue
        print(f"\n· {r['name']} ({r['start']}~{r['end']})")
        for a, b, d in r["gaps"]:
            print(f"    공백 {a} → {b} ({d}일)")
        for ts, v, z in r["spikes"]:
            print(f"    이상치 {ts}  값={v:,.4g}  변화량 z={z}")


def revenue_reports() -> list[dict]:
    """계열사마다 (분기, 연간) 두 시계열을 점검한다.

    상장 계열사는 분·반기보고서의 "요약재무정보"에서 누적 매출이 나와 분기로 역산되지만,
    감사보고서만 내는 계열사(이노켐/데이타시스템)와 상장 전 기간(엔씨켐 2020~2023)은
    손익계산서에서 뽑은 연간치밖에 없다. 어느 쪽을 쓸지는 계열사마다 다르므로 둘 다 낸다.
    """
    import contextlib
    import io

    import dart_parser  # noqa: F401  (eda_utils가 import한다)
    import eda_utils

    reports = []
    for label, companies in TARGETS.items():
        noise = io.StringIO()  # eda_utils가 파일별 성공/실패를 직접 print해서 여기선 삼킨다
        with contextlib.redirect_stdout(noise):
            cum_df, _ = eda_utils.extract_cumulative_metric(
                DART_DIR, companies, eda_utils._SUMMARY_REVENUE_RE,
                value_col="revenue_cum", section_contains="요약재무정보",
            )
            annual_df, _ = eda_utils.extract_annual_metric(DART_DIR, companies, value_col="revenue")

        if not cum_df.empty:
            q = eda_utils.cumulative_to_quarterly(cum_df, "revenue_cum", "revenue")
            reports.append(inspect_series(
                f"매출(분기)::{label}",
                pd.Series(q["revenue"].values, index=pd.to_datetime(q.index)),
            ))
        if not annual_df.empty:
            reports.append(inspect_series(
                f"매출(연간)::{label}",
                pd.Series(annual_df["revenue"].values, index=pd.to_datetime(annual_df.index)),
                expect_freq_days=365,
            ))
    return reports


def indicator_reports() -> list[dict]:
    from sqlalchemy import create_engine, text

    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        from dotenv import load_dotenv
        load_dotenv(ROOT / "dashboard" / "backend" / ".env")
        url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        print("\n[건너뜀] DATABASE_URL이 없어 경제지표 점검은 못 했습니다. "
              "dashboard/backend/.env에 채우거나 환경변수로 주세요.")
        return []

    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        df = pd.read_sql(
            text("SELECT indicator_id, series_name, date, value FROM indicator_points"),
            conn, parse_dates=["date"],
        )

    reports = []
    for (ind, name), sub in df.groupby(["indicator_id", "series_name"]):
        ser = sub.set_index("date")["value"].sort_index()
        reports.append(inspect_series(f"{ind}::{name}", ser))
    return reports


def demo() -> None:
    idx = pd.date_range("2020-01-31", periods=24, freq="ME")
    ser = pd.Series(range(100, 124), index=idx, dtype=float)
    assert inspect_series("clean", ser)["spikes"] == [], "추세만 있는 시계열은 이상치가 없어야 한다"
    assert inspect_series("clean", ser)["gaps"] == []

    spiked = ser.copy()
    spiked.iloc[10] = 9999.0
    r = inspect_series("spiked", spiked)
    assert len(r["spikes"]) >= 1 and r["spikes"][0][0] == idx[10].date(), r["spikes"]

    holed = ser.drop(idx[8:12])
    assert len(inspect_series("holed", holed)["gaps"]) == 1

    withnan = ser.copy()
    withnan.iloc[3] = None
    assert inspect_series("nan", withnan)["nan"] == 1

    assert robust_z(pd.Series([5.0] * 10)).abs().max() == 0, "상수 시계열은 판정 불가(0)"
    print("demo ok")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        print("매출 시계열 추출 중...")
        rev = revenue_reports()
        print_report("A. 매출 시계열 (분기 역산, 단위: 백만원)", rev)
        ind = indicator_reports()
        if ind:
            print_report("B. 경제지표 시계열", ind)
