"""계열사별 AI 브리핑 생성.

계열사에 매핑된 관련 지표들의 최근 값/변화율을 계산해 "사실 목록"을 만들고, 그 목록만 근거로
LLM에게 2~4문장 요약을 쓰게 한다. 실제 뉴스/공시를 실시간으로 읽어오는 게 아니라 이미 수집된
지표 시계열의 변화를 요약하는 방식이라, "눈에 띄는 지표 동향 브리핑"에 가깝다.

요청 경로에서 호출하지 않는다 — LLM 호출은 느리고 비용이 들어서, 지표 수집과 같은 이유로
스케줄러가 미리 생성해 DB에 캐싱해 둔 것만 API가 읽어서 돌려준다.
"""
import logging
import os
from datetime import datetime, timezone

from openai import OpenAI

from .registry import AFFILIATE_CATEGORY_INDICATOR_CATEGORIES, AFFILIATE_TOP_INDICATORS, INDICATORS, INDICATORS_BY_ID
from .store import (
    read_affiliates,
    read_briefing,
    read_indicator_briefing,
    read_stale_cache,
    write_briefing,
    write_briefing_error,
    write_indicator_briefing,
    write_indicator_briefing_error,
)

logger = logging.getLogger(__name__)

BRIEFING_TTL_SECONDS = 24 * 3600
BRIEFING_MODEL = "gpt-4o-mini"

_client: OpenAI | None = None


def _get_client() -> OpenAI | None:
    global _client
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    if _client is None:
        _client = OpenAI(api_key=api_key)
    return _client


def _series_fact(indicator_title: str, series_name: str, points: list[dict]) -> str | None:
    """시리즈 하나의 최근 동향을 한 줄 사실로 요약. 관측치가 너무 적으면 None."""
    valid = [p for p in points if p["value"] is not None]
    if len(valid) < 2:
        return None

    latest = valid[-1]
    baseline = valid[max(0, len(valid) - 1 - 12)]  # 대략 최근 12개 관측치(월간 지표면 약 1년) 전
    if baseline["value"] == 0:
        return None

    change_pct = (latest["value"] - baseline["value"]) / abs(baseline["value"]) * 100

    recent_window = valid[-36:]
    recent_values = [p["value"] for p in recent_window]
    marker = ""
    if len(recent_window) > 3:
        if latest["value"] >= max(recent_values):
            marker = " [최근 구간 중 최고치]"
        elif latest["value"] <= min(recent_values):
            marker = " [최근 구간 중 최저치]"

    label = indicator_title if series_name == indicator_title else f"{indicator_title} - {series_name}"
    return f"{label}: {latest['date']} 기준 {latest['value']:,.2f} ({baseline['date']} 대비 {change_pct:+.1f}%){marker}"


def _gather_facts(category: str) -> list[str]:
    relevant = set(AFFILIATE_CATEGORY_INDICATOR_CATEGORIES.get(category, []))
    facts = []
    for ind in INDICATORS:
        if ind.category not in relevant:
            continue
        cached = read_stale_cache(ind.id)
        if cached is None or cached["status"] != "ok":
            continue
        for s in cached["series"]:
            fact = _series_fact(ind.title, s["name"], s["points"])
            if fact:
                facts.append(fact)
    return facts


PROMPT_TEMPLATE = """당신은 삼양그룹 계열사를 담당하는 애널리스트입니다. 아래는 "{name}"({category} 업종)과 \
관련도가 높은 경제지표들의 최근 동향입니다.

{facts}

이 데이터만 근거로, 이 계열사 입장에서 눈여겨볼 만한 최근 상황을 2~4문장의 한국어 브리핑으로 작성하세요.
- 숫자를 인용할 때는 위에 주어진 값만 사용하고 새로 지어내지 마세요.
- 특별히 눈에 띄는 변화가 없으면 억지로 의미를 부여하지 말고 그렇다고 담백하게 말하세요.
- 존댓말로, 간결하게 작성하세요."""


