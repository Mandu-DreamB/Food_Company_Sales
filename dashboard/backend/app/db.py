import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from . import config  # noqa: F401  (.env 로드 부수효과)

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not DATABASE_URL:
    raise RuntimeError(
        ".env에 DATABASE_URL을 설정해주세요. "
        "예: postgresql+psycopg://dashboard_app:비밀번호@localhost:5432/samyang_dashboard"
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
