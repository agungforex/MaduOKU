from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class IndicatorConfig:
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    adx_period: int = 14
    adx_trend_threshold: float = 25.0


@dataclass
class DivergenceConfig:
    pivot_left: int = 3
    pivot_right: int = 3
    max_pivot_lookback: int = 5


@dataclass
class ScoringConfig:
    min_score_to_alert: int = 2


@dataclass
class TelegramConfig:
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


_DEFAULT_SYMBOLS = {
    "gold": {"yfinance": "GC=F", "binance_futures": "PAXGUSDT"},
    "bitcoin": {"yfinance": "BTC-USD", "binance_futures": "BTCUSDT"},
}


@dataclass
class Config:
    symbols: dict = field(default_factory=lambda: dict(_DEFAULT_SYMBOLS))
    data_source: str = "yfinance"  # "yfinance" | "binance_futures"
    interval: str = "1h"
    lookback_period: str = "60d"
    binance_limit: int = 500
    indicators: IndicatorConfig = field(default_factory=IndicatorConfig)
    divergence: DivergenceConfig = field(default_factory=DivergenceConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)

    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        with open(path, "r") as f:
            raw = yaml.safe_load(f) or {}

        cfg = cls()
        cfg.symbols = raw.get("symbols", cfg.symbols)
        cfg.data_source = raw.get("data_source", cfg.data_source)
        cfg.interval = raw.get("interval", cfg.interval)
        cfg.lookback_period = raw.get("lookback_period", cfg.lookback_period)
        cfg.binance_limit = raw.get("binance_limit", cfg.binance_limit)

        ind = raw.get("indicators", {})
        cfg.indicators = IndicatorConfig(
            rsi_period=ind.get("rsi_period", 14),
            macd_fast=ind.get("macd_fast", 12),
            macd_slow=ind.get("macd_slow", 26),
            macd_signal=ind.get("macd_signal", 9),
            adx_period=ind.get("adx_period", 14),
            adx_trend_threshold=ind.get("adx_trend_threshold", 25.0),
        )

        div = raw.get("divergence", {})
        cfg.divergence = DivergenceConfig(
            pivot_left=div.get("pivot_left", 3),
            pivot_right=div.get("pivot_right", 3),
            max_pivot_lookback=div.get("max_pivot_lookback", 5),
        )

        sc = raw.get("scoring", {})
        cfg.scoring = ScoringConfig(min_score_to_alert=sc.get("min_score_to_alert", 2))

        tg = raw.get("telegram", {})
        cfg.telegram = TelegramConfig(
            enabled=tg.get("enabled", False),
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        )

        return cfg
