"""계열사별 DART 매출 × 경제지표 상관관계 노트북에서 공통으로 쓰는 함수 모음.

각 계열사 노트북(예: samyang_food_correlation.ipynb, samyang_packaging_correlation.ipynb)은
①어떤 정규식으로 매출을 뽑을지, ②TARGETS(어떤 경제지표를 볼지)만 각자 정의하고,
누적 매출 -> 분기 역산 -> 지표 정렬 -> 상관관계 계산/시각화는 이 모듈의 함수를 그대로 쓴다.
"""
import re
from datetime import date
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

import dart_parser  # sys.path에 RAG 폴더를 추가한 뒤 import (노트북 쪽에서 처리)


def parse_period(fp: str):
    """dart_parser가 만든 'YYYY.MM.DD~YYYY.MM.DD' 형태의 fiscal_period 문자열을 파싱한다."""
    m = re.match(r"(\d{4})\.(\d{2})\.(\d{2})~(\d{4})\.(\d{2})\.(\d{2})", fp)
    if not m:
        return None
    y1, mo1, d1, y2, mo2, d2 = map(int, m.groups())
    return date(y1, mo1, d1), date(y2, mo2, d2)


def extract_cumulative_metric(dart_dir: Path, target_companies: set[str], row_re: re.Pattern,
                               value_col: str, section_contains: str | None = None):
    """DART XML 폴더에서 target_companies에 해당하는 문서만 골라, row_re로 매출(또는 다른 지표)
    누적치를 뽑는다. row_re는 group(1)에 콤마 포함 숫자를 캡처해야 한다
    (예: r"매출액\\s*\\|\\s*([\\d,]+)").

    section_contains가 주어지면 그 문자열이 breadcrumb(섹션 경로)에 포함된 문서에서만 찾는다
    (보통 "요약재무정보"처럼 표 형식이 고정된 섹션으로 좁혀서 오탐을 줄이는 용도).

    반환: (cum_df, failed) — cum_df 컬럼은 [file, doc_type, period_from, period_to, value_col].
    """
    records, failed = [], []
    for f in sorted(Path(dart_dir).glob("*.xml")):
        docs = dart_parser.parse_dart_xml(f)
        if not docs or docs[0].metadata["company"] not in target_companies:
            continue
        doc_type = docs[0].metadata["doc_type"]
        period = parse_period(docs[0].metadata["fiscal_period"])
        if period is None:
            failed.append((f.name, "기간 파싱 실패"))
            continue
        found = None
        for d in docs:
            if section_contains and section_contains not in d.metadata["section"]:
                continue
            m = row_re.search(d.page_content)
            if m:
                found = int(m.group(1).replace(",", ""))
                break
        if found is None:
            failed.append((f.name, "매출 행을 찾지 못함 (표 형식이 다른 보고서일 수 있음)"))
            continue
        records.append((f.name, doc_type, period[0], period[1], found))

    print(f"성공 {len(records)}건 / 실패 {len(failed)}건")
    for fname, reason in failed:
        print(" -", fname, ":", reason)

    best = {}
    for fname, doc_type, pfrom, pto, val in records:
        key = (doc_type, pfrom, pto)
        if key not in best or fname > best[key][0]:
            best[key] = (fname, doc_type, pfrom, pto, val)

    cum_df = pd.DataFrame(
        sorted(best.values(), key=lambda r: (r[3], r[2])),
        columns=["file", "doc_type", "period_from", "period_to", value_col],
    )
    return cum_df, failed


_SUMMARY_REVENUE_RE = re.compile(r"매출액\s*\|\s*([\d,]+)")
_NUMBER_CELL_RE = re.compile(r"[\d,]+")
_MIN_REVENUE_DIGITS = 7  # 실제 매출액(원 단위, 최소 억대)과 주석번호 나열("19,29")을 구분하는 최소 자릿수


