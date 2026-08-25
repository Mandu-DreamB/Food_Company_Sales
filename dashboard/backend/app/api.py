from fastapi import APIRouter, HTTPException, Query

from .config import missing_env
from .registry import (
    AFFILIATE_CATEGORY_INDICATOR_CATEGORIES,
    AFFILIATE_OVERVIEW_SOURCES,
    AFFILIATE_OVERVIEWS,
    AFFILIATE_TOP_INDICATORS,
    INDICATORS,
    INDICATORS_BY_ID,
    Indicator,
)
from .store import read_affiliates, read_all_logs, read_briefing, read_indicator_briefing, read_stale_cache
from .schemas import AffiliateList, BriefingResult, IndicatorResult, IndicatorWithBriefing

router = APIRouter(prefix="/api")


@router.get("/affiliates", response_model=AffiliateList)
def list_affiliates():
    rows = read_affiliates()
    # 탭 순서는 category_order가 정한다. dict가 삽입 순서를 유지하므로 중복 제거와 정렬이 한 번에 끝난다.
    categories = list(dict.fromkeys(
        row["category"] for row in sorted(rows, key=lambda r: r["category_order"])
    ))
    for row in rows:
        row["overview"] = AFFILIATE_OVERVIEWS.get(row["id"])
        row["overview_sources"] = AFFILIATE_OVERVIEW_SOURCES.get(row["id"], [])
    return AffiliateList(categories=categories, affiliates=rows)


@router.get("/affiliates/{affiliate_id}/briefing", response_model=BriefingResult)
def get_affiliate_briefing(affiliate_id: str):
    if not any(a["id"] == affiliate_id for a in read_affiliates()):
        raise HTTPException(status_code=404, detail="affiliate not found")

    briefing = read_briefing(affiliate_id)
    if briefing is None:
        return BriefingResult(status="not_generated")

    return BriefingResult(status=briefing["status"], text=briefing["text"], generated_at=briefing["generated_at"])


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
def list_sources(affiliate_id: str | None = Query(None)):
    indicators = INDICATORS
    if affiliate_id is not None:
        affiliate = next((a for a in read_affiliates() if a["id"] == affiliate_id), None)
        if affiliate is None:
            raise HTTPException(status_code=404, detail="affiliate not found")
        relevant = set(AFFILIATE_CATEGORY_INDICATOR_CATEGORIES.get(affiliate["category"], []))
        indicators = [ind for ind in INDICATORS if ind.category in relevant]

    # 지표마다 DB를 왕복하면 N+1이 되어 느려지므로, 로그는 한 번의 쿼리로만 읽는다.
    logs = read_all_logs()
    return [
        _result(ind, log=logs.get(ind.id), missing=missing_env(ind.required_env))
        for ind in indicators
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


@router.get("/affiliates/{affiliate_id}/top-indicators", response_model=list[IndicatorWithBriefing])
def get_top_indicators(affiliate_id: str):
    """이 계열사와 가장 연관된 지표 3개(registry.AFFILIATE_TOP_INDICATORS)를 시계열 + AI 요약과
    함께 반환한다. 아직 큐레이션 안 된 계열사면 빈 리스트."""
    indicator_ids = AFFILIATE_TOP_INDICATORS.get(affiliate_id, [])
    results = []
    for indicator_id in indicator_ids:
        ind = INDICATORS_BY_ID.get(indicator_id)
        if ind is None:
            continue

        missing = missing_env(ind.required_env)
        if missing:
            base = _result(ind, log=None, missing=missing)
        else:
            cached = read_stale_cache(indicator_id)
            base = (
                _result(ind, log=None, missing=[])
                if cached is None
                else _result(ind, log=cached, missing=[], series=cached["series"])
            )

        briefing_row = read_indicator_briefing(indicator_id)
        briefing = (
            BriefingResult(status="not_generated")
            if briefing_row is None
            else BriefingResult(
                status=briefing_row["status"], text=briefing_row["text"], generated_at=briefing_row["generated_at"]
            )
        )
        results.append(IndicatorWithBriefing(**base.model_dump(), briefing=briefing))

    return results
