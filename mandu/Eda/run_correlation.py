"""선별된 계열사 매출 × 경제지표 상관관계 일괄 분석.

screen_affiliates.py / inspect_data.py로 걸러낸 계열사만 대상으로 한다.
어떤 지표를 볼지는 백엔드 registry.py의 업종별 큐레이션(AFFILIATE_CATEGORY_INDICATOR_CATEGORIES)을
그대로 쓴다 — 계열사마다 지표 목록을 손으로 다시 적으면 대시보드와 어긋난다.

매출 추출은 DART XML을 한 번만 훑어 out/revenue.csv에 캐시한다(계열사마다 다시 파싱하면 코퍼스를
6번 훑게 되어 몇 분씩 걸린다). --rebuild로 캐시를 다시 만든다.

사용법:
    python mandu/Eda/run_correlation.py [--rebuild]
"""
import os
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "RAG"))
sys.path.insert(0, str(ROOT / "dashboard" / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

DART_DIR = ROOT / "RAG" / "data" / "dart_xml"
OUT_DIR = Path(__file__).resolve().parent / "out"
REVENUE_CSV = OUT_DIR / "revenue.csv"

SAMYANG = {"(주)삼양사", "삼양사"}

# (라벨, 업종, 회사명, 추출방식, 부문). 업종은 registry.AFFILIATE_CATEGORY_INDICATOR_CATEGORIES의 키.
#   segment = "II. 사업의 내용"의 "<부문> | 매출액: | 숫자" 누적치 -> 분기 역산
#   entity  = "요약재무정보"의 "매출액 | 숫자" 누적치 -> 분기 역산
#   annual  = 손익계산서/요약재무정보의 연간 매출 (감사보고서만 내는 계열사)
# 삼양사(코스메틱)은 제외했다: 23개 보고서 전부 부문이 식품/화학/기타뿐이라 코스메틱 매출만
# 따로 뗄 수가 없다(코스메틱 사업은 화학부문에 포함돼 있다).
TARGETS = [
    ("삼양홀딩스", "지주", {"(주)삼양홀딩스", "삼양홀딩스"}, "entity", None),
    ("삼양사(식품)", "식품", SAMYANG, "segment", "식품"),
    ("삼양사(화학)", "화학", SAMYANG, "segment", "화학"),
    ("삼양패키징", "패키징", {"(주)삼양패키징", "삼양패키징"}, "entity", None),
    ("삼양엔씨켐", "화학", {"(주)삼양엔씨켐", "(주)엔씨켐"}, "annual", None),
    ("삼양이노켐", "화학", {"삼양이노켐주식회사", "삼양이노켐"}, "annual", None),
    ("삼양데이타시스템", "IT",
     {"삼양데이타시스템(주)", "삼양데이타시스템", "삼양데이타시스템 주식회사"}, "annual", None),
]

ANNUAL_DOC_TYPES = ("사업보고서", "감사보고서", "연결감사보고서")
DOC_PRIORITY = {"사업보고서": 0, "연결감사보고서": 1, "감사보고서": 2}
MIN_N = 6  # 이보다 표본이 적으면 상관계수를 내지 않는다


def build_revenue() -> pd.DataFrame:
    """DART XML을 한 번만 훑어 모든 대상의 구간별 매출을 뽑는다.
    반환 컬럼: label, period_from, period_to, revenue (백만원)."""
    import dart_parser
    import eda_utils

    seg_res = {
        seg: re.compile(rf"{seg}\s*\|\s*매출액:?\s*\|\s*([\d,]+)")
        for _, _, _, kind, seg in TARGETS if kind == "segment"
    }
    records: dict[str, list] = {label: [] for label, *_ in TARGETS}

    for f in sorted(DART_DIR.glob("*.xml")):
        docs = dart_parser.parse_dart_xml(f)
        if not docs:
            continue
        meta = docs[0].metadata
        period = eda_utils.parse_period(meta["fiscal_period"])
        if period is None:
            continue
        pfrom, pto = period
        doc_type = meta["doc_type"]

        for label, _, companies, kind, seg in TARGETS:
            if meta["company"] not in companies:
                continue
            value = None
            if kind == "segment":
                for d in docs:
                    m = seg_res[seg].search(d.page_content)
                    if m:
                        value = int(m.group(1).replace(",", ""))
                        break
            elif kind == "entity":
                for d in docs:
                    if "요약재무정보" not in d.metadata["section"]:
                        continue
                    m = eda_utils._SUMMARY_REVENUE_RE.search(d.page_content)
                    if m:
                        value = int(m.group(1).replace(",", ""))
                        break
            else:  # annual
                if doc_type not in ANNUAL_DOC_TYPES or (pto - pfrom).days < 300:
                    continue
                for d in docs:
                    if "요약재무정보" in d.metadata["section"]:
                        m = eda_utils._SUMMARY_REVENUE_RE.search(d.page_content)
                        if m:
                            value = int(m.group(1).replace(",", ""))
                            break
                if value is None:
                    for d in docs:
                        sec = d.metadata["section"]
                        if re.search(r"재\s*무\s*제\s*표", sec) and "주석" not in sec:
                            won = eda_utils._statement_revenue(d.page_content)
                            if won is not None:
                                value = round(won / 1_000_000)
                                break
            if value is not None:
                records[label].append((f.name, doc_type, pfrom, pto, value))

    frames = []
    for label, _, _, kind, _ in TARGETS:
        rows = records[label]
        if not rows:
            print(f"  [경고] {label}: 매출을 한 건도 못 뽑았습니다")
            continue
        if kind == "annual":
            # 같은 해에 사업보고서와 감사보고서가 둘 다 있으면 사업보고서를 쓴다.
            best_year: dict[int, tuple] = {}
            for _, doc_type, pf, pt, v in rows:
                pri = DOC_PRIORITY.get(doc_type, 3)
                if pf.year not in best_year or pri < best_year[pf.year][0]:
                    best_year[pf.year] = (pri, pf, pt, v)
            df = pd.DataFrame([(pf, pt, v) for _, pf, pt, v in best_year.values()],
                              columns=["period_from", "period_to", "revenue"])
        else:
            # 같은 (보고서종류, 기간)이 중복되면 나중 접수분(파일명이 큰 쪽)을 쓴다 — 정정공시 대응.
            best: dict[tuple, tuple] = {}
            for fname, doc_type, pf, pt, v in rows:
                key = (doc_type, pf, pt)
                if key not in best or fname > best[key][0]:
                    best[key] = (fname, doc_type, pf, pt, v)
            cum_df = pd.DataFrame(
                sorted(best.values(), key=lambda r: (r[3], r[2])),
                columns=["file", "doc_type", "period_from", "period_to", "revenue_cum"],
            )
            q = eda_utils.cumulative_to_quarterly(cum_df, "revenue_cum", "revenue").reset_index()
            df = q[["period_from", "period_to", "revenue"]]

        df = df.sort_values("period_to")
        df.insert(0, "label", label)
        frames.append(df)
        print(f"  {label}: {len(df)}개 구간 ({df.period_to.min()} ~ {df.period_to.max()})")

    out = pd.concat(frames, ignore_index=True)
    OUT_DIR.mkdir(exist_ok=True)
    out.to_csv(REVENUE_CSV, index=False, encoding="utf-8-sig")
    return out


def load_revenue(rebuild: bool) -> pd.DataFrame:
    if rebuild or not REVENUE_CSV.exists():
        print("DART XML에서 매출 추출 중 (1~3분)...")
        return build_revenue()
    print(f"매출 캐시 사용: {REVENUE_CSV} (--rebuild로 재생성)")
    return pd.read_csv(REVENUE_CSV, parse_dates=["period_from", "period_to"])


def indicator_ids_for(category: str) -> list[str]:
    from app import registry
    wanted = registry.AFFILIATE_CATEGORY_INDICATOR_CATEGORIES.get(category, registry.ALL_CATEGORIES)
    return [ind.id for ind in registry.INDICATORS if ind.category in wanted]


def main(rebuild: bool = False) -> None:
    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text
    import eda_utils

    load_dotenv(ROOT / "dashboard" / "backend" / ".env")
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    with engine.connect() as conn:
        points = pd.read_sql(
            text("SELECT indicator_id, series_name, date, value FROM indicator_points"),
            conn, parse_dates=["date"],
        )

    revenue = load_revenue(rebuild)
    OUT_DIR.mkdir(exist_ok=True)
    summary = []

    # 지표는 업종 큐레이션으로 좁히지 않고 전부 본다. registry의 업종별 매핑은 계열사 매출
    # 시계열이 없던 시절 업종 상식으로 손수 정한 것이라(registry.py 주석 참고), 그걸로 미리
    # 걸러버리면 매핑이 맞는지 틀렸는지를 데이터로 확인할 수가 없다. 대신 각 지표가 큐레이션
    # 안에 있었는지를 표시해서, 그 매핑을 실측으로 교체할 근거를 남긴다.
    all_series = {
        f"{i}::{s}": g.set_index("date")["value"].sort_index()
        for (i, s), g in points.groupby(["indicator_id", "series_name"])
    }
    print(f"전체 지표 시계열 {len(all_series)}개")

    for label, category, _, _, _ in TARGETS:
        rev = revenue[revenue.label == label].set_index("period_to")
        curated = set(indicator_ids_for(category))
        n_curated = sum(1 for k in all_series if k.split("::")[0] in curated)

        print(f"\n{'=' * 78}\n{label}  [{category}]  구간 {len(rev)}개 · "
              f"지표 {len(all_series)}개 (업종 큐레이션 {n_curated}개)")
        if len(rev) < MIN_N:
            print(f"  건너뜀: 구간이 {len(rev)}개뿐이라 상관계수를 낼 수 없습니다 (최소 {MIN_N})")
            summary.append((label, len(rev), None, None, None))
            continue

        # 매출 구간의 절반 이상 겹치는 지표만 본다. 연 1회 지표(n=6)를 26분기 매출과
        # 맞추면 6점짜리 상관이 나오는데, |r|로만 줄세우면 그게 26점짜리보다 위로 올라온다.
        min_n = max(MIN_N, len(rev) // 2)
        aligned = eda_utils.align_indicators_to_periods(rev, "revenue", all_series)
        level = eda_utils.corr_table(aligned, all_series, "revenue", min_n=min_n)
        pct = aligned.drop(columns=["period_from"]).pct_change().dropna(how="all")
        change = eda_utils.corr_table(pct, all_series, "revenue", min_n=min_n)

        level.to_csv(OUT_DIR / f"corr_level_{label}.csv", index=False, encoding="utf-8-sig")
        change.to_csv(OUT_DIR / f"corr_change_{label}.csv", index=False, encoding="utf-8-sig")

        # 레벨 상관은 매출과 지표가 둘 다 우상향하기만 해도 크게 나온다. 변화율에서도 같은
        # 부호로 남는 지표만 실제 연동으로 보고 *로 표시한다.
        chg = change.set_index("indicator")["pearson"].to_dict()

        def is_robust(indicator: str, level_r: float) -> bool:
            c = chg.get(indicator)
            return c is not None and c * level_r > 0 and abs(c) > 0.3

        print(f"  {'지표':<44}{'레벨r':>8}{'변화율r':>9}{'n':>4}  큐레")
        for _, row in level.head(12).iterrows():
            c = chg.get(row.indicator)
            cell = f"{c:>9.2f}" if c is not None else "        -"
            mark = " *" if is_robust(row.indicator, row.pearson) else "  "
            inside = "O" if row.indicator.split("::")[0] in curated else "X"
            print(f"  {row.indicator[:43]:<44}{row.pearson:>8.2f}{cell}{row.n:>4}{mark}  {inside}")

        robust_rows = [r for _, r in level.iterrows() if is_robust(r.indicator, r.pearson)]
        outside = [r.indicator for r in robust_rows if r.indicator.split("::")[0] not in curated]
        if outside:
            print(f"  → 견고 신호 {len(robust_rows)}개 중 {len(outside)}개가 업종 큐레이션 밖:")
            for name in outside[:8]:
                print(f"      {name}")
            if len(outside) > 8:
                print(f"      ... 외 {len(outside) - 8}개")
        summary.append((label, len(rev), len(level), len(robust_rows), len(outside)))

    print(f"\n{'=' * 78}\n요약  (견고 = 레벨·변화율 양쪽에서 같은 부호로 남은 지표 수,"
          f"\n       큐레밖 = 그중 registry 업종 매핑에 없던 지표 수)")
    print(f"{'계열사':<20}{'구간':>5}{'지표':>6}{'견고':>6}{'큐레밖':>7}")
    for label, n, *cells in summary:
        row = "".join(f"{(c if c is not None else '-'):>{w}}" for c, w in zip(cells, (6, 6, 7)))
        print(f"{label:<20}{n:>5}{row}")
    print(f"\n상세 CSV: {OUT_DIR}")


# ---------------------------------------------------------------------------
# 추세/계절성 검증 (--verify)
# ---------------------------------------------------------------------------

def _yoy(df: pd.DataFrame, lag: int = 4) -> pd.DataFrame:
    """전년동기대비 변화율.

    레벨 상관은 매출과 지표가 둘 다 우상향하기만 해도 커지고, 분기 변화율(QoQ)은 매출
    계절성(4분기 급증) 때문에 톱니파가 되어 진동하는 지표와 우연히 붙는다. YoY는 추세와
    계절성을 동시에 걷어내므로, 여기서도 남는 상관만 실제 연동으로 볼 수 있다."""
    return (df / df.shift(lag) - 1).dropna(how="all")


def verify_trend(top_n: int = 15) -> None:
    """레벨 상관 상위 지표가 추세를 걷어낸 뒤에도 살아남는지 본다.

    함께 보는 값:
      추세r = 지표와 시간(구간 순번)의 상관. 절댓값이 크면 그 지표는 사실상 시간의 대리변수라
              우상향하는 무엇과도 상관이 높게 나온다.
      YoYr  = 매출·지표를 둘 다 전년동기대비 변화율로 바꾼 뒤의 상관.
    판정: YoY에서도 레벨과 같은 부호로 |r| > 0.3이면 '생존', 아니면 '추세동조'.
    """
    from dotenv import load_dotenv
    from sqlalchemy import create_engine, text
    import eda_utils

    load_dotenv(ROOT / "dashboard" / "backend" / ".env")
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    with engine.connect() as conn:
        points = pd.read_sql(
            text("SELECT indicator_id, series_name, date, value FROM indicator_points"),
            conn, parse_dates=["date"],
        )
    all_series = {
        f"{i}::{s}": g.set_index("date")["value"].sort_index()
        for (i, s), g in points.groupby(["indicator_id", "series_name"])
    }
    revenue = load_revenue(False)
    OUT_DIR.mkdir(exist_ok=True)

    for label, category, _, _, _ in TARGETS:
        rev = revenue[revenue.label == label].set_index("period_to")
        bar = "=" * 84
        if len(rev) < 12:  # YoY는 4구간을 잃는다. 연간 계열사는 검증 자체가 불가능하다.
            print(f"\n{bar}\n{label}: 구간 {len(rev)}개 — YoY 검증 불가 (분기 12개 이상 필요)")
            continue

        min_n = max(MIN_N, len(rev) // 2)
        aligned = eda_utils.align_indicators_to_periods(rev, "revenue", all_series)
        level = eda_utils.corr_table(aligned, all_series, "revenue", min_n=min_n)
        values = aligned.drop(columns=["period_from"])
        yoy = _yoy(values)
        time_idx = pd.Series(range(len(values)), index=values.index, dtype=float)
        rev_trend = values["revenue"].corr(time_idx)

        print(f"\n{bar}\n{label}  구간 {len(rev)}개 · 매출의 추세r {rev_trend:+.2f}")
        print(f"  {'지표':<42}{'레벨r':>7}{'추세r':>7}{'YoYr':>7}{'n':>4}  판정")

        rows = []
        for _, row in level.iterrows():
            key = row.indicator
            trend_r = values[key].corr(time_idx)
            pair = yoy[["revenue", key]].dropna()
            yoy_r = pair["revenue"].corr(pair[key]) if len(pair) >= MIN_N else float("nan")
            ok = pd.notna(yoy_r) and yoy_r * row.pearson > 0 and abs(yoy_r) > 0.3
            rows.append({"indicator": key, "level_r": row.pearson, "trend_r": trend_r,
                         "yoy_r": yoy_r, "n_yoy": len(pair), "survived": ok})

        for r in rows[:top_n]:
            cell = f"{r['yoy_r']:>7.2f}" if pd.notna(r["yoy_r"]) else "      -"
            print(f"  {r['indicator'][:41]:<42}{r['level_r']:>7.2f}{r['trend_r']:>7.2f}"
                  f"{cell}{r['n_yoy']:>4}  {'생존' if r['survived'] else '추세동조'}")

        survivors = [r for r in rows if r["survived"]]
        print(f"  → 상위 {top_n}개 중 {sum(r['survived'] for r in rows[:top_n])}개 생존"
              f" · 전체 {len(rows)}개 중 {len(survivors)}개 생존")

        # 귀무 기준선. YoY는 겹치는 구간이라 자기상관이 심하고, n이 14~22인데 지표를 119개나
        # 시험하면 아무 관계 없이도 상당수가 |r| > 0.3을 넘는다. 매출을 순환 이동시켜(실제
        # 타이밍 관계는 깨고 매출 자체의 자기상관은 보존) 같은 기준으로 세면 그 노이즈 바닥이
        # 나온다. 실제 생존 수가 이 바닥을 못 넘으면 생존 목록 전체를 신호로 읽으면 안 된다.
        keys = [r["indicator"] for r in rows]
        y = yoy["revenue"]

        def _count(target: pd.Series) -> int:
            merged = pd.concat([target.rename("_r"), yoy[keys]], axis=1).dropna(how="all")
            return int((merged[keys].corrwith(merged["_r"]).abs() > 0.3).sum())

        def _rotate(values, k):
            return list(values[-k:]) + list(values[:-k])

        null = pd.Series([_count(pd.Series(_rotate(y.values, k), index=y.index))
                          for k in range(1, len(y))])
        p_value = (null >= len(survivors)).mean()
        print(f"  귀무 기준선(매출 순환이동 {len(null)}회): 중앙 {int(null.median())}개 ·"
              f" 최대 {null.max()}개 → p = {p_value:.2f}"
              f"  {'[노이즈 바닥을 못 넘음 — 생존 목록을 신호로 읽지 말 것]' if p_value > 0.05 else ''}")
        if survivors:
            print("  생존 지표(YoY |r| 순):")
            for r in sorted(survivors, key=lambda r: -abs(r["yoy_r"]))[:10]:
                print(f"      {r['indicator'][:45]:<46} YoYr {r['yoy_r']:+.2f}  추세r {r['trend_r']:+.2f}")
        pd.DataFrame(rows).to_csv(OUT_DIR / f"verify_trend_{label}.csv",
                                  index=False, encoding="utf-8-sig")




if __name__ == "__main__":
    if "--verify" in sys.argv:
        verify_trend()
    else:
        main("--rebuild" in sys.argv)
