"""Challenger #11: the live EMA20/100 rule run on a basket of large coins.

Pre-registered in ``docs/PORTFOLIO_DESIGN_2026-09-16.md`` (committed before this
file ran). Nothing about any single trade changes: each coin gets an equal share
of capital and its own long/flat EMA20/100 sleeve, never rebalanced, and the
portfolio is the sum of the sleeves. The question is only whether breadth buys a
shallower drawdown without giving up much Sharpe.

    PYTHONPATH=. .venv/bin/python scripts/research/portfolio_study.py
"""

from __future__ import annotations

import hashlib
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from app.backend.backtesting.data import load_csv  # noqa: E402
from app.backend.backtesting.engine import BacktestConfig, run_backtest  # noqa: E402
from app.backend.backtesting.metrics import _max_drawdown, _sharpe  # noqa: E402
from app.backend.backtesting.strategies import EmaCrossover  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "ml" / "historical"
DESIGN = ROOT / "docs" / "PORTFOLIO_DESIGN_2026-09-16.md"
HOLDOUT = pd.Timestamp("2026-07-16", tz="UTC")

U8 = ["BTC", "ETH", "BNB", "XRP", "LTC", "ADA", "DOGE", "SOL"]
U6 = ["BTC", "ETH", "BNB", "XRP", "LTC", "ADA"]
FEES = [0.001, 0.002]
SLIPPAGE = 0.0002
WARMUP = 100
CAPITAL = 10_000.0
PPY = 365.0
DD_MARGIN = 0.05
SHARPE_SLACK = 0.10


def load(coin: str) -> pd.DataFrame:
    df = load_csv(str(DATA / f"{coin}USDT_1d.csv"))
    return df[df.index < HOLDOUT]


