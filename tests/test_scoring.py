from maduoku.signals.divergence import DivergenceSignal
from maduoku.signals.liquidity_sweep import SweepSignal
from maduoku.signals.macro import MacroSignal
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


def test_divergence_plus_sweep_confluence_triggers_alert():
    signals = [
        DivergenceSignal("regular_bearish", "RSI", None, "detail"),
        SweepSignal("bearish_sweep", "LiquiditySweep", None, "swept high, closed back below"),
    ]
    regime = RegimeState(trending=True, adx_value=30.0)

    warning = score_signals("gold", signals, regime, min_score_to_alert=2)

    assert warning.direction == "bearish"
    assert warning.score >= 2


def test_sweep_alone_below_threshold_does_not_trigger():
    signals = [SweepSignal("bullish_sweep", "LiquiditySweep", None, "swept low, closed back above")]
    regime = RegimeState(trending=True, adx_value=30.0)

    warning = score_signals("bitcoin", signals, regime, min_score_to_alert=2)

    assert warning.direction == "none"


def test_divergence_plus_macro_confluence_triggers_alert():
    signals = [
        DivergenceSignal("regular_bullish", "RSI", None, "detail"),
        MacroSignal("macro_bullish", "DXY", None, "DXY trending down (inverse correlation)"),
    ]
    regime = RegimeState(trending=True, adx_value=30.0)

    warning = score_signals("gold", signals, regime, min_score_to_alert=2)

    assert warning.direction == "bullish"
    assert warning.score >= 2
