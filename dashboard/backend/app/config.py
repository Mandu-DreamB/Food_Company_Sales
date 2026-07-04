import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def missing_env(required: list[str]) -> list[str]:
    return [key for key in required if not os.getenv(key, "").strip()]
