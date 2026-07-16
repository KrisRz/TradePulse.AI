"""Download historical OHLCV from Binance — regenerate backtest data on demand.

Historical price data is NOT committed to git (it bloats the repo and is freely
re-downloadable). This tool reconstructs it from Binance's public API into the
same CSV layout ``data.load_csv`` reads, so a fresh clone can recreate exactly
what a backtest needs.

Example:
    python -m app.backend.backtesting.download \
        --symbol BTCUSDT --interval 1h --start 2020-01-01 --end 2024-12-31 \
        --out data/ml/historical/BTCUSDT_1h_2020_2024.csv
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
import requests

_BASE = "https://api.binance.com/api/v3/klines"
_COLS = ["open", "high", "low", "close", "volume"]
_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000,
       "4h": 14_400_000, "1d": 86_400_000}


def fetch_history(symbol: str, interval: str, start: str, end: str | None = None,
                  pause: float = 0.25) -> pd.DataFrame:
    """Paginate Binance klines between ``start`` and ``end`` (ISO dates)."""
    if interval not in _MS:
        raise ValueError(f"Unsupported interval {interval!r}")
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms = int(pd.Timestamp(end or pd.Timestamp.utcnow(), tz="UTC").timestamp() * 1000) \
        if end else int(time.time() * 1000)

    frames, cursor = [], start_ms
    while cursor < end_ms:
        resp = requests.get(_BASE, params={
            "symbol": symbol, "interval": interval,
            "startTime": cursor, "endTime": end_ms, "limit": 1000,
        }, timeout=15)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break
        frames.append(rows)
        cursor = rows[-1][0] + _MS[interval]   # advance past last open_time
        if len(rows) < 1000:
            break
        time.sleep(pause)   # be gentle with the public API

    flat = [r for batch in frames for r in batch]
    if not flat:
        raise RuntimeError("No klines returned")
    df = pd.DataFrame(flat, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore",
    ])
    idx = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.set_index(idx)[_COLS].astype(float)
    df.index.name = "timestamp"
    return df[~df.index.duplicated(keep="first")].sort_index()


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Download Binance OHLCV history to CSV.")
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--interval", default="1h", choices=list(_MS))
    p.add_argument("--start", required=True, help="ISO date, e.g. 2020-01-01")
    p.add_argument("--end", default=None, help="ISO date (default: now)")
    p.add_argument("--out", required=True, help="Output CSV path")
    args = p.parse_args(argv)

    df = fetch_history(args.symbol, args.interval, args.start, args.end)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out)
    print(f"Saved {len(df):,} bars to {out} ({df.index[0]} -> {df.index[-1]})")


if __name__ == "__main__":
    main()
