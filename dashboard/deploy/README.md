# 배포 가이드

```
Vercel (프론트, HTTPS)
   │  fetch https://api.<도메인>/api/...
   ▼
Ubuntu VM ── nginx (443, Let's Encrypt)
               ├─ api.<도메인>    → backend (FastAPI :8000)
               ├─ s3.<도메인>     → MinIO S3 API (:9000)
               └─ minio.<도메인>  → MinIO 콘솔 (:9001)
             backend ─ postgres (:5432, 외부 비공개)
             MinIO 버킷: rag-documents / rag-index / pg-backups
```

Postgres·MinIO는 호스트 포트를 열지 않습니다. 밖에서 닿는 건 nginx의 80/443뿐입니다.

> 챗봇 RAG 서버(:8001)는 이번 배포에서 제외했습니다. 프론트에서 챗봇 버튼을 누르면
> 응답 실패로 보입니다. 붙일 준비(버킷·업로드 스크립트)는 해뒀습니다 → [나중에 RAG 붙이기](#나중에-rag-서버-붙이기)

---

## A. 지금 바로: 내 PC에서 띄우기

서버가 없어도 전체 스택(nginx + FastAPI + Postgres + MinIO)을 로컬에서 그대로 돌릴 수 있습니다.
서버에 올릴 때와 **같은 구성**이라 여기서 되면 서버에서도 됩니다.

### A-1. Docker Desktop 준비 (WSL2)

Docker Desktop이 깔려 있어도 WSL2가 없으면 엔진이 안 뜹니다. **관리자 권한 PowerShell**에서:

```powershell
wsl --install --no-distribution
```

재부팅 후 Docker Desktop을 실행하고, 새 터미널에서 `docker info`가 정상 출력되면 준비 완료입니다.
(`docker` 명령이 없다고 나오면 터미널을 새로 열어야 PATH가 잡힙니다.)

### A-2. 기동

```powershell
cd dashboard\deploy

# 매번 -f 두 개를 붙이기 번거로우므로 환경변수로 고정한다 (터미널 세션 한정)
$env:COMPOSE_FILE = "docker-compose.yml;docker-compose.local.yml"

docker compose up -d --build
docker compose run --rm minio-init      # 버킷 3개 생성 (멱등)
```

`COMPOSE_FILE`을 설정해두면 `scripts/*.sh`와 `docker compose logs` 같은 명령도 전부 로컬 구성을
바라봅니다. 설정하지 않았다면 명령마다 `-f docker-compose.yml -f docker-compose.local.yml`을
붙여야 합니다. (구분자는 PowerShell/Windows에서 `;`, Linux/macOS에서 `:`)

| 주소 | 내용 |
|---|---|
| http://localhost:8000 | API (`{"status":"ok"}`) |
| http://localhost:8000/api/sources | 지표 목록 |
| http://localhost:9001 | MinIO 콘솔 (계정은 `deploy/.env` 참고) |
| http://localhost:9000 | MinIO S3 엔드포인트 |

프론트는 그냥 로컬 개발 서버로 띄우면 됩니다 (`cd dashboard/frontend && npm run dev`).

### A-3. Vercel에 올린 프론트를 내 PC 백엔드에 연결하기 (Cloudflare Tunnel)

공인 IP도 도메인도 없이, 로컬 백엔드에 임시 HTTPS 주소를 붙일 수 있습니다. 계정도 필요 없습니다.

```powershell
docker compose --profile tunnel up -d cloudflared
docker compose logs cloudflared
```

로그에 찍히는 `https://xxxx-xxxx.trycloudflare.com` 주소를 Vercel의 `VITE_API_BASE_URL`에 넣으면
됩니다. CORS는 백엔드가 `*.vercel.app`을 기본 허용하므로 추가 설정이 없습니다.

주의: 이 주소는 **컨테이너를 재시작할 때마다 바뀌고, 내 PC가 꺼지면 죽습니다.** 시연·테스트용입니다.
고정 주소가 필요하면 Cloudflare 계정을 만들어 named tunnel을 쓰거나, 아래 서버 배포로 넘어가세요.

### A-4. 정리

```powershell
docker compose down        # 중지 (데이터 유지)
docker compose down -v     # 볼륨까지 삭제
```

---

## B. 서버에 배포하기

> **Oracle Cloud 무료 VM을 쓴다면 → [ORACLE_CLOUD.md](ORACLE_CLOUD.md)를 보세요.**
> 요금이 나오지 않게 하는 설정(예산 알림, 한도, 절대 하지 말 것)과 Oracle 특유의 함정
> (방화벽 2중 구조, 2026년 6월 축소된 무료 한도)까지 포함한 전용 가이드입니다.
> 아래는 서버 종류와 무관한 공통 절차입니다.

## 0. 준비물

- Ubuntu 22.04+ VM, 공인 IP, 2GB RAM 이상 (MinIO + Postgres + FastAPI 동시 구동)
- 방화벽에서 **80, 443만** 열기
- Docker + Compose 플러그인

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # 로그아웃 후 재접속
```

## 1. 도메인 — 아직 없다면 sslip.io

Vercel은 HTTPS라 **백엔드도 반드시 HTTPS여야 합니다.** HTTP로 두면 브라우저가
mixed content로 차단해서 대시보드가 빈 화면이 됩니다. 도메인을 안 샀어도 방법이 있습니다.

| 상황 | 방법 |
|---|---|
| 도메인 없음 (지금) | **sslip.io** — `api.203-0-113-5.sslip.io` 처럼 IP를 도메인처럼 씁니다. DNS 설정 없이 바로 Let's Encrypt 인증서가 발급됩니다. |
| 도메인 구매 후 | A 레코드 3개(`api`, `s3`, `minio`)를 서버 IP로 → `.env`의 도메인 3줄 수정 → `init-letsencrypt.sh` 재실행 |
| 공인 IP가 없음 (집/사내망) | Cloudflare Tunnel로 대체 (nginx는 그대로 두고 터널이 443을 대신 받음) |

sslip.io는 무료지만 공용 도메인이라 Let's Encrypt 발급 한도를 공유합니다. 개발/시연엔 충분하고,
실서비스로 갈 땐 도메인을 사는 걸 권합니다.

## 2. 서버에 코드 올리고 설정

```bash
git clone <이 저장소> /srv/food_sales
cd /srv/food_sales/dashboard

# 백엔드 API 키
cp backend/.env.example backend/.env
vi backend/.env          # EIA/KOSIS/DATA_GO_KR/ECOS/FRED/REALTY 키 입력
                         # DATABASE_URL은 compose가 덮어쓰므로 그대로 둬도 됨

# 배포 설정
cd deploy
cp .env.example .env
vi .env                  # 도메인 3개, LETSENCRYPT_EMAIL, POSTGRES_PASSWORD, MINIO_ROOT_PASSWORD

chmod +x scripts/*.sh
```

비밀번호 생성이 귀찮으면: `openssl rand -base64 24`

## 3. 기동

```bash
cd /srv/food_sales/dashboard/deploy

docker compose build
docker compose up -d postgres minio
docker compose run --rm minio-init      # 버킷 3개 생성 (멱등)
docker compose up -d backend
STAGING=1 ./scripts/init-letsencrypt.sh # 먼저 테스트 인증서로 리허설 (발급 한도 절약)
./scripts/init-letsencrypt.sh           # 진짜 인증서 발급 + nginx 기동
docker compose --profile prod up -d     # certbot 자동갱신까지 전부 기동
```

확인:

```bash
curl https://api.<도메인>/            # {"status":"ok"}
curl https://api.<도메인>/api/sources # 지표 목록 JSON
docker compose ps                     # 전부 running / healthy
docker compose logs -f backend        # 15분 수집 잡 로그
```

MinIO 콘솔: `https://minio.<도메인>` (계정 = `.env`의 `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`)

> 첫 기동 직후 `/api/sources`는 비어 있을 수 있습니다. 백그라운드 수집 잡이 한 바퀴 돌아야
> `indicator_points`가 채워집니다. 로그에 `collect_all finished`가 뜨면 완료된 겁니다.

계열사 카드가 안 보이면 시드를 한 번 넣어주세요:

```bash
docker compose exec backend python scripts/seed_affiliates.py
```

## 4. 프론트엔드 (Vercel)

Vercel 대시보드에서 **Add New → Project → 이 저장소 임포트**:

| 항목 | 값 |
|---|---|
| Root Directory | `dashboard/frontend` |
| Framework Preset | Vite (자동 감지) |
| Build Command / Output | `npm run build` / `dist` (`vercel.json`에 이미 있음) |

Environment Variables (Production + Preview 둘 다):

| 이름 | 값 |
|---|---|
| `VITE_API_BASE_URL` | `https://api.<도메인>` |
| `VITE_RAG_API_BASE_URL` | (RAG 배포 전까지 비워둠) |

`vercel.json`의 rewrite가 새로고침 시 404 나는 SPA 문제를 막아줍니다.

CORS는 백엔드가 `*.vercel.app`을 기본 허용합니다. **Vercel에 커스텀 도메인을 붙였다면**
`deploy/.env`의 `CORS_ALLOW_ORIGIN_REGEX`에 추가하고 `docker compose up -d backend`로 재기동하세요:

```
CORS_ALLOW_ORIGIN_REGEX=http://(localhost|127\.0\.0\.1):\d+|https://.*\.vercel\.app|https://dashboard\.example\.com
```

## 5. 백업

```bash
./scripts/backup_pg.sh    # 덤프 → MinIO pg-backups 버킷
```

cron 등록 (매일 새벽 3시):

```bash
crontab -e
0 3 * * * cd /srv/food_sales/dashboard/deploy && ./scripts/backup_pg.sh >> /var/log/pg-backup.log 2>&1
```

버킷에 30일 만료 규칙이 걸려 있어 오래된 백업은 MinIO가 자동으로 지웁니다.

복구:

```bash
docker compose run --rm --entrypoint sh minio-init -c \
  "mc alias set local http://minio:9000 \$MINIO_ROOT_USER \$MINIO_ROOT_PASSWORD && \
   mc cp local/pg-backups/<파일명> /backups/"
docker compose exec -T postgres sh -c \
  'gunzip -c /backups/<파일명> | psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
```

## 나중에 RAG 서버 붙이기

README에 적어두신 "벡터DB를 Render에 유료 배포해야 함" 문제는 MinIO로 해결됩니다.
인덱스를 서비스가 아니라 **파일**로 취급하면 됩니다.

1. 문서 업로드: `./scripts/upload_rag_docs.sh` (`data/` → `rag-documents` 버킷)
   - `data/`는 `.gitignore` 대상이라 `git clone`으로는 서버에 안 옵니다. 먼저 복사하세요:
     `scp -r data/ <user>@<서버IP>:/srv/food_sales/data/`
2. RAG 서버는 기동 시 `rag-index` 버킷에서 인덱스(FAISS/Chroma 파일)를 내려받아 메모리에 적재
3. 인덱스를 새로 만들면 다시 `rag-index`에 업로드

compose에 서비스 한 개를 추가하고 nginx에 `rag.<도메인>` 서버 블록만 붙이면 됩니다.
백엔드 컨테이너엔 이미 `S3_ENDPOINT_URL` / `S3_ACCESS_KEY` / `S3_SECRET_KEY`를 넣어뒀습니다.
Vercel의 `VITE_RAG_API_BASE_URL`을 그 주소로 바꾸면 챗봇이 살아납니다.

## 자주 겪는 문제

| 증상 | 원인 / 해결 |
|---|---|
| 프론트에서 데이터가 안 옴, 콘솔에 CORS 에러 | `CORS_ALLOW_ORIGIN_REGEX`에 Vercel 도메인 추가 후 backend 재기동 |
| 콘솔에 mixed content 경고 | `VITE_API_BASE_URL`이 `http://`로 돼 있음 → `https://`로 |
| `init-letsencrypt.sh`가 발급 실패 | 80 포트가 막혔거나 도메인이 서버 IP를 안 가리킴. `STAGING=1 ./scripts/init-letsencrypt.sh`로 한도 안 쓰고 테스트 |
| MinIO 콘솔 로그인 후 화면이 깨짐 | `.env`의 `MINIO_CONSOLE_DOMAIN`과 실제 접속 주소가 다름 |
| 지표가 전부 `error` 상태 | `backend/.env`에 API 키 누락. `docker compose logs backend`로 확인 |
| 수집 잡이 두 번씩 돎 | uvicorn 워커를 늘렸을 때 발생. Dockerfile의 `--workers 1`을 유지할 것 |