def span_for(frames: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    start = max(f.index[WARMUP] for f in frames.values())
    end = min(f.index[-1] for f in frames.values())
    idx = frames["BTC"].loc[start:end].index
    for coin, f in frames.items():
        sub = f.loc[start:end].index
        if not sub.equals(idx):
            raise SystemExit(f"{coin}: calendar differs from BTC inside the span "
                             f"({len(sub)} vs {len(idx)} bars) — no test")
    return idx


def sleeve(frame: pd.DataFrame, span: pd.DatetimeIndex, fee: float, capital: float,
           hold: bool = False) -> tuple[pd.Series, int]:
    history = frame.loc[:span[-1]]
    sub = frame.loc[span]
    if hold:
        target = pd.Series(1, index=sub.index)
    else:
        target = EmaCrossover(fast=20, slow=100, allow_short=False) \
            .target_positions(history).reindex(sub.index).fillna(0).astype(int)
    cfg = BacktestConfig(fee_rate=fee, slippage=SLIPPAGE, initial_capital=capital,
                         allow_short=False)
    res = run_backtest(sub, target, cfg, "sleeve", "1d")
    return res.equity_curve, len(res.trades)


def longest_underwater_days(equity: pd.Series) -> int:
    under = equity < equity.cummax()
    longest = run = 0
    for flag in under:
        run = run + 1 if flag else 0
        longest = max(longest, run)
    return int(longest)


def stats(equity: pd.Series) -> dict:
    return {"sharpe": _sharpe(equity, PPY), "max_dd": _max_drawdown(equity),
            "ret": float(equity.iloc[-1] / equity.iloc[0] - 1.0),
            "underwater_days": longest_underwater_days(equity)}


def halves(span: pd.DatetimeIndex) -> list[pd.DatetimeIndex]:
    mid = span[0] + (span[-1] - span[0]) / 2
    return [span[span < mid], span[span >= mid]]


def evaluate_universe(name: str, coins: list[str], frames: dict[str, pd.DataFrame]) -> dict:
    span = span_for({c: frames[c] for c in coins})
    out = {"name": name, "coins": coins, "start": span[0].date(), "end": span[-1].date(),
           "bars": len(span), "fees": {}}
    for fee in FEES:
        sleeves, trades = {}, 0
        for coin in coins:
            eq, n = sleeve(frames[coin], span, fee, CAPITAL / len(coins))
            sleeves[coin] = eq
            trades += n
        portfolio = sum(sleeves.values())
        btc_ema, btc_trades = sleeve(frames["BTC"], span, fee, CAPITAL)
        # Costs are proportional, so a sleeve scales linearly with its capital.
        # If this fails, the portfolio arithmetic below is not what it claims.
        np.testing.assert_allclose(sleeves["BTC"].to_numpy() * len(coins),
                                   btc_ema.to_numpy(), rtol=1e-9)
        btc_hold, _ = sleeve(frames["BTC"], span, fee, CAPITAL, hold=True)
        basket_hold = sum(sleeve(frames[c], span, fee, CAPITAL / len(coins), hold=True)[0]
                          for c in coins)

        halves_dd = []
        for part in halves(span):
            halves_dd.append({"from": part[0].date(), "to": part[-1].date(),
                              "portfolio": _max_drawdown(portfolio.loc[part]),
                              "btc_ema": _max_drawdown(btc_ema.loc[part])})

        leave_one_out = {}
        for coin in coins:
            rest = sum(eq for c, eq in sleeves.items() if c != coin) * len(coins) / (len(coins) - 1)
            leave_one_out[coin] = _max_drawdown(rest)

        out["fees"][fee] = {
            "portfolio": {**stats(portfolio), "trades": trades},
            "btc_ema": {**stats(btc_ema), "trades": btc_trades},
            "btc_hold": stats(btc_hold),
            "basket_hold": stats(basket_hold),
            "halves": halves_dd,
            "leave_one_out_dd": leave_one_out,
            "sleeves": {c: stats(eq) for c, eq in sleeves.items()},
        }
    return out


def verdict(results: list[dict]) -> dict:
    checks = {}
    for r in results:
        name = r["name"]
        h1 = []
        for fee in FEES:
            f = r["fees"][fee]
            h1.append(f["portfolio"]["max_dd"] - f["btc_ema"]["max_dd"] >= DD_MARGIN)
            h1.extend(h["portfolio"] - h["btc_ema"] >= DD_MARGIN for h in f["halves"])
        h2 = all(r["fees"][fee]["portfolio"]["sharpe"]
                 >= r["fees"][fee]["btc_ema"]["sharpe"] - SHARPE_SLACK for fee in FEES)
        f1 = r["fees"][0.001]
        h3 = all(dd - f1["btc_ema"]["max_dd"] >= DD_MARGIN
                 for dd in f1["leave_one_out_dd"].values())
        h4 = f1["portfolio"]["sharpe"] > f1["basket_hold"]["sharpe"]
        checks[name] = {"H1": all(h1), "H2": h2, "H3": h3, "H4": h4}
    accepted = all(all(c.values()) for c in checks.values())
    return {"checks": checks, "accepted": accepted}


def pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def main() -> int:
    digest = hashlib.sha256(DESIGN.read_bytes()).hexdigest()
    print(f"design: {DESIGN.name}  sha256 {digest}")
    frames = {c: load(c) for c in U8}
    results = [evaluate_universe("U8", U8, frames), evaluate_universe("U6", U6, frames)]

    for r in results:
        print(f"\n=== {r['name']} {'+'.join(r['coins'])}: {r['start']} → {r['end']} "
              f"({r['bars']} days) ===")
        for fee in FEES:
            f = r["fees"][fee]
            print(f"\n fee {fee*100:.1f}%{'':>14}{'Sharpe':>8}{'maxDD':>9}{'return':>12}"
                  f"{'underwater':>12}{'trades':>8}")
            for key, label in (("portfolio", "portfolio EMA"), ("btc_ema", "BTC-EMA (live)"),
                               ("btc_hold", "BTC hold"), ("basket_hold", "basket hold")):
                s = f[key]
                print(f"  {label:<20}{s['sharpe']:>8.2f}{s['max_dd']*100:>8.1f}%"
                      f"{pct(s['ret']):>12}{s['underwater_days']:>10} d"
                      f"{s.get('trades', ''):>8}")
            for h in f["halves"]:
                print(f"  half {h['from']} → {h['to']}: maxDD portfolio "
                      f"{h['portfolio']*100:.1f}% vs BTC-EMA {h['btc_ema']*100:.1f}% "
                      f"(margin {(h['portfolio'] - h['btc_ema'])*100:+.1f} pp)")
            if fee == 0.001:
                print("  leave-one-out maxDD: " + ", ".join(
                    f"-{c} {dd*100:.1f}%" for c, dd in f["leave_one_out_dd"].items()))
                print("  sleeves (Sharpe / maxDD): " + ", ".join(
                    f"{c} {s['sharpe']:.2f}/{s['max_dd']*100:.0f}%"
                    for c, s in f["sleeves"].items()))

    v = verdict(results)
    print("\n=== decision (pre-registered H1-H4, both universes) ===")
    for name, c in v["checks"].items():
        print(f"  {name}: " + "  ".join(f"{k} {'pass' if ok else 'FAIL'}" for k, ok in c.items()))
    print(f"\nVERDICT: {'ACCEPT' if v['accepted'] else 'REJECT'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
