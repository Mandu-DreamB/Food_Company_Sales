from typing import Optional
from pydantic import BaseModel


class Point(BaseModel):
    date: str
    value: Optional[float] = None


class Series(BaseModel):
    name: str
    points: list[Point]


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
