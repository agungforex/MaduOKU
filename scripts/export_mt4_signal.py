#!/usr/bin/env python3
"""Export the latest reversal signal per timeframe into MT4's Common
Files folder, in the simple CSV format
mt4/MaduOKU_ReversalDashboard.mq4 reads:

    yyyy.mm.dd hh:mi,signal,prob_none,prob_bullish,prob_bearish

Run this on a schedule (e.g. right after your existing cronjob
refreshes data/raw/*.csv with the latest bars) so the MT4 dashboard
always shows a fresh signal.

Usage:
    python scripts/export_mt4_signal.py --symbol XAUUSD \
        --mt4-common-files "C:/Users/you/AppData/Roaming/MetaQuotes/Terminal/Common/Files"

Find your terminal's Common\\Files folder from MT4: File -> Open Data
Folder -> go up one level -> Common -> Files. It's shared by every MT4
terminal installed on the machine, so the same folder is used no
matter which terminal/chart the indicator is attached in.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from reversal.data import discover_higher_timeframes, load_ohlc_csv  # noqa: E402
from reversal.features import build_features  # noqa: E402
from reversal.model import load_model, predict_signals  # noqa: E402

TIMEFRAMES = [5, 15, 60, 240]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True, help="e.g. XAUUSD or BTCUSD (matches your CSV/model filenames)")
    parser.add_argument("--data-dir", default="data/raw", help="Folder with <SYMBOL><TF>.csv files")
    parser.add_argument("--models-dir", default="models", help="Folder with <SYMBOL><TF>_reversal.joblib files")
    parser.add_argument("--mt4-common-files", required=True,
                         help="Path to MT4's Common/Files folder (shared across all terminals on this machine)")
    parser.add_argument("--subfolder", default="MaduOKU_Signals", help="Subfolder name under Common/Files")
    args = parser.parse_args()

    out_dir = Path(args.mt4_common_files) / args.subfolder
    out_dir.mkdir(parents=True, exist_ok=True)

    for tf in TIMEFRAMES:
        csv_path = Path(args.data_dir) / f"{args.symbol}{tf}.csv"
        model_path = Path(args.models_dir) / f"{args.symbol}{tf}_reversal.joblib"
        if not csv_path.exists() or not model_path.exists():
            missing = csv_path if not csv_path.exists() else model_path
            print(f"[{args.symbol}{tf}] skipped (missing {missing})")
            continue

        df = load_ohlc_csv(str(csv_path))
        htf_frames = {
            label: load_ohlc_csv(htf_path)
            for label, htf_path in discover_higher_timeframes(str(csv_path))
        }

        feats = build_features(df, htf_frames=htf_frames).dropna()
        bundle = load_model(str(model_path))
        signals = predict_signals(bundle["model"], feats, thresholds=bundle.get("thresholds"))
        latest = signals.iloc[-1]
        ts = signals.index[-1]

        line = (
            f"{ts:%Y.%m.%d %H:%M},{latest['signal']},"
            f"{latest['prob_none']:.4f},{latest['prob_bullish_reversal']:.4f},{latest['prob_bearish_reversal']:.4f}\n"
        )
        out_file = out_dir / f"{args.symbol}{tf}.csv"
        out_file.write_text(line)
        print(f"[{args.symbol}{tf}] {line.strip()} -> {out_file}")


if __name__ == "__main__":
    main()
