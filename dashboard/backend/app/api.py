from fastapi import APIRouter, HTTPException

from .config import missing_env
from .registry import INDICATORS, INDICATORS_BY_ID, Indicator
from .store import read_all_logs, read_stale_cache
from .schemas import IndicatorResult

router = APIRouter(prefix="/api")


def _result(
    ind: Indicator, *, log: dict | None, missing: list[str], series: list[dict] | None = None
) -> IndicatorResult:
    if missing:
        return IndicatorResult(
            id=ind.id, title=ind.title, category=ind.category, unit=ind.unit,
            frequency=ind.frequency, missing_env=missing, status="missing_key",
            error=f"{', '.join(missing)} 환경변수가 설정되지 않았습니다.", series=[],
        )

    if log is None:
        return IndicatorResult(
            id=ind.id, title=ind.title, category=ind.category, unit=ind.unit,
            frequency=ind.frequency, missing_env=[], status="not_fetched", series=[],
        )

    return IndicatorResult(
        id=ind.id, title=ind.title, category=ind.category, unit=ind.unit,
        frequency=ind.frequency, missing_env=[], status=log["status"],
        error=log["error"], fetched_at=log["fetched_at"], series=series or [],
    )


@router.get("/sources", response_model=list[IndicatorResult])
def list_sources():
    # 지표마다 DB를 왕복하면 N+1이 되어 느려지므로, 로그는 한 번의 쿼리로만 읽는다.
    logs = read_all_logs()
    return [
        _result(ind, log=logs.get(ind.id), missing=missing_env(ind.required_env))
        for ind in INDICATORS
    ]


@router.get("/sources/{indicator_id}", response_model=IndicatorResult)
def get_source(indicator_id: str):
    ind = INDICATORS_BY_ID.get(indicator_id)
    if ind is None:
        raise HTTPException(status_code=404, detail="indicator not found")

    missing = missing_env(ind.required_env)
    if missing:
        return _result(ind, log=None, missing=missing)

    cached = read_stale_cache(ind.id)
    if cached is None:
        return _result(ind, log=None, missing=[])

    return _result(ind, log=cached, missing=[], series=cached["series"])
