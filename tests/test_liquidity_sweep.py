import pandas as pd

from maduoku.signals.liquidity_sweep import detect_liquidity_sweep


def _make_df(rows: list[dict]) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=len(rows), freq="h")
    return pd.DataFrame(rows, index=idx)


def _flat_rows(n: int, level: float = 100.0) -> list[dict]:
    return [{"Open": level, "High": level + 0.5, "Low": level - 0.5, "Close": level} for _ in range(n)]


def test_bearish_sweep_detected_when_high_swept_and_closed_back_below():
    rows = _flat_rows(20, level=100.0)
    # last bar wicks above the prior 20-bar high (100.5) then closes back below it
    rows.append({"Open": 100.2, "High": 102.0, "Low": 100.0, "Close": 100.3})

    df = _make_df(rows)
    signals = detect_liquidity_sweep(df, lookback=20)

    kinds = {s.kind for s in signals}
    assert "bearish_sweep" in kinds


def test_bullish_sweep_detected_when_low_swept_and_closed_back_above():
    rows = _flat_rows(20, level=100.0)
    # last bar wicks below the prior 20-bar low (99.5) then closes back above it
    rows.append({"Open": 99.8, "High": 100.0, "Low": 98.0, "Close": 99.7})

    df = _make_df(rows)
    signals = detect_liquidity_sweep(df, lookback=20)

    kinds = {s.kind for s in signals}
    assert "bullish_sweep" in kinds


def test_no_sweep_when_price_stays_in_range():
    rows = _flat_rows(25, level=100.0)
    df = _make_df(rows)

    signals = detect_liquidity_sweep(df, lookback=20)
    assert signals == []


def test_no_sweep_when_break_closes_beyond_range_instead_of_back_inside():
    rows = _flat_rows(20, level=100.0)
    # closes *beyond* the swept high — this is a breakout, not a sweep
    rows.append({"Open": 100.2, "High": 102.0, "Low": 100.0, "Close": 101.8})

    df = _make_df(rows)
    signals = detect_liquidity_sweep(df, lookback=20)
    assert signals == []


def test_insufficient_history_returns_no_signals():
    df = _make_df(_flat_rows(5))
    assert detect_liquidity_sweep(df, lookback=20) == []
