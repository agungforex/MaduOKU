"""Build the feature matrix used by the hybrid model: raw technical
indicator values plus rule-based signal flags (divergence, candlestick
patterns, overbought/oversold, band touches)."""
from __future__ import annotations

import pandas as pd

from . import indicators as ind


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """df must have columns: open, high, low, close, volume.
    Returns a feature DataFrame aligned to df.index (NaNs from warm-up
    windows are left in; drop them before training)."""
    close, high, low, volume = df["close"], df["high"], df["low"], df["volume"]

    feats = pd.DataFrame(index=df.index)

    feats["rsi_14"] = ind.rsi(close, 14)
    feats["rsi_overbought"] = (feats["rsi_14"] > 70).astype(int)
    feats["rsi_oversold"] = (feats["rsi_14"] < 30).astype(int)

    macd_line, signal_line, hist = ind.macd(close)
    feats["macd_hist"] = hist
    feats["macd_cross_up"] = ((hist > 0) & (hist.shift(1) <= 0)).astype(int)
    feats["macd_cross_down"] = ((hist < 0) & (hist.shift(1) >= 0)).astype(int)

    upper, mid, lower = ind.bollinger_bands(close)
    feats["bb_pct_b"] = (close - lower) / (upper - lower)
    feats["bb_upper_touch"] = (close >= upper).astype(int)
    feats["bb_lower_touch"] = (close <= lower).astype(int)

    feats["atr_14"] = ind.atr(high, low, close, 14)
    feats["atr_pct"] = feats["atr_14"] / close

    k, d = ind.stochastic(high, low, close)
    feats["stoch_k"] = k
    feats["stoch_d"] = d
    feats["stoch_overbought"] = (k > 80).astype(int)
    feats["stoch_oversold"] = (k < 20).astype(int)

    feats["vol_zscore"] = ind.volume_zscore(volume)

    bearish_div, bullish_div = ind.rolling_extrema_divergence(close, feats["rsi_14"], window=20)
    feats["bearish_divergence"] = bearish_div.astype(int)
    feats["bullish_divergence"] = bullish_div.astype(int)

    patterns = ind.candlestick_patterns(df)
    for col in patterns.columns:
        feats[col] = patterns[col].astype(int)

    feats["roc_5"] = close.pct_change(5)
    feats["roc_10"] = close.pct_change(10)
    feats["sma_20_dist"] = (close - ind.sma(close, 20)) / close

    return feats


def build_training_set(df: pd.DataFrame, labels: pd.Series):
    """Align features and labels, dropping warm-up NaN rows."""
    feats = build_features(df)
    data = feats.join(labels)
    data = data.dropna()
    X = data.drop(columns=[labels.name])
    y = data[labels.name]
    return X, y
