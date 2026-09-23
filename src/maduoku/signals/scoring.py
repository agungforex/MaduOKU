from __future__ import annotations

from dataclasses import dataclass, field

from .divergence import DivergenceSignal
from .regime import RegimeState

BULLISH_REVERSAL = {"regular_bullish"}
BEARISH_REVERSAL = {"regular_bearish"}


@dataclass
class EarlyWarning:
    symbol: str
    direction: str  # "bullish" | "bearish" | "none"
    score: int
    regime: RegimeState
    reasons: list[str] = field(default_factory=list)

    @property
    def is_actionable(self) -> bool:
        return self.direction != "none"


def score_signals(
    symbol: str,
    divergence_signals: list[DivergenceSignal],
    regime: RegimeState,
    min_score_to_alert: int = 2,
) -> EarlyWarning:
    """Combine divergence evidence across indicators into a single confluence
    score. Only *regular* divergence counts as a reversal warning; hidden
    divergence (continuation) is reported but does not add to the score.

    Ranging markets (low ADX) get a bonus point, since reversals are more
    reliable/expected outside strong trends. Reversal warnings *against* a
    strong trend are still surfaced, but flagged as lower-confidence via the
    reasons list rather than suppressed outright.
    """
    bull_hits = [s for s in divergence_signals if s.kind in BULLISH_REVERSAL]
    bear_hits = [s for s in divergence_signals if s.kind in BEARISH_REVERSAL]

    reasons = [f"{s.indicator_name}: {s.detail}" for s in divergence_signals]

    bull_score = len(bull_hits)
    bear_score = len(bear_hits)

    if not regime.trending:
        if bull_score:
            bull_score += 1
        if bear_score:
            bear_score += 1
        reasons.append(f"ranging market (ADX={regime.adx_value:.1f}) favors reversal")
    else:
        reasons.append(f"trending market (ADX={regime.adx_value:.1f}) — reversal signals are lower-confidence")

    if bull_score > bear_score and bull_score >= min_score_to_alert:
        return EarlyWarning(symbol, "bullish", bull_score, regime, reasons)
    if bear_score > bull_score and bear_score >= min_score_to_alert:
        return EarlyWarning(symbol, "bearish", bear_score, regime, reasons)

    return EarlyWarning(symbol, "none", max(bull_score, bear_score), regime, reasons)
