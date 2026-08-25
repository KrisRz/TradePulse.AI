"""Challenger #9: does a trailing stop beat the plain EMA20/100 exit?

Pre-registered in ``docs/TRAILING_STOP_DESIGN_2026-08-25.md``. The decision rule
lives there and was fixed before this ran: a challenger is accepted only if it
beats baseline Sharpe on *both* timeframes across a contiguous run of at least
three adjacent parameter values. Anything else is a reject, and the whole grid
is printed either way.

Every one of the eight challengers measured so far changed the *entry* or the
*size*. This one changes the *exit*, which nothing has touched — the engine has
carried ``stop_loss_pct``/``take_profit_pct`` since the beginning and neither was
ever pointed at the live strategy.

Why this file re-implements the simulation loop instead of calling
``run_backtest``: the production engine's stop is anchored to the *entry* price
and never moves. A trailing stop has to ride the running peak, which is a
different state machine. Rather than widen the engine mid-M5 for a candidate
that will probably be rejected, the loop is mirrored here and pinned to the
engine's own cost helpers, so entry/exit fills and fees are the same arithmetic
in both places. ``--verify-baseline`` proves that: with trailing disabled this
loop must reproduce ``run_backtest`` trade for trade.

    python scripts/research/trailing_stop_study.py
    python scripts/research/trailing_stop_study.py --verify-baseline
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from app.backend.backtesting.costs import (  # noqa: E402
    apply_fee,
    entry_fill_price,
    exit_fill_price,
)
from app.backend.backtesting.engine import BacktestConfig, run_backtest  # noqa: E402
from app.backend.backtesting.indicators import atr  # noqa: E402
from app.backend.backtesting.metrics import _max_drawdown, _periods_per_year, _sharpe  # noqa: E402
from app.backend.backtesting.strategies.ema_crossover import EmaCrossover  # noqa: E402

# The M5 measurement window is holdout. Research never reads at or past it.
HOLDOUT = pd.Timestamp("2026-07-16", tz="UTC")
DATA = pathlib.Path(__file__).resolve().parents[2] / "data" / "ml" / "historical"

FEE = 0.001
SLIPPAGE = 0.0002
ATR_MULTIPLES = (2.0, 3.0, 4.0, 5.0, 6.0, 8.0)
PCT_STOPS = (0.10, 0.15, 0.20, 0.25, 0.30, 0.40)


def load(timeframe: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / f"BTCUSDT_{timeframe}.csv", parse_dates=["timestamp"])
    df = df.set_index("timestamp").sort_index()
    return df[df.index < HOLDOUT]


def simulate(
    df: pd.DataFrame,
    target: pd.Series,
    *,
    trail_atr: float | None = None,
    trail_pct: float | None = None,
    initial_capital: float = 10_000.0,
) -> tuple[pd.Series, list[dict]]:
    """Mirror of ``run_backtest`` with the stop anchored to the running peak.

    Returns the mark-to-market equity curve and the closed trades. With both
    trailing arguments ``None`` this is the engine's long-only path exactly.
    """
    o = df["open"].to_numpy(dtype=float)
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    tgt = target.reindex(df.index).fillna(0.0).round().astype(int).to_numpy()
    idx = df.index
    n = len(df)

    atr_arr = (
        atr(df["high"], df["low"], df["close"], 14).to_numpy(dtype=float)
        if trail_atr is not None
        else np.zeros(n)
    )

    realized = initial_capital
    equity_curve = np.empty(n, dtype=float)
    side = 0
    entry_fill = 0.0
    entry_equity = realized
    entry_i = 0
    equity_before_entry = realized
    blocked_side = 0
    pending = 0
    peak = 0.0            # running high watermark since entry, drives the stop
    trades: list[dict] = []

    def open_position(new_side: int, fill_price: float, i: int) -> None:
        nonlocal side, entry_fill, entry_equity, entry_i, equity_before_entry
        nonlocal realized, peak
        equity_before_entry = realized
        realized = apply_fee(realized, FEE)
        side = new_side
        entry_fill = entry_fill_price(fill_price, new_side, SLIPPAGE)
        entry_equity = realized
        entry_i = i
        peak = entry_fill

    def close_position(exit_price_raw: float, i: int, reason: str) -> None:
        nonlocal side, realized, blocked_side
        exit_fill = exit_fill_price(exit_price_raw, side, SLIPPAGE)
        gross = side * (exit_fill / entry_fill - 1.0)
        realized = apply_fee(entry_equity * (1.0 + gross), FEE)
        trades.append(
            {
                "entry_time": idx[entry_i],
                "exit_time": idx[i],
                "side": side,
                "entry_price": entry_fill,
                "exit_price": exit_fill,
                "gross_return": gross,
                "net_return": realized / equity_before_entry - 1.0,
                "bars_held": i - entry_i,
                "exit_reason": reason,
            }
        )
        blocked_side = side if reason in ("stop", "take_profit", "max_hold") else 0
        side = 0

    for i in range(n):
        # 1) Execute the target decided on the previous bar, at this bar's open.
        if pending != side:
            if side != 0 and pending != side:
                close_position(o[i], i, reason="signal")
            if pending != 0 and side == 0:
                open_position(pending, o[i], i)

        # 2) Trailing stop, intrabar. The peak is updated from this bar's high
        #    *before* testing the low, so a bar that makes a new high and then
        #    falls back is measured against the fresh peak - the pessimistic
        #    reading, matching the engine's "assume the stop" convention.
        if side == 1 and (trail_atr is not None or trail_pct is not None):
            peak = max(peak, high[i])
            if trail_atr is not None:
                a = atr_arr[i]
                stop_price = peak - trail_atr * a if np.isfinite(a) else None
            else:
                stop_price = peak * (1.0 - trail_pct)
            if stop_price is not None and low[i] <= stop_price:
                close_position(stop_price, i, reason="stop")

        # 3) Mark to market at this bar's close.
        if side != 0:
            equity_curve[i] = entry_equity * (1.0 + side * (close[i] / entry_fill - 1.0))
        else:
            equity_curve[i] = realized

        # 4) Decide the target for the next bar, honouring the re-entry block.
        want = tgt[i]
        if want < 0:
            want = 0                     # long-only, as live
        if want == 0:
            blocked_side = 0
        elif want == blocked_side:
            want = 0
        pending = want

    # Close whatever is still open at the end of the data, as the engine does.
    if side != 0:
        close_position(close[n - 1], n - 1, reason="end")
        equity_curve[n - 1] = realized

    return pd.Series(equity_curve, index=idx), trades


def score(equity: pd.Series, trades: list[dict], df: pd.DataFrame) -> dict:
    ppy = _periods_per_year(df.index)
    stops = sum(1 for t in trades if t["exit_reason"] == "stop")
    return {
        "sharpe": _sharpe(equity, ppy),
        "max_dd": _max_drawdown(equity),
        "total_return": equity.iloc[-1] / 10_000.0 - 1.0,
        "trades": len(trades),
        "stopped": stops,
    }


def verify_baseline() -> bool:
    """The mirrored loop must reproduce the production engine exactly."""
    ok = True
    for tf in ("1d", "4h"):
        df = load(tf)
        target = EmaCrossover(fast=20, slow=100, allow_short=False).target_positions(df)
        mine_eq, mine_trades = simulate(df, target)
        theirs = run_backtest(
            df,
            target,
            BacktestConfig(fee_rate=FEE, slippage=SLIPPAGE, allow_short=False),
            "EMA20/100",
            tf,
        )
        their_trades = theirs.trades_frame
        same_count = len(mine_trades) == len(their_trades)
        same_pnl = same_count and all(
            m["net_return"] == t                     # exact, not approximate
            for m, t in zip(mine_trades, their_trades["net_return"])
        )
        print(f"  {tf}: trades {len(mine_trades)} vs {len(their_trades)} "
              f"| identical net returns: {same_pnl}")
        ok = ok and same_count and same_pnl
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-baseline", action="store_true",
                    help="prove the mirrored loop equals the production engine")
    args = ap.parse_args()

    if args.verify_baseline:
        print("Verifying the mirrored loop against run_backtest (trailing off):")
        ok = verify_baseline()
        print("VERDICT:", "identical" if ok else "DIVERGED - results untrustworthy")
        return 0 if ok else 1

    results: dict[str, dict] = {}
    for tf in ("1d", "4h"):
        df = load(tf)
        target = EmaCrossover(fast=20, slow=100, allow_short=False).target_positions(df)

        base_eq, base_tr = simulate(df, target)
        base = score(base_eq, base_tr, df)
        results[tf] = {"baseline": base, "atr": {}, "pct": {}}

        print(f"\n===== BTCUSDT {tf} — EMA20/100 long-only, data < {HOLDOUT.date()} =====")
        print(f"{'variant':<22}{'Sharpe':>9}{'maxDD':>9}{'total':>11}"
              f"{'trades':>8}{'stopped':>9}")
        print(f"{'BASELINE (no stop)':<22}{base['sharpe']:>9.3f}{base['max_dd']:>9.1%}"
              f"{base['total_return']:>11.1%}{base['trades']:>8}{base['stopped']:>9}")

        for k in ATR_MULTIPLES:
            eq, tr = simulate(df, target, trail_atr=k)
            s = score(eq, tr, df)
            results[tf]["atr"][k] = s
            flag = "  <-- beats" if s["sharpe"] > base["sharpe"] else ""
            print(f"{'trail ' + str(k) + 'x ATR14':<22}{s['sharpe']:>9.3f}"
                  f"{s['max_dd']:>9.1%}{s['total_return']:>11.1%}"
                  f"{s['trades']:>8}{s['stopped']:>9}{flag}")

        for p in PCT_STOPS:
            eq, tr = simulate(df, target, trail_pct=p)
            s = score(eq, tr, df)
            results[tf]["pct"][p] = s
            flag = "  <-- beats" if s["sharpe"] > base["sharpe"] else ""
            print(f"{'trail ' + format(p, '.0%'):<22}{s['sharpe']:>9.3f}"
                  f"{s['max_dd']:>9.1%}{s['total_return']:>11.1%}"
                  f"{s['trades']:>8}{s['stopped']:>9}{flag}")

    # ---- the pre-registered decision rule, applied mechanically -------------
    print("\n" + "=" * 72)
    print("PRE-REGISTERED DECISION RULE")
    print("  accept only if: beats baseline Sharpe on BOTH timeframes,")
    print("                  on a contiguous run of >=3 adjacent parameter values")
    print("=" * 72)

    verdict_accept = False
    for family, grid in (("ATR", ATR_MULTIPLES), ("pct", PCT_STOPS)):
        key = "atr" if family == "ATR" else "pct"
        beats = {
            tf: [p for p in grid
                 if results[tf][key][p]["sharpe"] > results[tf]["baseline"]["sharpe"]]
            for tf in ("1d", "4h")
        }
        both = [p for p in grid if p in beats["1d"] and p in beats["4h"]]
        run = longest_run(both, grid)
        print(f"\n{family}: beats on 1d at {beats['1d'] or 'nothing'}")
        print(f"{'':>{len(family)}}  beats on 4h at {beats['4h'] or 'nothing'}")
        print(f"{'':>{len(family)}}  beats on BOTH at {both or 'nothing'} "
              f"-> longest contiguous run = {run}")
        if run >= 3:
            verdict_accept = True

    print("\nVERDICT:", "ACCEPT" if verdict_accept else "REJECT")
    return 0


def longest_run(hits: list, grid: tuple) -> int:
    """Longest streak of adjacent grid values that all appear in ``hits``."""
    best = cur = 0
    for p in grid:
        cur = cur + 1 if p in hits else 0
        best = max(best, cur)
    return best


if __name__ == "__main__":
    raise SystemExit(main())
