import numpy as np
import pandas as pd

from maduoku.backtest.engine import run_backtest, summarize
from maduoku.config import Config


def _synthetic_ohlcv(n: int = 300, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    steps = rng.normal(loc=0.0, scale=1.0, size=n)
    # add a slow oscillation so price trends and reverses, giving the
    # detector something to find rather than pure random noise.
    trend = 10 * np.sin(np.linspace(0, 6 * np.pi, n))
    close = 100 + np.cumsum(steps) * 0.2 + trend

    high = close + rng.uniform(0.1, 0.5, size=n)
    low = close - rng.uniform(0.1, 0.5, size=n)
    open_ = close + rng.normal(0, 0.2, size=n)
    volume = rng.uniform(100, 1000, size=n)

    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume}, index=idx)


def test_run_backtest_produces_well_formed_trades():
    df = _synthetic_ohlcv()
    cfg = Config()

    trades = run_backtest(df, cfg, forward_bars=5, step=2)

    assert list(trades.columns) == ["time", "direction", "score", "entry", "exit", "return"]
    if not trades.empty:
        assert set(trades["direction"]).issubset({"bullish", "bearish"})
        assert trades["score"].min() >= cfg.scoring.min_score_to_alert


def test_summarize_handles_empty_trades():
    empty = pd.DataFrame(columns=["time", "direction", "score", "entry", "exit", "return"])
    summary = summarize(empty)

    assert summary.total_signals == 0
    assert summary.win_rate == 0.0
    assert summary.by_direction.empty


def test_summarize_computes_win_rate_and_avg_return():
    trades = pd.DataFrame(
        {
            "time": pd.date_range("2024-01-01", periods=4, freq="h"),
            "direction": ["bullish", "bullish", "bearish", "bearish"],
            "score": [2, 2, 3, 2],
            "entry": [100, 100, 100, 100],
            "exit": [101, 99, 103, 97],
            "return": [0.01, -0.01, 0.03, -0.03],
        }
    )

    summary = summarize(trades)

    assert summary.total_signals == 4
    assert summary.win_rate == 0.5
    assert summary.avg_return == 0.0
    assert set(summary.by_direction.index) == {"bullish", "bearish"}
