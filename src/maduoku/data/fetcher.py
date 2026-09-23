from __future__ import annotations

import pandas as pd
import yfinance as yf


def fetch_ohlcv(ticker: str, interval: str = "1h", period: str = "60d") -> pd.DataFrame:
    """Fetch OHLCV candles for a symbol via yfinance.

    Returns a DataFrame indexed by datetime with columns:
    Open, High, Low, Close, Volume
    """
    df = yf.download(
        ticker,
        interval=interval,
        period=period,
        auto_adjust=True,
        progress=False,
    )
    if df.empty:
        raise ValueError(f"No data returned for {ticker} (interval={interval}, period={period})")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.rename(columns=str.title)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
