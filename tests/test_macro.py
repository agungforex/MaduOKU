import pandas as pd

from maduoku.signals.macro import macro_bias_signal, macro_trend_direction


def _series(values: list[float]) -> pd.Series:
    idx = pd.date_range("2024-01-01", periods=len(values), freq="h")
    return pd.Series(values, index=idx)


def test_macro_trend_direction_up():
    s = _series([100, 100, 100, 100, 100, 103])
    assert macro_trend_direction(s, lookback=5) == "up"


def test_macro_trend_direction_down():
    s = _series([100, 100, 100, 100, 100, 97])
    assert macro_trend_direction(s, lookback=5) == "down"


def test_macro_trend_direction_flat_within_threshold():
    s = _series([100, 100, 100, 100, 100, 100.05])
    assert macro_trend_direction(s, lookback=5) == "flat"


def test_macro_trend_direction_insufficient_history():
    s = _series([100, 101])
    assert macro_trend_direction(s, lookback=5) == "flat"


def test_positive_correlation_up_is_bullish():
    # e.g. VIX rising -> bullish bias for gold (correlation +1)
    s = _series([100, 100, 100, 100, 100, 105])
    signal = macro_bias_signal("VIX", s, correlation=1, lookback=5)
    assert signal is not None
    assert signal.kind == "macro_bullish"


def test_inverse_correlation_up_is_bearish():
    # e.g. DXY rising -> bearish bias for gold (correlation -1)
    s = _series([100, 100, 100, 100, 100, 105])
    signal = macro_bias_signal("DXY", s, correlation=-1, lookback=5)
    assert signal is not None
    assert signal.kind == "macro_bearish"


def test_inverse_correlation_down_is_bullish():
    # e.g. DXY falling -> bullish bias for gold (correlation -1)
    s = _series([100, 100, 100, 100, 100, 95])
    signal = macro_bias_signal("DXY", s, correlation=-1, lookback=5)
    assert signal is not None
    assert signal.kind == "macro_bullish"


def test_flat_macro_returns_no_signal():
    s = _series([100, 100, 100, 100, 100, 100.0])
    assert macro_bias_signal("DXY", s, correlation=-1, lookback=5) is None
