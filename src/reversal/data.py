"""Load and normalize OHLC(V) CSV data for reversal detection."""
from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ["open", "high", "low", "close"]


def load_ohlc_csv(path: str, tz: str | None = None) -> pd.DataFrame:
    """Load a CSV with a datetime column plus OHLC(V) columns.

    Column names are matched case-insensitively against common variants
    (time/date/datetime, o/open, h/high, l/low, c/close, v/volume/vol).
    Returns a DataFrame indexed by datetime, sorted ascending, with
    lowercase columns: open, high, low, close, volume (volume may be NaN).
    """
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

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")
    if "datetime" not in df.columns:
        raise ValueError("CSV must have a date/time column")
    if "volume" not in df.columns:
        df["volume"] = float("nan")

    df["datetime"] = pd.to_datetime(df["datetime"], utc=False)
    if tz:
        df["datetime"] = df["datetime"].dt.tz_localize(tz, ambiguous="infer", nonexistent="shift_forward") \
            if df["datetime"].dt.tz is None else df["datetime"].dt.tz_convert(tz)

    df = df.set_index("datetime").sort_index()
    df = df[["open", "high", "low", "close", "volume"]].astype(float, errors="ignore")
    df = df[~df.index.duplicated(keep="last")]
    return df
