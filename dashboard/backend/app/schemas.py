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


class AffiliateList(BaseModel):
    """랜딩 페이지가 필요한 두 가지: 탭 순서(categories)와 카드 순서(affiliates)."""

    categories: list[str]
    affiliates: list[Affiliate]


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
