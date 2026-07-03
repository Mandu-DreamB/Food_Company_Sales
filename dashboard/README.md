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

## 1. 백엔드 실행

```bash
cd dashboard/backend
python -m venv .venv
./.venv/Scripts/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# .env를 열어 보유한 API 키를 채워 넣습니다 (아래 참고)

uvicorn app.main:app --reload --port 8000
```

키를 하나도 넣지 않아도 서버는 정상적으로 뜨고, `yfinance`(글로벌 시장지표),
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

## 2. 프론트엔드 실행

```bash
cd dashboard/frontend
npm install
npm run dev
```

`http://localhost:5173`에서 대시보드를 확인할 수 있습니다. (백엔드는 `http://localhost:8000`에서
실행되고 있어야 합니다.)

## 동작 방식

- 지표 목록(`/api/sources`)은 캐시 파일 존재 여부와 `.env` 키 유무만 확인하며, 네트워크 호출을
  하지 않습니다 (사이드바/카드 목록이 빠르게 뜨는 이유).
- 지표 상세(`/api/sources/{id}`)에 들어가야 실제로 API를 호출하고, 결과를
  `backend/app/.cache/{id}.json`에 저장합니다. 이후 요청은 TTL(일별 6시간, 그 외 24시간) 동안
  캐시를 재사용합니다.
- 상세 페이지의 "새로고침" 버튼 또는 `?refresh=true` 쿼리로 캐시를 무시하고 즉시 재수집할 수
  있습니다.
- API 호출이 실패해도 서버는 죽지 않고 `status: "error"`와 마지막으로 성공한 캐시 데이터를 함께
  돌려줍니다.
