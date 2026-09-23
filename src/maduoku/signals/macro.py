from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class MacroSignal:
    kind: str  # "macro_bullish" | "macro_bearish"
    indicator_name: str
    price_index: pd.Timestamp
    detail: str


def macro_trend_direction(close: pd.Series, lookback: int = 5, flat_threshold: float = 0.001) -> str:
    """Return 'up', 'down', or 'flat' based on % change over the last
    `lookback` bars. `flat_threshold` filters out noise too small to call
    a real move (default 0.1%).
    """
    if len(close) < lookback + 1:
        return "flat"

    start = close.iloc[-1 - lookback]
    change = (close.iloc[-1] - start) / start

    if change > flat_threshold:
        return "up"
    if change < -flat_threshold:
        return "down"
    return "flat"


def macro_bias_signal(
    name: str, close: pd.Series, correlation: int, lookback: int = 5
) -> MacroSignal | None:
    """Translate a macro instrument's recent trend into a bullish/bearish
    bias for the correlated tradable symbol.

    `correlation` is +1 for a positively-correlated instrument (macro up ->
    bullish bias) or -1 for an inversely-correlated one (macro up -> bearish
    bias) — e.g. DXY is typically -1 for gold, VIX is typically +1 for gold
    and -1 for bitcoin (risk-off flows into gold, out of risk assets).
    """
    direction = macro_trend_direction(close, lookback)
    if direction == "flat":
        return None

    macro_up_means_bullish = correlation > 0
    is_bullish = (direction == "up") == macro_up_means_bullish
    kind = "macro_bullish" if is_bullish else "macro_bearish"
    corr_label = "positive" if correlation > 0 else "inverse"

    return MacroSignal(
        kind,
        name,
        close.index[-1],
        f"{name} trending {direction} ({corr_label} correlation)",
    )
