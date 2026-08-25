"""계열사별로 "최근 N년 연간 매출"을 DART XML에서 실제로 뽑을 수 있는지 선별한다.

상관관계 노트북을 계열사마다 만들기 전에, 애초에 매출 시계열이 안 나오는 계열사를 먼저
걸러내는 용도. 매출 추출 로직은 eda_utils(노트북들이 쓰는 것)를 그대로 재사용한다.

사용법: python mandu/Eda/screen_affiliates.py [최소연수, 기본 3]
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "RAG"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import dart_parser  # noqa: E402
import eda_utils  # noqa: E402

DART_DIR = ROOT / "RAG" / "data" / "dart_xml"
ANNUAL_DOC_TYPES = ("사업보고서", "감사보고서", "연결감사보고서")

# seed_affiliates.py의 AFFILIATES와 같은 목록. 카드 하나가 사업부문인 경우(삼양사 화학/식품/
# 코스메틱)는 DART 보고서가 법인 단위라 셋 다 같은 법인을 본다.
AFFILIATES = [
    "삼양홀딩스", "삼양사(화학)", "삼양사(식품)", "삼양사(코스메틱)", "삼남석유화학",
    "삼양화성", "삼양이노켐", "삼양화인테크놀로지", "삼양KCI", "삼양엔씨켐",
    "VERDANT", "삼양바이오팜", "삼양패키징", "삼양데이타시스템",
]
# DART 표제 회사명이 계열사명과 다른 경우만 적는다. 같은 법인의 옛 상호는 합쳐서 센다
# (엔씨켐은 2024년에 삼양엔씨켐으로 개명 — 개명 전 감사보고서도 같은 회사의 매출이다).
ALIASES = {"삼양엔씨켐": ["엔씨켐"]}


def normalize(name: str) -> str:
    """'(주)삼양사', '삼양이노켐주식회사', '삼양사(식품)' -> '삼양사' / '삼양이노켐'."""
    name = re.sub(r"\(.*?\)|주식회사|\s", "", name)
    return name


def scan() -> dict[str, dict]:
    """XML을 한 번씩만 파싱하면서 법인별 연간 매출 연도와 분·반기 보고서 수를 모은다."""
    stats: dict[str, dict] = defaultdict(lambda: {"annual": {}, "interim": 0, "failed": []})
    for f in sorted(DART_DIR.glob("*.xml")):
        docs = dart_parser.parse_dart_xml(f)
        if not docs:
            continue
        meta = docs[0].metadata
        key = normalize(meta["company"])
        period = eda_utils.parse_period(meta["fiscal_period"])
        if period is None:
            continue
        if meta["doc_type"] not in ANNUAL_DOC_TYPES or (period[1] - period[0]).days < 300:
            stats[key]["interim"] += 1
            continue

        revenue = None
        for d in docs:
            if "요약재무정보" in d.metadata["section"]:
                m = eda_utils._SUMMARY_REVENUE_RE.search(d.page_content)
                if m:
                    revenue = int(m.group(1).replace(",", ""))
                    break
        if revenue is None:
            for d in docs:
                if re.search(r"재\s*무\s*제\s*표", d.metadata["section"]) and "주석" not in d.metadata["section"]:
                    won = eda_utils._statement_revenue(d.page_content)
                    if won is not None:
                        revenue = round(won / 1_000_000)
                        break
        if revenue is None:
            stats[key]["failed"].append(f"{f.name}({meta['doc_type']})")
        else:
            stats[key]["annual"][period[0].year] = revenue
    return stats


def main(min_years: int = 3) -> None:
    stats = scan()
    print(f"\n{'계열사':<22}{'연간매출 연도':<24}{'분/반기':>7}  판정")
    print("-" * 78)
    passed, dropped = [], []
    for affiliate in AFFILIATES:
        key = normalize(affiliate)
        parts = [stats[k] for k in [key] + ALIASES.get(key, []) if k in stats]
        annual = {y: v for part in parts for y, v in part["annual"].items()}
        years = sorted(annual)
        ok = len(years) >= min_years
        (passed if ok else dropped).append(affiliate)
        span = f"{years[0]}~{years[-1]}({len(years)}년)" if years else "없음"
        interim = sum(part["interim"] for part in parts)
        print(f"{affiliate:<22}{span:<24}{interim:>7}  {'통과' if ok else '제외'}")
        failed = [f for part in parts for f in part["failed"]]
        if failed:
            print(f"{'':<22}└ 매출 추출 실패: {', '.join(failed)}")

    print(f"\n통과 {len(passed)}곳: {', '.join(passed)}")
    print(f"제외 {len(dropped)}곳: {', '.join(dropped)}")

    known = {normalize(a) for a in AFFILIATES} | {v for vs in ALIASES.values() for v in vs}
    extra = [k for k, v in stats.items() if k not in known and len(v["annual"]) >= min_years]
    if extra:
        print(f"\n계열사 목록엔 없는데 {min_years}년치 매출이 있는 법인: {', '.join(extra)}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
