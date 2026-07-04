from datetime import date
import pandas as pd
import yfinance as yf
from dateutil.relativedelta import relativedelta
from .util import series_from_wide

TICKERS = {
    "WTI유가": "CL=F",
    "브렌트유": "BZ=F",
    "천연가스": "NG=F",
    "구리(전기동)": "HG=F",
    "밀": "ZW=F",
    "옥수수": "ZC=F",
    "대두": "ZS=F",
    "대두유": "ZL=F",
    "설탕(원당)": "SB=F",
    "커피": "KC=F",
    "달러인덱스": "DX-Y.NYB",
    "원달러환율": "KRW=X",
    "원유로환율": "EURKRW=X",
    "KOSPI": "^KS11",
    "미국국채10년": "^TNX",
}


def fetch_market_prices() -> list[dict]:
    end = date.today()
    start = end - relativedelta(years=6)

    raw = yf.download(
        list(TICKERS.values()),
        start=start.isoformat(),
        end=end.isoformat(),
        interval="1d",
        auto_adjust=False,
        group_by="column",
        progress=False,
        threads=True,
    )

    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"].copy()
    else:
        close = raw[["Close"]].copy()
        close.columns = list(TICKERS.values())

    sym2name = {v: k for k, v in TICKERS.items()}
    close = close.rename(columns=sym2name)
    close = close[[n for n in TICKERS if n in close.columns]].reset_index()
    close = close.rename(columns={close.columns[0]: "date"})

    return series_from_wide(close, "date", list(TICKERS.keys()))
