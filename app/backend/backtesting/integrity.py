"""Integrity validation for historical OHLCV data (plan §4).

Bad data means a wrong backtest means wrong decisions, so every dataset gets
audited before it feeds research or gate metrics. Two classes of findings:

- **Hard failures** — the file is broken and must not be used: non-monotonic
  or duplicated timestamps, non-UTC index, NaN, non-positive prices, negative
  volume, or OHLC rows violating ``high >= max(open, close)`` /
  ``low <= min(open, close)``.
- **Gaps** — missing bars. Binance history genuinely contains them (exchange
  maintenance windows, e.g. 2018-02-08), so gaps are REPORTED for review, not
  fabricated and not an automatic failure. ``--strict`` promotes them to
  failures for datasets where continuity is required.

Usage:
    python -m app.backend.backtesting.integrity data/ml/historical/*.csv
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .data import load_csv

# Interval token (from filename, e.g. BTCUSDT_1h.csv) -> expected bar spacing.
_SPACING = {
    "1m": pd.Timedelta(minutes=1), "3m": pd.Timedelta(minutes=3),
    "5m": pd.Timedelta(minutes=5), "15m": pd.Timedelta(minutes=15),
    "30m": pd.Timedelta(minutes=30), "1h": pd.Timedelta(hours=1),
    "2h": pd.Timedelta(hours=2), "4h": pd.Timedelta(hours=4),
    "1d": pd.Timedelta(days=1),
}


@dataclass
class IntegrityReport:
    path: str
    bars: int = 0
    start: str = ""
    end: str = ""
    spacing: str = ""
    failures: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


def infer_spacing(df: pd.DataFrame, path: Path) -> pd.Timedelta:
    """Expected bar spacing from the filename token, else the modal delta."""
    for token, delta in _SPACING.items():
        if f"_{token}" in path.stem or f"-{token}-" in path.stem:
            return delta
    return df.index.to_series().diff().mode().iloc[0]


def validate_frame(df: pd.DataFrame, spacing: pd.Timedelta,
                   path: str = "<frame>") -> IntegrityReport:
    """Run every integrity check on a loaded OHLCV frame."""
    rep = IntegrityReport(path=path, bars=len(df), spacing=str(spacing))
    if df.empty:
        rep.failures.append("empty dataset")
        return rep
    rep.start, rep.end = str(df.index[0]), str(df.index[-1])

    if df.index.tz is None:
        rep.failures.append("index is not timezone-aware (expected UTC)")
    dupes = int(df.index.duplicated().sum())
    if dupes:
        rep.failures.append(f"{dupes} duplicated timestamps")
    if not df.index.is_monotonic_increasing:
        rep.failures.append("index is not monotonically increasing")

    nans = int(df[["open", "high", "low", "close", "volume"]].isna().sum().sum())
    if nans:
        rep.failures.append(f"{nans} NaN values")
    nonpos = int((df[["open", "high", "low", "close"]] <= 0).any(axis=1).sum())
    if nonpos:
        rep.failures.append(f"{nonpos} rows with non-positive prices")
    negvol = int((df["volume"] < 0).sum())
    if negvol:
        rep.failures.append(f"{negvol} rows with negative volume")

    bad_high = df["high"] < df[["open", "close"]].max(axis=1)
    bad_low = df["low"] > df[["open", "close"]].min(axis=1)
    if int(bad_high.sum()):
        rep.failures.append(f"{int(bad_high.sum())} rows with high < max(open, close)")
    if int(bad_low.sum()):
        rep.failures.append(f"{int(bad_low.sum())} rows with low > min(open, close)")

    # Gap scan — every step larger than the expected spacing.
    deltas = df.index.to_series().diff().iloc[1:]
    for when, delta in deltas[deltas > spacing].items():
        missing = int(delta / spacing) - 1
        prev = when - delta
        rep.gaps.append(f"{missing} bar(s) missing after {prev} (gap {delta})")
    return rep


def validate_file(path: str | Path) -> IntegrityReport:
    path = Path(path)
    df = load_csv(path)
    # load_csv dedupes/sorts defensively — re-read raw to catch source defects.
    raw = pd.read_csv(path)
    ts = pd.to_datetime(raw["timestamp"], utc=True)
    rep = validate_frame(df.copy(), infer_spacing(df, path), str(path))
    raw_dupes = int(ts.duplicated().sum())
    if raw_dupes:
        rep.failures.append(f"{raw_dupes} duplicated timestamps in source file")
    if not ts.is_monotonic_increasing:
        rep.failures.append("source file timestamps are not sorted")
    return rep


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Validate historical OHLCV CSV integrity.")
    p.add_argument("paths", nargs="+", help="CSV files to validate")
    p.add_argument("--strict", action="store_true",
                   help="treat gaps as failures (require perfect continuity)")
    p.add_argument("--max-gap-lines", type=int, default=10,
                   help="how many gap details to print per file")
    args = p.parse_args(argv)

    all_ok = True
    for path in args.paths:
        rep = validate_file(path)
        failed = bool(rep.failures) or (args.strict and bool(rep.gaps))
        all_ok &= not failed
        verdict = "FAIL" if failed else "OK"
        print(f"[{verdict}] {rep.path}: {rep.bars:,} bars, "
              f"{rep.start} -> {rep.end}, spacing {rep.spacing}")
        for f in rep.failures:
            print(f"       FAILURE: {f}")
        for g in rep.gaps[: args.max_gap_lines]:
            print(f"       gap: {g}")
        if len(rep.gaps) > args.max_gap_lines:
            print(f"       … and {len(rep.gaps) - args.max_gap_lines} more gaps")
        if not rep.gaps and not rep.failures:
            print("       clean: no gaps, no defects")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
