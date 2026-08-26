"""DB 조회형 챗봇 — 자연어 질문을 읽기 전용 SQL 한 방으로 바꿔 실행하고, 그 결과로 답한다.

RAG 챗봇(`RAG/api.py`, 공시 문서 기반)과 달리 이쪽은 대시보드가 수집해 둔 지표 시계열 DB를
직접 조회한다. LLM 호출 2번(SQL 생성 → 결과 서술) + 쿼리 1번.

안전장치는 셋뿐이다: SELECT/WITH로 시작하는 단일 문장만 허용, 읽기 전용 트랜잭션,
statement_timeout. 앱이 쓰는 DB 계정 자체는 쓰기 권한이 있으므로 마지막 방어선은 READ ONLY다.
"""
import json
import logging
import re
from bisect import bisect_left
from datetime import date, timedelta
from functools import lru_cache

from sqlalchemy import text

from . import models  # noqa: F401  (Base.registry에 모델 등록 — _tables_prompt가 이걸 읽는다)
from .briefing import BRIEFING_MODEL, _get_client
from .db import Base, SessionLocal
from .registry import INDICATORS, INDICATORS_BY_ID

logger = logging.getLogger(__name__)

MAX_ROWS = 200

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy|call|do|merge|vacuum)\b",
    re.IGNORECASE,
)


def _clean_sql(raw: str) -> str:
    """LLM이 뱉은 텍스트에서 실행 가능한 단일 SELECT만 꺼낸다. 아니면 ValueError."""
    sql = re.sub(r"^```(?:sql)?|```$", "", raw.strip(), flags=re.IGNORECASE | re.MULTILINE).strip()
    sql = sql.rstrip(";").strip()

    if ";" in sql:
        raise ValueError("여러 개의 SQL 문장은 실행할 수 없습니다.")
    if not re.match(r"^(select|with)\b", sql, re.IGNORECASE):
        raise ValueError("조회(SELECT) 질의만 실행할 수 있습니다.")
    if _FORBIDDEN.search(sql):
        raise ValueError("데이터를 변경하는 질의는 실행할 수 없습니다.")
    return sql


def _run_sql(sql: str) -> list[dict]:
    with SessionLocal() as session:
        session.execute(text("SET TRANSACTION READ ONLY"))
        session.execute(text("SET LOCAL statement_timeout = '10s'"))
        rows = session.execute(text(sql)).mappings().all()
        return [{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in row.items()}
                for row in rows[:MAX_ROWS]]


@lru_cache(maxsize=1)
def _tables_prompt() -> str:
    """테이블/컬럼 목록을 models.py에서 그대로 뽑는다. 프롬프트에 스키마를 베껴 두면 모델이 바뀔 때
    조용히 어긋나므로, 설명글도 각 모델의 docstring 첫 줄을 재사용한다."""
    lines = []
    for mapper in sorted(Base.registry.mappers, key=lambda m: m.class_.__tablename__):
        table = mapper.class_.__table__
        columns = ", ".join(f"{c.name} {c.type}" for c in table.columns)
        doc = (mapper.class_.__doc__ or "").strip().split("\n")[0]
        lines.append(f"- {table.name}({columns}) — {doc}")
    return "\n".join(lines)


