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

## MT4 dashboard

Two options, same on-chart look (a small panel with signals for
M5/M15/H1/H4), different trade-offs:

- **`MaduOKU_ReversalDashboard_Standalone.mq4`** — pure MQL4, one file,
  no setup beyond compiling and dragging it onto a chart. Computes a
  rule-based reversal score natively from RSI, MACD, Bollinger Bands,
  RSI/price divergence and candlestick patterns. Doesn't use the
  trained ML models, so it's less accurate than the tuned pipeline,
  but has zero moving parts (no Python, no Task Scheduler, no shared
  files). Good default if you just want something simple that works.
- **`MaduOKU_ReversalDashboard.mq4`** — reads signals produced by the
  trained ML models (with hyperparameter + threshold tuning and
  multi-timeframe context), via `scripts/export_mt4_signal.py` and
  Windows Task Scheduler (see below). More accurate, more setup.

### Standalone (recommended for simplicity)

Copy `mt4/MaduOKU_ReversalDashboard_Standalone.mq4` into your
terminal's `MQL4/Indicators/` folder (MT4: File -> Open Data Folder),
compile it in MetaEditor, and attach it to any chart. That's it — no
Python, no cronjob. `InpMinScore` controls how many aligned signals
(RSI, MACD cross, Bollinger touch, divergence, candlestick pattern)
are required before it flags a reversal; raise it for fewer, higher-
conviction alerts.

### ML-backed (ADVANCED — via Python bridge)

`mt4/MaduOKU_ReversalDashboard.mq4` is a chart indicator that shows the
latest signal for a symbol across all 4 trained timeframes (M5/M15/H1/H4)
at once, in a small on-chart panel — attach it to any single chart and
it still shows all four. MT4 can't run Python directly, so the two
sides are bridged through a small shared file:

1. **Install the indicator**: copy `mt4/MaduOKU_ReversalDashboard.mq4`
   into your terminal's `MQL4/Indicators/` folder (MT4: File -> Open
   Data Folder), then compile it in MetaEditor and attach it to a
   chart. If your broker's symbol name differs from the one used in
   training (e.g. `XAUUSD+` instead of `XAUUSD`), set the
   `InpSymbolOverride` input.

2. **Run the exporter on a schedule** (e.g. right after your existing
   cronjob refreshes `data/raw/*.csv` with fresh bars):

   ```bash
   python scripts/export_mt4_signal.py \
     --symbol XAUUSD \
     --mt4-common-files "C:/Users/you/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
   ```

   This writes one small file per timeframe (e.g.
   `MaduOKU_Signals/XAUUSD15.csv`) into MT4's shared *Common\Files*
   folder (find it via File -> Open Data Folder -> go up one level ->
   Common -> Files — it's shared across every terminal on the
   machine). The indicator polls those files every `InpRefreshSeconds`
   and repaints the dashboard.

   **On Windows, automate this with Task Scheduler** using the files
   in `windows/`:
   - Edit the three paths at the top of `windows/run_mt4_export.bat`
     (project folder, Python executable, MT4 Common\Files folder).
   - Register it to run every few minutes:
     ```powershell
     cd C:\MaduOKU\windows
     powershell -ExecutionPolicy Bypass -File .\register_task.ps1
     ```
   - This creates a task named `MaduOKU_MT4_Export` (visible in Task
     Scheduler) that reruns the exporter on the interval set in
     `register_task.ps1` (`$IntervalMinutes`, default 5). Logs go to
     `logs\mt4_export.log` inside the project folder — check there
     first if the dashboard shows `[STALE]`.
   - If you add more symbols later, add another
     `export_mt4_signal.py --symbol ...` line to `run_mt4_export.bat`.

3. The dashboard flags a row **[STALE]** if its file hasn't been
   refreshed recently (more than 3x that timeframe's bar length) —
   a sign the exporter/cronjob has stopped running, not that the model
   is broken.

## Notes

- The train/test split is time-ordered (no shuffling) to avoid
  look-ahead leakage.
- Labels use future data by design (that's how supervised training
  works for this kind of task); features at each bar only use past
  data, so inference on new bars is leak-free.
- Start with a reasonably sized dataset (a few thousand bars) per
  asset/timeframe so both reversal classes have enough examples.
