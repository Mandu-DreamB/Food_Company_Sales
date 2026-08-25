from dataclasses import dataclass
from typing import Callable

from .sources import energy, steel_wood, livestock_rice, market_yfinance, fao
from .sources import rates, fomc, housing
from .sources import prices_labor_kosis, consumption_kosis, construction_kosis, auto_kosis, airport_trade
from .sources import samyang_stocks

DAILY_TTL = 6 * 3600
MONTHLY_TTL = 24 * 3600
NO_KEY_TTL = 12 * 3600


@dataclass
class Indicator:
    id: str
    title: str
    category: str
    unit: str
    frequency: str
    required_env: list[str]
    ttl_seconds: int
    fetch: Callable[[], list[dict]]


INDICATORS: list[Indicator] = [
    Indicator("energy_oil_gas", "유가 · 천연가스 (WTI/Brent/Natural Gas)", "에너지·원자재",
              "$/BBL, $/MMBtu", "daily", ["EIA_API_KEY"], DAILY_TTL, energy.fetch_eia_oil_gas),
    Indicator("energy_oecd_stocks", "OECD 원유 재고", "에너지·원자재",
              "천 배럴", "monthly", ["EIA_API_KEY"], MONTHLY_TTL, energy.fetch_eia_oecd_stocks),
    Indicator("steel_prices", "철강 원자재 가격 (철광석/철스크랩/철근/열연 등)", "에너지·원자재",
              "$/톤, 천원/톤", "monthly", ["DATA_GO_KR_KEY"], MONTHLY_TTL, steel_wood.fetch_steel_prices),
    Indicator("wood_import_prices", "목재류 수입단가 (원목/제재목/합판/MDF/PB)", "에너지·원자재",
              "USD/톤", "monthly", ["DATA_GO_KR_KEY"], MONTHLY_TTL, steel_wood.fetch_wood_import_prices),
    Indicator("livestock_prices", "축산물 소비자가격 (한우/돼지/닭/계란/우유)", "농축수산물",
              "원", "monthly", ["DATA_GO_KR_KEY"], MONTHLY_TTL, livestock_rice.fetch_livestock_prices),
    Indicator("rice_price", "산지 쌀가격", "농축수산물",
              "원/20kg", "monthly", ["KOSIS_API_KEY"], MONTHLY_TTL, livestock_rice.fetch_rice_price),
    Indicator("market_yfinance", "글로벌 시장지표 15종 (원자재·환율·주가·금리)", "금융시장",
              "티커별 상이", "daily", [], NO_KEY_TTL, market_yfinance.fetch_market_prices),
    Indicator("fao_food_price_index", "FAO 세계 식품가격지수", "농축수산물",
              "지수", "monthly", [], NO_KEY_TTL, fao.fetch_fao_food_price_index),
    Indicator("policy_rates", "기준금리 (한국/미국/중국/일본/유럽)", "금리·통화정책",
              "연 %", "monthly", ["ECOS_API_KEY"], MONTHLY_TTL, rates.fetch_policy_rates),
    Indicator("household_credit", "가계신용 동향", "금리·통화정책",
              "십억원", "quarterly", ["ECOS_API_KEY"], MONTHLY_TTL, rates.fetch_household_credit),
    Indicator("ecos_monthly_macro", "국고채 금리 · 경상수지 · 소비자심리지수", "금리·통화정책",
              "혼합", "monthly", ["ECOS_API_KEY"], MONTHLY_TTL, rates.fetch_ecos_monthly_macro),
    Indicator("ecos_gdp_growth", "GDP 성장률 (전기대비, 계/민간소비/설비투자/건설투자)", "금리·통화정책",
              "%", "quarterly", ["ECOS_API_KEY"], MONTHLY_TTL, rates.fetch_ecos_gdp_growth),
    Indicator("fomc_dot_plot", "FOMC 점도표 (연방기금금리 전망 중앙값)", "금리·통화정책",
              "연 %", "irregular", ["FRED_API_KEY"], MONTHLY_TTL, fomc.fetch_fomc_dot_plot),
    Indicator("housing_price_index", "주택가격 매매지수 (계/수도권/기타)", "부동산",
              "2021=100", "monthly", ["REALTY_API_KEY"], MONTHLY_TTL, housing.fetch_housing_price_index),
    Indicator("housing_trade_volume", "전국 주택매매거래량", "부동산",
              "건", "monthly", ["REALTY_API_KEY"], MONTHLY_TTL, housing.fetch_housing_trade_volume),
    Indicator("apartment_construction", "아파트 착공/준공 실적 (계/수도권/기타)", "부동산",
              "호", "monthly", ["KOSIS_API_KEY"], MONTHLY_TTL, construction_kosis.fetch_apartment_construction),
    Indicator("construction_cost_index", "건설공사비지수", "부동산",
              "2020=100", "monthly", ["KOSIS_API_KEY"], MONTHLY_TTL, construction_kosis.fetch_construction_cost_index),
    Indicator("electric_construction_cost_index", "전기공사비지수", "부동산",
              "2020=100", "monthly", ["KOSIS_API_KEY"], MONTHLY_TTL, construction_kosis.fetch_electric_construction_cost_index),
    Indicator("price_index_kr_us", "한/미 소비자물가 총지수", "물가·고용",
              "지수", "monthly", ["KOSIS_API_KEY"], MONTHLY_TTL, prices_labor_kosis.fetch_price_index),
    Indicator("unemployment_kr_us", "한/미 실업률", "물가·고용",
              "%", "monthly", ["KOSIS_API_KEY"], MONTHLY_TTL, prices_labor_kosis.fetch_unemployment_rate),
    Indicator("import_price_index", "수입물가지수 (나프타/석유화학/합성수지 등)", "물가·고용",
              "지수", "monthly", ["KOSIS_API_KEY"], MONTHLY_TTL, prices_labor_kosis.fetch_price_index),
    Indicator("retail_sales", "국내 소매판매액 (백화점/대형마트/면세점)", "소비·유통",
              "지수", "monthly", ["KOSIS_API_KEY"], MONTHLY_TTL, consumption_kosis.fetch_retail_sales),
    Indicator("online_shopping", "온라인쇼핑 거래액 (전체/의복)", "소비·유통",
              "백만원", "monthly", ["KOSIS_API_KEY"], MONTHLY_TTL, consumption_kosis.fetch_online_shopping),
    Indicator("household_income_growth", "가계소득 실질 증감률 (전년동분기대비)", "소비·유통",
              "%", "quarterly", ["KOSIS_API_KEY"], MONTHLY_TTL, consumption_kosis.fetch_household_income_growth),
    Indicator("cosmetics_sales", "화장품 소매판매액", "소비·유통",
              "백만원", "monthly", ["KOSIS_API_KEY"], MONTHLY_TTL, consumption_kosis.fetch_cosmetics_sales),
    Indicator("cosmetics_sales_index", "화장품 소매판매액지수", "소비·유통",
              "2020=100", "monthly", ["KOSIS_API_KEY"], MONTHLY_TTL, consumption_kosis.fetch_cosmetics_sales_index),
    Indicator("cosmetics_export", "화장품 수출액 (계/중국/미국/일본/동남아)", "무역·수출",
              "달러", "monthly", ["DATA_GO_KR_KEY"], MONTHLY_TTL, airport_trade.fetch_cosmetics_export),
    Indicator("auto_production_export", "자동차 생산/수출대수 (연간)", "자동차",
              "대", "annual", ["KOSIS_API_KEY"], MONTHLY_TTL, auto_kosis.fetch_auto_production_export),
    Indicator("auto_export_value", "자동차 수출액", "자동차",
              "억불", "annual", [], NO_KEY_TTL, auto_kosis.fetch_auto_export_value),
    Indicator("auto_production_index", "자동차 생산지수", "자동차",
              "2020=100", "monthly", ["KOSIS_API_KEY"], MONTHLY_TTL, auto_kosis.fetch_auto_production_index),
    Indicator("auto_inventory_index", "자동차 제조업 재고지수", "자동차",
              "2020=100", "monthly", ["KOSIS_API_KEY"], MONTHLY_TTL, auto_kosis.fetch_auto_inventory_index),
    Indicator("incheon_airport_stats", "인천공항 항공통계 (인바운드/아웃바운드/중국발)", "무역·수출",
              "명, 편", "monthly", ["DATA_GO_KR_KEY"], MONTHLY_TTL, airport_trade.fetch_incheon_airport_stats),
    Indicator("samyang_stock_prices", "삼양그룹 상장 계열사 주가 (삼양사/삼양패키징/삼양엔씨켐)", "계열사 주가",
              "원", "daily", [], NO_KEY_TTL, samyang_stocks.fetch_samyang_stock_prices),
]

