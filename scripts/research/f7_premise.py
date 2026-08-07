"""F7 premise measurement: how often would position-level risk controls fire?

Before building the stop-loss + daily-loss-limit (plan F7), measure — on
PRE-HOLDOUT data only (< 2026-07-16) — how often each candidate threshold
would have triggered on the validated EMA20/100 long-only strategy, and what
it would have done to the metrics. Thresholds for the live control are
pre-registered from THIS output, before the control exists.

Two stop semantics are measured, because they are not the same thing:
- intrabar (engine): low <= entry_fill*(1-x), filled AT the stop price —
  what a resting exchange stop order would approximate;
- bar-close (live 4h reality): the bot only sees closes every 4h, so it can
  only notice close <= entry_fill*(1-x) and exit at the NEXT opportunity.

Usage: python scripts/research/f7_premise.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.backend.backtesting.data import load_csv
from app.backend.backtesting.engine import BacktestConfig, run_backtest
from app.backend.backtesting.strategies import EmaCrossover

HOLDOUT = pd.Timestamp("2026-07-16", tz="UTC")
STOP_LEVELS = [0.05, 0.10, 0.15]
DAILY_LEVELS = [0.05, 0.10, 0.15]
BARS_PER_YEAR = {"1d": 365.0, "4h": 365.0 * 6}


def sharpe(equity: pd.Series, bars_per_year: float) -> float:
    rets = equity.pct_change().dropna()
    sd = rets.std(ddof=1)
    return float(rets.mean() / sd * np.sqrt(bars_per_year)) if sd > 0 else float("nan")


def max_dd(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1.0).min())


def analyze(path: str, timeframe: str) -> None:
    df = load_csv(path)
    df = df[df.index < HOLDOUT]
    strat = EmaCrossover(fast=20, slow=100, allow_short=False)
    target = strat.target_positions(df)
    base_cfg = BacktestConfig()
    base = run_backtest(df, target, base_cfg, "ema", timeframe)
    years = (df.index[-1] - df.index[0]).days / 365.25
    print(f"\n=== {path} ({timeframe}) — {len(df)} bars, {years:.1f}y, "
          f"{len(base.trades)} trades, Sharpe {sharpe(base.equity_curve, BARS_PER_YEAR[timeframe]):.2f}, "
          f"maxDD {max_dd(base.equity_curve)*100:.0f}% ===")

    # -- per-position adverse excursions (both semantics) ------------------- #
    print(f"{'stop':>6} | {'intrabar hits':>13} | {'close hits':>10} | "
          f"{'hits/yr':>7} | {'Sharpe(sl)':>10} | {'maxDD(sl)':>9} | {'trades':>6}")
    for sl in STOP_LEVELS:
        intrabar = closebar = 0
        for t in base.trades:
            pos = df.loc[t.entry_time:t.exit_time]
            stop_price = t.entry_price * (1.0 - sl)
            if (pos["low"] <= stop_price).any():
                intrabar += 1
            if (pos["close"] <= stop_price).any():
                closebar += 1
        cfg = BacktestConfig(stop_loss_pct=sl)
        res = run_backtest(df, target, cfg, "ema+sl", timeframe)
        print(f"{sl*100:5.0f}% | {intrabar:13d} | {closebar:10d} | "
              f"{intrabar/years:7.2f} | "
              f"{sharpe(res.equity_curve, BARS_PER_YEAR[timeframe]):10.2f} | "
              f"{max_dd(res.equity_curve)*100:8.0f}% | {len(res.trades):6d}")

    # -- daily (UTC) loss from day-start equity, while in position ---------- #
    eq = base.equity_curve
    day = eq.index.tz_convert("UTC").normalize()
    day_start = eq.groupby(day).transform("first")
    daily_dd = eq / day_start - 1.0
    worst_by_day = daily_dd.groupby(day).min()
    print(f"{'daily':>6} | {'days breached':>13} | {'per year':>8}")
    for y in DAILY_LEVELS:
        breached = int((worst_by_day <= -y).sum())
        print(f"{y*100:5.0f}% | {breached:13d} | {breached/years:8.2f}")


if __name__ == "__main__":
    analyze("data/ml/historical/BTCUSDT_1d.csv", "1d")
    analyze("data/ml/historical/BTCUSDT_4h.csv", "4h")
