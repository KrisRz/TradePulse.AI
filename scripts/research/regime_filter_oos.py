"""OOS harness for regime filters over EMA20/100 — the L1 idea, honestly.

Borrowed IDEA, new code: the 6-layer system's Layer 1 tried to classify the
market regime and gate entries on it. The models were taught to imitate
hand-written rules, so nobody ever learned whether the IDEA works. This asks
that question the project's way: pre-specified filters, OOS spans only, fee
grid, decision rule registered before the first number.

This is also queue item #1 (docs/RESEARCH_ULEPSZEN_2026-08-07.md, twice
corrected): the simple regime/volatility filter is THE BENCHMARK the future
meta-labeler must beat. Whatever wins here sets that bar; if nothing beats
plain EMA, the bar is plain EMA.

Filters gate the LONG side only (w = ema_signal * filter): they can take the
bot out of the market, never into a new kind of position. All are textbook
constructions, written down before running, none tuned:

- price>SMA200      : hold EMA longs only above the 200d average (trend regime)
- SMA200 rising     : hold only while the 200d average slopes up (20d diff)
- calm vol          : hold only while 20d realized vol is below its own
                      trailing 1y 80th percentile (the "volatile" L1 state)

Full-sample flavours of the first two were printed once in the M4/F2 era
(vol_targeting_study.regime_filter_study); the per-layout OOS numbers, the
fee grid and the DD comparison below have never been seen. Conventions
identical to ema_ensemble_oos.py: decide close(t), earn open(t+1)->open(t+2),
pay (fee+slip)*|dw|; holdout <2026-07-16 enforced.

Usage: PYTHONPATH=. python scripts/research/regime_filter_oos.py
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "ml" / "historical" / "BTCUSDT_1d.csv"

HOLDOUT_START = "2026-07-16"
LAYOUTS = [(730, 180), (500, 125), (1000, 250), (365, 90)]
FEE_GRID = [0.001, 0.002, 0.003, 0.005]
SLIPPAGE = 0.0002
ANNUALIZE = np.sqrt(365)

# --------------------------------------------------------------------------- #
# PRE-REGISTERED DECISION RULE — written 2026-08-08 BEFORE running.
# --------------------------------------------------------------------------- #
DECISION_RULE = {
    "registered": "2026-08-08",
    "question": "Does any pre-specified regime filter improve the deployed "
                "EMA20/100 out-of-sample — and which one is the benchmark "
                "the meta-labeler must beat?",
    "accept_filter_if": [
        "filter Sharpe >= baseline Sharpe in >=3 of 4 layouts @ fee 0.001",
        "filter Sharpe >= baseline Sharpe in >=3 of 4 layouts @ fee 0.002",
        "filter maxDD no worse than baseline in >=3 of 4 layouts @ fee 0.001",
    ],
    "on_accept": "the winning filter becomes (a) the meta-labeler's benchmark "
                 "and (b) a post-M5 candidate for the full M4 harness. "
                 "Nothing changes in the M5 window.",
    "on_reject": "the meta-labeler's benchmark is plain EMA20/100; filters "
                 "leave the queue. A negative result is the deliverable.",
    "note": "all three must hold per filter; two of three is a rejection",
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


def net_returns(df: pd.DataFrame, w: pd.Series, fee: float) -> pd.Series:
    r_bar = df["open"].pct_change().shift(-2)
    cost = (fee + SLIPPAGE) * w.diff().abs().fillna(0.0)
    return ((w.fillna(0.0) * r_bar).fillna(0.0) - cost).iloc[:-2]


def oos_slice(n_bars: int, train: int, test: int) -> slice:
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
    for line in DECISION_RULE["accept_filter_if"]:
        print(f"  - {line}")
    print(f"  note: {DECISION_RULE['note']}")
    print(f"  on accept: {DECISION_RULE['on_accept']}")
    print(f"  on reject: {DECISION_RULE['on_reject']}\n")

    df = load()
    close = df["close"]
    sig = (close.ewm(span=20, adjust=False).mean()
           > close.ewm(span=100, adjust=False).mean()).astype(float)

    sma200 = close.rolling(200).mean()
    vol20 = close.pct_change().rolling(20).std()
    vol_bar = vol20.rolling(365).quantile(0.8)      # trailing, no look-ahead

    filters = {
        "price>SMA200": (close > sma200).astype(float),
        "SMA200 rising": (sma200.diff(20) > 0).astype(float),
        "calm vol": (vol20 < vol_bar).astype(float),
    }
    weights = {"baseline": sig, "bh": pd.Series(1.0, index=df.index)}
    weights.update({name: sig * f.fillna(0.0) for name, f in filters.items()})

    print(f"{'layout':<12}{'fee':>7}" + "".join(f"{n[:12]:>14}" for n in weights))
    cells = []
    for layout in LAYOUTS:
        sl = oos_slice(len(df), *layout)
        years = (sl.stop - sl.start) / 365
        for fee in FEE_GRID:
            row = {"layout": layout, "fee": fee}
            for name, w in weights.items():
                r = net_returns(df, w, fee).iloc[sl]
                row[f"{name}_sharpe"] = sharpe(r)
                row[f"{name}_dd"] = max_dd(r)
                row[f"{name}_expo"] = float(w.iloc[sl].mean())
                row[f"{name}_turn"] = float(w.iloc[sl].diff().abs().sum()) / years
            cells.append(row)
            print(f"{str(layout):<12}{fee:>7.3f}"
                  + "".join(f"{row[f'{n}_sharpe']:>14.2f}" for n in weights))

    def count(fee: float, name: str, key: str, cmp) -> int:
        return sum(1 for c in cells if c["fee"] == fee
                   and cmp(c[f"{name}_{key}"], c[f"baseline_{key}"]))

    print(f"\n{'=' * 78}\nVERDICTS (rule applied mechanically, per filter)\n{'=' * 78}")
    verdicts = {}
    ge = lambda a, b: a >= b
    for name in filters:
        checks = {
            "Sharpe >= baseline in >=3/4 @0.001": count(0.001, name, "sharpe", ge) >= 3,
            "Sharpe >= baseline in >=3/4 @0.002": count(0.002, name, "sharpe", ge) >= 3,
            "maxDD no worse in >=3/4 @0.001": count(0.001, name, "dd", ge) >= 3,
        }
        verdicts[name] = {"checks": checks, "accepted": all(checks.values())}
        print(f"\n  {name}: {'ACCEPT' if verdicts[name]['accepted'] else 'REJECT'}")
        for c, ok in checks.items():
            print(f"    [{'PASS' if ok else 'FAIL'}] {c}")

    accepted = [n for n, v in verdicts.items() if v["accepted"]]
    print(f"\n{'=' * 78}")
    if accepted:
        print(f"ACCEPTED: {', '.join(accepted)} -> benchmark for the meta-labeler"
              f" + post-M5 M4-harness candidate(s)")
    else:
        print("ACCEPTED: none. The meta-labeler's benchmark is plain EMA20/100.")
    print("=" * 78)

    out = ROOT / "docs" / "regime_filter_oos_result.json"
    out.write_text(json.dumps({"decision_rule": DECISION_RULE,
                               "verdicts": {n: v for n, v in verdicts.items()},
                               "cells": cells}, indent=2, default=str))
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
