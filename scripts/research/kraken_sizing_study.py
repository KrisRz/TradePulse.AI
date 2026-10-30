"""How the bot should hold `w` of the account: entry-sized (A) or band-rebalanced (B).

Implements docs/KRAKEN_SIZING_DESIGN_2026-10-30.md exactly; prints the design's
SHA-256 first. Reuses the GBP price series and strategy of kraken_venue_study.py.

    PYTHONPATH=. .venv/bin/python scripts/research/kraken_sizing_study.py --cache <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from app.backend.backtesting.data import load_csv  # noqa: E402
from app.backend.backtesting.engine import BacktestConfig, run_backtest  # noqa: E402
from gate_b_power import max_drawdown  # noqa: E402
from kraken_venue_study import HOLDOUT, SLIPPAGE, STOP, fx_usd_per_gbp, in_gbp, signal  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
DESIGN = ROOT / "docs/KRAKEN_SIZING_DESIGN_2026-10-30.md"
FEE = 0.008
CAPITAL = 200.0
MIN_ORDER = 5.0
FAMILY_A = (0.5, 0.4, 0.3)
FAMILY_B = (0.05, 0.10, 0.15)
START = "2018-01-01"


def strategy_days(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    """Daily return of a fully invested strategy and the id of the trade each day
    belongs to (-1 when flat), from the engine's own trade list."""
    cfg = BacktestConfig(fee_rate=FEE, slippage=SLIPPAGE, allow_short=False, stop_loss_pct=STOP)
    res = run_backtest(df, signal(df), cfg, "live", "1d")
    eq = res.equity_curve
    ret = eq.pct_change().fillna(0.0)
    trade_id = pd.Series(-1, index=eq.index)
    for i, t in enumerate(res.trades):
        trade_id.loc[t.entry_time:t.exit_time] = i
    keep = eq.index >= START
    return ret[keep].to_numpy(), trade_id[keep].to_numpy(), eq.index[keep]


def account(ret: np.ndarray, tid: np.ndarray, w: float, band: float | None) -> tuple[np.ndarray, int, float]:
    cash, inv, fees, n = CAPITAL, 0.0, 0.0, 0
    out = np.empty(len(ret))
    for t in range(len(ret)):
        if tid[t] >= 0 and (t == 0 or tid[t] != tid[t - 1]):      # a new trade starts
            total = cash + inv
            inv, cash = w * total, total - w * total
        if tid[t] >= 0:
            inv *= 1 + ret[t]
        last_day = tid[t] >= 0 and (t + 1 == len(ret) or tid[t + 1] != tid[t])
        if band is not None and tid[t] >= 0 and not last_day:
            total = cash + inv
            if abs(inv / total - w) > band:
                d = w * total - inv
                if abs(d) >= MIN_ORDER:
                    fee = FEE * abs(d)
                    inv, cash, fees, n = inv + d, cash - d - fee, fees + fee, n + 1
        if last_day:                                                # exit fee is inside ret
            cash, inv = cash + inv, 0.0
        out[t] = cash + inv
    return out, n, fees


def report(name: str, eq: np.ndarray, n: int, fees: float) -> tuple[float, float]:
    x = np.diff(eq, prepend=CAPITAL) / np.concatenate(([CAPITAL], eq[:-1]))
    years = len(x) / 365
    share = {}
    cells = []
    for win in (365, 730):
        dds = np.array([max_drawdown(x[s:s + win]) for s in range(0, len(x) - win, 7)])
        share[win] = float(np.mean(dds >= -0.25))
        cells.append(f"{win}d DD<=25% {share[win]:.0%} (median {np.median(dds):.1%})")
    avg_eq = float(np.mean(eq))
    print(f"  {name}: maxDD {max_drawdown(x):.1%}, CAGR {(eq[-1] / CAPITAL) ** (1 / years) - 1:+.1%}, "
          + ", ".join(cells)
          + f", rebalances {n / years:.1f}/yr, rebalance cost {fees / years / avg_eq:.2%}/yr")
    return share[365], share[730]


def passes(s: tuple[float, float]) -> bool:
    return s[1] >= 0.75 and s[0] >= 0.90


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cache", required=True, type=pathlib.Path)
    args = p.parse_args()
    print(f"design {DESIGN.name} sha256 {hashlib.sha256(DESIGN.read_bytes()).hexdigest()}")
    df = load_csv(ROOT / "data/ml/historical/BTCUSDT_1d.csv")
    df = in_gbp(df[df.index < HOLDOUT], fx_usd_per_gbp(args.cache))
    ret, tid, idx = strategy_days(df)
    print(f"GBP 1d {idx[0].date()}..{idx[-1].date()}, {len(ret)} days, {tid.max() + 1} trades, fee {FEE:.2%}")

    print("\nFamily A — entry-sized, no rebalancing")
    a = {w: report(f"w={w}", *account(ret, tid, w, None)) for w in FAMILY_A}
    print("\nFamily B — w=0.5, rebalance when |share-0.5| > b (min order £5)")
    b = {band: report(f"b={band}", *account(ret, tid, 0.5, band)) for band in FAMILY_B}

    print("\nSELECTION (design rule)")
    a_pass = [w for w in FAMILY_A if passes(a[w])]
    b_pass = [band for band in FAMILY_B if passes(b[band])]
    if a_pass:
        print(f"  family A passes for w in {a_pass} -> CHOSEN: entry-sized w={max(a_pass)}")
    elif b_pass:
        print(f"  family A: none passes; family B passes for b in {b_pass} -> CHOSEN: w=0.5, band b={max(b_pass)}")
    else:
        print("  nothing passes -> no pilot in this form")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
