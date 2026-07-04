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


class IndicatorFetchLog(Base):
    """지표별 마지막 수집 시각/상태 (TTL 캐시 판단 + 대시보드 상태 표시용)."""

    __tablename__ = "indicator_fetch_log"

    indicator_id = Column(String, primary_key=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False)
    error = Column(Text, nullable=True)
