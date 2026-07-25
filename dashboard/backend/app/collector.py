import logging
from datetime import datetime, timezone

from .config import missing_env
from .registry import INDICATORS, Indicator
from .store import read_cache, write_cache, write_error

logger = logging.getLogger(__name__)


def collect_one(indicator: Indicator, *, force: bool = False) -> str:
    """지표 하나를 갱신 시도. 반환값은 'skipped_missing_key' | 'skipped_fresh' | 'ok' | 'error'."""
    if missing_env(indicator.required_env):
        return "skipped_missing_key"

    if not force and read_cache(indicator.id, indicator.ttl_seconds) is not None:
        return "skipped_fresh"

    now = datetime.now(timezone.utc)
    try:
        series = indicator.fetch()
        write_cache(indicator.id, series, now)
    except Exception as exc:
        write_error(indicator.id, str(exc), now)
        logger.warning("indicator collect failed id=%s error=%s", indicator.id, exc)
        return "error"

    return "ok"


def collect_all(*, force: bool = False) -> dict[str, str]:
    """등록된 모든 지표를 순회하며 갱신. API 요청 경로가 아니라 스케줄러/배치에서만 호출한다."""
    return {indicator.id: collect_one(indicator, force=force) for indicator in INDICATORS}
