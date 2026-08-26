"""mandu/Eda/run_correlation.py가 뽑아 둔 CSV를 correlations 테이블에 적재한다.

CSV 세 종류를 (계열사, 지표, 시리즈) 키로 합친다:
  corr_level_{라벨}.csv   레벨 상관   (pearson, spearman, n)
  corr_change_{라벨}.csv  변화율 상관 (pearson)
  verify_trend_{라벨}.csv 추세 검증   (level_r, trend_r, yoy_r, n_yoy, survived)

verify는 상위 지표만 대상이라 없는 행이 많다 — 그 경우 검증 컬럼은 NULL로 남는다.
r값만 보고 관계가 있다고 말하면 안 되는 이유는 커밋 d64df9d 참고(귀무 기준선 미달).

사용법:
    (backend/.venv 활성화 후) python scripts/seed_correlations.py
멱등(upsert). CSV에서 사라진 조합은 DB에서도 삭제된다.
"""
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import Affiliate, Correlation  # noqa: E402
from app.registry import AFFILIATE_CATEGORY_INDICATOR_CATEGORIES, INDICATORS_BY_ID  # noqa: E402

OUT_DIR = Path(__file__).resolve().parents[3] / "mandu" / "Eda" / "out"


def _read(path: Path) -> dict[tuple[str, str], dict]:
    """indicator 컬럼("지표id::시리즈명")을 키로 나눠 담는다. 파일이 없으면 빈 dict."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = {}
        for row in csv.DictReader(f):
            indicator_id, _, series_name = row["indicator"].partition("::")
            rows[(indicator_id, series_name)] = row
    return rows


def _float(row: dict | None, key: str) -> float | None:
    value = (row or {}).get(key, "")
    return float(value) if value not in ("", None) else None


def _int(row: dict | None, key: str) -> int | None:
    value = (row or {}).get(key, "")
    return int(float(value)) if value not in ("", None) else None


def rows_for(affiliate_id: str, label: str, category: str, now: datetime) -> list[dict]:
    level = _read(OUT_DIR / f"corr_level_{label}.csv")
    change = _read(OUT_DIR / f"corr_change_{label}.csv")
    verify = _read(OUT_DIR / f"verify_trend_{label}.csv")

    curated_categories = set(AFFILIATE_CATEGORY_INDICATOR_CATEGORIES.get(category, []))
    out = []
    for key in level.keys() | change.keys() | verify.keys():
        indicator_id, series_name = key
        indicator = INDICATORS_BY_ID.get(indicator_id)
        v = verify.get(key)
        out.append({
            "affiliate_id": affiliate_id,
            "indicator_id": indicator_id,
            "series_name": series_name,
            "level_r": _float(level.get(key), "pearson"),
            "level_spearman": _float(level.get(key), "spearman"),
            "n": _int(level.get(key), "n"),
            "change_r": _float(change.get(key), "pearson"),
            "trend_r": _float(v, "trend_r"),
            "yoy_r": _float(v, "yoy_r"),
            "n_yoy": _int(v, "n_yoy"),
            "survived": None if v is None else v["survived"].strip().lower() == "true",
            "curated": indicator is not None and indicator.category in curated_categories,
            "computed_at": now,
        })
    return out


def seed() -> None:
    Base.metadata.create_all(bind=engine, tables=[Correlation.__table__])
    now = datetime.now(timezone.utc)

    with SessionLocal() as session:
        # 라벨은 CSV 파일명이자 affiliates.name이다. 이름으로 못 찾으면 그 계열사는 분석 대상이 아니다.
        affiliates = {a.name: (a.id, a.category) for a in session.scalars(select(Affiliate)).all()}

        values = []
        for path in sorted(OUT_DIR.glob("corr_level_*.csv")):
            label = path.stem.removeprefix("corr_level_")
            if label not in affiliates:
                print(f"  건너뜀: '{label}' — affiliates 테이블에 같은 이름이 없습니다.")
                continue
            affiliate_id, category = affiliates[label]
            values.extend(rows_for(affiliate_id, label, category, now))

        if not values:
            raise SystemExit(f"{OUT_DIR}에 corr_level_*.csv가 없습니다. run_correlation.py를 먼저 돌리세요.")

        stmt = pg_insert(Correlation).values(values)
        session.execute(stmt.on_conflict_do_update(
            index_elements=["affiliate_id", "indicator_id", "series_name"],
            set_={c: stmt.excluded[c] for c in (
                "level_r", "level_spearman", "n", "change_r",
                "trend_r", "yoy_r", "n_yoy", "survived", "curated", "computed_at")},
        ))
        session.execute(delete(Correlation).where(Correlation.computed_at != now))
        session.commit()

    survived = sum(1 for v in values if v["survived"])
    print(f"correlations: {len(values)}건 적재 완료 "
          f"(계열사 {len({v['affiliate_id'] for v in values})}곳 · 추세검증 생존 {survived}건)")


if __name__ == "__main__":
    seed()
