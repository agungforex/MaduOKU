#!/usr/bin/env python3
"""Run a trained reversal model on new/recent OHLC data and print the
latest signal plus recent history.

Usage:
    python scripts/predict.py --csv data/raw/gold_h1.csv --model models/gold_reversal.joblib --tail 10
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reversal.data import discover_higher_timeframes, load_ohlc_csv  # noqa: E402
from reversal.features import build_features  # noqa: E402
from reversal.model import load_model, predict_signals  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, help="Path to OHLC(V) CSV to score")
    parser.add_argument("--model", required=True, help="Path to a trained model .joblib file")
    parser.add_argument("--tail", type=int, default=10, help="Number of most recent rows to print")
    args = parser.parse_args()

    df = load_ohlc_csv(args.csv)
    bundle = load_model(args.model)
    model = bundle["model"] if isinstance(bundle, dict) else bundle
    thresholds = bundle.get("thresholds") if isinstance(bundle, dict) else None
    expected_htf = bundle.get("htf_labels", []) if isinstance(bundle, dict) else []

    htf_frames = {}
    for label, htf_path in discover_higher_timeframes(args.csv):
        htf_frames[label] = load_ohlc_csv(htf_path)
    missing = set(expected_htf) - set(htf_frames)
    if missing:
        raise ValueError(
            f"Model was trained with higher-timeframe context {sorted(missing)} "
            f"but the matching sibling CSV(s) weren't found next to {args.csv}"
        )

    feats = build_features(df, htf_frames=htf_frames).dropna()
    signals = predict_signals(model, feats, thresholds=thresholds)
    result = df.loc[signals.index, ["close"]].join(signals)

    print(result.tail(args.tail).to_string())
    latest = result.iloc[-1]
    print(f"\nLatest bar ({result.index[-1]}): signal = {latest['signal']}")


if __name__ == "__main__":
    main()