@lru_cache(maxsize=1)
def _schema_prompt() -> str:
    """지표 목록 + 실제 저장된 series_name까지 붙여야 LLM이 WHERE 절을 맞게 쓴다.
    series_name은 수집 소스가 바뀌지 않는 한 고정이라 프로세스 단위로 캐싱한다."""
    with SessionLocal() as session:
        pairs = session.execute(
            text("SELECT DISTINCT indicator_id, series_name FROM indicator_points ORDER BY 1, 2")
        ).all()

    series_by_id: dict[str, list[str]] = {}
    for indicator_id, series_name in pairs:
        series_by_id.setdefault(indicator_id, []).append(series_name)

    with SessionLocal() as session:
        # status는 값이 몇 개 안 되는데 LLM이 모르면 'failed' 같은 없는 값으로 필터를 건다.
        statuses = [r[0] for r in session.execute(
            text("SELECT DISTINCT status FROM indicator_fetch_log")).all()]

    lines = [f"indicator_fetch_log.status에 실제로 들어 있는 값: {', '.join(statuses) or '(없음)'}", ""]
    for ind in INDICATORS:
        names = series_by_id.get(ind.id, [])
        suffix = f" | series_name: {', '.join(names)}" if names else " | (수집된 데이터 없음)"
        lines.append(f"- {ind.id}: {ind.title} ({ind.category}, 단위 {ind.unit}, {ind.frequency}){suffix}")

    return "\n".join(lines)


SQL_PROMPT = """당신은 PostgreSQL 전문가입니다. 아래 스키마를 보고 사용자 질문에 답할 수 있는 SELECT 문을 \
정확히 하나만 작성하세요.

테이블:
{tables}

indicator_points에 들어 있는 indicator_id와 series_name:
{schema}

규칙:
- SELECT(또는 WITH) 문 하나만. 설명, 주석, 코드펜스 없이 SQL만 출력하세요.
- 항상 LIMIT을 붙이고 {max_rows} 이하로 두세요.
- value가 NULL인 행은 대개 제외하세요.
- 질문이 특정 시점을 말하지 않으면 최신 데이터를 기준으로 하세요.
- affiliates.id는 영문 슬러그(samyang-holdings 등)이고 한글 회사명은 name 컬럼입니다. 회사명으로 찾을 때는 name을 LIKE로 매칭하세요.
- 계열사와 지표를 잇는 다리는 correlations 테이블입니다. affiliates.id = correlations.affiliate_id,
  (correlations.indicator_id, correlations.series_name) = (indicator_points.indicator_id, indicator_points.series_name)로 조인하세요.
- correlations의 상관계수는 "관계가 있다"는 증거가 아닙니다. 표본이 분기 18~26개뿐이라 귀무 기준선을
  넘지 못했습니다. r을 인용할 때는 반드시 survived와 trend_r를 함께 언급하고, survived가 false거나
  |trend_r| > 0.5면 "추세가 같이 움직인 것일 뿐 인과로 볼 수 없다"고 덧붙이세요.
- correlations에 없는 계열사(분석 대상이 아니었던 곳)는 그 사실을 그대로 말하세요.
- indicator_points는 관측값 테이블이라 한 지표에 수백~수천 행입니다. 상관계수나 지표 목록만
  필요하면 correlations만 조회하세요. 조인하면 행이 폭발합니다. 실제 값이 필요할 때만 조인하고
  그때는 집계(MAX(date), AVG(value) 등)하거나 서브쿼리로 최신 1행만 뽑으세요.
- indicator_id의 한글 이름은 아래 지표 목록에 있습니다. 답변에는 그 이름을 쓰세요.
- 스키마로 답할 수 없는 질문이면 SQL 대신 정확히 `UNANSWERABLE` 한 단어만 출력하세요.

질문: {question}"""