INDICATORS_BY_ID = {ind.id: ind for ind in INDICATORS}

ALL_CATEGORIES = list(dict.fromkeys(ind.category for ind in INDICATORS))

# 계열사 업종별로 관련도가 높은 지표 카테고리 큐레이션.
# 계열사 단위 매출/재무 시계열이 아직 없어서(로드맵 2단계 "매출/주가 vs 지표 상관관계 분석" 미착수)
# 통계적 상관관계 대신 업종 지식 기반으로 매핑했다. 그 데이터가 생기면 이 매핑을 실측 상관관계로
# 교체/보완하면 된다. "계열사 주가"는 그룹 전체와 관련 있다고 보고 모든 업종에 포함시킨다.
AFFILIATE_CATEGORY_INDICATOR_CATEGORIES: dict[str, list[str]] = {
    "지주": ALL_CATEGORIES,
    "화학": ["에너지·원자재", "물가·고용", "금리·통화정책", "무역·수출", "계열사 주가"],
    "식품": ["농축수산물", "소비·유통", "물가·고용", "계열사 주가"],
    "의약바이오": ["금융시장", "금리·통화정책", "물가·고용", "계열사 주가"],
    "패키징": ["에너지·원자재", "소비·유통", "무역·수출", "계열사 주가"],
    "코스메틱": ["소비·유통", "무역·수출", "물가·고용", "계열사 주가"],
    "IT": ["금융시장", "금리·통화정책", "계열사 주가"],
}

