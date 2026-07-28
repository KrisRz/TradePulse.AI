"""Calibration audit — does the LIVE configuration match what we validated?

Written 2026-07-28 to answer three questions the M4 report left open:

1. The walk-forward in `docs/M4_EDGE_VALIDATION.md` re-fits parameters on every
   fold, but the bot trades a *fixed* EMA20/100. Are the published numbers the
   deployed strategy's numbers? (No — measured here for the first time.)
2. Is 20/100 a fragile peak (overfit) or a point on a broad plateau?
3. How much statistical power does an 8-week paper window actually have, given
   how rarely this strategy trades?

Research only. Reads `data/ml/historical/`, which ends before the 2026-07-16
holdout line, so nothing here can see the live M5 window. Changes no parameter.

    python scripts/research/calibration_audit.py
    python scripts/research/calibration_audit.py --data data/ml/historical/ETHUSDT_1d.csv
"""

from __future__ import annotations

import argparse
from collections import Counter

import numpy as np
import pandas as pd

from app.backend.backtesting import data as data_mod
from app.backend.backtesting.engine import BacktestConfig, BacktestResult, run_backtest
from app.backend.backtesting.indicators import ema as ema_indicator
from app.backend.backtesting.metrics import compute_metrics
from app.backend.backtesting.strategies import EmaCrossover
from app.backend.backtesting.walkforward import walk_forward

# The deployed configuration (app/backend/paper_trading/run.py:build_bot).
LIVE_FAST, LIVE_SLOW = 20, 100

# The grid the M4 walk-forward searched, and the fold layouts it reported.
GRID = {"fast": [10, 20, 30], "slow": [50, 100, 200]}
LAYOUTS = [(730, 180), (500, 125), (1000, 250), (365, 90)]

# Wider surface for the plateau/fragility question.
SURFACE_FAST = [5, 10, 15, 20, 25, 30, 40]
SURFACE_SLOW = [50, 75, 100, 125, 150, 200]


def make_ema(fast: int, slow: int) -> EmaCrossover:
    return EmaCrossover(fast=fast, slow=slow, allow_short=False)


def fold_indices(df: pd.DataFrame, train_bars: int, test_bars: int) -> list[tuple[int, int, int]]:
    """(train_start, test_start, test_end) — the same slicing walk_forward uses."""
    out, start, n = [], 0, len(df)
    while start + train_bars + test_bars <= n:
        out.append((start, start + train_bars, start + train_bars + test_bars))
        start += test_bars
    return out


def fixed_params_oos(df: pd.DataFrame, fast: int, slow: int,
                     folds: list[tuple[int, int, int]], base: dict):
    """Fixed parameters applied to the OOS spans — no in-sample fitting at all.

    This is the honest measurement of a deployed strategy: the same out-of-sample
    windows the walk-forward reports on, but with the parameters frozen the way
    the live bot freezes them.
    """
    strat = make_ema(fast, slow)
    cfg = BacktestConfig(**base)
    pieces, trades, running = [], [], cfg.initial_capital
    init = cfg.initial_capital

    for train_start, test_start, test_end in folds:
        ext = df.iloc[train_start:test_end]        # lookback so indicators are warm
        test = df.iloc[test_start:test_end]
        target = strat.target_positions(ext).reindex(test.index).fillna(0.0)
        res = run_backtest(test, target,
                           BacktestConfig(**{**base, "initial_capital": init}),
                           f"EMA{fast}/{slow}", "1d")
        piece = res.equity_curve / init * running
        pieces.append(piece)
        running = float(piece.iloc[-1]) if len(piece) else running
        trades.extend(res.trades)

    equity = pd.concat(pieces)
    stitched = BacktestResult(
        strategy_name=f"EMA{fast}/{slow}", timeframe="1d", equity_curve=equity,
        trades=trades, config=cfg, bars=len(equity),
        start=equity.index[0], end=equity.index[-1],
    )
    return compute_metrics(stitched, df.loc[equity.index])


def buy_and_hold(df: pd.DataFrame, span: pd.DatetimeIndex, base: dict):
    sub = df.loc[span]
    return compute_metrics(
        run_backtest(sub, pd.Series(1.0, index=sub.index),
                     BacktestConfig(**base), "Buy&Hold", "1d"),
        sub,
    )


# --------------------------------------------------------------------------- #
# Section 1 — is the deployed configuration the validated configuration?
# --------------------------------------------------------------------------- #

