from typing import Optional
from pydantic import BaseModel


class Point(BaseModel):
    date: str
    value: Optional[float] = None


class Series(BaseModel):
    name: str
    points: list[Point]


class Affiliate(BaseModel):
    id: str
    name: str
    category: str
    logo_text: str
    overview: Optional[str] = None
    overview_sources: list[str] = []


class AffiliateList(BaseModel):
    """랜딩 페이지가 필요한 두 가지: 탭 순서(categories)와 카드 순서(affiliates)."""

    categories: list[str]
    affiliates: list[Affiliate]


class BriefingResult(BaseModel):
    status: str  # "ok" | "error" | "not_generated"
    text: Optional[str] = None
    generated_at: Optional[str] = None


class IndicatorMeta(BaseModel):
    id: str
    title: str
    category: str
    unit: str
    frequency: str
    missing_env: list[str]


class IndicatorResult(IndicatorMeta):
    status: str  # "ok" | "missing_key" | "error"
    error: Optional[str] = None
    fetched_at: Optional[str] = None
    series: list[Series] = []


class IndicatorWithBriefing(IndicatorResult):
    """계열사 상세 페이지의 '가장 연관된 지표' 카드용 — 지표 데이터 + 그 지표의 AI 요약."""

    briefing: Optional[BriefingResult] = None
