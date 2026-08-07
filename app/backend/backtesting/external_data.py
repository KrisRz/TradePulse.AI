"""Bulk download of NON-price research data: funding, OI metrics, Coin Metrics.

Why these three (evidence ranking in docs/RESEARCH_ULEPSZEN_2026-08-07.md):
funding rate and open-interest metrics are the best-evidenced free features for
a future meta-labeler, and both are IMMUTABLE once published (settled values,
never revised) — point-in-time by construction. The Coin Metrics community CSV
(MVRV-Z, SOPR, active addresses) carries a small revision risk, which is
exactly why it is downloaded as a dated SNAPSHOT: freezing a copy today
removes any chance of look-ahead entering a backtest through silent upstream
revisions later.

Sources (all free, no API key):
- funding:  data.binance.vision futures/um/monthly/fundingRate/<SYMBOL>/
            header ``calc_time,funding_interval_hours,last_funding_rate``,
            calc_time in ms. Published from 2020-01 (perp launched 2019-09;
            the API has the earlier months, the archive does not).
- metrics:  data.binance.vision futures/um/daily/metrics/<SYMBOL>/
            5-minute rows, header with ``create_time`` as a naive UTC string,
            published from 2020-09-01. The REST endpoint keeps only 30 days —
            these archives are the ONLY free history. Rows can be duplicated
            inside one file (observed on 2020-09-01) — deduplicated here.
- coinmetrics: github.com/coinmetrics/data community CSV (btc.csv, daily,
            from genesis, CC-licensed).

Usage:
    python -m app.backend.backtesting.external_data --dataset funding \
        --symbol BTCUSDT --start 2020-01 --end 2026-08-06 \
        --out data/ml/external/BTCUSDT_funding.csv
    python -m app.backend.backtesting.external_data --dataset metrics \
        --symbol BTCUSDT --start 2020-09-01 --end 2026-08-06 \
        --out data/ml/external/BTCUSDT_metrics.csv
    python -m app.backend.backtesting.external_data --dataset coinmetrics \
        --out data/ml/external/coinmetrics_btc_snapshot_2026-08-07.csv
"""

from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

from .bulk_download import _fetch_zip, _month_start, _verify_checksum

_FUTURES_BASE = "https://data.binance.vision/data/futures/um"
_COINMETRICS_URL = ("https://raw.githubusercontent.com/coinmetrics/data/"
                    "master/csv/{asset}.csv")

_FUNDING_COLUMNS = ["calc_time", "funding_interval_hours", "last_funding_rate"]
_METRICS_COLUMNS = [
    "create_time", "symbol", "sum_open_interest", "sum_open_interest_value",
    "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio",
    "count_long_short_ratio", "sum_taker_long_short_vol_ratio",
]
# calc_time magnitude thresholds, same convention as bulk_download.
_US_THRESHOLD = 10 ** 14


def _read_zip_csv(payload: bytes, expected_first_col: str,
                  names: list[str]) -> pd.DataFrame:
    """The single CSV inside an archive, with or without its header row."""
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        with zf.open(zf.namelist()[0]) as fh:
            first = fh.readline()
            fh.seek(0)
            skip = 1 if first.split(b",")[0].strip() == expected_first_col.encode() else 0
            return pd.read_csv(fh, header=None, names=names, skiprows=skip)


