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
