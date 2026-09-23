"""Technical indicators and rule-based signal flags, implemented from
scratch with pandas/numpy (no ta-lib dependency needed)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger_bands(close: pd.Series, window: int = 20, num_std: float = 2.0):
    mid = sma(close, window)
    std = close.rolling(window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / window, adjust=False).mean()


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_window: int = 14, d_window: int = 3):
    lowest_low = low.rolling(k_window).min()
    highest_high = high.rolling(k_window).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    d = k.rolling(d_window).mean()
    return k, d


def volume_zscore(volume: pd.Series, window: int = 20) -> pd.Series:
    mean = volume.rolling(window).mean()
    std = volume.rolling(window).std()
    return (volume - mean) / std.replace(0, np.nan)


def rolling_extrema_divergence(price: pd.Series, osc: pd.Series, window: int = 20) -> tuple[pd.Series, pd.Series]:
    """Flag bearish/bullish divergence between price and an oscillator
    (e.g. RSI) using rolling local extrema over `window` bars.

    Bearish divergence: price makes a higher high, oscillator makes a
    lower high (momentum fading on an uptrend -> possible top).
    Bullish divergence: price makes a lower low, oscillator makes a
    higher low (momentum fading on a downtrend -> possible bottom).
    """
    price_roll_max = price.rolling(window).max()
    price_roll_min = price.rolling(window).min()
    osc_roll_max = osc.rolling(window).max()
    osc_roll_min = osc.rolling(window).min()

    price_prev_max = price_roll_max.shift(window)
    price_prev_min = price_roll_min.shift(window)
    osc_prev_max = osc_roll_max.shift(window)
    osc_prev_min = osc_roll_min.shift(window)

    bearish_div = (price_roll_max > price_prev_max) & (osc_roll_max < osc_prev_max)
    bullish_div = (price_roll_min < price_prev_min) & (osc_roll_min > osc_prev_min)
    return bearish_div.fillna(False), bullish_div.fillna(False)


def candlestick_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """Return boolean flags for a handful of classic reversal candlestick
    patterns, computed from open/high/low/close only."""
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    body = (c - o).abs()
    range_ = (h - l).replace(0, np.nan)
    upper_wick = h - c.where(c >= o, o)
    lower_wick = c.where(c <= o, o) - l

    prev_o, prev_c = o.shift(1), c.shift(1)

    bullish_engulfing = (c > o) & (prev_c < prev_o) & (c >= prev_o) & (o <= prev_c)
    bearish_engulfing = (c < o) & (prev_c > prev_o) & (o >= prev_c) & (c <= prev_o)

    hammer = (lower_wick >= 2 * body) & (upper_wick <= 0.3 * body.replace(0, np.nan)) & (body / range_ < 0.35)
    shooting_star = (upper_wick >= 2 * body) & (lower_wick <= 0.3 * body.replace(0, np.nan)) & (body / range_ < 0.35)
    doji = body / range_ < 0.1

    return pd.DataFrame({
        "bullish_engulfing": bullish_engulfing.fillna(False),
        "bearish_engulfing": bearish_engulfing.fillna(False),
        "hammer": hammer.fillna(False),
        "shooting_star": shooting_star.fillna(False),
        "doji": doji.fillna(False),
    })
