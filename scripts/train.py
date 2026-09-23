#!/usr/bin/env python3
"""Train the hybrid reversal-detection model from a historical CSV,
with hyperparameter search and decision-threshold tuning.

Usage:
    python scripts/train.py --csv data/raw/gold_h1.csv --asset gold \
        --min-pct 0.015 --horizon 10 --out models/gold_reversal.joblib
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reversal.backtest import average_lead_time, evaluate_predictions  # noqa: E402
from reversal.data import load_ohlc_csv  # noqa: E402
from reversal.features import build_training_set  # noqa: E402
from reversal.labeling import build_reversal_labels  # noqa: E402
from reversal.model import save_model, time_ordered_splits, train_model  # noqa: E402
from reversal.tuning import grid_search_hyperparams, predict_with_thresholds, tune_thresholds  # noqa: E402

PARAM_GRID = {"max_depth": [2, 3], "learning_rate": [0.05, 0.1]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, help="Path to historical OHLC(V) CSV")
    parser.add_argument("--asset", default="asset", help="Label for logging, e.g. gold or bitcoin")
    parser.add_argument("--min-pct", type=float, default=0.02,
                         help="Minimum swing retracement to confirm a pivot (e.g. 0.02 = 2%%)")
    parser.add_argument("--horizon", type=int, default=10,
                         help="Bars ahead within which a pivot counts as 'imminent'")
    parser.add_argument("--out", default="models/reversal_model.joblib", help="Output path for the trained model")
    parser.add_argument("--skip-tuning", action="store_true",
                         help="Skip hyperparameter search and use DEFAULT_PARAMS (faster, for quick checks)")
    args = parser.parse_args()

    print(f"[{args.asset}] loading {args.csv} ...")
    df = load_ohlc_csv(args.csv)
    print(f"[{args.asset}] {len(df)} bars loaded, range {df.index.min()} -> {df.index.max()}")

    labels = build_reversal_labels(df["close"], min_pct=args.min_pct, horizon=args.horizon)
    print(f"[{args.asset}] label distribution:\n{labels.value_counts().sort_index()}")

    X, y = build_training_set(df, labels)
    X_train, X_val, X_test, y_train, y_val, y_test = time_ordered_splits(X, y)
    print(f"[{args.asset}] train/val/test sizes: {len(X_train)}/{len(X_val)}/{len(X_test)}, {X.shape[1]} features")

    if args.skip_tuning:
        best_params = {}
    else:
        best_params, cv_score = grid_search_hyperparams(X_train, y_train, PARAM_GRID)
        print(f"[{args.asset}] best hyperparams: {best_params} (CV macro-F1 on reversal classes: {cv_score:.3f})")

    model = train_model(X_train, y_train, params=best_params)

    val_proba = model.predict_proba(X_val)
    thresholds = tune_thresholds(y_val.to_numpy(), val_proba, model.classes_)
    print(f"[{args.asset}] tuned thresholds (from validation set): {thresholds}")

    test_proba = model.predict_proba(X_test)
    default_pred = model.predict(X_test)
    tuned_pred = predict_with_thresholds(test_proba, model.classes_, thresholds)

    print(f"\n[{args.asset}] === held-out test: default argmax ===")
    print(evaluate_predictions(y_test, default_pred))
    print(f"\n[{args.asset}] === held-out test: tuned thresholds ===")
    print(evaluate_predictions(y_test, tuned_pred))

    y_test_reset = y_test.reset_index(drop=True)
    for cls, name in [(1, "bullish"), (2, "bearish")]:
        lead = average_lead_time(y_test_reset, tuned_pred, cls)
        if lead is not None:
            print(f"[{args.asset}] avg lead time before {name} pivot (tuned): {lead:.1f} bars")
        else:
            print(f"[{args.asset}] no {name} pivots correctly anticipated in test set (tuned)")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_model({"model": model, "thresholds": thresholds, "params": best_params}, str(out_path))
    print(f"[{args.asset}] model saved to {out_path}")


if __name__ == "__main__":
    main()
