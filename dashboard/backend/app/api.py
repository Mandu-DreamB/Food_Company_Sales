from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from .config import missing_env
from .registry import INDICATORS, INDICATORS_BY_ID
from .cache import read_cache, read_stale_cache, write_cache
from .schemas import IndicatorResult

router = APIRouter(prefix="/api")


@router.get("/sources", response_model=list[IndicatorResult])
def list_sources():
    results = []
    for ind in INDICATORS:
        missing = missing_env(ind.required_env)
        cached = read_stale_cache(ind.id)
        status = "missing_key" if missing else ("cached" if cached else "not_fetched")
        results.append(IndicatorResult(
            id=ind.id, title=ind.title, category=ind.category, unit=ind.unit,
            frequency=ind.frequency, missing_env=missing, status=status,
            fetched_at=cached["fetched_at"] if cached else None, series=[],
        ))
    return results


@router.get("/sources/{indicator_id}", response_model=IndicatorResult)
def get_source(indicator_id: str, refresh: bool = False):
    ind = INDICATORS_BY_ID.get(indicator_id)
    if ind is None:
        raise HTTPException(status_code=404, detail="indicator not found")

    missing = missing_env(ind.required_env)
    if missing:
        return IndicatorResult(
            id=ind.id, title=ind.title, category=ind.category, unit=ind.unit,
            frequency=ind.frequency, missing_env=missing, status="missing_key",
            error=f"{', '.join(missing)} 환경변수가 설정되지 않았습니다.", series=[],
        )

    if not refresh:
        cached = read_cache(ind.id, ind.ttl_seconds)
        if cached:
            return IndicatorResult(
                id=ind.id, title=ind.title, category=ind.category, unit=ind.unit,
                frequency=ind.frequency, missing_env=[], status="ok",
                fetched_at=cached["fetched_at"], series=cached["series"],
            )

    try:
        series = ind.fetch()
        now = datetime.now(timezone.utc)
        write_cache(ind.id, series, now.isoformat(), now.timestamp())
        return IndicatorResult(
            id=ind.id, title=ind.title, category=ind.category, unit=ind.unit,
            frequency=ind.frequency, missing_env=[], status="ok",
            fetched_at=now.isoformat(), series=series,
        )
    except Exception as exc:
        stale = read_stale_cache(ind.id)
        return IndicatorResult(
            id=ind.id, title=ind.title, category=ind.category, unit=ind.unit,
            frequency=ind.frequency, missing_env=[], status="error",
            error=str(exc), fetched_at=stale["fetched_at"] if stale else None,
            series=stale["series"] if stale else [],
        )
