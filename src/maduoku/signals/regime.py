from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class RegimeState:
    trending: bool
    adx_value: float


def classify_regime(adx_series: pd.Series, trend_threshold: float = 25.0) -> RegimeState:
    latest = adx_series.dropna().iloc[-1] if adx_series.dropna().size else float("nan")
    return RegimeState(trending=bool(latest >= trend_threshold), adx_value=float(latest))