def _statement_revenue(text: str) -> int | None:
    """포괄손익계산서 스타일 표에서 '매출액' 행의 첫 큰 숫자 셀을 찾는다.

    "I. 매출액 | 19, 29 |  | 281,418,096,468 |  | 239,117,050,983"처럼 매출액과 실제
    금액 사이에 주석 번호("19, 29", 공백 없이 "20,30"으로 붙는 경우도 있음) 열이 끼어드는
    경우가 있어, 단순히 매출액 뒤 첫 숫자를 잡으면 그 주석 번호를 잘못 캡처한다. 그래서 행을
    셀 단위로 쪼갠 뒤, 콤마를 뗀 순수 자릿수가 _MIN_REVENUE_DIGITS 이상인 셀(주석 번호 나열은
    보통 2~4자리)만 실제 매출액으로 인정한다.
    """
    for row in text.split(dart_parser.TABLE_ROW_SEP):
        cells = [c.strip() for c in row.split("|")]
        if not cells or "매출액" not in cells[0] or "비율" in cells[0] or "%" in cells[0]:
            continue
        for c in cells[1:]:
            if _NUMBER_CELL_RE.fullmatch(c):
                digits = c.replace(",", "")
                if len(digits) >= _MIN_REVENUE_DIGITS:
                    return int(digits)
    return None


def extract_annual_metric(dart_dir: Path, target_companies: set[str], value_col: str,
                           annual_doc_types: tuple[str, ...] = ("사업보고서", "감사보고서", "연결감사보고서")):
    """상장사가 아니라 연 1회 사업/감사보고서만 내는 계열사용. 분기가 없으니 diff 없이
    보고서 1건당 연간 매출 1건을 그대로 쓴다 (반기·분기보고서는 건너뛴다).

    표 형식이 보고서 종류마다 달라 두 패턴을 순서대로 시도한다:
      1) "요약재무정보" 섹션의 "매출액 | 12,345" (단위: 백만원, 사업/분기/반기보고서)
      2) "재무제표" 섹션(주석 제외)의 "Ⅰ.매출액(주21) | | 12,345,678,901" (단위: 원, 감사보고서
         -> 백만원으로 환산). 같은 문서의 '주석' 섹션에는 단위가 다른(천원) 매출 내역이 또
         나오므로 반드시 제외해야 한다.

    같은 연도에 여러 보고서가 있으면(예: 사업보고서 + 감사보고서) 사업보고서를 우선한다.

    반환: (annual_df, failed) — annual_df는 period_to를 index로 하는
    [file, doc_type, period_from, value_col] 표.
    """
    DOC_PRIORITY = {"사업보고서": 0, "연결감사보고서": 1, "감사보고서": 2}

    records, failed = [], []
    for f in sorted(Path(dart_dir).glob("*.xml")):
        docs = dart_parser.parse_dart_xml(f)
        if not docs or docs[0].metadata["company"] not in target_companies:
            continue
        doc_type = docs[0].metadata["doc_type"]
        if doc_type not in annual_doc_types:
            continue
        period = parse_period(docs[0].metadata["fiscal_period"])
        if period is None or (period[1] - period[0]).days < 300:
            continue  # 연간 전체 기간이 아니면(반기/분기 등) 건너뜀

        found = None
        for d in docs:
            if "요약재무정보" in d.metadata["section"]:
                m = _SUMMARY_REVENUE_RE.search(d.page_content)
                if m:
                    found = int(m.group(1).replace(",", ""))
                    break
        if found is None:
            for d in docs:
                # DART 원문 TITLE이 "재 무 제 표"처럼 글자 사이 공백을 넣어 렌더링되는 경우가 있다.
                if re.search(r"재\s*무\s*제\s*표", d.metadata["section"]) and "주석" not in d.metadata["section"]:
                    won = _statement_revenue(d.page_content)
                    if won is not None:
                        found = round(won / 1_000_000)
                        break
        if found is None:
            failed.append((f.name, doc_type, "매출 행을 찾지 못함"))
            continue
        records.append((f.name, doc_type, period[0], period[1], found))

    print(f"성공 {len(records)}건 / 실패 {len(failed)}건")
    for fname, doc_type, reason in failed:
        print(" -", fname, f"({doc_type})", ":", reason)

    best = {}
    for fname, doc_type, pfrom, pto, val in records:
        year = pfrom.year
        priority = DOC_PRIORITY.get(doc_type, 3)
        if year not in best or priority < best[year][0]:
            best[year] = (priority, fname, doc_type, pfrom, pto, val)

    rows = sorted((r[1:] for r in best.values()), key=lambda r: r[2])
    annual_df = pd.DataFrame(rows, columns=["file", "doc_type", "period_from", "period_to", value_col])
    return annual_df.set_index("period_to"), failed


