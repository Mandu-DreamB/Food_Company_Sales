from sqlalchemy import Boolean, Column, Integer, String, Date, Float, DateTime, Text, UniqueConstraint
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


class IndicatorBriefing(Base):
    """지표 1개의 최신 AI 요약 (registry.AFFILIATE_TOP_INDICATORS에 등장하는 지표만 생성).
    AffiliateBriefing과 같은 이유로 요청 경로에서 생성하지 않고 스케줄러가 미리 채워 둔다."""

    __tablename__ = "indicator_briefings"

    indicator_id = Column(String, primary_key=True)
    text = Column(Text, nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False)
    error = Column(Text, nullable=True)


class Correlation(Base):
    """계열사 매출 × 지표 상관계수 (mandu/Eda/run_correlation.py 산출). survived=False거나 |trend_r|이 0.5를 넘으면 추세동조이므로 관계가 있다고 해석하면 안 된다."""

    __tablename__ = "correlations"

    affiliate_id = Column(String, primary_key=True)
    indicator_id = Column(String, primary_key=True)
    series_name = Column(String, primary_key=True)
    level_r = Column(Float, nullable=True)        # 레벨(원계열) 피어슨
    level_spearman = Column(Float, nullable=True)
    n = Column(Integer, nullable=True)            # 레벨 상관의 표본 구간 수
    change_r = Column(Float, nullable=True)       # 전기대비 변화율끼리의 피어슨
    trend_r = Column(Float, nullable=True)        # 지표와 시간의 상관. 크면 그 지표는 시간의 대리변수다
    yoy_r = Column(Float, nullable=True)          # 추세·계절성을 걷어낸 전년동기대비 상관
    n_yoy = Column(Integer, nullable=True)
    survived = Column(Boolean, nullable=True)     # YoY에서도 레벨과 같은 부호로 |r|>0.3인가
    curated = Column(Boolean, nullable=False)     # registry의 업종 큐레이션에 포함된 지표인가
    computed_at = Column(DateTime(timezone=True), nullable=False)
