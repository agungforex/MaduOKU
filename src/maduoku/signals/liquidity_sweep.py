from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class SweepSignal:
    kind: str  # "bullish_sweep" | "bearish_sweep"
    indicator_name: str
    price_index: pd.Timestamp
    detail: str


def detect_liquidity_sweep(df: pd.DataFrame, lookback: int = 20) -> list[SweepSignal]:
    """Detect a stop-hunt / liquidity sweep on the most recent completed bar:
    price wicks beyond the prior `lookback`-bar high or low, then closes back
    inside it — a classic Smart Money Concepts sign that resting stop orders
    were grabbed right before a reversal.
    """
    if len(df) < lookback + 1:
        return []

    window = df.iloc[-(lookback + 1) : -1]
    prior_high = window["High"].max()
    prior_low = window["Low"].min()

    last = df.iloc[-1]
    signals: list[SweepSignal] = []

    if last["High"] > prior_high and last["Close"] < prior_high:
        signals.append(
            SweepSignal(
                "bearish_sweep",
                "LiquiditySweep",
                df.index[-1],
                f"swept high {prior_high:.4g} then closed back below at {last['Close']:.4g}",
            )
        )

    if last["Low"] < prior_low and last["Close"] > prior_low:
        signals.append(
            SweepSignal(
                "bullish_sweep",
                "LiquiditySweep",
                df.index[-1],
                f"swept low {prior_low:.4g} then closed back above at {last['Close']:.4g}",
            )
        )

    return signals