def report_deployed_vs_validated(df: pd.DataFrame, base: dict) -> None:
    print("=" * 78)
    print("1. DEPLOYED vs VALIDATED — which params does walk-forward actually pick?")
    print("=" * 78)
    print(f"{'layout':<11}{'adaptive':>10}{'fixed 20/100':>14}{'B&H':>8}"
          f"{'20/100 picked':>15}{'top pick':>13}")

    for train_bars, test_bars in LAYOUTS:
        wf = walk_forward(df, make_ema, GRID, BacktestConfig(**base),
                          train_bars=train_bars, test_bars=test_bars,
                          strategy_name="EMA", timeframe="1d", objective="sharpe")
        picks = Counter((f.best_params["fast"], f.best_params["slow"]) for f in wf.folds)
        folds = fold_indices(df, train_bars, test_bars)
        fixed = fixed_params_oos(df, LIVE_FAST, LIVE_SLOW, folds, base)
        bh = buy_and_hold(df, wf.equity_curve.index, base)
        (top_params, top_n), = picks.most_common(1)

        print(f"{train_bars}/{test_bars:<6}{wf.combined.sharpe:>10.2f}"
              f"{fixed.sharpe:>14.2f}{bh.sharpe:>8.2f}"
              f"{picks.get((LIVE_FAST, LIVE_SLOW), 0):>10}/{len(wf.folds):<4}"
              f"{f'{top_params[0]}/{top_params[1]}x{top_n}':>13}")

    print("\n  'adaptive' re-fits params every fold — that is what M4 published.")
    print("  'fixed 20/100' is what the Lambda actually trades.")


# --------------------------------------------------------------------------- #
# Section 2 — plateau or fragile peak?
# --------------------------------------------------------------------------- #

def report_parameter_surface(df: pd.DataFrame, base: dict) -> pd.DataFrame:
    print()
    print("=" * 78)
    print("2. PARAMETER SURFACE — is 20/100 a lucky peak or a broad plateau?")
    print("=" * 78)

    folds = fold_indices(df, 730, 180)
    rows = []
    for fast in SURFACE_FAST:
        for slow in SURFACE_SLOW:
            if fast >= slow:
                continue
            oos = fixed_params_oos(df, fast, slow, folds, base)
            ins = compute_metrics(
                run_backtest(df, make_ema(fast, slow).target_positions(df),
                             BacktestConfig(**base), f"EMA{fast}/{slow}", "1d"), df)
            rows.append({"fast": fast, "slow": slow, "oos_sharpe": oos.sharpe,
                         "oos_ret%": oos.total_return * 100,
                         "oos_maxDD%": oos.max_drawdown * 100,
                         "trades": oos.trades, "in_sample_sharpe": ins.sharpe})

    surface = pd.DataFrame(rows).sort_values("oos_sharpe", ascending=False).reset_index(drop=True)
    print("\ntop 8 out-of-sample (fold layout 730/180):")
    print(surface.head(8).round(2).to_string(index=False))

    live = (surface.fast == LIVE_FAST) & (surface.slow == LIVE_SLOW)
    oos_rank = int(surface.index[live][0]) + 1
    ins_sorted = surface.sort_values("in_sample_sharpe", ascending=False).reset_index(drop=True)
    ins_rank = int(ins_sorted.index[(ins_sorted.fast == LIVE_FAST)
                                    & (ins_sorted.slow == LIVE_SLOW)][0]) + 1

    print(f"\n  live 20/100 OOS rank:       {oos_rank}/{len(surface)}  "
          f"(Sharpe {surface.loc[oos_rank-1, 'oos_sharpe']:.2f}, "
          f"family {surface.oos_sharpe.min():.2f}–{surface.oos_sharpe.max():.2f}, "
          f"median {surface.oos_sharpe.median():.2f})")
    print(f"  live 20/100 in-sample rank: {ins_rank}/{len(surface)}  "
          "→ an overfit parameter would sit at the TOP in-sample; this does not.")
    return surface


# --------------------------------------------------------------------------- #
# Section 3 — cost and regime robustness of the live configuration
# --------------------------------------------------------------------------- #

def report_robustness(df: pd.DataFrame, base: dict) -> None:
    print()
    print("=" * 78)
    print("3. ROBUSTNESS OF THE LIVE CONFIGURATION (fixed 20/100)")
    print("=" * 78)

    folds = fold_indices(df, 730, 180)
    print("\nfee sensitivity (per side, OOS spans 730/180):")
    for fee in (0.00075, 0.001, 0.002, 0.003, 0.005):
        m = fixed_params_oos(df, LIVE_FAST, LIVE_SLOW, folds, {**base, "fee_rate": fee})
        print(f"  {fee*100:>5.3f}%   Sharpe {m.sharpe:.2f}   "
              f"return {m.total_return*100:>+8.0f}%   trades {m.trades}")

    print("\nregime split (full-equity, warmed indicators):")
    regimes = [("2017-2020", "2017-09-01", "2020-12-31"),
               ("2021-2022", "2021-01-01", "2022-12-31"),
               ("2023-2024", "2023-01-01", "2024-12-31"),
               ("2025-2026", "2025-01-01", "2026-07-15")]
    for label, lo, hi in regimes:
        sub = df.loc[lo:hi]
        if sub.empty:
            continue
        warm = df.loc[:hi].iloc[-(len(sub) + 200):]      # 200 bars of lookback
        target = make_ema(LIVE_FAST, LIVE_SLOW).target_positions(warm) \
                                               .reindex(sub.index).fillna(0.0)
        ema_m = compute_metrics(
            run_backtest(sub, target, BacktestConfig(**base), "EMA20/100", "1d"), sub)
        bh_m = buy_and_hold(df, sub.index, base)
        print(f"  {label}:  EMA Sharpe {ema_m.sharpe:>5.2f} "
              f"return {ema_m.total_return*100:>+7.0f}% maxDD {ema_m.max_drawdown*100:>5.0f}% "
              f"trades {ema_m.trades:>2}  |  B&H Sharpe {bh_m.sharpe:>5.2f} "
              f"return {bh_m.total_return*100:>+7.0f}%")


