#!/usr/bin/env python3
"""Train the hybrid reversal-detection model from a historical CSV.

Usage:
    python scripts/train.py --csv data/raw/gold_h1.csv --asset gold \
        --min-pct 0.015 --horizon 10 --out models/gold_reversal.joblib
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reversal.backtest import average_lead_time, evaluate  # noqa: E402
from reversal.data import load_ohlc_csv  # noqa: E402
from reversal.features import build_training_set  # noqa: E402
from reversal.labeling import build_reversal_labels  # noqa: E402
from reversal.model import save_model, train_model  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, help="Path to historical OHLC(V) CSV")
    parser.add_argument("--asset", default="asset", help="Label for logging, e.g. gold or bitcoin")
    parser.add_argument("--min-pct", type=float, default=0.02,
                         help="Minimum swing retracement to confirm a pivot (e.g. 0.02 = 2%%)")
    parser.add_argument("--horizon", type=int, default=10,
                         help="Bars ahead within which a pivot counts as 'imminent'")
    parser.add_argument("--out", default="models/reversal_model.joblib", help="Output path for the trained model")
    args = parser.parse_args()

    print(f"[{args.asset}] loading {args.csv} ...")
    df = load_ohlc_csv(args.csv)
    print(f"[{args.asset}] {len(df)} bars loaded, range {df.index.min()} -> {df.index.max()}")

    labels = build_reversal_labels(df["close"], min_pct=args.min_pct, horizon=args.horizon)
    print(f"[{args.asset}] label distribution:\n{labels.value_counts().sort_index()}")

    X, y = build_training_set(df, labels)
    print(f"[{args.asset}] training on {len(X)} rows, {X.shape[1]} features")

    model, (X_train, X_test, y_train, y_test) = train_model(X, y)
    print(f"[{args.asset}] evaluation on held-out (most recent) 20% of data:\n")
    print(evaluate(model, X_test, y_test))

    y_pred_test = model.predict(X_test)
    for cls, name in [(1, "bullish"), (2, "bearish")]:
        lead = average_lead_time(y_test.reset_index(drop=True), y_pred_test, cls)
        if lead is not None:
            print(f"[{args.asset}] avg lead time before {name} pivot: {lead:.1f} bars")
        else:
            print(f"[{args.asset}] no {name} pivots correctly anticipated in test set")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_model(model, str(out_path))
    print(f"[{args.asset}] model saved to {out_path}")


if __name__ == "__main__":
    main()
