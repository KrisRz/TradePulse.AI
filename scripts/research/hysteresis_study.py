"""Challenger #10: a hysteresis band on the EMA20/100 cross, 4h channel.

Pre-registered in ``docs/HYSTERESIS_DESIGN_2026-09-16.md`` (committed before this
file ran). The decision rule R1-R4 lives there; this script only implements it and
prints the whole grid whatever the verdict.

The candidate changes one thing: how far the EMA gap has to travel before the bot
changes its mind. Long above +b, flat below -b, and in between it keeps whatever
it held. With b = 0 the target series must equal ``EmaCrossover(20, 100)``
exactly, or nothing below means anything — that is checked first.

Parameters are fixed, so each fold layout is measured as ONE continuous run over
its out-of-sample span, with indicators warmed on the history before it
(stitching folds adds ~0.05 Sharpe of artefact — audit 2026-09-04, MEDIUM-3).

    PYTHONPATH=. .venv/bin/python scripts/research/hysteresis_study.py
"""

from __future__ import annotations

import argparse
import hashlib
import math
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from app.backend.backtesting.data import load_csv  # noqa: E402
from app.backend.backtesting.engine import BacktestConfig, run_backtest  # noqa: E402
from app.backend.backtesting.indicators import ema  # noqa: E402
from app.backend.backtesting.metrics import compute_metrics  # noqa: E402
from app.backend.backtesting.strategies import EmaCrossover  # noqa: E402
from app.backend.paper_trading.gate import (  # noqa: E402
    expected_max_sharpe,
    probabilistic_sharpe,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "ml" / "historical"
DESIGN = ROOT / "docs" / "HYSTERESIS_DESIGN_2026-09-16.md"
HOLDOUT = pd.Timestamp("2026-07-16", tz="UTC")

FAST, SLOW = 20, 100
BANDS = [0.0025, 0.005, 0.0075, 0.01, 0.015, 0.02]
FEES = [0.001, 0.002, 0.003]
LAYOUTS = [(730, 180), (500, 125), (1000, 250), (365, 90)]
SLIPPAGE = 0.0002
PRIOR_TRIALS = 10
R3_LAYOUT = (365, 90)
R4_LAYOUT, R4_FEE = (365, 90), 0.001


def load(timeframe: str) -> pd.DataFrame:
    df = load_csv(str(DATA / f"BTCUSDT_{timeframe}.csv"))
    cutoff = HOLDOUT if df.index.tz is not None else HOLDOUT.tz_localize(None)
    return df[df.index < cutoff]


def baseline_target(df: pd.DataFrame) -> pd.Series:
    return EmaCrossover(fast=FAST, slow=SLOW, allow_short=False).target_positions(df)


def hysteresis_target(df: pd.DataFrame, band: float) -> pd.Series:
    """Long above +band, flat below -band, otherwise hold; flat through warmup."""
    close = df["close"]
    slow = ema(close, SLOW)
    gap = ((ema(close, FAST) - slow) / slow).to_numpy()
    out = np.zeros(len(df), dtype=int)
    state = 0
    for i, g in enumerate(gap):
        if i < SLOW:
            continue
        if g > band:
            state = 1
        elif g < -band:
            state = 0
        out[i] = state
    return pd.Series(out, index=df.index)


def spans(df: pd.DataFrame):
    """For each layout: (first OOS bar, end of the last fold) — the walk-forward slicing."""
    out = {}
    for train, test in LAYOUTS:
        n_folds = (len(df) - train) // test
        if n_folds < 1:
            continue
        out[(train, test)] = (train, train + n_folds * test)
    return out


def run(df: pd.DataFrame, target_fn, span: tuple[int, int], fee: float,
        timeframe: str = "4h"):
    start, end = span
    warm = df.iloc[:end]
    sub = df.iloc[start:end]
    target = target_fn(warm).reindex(sub.index).fillna(0).astype(int)
    cfg = BacktestConfig(fee_rate=fee, slippage=SLIPPAGE, allow_short=False)
    res = run_backtest(sub, target, cfg, "hysteresis", timeframe)
    return compute_metrics(res, sub), res.equity_curve


def yearly_log_returns(equity: pd.Series) -> pd.Series:
    by_year = equity.groupby(equity.index.year).last()
    prev = by_year.shift(1)
    prev.iloc[0] = equity.iloc[0]
    return np.log(by_year / prev)


def contiguous_runs(flags: list[bool], min_len: int = 3) -> list[list[int]]:
    runs, current = [], []
    for i, ok in enumerate(flags):
        if ok:
            current.append(i)
        else:
            if len(current) >= min_len:
                runs.append(current)
            current = []
    if len(current) >= min_len:
        runs.append(current)
    return runs


def study(timeframe: str, verbose: bool = True) -> dict:
    df = load(timeframe)
    lay = spans(df)

    full_base = baseline_target(df)
    full_zero = hysteresis_target(df, 0.0)
    if not full_base.equals(full_zero):
        diff = int((full_base != full_zero).sum())
        raise SystemExit(f"b=0 does not reproduce EmaCrossover ({diff} bars differ) — no test")

    cells = {}
    curves = {}
    for layout, span in lay.items():
        for fee in FEES:
            base_m, base_eq = run(df, baseline_target, span, fee, timeframe)
            bh_m, _ = run(df, lambda d: pd.Series(1, index=d.index), span, fee, timeframe)
            cells[("base", layout, fee)] = base_m
            cells[("bh", layout, fee)] = bh_m
            curves[("base", layout, fee)] = base_eq
            for band in BANDS:
                m, eq = run(df, lambda d, b=band: hysteresis_target(d, b), span, fee, timeframe)
                cells[(band, layout, fee)] = m
                curves[(band, layout, fee)] = eq

    if verbose:
        print(f"\n=== {timeframe}: {df.index[0].date()} → {df.index[-1].date()}, "
              f"{len(df)} bars; b=0 reproduces the baseline exactly ===")
        for fee in FEES:
            print(f"\nfee {fee*100:.1f}% — Sharpe (trades) per layout; maxDD in brackets")
            header = f"{'':>10}" + "".join(f"{f'{t}/{s}':>24}" for t, s in lay)
            print(header)
            for key in ["bh", "base", *BANDS]:
                label = key if isinstance(key, str) else f"b={key*100:.2f}%"
                row = f"{label:>10}"
                for layout in lay:
                    m = cells[(key, layout, fee)]
                    row += f"{m.sharpe:>9.2f} ({m.trades:>3}) [{m.max_drawdown*100:>5.0f}%]"
                print(row)
    return {"df": df, "layouts": list(lay), "cells": cells, "curves": curves}


def verdict(res: dict) -> dict:
    cells, layouts = res["cells"], res["layouts"]

    def beats_base(band, fee):
        return sum(cells[(band, l, fee)].sharpe > cells[("base", l, fee)].sharpe for l in layouts)

    r1_flags = [all(beats_base(b, fee) >= 3 for fee in (0.001, 0.002)) for b in BANDS]
    r1_runs = contiguous_runs(r1_flags)

    def beats_bh(key, fee):
        return sum(cells[(key, l, fee)].sharpe > cells[("bh", l, fee)].sharpe for l in layouts)

    base_bh_03 = beats_bh("base", 0.003)
    out = {"r1_flags": dict(zip(BANDS, r1_flags)), "r1_runs": [[BANDS[i] for i in r] for r in r1_runs],
           "base_beats_bh_at_0.3": base_bh_03,
           "cand_beats_bh_at_0.3": {b: beats_bh(b, 0.003) for b in BANDS},
           "beats_base": {b: {fee: beats_base(b, fee) for fee in FEES} for b in BANDS}}

    accepted_run = None
    details = []
    for run_idx in r1_runs:
        run_bands = [BANDS[i] for i in run_idx]
        r2 = all(beats_bh(b, 0.003) > base_bh_03 for b in run_bands)
        middle = run_bands[(len(run_bands) - 1) // 2]
        cand_y = yearly_log_returns(res["curves"][(middle, R3_LAYOUT, 0.001)])
        base_y = yearly_log_returns(res["curves"][("base", R3_LAYOUT, 0.001)])
        d = (cand_y - base_y).dropna()
        r3 = bool(d.sum() > 0 and (d.sum() - d.max()) > 0)
        details.append({"run": run_bands, "r2": r2, "r3": r3, "r3_middle": middle,
                        "r3_by_year": d.round(4).to_dict()})
        if r2 and r3 and accepted_run is None:
            accepted_run = run_bands
    out["runs"] = details

    # R4 — DSR of the best cell against N = prior trials + grid size.
    per_bar = {}
    for b in BANDS:
        rets = res["curves"][(b, R4_LAYOUT, R4_FEE)].pct_change().dropna()
        per_bar[b] = (rets, float(rets.mean() / rets.std(ddof=1)))
    best = max(BANDS, key=lambda b: per_bar[b][1])
    rets, sr = per_bar[best]
    var = float(np.var([v[1] for v in per_bar.values()], ddof=1))
    n_trials = PRIOR_TRIALS + len(BANDS)
    sr_star = expected_max_sharpe(n_trials, var)
    dsr = probabilistic_sharpe(sr, sr_star, len(rets), float(rets.skew()),
                               float(rets.kurt()) + 3.0)
    out["r4"] = {"best_band": best, "sr_per_bar": sr, "trial_var_per_bar": var,
                 "n_trials": n_trials, "expected_max_sr_per_bar": sr_star, "dsr": dsr,
                 "pass": bool(math.isfinite(dsr) and dsr >= 0.95)}

    out["accepted"] = bool(accepted_run is not None and out["r4"]["pass"])
    out["accepted_run"] = accepted_run
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.parse_args(argv)
    digest = hashlib.sha256(DESIGN.read_bytes()).hexdigest()
    print(f"design: {DESIGN.name}  sha256 {digest}")

    res = study("4h")
    v = verdict(res)
    print("\n=== decision (pre-registered R1-R4) ===")
    print(f"R1 per band (beats baseline in >=3/4 layouts at 0.1% AND 0.2%): "
          f"{ {f'{b*100:.2f}%': ok for b, ok in v['r1_flags'].items()} }")
    print("   layouts beaten per band/fee: " + "; ".join(
        f"{b*100:.2f}%: " + "/".join(str(v['beats_base'][b][f]) for f in FEES) for b in BANDS))
    print(f"R1 contiguous runs (>=3): {v['r1_runs'] or 'none'}")
    print(f"R2 beats B&H at 0.3%: baseline {v['base_beats_bh_at_0.3']}/4, candidate "
          + ", ".join(f"{b*100:.2f}%={n}" for b, n in v['cand_beats_bh_at_0.3'].items()))
    for d in v["runs"]:
        print(f"   run {d['run']}: R2 {'pass' if d['r2'] else 'FAIL'}, "
              f"R3 (b={d['r3_middle']*100:.2f}%) {'pass' if d['r3'] else 'FAIL'} {d['r3_by_year']}")
    r4 = v["r4"]
    print(f"R4 best cell b={r4['best_band']*100:.2f}% SR/bar {r4['sr_per_bar']:.4f} vs "
          f"E[max] {r4['expected_max_sr_per_bar']:.4f} (N={r4['n_trials']}, "
          f"var {r4['trial_var_per_bar']:.2e}) → DSR {r4['dsr']:.3f} "
          f"{'pass' if r4['pass'] else 'FAIL'}")
    print(f"\nVERDICT: {'ACCEPT' if v['accepted'] else 'REJECT'}"
          + (f" (band run {v['accepted_run']})" if v["accepted"] else ""))

    print("\n--- diagnostic only (not part of the verdict): BTC 1d ---")
    try:
        study("1d")
    except SystemExit as exc:
        print(f"1d diagnostic skipped: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
