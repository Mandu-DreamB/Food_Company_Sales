#!/usr/bin/env bash
# 최초 1회 실행: 인증서가 없는 상태에서 nginx를 띄우고 Let's Encrypt 인증서를 발급받는다.
# 도메인을 바꿨을 때도 다시 실행하면 된다.
#
#   cd dashboard/deploy && ./scripts/init-letsencrypt.sh
#
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "❌ .env가 없습니다. cp .env.example .env 후 값을 채우세요."; exit 1; }
set -a; . ./.env; set +a

: "${API_DOMAIN:?.env에 API_DOMAIN이 필요합니다}"
: "${MINIO_DOMAIN:?.env에 MINIO_DOMAIN이 필요합니다}"
: "${MINIO_CONSOLE_DOMAIN:?.env에 MINIO_CONSOLE_DOMAIN이 필요합니다}"
: "${LETSENCRYPT_EMAIL:?.env에 LETSENCRYPT_EMAIL이 필요합니다}"

STAGING="${STAGING:-0}"   # STAGING=1 로 실행하면 테스트 인증서(발급 횟수 제한 없음)
CERT_PATH="/etc/letsencrypt/live/${API_DOMAIN}"

echo "▶ 대상 도메인: ${API_DOMAIN}, ${MINIO_DOMAIN}, ${MINIO_CONSOLE_DOMAIN}"

echo "▶ 1/5 임시 자체서명 인증서 생성 (nginx가 뜨려면 인증서 파일이 먼저 있어야 함)"
docker compose run --rm --entrypoint sh certbot -c "
  mkdir -p ${CERT_PATH} &&
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout ${CERT_PATH}/privkey.pem \
    -out ${CERT_PATH}/fullchain.pem \
    -subj '/CN=localhost'
"

echo "▶ 2/5 nginx 기동"
docker compose up -d nginx

echo "▶ 3/5 임시 인증서 삭제"
docker compose run --rm --entrypoint sh certbot -c "rm -rf /etc/letsencrypt/live/${API_DOMAIN} /etc/letsencrypt/archive/${API_DOMAIN} /etc/letsencrypt/renewal/${API_DOMAIN}.conf"

echo "▶ 4/5 Let's Encrypt 인증서 발급"
docker compose run --rm --entrypoint certbot certbot certonly \
  --webroot -w /var/www/certbot \
  --cert-name "${API_DOMAIN}" \
  -d "${API_DOMAIN}" -d "${MINIO_DOMAIN}" -d "${MINIO_CONSOLE_DOMAIN}" \
  --email "${LETSENCRYPT_EMAIL}" \
  --agree-tos --no-eff-email --non-interactive \
  $([ "${STAGING}" != "0" ] && echo "--staging")

echo "▶ 5/5 nginx 리로드"
docker compose exec nginx nginx -s reload

echo "✅ 완료: https://${API_DOMAIN}/ 를 열어보세요 ({\"status\":\"ok\"}가 나와야 합니다)"