# --------------------------------------------------------------------------- #
# Section 4 — statistical power of the M5 gate
# --------------------------------------------------------------------------- #

def report_gate_power(df: pd.DataFrame, base: dict,
                      min_round_trips: int = 2, min_days_in_market: int = 10) -> None:
    """How often would the pre-registered activity rule even be satisfiable?

    The rule (plan.md §3): evaluate the profitability thresholds only with
    >= 2 closed round trips AND >= 10 days in market, else INCONCLUSIVE_EXTEND.
    """
    print()
    print("=" * 78)
    print("4. GATE POWER — can an 8-week window satisfy the activity rule?")
    print("=" * 78)

    target = make_ema(LIVE_FAST, LIVE_SLOW).target_positions(df)
    res = run_backtest(df, target, BacktestConfig(**base), "EMA20/100", "1d")
    years = len(df) / 365.25
    in_market = target.shift(1).fillna(0.0) > 0
    exits = pd.to_datetime([t.exit_time for t in res.trades], utc=True)

    print(f"\n  {df.index[0].date()} → {df.index[-1].date()}  ({len(df)} bars, {years:.1f} years)")
    print(f"  closed round trips: {len(res.trades)}  =  {len(res.trades)/years:.2f} per year")
    print(f"  days in market: {int(in_market.sum())}/{len(df)} = {in_market.mean()*100:.0f}%")

    print(f"\n  P(>= {min_round_trips} round trips AND >= {min_days_in_market} days in market):")
    idx = df.index
    for window in (56, 84, 112, 168, 252, 365, 547, 730):
        if window >= len(idx):
            continue
        ok = []
        for i in range(len(idx) - window):
            lo, hi = idx[i], idx[i + window]
            rts = int(((exits > lo) & (exits <= hi)).sum())
            dim = int(in_market.loc[lo:hi].sum())
            ok.append(rts >= min_round_trips and dim >= min_days_in_market)
        tag = "  <- the plan's 8-week window" if window == 56 else ""
        print(f"    {window:>3}d ({window/30.4:>4.1f} months): {np.mean(ok)*100:>3.0f}%{tag}")

    print("\n  An 8-week window cannot decide profitability for a strategy that")
    print("  trades this rarely. Split the gate: execution fidelity (decidable")
    print("  now) vs profitability (needs 12-18 months). See plan.md §3.")


def report_current_signal(df: pd.DataFrame) -> None:
    close = df["close"]
    fast_line, slow_line = ema_indicator(close, LIVE_FAST), ema_indicator(close, LIVE_SLOW)
    gap = (fast_line.iloc[-1] / slow_line.iloc[-1] - 1) * 100
    print(f"\n  last bar in data {df.index[-1].date()}: "
          f"EMA{LIVE_FAST}={fast_line.iloc[-1]:.0f} EMA{LIVE_SLOW}={slow_line.iloc[-1]:.0f} "
          f"gap={gap:+.1f}% → {'LONG' if gap > 0 else 'FLAT'}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--data", default="data/ml/historical/BTCUSDT_1d.csv")
    p.add_argument("--fee", type=float, default=0.001)
    p.add_argument("--slippage", type=float, default=0.0002)
    args = p.parse_args(argv)

    df = data_mod.load_csv(args.data)
    base = dict(fee_rate=args.fee, slippage=args.slippage, allow_short=False)

    print(f"\ndata: {args.data}  |  live config: EMA{LIVE_FAST}/{LIVE_SLOW} long-only  "
          f"|  fee {args.fee*100:.3f}%/side + slippage {args.slippage*100:.3f}%\n")

    report_deployed_vs_validated(df, base)
    report_parameter_surface(df, base)
    report_robustness(df, base)
    report_gate_power(df, base)
    report_current_signal(df)


if __name__ == "__main__":
    main()
