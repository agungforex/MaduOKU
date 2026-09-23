from maduoku.signals.divergence import DivergenceSignal
from maduoku.signals.regime import RegimeState
from maduoku.signals.scoring import score_signals


def test_bullish_confluence_triggers_alert():
    signals = [
        DivergenceSignal("regular_bullish", "RSI", None, "detail"),
        DivergenceSignal("regular_bullish", "MACD", None, "detail"),
    ]
    regime = RegimeState(trending=False, adx_value=15.0)

    warning = score_signals("gold", signals, regime, min_score_to_alert=2)

    assert warning.direction == "bullish"
    assert warning.is_actionable
    assert warning.score >= 2


def test_no_signals_yields_none_direction():
    regime = RegimeState(trending=True, adx_value=30.0)
    warning = score_signals("bitcoin", [], regime, min_score_to_alert=2)

    assert warning.direction == "none"
    assert not warning.is_actionable


def test_hidden_divergence_does_not_trigger_alone():
    signals = [DivergenceSignal("hidden_bullish", "RSI", None, "detail")]
    regime = RegimeState(trending=True, adx_value=30.0)

    warning = score_signals("gold", signals, regime, min_score_to_alert=2)

    assert warning.direction == "none"
