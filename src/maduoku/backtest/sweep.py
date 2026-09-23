from __future__ import annotations

import copy
import itertools

import pandas as pd

from ..config import Config
from .engine import run_backtest, summarize


def _apply_param(cfg: Config, dotted_key: str, value) -> None:
    """Set a nested config field from a dotted path, e.g.
    'indicators.adx_trend_threshold' -> cfg.indicators.adx_trend_threshold = value
    """
    parts = dotted_key.split(".")
    obj = cfg
    for part in parts[:-1]:
        obj = getattr(obj, part)
    setattr(obj, parts[-1], value)


def grid_search(
    df: pd.DataFrame,
    base_cfg: Config,
    grid: dict[str, list],
    forward_bars: int = 5,
    step: int = 1,
    min_signals: int = 1,
) -> pd.DataFrame:
    """Run the backtest engine over every combination of parameter values in
    `grid` (dotted config paths -> candidate values) and rank combinations by
    average return per signal.

    Combinations that fire fewer than `min_signals` trades are dropped —
    a high win rate from 2 lucky signals is not a config worth trusting.
    """
    if not grid:
        return pd.DataFrame()

    keys = list(grid.keys())
    value_lists = [grid[k] for k in keys]

    rows = []
    for combo in itertools.product(*value_lists):
        cfg = copy.deepcopy(base_cfg)
        for key, value in zip(keys, combo):
            _apply_param(cfg, key, value)

        trades = run_backtest(df, cfg, forward_bars=forward_bars, step=step)
        summary = summarize(trades)

        if summary.total_signals < min_signals:
            continue

        row = dict(zip(keys, combo))
        row.update(signals=summary.total_signals, win_rate=summary.win_rate, avg_return=summary.avg_return)
        rows.append(row)

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values("avg_return", ascending=False).reset_index(drop=True)
    return result
