# Oracle Cloud 무료 VM 배포 (요금 0원 유지)

이 문서의 목적은 두 가지입니다. **① 대시보드를 상시 운영되는 서버에 올린다. ② 절대 요금이 나오지 않게 한다.**

> **2026년 6월 15일 변경 주의**
> Oracle이 공지 없이 Always Free의 Ampere A1 한도를 **4 OCPU / 24GB → 2 OCPU / 12GB로 절반 축소**했습니다.
> 새 한도를 초과한 기존 인스턴스는 **2026년 8월 18일부터 종료** 예고 상태입니다.
> 인터넷의 옛날 가이드가 "4 OCPU / 24GB로 만드세요"라고 하는데, **그대로 따라 하면 인스턴스가 종료됩니다.**
> 아래 절차는 축소된 한도(2 OCPU / 12GB) 기준입니다. 우리 스택엔 이것도 충분합니다.

---

## 0. 요금이 나오는 경우는 딱 하나

**계정을 Pay As You Go(유료)로 업그레이드하지 않는 한, 카드에 청구되지 않습니다.**
Always Free 계정은 한도를 넘는 리소스를 **애초에 생성할 수 없게** 막혀 있습니다. 즉 최대 방어책은
단순합니다 — **"업그레이드" 버튼을 누르지 않는 것.**

가입 시 카드를 등록하지만 본인확인용이며, 소액(약 1달러) 임시 승인 후 취소됩니다.
30일 체험 크레딧($300) 기간에는 유료 리소스도 만들 수 있는데, 체험이 끝나면 **자동으로 정지·삭제되고
청구되지 않습니다.** 이때 콘솔이 "업그레이드하면 유지됩니다"라고 권하는데, **누르지 마세요.**

### 절대 하지 말 것

| 금지 | 이유 |
|---|---|
| **"Upgrade to Pay As You Go" 클릭** | 유일하게 실제 청구가 시작되는 지점 |
| A1 인스턴스를 2 OCPU / 12GB 초과로 생성 | 2026-06-15 이후 한도 초과분은 종료 대상 |
| 블록/부트 볼륨 총합 200GB 초과 | 초과분 과금 |
| 부트 볼륨 성능을 "높은 성능(High)"으로 변경 | VPU 추가분 과금. **"균형(Balanced)" 기본값 유지** |
| 볼륨 백업 정책을 6개 이상 생성 | 무료는 백업 5개까지 |
| Autonomous DB / Load Balancer 추가 생성 | 무료 수량(각 2개 / 1개)을 넘기면 과금 |

우리 배포는 **컴퓨트 1대 + 부트볼륨 50GB**만 씁니다. 로드밸런서·오브젝트스토리지·DB 서비스를
쓰지 않습니다 (Postgres도 MinIO도 VM 안의 Docker 컨테이너입니다).

---

## 1. 가입

https://www.oracle.com/kr/cloud/free/ → "무료로 시작하기"

- **홈 리전은 신중히**: 나중에 못 바꿉니다. `South Korea Central (Seoul)` 또는 `Chuncheon` 권장.
  단, 서울/춘천은 A1 용량이 자주 없습니다. 안 되면 `Japan East (Tokyo)`가 대안입니다.
- 가입 완료까지 수 시간~하루가 걸릴 수 있습니다.

## 2. 가장 먼저: 예산 알림 (0원 감시)

인스턴스를 만들기 **전에** 걸어두세요.

콘솔 → 좌측 메뉴 **Billing & Cost Management → Budgets → Create Budget**

| 항목 | 값 |
|---|---|
| Budget Scope | Compartment → `(root)` |
| Target | 루트 컴파트먼트 |
| Monthly Budget Amount | `1` (USD) |
| Alert Rule → Threshold | `1` **%** of budget (= $0.01) |
| Email | 본인 메일 |

