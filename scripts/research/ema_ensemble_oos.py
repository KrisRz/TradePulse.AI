"""OOS harness for the EMA-speed AVERAGE ensemble — the honest follow-up.

The 2026-08-07 screen (ema_ensemble_study.py) was full-sample and descriptive:
AVERAGE beat the baseline in both epochs and 6/9 years, MAJORITY lost. That
earns a *question*, not a verdict. This script asks the question the way
scenario_lab asks it: out-of-sample spans only, four fold layouts, a fee grid,
buy & hold alongside, and a decision rule registered BEFORE the first number.

Why return-level and not the trade engine: the engine rounds targets to
-1/0/+1 (engine.py) and the paper book has no fractional positions. Building
that support is exactly the adoption cost this study decides on — so the study
itself must not require it. The simulation convention is identical to M4/F2
and ema_ensemble_study.py: decide at close(t), earn open(t+1)->open(t+2),
pay (fee + slippage) x |delta weight|.

No fitting happens anywhere: members are the pre-specified family around the
deployed 20/100 (registered 2026-08-07, before any result). The "train" span
of each fold layout is therefore only indicator burn-in; OOS spans are the
same contiguous test tiling scenario_lab uses.

Usage: PYTHONPATH=. python scripts/research/ema_ensemble_oos.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "ml" / "historical" / "BTCUSDT_1d.csv"

HOLDOUT_START = "2026-07-16"          # nothing at/after this enters the study
MEMBERS = [(10, 50), (15, 75), (20, 100), (30, 150), (40, 200)]
LAYOUTS = [(730, 180), (500, 125), (1000, 250), (365, 90)]   # = scenario_lab
FEE_GRID = [0.001, 0.002, 0.003, 0.005]                       # per side
SLIPPAGE = 0.0002
ANNUALIZE = np.sqrt(365)

# --------------------------------------------------------------------------- #
# PRE-REGISTERED DECISION RULE — written 2026-08-08 BEFORE running.
# The full-sample screen was seen on 2026-08-07; the per-layout OOS numbers,
# the fee-grid behaviour and the B&H comparison below have NOT been.
# --------------------------------------------------------------------------- #
DECISION_RULE = {
    "registered": "2026-08-08",
    "question": "Does the pre-specified 5-member AVERAGE ensemble beat the "
                "deployed single EMA20/100 out-of-sample, and survive fees?",
    "accept_if": [
        "ensemble Sharpe >= baseline Sharpe in >=3 of 4 layouts @ fee 0.001",
        "ensemble Sharpe >= baseline Sharpe in >=3 of 4 layouts @ fee 0.002",
        "ensemble Sharpe >  B&H Sharpe      in >=3 of 4 layouts @ fee 0.002",
        "ensemble maxDD no worse than baseline in >=3 of 4 layouts @ fee 0.001",
    ],
    "on_accept": "queue for post-M5: fractional positions in engine+book, then "
                 "the full M4 harness. Nothing changes in the M5 window.",
    "on_reject": "ensemble drops off the adoption queue; a negative result is "
                 "the deliverable.",
    "note": "all four must hold; three of four is a rejection, not a debate",
}


def load() -> pd.DataFrame:
    df = pd.read_csv(DATA, parse_dates=["timestamp"], index_col="timestamp")
    cutoff = pd.Timestamp(HOLDOUT_START)
    if getattr(df.index, "tz", None) is not None:
        cutoff = cutoff.tz_localize(df.index.tz)
    before = len(df)
    df = df[df.index < cutoff]
    print(f"holdout: {before - len(df)} bar(s) at/after {HOLDOUT_START} excluded"
          f" ({len(df)} bars remain, {df.index[0].date()} -> {df.index[-1].date()})")
    return df


def ema_signal(close: pd.Series, fast: int, slow: int) -> pd.Series:
    f = close.ewm(span=fast, adjust=False).mean()
    s = close.ewm(span=slow, adjust=False).mean()
    return (f > s).astype(float)


def net_returns(df: pd.DataFrame, w: pd.Series, fee: float) -> pd.Series:
    """Per-bar net returns for a weight series, M4/F2 conventions."""
    r_bar = df["open"].pct_change().shift(-2)     # close(t) decision -> o+1..o+2
    cost = (fee + SLIPPAGE) * w.diff().abs().fillna(0.0)
    return ((w.fillna(0.0) * r_bar).fillna(0.0) - cost).iloc[:-2]


def oos_slice(n_bars: int, train: int, test: int) -> slice:
    """Contiguous union of scenario_lab's test spans for one layout."""
    n_folds = (n_bars - train) // test
    return slice(train, train + n_folds * test)