ANSWER_PROMPT = """사용자 질문에 아래 DB 조회 결과만 근거로 답하고, 차트로 보여줄 만하면 차트 스펙도 함께 내세요.

질문: {question}
실행한 SQL: {sql}
결과({row_count}행): {rows}

- 결과에 없는 숫자는 지어내지 마세요.
- 결과가 비어 있으면 해당 데이터가 없다고 말하세요.
- 표가 필요할 만큼 길면 핵심 몇 줄만 요약하세요.
- chart를 채웠으면 answer에 "차트 스펙" 같은 내부 용어를 쓰지 말고, 그 차트가 무엇을 보여주는지와
  눈에 띄는 점을 한두 문장으로 쓰세요. 차트는 대시보드에 카드로 추가된다고 안내하세요.

JSON 하나만 출력하세요: {{"answer": "한국어 존댓말 답변", "chart": null 또는 차트 스펙}}
차트 스펙 형식:
{{"title": "차트 제목", "transform": "none" 또는 "yoy",
  "series": [{{"indicator_id": "...", "series_name": "..."}}],
  "from": "YYYY-MM-DD" 또는 null, "to": "YYYY-MM-DD" 또는 null}}
- 시계열 추이를 묻거나 "그래프/차트로 보여줘"라고 하면 chart를 채우세요. 단순 개수·이름 조회면 null.
- indicator_id와 series_name은 아래 지표 목록에 있는 값을 그대로 쓰세요. 지어내지 마세요.
- 여러 지표를 비교하라고 하면 series에 여러 개를 넣으세요(단위가 달라도 화면에서 지수화됩니다).
- transform "yoy"는 전년동기대비 증감률(%)입니다. 추세/계절성을 걷어내고 볼 때만 쓰세요.
- from을 비우면 전체 기간입니다. "최근 N년"이면 from을 계산해 넣으세요.

쓸 수 있는 indicator_id / series_name:
{schema}

답변 작성 규칙:
- SQL이 correlations 테이블을 건드렸다면(수치를 인용했든 안 했든) "영향을 미친다", "요인이다" 같은
  인과 표현을 쓰지 말고 "같이 움직였다" 정도로만 쓰세요. 그리고 표본이 분기 20여 개뿐이라 통계적으로
  확인된 관계는 아니라는 단서를 반드시 마지막에 한 문장 붙이세요."""


def _yoy(points: list[dict]) -> list[dict]:
    """전년동기대비 증감률(%). 지표마다 주기가 달라서(일/월/분기) 고정 lag를 쓸 수 없으므로,
    1년 전 날짜에 가장 가까운 관측치를 찾아 비교한다. 20일 이상 벌어지면(= 그 시점 데이터가
    아예 없으면) 버린다 — 월간 지표에서 옆 달을 "1년 전"으로 잘못 집는 걸 막는다."""
    dates = [p["date"] for p in points]
    out = []
    for i, p in enumerate(points):
        if p["value"] is None:
            continue
        target = date.fromisoformat(p["date"]) - timedelta(days=365)
        j = bisect_left(dates, target.isoformat())
        candidates = [k for k in (j - 1, j) if 0 <= k < i and points[k]["value"]]
        if not candidates:
            continue
        base = min(candidates, key=lambda k: abs((date.fromisoformat(dates[k]) - target).days))
        if abs((date.fromisoformat(dates[base]) - target).days) > 20:
            continue
        prev = points[base]["value"]
        out.append({"date": p["date"], "value": (p["value"] - prev) / abs(prev) * 100})
    return out