def cumulative_to_quarterly(cum_df: pd.DataFrame, cum_col: str, out_col: str) -> pd.DataFrame:
    """같은 회계연도 안에서 연속 보고서의 누적치를 차분해 분기(또는 반기)별 구간값으로 바꾼다.

    그 해의 첫 보고서가 통상적인 첫 구간(약 90일)보다 훨씬 길면(=앞선 보고서가 없어서
    여러 구간이 뭉친 경우), 그 값은 구간화하지 않고 기준점만 갱신한다 (이상치 방지).
    """
    quarter_records = []
    by_year: dict[int, list] = {}
    for _, row in cum_df.iterrows():
        by_year.setdefault(row.period_from.year, []).append(row)

    for year, rows in sorted(by_year.items()):
        rows = sorted(rows, key=lambda r: r.period_to)
        prev_end, prev_val = date(year, 1, 1), 0
        for row in rows:
            if prev_val == 0 and (row.period_to - prev_end).days > 100:
                prev_end, prev_val = row.period_to, row[cum_col]
                continue
            quarter_records.append({
                "period_from": prev_end,
                "period_to": row.period_to,
                out_col: row[cum_col] - prev_val,
            })
            prev_end, prev_val = row.period_to, row[cum_col]

    return pd.DataFrame(quarter_records).set_index("period_to")


def load_indicator_series(engine, targets: dict[str, list[str]]) -> dict[str, pd.Series]:
    """PostgreSQL의 indicator_points 테이블에서 targets(indicator_id -> series_name 목록)에
    해당하는 시계열만 로드해 {"indicator_id::series_name": Series} 형태로 반환한다."""
    from sqlalchemy import text

    with engine.connect() as conn:
        points = pd.read_sql(
            text("SELECT indicator_id, series_name, date, value FROM indicator_points "
                 "WHERE indicator_id = ANY(:ids)"),
            conn,
            params={"ids": list(targets.keys())},
            parse_dates=["date"],
        )

    all_series = {}
    for ind_id, names in targets.items():
        for name in names:
            sub = points[(points.indicator_id == ind_id) & (points.series_name == name)]
            if sub.empty:
                continue
            all_series[f"{ind_id}::{name}"] = sub.set_index("date")["value"].sort_index()
    return all_series


def align_indicators_to_periods(period_df: pd.DataFrame, value_col: str,
                                 all_series: dict[str, pd.Series]) -> pd.DataFrame:
    """period_df(index=period_to, 컬럼에 period_from과 value_col)의 각 구간에 대해,
    그 구간 안 지표 값의 평균을 계산해 나란히 정렬한다."""
    rows = []
    for pto, row in period_df.iterrows():
        pfrom = row["period_from"]
        rec = {"period_from": pfrom, value_col: row[value_col]}
        for key, ser in all_series.items():
            window = ser[(ser.index >= pd.Timestamp(pfrom)) & (ser.index <= pd.Timestamp(pto))]
            rec[key] = window.mean() if len(window) else None
        rows.append(rec)
    return pd.DataFrame(rows, index=period_df.index)


