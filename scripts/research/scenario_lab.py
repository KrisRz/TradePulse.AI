"""Scenario lab — one mill every candidate strategy goes through.

Why this exists
---------------
Strategy ideas are free and infinite; validating one honestly is the expensive,
rare thing. This project already owns that machinery — walk-forward, a shared
cost model, an enforced holdout, pre-registered thresholds. What it lacked was a
single place to point that machinery at a *new* candidate.

The trap this is built to avoid
-------------------------------
Test fifty strategies, pick the best, and you will find excellent backtest
numbers by pure chance. At p<0.05, fifty trials produce ~2.5 false positives
before any skill is involved. That is how retail algo trading usually dies: not
on a bad strategy, but on selecting the best of many.

Three defences, all mandatory:

1. **The decision rule is pre-registered** — declared in :data:`DECISION_RULE`
   below, printed before any result, and never edited to fit an outcome.
2. **Trials are counted and charged for.** Every candidate·layout·fee cell is a
   trial, and the report ends with a Deflated Sharpe Ratio (Bailey & López de
   Prado 2014), which asks: given how many things we tried, how surprising is
   the best one? A Sharpe that looks fine alone can be unremarkable as the
   maximum of forty draws.
3. **The holdout is enforced, not trusted.** Every dataset is truncated before
   :data:`HOLDOUT_START`; the live M5 window cannot leak in even by accident.

Accepting a candidate does NOT change the running bot. It starts a *new* paper
window for that channel. The BTC 1d book being measured since 2026-07-16 is
never modified — that is what makes its eventual verdict mean anything.

    python scripts/research/scenario_lab.py                 # all candidates
    python scripts/research/scenario_lab.py --only btc_4h
    python scripts/research/scenario_lab.py --json out.json
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from app.backend.backtesting.data import load_csv  # noqa: E402
from app.backend.backtesting.engine import (  # noqa: E402
    BacktestConfig,
    BacktestResult,
    run_backtest,
)
from app.backend.backtesting.metrics import compute_metrics  # noqa: E402
from app.backend.backtesting.strategies import (  # noqa: E402
    EmaCrossover,
    RsiMeanReversion,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "ml" / "historical"

#: Nothing at or after this date may enter a backtest — it is the live window.
HOLDOUT_START = "2026-07-16"

#: Fee levels per side. The live venue charges 0.001; the rest probe how much
#: cost the edge survives, which matters far more at higher trade frequencies.
FEE_GRID = [0.001, 0.002, 0.003, 0.005]

#: Fold layouts, same four the M4 walk-forward and the calibration audit used.
LAYOUTS = [(730, 180), (500, 125), (1000, 250), (365, 90)]

SLIPPAGE = 0.0002
INITIAL_CAPITAL = 10_000.0

# --------------------------------------------------------------------------- #
# PRE-REGISTERED DECISION RULE — write it here BEFORE running anything.
# Editing this after seeing results is the whole failure mode this file exists
# to prevent. If a rule turns out to be wrong, change it in a commit of its own,
# state why, and re-run everything from scratch.
# --------------------------------------------------------------------------- #
DECISION_RULE = {
    "registered": "2026-08-06",
    "accept_if": [
        "OOS Sharpe >= 0.8 at fee 0.002 in at least 3 of the 4 layouts",
        "beats buy & hold on Sharpe in at least 3 of the 4 layouts",
        "at least 20 closed trades across the OOS span (else underpowered)",
        "Deflated Sharpe Ratio >= 0.95 after charging for every trial run",
    ],
    "on_accept": "start a NEW paper window for that channel — never modify BTC 1d",
    "note": "all four must hold; three out of four is a rejection, not a debate",
}


# --------------------------------------------------------------------------- #
# Candidates
# --------------------------------------------------------------------------- #
@dataclass
class Candidate:
    """One thing we are asking a question about."""

    key: str
    description: str
    csv: pathlib.Path
    timeframe: str
    build: Callable[[], object]
    #: Why this is worth asking. Printed, so nobody has to guess later.
    rationale: str = ""


def ema(fast: int, slow: int, allow_short: bool = False) -> Callable[[], object]:
    return lambda: EmaCrossover(fast=fast, slow=slow, allow_short=allow_short)


def rsi_mr(allow_short: bool) -> Callable[[], object]:
    """Textbook defaults (14, 30/70, exit 50) — deliberately NOT tuned."""
    return lambda: RsiMeanReversion(allow_short=allow_short)


CANDIDATES: list[Candidate] = [
    Candidate(
        key="btc_1d_live",
        description="BTC 1d EMA20/100 long-only — the deployed configuration",
        csv=DATA / "BTCUSDT_1d.csv", timeframe="1d", build=ema(20, 100),
        rationale="The control. Every other row is only meaningful next to this one.",
    ),
    Candidate(
        key="btc_4h",
        description="BTC 4h EMA20/100 long-only",
        csv=DATA / "BTCUSDT_4h.csv", timeframe="4h", build=ema(20, 100),
        rationale="7.2x the round-trips of 1d, so a verdict arrives in months "
                  "instead of years — IF the edge survives 7x the fee drag.",
    ),
    Candidate(
        key="eth_1d",
        description="ETH 1d EMA20/100 long-only",
        csv=DATA / "ETHUSDT_1d.csv", timeframe="1d", build=ema(20, 100),
        rationale="A second parallel channel at the same trade rate, not a faster "
                  "one. Diversifies the bet without changing the strategy.",
    ),
    Candidate(
        key="btc_1d_rsi",
        description="BTC 1d RSI mean-reversion long-only (buy dips)",
        csv=DATA / "BTCUSDT_1d.csv", timeframe="1d", build=rsi_mr(False),
        rationale="The user's 2026-08-08 premise: buy when it falls instead of "
                  "following the trend. Textbook parameters, no tuning.",
    ),
    Candidate(
        key="btc_1d_rsi_ls",
        description="BTC 1d RSI mean-reversion long+short (buy dips, sell rips)",
        csv=DATA / "BTCUSDT_1d.csv", timeframe="1d", build=rsi_mr(True),
        rationale="Full counter-trend: also sell when it rises. The short leg "
                  "of trend-following already failed; this asks if the "
                  "mean-reversion short is any different.",
    ),
    Candidate(
        key="btc_4h_rsi_ls",
        description="BTC 4h RSI mean-reversion long+short",
        csv=DATA / "BTCUSDT_4h.csv", timeframe="4h", build=rsi_mr(True),
        rationale="Counter-trend at higher frequency — closer to day trading, "
                  "more signals, 6x the fee events of 1d.",
    ),
    Candidate(
        key="btc_1h_rsi_ls",
        description="BTC 1h RSI mean-reversion long+short",
        csv=DATA / "BTCUSDT_1h.csv", timeframe="1h", build=rsi_mr(True),
        rationale="The closest our validated data gets to day trading. If "
                  "aggressive short-horizon reversal works anywhere, it is "
                  "here — and so is 24x the fee drag of 1d.",
    ),
    Candidate(
        key="btc_1d_short",
        description="BTC 1d EMA20/100 WITH a short leg",
        csv=DATA / "BTCUSDT_1d.csv", timeframe="1d", build=ema(20, 100, allow_short=True),
        rationale="The bot sat flat while BTC fell 12.73% since 2026-05-29. A short "
                  "leg would monetise that. NOTE: the fractional cost model "
                  "understates short fees (see docs/QUANTITY_BOOK_2026-08-06.md), "
                  "so treat a marginal pass here as a fail.",
    ),
]


# --------------------------------------------------------------------------- #
# The mill — identical for every candidate
# --------------------------------------------------------------------------- #
def load(candidate: Candidate) -> pd.DataFrame:
    """Load and truncate. The holdout is enforced here, not assumed elsewhere."""
    if not candidate.csv.exists():
        raise FileNotFoundError(candidate.csv)
    df = load_csv(str(candidate.csv))

    # The CSVs carry a tz-aware index; a naive cutoff raises rather than
    # silently comparing wrong, so match whatever the data uses.
    cutoff = pd.Timestamp(HOLDOUT_START)
    if getattr(df.index, "tz", None) is not None:
        cutoff = cutoff.tz_localize(df.index.tz) if cutoff.tzinfo is None \
            else cutoff.tz_convert(df.index.tz)

    before = len(df)
    df = df[df.index < cutoff]
    dropped = before - len(df)
    print(f"  holdout: {dropped} bar(s) at/after {HOLDOUT_START} excluded"
          if dropped else f"  holdout: clean (data ends {df.index[-1].date()})")
    return df


def fold_indices(df: pd.DataFrame, train_bars: int, test_bars: int):
    """(train_start, test_start, test_end) — the slicing walk_forward uses."""
    out, start, n = [], 0, len(df)
    while start + train_bars + test_bars <= n:
        out.append((start, start + train_bars, start + train_bars + test_bars))
        start += test_bars
    return out


def fixed_params_oos(df: pd.DataFrame, strategy, folds, base: dict, name: str,
                     timeframe: str):
    """Fixed parameters over the OOS spans — no in-sample fitting at all.

    This is the honest measurement of a *deployed* strategy: the same
    out-of-sample windows a walk-forward reports on, but with parameters frozen
    the way a live bot freezes them. Lifted from ``calibration_audit.py`` so both
    answer the question the same way.
    """
    cfg = BacktestConfig(**base)
    pieces, trades, running = [], [], cfg.initial_capital
    init = cfg.initial_capital

    for train_start, test_start, test_end in folds:
        ext = df.iloc[train_start:test_end]      # lookback keeps indicators warm
        test = df.iloc[test_start:test_end]
        target = strategy.target_positions(ext).reindex(test.index).fillna(0.0)
        res = run_backtest(test, target,
                           BacktestConfig(**{**base, "initial_capital": init}),
                           name, timeframe)
        piece = res.equity_curve / init * running
        pieces.append(piece)
        running = float(piece.iloc[-1]) if len(piece) else running
        trades.extend(res.trades)

    if not pieces:
        return None, None
    equity = pd.concat(pieces)
    stitched = BacktestResult(
        strategy_name=name, timeframe=timeframe, equity_curve=equity,
        trades=trades, config=cfg, bars=len(equity),
        start=equity.index[0], end=equity.index[-1],
    )
    return compute_metrics(stitched, df.loc[equity.index]), equity


def buy_and_hold(df: pd.DataFrame, span, base: dict, timeframe: str):
    sub = df.loc[span]
    return compute_metrics(
        run_backtest(sub, pd.Series(1.0, index=sub.index),
                     BacktestConfig(**base), "Buy&Hold", timeframe),
        sub,
    )


# --------------------------------------------------------------------------- #
# Trial accounting — the defence against picking the best of many
# --------------------------------------------------------------------------- #
def expected_max_sharpe(sharpes: list[float]) -> float:
    """Expected MAXIMUM Sharpe across N skill-less trials (Bailey & LdP 2014).

    Run enough variants and the best one looks good even when none has an edge.
    This is how good the winner would be expected to look *by chance alone*,
    given how many draws were taken and how much they varied. It is the bar a
    real result has to clear.
    """
    n = len(sharpes)
    if n < 2:
        return 0.0
    variance = float(np.var(sharpes, ddof=1))
    if variance <= 0:
        return 0.0
    gamma = 0.5772156649015329                    # Euler–Mascheroni
    from scipy.stats import norm                  # only needed here

    z1 = norm.ppf(1.0 - 1.0 / n)
    z2 = norm.ppf(1.0 - 1.0 / (n * math.e))
    return math.sqrt(variance) * ((1.0 - gamma) * z1 + gamma * z2)


def deflated_sharpe(observed: float, benchmark: float, returns: pd.Series) -> float:
    """Probability the observed Sharpe beats the selection-adjusted benchmark.

    Corrects for three things a raw Sharpe ignores: how many trials were run
    (via ``benchmark``), how non-normal the returns are, and how short the
    sample is. Below ~0.95 the result is not distinguishable from luck.
    """
    r = returns.dropna()
    n = len(r)
    if n < 30:
        return float("nan")
    skew = float(r.skew())
    kurt = float(r.kurtosis()) + 3.0              # pandas gives excess kurtosis
    denom = 1.0 - skew * observed + ((kurt - 1.0) / 4.0) * observed ** 2
    if denom <= 0:
        return float("nan")
    z = (observed - benchmark) * math.sqrt(n - 1) / math.sqrt(denom)
    from scipy.stats import norm

    return float(norm.cdf(z))


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
@dataclass
class Cell:
    candidate: str
    layout: tuple
    fee: float
    sharpe: float
    bh_sharpe: float
    total_return: float
    bh_return: float
    max_drawdown: float
    trades: int
    exposure: float


@dataclass
class Verdict:
    candidate: str
    description: str
    cells: list = field(default_factory=list)
    trades_total: int = 0
    checks: dict = field(default_factory=dict)
    accepted: bool = False
    periods_per_year: float = 365.0
    best_returns: Optional[pd.Series] = None


def evaluate(candidate: Candidate, verbose: bool = True) -> Optional[Verdict]:
    if verbose:
        print(f"\n{'=' * 78}\n{candidate.key}: {candidate.description}\n{'=' * 78}")
        if candidate.rationale:
            print(f"  why: {candidate.rationale}")
    try:
        df = load(candidate)
    except FileNotFoundError as exc:
        print(f"  SKIPPED — no data at {exc}")
        return None

    verdict = Verdict(candidate=candidate.key, description=candidate.description)
    if verbose:
        print(f"  {len(df)} bars, {df.index[0].date()} → {df.index[-1].date()}")
        print(f"\n  {'layout':<12}{'fee':>7}{'Sharpe':>9}{'B&H':>8}{'return':>10}"
              f"{'B&H ret':>10}{'maxDD':>9}{'trades':>8}")

    for layout in LAYOUTS:
        folds = fold_indices(df, *layout)
        if not folds:
            if verbose:
                print(f"  {str(layout):<12}  — not enough bars for this layout")
            continue
        for fee in FEE_GRID:
            base = {"fee_rate": fee, "slippage": SLIPPAGE,
                    "initial_capital": INITIAL_CAPITAL}
            metrics, equity = fixed_params_oos(
                df, candidate.build(), folds, base, candidate.key, candidate.timeframe)
            if metrics is None:
                continue
            bh = buy_and_hold(df, equity.index, base, candidate.timeframe)
            cell = Cell(candidate.key, layout, fee, metrics.sharpe, bh.sharpe,
                        metrics.total_return, bh.total_return, metrics.max_drawdown,
                        metrics.trades, metrics.exposure)
            verdict.cells.append(cell)
            if fee == 0.002 and verdict.best_returns is None:
                verdict.best_returns = equity.pct_change()
            if verbose:
                print(f"  {str(layout):<12}{fee:>7.3f}{metrics.sharpe:>9.2f}"
                      f"{bh.sharpe:>8.2f}{metrics.total_return:>9.1%}"
                      f"{bh.total_return:>10.1%}{metrics.max_drawdown:>9.1%}"
                      f"{metrics.trades:>8d}")

    if not verdict.cells:
        return None

    # Pre-registered checks, applied mechanically.
    at_gate_fee = [c for c in verdict.cells if c.fee == 0.002]
    verdict.trades_total = max((c.trades for c in verdict.cells), default=0)
    verdict.checks = {
        "sharpe>=0.8 in >=3 layouts @0.2% fee":
            sum(1 for c in at_gate_fee if c.sharpe >= 0.8) >= 3,
        "beats B&H in >=3 layouts @0.2% fee":
            sum(1 for c in at_gate_fee if c.sharpe > c.bh_sharpe) >= 3,
        f"at least 20 closed trades (has {verdict.trades_total})":
            verdict.trades_total >= 20,
    }
    return verdict


def report(verdicts: list[Verdict]) -> dict:
    """Charge every candidate for the trials it took, then apply the rule."""
    all_sharpes = [c.sharpe for v in verdicts for c in v.cells]
    n_trials = len(all_sharpes)
    benchmark = expected_max_sharpe(all_sharpes)

    print(f"\n{'=' * 78}\nTRIAL ACCOUNTING — the defence against picking the best of many"
          f"\n{'=' * 78}")
    print(f"  trials run                : {n_trials} "
          f"({len(verdicts)} candidates x {len(LAYOUTS)} layouts x {len(FEE_GRID)} fees)")
    print(f"  best Sharpe observed      : {max(all_sharpes):.2f}")
    print(f"  expected best by CHANCE   : {benchmark:.2f}")
    print("  ^ a skill-less search of this size is expected to produce a winner")
    print("    this good. Anything at or below it tells us nothing at all.")
    print("  CAVEAT: layout and fee cells of one candidate are strongly")
    print("    correlated, not independent draws, so this bar is softer than the")
    print("    trial count suggests. It is a guardrail, not an oracle — a result")
    print("    that only just clears it should be treated as unproven.")

    summary = {"decision_rule": DECISION_RULE, "n_trials": n_trials,
               "expected_max_sharpe_by_chance": benchmark, "candidates": []}

    print(f"\n{'=' * 78}\nVERDICTS (pre-registered rule, applied mechanically)\n{'=' * 78}")
    for v in verdicts:
        gate_cells = [c for c in v.cells if c.fee == 0.002]
        best = max(gate_cells, key=lambda c: c.sharpe) if gate_cells else None
        dsr = float("nan")
        if v.best_returns is not None and best is not None:
            dsr = deflated_sharpe(best.sharpe, benchmark, v.best_returns)
        v.checks[f"deflated Sharpe >= 0.95 (is {dsr:.3f})"] = (
            not math.isnan(dsr) and dsr >= 0.95)
        v.accepted = all(v.checks.values())

        print(f"\n  {v.candidate}: {'ACCEPT' if v.accepted else 'REJECT'}")
        for name, ok in v.checks.items():
            print(f"    [{'PASS' if ok else 'FAIL'}] {name}")
        summary["candidates"].append({
            "key": v.candidate, "description": v.description,
            "accepted": v.accepted, "checks": v.checks,
            "deflated_sharpe": None if math.isnan(dsr) else dsr,
            "best_gate_sharpe": best.sharpe if best else None,
            "cells": [c.__dict__ for c in v.cells],
        })

    accepted = [v.candidate for v in verdicts if v.accepted]
    print(f"\n{'=' * 78}")
    if accepted:
        print(f"ACCEPTED: {', '.join(accepted)}")
        print(f"NEXT: {DECISION_RULE['on_accept']}")
    else:
        print("ACCEPTED: none. The running BTC 1d channel stands unchanged.")
    print("=" * 78)
    return summary


def print_preregistration() -> None:
    """Print the rule BEFORE any number, so it cannot be quietly reinterpreted."""
    print("=" * 78)
    print(f"PRE-REGISTERED DECISION RULE (registered {DECISION_RULE['registered']})")
    print("=" * 78)
    for line in DECISION_RULE["accept_if"]:
        print(f"  - {line}")
    print(f"  note: {DECISION_RULE['note']}")
    print(f"  on accept: {DECISION_RULE['on_accept']}")
    print(f"  holdout enforced: nothing at/after {HOLDOUT_START} enters any backtest")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--only", action="append",
                   help="evaluate only these candidate keys (repeatable)")
    p.add_argument("--list", action="store_true", help="list candidates and exit")
    p.add_argument("--json", type=pathlib.Path, help="write the full summary here")
    args = p.parse_args(argv)

    if args.list:
        for c in CANDIDATES:
            print(f"  {c.key:<16} {c.description}")
        return 0

    chosen = [c for c in CANDIDATES if not args.only or c.key in args.only]
    if not chosen:
        print(f"no candidate matches {args.only}")
        return 2

    print_preregistration()
    verdicts = [v for v in (evaluate(c) for c in chosen) if v is not None]
    if not verdicts:
        print("\nnothing evaluated — is data/ml/historical/ populated?")
        return 1

    summary = report(verdicts)
    if args.json:
        args.json.write_text(json.dumps(summary, indent=2, default=str))
        print(f"\nwritten: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
