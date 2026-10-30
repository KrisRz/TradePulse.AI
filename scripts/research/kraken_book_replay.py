"""Does the REAL book, driven the way the bot drives it, keep R2?

docs/KRAKEN_SIZING_RESULTS_2026-10-30.md measured the band on the engine's equity
curve (fills at the next open, intrabar stop). The bot decides and trades at the
bar's close and applies F7 on closes. This replays ``PaperPortfolio`` itself
(exposure 0.5, band 0.15, £5 minimum, 0.80%) with the production F7 overlay over
the same GBP history, and reads R2 off its equity — the implementation, not the
model of it.

    PYTHONPATH=. .venv/bin/python scripts/research/kraken_book_replay.py --cache <dir>
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from app.backend.backtesting.data import load_csv  # noqa: E402
from app.backend.paper_trading import position_risk  # noqa: E402
from app.backend.paper_trading.portfolio import PaperPortfolio  # noqa: E402
from gate_b_power import max_drawdown  # noqa: E402
from kraken_venue_study import HOLDOUT, SLIPPAGE, fx_usd_per_gbp, in_gbp, signal  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
START = pd.Timestamp("2018-01-01", tz="UTC")


def replay(df, exposure: float, band: float | None) -> tuple[np.ndarray, PaperPortfolio]:
    book = PaperPortfolio(fee_rate=0.008, slippage=SLIPPAGE, initial_capital=200.0,
                          exposure=exposure, rebalance_band=band, min_rebalance=5.0)
    risk = position_risk.PositionRiskState()
    target = signal(df)
    equity = []
    for ts, price, tgt in zip(df.index, df["close"].to_numpy(float), target.to_numpy()):
        allowed = position_risk.apply(risk, int(tgt), book, price, str(ts))
        book.reconcile(allowed, price, str(ts))
        if ts >= START:
            equity.append(book.equity(price))
    return np.asarray(equity), book


def report(name: str, eq: np.ndarray, book: PaperPortfolio) -> None:
    x = np.diff(eq, prepend=eq[0]) / np.concatenate(([eq[0]], eq[:-1]))
    years = len(x) / 365
    cells = []
    share = {}
    for win in (365, 730):
        dds = np.array([max_drawdown(x[s:s + win]) for s in range(0, len(x) - win, 7)])
        share[win] = float(np.mean(dds >= -0.25))
        cells.append(f"{win}d DD<=25% {share[win]:.0%} (median {np.median(dds):.1%})")
    r2 = share[730] >= 0.75 and share[365] >= 0.90
    print(f"  {name}: maxDD {max_drawdown(x):.1%}, CAGR {(eq[-1] / eq[0]) ** (1 / years) - 1:+.1%}, "
          + ", ".join(cells) + f", trades {len(book.trades)}, rebalances {len(book.rebalances) / years:.1f}/yr"
          + f" -> R2 {'PASS' if r2 else 'FAIL'}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cache", required=True, type=pathlib.Path)
    args = p.parse_args()
    df = load_csv(ROOT / "data/ml/historical/BTCUSDT_1d.csv")
    df = in_gbp(df[df.index < HOLDOUT], fx_usd_per_gbp(args.cache))
    print(f"GBP 1d, book replay from {START}, bot semantics (close fills, F7 on closes), fee 0.80%")
    for name, w, b in (("full equity (today's bot)", 1.0, None),
                       ("w=0.5 at entry only", 0.5, None),
                       ("w=0.5, band 0.15 (pilot)", 0.5, 0.15)):
        report(name, *replay(df, w, b))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
