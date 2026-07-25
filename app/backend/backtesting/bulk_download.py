"""Bulk historical OHLCV from Binance public data dumps (data.binance.vision).

For multi-year 1h/1m history the live REST API (``download.py``) is slow and
rate-limited; Binance publishes the same klines as static monthly/daily zip
archives (repo: github.com/binance/binance-public-data). This tool downloads
those archives and writes ONE CSV in the exact layout ``data.load_csv`` and
``download.py`` produce (header + ``timestamp`` index), so backtests read it
unchanged.

Format traps handled here:
- files before 2025-01-01 stamp ``open_time`` in milliseconds, later ones in
  microseconds (detected per-row by magnitude);
- newer archives may include a header row, older ones never do;
- months before the symbol listed (or gaps in the archive) return HTTP 404 —
  skipped, but a fully empty result is an error;
- each zip has a published SHA-256 (``.CHECKSUM``) which is verified;
- after the 2018-02-08/09 maintenance the kline grid restarted mid-interval
  (open times at :28:14.789 for ~43 hourly bars) — bars are floored onto the
  interval grid, exactly where ``data.resample`` would bucket them anyway.

Example (full 1h history up to the M5 holdout line):
    python -m app.backend.backtesting.bulk_download \
        --symbol BTCUSDT --interval 1h --start 2017-08 --end 2026-07-16 \
        --out data/ml/historical/BTCUSDT_1h.csv
"""

from __future__ import annotations

import argparse
import hashlib
import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

_BASE = "https://data.binance.vision/data/spot"
_COLS = ["open", "high", "low", "close", "volume"]
_RAW_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]
# open_time magnitude thresholds: seconds ~1e9, ms ~1e12, µs ~1e15.
_US_THRESHOLD = 10 ** 14
_SPACING = {
    "1m": "1min", "3m": "3min", "5m": "5min", "15m": "15min", "30m": "30min",
    "1h": "1h", "2h": "2h", "4h": "4h", "1d": "1D",
}


def _fetch_zip(url: str, timeout: float = 30.0) -> bytes | None:
    """Download one archive; None on 404 (month/day not published)."""
    resp = requests.get(url, timeout=timeout)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.content


def _verify_checksum(url: str, payload: bytes, timeout: float = 30.0) -> None:
    """Verify payload against the published .CHECKSUM file (best effort)."""
    resp = requests.get(url + ".CHECKSUM", timeout=timeout)
    if resp.status_code == 404:
        return  # a few very old archives have no checksum file
    resp.raise_for_status()
    expected = resp.text.split()[0].strip().lower()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise RuntimeError(f"Checksum mismatch for {url}")


def _parse_archive(payload: bytes, interval: str) -> pd.DataFrame:
    """Read the single CSV inside a klines zip into an OHLCV frame."""
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        with zf.open(zf.namelist()[0]) as fh:
            first = fh.readline()
            fh.seek(0)
            skip = 1 if first.split(b",")[0].strip() == b"open_time" else 0
            df = pd.read_csv(fh, header=None, names=_RAW_COLUMNS, skiprows=skip)
    unit = df["open_time"].map(lambda t: "us" if t > _US_THRESHOLD else "ms")
    ts = pd.to_datetime(
        df["open_time"].where(unit == "ms", df["open_time"] // 1000),
        unit="ms", utc=True)
    # Snap post-maintenance mid-interval open times onto the interval grid.
    floored = ts.dt.floor(_SPACING[interval])
    off_grid = int((floored != ts).sum())
    if off_grid:
        print(f"    note: {off_grid} bar(s) floored onto the {interval} grid")
    df = df.set_index(floored)[_COLS].astype(float)
    df.index.name = "timestamp"
    return df


def _month_start(ts: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(ts.year, ts.month, 1, tz="UTC")


def fetch_bulk(symbol: str, interval: str, start: str, end: str,
               verbose: bool = True) -> pd.DataFrame:
    """Assemble [start, end] (inclusive, UTC dates) from monthly + daily zips.

    Monthly archives cover complete months; the final partial month (if any)
    is filled from daily archives.
    """
    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC")
    if start_ts >= end_ts:
        raise ValueError("start must be before end")
    # Complete months come from monthly archives …
    last_full_month_end = _month_start(end_ts) - pd.Timedelta(seconds=1)
    frames: list[pd.DataFrame] = []
    for month in pd.date_range(_month_start(start_ts),
                               min(end_ts, last_full_month_end), freq="MS"):
        tag = f"{symbol}-{interval}-{month:%Y-%m}"
        url = f"{_BASE}/monthly/klines/{symbol}/{interval}/{tag}.zip"
        payload = _fetch_zip(url)
        if payload is None:
            if verbose:
                print(f"  {tag}: not published (404), skipped")
            continue
        _verify_checksum(url, payload)
        frames.append(_parse_archive(payload, interval))
        if verbose:
            print(f"  {tag}: {len(frames[-1]):,} bars")
    # … the trailing partial month from daily archives.
    for day in pd.date_range(_month_start(end_ts), end_ts, freq="D"):
        tag = f"{symbol}-{interval}-{day:%Y-%m-%d}"
        url = f"{_BASE}/daily/klines/{symbol}/{interval}/{tag}.zip"
        payload = _fetch_zip(url)
        if payload is None:
            if verbose:
                print(f"  {tag}: not published (404), skipped")
            continue
        _verify_checksum(url, payload)
        frames.append(_parse_archive(payload, interval))
    if not frames:
        raise RuntimeError(f"No archives found for {symbol} {interval} {start}..{end}")

    df = pd.concat(frames)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    # Inclusive end DATE: keep every bar opening before the following midnight.
    cutoff = end_ts.normalize() + pd.Timedelta(days=1)
    return df[(df.index >= start_ts) & (df.index < cutoff)]


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        description="Bulk-download Binance OHLCV history (data.binance.vision) to CSV.")
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--interval", default="1h",
                   choices=["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"])
    p.add_argument("--start", required=True, help="ISO date or month, e.g. 2017-08")
    p.add_argument("--end", required=True, help="ISO date (inclusive), e.g. 2026-07-16")
    p.add_argument("--out", required=True, help="Output CSV path")
    args = p.parse_args(argv)

    df = fetch_bulk(args.symbol, args.interval, args.start, args.end)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out)
    print(f"Saved {len(df):,} bars to {out} ({df.index[0]} -> {df.index[-1]})")


if __name__ == "__main__":
    main()
