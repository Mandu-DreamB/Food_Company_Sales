# 지표 시각화 대시보드

`louis/01_openapi_testing.ipynb`에서 수집하던 31개 경제 지표(유가, 철강, 금리, 물가, 주택가격,
환율 등)를 그래프로 볼 수 있는 웹 대시보드입니다. FastAPI 백엔드가 각 지표의 원본 API를 호출해
정규화된 시계열로 변환하고, React 프론트엔드가 이를 차트로 그립니다.

## 구조

```
dashboard/
  backend/    FastAPI 서버 (지표 수집 + 캐싱 + REST API)
  frontend/   React(Vite) 대시보드 UI
```

## 1. PostgreSQL 준비

로컬에 설치된 PostgreSQL에 이 프로젝트 전용 DB/계정을 만듭니다 (Windows 예시).

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres
```

```sql
CREATE DATABASE samyang_dashboard;
CREATE USER dashboard_app WITH PASSWORD '원하는비밀번호';
GRANT ALL PRIVILEGES ON DATABASE samyang_dashboard TO dashboard_app;
\c samyang_dashboard
GRANT ALL ON SCHEMA public TO dashboard_app;
```

## 2. 백엔드 실행

```bash
cd dashboard/backend
python -m venv .venv
./.venv/Scripts/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# .env를 열어 DATABASE_URL과 보유한 API 키를 채워 넣습니다 (아래 참고)
# DATABASE_URL=postgresql+psycopg://dashboard_app:원하는비밀번호@localhost:5432/samyang_dashboard

uvicorn app.main:app --reload --port 8000
```

서버가 처음 뜰 때 필요한 테이블(`indicator_points`, `indicator_fetch_log`)을 자동으로
생성합니다. API 키를 하나도 넣지 않아도 서버는 정상적으로 뜨고, `yfinance`(글로벌 시장지표),
FAO 식품가격지수, 자동차 수출액(e-나라지표)은 키 없이 바로 조회됩니다. 나머지 지표는
`.env`에 해당 키를 채운 뒤 다시 조회하면 자동으로 정상 상태로 바뀝니다.

### 필요한 API 키

| 키 | 발급처 | 대상 지표 |
|---|---|---|
| `EIA_API_KEY` | https://www.eia.gov/opendata/register.php | 유가/천연가스, OECD 원유재고 |
| `KOSIS_API_KEY` | https://kosis.kr/openapi/ | 물가지수, 실업률, 소매판매, 온라인쇼핑, 가계소득, 건설/전기공사비, 아파트착공준공, 화장품판매, 자동차 생산 등 |
| `DATA_GO_KR_KEY` | https://www.data.go.kr/ | 철강, 목재수입단가, 축산물, 인천공항, 화장품수출 |
| `ECOS_API_KEY` | https://ecos.bok.or.kr/api/ | 기준금리, 가계신용, 거시지표 |
| `FRED_API_KEY` | https://fred.stlouisfed.org/docs/api/api_key.html | FOMC 점도표 |
| `REALTY_API_KEY` | https://www.reb.or.kr/r-one/ | 주택가격지수, 주택거래량 |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys | 계열사 AI 브리핑 (아래 참고). 없어도 서버는 정상 동작하며, 브리핑만 생성되지 않습니다 |

## 3. 프론트엔드 실행

```bash
cd dashboard/frontend
npm install
npm run dev
```

`http://localhost:5173`에서 대시보드를 확인할 수 있습니다. (백엔드는 `http://localhost:8000`에서
실행되고 있어야 합니다.)

## 동작 방식

- 랜딩 페이지의 계열사 카드는 `/api/affiliates`가 DB의 `affiliates` 테이블을 읽어 내려줍니다.
  계열사가 바뀌면 `backend/scripts/seed_affiliates.py`의 목록을 고치고 다시 실행하세요
  (`python scripts/seed_affiliates.py`, 멱등).
- 지표 목록(`/api/sources`)은 DB의 `indicator_fetch_log` 존재 여부와 `.env` 키 유무만
  확인하며, 외부 API 호출을 하지 않습니다 (사이드바/카드 목록이 빠르게 뜨는 이유).
- 지표 상세(`/api/sources/{id}`)에 들어가야 실제로 외부 API를 호출하고, 결과를 PostgreSQL의
  `indicator_points`(시계열 값) / `indicator_fetch_log`(수집 상태) 테이블에 저장합니다.
  이후 요청은 TTL(일별 지표 6시간, 그 외 24시간) 동안 DB에 저장된 값을 재사용합니다.
- 상세 페이지의 "새로고침" 버튼 또는 `?refresh=true` 쿼리로 캐시를 무시하고 즉시 재수집할 수
  있습니다.
- API 호출이 실패해도 서버는 죽지 않고 `status: "error"`와 마지막으로 성공한 캐시 데이터를 함께
  돌려줍니다.

## AI 브리핑

계열사 페이지(`/company/:affiliateId`) 상단에, 그 계열사 업종과 관련된 지표들의 최근 동향을 LLM이
2~4문장으로 요약해 주는 브리핑이 뜹니다. 실시간 뉴스/공시를 읽어오는 게 아니라, **이미 DB에 쌓인
지표 시계열의 최근 값·변화율·최고/최저 여부를 계산해서 "사실 목록"으로 만들고, 그 목록만 근거로
LLM이 문장을 쓰는 방식**입니다 (`app/briefing.py`).

