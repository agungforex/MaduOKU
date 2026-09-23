import numpy as np
import pandas as pd

from maduoku.backtest.sweep import grid_search
from maduoku.config import Config


def _synthetic_ohlcv(n: int = 300, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    steps = rng.normal(loc=0.0, scale=1.0, size=n)
    trend = 10 * np.sin(np.linspace(0, 6 * np.pi, n))
    close = 100 + np.cumsum(steps) * 0.2 + trend

    high = close + rng.uniform(0.1, 0.5, size=n)
    low = close - rng.uniform(0.1, 0.5, size=n)
    open_ = close + rng.normal(0, 0.2, size=n)
    volume = rng.uniform(100, 1000, size=n)

    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=idx)


def test_grid_search_covers_every_combination_when_min_signals_is_zero():
    df = _synthetic_ohlcv()
    cfg = Config()
    grid = {
        "indicators.adx_trend_threshold": [20, 30],
        "scoring.min_score_to_alert": [2, 3],
    }

    results = grid_search(df, cfg, grid, forward_bars=5, step=3, min_signals=0)

    assert len(results) <= 4
    assert {"indicators.adx_trend_threshold", "scoring.min_score_to_alert", "signals", "win_rate", "avg_return"} <= set(
        results.columns
    )
    if len(results) > 1:
        assert results["avg_return"].is_monotonic_decreasing


def test_grid_search_drops_combos_below_min_signals():
    df = _synthetic_ohlcv()
    cfg = Config()
    grid = {"scoring.min_score_to_alert": [2, 99]}  # 99 is unreachable -> 0 signals

    results = grid_search(df, cfg, grid, forward_bars=5, step=3, min_signals=1)

    assert all(results["scoring.min_score_to_alert"] != 99)


def test_grid_search_does_not_mutate_base_config():
    df = _synthetic_ohlcv()
    cfg = Config()
    original_threshold = cfg.indicators.adx_trend_threshold

    grid_search(df, cfg, {"indicators.adx_trend_threshold": [15, 40]}, forward_bars=5, step=5, min_signals=0)

    assert cfg.indicators.adx_trend_threshold == original_threshold


def test_grid_search_empty_grid_returns_empty_dataframe():
    df = _synthetic_ohlcv(n=50)
    cfg = Config()

    results = grid_search(df, cfg, {}, forward_bars=5, step=5, min_signals=0)
    assert results.empty