이러면 **1센트라도 청구가 잡히는 순간** 메일이 옵니다. 알림은 하루 단위로 집계되므로
완벽한 차단막은 아니지만, 사고를 조기에 잡아줍니다.

확인은 **Billing → Cost Analysis**에서 언제든 볼 수 있습니다. 정상이라면 계속 `$0.00`입니다.

## 3. 인스턴스 생성

콘솔 → **Compute → Instances → Create Instance**

| 항목 | 값 | 확인 사항 |
|---|---|---|
| Image | Canonical **Ubuntu 24.04** (aarch64) | |
| Shape | **VM.Standard.A1.Flex** | 화면에 **"Always Free-eligible"** 초록 배지가 보여야 합니다 |
| OCPU | **2** | 절대 초과 금지 |
| Memory | **12 GB** | 절대 초과 금지 |
| Boot volume | **50 GB**, 성능 **Balanced** | 200GB 한도 내. 성능을 올리면 과금 |
| Public IPv4 | 할당 | |
| SSH key | 새로 생성 → 개인키 다운로드 | 잃어버리면 접속 불가 |

> **"Out of capacity" 에러**가 자주 납니다. Always Free의 A1은 인기가 많아 물량이 없을 때가 많습니다.
> 해결: 가용 도메인(AD-1/2/3)을 바꿔가며 재시도, 시간대를 바꿔 재시도, 그래도 안 되면 다른 리전.
> **"업그레이드하면 됩니다"라는 안내가 뜨는데 누르지 마세요.** 그게 과금 시작점입니다.
> A1을 끝내 못 받으면 → 로컬 + Cloudflare Tunnel(README의 A절)로 버티거나 유료 VPS를 고려하세요.
> (AMD 마이크로 무료 인스턴스는 RAM 1GB라 이 스택엔 부족합니다.)

인스턴스 생성 후 **공인 IP를 메모**해 두세요. 아래에서 `<서버IP>`로 씁니다.

## 4. 방화벽 (두 군데를 다 열어야 합니다)

Oracle의 대표적인 함정입니다. 클라우드 방화벽과 OS 방화벽이 **따로** 있습니다.

**① VCN 보안 목록** — 콘솔 → Networking → Virtual Cloud Networks → 해당 VCN →
Security Lists → Default Security List → **Add Ingress Rules**

| Source CIDR | Protocol | Dest. Port |
|---|---|---|
| `0.0.0.0/0` | TCP | `80` |
| `0.0.0.0/0` | TCP | `443` |

**② 인스턴스 안의 iptables** — SSH 접속 후:

```bash
ssh -i <개인키> ubuntu@<서버IP>

sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

## 5. Docker 설치

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
exit          # 로그아웃 후 다시 SSH 접속해야 그룹이 적용됩니다
```

```bash
docker run --rm hello-world     # 정상 동작 확인
```

> ARM(aarch64) 서버지만 우리가 쓰는 이미지(postgres, minio, nginx, certbot, python)는 전부
> arm64를 지원합니다. 별도 설정 없이 그대로 동작합니다.

## 6. 배포

```bash
sudo mkdir -p /srv && sudo chown $USER /srv
git clone <이 저장소> /srv/food_sales
cd /srv/food_sales/dashboard

# 백엔드 API 키 (로컬 PC의 dashboard/backend/.env를 scp로 복사해도 됩니다)
cp backend/.env.example backend/.env
nano backend/.env

# 배포 설정
cd deploy
cp .env.example .env
nano .env
```

`.env`에서 도메인 3줄을 **서버 IP 기반 sslip.io 주소**로 채웁니다.
IP가 `152.70.100.20`이면 점을 하이픈으로 바꿔서:

```
API_DOMAIN=api.152-70-100-20.sslip.io
MINIO_DOMAIN=s3.152-70-100-20.sslip.io
MINIO_CONSOLE_DOMAIN=minio.152-70-100-20.sslip.io
LETSENCRYPT_EMAIL=luisluos@gmail.com
POSTGRES_PASSWORD=<openssl rand -base64 24 결과>
MINIO_ROOT_PASSWORD=<openssl rand -base64 24 결과>
```

