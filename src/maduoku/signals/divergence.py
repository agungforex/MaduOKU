from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .pivots import pivot_highs, pivot_lows

DivergenceKind = str  # "regular_bullish" | "regular_bearish" | "hidden_bullish" | "hidden_bearish"


@dataclass
class DivergenceSignal:
    kind: DivergenceKind
    indicator_name: str
    price_index: pd.Timestamp
    detail: str


def _last_two(idx: list[int], max_lookback: int) -> list[int]:
    return idx[-max_lookback:] if len(idx) > max_lookback else idx


def detect_divergence(
    df: pd.DataFrame,
    indicator: pd.Series,
    indicator_name: str,
    left: int = 3,
    right: int = 3,
    max_pivot_lookback: int = 5,
) -> list[DivergenceSignal]:
    """Compare the last two swing highs/lows in price vs. an oscillator to
    find regular and hidden bullish/bearish divergence.

    Regular bearish: price HH, indicator LH  -> warns of downside reversal.
    Regular bullish: price LL, indicator HL  -> warns of upside reversal.
    Hidden bearish:  price LH, indicator HH  -> warns of trend continuation down.
    Hidden bullish:  price HL, indicator LL  -> warns of trend continuation up.
    """
    close = df["Close"]
    signals: list[DivergenceSignal] = []

    highs = _last_two(pivot_highs(close, left, right), max_pivot_lookback)
    lows = _last_two(pivot_lows(close, left, right), max_pivot_lookback)

    if len(highs) >= 2:
        i1, i2 = highs[-2], highs[-1]
        price_hh = close.iloc[i2] > close.iloc[i1]
        ind_lh = indicator.iloc[i2] < indicator.iloc[i1]
        price_lh = close.iloc[i2] < close.iloc[i1]
        ind_hh = indicator.iloc[i2] > indicator.iloc[i1]

        if price_hh and ind_lh:
            signals.append(
                DivergenceSignal(
                    "regular_bearish",
                    indicator_name,
                    close.index[i2],
                    f"price higher-high but {indicator_name} lower-high",
                )
            )
        elif price_lh and ind_hh:
            signals.append(
                DivergenceSignal(
                    "hidden_bearish",
                    indicator_name,
                    close.index[i2],
                    f"price lower-high but {indicator_name} higher-high",
                )
            )

    if len(lows) >= 2:
        i1, i2 = lows[-2], lows[-1]
        price_ll = close.iloc[i2] < close.iloc[i1]
        ind_hl = indicator.iloc[i2] > indicator.iloc[i1]
        price_hl = close.iloc[i2] > close.iloc[i1]
        ind_ll = indicator.iloc[i2] < indicator.iloc[i1]

        if price_ll and ind_hl:
            signals.append(
                DivergenceSignal(
                    "regular_bullish",
                    indicator_name,
                    close.index[i2],
                    f"price lower-low but {indicator_name} higher-low",
                )
            )
        elif price_hl and ind_ll:
            signals.append(
                DivergenceSignal(
                    "hidden_bullish",
                    indicator_name,
                    close.index[i2],
                    f"price higher-low but {indicator_name} lower-low",
                )
            )

    return signals