- **생성 주기**: 지표 수집(15분 간격)과는 별개로 **24시간마다** 스케줄러(`app/main.py`)가 돌며,
  마지막 생성이 24시간을 넘긴 계열사만 다시 생성합니다. 즉 지표 데이터가 갱신돼도 최대 24시간
  이내에 브리핑에 반영됩니다 — 매번 즉시 반영하지 않는 이유는 재배포/재시작마다 LLM을 다시 부르면
  비용과 시간이 계속 나가기 때문입니다. (지금은 이 24시간 주기를 그대로 유지하기로 함. 즉시
  재생성이 필요하면 `python -c "from app.briefing import generate_all_briefings; generate_all_briefings(force=True)"`
  를 수동으로 실행)
- **저장**: `affiliate_briefings` 테이블에 계열사당 1행 (텍스트/생성시각/상태). 생성 실패해도
  마지막 성공 텍스트는 그대로 두고 상태만 `error`로 남깁니다 (지표 수집 실패 처리와 동일한 패턴).
- **API**: `GET /api/affiliates/{affiliate_id}/briefing` — `status`가 `ok`가 아니거나 `text`가
  없으면 프론트는 브리핑 박스를 그냥 숨깁니다 (페이지 전체가 깨지지 않음).
- **관련 지표 매핑**: 계열사 업종별로 어떤 지표 카테고리가 "관련 있다"고 볼지는 `app/registry.py`의
  `AFFILIATE_CATEGORY_INDICATOR_CATEGORIES`에 있습니다. 실제 매출/재무 데이터 기반 통계적
  상관관계가 아니라 업종 지식으로 큐레이션한 것이라, 로드맵 2단계(매출 vs 지표 상관관계 분석)가
  진행되면 이 매핑을 데이터 기반으로 교체/보완할 수 있습니다.

## 지표 DB 챗봇 (txt2sql)

계열사 페이지 우측 하단, 공시 RAG 챗봇 왼쪽에 하나 더 있는 위젯입니다. 공시 문서가 아니라
**대시보드가 수집해 둔 지표 DB를 직접 조회**해서 답합니다 (`app/dbchat.py`, `POST /api/db-chat`).

동작: 질문 → LLM이 SELECT 한 문장 생성 → 실행 → 결과만 근거로 답변 + (필요하면) 차트 스펙.
LLM 호출 2번, 쿼리 1번. 브리핑과 달리 미리 만들어 둘 수 없어 요청 경로에서 LLM을 부릅니다.

- **스키마 프롬프트**: `models.py`의 SQLAlchemy 메타데이터에서 테이블/컬럼을 뽑고 설명글은 각
  모델의 docstring 첫 줄을 씁니다. 프롬프트에 스키마를 베껴 두지 않으므로 모델이 바뀌면 따라갑니다.
  여기에 `registry.INDICATORS`의 지표 목록과 DB에 실제로 있는 `series_name`을 붙입니다.
- **안전장치**: 단일 SELECT/WITH만 허용(세미콜론·DML 키워드 거부), `SET TRANSACTION READ ONLY`,
  `statement_timeout 10s`, 결과 200행 상한. 앱 DB 계정 자체는 쓰기 권한이 있으므로 READ ONLY가
  마지막 방어선입니다. 가드 자체 검사는 `python -m app.dbchat`.
- **차트**: 답변과 함께 `{indicator_id, series_name, from, to, transform}` 스펙을 JSON으로 받고,
  **값은 서버가 DB에서 직접 읽어** 채웁니다(LLM이 숫자를 지어낼 수 없음). 프론트는 그걸 관련 지표
  카드와 같은 `MultiSeriesChart`로 대시보드 맨 위에 카드로 띄웁니다. `transform: "yoy"`는
  전년동기대비 증감률(%)이고, 지표마다 주기가 달라 1년 전 날짜에 가장 가까운 관측치를 찾아 씁니다.
  페이지 코드를 LLM이 생성하게 하지 않은 이유는 브라우저에서 LLM 출력 코드를 실행해야 하기 때문입니다.

## 상관관계 테이블

`mandu/Eda/run_correlation.py`의 CSV 결과를 `correlations` 테이블에 적재합니다
(`python scripts/seed_correlations.py`, 멱등). 계열사↔지표를 잇는 유일한 DB 컬럼이라 챗봇이
"이 계열사 관련 지표" 류 질문에 조인으로 답할 수 있게 해 줍니다.

**단, 이 상관계수는 관계의 증거가 아닙니다.** 표본이 분기 18~26개뿐이라 생존 지표 수가 귀무
기준선을 넘지 못했습니다(커밋 d64df9d). 그래서 `level_r`만이 아니라 `trend_r`(지표와 시간의 상관),
`yoy_r`(추세·계절성 제거), `survived`, `curated`를 함께 저장하고, 챗봇 프롬프트가 인과 표현을
금지하고 "통계적으로 확인된 관계는 아니다"라는 단서를 붙이도록 강제합니다.

문제점
1. 챗봇에서 RAG의 내장 벡터DB도 RENDER에 따로 배포를 해야함(유료배포)

# 삼양사 x 경제지표 매출관계
https://claude.ai/code/artifact/64eec523-94a0-4b32-9bdb-551a254a11ba
