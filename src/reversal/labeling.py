"""Reversal labeling for supervised training.

Labels are built with a zigzag algorithm (swing pivots defined by a
minimum percentage retracement) and then projected backward onto a
lookahead window: a bar is labeled as "reversal imminent" if a
confirmed swing pivot occurs within the next `horizon` bars.

Only forward-looking information is used to build the *label* (this is
standard for training a predictive model). At inference time only past
bars are used as features -- see features.py / model.py.

Label values:
    0 = no reversal expected soon
    1 = bullish reversal imminent (swing low ahead -> expect price to turn up)
    2 = bearish reversal imminent (swing high ahead -> expect price to turn down)
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def zigzag_pivots(close: pd.Series, min_pct: float = 0.02) -> pd.Series:
    """Confirmed zigzag swing pivots.

    Returns a Series aligned to `close.index` with:
        +1 at a confirmed swing LOW (bottom)
        -1 at a confirmed swing HIGH (top)
         0 elsewhere
    """
    values = close.to_numpy()
    n = len(values)
    pivots = np.zeros(n, dtype=int)
    if n == 0:
        return pd.Series(pivots, index=close.index)

    last_pivot_idx = 0
    last_pivot_price = values[0]
    direction = 0  # 0 = undetermined, 1 = up, -1 = down
    extreme_idx = 0
    extreme_price = values[0]

    for i in range(1, n):
        price = values[i]

        if direction == 0:
            change = (price - last_pivot_price) / last_pivot_price
            if change >= min_pct:
                direction = 1
                extreme_idx, extreme_price = i, price
            elif change <= -min_pct:
                direction = -1
                extreme_idx, extreme_price = i, price
        elif direction == 1:
            if price > extreme_price:
                extreme_price, extreme_idx = price, i
            drawdown = (price - extreme_price) / extreme_price
            if drawdown <= -min_pct:
                pivots[extreme_idx] = -1  # swing high confirmed
                last_pivot_idx, last_pivot_price = extreme_idx, extreme_price
                direction = -1
                extreme_idx, extreme_price = i, price
        elif direction == -1:
            if price < extreme_price:
                extreme_price, extreme_idx = price, i
            rally = (price - extreme_price) / extreme_price
            if rally >= min_pct:
                pivots[extreme_idx] = 1  # swing low confirmed
                last_pivot_idx, last_pivot_price = extreme_idx, extreme_price
                direction = 1
                extreme_idx, extreme_price = i, price

    return pd.Series(pivots, index=close.index)


def build_reversal_labels(close: pd.Series, min_pct: float = 0.02, horizon: int = 10) -> pd.Series:
    """Label each bar 0/1/2 based on whether a confirmed swing pivot
    (bottom=1, top=2) falls within the next `horizon` bars."""
    pivots = zigzag_pivots(close, min_pct=min_pct)
    n = len(pivots)
    labels = np.zeros(n, dtype=int)
    pivot_arr = pivots.to_numpy()

    next_bottom = np.full(n, np.inf)
    next_top = np.full(n, np.inf)
    upcoming_bottom = np.inf
    upcoming_top = np.inf
    for i in range(n - 1, -1, -1):
        if pivot_arr[i] == 1:
            upcoming_bottom = i
        if pivot_arr[i] == -1:
            upcoming_top = i
        next_bottom[i] = upcoming_bottom
        next_top[i] = upcoming_top

    for i in range(n):
        dist_bottom = next_bottom[i] - i
        dist_top = next_top[i] - i
        candidates = []
        if 0 < dist_bottom <= horizon:
            candidates.append((dist_bottom, 1))
        if 0 < dist_top <= horizon:
            candidates.append((dist_top, 2))
        if candidates:
            candidates.sort()
            labels[i] = candidates[0][1]

    return pd.Series(labels, index=close.index, name="label")
