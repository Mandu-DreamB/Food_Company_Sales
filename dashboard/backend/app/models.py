from sqlalchemy import Column, Integer, String, Date, Float, DateTime, Text, UniqueConstraint
from .db import Base


class IndicatorPoint(Base):
    """지표 하나의 시계열 관측값 한 개 (indicator_id + series_name + date 당 1행)."""

    __tablename__ = "indicator_points"

    id = Column(Integer, primary_key=True)
    indicator_id = Column(String, nullable=False, index=True)
    series_name = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    value = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("indicator_id", "series_name", "date", name="uq_indicator_point"),
    )


class Affiliate(Base):
    """삼양그룹 계열사 1곳 (랜딩 페이지의 계열사 카드 1장).

    프론트에 하드코딩돼 있던 AFFILIATES/CATEGORIES를 대체한다. 탭(카테고리)과 카드의 노출 순서까지
    DB가 결정할 수 있도록 category_order/sort_order를 함께 둔다.
    """

    __tablename__ = "affiliates"

    id = Column(String, primary_key=True)  # 슬러그. 프론트 라우팅 키로 그대로 쓴다.
    name = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    category_order = Column(Integer, nullable=False)
    logo_text = Column(String, nullable=False)
    sort_order = Column(Integer, nullable=False)


class IndicatorFetchLog(Base):
    """지표별 마지막 수집 시각/상태 (TTL 캐시 판단 + 대시보드 상태 표시용)."""

    __tablename__ = "indicator_fetch_log"

    indicator_id = Column(String, primary_key=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False)
    error = Column(Text, nullable=True)


class AffiliateBriefing(Base):
    """계열사 1곳의 최신 AI 브리핑 (관련 지표 최근 동향을 LLM이 요약한 텍스트).
    지표 수집과 같은 이유로 요청 경로에서 생성하지 않고 스케줄러가 미리 채워 둔다."""

    __tablename__ = "affiliate_briefings"

    affiliate_id = Column(String, primary_key=True)
    text = Column(Text, nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False)
    error = Column(Text, nullable=True)
