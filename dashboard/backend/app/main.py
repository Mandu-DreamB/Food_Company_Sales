import logging
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .briefing import generate_all_briefings, generate_all_indicator_briefings
from .collector import collect_all
from .db import Base, engine
from . import models  # noqa: F401  (Base.metadata에 테이블 등록)

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def _run_collect_all() -> None:
    results = collect_all()
    logger.info("collect_all finished: %s", results)


def _run_generate_briefings() -> None:
    # 지표 수집(_run_collect_all)이 최소 한 번은 채워 놓은 뒤에 브리핑을 만들어야 근거가 있다.
    # generate_all_briefings 자체가 지표 데이터 없으면 "데이터 부족" 문구로 처리하므로 순서를
    # 엄격히 강제하지는 않지만, 매 실행마다 신선도(TTL)를 확인하므로 다음 주기에 자연히 채워진다.
    results = generate_all_briefings()
    logger.info("generate_all_briefings finished: %s", results)


def _run_generate_indicator_briefings() -> None:
    results = generate_all_indicator_briefings()
    logger.info("generate_all_indicator_briefings finished: %s", results)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # 요청 경로에서는 외부 API를 호출하지 않는다. DB 채우기는 전적으로 이 백그라운드 잡이 담당한다.
    scheduler.add_job(_run_collect_all, "interval", minutes=15, id="collect_all", next_run_time=datetime.now())
    scheduler.add_job(
        _run_generate_briefings, "interval", hours=24, id="generate_briefings", next_run_time=datetime.now()
    )
    scheduler.add_job(
        _run_generate_indicator_briefings, "interval", hours=24,
        id="generate_indicator_briefings", next_run_time=datetime.now(),
    )
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="지표 대시보드 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+|https://.*\.onrender\.com",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"status": "ok"}