def sharpe(r: pd.Series) -> float:
    return float(r.mean() / r.std() * ANNUALIZE) if r.std() > 0 else 0.0


def max_dd(r: pd.Series) -> float:
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1).min())


def main() -> int:
    print("=" * 78)
    print(f"PRE-REGISTERED DECISION RULE (registered {DECISION_RULE['registered']})")
    print("=" * 78)
    for line in DECISION_RULE["accept_if"]:
        print(f"  - {line}")
    print(f"  note: {DECISION_RULE['note']}")
    print(f"  on accept: {DECISION_RULE['on_accept']}")
    print(f"  on reject: {DECISION_RULE['on_reject']}\n")

    df = load()
    close = df["close"]
    signals = pd.DataFrame({f"{f}/{s}": ema_signal(close, f, s) for f, s in MEMBERS})
    weights = {
        "baseline": signals["20/100"],
        "ensemble": signals.mean(axis=1),
        "bh": pd.Series(1.0, index=df.index),
    }

    print(f"{'layout':<12}{'fee':>7}{'base':>8}{'ens':>8}{'B&H':>8}"
          f"{'baseDD':>9}{'ensDD':>9}{'baseT/y':>9}{'ensT/y':>8}")
    cells = []
    for layout in LAYOUTS:
        sl = oos_slice(len(df), *layout)
        years = (sl.stop - sl.start) / 365
        for fee in FEE_GRID:
            row = {"layout": layout, "fee": fee, "oos_years": round(years, 2)}
            for name, w in weights.items():
                r = net_returns(df, w, fee).iloc[sl]
                row[f"{name}_sharpe"] = sharpe(r)
                row[f"{name}_dd"] = max_dd(r)
                row[f"{name}_turn"] = float(w.iloc[sl].diff().abs().sum()) / years
            cells.append(row)
            print(f"{str(layout):<12}{fee:>7.3f}{row['baseline_sharpe']:>8.2f}"
                  f"{row['ensemble_sharpe']:>8.2f}{row['bh_sharpe']:>8.2f}"
                  f"{row['baseline_dd']:>9.1%}{row['ensemble_dd']:>9.1%}"
                  f"{row['baseline_turn']:>9.1f}{row['ensemble_turn']:>8.1f}")

    def count(fee: float, pred) -> int:
        return sum(1 for c in cells if c["fee"] == fee and pred(c))

    checks = {
        "ens >= base Sharpe in >=3/4 @0.001":
            count(0.001, lambda c: c["ensemble_sharpe"] >= c["baseline_sharpe"]) >= 3,
        "ens >= base Sharpe in >=3/4 @0.002":
            count(0.002, lambda c: c["ensemble_sharpe"] >= c["baseline_sharpe"]) >= 3,
        "ens > B&H Sharpe in >=3/4 @0.002":
            count(0.002, lambda c: c["ensemble_sharpe"] > c["bh_sharpe"]) >= 3,
        "ens maxDD no worse than base in >=3/4 @0.001":
            count(0.001, lambda c: c["ensemble_dd"] >= c["baseline_dd"]) >= 3,
    }
    accepted = all(checks.values())

    print(f"\n{'=' * 78}\nVERDICT (rule applied mechanically)\n{'=' * 78}")
    for name, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\n  ensemble AVERAGE: {'ACCEPT' if accepted else 'REJECT'}")
    print(f"  next: {DECISION_RULE['on_accept' if accepted else 'on_reject']}")

    out = ROOT / "docs" / "ema_ensemble_oos_result.json"
    out.write_text(json.dumps(
        {"decision_rule": DECISION_RULE, "checks": checks, "accepted": accepted,
         "cells": cells}, indent=2, default=str))
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
