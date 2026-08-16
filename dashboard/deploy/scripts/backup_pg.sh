#!/usr/bin/env bash
# PostgreSQL 덤프를 떠서 MinIO의 pg-backups 버킷에 올린다.
# cron 예시 (매일 새벽 3시):
#   0 3 * * * cd /srv/food_sales/dashboard/deploy && ./scripts/backup_pg.sh >> /var/log/pg-backup.log 2>&1
#
set -euo pipefail
cd "$(dirname "$0")/.."

set -a; . ./.env; set +a

STAMP="$(date +%Y%m%d-%H%M%S)"
FILE="${POSTGRES_DB}-${STAMP}.sql.gz"

echo "▶ 덤프 생성: ${FILE}"
docker compose exec -T postgres sh -c \
  "pg_dump -U \"\$POSTGRES_USER\" \"\$POSTGRES_DB\" | gzip > /backups/${FILE}"

echo "▶ MinIO 업로드: local/pg-backups/${FILE}"
# --no-deps: 이게 없으면 compose가 minio 컨테이너를 "설정에 맞게" 재생성한다.
# (로컬 오버레이를 쓰는 환경에서 백업이 MinIO를 재시작시키는 사고를 막는다)
docker compose run --rm --no-deps --entrypoint sh minio-init -c "
  mc alias set local http://minio:9000 \$MINIO_ROOT_USER \$MINIO_ROOT_PASSWORD &&
  mc cp /backups/${FILE} local/pg-backups/${FILE}
"

echo "▶ 로컬 덤프 정리 (7일 초과분 삭제)"
docker compose exec -T postgres sh -c "find /backups -name '*.sql.gz' -mtime +7 -delete"

echo "✅ 백업 완료: ${FILE}"
echo "   (버킷은 30일 만료 규칙이 걸려 있어 오래된 백업은 MinIO가 스스로 지웁니다)"