def parse_funding_archive(payload: bytes) -> pd.DataFrame:
    """One monthly funding zip -> frame indexed by UTC settlement time."""
    df = _read_zip_csv(payload, "calc_time", _FUNDING_COLUMNS)
    raw = df["calc_time"].astype("int64")
    ts = pd.to_datetime(raw.where(raw < _US_THRESHOLD, raw // 1000),
                        unit="ms", utc=True)
    # .to_numpy(): building a frame from Series with a NEW index would align
    # on the old integer index and silently produce all-NaN columns.
    out = pd.DataFrame({
        "funding_rate": df["last_funding_rate"].astype(float).to_numpy(),
        "funding_interval_hours": df["funding_interval_hours"].astype(int).to_numpy(),
    }, index=pd.DatetimeIndex(ts, name="timestamp"))
    return out


def parse_metrics_archive(payload: bytes) -> pd.DataFrame:
    """One daily metrics zip -> 5-minute frame indexed by UTC time.

    Duplicated rows (identical timestamp) are collapsed to the first — the
    2020-09-01 archive ships every row twice.
    """
    df = _read_zip_csv(payload, "create_time", _METRICS_COLUMNS)
    ts = pd.to_datetime(df["create_time"], utc=True, format="mixed")
    df = df.drop(columns=["create_time", "symbol"]).astype(float)
    df.index = ts
    df.index.name = "timestamp"
    return df[~df.index.duplicated(keep="first")]


def fetch_funding(symbol: str, start: str, end: str,
                  verbose: bool = True) -> pd.DataFrame:
    """Monthly funding archives covering [start, end] (UTC dates, inclusive)."""
    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC")
    if start_ts >= end_ts:
        raise ValueError("start must be before end")
    frames: list[pd.DataFrame] = []
    for month in pd.date_range(_month_start(start_ts), _month_start(end_ts),
                               freq="MS"):
        tag = f"{symbol}-fundingRate-{month:%Y-%m}"
        url = f"{_FUTURES_BASE}/monthly/fundingRate/{symbol}/{tag}.zip"
        payload = _fetch_zip(url)
        if payload is None:
            if verbose:
                print(f"  {tag}: not published (404), skipped")
            continue
        _verify_checksum(url, payload)
        frames.append(parse_funding_archive(payload))
        if verbose:
            print(f"  {tag}: {len(frames[-1]):,} settlements")
    if not frames:
        raise RuntimeError(f"No funding archives for {symbol} {start}..{end}")
    df = pd.concat(frames)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    cutoff = end_ts.normalize() + pd.Timedelta(days=1)
    return df[(df.index >= start_ts) & (df.index < cutoff)]


def fetch_metrics(symbol: str, start: str, end: str,
                  verbose: bool = True) -> pd.DataFrame:
    """Daily metrics archives (5-min OI & ratios) — daily zips only exist."""
    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC")
    if start_ts >= end_ts:
        raise ValueError("start must be before end")
    frames: list[pd.DataFrame] = []
    missing = 0
    for day in pd.date_range(start_ts.normalize(), end_ts.normalize(), freq="D"):
        tag = f"{symbol}-metrics-{day:%Y-%m-%d}"
        url = f"{_FUTURES_BASE}/daily/metrics/{symbol}/{tag}.zip"
        payload = _fetch_zip(url)
        if payload is None:
            missing += 1
            if verbose:
                print(f"  {tag}: not published (404), skipped")
            continue
        _verify_checksum(url, payload)
        frames.append(parse_metrics_archive(payload))
        if verbose and len(frames) % 200 == 0:
            print(f"  ... {len(frames)} day(s) downloaded (up to {tag})")
    if not frames:
        raise RuntimeError(f"No metrics archives for {symbol} {start}..{end}")
    if verbose:
        print(f"  {len(frames)} day(s) downloaded, {missing} missing")
    df = pd.concat(frames)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df


def fetch_coinmetrics(asset: str = "btc", timeout: float = 120.0) -> pd.DataFrame:
    """The full Coin Metrics community series for one asset, as published TODAY.

    Store the result as a dated snapshot and never overwrite it: the value of
    this download is precisely that it cannot be revised after the fact.
    """
    url = _COINMETRICS_URL.format(asset=asset)
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    if "time" not in df.columns:
        raise RuntimeError(f"Unexpected Coin Metrics layout: {list(df.columns)[:8]}")
    df["time"] = pd.to_datetime(df["time"], utc=True, format="mixed")
    return df.set_index("time").sort_index()


def _summarize(df: pd.DataFrame, label: str) -> None:
    print(f"{label}: {len(df):,} rows, {df.index[0]} -> {df.index[-1]}, "
          f"{df.index.duplicated().sum()} duplicate timestamps")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        description="Bulk-download non-price research data (funding / OI metrics / Coin Metrics).")
    p.add_argument("--dataset", required=True,
                   choices=["funding", "metrics", "coinmetrics"])
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--asset", default="btc", help="coinmetrics asset id")
    p.add_argument("--start", help="ISO date or month (funding/metrics)")
    p.add_argument("--end", help="ISO date, inclusive (funding/metrics)")
    p.add_argument("--out", required=True, help="Output CSV path")
    args = p.parse_args(argv)

    if args.dataset == "coinmetrics":
        df = fetch_coinmetrics(args.asset)
    else:
        if not args.start or not args.end:
            p.error(f"--dataset {args.dataset} requires --start and --end")
        fetcher = fetch_funding if args.dataset == "funding" else fetch_metrics
        df = fetcher(args.symbol, args.start, args.end)

    out = Path(args.out)
    if args.dataset == "coinmetrics" and out.exists():
        raise SystemExit(f"{out} already exists — snapshots are immutable, "
                         f"pick a new dated filename")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out)
    _summarize(df, str(out))


if __name__ == "__main__":
    main()
