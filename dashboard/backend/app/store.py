from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from .db import SessionLocal
from .models import IndicatorPoint, IndicatorFetchLog


def _load(session, indicator_id: str, fetched_at: datetime) -> dict:
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

    return {"series": series, "fetched_at": fetched_at.isoformat()}


def read_cache(indicator_id: str, ttl_seconds: int) -> dict | None:
    with SessionLocal() as session:
        log = session.get(IndicatorFetchLog, indicator_id)
        if log is None:
            return None

        age = (datetime.now(timezone.utc) - log.fetched_at).total_seconds()
        if age > ttl_seconds:
            return None

        return _load(session, indicator_id, log.fetched_at)


def read_stale_cache(indicator_id: str) -> dict | None:
    with SessionLocal() as session:
        log = session.get(IndicatorFetchLog, indicator_id)
        if log is None:
            return None

        return _load(session, indicator_id, log.fetched_at)


def write_cache(indicator_id: str, series: list[dict], fetched_at_iso: str, fetched_at_epoch: float) -> None:
    fetched_at = datetime.fromtimestamp(fetched_at_epoch, tz=timezone.utc)

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