# 계열사 상세 페이지("가장 연관된 지표 3개")에 쓰는 큐레이션. 두 조건을 모두 만족해야 올린다:
#   1) 위 AFFILIATE_CATEGORY_INDICATOR_CATEGORIES 안에 있는 카테고리일 것(업종 타당성)
#   2) (매출 데이터가 있는 계열사는) mandu/Eda/affiliates_correlation.ipynb에서 레벨·변화율
#      상관계수가 같은 부호로 남는 "견고" 지표일 것 — 레벨 상관 1위만 보고 넣지 않는다.
#      household_credit(가계신용)처럼 레벨r은 최상위여도 추세r이 거의 같은 크기로 나오는 지표
#      (=시간과의 상관이 매출과의 상관만큼 커서 추세 동조로 의심됨, 해당 노트북 6절 참고)는
#      제외했다.
# 계열사 14곳 중 상관관계를 실제로 계산할 수 있었던 건 6곳뿐이다:
#   - 데이터 탄탄함(분기 18~26개, 레벨+변화율 다 계산): 홀딩스·식품·화학·패키징
#   - 데이터 약함(연 1회 감사보고서, n=6, 레벨 상관만 참고 가능): 이노켐·데이타시스템
#   - 데이터 없음(매출을 못 뽑음): 나머지 8곳 — 업종 큐레이션 + DART 사업보고서 내용만으로 선정.
#     예: 삼양사(코스메틱)은 registry에 화장품 전용 지표(cosmetics_sales 등)가 있어 그대로 매칭,
#     화학 소재사들은 import_price_index가 "나프타/석유화학/합성수지" 수입물가를 직접 포함해서 우선.
AFFILIATE_TOP_INDICATORS: dict[str, list[str]] = {
    "samyang-holdings": ["energy_oil_gas", "fao_food_price_index", "unemployment_kr_us"],
    "samyang-food": ["fao_food_price_index", "rice_price", "price_index_kr_us"],
    "samyang-chemical": ["energy_oil_gas", "steel_prices", "wood_import_prices"],
    "samyang-packaging": ["energy_oil_gas", "retail_sales", "incheon_airport_stats"],
    "samyang-innochem": ["wood_import_prices", "steel_prices", "samyang_stock_prices"],
    "samyang-data-system": ["market_yfinance", "ecos_monthly_macro", "policy_rates"],
    "samyang-cosmetic": ["cosmetics_sales", "cosmetics_export", "retail_sales"],
    "samnam-petrochemical": ["energy_oil_gas", "import_price_index", "policy_rates"],
    "samyang-chemical-corp": ["energy_oil_gas", "import_price_index", "samyang_stock_prices"],
    "samyang-finetechnology": ["energy_oil_gas", "import_price_index", "samyang_stock_prices"],
    "samyang-kci": ["energy_oil_gas", "import_price_index", "samyang_stock_prices"],
    "samyang-ncchem": ["energy_oil_gas", "import_price_index", "samyang_stock_prices"],
    "verdant": ["energy_oil_gas", "import_price_index", "samyang_stock_prices"],
    "samyang-biopharm": ["market_yfinance", "policy_rates", "price_index_kr_us"],
}

