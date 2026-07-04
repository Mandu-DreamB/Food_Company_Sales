import json
import time
from pathlib import Path
from .config import CACHE_DIR


def _cache_path(indicator_id: str) -> Path:
    return CACHE_DIR / f"{indicator_id}.json"


def read_cache(indicator_id: str, ttl_seconds: int) -> dict | None:
    path = _cache_path(indicator_id)
    if not path.exists():
        return None

    payload = json.loads(path.read_text(encoding="utf-8"))
    if time.time() - payload["fetched_at_epoch"] > ttl_seconds:
        return None

    return payload


def read_stale_cache(indicator_id: str) -> dict | None:
    path = _cache_path(indicator_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_cache(indicator_id: str, series: list[dict], fetched_at_iso: str, fetched_at_epoch: float) -> None:
    payload = {
        "series": series,
        "fetched_at": fetched_at_iso,
        "fetched_at_epoch": fetched_at_epoch,
    }
    _cache_path(indicator_id).write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
