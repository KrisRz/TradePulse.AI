"""How often would Gate B pass the strategy it exists to judge?

Written 2026-09-16 for the addendum to docs/GATE_B_PREREGISTRATION_2026-09-05.md.
Two lenses, both on pre-holdout BTC 1d data:

1. Real rolling windows of the live configuration (production engine, EMA20/100
   long-only, F7 10% stop), started every 7 days — how often the gate's
   return-based criteria would have been met, for several drawdown caps.
2. A block bootstrap (20-day blocks) of three worlds — the strategy as good as its
   backtest, one no better than buy & hold, one with zero skill — to show how much
   each criterion actually tells them apart.

The activity rule and profit factor need trade structure and are not modelled;
the numbers are therefore an upper bound on how often the full gate passes.

    PYTHONPATH=. .venv/bin/python scripts/research/gate_b_power.py
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd
from scipy.stats import kurtosis, norm, skew

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from app.backend.backtesting.data import load_csv  # noqa: E402
from app.backend.backtesting.engine import BacktestConfig, run_backtest  # noqa: E402
from app.backend.backtesting.strategies import EmaCrossover  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
HOLDOUT = pd.Timestamp("2026-07-16", tz="UTC")
START = "2018-01-01"
CAPS = (0.25, 0.35, 0.50)
WINDOWS = (365, 730)
DRAWS = 3000


def max_drawdown(x: np.ndarray) -> float:
    eq = np.cumprod(1 + x)
    return float((eq / np.maximum.accumulate(eq) - 1).min())


def psr(x: np.ndarray) -> float:
    s = x.mean() / x.std(ddof=1)
    den = 1 - skew(x) * s + (kurtosis(x, fisher=False) - 1) / 4 * s * s
    return float(norm.cdf(s * np.sqrt(len(x) - 1) / np.sqrt(den))) if den > 0 else float("nan")


def sharpe(x: np.ndarray) -> float:
    return float(np.sqrt(365) * x.mean() / x.std(ddof=1))


def criteria(xs: np.ndarray, xb: np.ndarray, cap: float) -> tuple[bool, bool, bool]:
    base = bool(np.prod(1 + xs) > 1 and max_drawdown(xs) >= -cap)
    return base, base and psr(xs) >= 0.95, base and psr(xs) >= 0.95 and sharpe(xs) >= sharpe(xb)


def load() -> tuple[np.ndarray, np.ndarray]:
    df = load_csv(str(ROOT / "data/ml/historical/BTCUSDT_1d.csv"))
    df = df[df.index < HOLDOUT]
    target = EmaCrossover(20, 100, allow_short=False).target_positions(df)
    cfg = BacktestConfig(allow_short=False, stop_loss_pct=0.10)
    strat = run_backtest(df, target, cfg, "live", "1d").equity_curve.pct_change().fillna(0.0)
    hold = df["close"].pct_change().fillna(0.0)
    return strat[strat.index >= START].to_numpy(), hold[hold.index >= START].to_numpy()


def rolling(strat: np.ndarray, hold: np.ndarray) -> None:
    n = len(strat)
    print(f"live configuration: maxDD {max_drawdown(strat):.0%}, Sharpe {sharpe(strat):.2f}")
    for w in WINDOWS:
        starts = [s for s in range(0, n - w, 7) if strat[s:s + w].std() > 0]
        dds = [max_drawdown(strat[s:s + w]) for s in starts]
        cells = []
        for cap in CAPS:
            rows = [criteria(strat[s:s + w], hold[s:s + w], cap) for s in starts]
            base, b5, now = (np.mean([r[i] for r in rows]) for i in range(3))
            cells.append(f"cap {cap:.0%}: {base:.2f}/{b5:.2f}/{now:.2f}")
        print(f"  {w}d windows ({len(starts)}), median DD {np.median(dds):.0%} — "
              f"base / +B5 / +B5+B6: " + " | ".join(cells))


def bootstrap(strat: np.ndarray, hold: np.ndarray) -> None:
    rng = np.random.default_rng(11)
    target_sr = hold.mean() / hold.std(ddof=1)
    worlds = {
        "as good as the backtest": strat,
        "no better than buy & hold": strat - (strat.mean() - strat.std(ddof=1) * target_sr),
        "zero skill": strat - strat.mean(),
    }
    n = len(strat)
    for w in WINDOWS:
        print(f"  bootstrap {w}d, cap 25% — base / +B5 / +B5+B6 / B6 alone")
        for name, series in worlds.items():
            hits = np.zeros(4)
            for _ in range(DRAWS):
                starts = rng.integers(0, n, size=int(np.ceil(w / 20)))
                idx = np.concatenate([(np.arange(s, s + 20) % n) for s in starts])[:w]
                xs, xb = series[idx], hold[idx]
                base, b5, now = criteria(xs, xb, 0.25)
                hits += (base, b5, now, sharpe(xs) >= sharpe(xb))
            print(f"    {name:<26}" + " / ".join(f"{h / DRAWS:.2f}" for h in hits))


def main() -> int:
    strat, hold = load()
    rolling(strat, hold)
    bootstrap(strat, hold)
    return 0


if __name__ == "__main__":
    sys.exit(main())
