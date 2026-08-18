from datetime import date

import FinanceDataReader as fdr
from dateutil.relativedelta import relativedelta

from .util import series_from_wide

# 상장 계열사만 대상 (비상장 계열사는 종목코드가 없어 주가 자체가 없음)
TICKERS = {
    "삼양사": "005090",
    "삼양패키징": "272550",
    "삼양엔씨켐": "482630",
}


def fetch_samyang_stock_prices() -> list[dict]:
    start = date.today() - relativedelta(years=6)

    frames = []
    for name, code in TICKERS.items():
        df = fdr.DataReader(code, start.isoformat())[["Close"]].rename(columns={"Close": name})
        frames.append(df)

    wide = frames[0]
    for df in frames[1:]:
        wide = wide.join(df, how="outer")
    wide = wide.reset_index().rename(columns={"Date": "date"})

    return series_from_wide(wide, "date", list(TICKERS.keys()))
