from __future__ import annotations

import pandas as pd


def pivot_highs(series: pd.Series, left: int = 3, right: int = 3) -> list[int]:
    """Return integer-position indices of local maxima (fractal highs)."""
    vals = series.to_numpy()
    n = len(vals)
    idx = []
    for i in range(left, n - right):
        window = vals[i - left : i + right + 1]
        if vals[i] == window.max() and (window == vals[i]).sum() == 1:
            idx.append(i)
    return idx


def pivot_lows(series: pd.Series, left: int = 3, right: int = 3) -> list[int]:
    """Return integer-position indices of local minima (fractal lows)."""
    vals = series.to_numpy()
    n = len(vals)
    idx = []
    for i in range(left, n - right):
        window = vals[i - left : i + right + 1]
        if vals[i] == window.min() and (window == vals[i]).sum() == 1:
            idx.append(i)
    return idx