def corr_table(df: pd.DataFrame, all_series: dict[str, pd.Series], value_col: str,
               min_n: int = 6) -> pd.DataFrame:
    """value_col과 all_series의 각 지표 사이 피어슨/스피어만 상관계수를 계산해
    |pearson| 내림차순으로 정렬한 표를 만든다."""
    out = []
    for key in all_series.keys():
        if key not in df.columns:
            continue
        sub = df[[value_col, key]].dropna()
        if len(sub) < min_n or sub[key].std() == 0:
            continue
        out.append({
            "indicator": key,
            "pearson": sub[value_col].corr(sub[key]),
            "spearman": sub[value_col].corr(sub[key], method="spearman"),
            "n": len(sub),
        })
    # 표본이 min_n에 못 미치면 out이 비는데(연 1회 보고서 계열사의 변화율 등), 그대로
    # DataFrame으로 만들면 컬럼조차 없어서 sort_values가 KeyError를 낸다.
    if not out:
        return pd.DataFrame(columns=["indicator", "pearson", "spearman", "n"])
    return pd.DataFrame(out).sort_values("pearson", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)


def plot_top_correlations(corr_df: pd.DataFrame, title: str, top_n: int = 15):
    """corr_table 결과를 |pearson| 상위 top_n개만 가로 막대그래프로 그린다."""
    top = corr_df.head(top_n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = ["#B6512E" if v >= 0 else "#1F6E78" for v in top["pearson"]]
    ax.barh(top["indicator"], top["pearson"], color=colors)
    ax.axvline(0, color="#888", linewidth=0.8)
    ax.set_xlim(-0.85, 0.85)
    ax.set_title(title)
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.show()


def lag_correlation_table(level_df: pd.DataFrame, all_series: dict[str, pd.Series], value_col: str,
                           max_lag: int = 4, min_n: int = 6) -> pd.DataFrame:
    """지표가 t-L 구간 시점, value_col은 t 구간 시점일 때의 레벨 상관계수를 lag 0..max_lag-1에
    대해 계산하고, 각 지표별로 |상관계수|가 가장 큰 lag를 best_lag로 뽑는다.

    다중비교 주의: 지표 수 x lag 조합을 모두 훑어 최댓값을 고르는 방식이라, 표본이 적으면
    우연히 강한 값이 나올 수 있다. 결과는 확정된 관계가 아니라 가설 후보로 취급할 것.
    """
    lag_rows = []
    for key in all_series.keys():
        if key not in level_df.columns:
            continue
        per_lag = {}
        for L in range(max_lag):
            shifted = level_df[key].shift(L)
            sub = pd.concat([level_df[value_col], shifted.rename("ind")], axis=1).dropna()
            if len(sub) < min_n:
                continue
            per_lag[L] = sub[value_col].corr(sub["ind"])
        if not per_lag:
            continue
        best_lag = max(per_lag, key=lambda L: abs(per_lag[L]))
        lag_rows.append({
            "indicator": key, "best_lag": best_lag, "best_corr": per_lag[best_lag],
            **{f"L{L}": per_lag.get(L) for L in range(max_lag)},
        })

    if not lag_rows:  # corr_table과 같은 이유
        return pd.DataFrame(columns=["indicator", "best_lag", "best_corr"] + [f"L{L}" for L in range(max_lag)])
    return pd.DataFrame(lag_rows).sort_values("best_corr", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)


def plot_lag_heatmap(lag_df: pd.DataFrame, title: str, max_lag: int = 4, top_n: int = 14):
    """lag_correlation_table 결과를 지표 x lag 히트맵으로 그린다."""
    lag_cols = [f"L{L}" for L in range(max_lag)]
    top_lag = lag_df.head(top_n).set_index("indicator")[lag_cols]
    fig, ax = plt.subplots(figsize=(6, 7))
    im = ax.imshow(top_lag.values, cmap="RdYlGn", vmin=-0.8, vmax=0.8, aspect="auto")
    ax.set_xticks(range(max_lag), lag_cols)
    ax.set_yticks(range(len(top_lag)), top_lag.index)
    for i in range(top_lag.shape[0]):
        for j in range(top_lag.shape[1]):
            ax.text(j, i, f"{top_lag.values[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.7, label="Pearson r")
    ax.set_title(title)
    plt.tight_layout()
    plt.show()
