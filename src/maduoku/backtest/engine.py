from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..config import Config
from ..indicators.adx import adx
from ..indicators.macd import macd
from ..indicators.rsi import rsi
from ..signals.divergence import detect_divergence
from ..signals.liquidity_sweep import detect_liquidity_sweep
from ..signals.regime import classify_regime
from ..signals.scoring import score_signals


@dataclass
class BacktestSummary:
    total_signals: int
    win_rate: float
    avg_return: float
    by_direction: pd.DataFrame


def run_backtest(df: pd.DataFrame, cfg: Config, forward_bars: int = 5, step: int = 1) -> pd.DataFrame:
    """Walk forward through history, re-running the live detection pipeline
    at each point using only data known up to that bar (no lookahead), and
    record the realized forward return whenever an actionable warning fires.

    A pivot needs `pivot_right` bars *after* it to be confirmed, so slicing
    the series to `df.iloc[:i+1]` naturally excludes any pivot the live
    system could not have known about yet at bar i.
    """
    close = df["Close"]
    rsi_series = rsi(close, cfg.indicators.rsi_period)
    _, _, macd_hist = macd(close, cfg.indicators.macd_fast, cfg.indicators.macd_slow, cfg.indicators.macd_signal)
    adx_series = adx(df, cfg.indicators.adx_period)

    div = cfg.divergence
    warmup = (
        max(cfg.indicators.adx_period, cfg.indicators.macd_slow, cfg.indicators.rsi_period)
        + div.pivot_left
        + div.pivot_right
        + 5
    )

    records = []
    n = len(df)
    for i in range(warmup, n - forward_bars, step):
        sub_df = df.iloc[: i + 1]
        signals = detect_divergence(
            sub_df, rsi_series.iloc[: i + 1], "RSI", div.pivot_left, div.pivot_right, div.max_pivot_lookback
        ) + detect_divergence(
            sub_df, macd_hist.iloc[: i + 1], "MACD", div.pivot_left, div.pivot_right, div.max_pivot_lookback
        )

        if cfg.liquidity_sweep.enabled:
            signals += detect_liquidity_sweep(sub_df, cfg.liquidity_sweep.lookback)

        regime = classify_regime(adx_series.iloc[: i + 1], cfg.indicators.adx_trend_threshold)
        warning = score_signals("backtest", signals, regime, cfg.scoring.min_score_to_alert)

        if not warning.is_actionable:
            continue

        entry = close.iloc[i]
        exit_ = close.iloc[i + forward_bars]
        raw_return = (exit_ - entry) / entry
        realized_return = raw_return if warning.direction == "bullish" else -raw_return

        records.append(
            {
                "time": df.index[i],
                "direction": warning.direction,
                "score": warning.score,
                "entry": entry,
                "exit": exit_,
                "return": realized_return,
            }
        )

    return pd.DataFrame(records, columns=["time", "direction", "score", "entry", "exit", "return"])


def summarize(trades: pd.DataFrame) -> BacktestSummary:
    if trades.empty:
        empty = pd.DataFrame(columns=["count", "win_rate", "avg_return"])
        return BacktestSummary(total_signals=0, win_rate=0.0, avg_return=0.0, by_direction=empty)

    by_direction = trades.groupby("direction")["return"].agg(
        count="count", win_rate=lambda s: (s > 0).mean(), avg_return="mean"
    )

    return BacktestSummary(
        total_signals=len(trades),
        win_rate=float((trades["return"] > 0).mean()),
        avg_return=float(trades["return"].mean()),
        by_direction=by_direction,
    )
