import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .collector import collect_all
from .db import Base, engine
from . import models  # noqa: F401  (Base.metadata에 테이블 등록)

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def _run_collect_all() -> None:
    results = collect_all()
    logger.info("collect_all finished: %s", results)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # 요청 경로에서는 외부 API를 호출하지 않는다. DB 채우기는 전적으로 이 백그라운드 잡이 담당한다.
    scheduler.add_job(_run_collect_all, "interval", minutes=15, id="collect_all", next_run_time=datetime.now())
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="지표 대시보드 API", lifespan=lifespan)

# 배포 환경마다 프론트 오리진이 다르므로 .env로 덮어쓸 수 있게 둔다.
# 기본값: 로컬 개발 + Vercel(프로덕션/프리뷰 도메인) + Render
DEFAULT_CORS_REGEX = (
    r"http://(localhost|127\.0\.0\.1):\d+"
    r"|https://.*\.vercel\.app"
    r"|https://.*\.onrender\.com"
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=os.getenv("CORS_ALLOW_ORIGIN_REGEX", "").strip() or DEFAULT_CORS_REGEX,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"status": "ok"}
