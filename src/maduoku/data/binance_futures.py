from __future__ import annotations

import pandas as pd
import requests

BASE_URL = "https://fapi.binance.com"
KLINES_ENDPOINT = f"{BASE_URL}/fapi/v1/klines"

_KLINE_COLUMNS = [
    "OpenTime",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "CloseTime",
    "QuoteVolume",
    "Trades",
    "TakerBuyBase",
    "TakerBuyQuote",
    "Ignore",
]


def fetch_ohlcv(
    symbol: str,
    interval: str = "1h",
    limit: int = 500,
    start_time: int | None = None,
    end_time: int | None = None,
    timeout: float = 15.0,
) -> pd.DataFrame:
    """Fetch historical OHLCV candles from Binance USDⓈ-M Futures.

    `symbol` is a Binance futures symbol, e.g. "BTCUSDT" or "PAXGUSDT" (gold proxy).
    `limit` is capped at 1500 by Binance's API.
    `start_time`/`end_time` are optional millisecond epoch timestamps.
    """
    params: dict[str, str | int] = {"symbol": symbol, "interval": interval, "limit": min(limit, 1500)}
    if start_time is not None:
        params["startTime"] = start_time
    if end_time is not None:
        params["endTime"] = end_time

    resp = requests.get(KLINES_ENDPOINT, params=params, timeout=timeout)
    resp.raise_for_status()
    raw = resp.json()

    if not raw:
        raise ValueError(f"No data returned for {symbol} (interval={interval}, limit={limit})")

    df = pd.DataFrame(raw, columns=_KLINE_COLUMNS)
    df["OpenTime"] = pd.to_datetime(df["OpenTime"], unit="ms")
    df = df.set_index("OpenTime")

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = df[col].astype(float)

    return df[["Open", "High", "Low", "Close", "Volume"]]