# 계열사 상세 페이지 맨 위 "사업보고서" 소개 박스. 삼양사(식품/화학)·삼양패키징·삼양엔씨켐은
# DART 최신 사업보고서의 "II. 사업의 내용" 원문(RAG/data/dart_xml)에서 사업 설명·시장점유율을
# 그대로 가져왔다. 나머지는 감사보고서만 제출해 DART에 사업 설명 문단이 없거나(이노켐·
# 데이타시스템·바이오팜), 공시 자체가 없는 계열사(홀딩스 등 6곳)라 일반적인 수준으로만 적었다 —
# 구체적인 수치·사실을 지어내지 않았다.
AFFILIATE_OVERVIEWS: dict[str, str] = {
    "samyang-holdings": (
        "삼양홀딩스는 2011년 삼양사의 식품·화학 부문이 인적분할되어 설립된 삼양그룹의 지주회사로, "
        "화학·식품·패키징·의약바이오·IT 계열사를 이끌고 있습니다.\n\n"
        "원유 등 원자재 가격, 물가·고용 같은 거시 지표가 그룹 전반의 실적에 폭넓게 영향을 줍니다."
    ),
    "samyang-food": (
        "삼양사 식품부문은 설탕·밀가루·전분당·유지 등을 생산해 '큐원' 브랜드로 판매합니다. "
        "국내 시장점유율은 설탕 32%, 전분당 28%, 밀가루 10% 수준입니다.\n\n"
        "원당·원맥·옥수수 등 주원료 대부분을 해외에서 수입하기 때문에, 국제 곡물가와 환율 변동이 "
        "원가에 직접 반영됩니다."
    ),
    "samyang-chemical": (
        "삼양사 화학부문은 엔지니어링 플라스틱, PET 용기·Flake, 이온교환수지 등을 생산합니다. "
        "PET Bottle 시장점유율 28%, 이온수지 시장점유율 38%를 차지하고 있습니다.\n\n"
        "원유를 원료로 하는 나프타·석유화학 제품 가격 변동이 원가 구조에 직접 연결됩니다."
    ),
    "samyang-packaging": (
        "삼양패키징은 1979년 국내 최초로 PET 용기 시장에 진출해 43년째 시장점유율 1위를 지키고 "
        "있으며, 무균충전(Aseptic) 음료 OEM 부문에서도 국내 1위 지위를 확보하고 있습니다.\n\n"
        "주원료인 PET Chip·재활용 PET 가격, 그리고 국제 유가 흐름이 원가에 직결됩니다."
    ),
    "samyang-ncchem": (
        "삼양엔씨켐은 반도체 노광·세정 공정에 쓰이는 정밀화학 소재(Polymer, PAG, PERR 중간체 등)를 "
        "전문적으로 개발·생산하는 반도체 소재 기업입니다.\n\n"
        "고객사와 계약 시점에 단가를 확정해 공급하는 구조라, 원재료 수입물가 변동이 다음 계약가에 "
        "반영되는 편입니다."
    ),
    "samyang-cosmetic": (
        "삼양사 코스메틱 부문은 퍼스널케어용 폴리머 등 화장품 원료를 생산·공급합니다.\n\n"
        "국내 화장품 소매판매·수출 동향과 소비 심리가 수요에 영향을 줍니다."
    ),
    "samyang-innochem": "삼양이노켐은 삼양그룹의 정밀화학 계열사입니다. 사업보고서 없이 감사보고서만 제출하고 있어 상세 사업 내용은 공개돼 있지 않습니다.",
    "samyang-data-system": "삼양데이타시스템은 삼양그룹의 IT 계열사로 그룹 전산시스템 구축·운영 등을 담당합니다.",
    "samnam-petrochemical": "삼남석유화학은 삼양그룹의 화학 계열사입니다. 사업보고서 없이 감사보고서만 제출하고 있어 상세 사업 내용은 공개돼 있지 않습니다.",
    "samyang-chemical-corp": "삼양화성은 삼양그룹의 화학 계열사입니다. 사업보고서 없이 감사보고서만 제출하고 있어 상세 사업 내용은 공개돼 있지 않습니다.",
    "samyang-finetechnology": "삼양화인테크놀로지는 삼양그룹의 화학 계열사입니다. 사업보고서 없이 감사보고서만 제출하고 있어 상세 사업 내용은 공개돼 있지 않습니다.",
    "samyang-kci": "삼양KCI는 삼양그룹의 화학 계열사입니다. 사업보고서 없이 감사보고서만 제출하고 있어 상세 사업 내용은 공개돼 있지 않습니다.",
    "verdant": "VERDANT는 삼양그룹의 화학 계열사입니다. 사업보고서 없이 감사보고서만 제출하고 있어 상세 사업 내용은 공개돼 있지 않습니다.",
    "samyang-biopharm": "삼양바이오팜은 삼양그룹의 의약바이오 계열사입니다. 사업보고서 없이 감사보고서만 제출하고 있어 상세 사업 내용은 공개돼 있지 않습니다.",
}

# 위 AFFILIATE_OVERVIEWS를 실제로 어느 DART 공시에서 가져왔는지. 값이 없는 계열사는 공시 자료
# 없이 업종 일반 정보로만 적었다는 뜻이라, 프론트에서 "공시 자료 없음" 문구를 대신 보여준다.
AFFILIATE_OVERVIEW_SOURCES: dict[str, list[str]] = {
    "samyang-food": ["삼양사 사업보고서 (2026-03-18 제출, 2025 회계연도) · II. 사업의 내용"],
    "samyang-chemical": ["삼양사 사업보고서 (2026-03-18 제출, 2025 회계연도) · II. 사업의 내용"],
    "samyang-packaging": ["삼양패키징 사업보고서 (2026-03-13 제출, 2025 회계연도) · II. 사업의 내용"],
    "samyang-ncchem": ["삼양엔씨켐 사업보고서 (2026-03-13 제출, 2025 회계연도) · II. 사업의 내용"],
}
