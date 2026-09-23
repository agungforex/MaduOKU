# MaduOKU — Early Reversal Detection

Hybrid rule-based + machine learning pipeline to detect early price
reversals on Gold (XAU) and Bitcoin, from your own historical OHLC(V)
CSV files.

## How it works

1. **Labeling** (`src/reversal/labeling.py`): a zigzag algorithm finds
   confirmed swing highs/lows using a minimum percentage retracement
   (`--min-pct`). Each bar is labeled `1` (bullish reversal imminent),
   `2` (bearish reversal imminent) or `0` (none) if a confirmed pivot
   falls within the next `--horizon` bars.
2. **Features** (`src/reversal/indicators.py`, `features.py`): RSI,
   MACD, Bollinger Bands, ATR, Stochastic, volume z-score,
   RSI/price divergence, and candlestick patterns (engulfing, hammer,
   shooting star, doji) — the rule-based signals become numeric
   features.
3. **Model** (`src/reversal/model.py`): a `GradientBoostingClassifier`
   is trained on those features to predict the 3-class label. This is
   the "combination" approach: rule-based signals feed the ML decision
   layer instead of firing trade signals on their own.
4. **Backtest** (`src/reversal/backtest.py`): classification report,
   confusion matrix, and average lead time (how many bars before the
   actual pivot the model's signal first fired).

## Setup

```bash
pip install -r requirements.txt
```

## CSV format

Any CSV with a date/time column and OHLC(V) columns works — headers are
matched case-insensitively (`time`/`date`/`datetime`, `open`, `high`,
`low`, `close`, `volume`). Put your files in `data/raw/`.

## Train

```bash
python scripts/train.py \
  --csv data/raw/gold_h1.csv \
  --asset gold \
  --min-pct 0.015 \
  --horizon 10 \
  --out models/gold_reversal.joblib
```

Tune `--min-pct` per asset volatility (e.g. lower for gold, higher for
Bitcoin) and `--horizon` for how early you want the warning (in bars of
whatever timeframe your CSV uses).

## Predict on new data

```bash
python scripts/predict.py \
  --csv data/raw/gold_h1_latest.csv \
  --model models/gold_reversal.joblib \
  --tail 10
```

## Notes

- The train/test split is time-ordered (no shuffling) to avoid
  look-ahead leakage.
- Labels use future data by design (that's how supervised training
  works for this kind of task); features at each bar only use past
  data, so inference on new bars is leak-free.
- Start with a reasonably sized dataset (a few thousand bars) per
  asset/timeframe so both reversal classes have enough examples.
