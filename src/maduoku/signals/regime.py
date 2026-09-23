from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class RegimeState:
    trending: bool
    adx_value: float = float("nan")
    method: str = "adx"
    label: str = ""

    def describe(self) -> str:
        if self.method == "hmm":
            return f"HMM regime={self.label}"
        return f"ADX={self.adx_value:.1f}"


def classify_regime(adx_series: pd.Series, trend_threshold: float = 25.0) -> RegimeState:
    latest = adx_series.dropna().iloc[-1] if adx_series.dropna().size else float("nan")
    trending = bool(latest >= trend_threshold)
    return RegimeState(
        trending=trending,
        adx_value=float(latest),
        method="adx",
        label="trending" if trending else "ranging",
    )
