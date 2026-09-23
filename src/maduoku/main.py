from __future__ import annotations

import argparse
import sys

from .alerts.telegram import send_telegram_message
from .config import Config
from .data import binance_futures
from .data.fetcher import fetch_ohlcv
from .indicators.adx import adx
from .indicators.macd import macd
from .indicators.rsi import rsi
from .signals.divergence import detect_divergence
from .signals.liquidity_sweep import detect_liquidity_sweep
from .signals.macro import macro_bias_signal
from .signals.regime import classify_regime
from .signals.scoring import EarlyWarning, score_signals


def fetch_data(name: str, cfg: Config):
    tickers = cfg.symbols[name]
    ticker = tickers[cfg.data_source]

    if cfg.data_source == "binance_futures":
        return binance_futures.fetch_ohlcv(ticker, interval=cfg.interval, limit=cfg.binance_limit)
    if cfg.data_source == "yfinance":
        return fetch_ohlcv(ticker, interval=cfg.interval, period=cfg.lookback_period)
    raise ValueError(f"Unknown data_source: {cfg.data_source!r}")


def fetch_macro_signals(name: str, cfg: Config) -> list:
    """Macro instruments (DXY, VIX, ...) aren't on Binance Futures, so these
    are always pulled via yfinance regardless of the main data_source. A
    fetch failure here is non-fatal — it just means one less confluence
    point for this run, not a failed scan.
    """
    entries = cfg.macro_filters.filters.get(name, [])
    if not cfg.macro_filters.enabled or not entries:
        return []

    signals = []
    for entry in entries:
        try:
            macro_df = fetch_ohlcv(entry.ticker, interval=cfg.interval, period=cfg.lookback_period)
        except Exception as exc:  # noqa: BLE001
            print(f"  (macro filter {entry.ticker} unavailable: {exc})", file=sys.stderr)
            continue

        signal = macro_bias_signal(entry.ticker, macro_df["Close"], entry.correlation, cfg.macro_filters.lookback)
        if signal:
            signals.append(signal)

    return signals


def analyze_symbol(name: str, cfg: Config) -> EarlyWarning:
    df = fetch_data(name, cfg)

    rsi_series = rsi(df["Close"], cfg.indicators.rsi_period)
    _, _, macd_hist = macd(
        df["Close"], cfg.indicators.macd_fast, cfg.indicators.macd_slow, cfg.indicators.macd_signal
    )
    adx_series = adx(df, cfg.indicators.adx_period)

    div = cfg.divergence
    signals = detect_divergence(
        df, rsi_series, "RSI", div.pivot_left, div.pivot_right, div.max_pivot_lookback
    ) + detect_divergence(
        df, macd_hist, "MACD", div.pivot_left, div.pivot_right, div.max_pivot_lookback
    )

    if cfg.liquidity_sweep.enabled:
        signals += detect_liquidity_sweep(df, cfg.liquidity_sweep.lookback)

    signals += fetch_macro_signals(name, cfg)

    regime = classify_regime(adx_series, cfg.indicators.adx_trend_threshold)
    return score_signals(name, signals, regime, cfg.scoring.min_score_to_alert)


def format_warning(warning: EarlyWarning) -> str:
    if warning.is_actionable:
        header = f"⚠️ EARLY WARNING REVERSAL: {warning.symbol.upper()} — {warning.direction.upper()} (score={warning.score})"
    else:
        header = f"{warning.symbol.upper()}: no reversal signal (score={warning.score})"

    body = "\n".join(f"  - {r}" for r in warning.reasons)
    return f"{header}\n{body}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MaduOKU — early warning reversal scanner")
    parser.add_argument("--config", default="config.example.yaml", help="Path to YAML config")
    parser.add_argument("--telegram", action="store_true", help="Send alerts to Telegram")
    args = parser.parse_args(argv)

    cfg = Config.from_yaml(args.config)

    exit_code = 0
    for name in cfg.symbols:
        try:
            warning = analyze_symbol(name, cfg)
        except Exception as exc:  # noqa: BLE001
            print(f"{name.upper()}: failed to analyze ({exc})", file=sys.stderr)
            exit_code = 1
            continue

        print(format_warning(warning))

        if args.telegram and warning.is_actionable:
            send_telegram_message(cfg.telegram.bot_token, cfg.telegram.chat_id, format_warning(warning))

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