def generate_affiliate_briefing(name: str, category: str) -> str:
    client = _get_client()
    if client is None:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    facts = _gather_facts(category)
    if not facts:
        return f"{name}과 관련된 지표 데이터가 아직 충분하지 않아 브리핑을 생성할 수 없습니다."

    prompt = PROMPT_TEMPLATE.format(name=name, category=category, facts="\n".join(f"- {f}" for f in facts))
    response = client.chat.completions.create(
        model=BRIEFING_MODEL,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def _is_fresh(affiliate_id: str) -> bool:
    briefing = read_briefing(affiliate_id)
    if briefing is None or briefing["status"] != "ok":
        return False
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(briefing["generated_at"])).total_seconds()
    return age <= BRIEFING_TTL_SECONDS


def generate_all_briefings(*, force: bool = False) -> dict[str, str]:
    """전체 계열사의 브리핑을 갱신. 스케줄러 전용 — API 요청 경로에서는 호출하지 않는다.
    반환값은 'skipped_fresh' | 'ok' | 'error'."""
    results = {}
    for affiliate in read_affiliates():
        affiliate_id = affiliate["id"]
        if not force and _is_fresh(affiliate_id):
            results[affiliate_id] = "skipped_fresh"
            continue

        now = datetime.now(timezone.utc)
        try:
            text = generate_affiliate_briefing(affiliate["name"], affiliate["category"])
            write_briefing(affiliate_id, text, now)
            results[affiliate_id] = "ok"
        except Exception as exc:
            write_briefing_error(affiliate_id, str(exc), now)
            logger.warning("briefing generation failed id=%s error=%s", affiliate_id, exc)
            results[affiliate_id] = "error"

    return results


INDICATOR_PROMPT_TEMPLATE = """당신은 경제지표를 요약하는 애널리스트입니다. 아래는 "{title}" 지표의 \
최근 동향입니다.

{facts}

이 데이터만 근거로, 1~2문장의 간결한 한국어 요약을 작성하세요.
- 숫자를 인용할 때는 위에 주어진 값만 사용하고 새로 지어내지 마세요.
- 특별히 눈에 띄는 변화가 없으면 억지로 의미를 부여하지 말고 그렇다고 담백하게 말하세요.
- 존댓말로 작성하세요."""


def generate_indicator_briefing(indicator_title: str, indicator_id: str) -> str:
    client = _get_client()
    if client is None:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    cached = read_stale_cache(indicator_id)
    facts = []
    if cached is not None and cached["status"] == "ok":
        for s in cached["series"]:
            fact = _series_fact(indicator_title, s["name"], s["points"])
            if fact:
                facts.append(fact)

    if not facts:
        return f"{indicator_title} 지표 데이터가 아직 충분하지 않아 요약을 생성할 수 없습니다."

    prompt = INDICATOR_PROMPT_TEMPLATE.format(title=indicator_title, facts="\n".join(f"- {f}" for f in facts))
    response = client.chat.completions.create(
        model=BRIEFING_MODEL,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def _indicator_is_fresh(indicator_id: str) -> bool:
    briefing = read_indicator_briefing(indicator_id)
    if briefing is None or briefing["status"] != "ok":
        return False
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(briefing["generated_at"])).total_seconds()
    return age <= BRIEFING_TTL_SECONDS


def generate_all_indicator_briefings(*, force: bool = False) -> dict[str, str]:
    """AFFILIATE_TOP_INDICATORS에 등장하는 지표만 갱신 (계열사 여러 곳에서 같은 지표를 써도
    한 번만 생성한다). 스케줄러 전용 — API 요청 경로에서는 호출하지 않는다.
    반환값은 'skipped_fresh' | 'ok' | 'error'."""
    results = {}
    indicator_ids = sorted({ind_id for ids in AFFILIATE_TOP_INDICATORS.values() for ind_id in ids})

    for indicator_id in indicator_ids:
        if not force and _indicator_is_fresh(indicator_id):
            results[indicator_id] = "skipped_fresh"
            continue

        indicator = INDICATORS_BY_ID.get(indicator_id)
        if indicator is None:
            continue

        now = datetime.now(timezone.utc)
        try:
            text = generate_indicator_briefing(indicator.title, indicator_id)
            write_indicator_briefing(indicator_id, text, now)
            results[indicator_id] = "ok"
        except Exception as exc:
            write_indicator_briefing_error(indicator_id, str(exc), now)
            logger.warning("indicator briefing generation failed id=%s error=%s", indicator_id, exc)
            results[indicator_id] = "error"

    return results
