"""지표 데이터를 외부 API에서 받아와 DB에 채워 넣는 배치 스크립트.

프론트/백엔드 API는 이 스크립트가 채워 둔 DB만 읽는다. 실시간 수집은 여기서만 일어난다.

사용법:
    (backend/.venv 활성화 후) python scripts/collect.py          # TTL 지난 지표만 갱신
    python scripts/collect.py --force                            # 전부 강제 재수집

Windows에서 주기 실행하려면 작업 스케줄러(Task Scheduler)에 위 명령을 등록하면 된다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.collector import collect_all  # noqa: E402

if __name__ == "__main__":
    force = "--force" in sys.argv
    results = collect_all(force=force)
    for indicator_id, status in results.items():
        print(f"{indicator_id}: {status}")
