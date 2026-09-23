"""Build the feature matrix used by the hybrid model: raw technical
indicator values plus rule-based signal flags (divergence, candlestick
patterns, overbought/oversold, band touches)."""
from __future__ import annotations

import pandas as pd

from . import indicators as ind


def build_htf_context_features(low_index: pd.DatetimeIndex, htf_df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Compact trend-context features from a higher timeframe, aligned
    onto `low_index`.

    Only higher-timeframe bars that have fully closed strictly before
    each low-timeframe timestamp are used (merge_asof, backward,
    excluding exact matches) -- this avoids leaking information from a
    higher-timeframe bar that hasn't closed yet at inference time.
    """
    close = htf_df["close"]
    htf_feats = pd.DataFrame(index=htf_df.index)
    htf_feats[f"{label}_rsi_14"] = ind.rsi(close, 14)
    _, _, hist = ind.macd(close)
    htf_feats[f"{label}_macd_hist"] = hist
    upper, mid, lower = ind.bollinger_bands(close)
    htf_feats[f"{label}_bb_pct_b"] = (close - lower) / (upper - lower)
    htf_feats[f"{label}_sma20_dist"] = (close - ind.sma(close, 20)) / close
    htf_feats[f"{label}_trend_up"] = (ind.sma(close, 20) > ind.sma(close, 50)).astype(int)
    htf_feats[f"{label}_roc_5"] = close.pct_change(5)

    low_frame = pd.DataFrame(index=low_index).reset_index()
    htf_frame = htf_feats.reset_index()
    merged = pd.merge_asof(
        low_frame, htf_frame, on="datetime", direction="backward", allow_exact_matches=False,
    )
    return merged.set_index("datetime")


def build_features(df: pd.DataFrame, htf_frames: dict[str, pd.DataFrame] | None = None) -> pd.DataFrame:
    """df must have columns: open, high, low, close, volume.
    `htf_frames` optionally maps a label (e.g. "htf60") to a higher
    timeframe OHLC DataFrame (see data.discover_higher_timeframes) --
    its trend context is merged in as extra features.
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

    for label, htf_df in (htf_frames or {}).items():
        htf_feats = build_htf_context_features(df.index, htf_df, label)
        feats = feats.join(htf_feats)

    return feats


def build_training_set(df: pd.DataFrame, labels: pd.Series, htf_frames: dict[str, pd.DataFrame] | None = None):
    """Align features and labels, dropping warm-up NaN rows."""
    feats = build_features(df, htf_frames=htf_frames)
    data = feats.join(labels)
    data = data.dropna()
    X = data.drop(columns=[labels.name])
    y = data[labels.name]
    return X, y
