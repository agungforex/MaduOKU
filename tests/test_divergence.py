import pandas as pd

from maduoku.signals.divergence import detect_divergence


def _df_from_close(closes: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="h")
    return pd.DataFrame({"Close": closes}, index=idx)


def test_regular_bearish_divergence_detected():
    # Price makes a higher high across two peaks; oscillator makes a lower high.
    close = [10, 12, 10, 9, 10, 14, 10]
    indicator = [50, 60, 50, 40, 50, 55, 50]

    df = _df_from_close(close)
    ind = pd.Series(indicator, index=df.index)

    signals = detect_divergence(df, ind, "TEST", left=1, right=1, max_pivot_lookback=5)
    kinds = {s.kind for s in signals}
    assert "regular_bearish" in kinds


def test_regular_bullish_divergence_detected():
    # Price makes a lower low across two troughs; oscillator makes a higher low.
    close = [10, 8, 10, 11, 10, 6, 10]
    indicator = [50, 40, 50, 55, 50, 45, 50]

    df = _df_from_close(close)
    ind = pd.Series(indicator, index=df.index)

    signals = detect_divergence(df, ind, "TEST", left=1, right=1, max_pivot_lookback=5)
    kinds = {s.kind for s in signals}
    assert "regular_bullish" in kinds


def test_no_signal_on_flat_series():
    close = [10.0] * 15
    df = _df_from_close(close)
    ind = pd.Series(close, index=df.index)

    signals = detect_divergence(df, ind, "TEST")
    assert signals == []
