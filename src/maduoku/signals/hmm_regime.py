from __future__ import annotations

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

from .regime import RegimeState


def classify_regime_hmm(
    close: pd.Series,
    n_states: int = 3,
    ranging_threshold: float = 0.0005,
    random_state: int = 42,
) -> RegimeState:
    """Fit a Gaussian HMM on log returns and label the current hidden state
    as trending-up, trending-down, or ranging based on that state's mean
    return, rather than a fixed ADX threshold.

    This adapts to each symbol's own volatility/behavior instead of assuming
    one threshold fits gold and bitcoin equally, at the cost of needing
    enough history to fit reliably and being sensitive to random_state on
    short series.
    """
    prices = close.dropna().to_numpy()
    min_bars = n_states * 20
    if len(prices) < min_bars:
        raise ValueError(f"need at least {min_bars} bars to fit a {n_states}-state HMM, got {len(prices)}")

    log_returns = np.diff(np.log(prices))
    X = log_returns.reshape(-1, 1)

    model = GaussianHMM(n_components=n_states, covariance_type="diag", n_iter=200, random_state=random_state)
    model.fit(X)

    hidden_states = model.predict(X)
    current_state = int(hidden_states[-1])
    state_mean = float(model.means_[current_state, 0])

    if abs(state_mean) < ranging_threshold:
        label = "ranging"
    elif state_mean > 0:
        label = "trending_up"
    else:
        label = "trending_down"

    return RegimeState(trending=label != "ranging", method="hmm", label=label)