기동:

```bash
chmod +x scripts/*.sh
docker compose build
docker compose up -d postgres minio
docker compose run --rm minio-init
docker compose up -d backend

# 인증서 발급 전에 테스트부터 (발급 횟수 한도를 아끼기 위해)
STAGING=1 ./scripts/init-letsencrypt.sh
# 성공하면 진짜 인증서로
./scripts/init-letsencrypt.sh

docker compose --profile prod up -d      # certbot 자동갱신 포함 전체 기동
```

확인:

```bash
curl https://api.152-70-100-20.sslip.io/          # {"status":"ok"}
docker compose ps
docker compose logs -f backend                     # collect_all finished 확인
docker compose exec backend python scripts/seed_affiliates.py   # 계열사 시드
```

## 7. Vercel 연결

Vercel 프로젝트 환경변수:

| 이름 | 값 |
|---|---|
| `VITE_API_BASE_URL` | `https://api.152-70-100-20.sslip.io` |

저장 후 재배포하면 끝입니다.

## 8. 백업 자동화

```bash
crontab -e
```

```
0 3 * * * cd /srv/food_sales/dashboard/deploy && ./scripts/backup_pg.sh >> /var/log/pg-backup.log 2>&1
```

백업은 **VM 안의 MinIO**에 쌓입니다(무료 블록 볼륨 200GB 안). OCI Object Storage를 쓰지 않으므로
추가 요금이 없습니다. 30일 만료 규칙이 걸려 있어 무한정 쌓이지도 않습니다.

---

## 유휴 회수 정책 (알아둘 것)

Oracle은 Always Free 인스턴스가 **7일 연속 유휴**하면 회수할 수 있습니다.
기준은 7일간 95백분위수로 **CPU < 20% & 네트워크 < 20% & 메모리 < 20%** (A1은 메모리 포함, 셋 다 해당될 때).

우리 백엔드는 15분마다 수집 잡을 돌리고 MinIO·Postgres가 상주해 메모리를 점유하므로 해당될 가능성은
낮지만, 트래픽이 거의 없으면 완전히 안전하다고 장담할 순 없습니다. 회수되면 인스턴스가 중지되며,
콘솔에서 다시 시작할 수 있습니다. (데이터는 부트 볼륨에 남습니다.)

## 월 1회 점검 체크리스트

1. **Billing → Cost Analysis** → 이번 달 비용이 `$0.00`인가
2. **Billing → Subscriptions**에 계정 유형이 여전히 **Always Free**인가 (Pay As You Go로 안 바뀌었나)
3. **Compute → Instances** → 인스턴스가 1대뿐이고 2 OCPU / 12GB인가
4. **Storage → Block Volumes / Boot Volumes** → 총합이 200GB 이하인가
5. `docker compose ps` → 컨테이너가 전부 running인가
6. `df -h` → 디스크 여유가 있는가 (백업이 쌓이면 정리)

## 문제 해결

| 증상 | 해결 |
|---|---|
| 인스턴스 생성 시 "Out of capacity" | AD를 바꿔 재시도 / 시간대 변경 / 다른 리전. **업그레이드는 하지 말 것** |
| SSH는 되는데 웹이 안 열림 | 4번의 **iptables**를 빠뜨린 경우가 대부분 |
| 인증서 발급 실패 | 80 포트 미개방 또는 sslip.io 주소의 IP가 실제 서버 IP와 다름 |
| Vercel에서 CORS 에러 | `CORS_ALLOW_ORIGIN_REGEX` 확인 후 `docker compose up -d backend` |
| 메모리 부족 | `docker stats`로 확인. 12GB면 충분하지만, 부족하면 swap 4GB 추가 |
