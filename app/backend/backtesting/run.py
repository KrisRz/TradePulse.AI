"""CLI: run the rule-based strategies over historical data and print a report.

Examples
--------
    # One year of BTCUSDT at 1h, default costs
    python -m app.backend.backtesting.run \
        --data 'data/ml/historical/raw_files/BTCUSDT-1m-2021-*.csv' --timeframe 1h

    # Compare several timeframes to see the fee/timeframe trade-off
    python -m app.backend.backtesting.run \
        --data 'data/ml/historical/raw_files/BTCUSDT-1m-2021-*.csv' \
        --timeframe 15m,1h,4h --sl 0.01 --tp 0.02
"""

from __future__ import annotations

import argparse

import pandas as pd

from . import data as data_mod
from .engine import BacktestConfig, run_backtest
from .metrics import Metrics, compute_metrics
from .strategies import EmaCrossover, RsiMeanReversion


def build_strategies() -> list:
    return [
        EmaCrossover(fast=20, slow=50),
        RsiMeanReversion(period=14, oversold=30, overbought=70),
    ]


def _buy_hold_metrics(df: pd.DataFrame, cfg: BacktestConfig, timeframe: str) -> Metrics:
    target = pd.Series(1, index=df.index, dtype=float)
    # Buy & hold pays costs once, so use a fee-free single-entry config baseline.
    bh_cfg = BacktestConfig(
        fee_rate=cfg.fee_rate, slippage=cfg.slippage,
        initial_capital=cfg.initial_capital, allow_short=False,
    )
    res = run_backtest(df, target, bh_cfg, strategy_name="Buy&Hold", timeframe=timeframe)
    return compute_metrics(res, df)


def run_report(
    df: pd.DataFrame,
    timeframe: str,
    cfg: BacktestConfig,
) -> list[Metrics]:
    tf_df = data_mod.resample(df, timeframe) if timeframe != "1m" else df
    rows: list[Metrics] = [_buy_hold_metrics(tf_df, cfg, timeframe)]
    for strat in build_strategies():
        target = strat.target_positions(tf_df)
        res = run_backtest(tf_df, target, cfg, strategy_name=strat.name, timeframe=timeframe)
        rows.append(compute_metrics(res, tf_df))
    return rows


def _fmt_pct(x: float) -> str:
    if x == float("inf"):
        return "inf"
    return f"{x * 100:+.1f}%"


def print_table(rows: list[Metrics]) -> None:
    if not rows:
        print("No results.")
        return
    header = f"{rows[0].start[:10]} → {rows[0].end[:10]}  |  timeframe {rows[0].timeframe}  |  {rows[0].bars} bars"
    print(header)
    print("-" * len(header))
    cols = (
        f"{'strategy':<18}{'return':>10}{'CAGR':>9}{'Sharpe':>8}"
        f"{'maxDD':>9}{'win%':>7}{'PF':>7}{'trades':>8}{'fee drag':>10}"
    )
    print(cols)
    print("-" * len(cols))
    for m in rows:
        pf = "inf" if m.profit_factor == float("inf") else f"{m.profit_factor:.2f}"
        print(
            f"{m.strategy:<18}{_fmt_pct(m.total_return):>10}{_fmt_pct(m.cagr):>9}"
            f"{m.sharpe:>8.2f}{_fmt_pct(m.max_drawdown):>9}{m.win_rate * 100:>6.0f}%"
            f"{pf:>7}{m.trades:>8}{_fmt_pct(m.total_fees_return_drag):>10}"
        )
    print()


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Backtest rule-based strategies on OHLCV data.")
    p.add_argument("--data", required=True, help="CSV path or glob pattern")
    p.add_argument("--timeframe", default="1h", help="Comma-separated, e.g. '15m,1h,4h'")
    p.add_argument("--start", default=None, help="ISO date, inclusive")
    p.add_argument("--end", default=None, help="ISO date, inclusive")
    p.add_argument("--fee", type=float, default=0.001, help="Fee rate per side (0.001 = 0.1%%)")
    p.add_argument("--slippage", type=float, default=0.0002)
    p.add_argument("--sl", type=float, default=None, help="Stop-loss fraction, e.g. 0.01")
    p.add_argument("--tp", type=float, default=None, help="Take-profit fraction, e.g. 0.02")
    p.add_argument("--max-hold", type=int, default=None, help="Max bars to hold a position")
    p.add_argument("--capital", type=float, default=10_000.0)
    p.add_argument("--no-short", action="store_true", help="Long-only")
    args = p.parse_args(argv)

    raw = data_mod.load_glob(args.data) if any(ch in args.data for ch in "*?[") else data_mod.load_csv(args.data)
    raw = data_mod.slice_dates(raw, args.start, args.end)
    print(f"Loaded {len(raw):,} 1m bars: {raw.index.min()} → {raw.index.max()}\n")

    cfg = BacktestConfig(
        fee_rate=args.fee,
        slippage=args.slippage,
        initial_capital=args.capital,
        stop_loss_pct=args.sl,
        take_profit_pct=args.tp,
        max_hold_bars=args.max_hold,
        allow_short=not args.no_short,
    )

    for tf in [t.strip() for t in args.timeframe.split(",") if t.strip()]:
        rows = run_report(raw, tf, cfg)
        print_table(rows)


if __name__ == "__main__":
    main()
