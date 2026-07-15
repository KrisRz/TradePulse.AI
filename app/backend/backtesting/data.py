"""Market data loading for backtests.

Handles both CSV layouts present in the repo:

1. Raw Binance klines (no header), e.g.
   ``data/ml/historical/raw_files/BTCUSDT-1m-2021-05.csv``
   columns: open_time_ms, open, high, low, close, volume, close_time_ms, ...

2. Header CSV with human timestamps, e.g.
   ``app/data/ml/historical/binance_fresh/BTCUSDT_1m_3months.csv``
   columns: timestamp, open, high, low, close, volume, ...

Everything is normalised to a DataFrame indexed by a UTC DatetimeIndex with
float columns: open, high, low, close, volume.
"""

from __future__ import annotations

import glob
from pathlib import Path
from typing import Iterable

import pandas as pd

OHLCV = ["open", "high", "low", "close", "volume"]

_RAW_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]

# Timeframe -> pandas resample rule
TIMEFRAMES = {
    "1m": "1min", "3m": "3min", "5m": "5min", "15m": "15min",
    "30m": "30min", "1h": "1h", "2h": "2h", "4h": "4h", "1d": "1D",
}


def _looks_like_header(first_line: str) -> bool:
    return "timestamp" in first_line.lower() or "open" in first_line.lower()


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load a single CSV of either supported layout into an OHLCV frame."""
    path = Path(path)
    with open(path, "r") as fh:
        first_line = fh.readline()

    if _looks_like_header(first_line):
        df = pd.read_csv(path)
        df = df.rename(columns={c: c.lower() for c in df.columns})
        ts = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index(ts)
    else:
        df = pd.read_csv(path, header=None, names=_RAW_COLUMNS)
        # Binance open_time is epoch milliseconds
        ts = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df = df.set_index(ts)

    df = df[OHLCV].astype(float)
    df.index.name = "time"
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df


def load_many(paths: Iterable[str | Path]) -> pd.DataFrame:
    """Load and concatenate several CSVs (e.g. many monthly files)."""
    frames = [load_csv(p) for p in paths]
    if not frames:
        raise ValueError("No data files matched.")
    df = pd.concat(frames)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df


def load_glob(pattern: str) -> pd.DataFrame:
    """Load every file matching a glob pattern, sorted by name."""
    paths = sorted(glob.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No files match: {pattern}")
    return load_many(paths)


def resample(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample 1m OHLCV up to a higher timeframe (e.g. '15m', '1h').

    Uses left-closed, left-labelled bins so a bar is stamped with its OPEN
    time — consistent with how the raw source stamps bars.
    """
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"Unknown timeframe {timeframe!r}. Options: {list(TIMEFRAMES)}")
    rule = TIMEFRAMES[timeframe]
    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    out = df.resample(rule, label="left", closed="left").agg(agg)
    return out.dropna(subset=["open", "high", "low", "close"])


def slice_dates(
    df: pd.DataFrame,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Inclusive date slice by ISO strings (e.g. '2021-01-01')."""
    if start is not None:
        df = df[df.index >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        df = df[df.index <= pd.Timestamp(end, tz="UTC")]
    return df
