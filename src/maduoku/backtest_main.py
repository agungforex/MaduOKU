from __future__ import annotations

import argparse

from .backtest.engine import run_backtest, summarize
from .config import Config
from .main import fetch_data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MaduOKU — backtest the reversal scanner against history")
    parser.add_argument("--config", default="config.example.yaml", help="Path to YAML config")
    parser.add_argument("--symbol", required=True, help="Symbol name from config.symbols, e.g. gold or bitcoin")
    parser.add_argument("--forward-bars", type=int, default=5, help="Bars ahead to measure return")
    parser.add_argument("--step", type=int, default=1, help="Stride between evaluated bars (speed vs. coverage)")
    args = parser.parse_args(argv)

    cfg = Config.from_yaml(args.config)
    df = fetch_data(args.symbol, cfg)

    trades = run_backtest(df, cfg, forward_bars=args.forward_bars, step=args.step)
    summary = summarize(trades)

    print(f"{args.symbol.upper()} — {len(df)} candles, {summary.total_signals} signals fired")
    print(f"Overall win rate: {summary.win_rate:.1%}, avg return per signal: {summary.avg_return:.3%}")
    if not summary.by_direction.empty:
        print(summary.by_direction.to_string())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
