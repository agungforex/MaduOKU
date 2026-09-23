from __future__ import annotations

import argparse

import yaml

from .backtest.sweep import grid_search
from .config import Config
from .main import fetch_data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MaduOKU — parameter sweep over the backtest engine")
    parser.add_argument("--config", default="config.example.yaml", help="Path to base YAML config")
    parser.add_argument("--grid", default="sweep.example.yaml", help="Path to YAML file defining the param grid")
    parser.add_argument("--symbol", required=True, help="Symbol name from config.symbols, e.g. gold or bitcoin")
    parser.add_argument("--forward-bars", type=int, default=5)
    parser.add_argument("--step", type=int, default=2, help="Stride between evaluated bars (speed vs. coverage)")
    parser.add_argument("--min-signals", type=int, default=5, help="Drop combos with fewer than this many trades")
    parser.add_argument("--top", type=int, default=10, help="How many top combos to print")
    parser.add_argument("--out", help="Optional path to save the full ranked results as CSV")
    args = parser.parse_args(argv)

    cfg = Config.from_yaml(args.config)
    df = fetch_data(args.symbol, cfg)

    with open(args.grid, "r") as f:
        grid = (yaml.safe_load(f) or {}).get("grid", {})

    if not grid:
        print("Grid file has no 'grid:' section with parameters to sweep.")
        return 1

    results = grid_search(
        df, cfg, grid, forward_bars=args.forward_bars, step=args.step, min_signals=args.min_signals
    )

    if results.empty:
        print("No parameter combination produced enough signals (try lowering --min-signals).")
        return 0

    print(f"{args.symbol.upper()} — {len(results)} combinations met min_signals={args.min_signals}\n")
    print(results.head(args.top).to_string(index=False))

    if args.out:
        results.to_csv(args.out, index=False)
        print(f"\nFull results saved to {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