def _resolve_chart(spec: dict) -> dict | None:
    """LLM이 낸 스펙을 실제 시계열로 바꾼다. 데이터는 DB에서 직접 읽으므로 LLM이 값을 지어낼 수 없다."""
    wanted = [(s.get("indicator_id"), s.get("series_name")) for s in spec.get("series") or []]
    wanted = [(i, n) for i, n in wanted if i and n]
    if not wanted:
        return None

    conditions = " OR ".join(
        f"(indicator_id = :i{k} AND series_name = :n{k})" for k in range(len(wanted))
    )
    params = {f"{p}{k}": v for k, (i, n) in enumerate(wanted) for p, v in (("i", i), ("n", n))}
    clauses = [f"({conditions})", "value IS NOT NULL"]
    for key, op in (("from", ">="), ("to", "<=")):
        if spec.get(key):
            clauses.append(f"date {op} :{key}_date")
            params[f"{key}_date"] = spec[key]

    sql = (f"SELECT indicator_id, series_name, date, value FROM indicator_points "
           f"WHERE {' AND '.join(clauses)} ORDER BY date")
    with SessionLocal() as session:
        session.execute(text("SET TRANSACTION READ ONLY"))
        rows = session.execute(text(sql), params).all()

    grouped: dict[tuple[str, str], list[dict]] = {}
    for indicator_id, series_name, date, value in rows:
        grouped.setdefault((indicator_id, series_name), []).append(
            {"date": date.isoformat(), "value": value})

    multi = len({i for i, _ in grouped}) > 1
    transform = spec.get("transform") or "none"
    series = []
    for (indicator_id, series_name), points in grouped.items():
        title = INDICATORS_BY_ID[indicator_id].title if indicator_id in INDICATORS_BY_ID else indicator_id
        name = f"{title} - {series_name}" if multi else series_name
        series.append({"name": name, "points": _yoy(points) if transform == "yoy" else points})

    if not series:
        return None
    units = {INDICATORS_BY_ID[i].unit for i, _ in grouped if i in INDICATORS_BY_ID}
    return {
        "title": spec.get("title") or "조회 결과",
        "unit": "% (전년동기대비)" if transform == "yoy" else (units.pop() if len(units) == 1 else "지표별 상이"),
        "transform": transform,
        "series": series,
    }


def answer_question(question: str) -> dict:
    client = _get_client()
    if client is None:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")

    raw = client.chat.completions.create(
        model=BRIEFING_MODEL,
        temperature=0,
        messages=[{"role": "user", "content": SQL_PROMPT.format(
            tables=_tables_prompt(), schema=_schema_prompt(), max_rows=MAX_ROWS, question=question)}],
    ).choices[0].message.content.strip()

    if raw.upper().startswith("UNANSWERABLE"):
        return {"answer": "수집된 지표 데이터로는 답할 수 없는 질문입니다. 지표·계열사 관련해서 다시 물어봐 주세요.",
                "sql": None}

    sql = _clean_sql(raw)
    logger.info("db-chat sql=%s", sql)
    rows = _run_sql(sql)

    reply = client.chat.completions.create(
        model=BRIEFING_MODEL,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": ANSWER_PROMPT.format(
            question=question, schema=_schema_prompt(), sql=sql, row_count=len(rows),
            rows=json.dumps(rows, ensure_ascii=False)[:6000])}],
    ).choices[0].message.content

    parsed = json.loads(reply)
    chart = None
    if isinstance(parsed.get("chart"), dict):
        try:
            chart = _resolve_chart(parsed["chart"])
        except Exception as exc:  # 차트는 부가 정보라 실패해도 답변은 그대로 돌려준다
            logger.warning("chart resolve failed spec=%s error=%s", parsed["chart"], exc)

    return {"answer": (parsed.get("answer") or "").strip(), "sql": sql, "chart": chart}


if __name__ == "__main__":
    assert _clean_sql("```sql\nSELECT 1;\n```") == "SELECT 1"
    assert _clean_sql("  select * from affiliates limit 5  ") == "select * from affiliates limit 5"
    monthly = [{"date": f"20{y:02d}-{m:02d}-01", "value": 100.0 + m} for y in (23, 24) for m in range(1, 13)]
    yoy = _yoy(monthly)
    assert len(yoy) == 12 and yoy[0]["date"] == "2024-01-01", yoy[:2]
    assert all(abs(p["value"]) < 1e-9 for p in yoy), yoy  # 매년 같은 패턴이면 증감률 0
    assert _yoy([{"date": "2024-01-01", "value": 1.0}]) == []  # 1년치 미만이면 빈 결과

    for bad in ["DELETE FROM affiliates", "SELECT 1; DROP TABLE affiliates", "UPDATE affiliates SET name='x'",
                "SELECT 1; SELECT 2", "탈세요 SELECT 1"]:
        try:
            _clean_sql(bad)
            raise AssertionError(f"통과하면 안 됨: {bad}")
        except ValueError:
            pass
    print("ok")
