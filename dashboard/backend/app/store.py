from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from .db import SessionLocal
from .models import Affiliate, AffiliateBriefing, IndicatorPoint, IndicatorFetchLog


def read_affiliates() -> list[dict]:
    """계열사 전체를 카드 노출 순서대로 반환. (scripts/seed_affiliates.py가 채워 둔 테이블)"""
    with SessionLocal() as session:
        rows = session.scalars(select(Affiliate).order_by(Affiliate.sort_order)).all()
        return [
            {
                "id": row.id,
                "name": row.name,
                "category": row.category,
                "category_order": row.category_order,
                "logo_text": row.logo_text,
            }
            for row in rows
        ]


def _load(session, indicator_id: str, log: IndicatorFetchLog) -> dict:
    rows = session.scalars(
        select(IndicatorPoint).where(IndicatorPoint.indicator_id == indicator_id)
    ).all()

    series_map: dict[str, list[dict]] = {}
    for row in rows:
        series_map.setdefault(row.series_name, []).append(
            {"date": row.date.isoformat(), "value": row.value}
        )

    series = [
        {"name": name, "points": sorted(points, key=lambda p: p["date"])}
        for name, points in series_map.items()
    ]

    return {
        "series": series,
        "fetched_at": log.fetched_at.isoformat(),
        "status": log.status,
        "error": log.error,
    }


def read_cache(indicator_id: str, ttl_seconds: int) -> dict | None:
    """TTL 이내의 캐시만 반환. 스케줄러가 재수집 여부를 판단할 때 사용."""
    with SessionLocal() as session:
        log = session.get(IndicatorFetchLog, indicator_id)
        if log is None:
            return None

        age = (datetime.now(timezone.utc) - log.fetched_at).total_seconds()
        if age > ttl_seconds:
            return None

        return _load(session, indicator_id, log)


def read_stale_cache(indicator_id: str) -> dict | None:
    """TTL과 무관하게 DB에 있는 마지막 수집 결과(시계열 포함)를 반환. 지표 상세 조회에서만 사용."""
    with SessionLocal() as session:
        log = session.get(IndicatorFetchLog, indicator_id)
        if log is None:
            return None

        return _load(session, indicator_id, log)


def read_all_logs() -> dict[str, dict]:
    """모든 지표의 상태(status/error/fetched_at)만 단일 쿼리로 반환. 시계열 포인트는 읽지 않는다.
    목록 화면은 포인트가 필요 없는데도 지표마다 DB를 왕복하면 N+1이 되어 느려지므로, 목록 조회는
    반드시 이 함수로 한 번에 처리한다."""
    with SessionLocal() as session:
        logs = session.scalars(select(IndicatorFetchLog)).all()
        return {
            log.indicator_id: {
                "status": log.status,
                "error": log.error,
                "fetched_at": log.fetched_at.isoformat(),
            }
            for log in logs
        }


def write_cache(indicator_id: str, series: list[dict], fetched_at: datetime) -> None:
    with SessionLocal() as session:
        session.execute(delete(IndicatorPoint).where(IndicatorPoint.indicator_id == indicator_id))

        for s in series:
            for point in s["points"]:
                if point["date"] is None:
                    continue
                session.add(IndicatorPoint(
                    indicator_id=indicator_id,
                    series_name=s["name"],
                    date=datetime.strptime(point["date"], "%Y-%m-%d").date(),
                    value=point["value"],
                ))

        stmt = pg_insert(IndicatorFetchLog).values(
            indicator_id=indicator_id, fetched_at=fetched_at, status="ok", error=None,
        ).on_conflict_do_update(
            index_elements=["indicator_id"],
            set_={"fetched_at": fetched_at, "status": "ok", "error": None},
        )
        session.execute(stmt)
        session.commit()


def write_error(indicator_id: str, error: str, attempted_at: datetime) -> None:
    """수집 실패 기록. IndicatorPoint(과거 데이터)와 마지막 '성공' 시각(fetched_at)은 건드리지 않고
    상태만 error로 남긴다. 아직 한 번도 성공한 적이 없으면 시도 시각을 기록해 not_fetched와 구분한다."""
    with SessionLocal() as session:
        log = session.get(IndicatorFetchLog, indicator_id)
        if log is None:
            session.add(IndicatorFetchLog(
                indicator_id=indicator_id, fetched_at=attempted_at, status="error", error=error,
            ))
        else:
            log.status = "error"
            log.error = error
        session.commit()


def read_briefing(affiliate_id: str) -> dict | None:
    with SessionLocal() as session:
        row = session.get(AffiliateBriefing, affiliate_id)
        if row is None:
            return None
        return {
            "text": row.text,
            "generated_at": row.generated_at.isoformat(),
            "status": row.status,
            "error": row.error,
        }


def write_briefing(affiliate_id: str, text: str, generated_at: datetime) -> None:
    with SessionLocal() as session:
        stmt = pg_insert(AffiliateBriefing).values(
            affiliate_id=affiliate_id, text=text, generated_at=generated_at, status="ok", error=None,
        ).on_conflict_do_update(
            index_elements=["affiliate_id"],
            set_={"text": text, "generated_at": generated_at, "status": "ok", "error": None},
        )
        session.execute(stmt)
        session.commit()


def write_briefing_error(affiliate_id: str, error: str, attempted_at: datetime) -> None:
    """브리핑 생성 실패 기록. 마지막 성공 텍스트/시각은 건드리지 않고 상태만 error로 남긴다
    (write_error와 같은 이유 — 화면에는 마지막으로 성공한 브리핑을 계속 보여줄 수 있게)."""
    with SessionLocal() as session:
        row = session.get(AffiliateBriefing, affiliate_id)
        if row is None:
            session.add(AffiliateBriefing(
                affiliate_id=affiliate_id, text=None, generated_at=attempted_at, status="error", error=error,
            ))
        else:
            row.status = "error"
            row.error = error
        session.commit()
