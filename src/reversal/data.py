"""Load and normalize OHLC(V) CSV data for reversal detection."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ["open", "high", "low", "close"]

# Matches filenames like BTCUSD5, XAUUSD240 -> ("BTCUSD", "5")
_SYMBOL_TF_RE = re.compile(r"^([A-Za-z]+)(\d+)$")


def discover_higher_timeframes(csv_path: str, max_higher: int = 2) -> list[tuple[str, str]]:
    """Given a path like data/raw/BTCUSD15.csv, find sibling CSVs for
    the same symbol at larger timeframes (e.g. BTCUSD60.csv,
    BTCUSD240.csv) by filename convention `<SYMBOL><MINUTES>.csv` in
    the same directory. Returns up to `max_higher` (label, path) pairs,
    nearest timeframe first. Returns [] if the filename doesn't match
    the convention or no larger-timeframe sibling exists."""
    path = Path(csv_path)
    m = _SYMBOL_TF_RE.match(path.stem)
    if not m:
        return []
    symbol, tf_str = m.groups()
    tf = int(tf_str)

    candidates = []
    for sibling in path.parent.glob(f"{symbol}*.csv"):
        m2 = _SYMBOL_TF_RE.match(sibling.stem)
        if not m2 or m2.group(1) != symbol:
            continue
        tf2 = int(m2.group(2))
        if tf2 > tf:
            candidates.append((tf2, sibling))
    candidates.sort(key=lambda x: x[0])
    return [(f"htf{tf2}", str(p)) for tf2, p in candidates[:max_higher]]

# MetaTrader history-center exports have no header row: two separate
# date/time columns, then OHLC, then volume (optionally tick volume
# followed by real volume/spread, which we ignore).
_MT_COLUMNS = {
    6: ["date", "time", "open", "high", "low", "close"],
    7: ["date", "time", "open", "high", "low", "close", "volume"],
    8: ["date", "time", "open", "high", "low", "close", "volume", "spread"],
}


def _looks_headerless(first_row: list[str]) -> bool:
    """True if the first row of the file is already data (MT export)
    rather than column names, i.e. its first cell parses as a date."""
    try:
        pd.to_datetime(first_row[0], format="%Y.%m.%d")
        return True
    except (ValueError, TypeError):
        return False


def load_ohlc_csv(path: str, tz: str | None = None) -> pd.DataFrame:
    """Load a CSV with a datetime column plus OHLC(V) columns.

    Supports two formats:
    - A header row with column names matched case-insensitively against
      common variants (time/date/datetime, o/open, h/high, l/low,
      c/close, v/volume/vol).
    - Headerless MetaTrader exports: `date,time,open,high,low,close[,volume[,spread]]`
      with date as `YYYY.MM.DD` and time as `HH:MM`.

    Returns a DataFrame indexed by datetime, sorted ascending, with
    lowercase columns: open, high, low, close, volume (volume may be NaN).
    """
    with open(path) as fh:
        first_line = fh.readline().strip()
    first_row = first_line.split(",")

    if _looks_headerless(first_row):
        n = len(first_row)
        if n not in _MT_COLUMNS:
            raise ValueError(f"Unrecognized headerless CSV with {n} columns: {path}")
        df = pd.read_csv(path, header=None, names=_MT_COLUMNS[n])
        df["datetime"] = pd.to_datetime(
            df["date"] + " " + df["time"], format="%Y.%m.%d %H:%M"
        )
        df = df.drop(columns=["date", "time"])
        return _finalize(df, tz)

    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    rename_map = {}
    for col in df.columns:
        if col in ("time", "date", "datetime", "timestamp"):
            rename_map[col] = "datetime"
        elif col in ("o", "open"):
            rename_map[col] = "open"
        elif col in ("h", "high"):
            rename_map[col] = "high"
        elif col in ("l", "low"):
            rename_map[col] = "low"
        elif col in ("c", "close", "adj close", "adj_close"):
            rename_map[col] = "close"
        elif col in ("v", "vol", "volume"):
            rename_map[col] = "volume"
    df = df.rename(columns=rename_map)

    if "datetime" not in df.columns:
        raise ValueError("CSV must have a date/time column")
    df["datetime"] = pd.to_datetime(df["datetime"], utc=False)
    return _finalize(df, tz)


def _finalize(df: pd.DataFrame, tz: str | None) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")
    if "volume" not in df.columns:
        df["volume"] = float("nan")

    if tz:
        df["datetime"] = df["datetime"].dt.tz_localize(tz, ambiguous="infer", nonexistent="shift_forward") \
            if df["datetime"].dt.tz is None else df["datetime"].dt.tz_convert(tz)

    df = df.set_index("datetime").sort_index()
    df = df[["open", "high", "low", "close", "volume"]].astype(float, errors="ignore")
    df = df[~df.index.duplicated(keep="last")]
    return df
