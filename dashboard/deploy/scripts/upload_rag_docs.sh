#!/usr/bin/env bash
# data/ 아래 DART 원문(XML/CSV)을 MinIO의 rag-documents 버킷에 올린다.
# 나중에 붙일 RAG 서버가 이 버킷에서 문서를 읽고, 만든 벡터 인덱스는
# rag-index 버킷에 저장하면 된다. (Render 유료 배포가 필요 없어지는 지점)
#
#   cd dashboard/deploy && ./scripts/upload_rag_docs.sh
#
set -euo pipefail
cd "$(dirname "$0")/.."

set -a; . ./.env; set +a

# compose에서 ../../data 를 /seed 로 읽기전용 마운트해두었다.
docker compose run --rm --no-deps --entrypoint sh minio-init -c "
  mc alias set local http://minio:9000 \$MINIO_ROOT_USER \$MINIO_ROOT_PASSWORD &&
  mc mirror --overwrite /seed local/rag-documents &&
  mc ls --recursive local/rag-documents | tail -20
"

echo "✅ 업로드 완료 → 콘솔에서 확인: https://${MINIO_CONSOLE_DOMAIN}"
