import numpy as np
import pandas as pd
import pytest

from maduoku.signals.hmm_regime import classify_regime_hmm


def _trending_close(n: int = 120, drift: float = 0.002, seed: int = 1) -> pd.Series:
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 0.0005, size=n)
    log_returns = drift + noise
    close = 100 * np.exp(np.cumsum(log_returns))
    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    return pd.Series(close, index=idx)


def _ranging_close(n: int = 120, seed: int = 2) -> pd.Series:
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 0.0003, size=n)
    close = 100 * np.exp(np.cumsum(noise))
    idx = pd.date_range("2024-01-01", periods=n, freq="h")
    return pd.Series(close, index=idx)


def test_strong_uptrend_is_labeled_trending():
    close = _trending_close(drift=0.003)
    regime = classify_regime_hmm(close, n_states=2, ranging_threshold=0.0005)

    assert regime.method == "hmm"
    assert regime.trending is True
    assert regime.label in {"trending_up", "trending_down"}


def test_strong_downtrend_is_labeled_trending_down():
    close = _trending_close(drift=-0.003)
    regime = classify_regime_hmm(close, n_states=2, ranging_threshold=0.0005)

    assert regime.trending is True
    assert regime.label == "trending_down"


def test_insufficient_history_raises():
    close = _ranging_close(n=10)
    with pytest.raises(ValueError):
        classify_regime_hmm(close, n_states=3)


def test_describe_uses_hmm_label():
    close = _trending_close(drift=0.003)
    regime = classify_regime_hmm(close, n_states=2)

    assert "HMM regime=" in regime.describe()
