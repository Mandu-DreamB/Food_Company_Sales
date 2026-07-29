"""삼양그룹 계열사 목록을 affiliates 테이블에 적재하는 스크립트.

프론트(src/data/affiliates.ts)에 하드코딩돼 있던 계열사/카테고리 매핑의 원본이다.
계열사가 추가·변경되면 아래 CATEGORIES/AFFILIATES만 고치고 다시 실행하면 된다.

사용법:
    (backend/.venv 활성화 후) python scripts/seed_affiliates.py

멱등(upsert)이므로 여러 번 실행해도 안전하다. 목록에서 빠진 계열사는 DB에서도 삭제된다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import Affiliate  # noqa: E402

# 랜딩 페이지 탭 순서
CATEGORIES = ["지주", "화학", "식품", "의약바이오", "패키징", "코스메틱", "IT"]

# (id, 이름, 카테고리, 로고 텍스트)
AFFILIATES = [
    ("samyang-holdings", "삼양홀딩스", "지주", "SAMYANG HOLDINGS"),
    ("samyang-chemical", "삼양사(화학)", "화학", "SAMYANG"),
    ("samyang-food", "삼양사(식품)", "식품", "SAMYANG"),
    ("samyang-cosmetic", "삼양사(코스메틱)", "코스메틱", "SAMYANG"),
    ("samnam-petrochemical", "삼남석유화학", "화학", "삼남석유화학"),
    ("samyang-chemical-corp", "삼양화성", "화학", "삼양화성"),
    ("samyang-innochem", "삼양이노켐", "화학", "SAMYANG INNOCHEM"),
    ("samyang-finetechnology", "삼양화인테크놀로지", "화학", "삼양화인테크놀로지"),
    ("samyang-kci", "삼양KCI", "화학", "SAMYANG KCI"),
    ("samyang-ncchem", "삼양엔씨켐", "화학", "삼양엔씨켐"),
    ("verdant", "VERDANT", "화학", "VERDANT"),
    ("samyang-biopharm", "삼양바이오팜", "의약바이오", "SAMYANG BIOPHARM"),
    ("samyang-packaging", "삼양패키징", "패키징", "SAMYANG PACKAGING"),
    ("samyang-data-system", "삼양데이타시스템", "IT", "SDS"),
]


def rows() -> list[dict]:
    unknown = {c for _, _, c, _ in AFFILIATES} - set(CATEGORIES)
    if unknown:
        raise SystemExit(f"CATEGORIES에 없는 카테고리입니다: {sorted(unknown)}")

    return [
        {
            "id": affiliate_id,
            "name": name,
            "category": category,
            "category_order": CATEGORIES.index(category),
            "logo_text": logo_text,
            "sort_order": i,
        }
        for i, (affiliate_id, name, category, logo_text) in enumerate(AFFILIATES)
    ]


def seed() -> None:
    Base.metadata.create_all(bind=engine, tables=[Affiliate.__table__])

    values = rows()
    with SessionLocal() as session:
        stmt = pg_insert(Affiliate).values(values)
        session.execute(stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "name": stmt.excluded.name,
                "category": stmt.excluded.category,
                "category_order": stmt.excluded.category_order,
                "logo_text": stmt.excluded.logo_text,
                "sort_order": stmt.excluded.sort_order,
            },
        ))
        session.execute(
            delete(Affiliate).where(Affiliate.id.notin_([v["id"] for v in values]))
        )
        session.commit()

    print(f"affiliates: {len(values)}건 적재 완료 (카테고리 {len(CATEGORIES)}종)")


if __name__ == "__main__":
    seed()
