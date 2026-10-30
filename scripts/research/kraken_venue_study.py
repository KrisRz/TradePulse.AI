"""Is the 1d bot viable on Kraken, priced in GBP, at Kraken's fees?

Implements docs/KRAKEN_VENUE_DESIGN_2026-10-30.md exactly (M1–M4 and the binding
decision rule R1–R4); prints the design's SHA-256 first so the run is tied to the
committed design.

Inputs (the network ones are fetched into --cache once and reused):
- data/ml/historical/BTCUSDT_1d.csv, pre-holdout only (< 2026-07-16);
- FRED DEXUSUK (USD per GBP), forward-filled over non-US-business days;
- Kraken public OHLC 1d for XBTGBP / XBTUSD (the API keeps the last 720 bars);
- Binance public klines 1d BTCUSDT (data-api.binance.vision, market data only);
- Kraken public Depth for XBTGBP, five snapshots one minute apart (M4, always live).

    PYTHONPATH=. .venv/bin/python scripts/research/kraken_venue_study.py --cache <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from app.backend.backtesting.data import load_csv  # noqa: E402
from app.backend.backtesting.strategies import EmaCrossover  # noqa: E402
from calibration_audit import (  # noqa: E402
    LAYOUTS, LIVE_FAST, LIVE_SLOW, buy_and_hold, fixed_params_continuous, fold_indices,
)
from gate_b_power import max_drawdown  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
DESIGN = ROOT / "docs/KRAKEN_VENUE_DESIGN_2026-10-30.md"
HOLDOUT = pd.Timestamp("2026-07-16", tz="UTC")
FEES = (0.001, 0.004, 0.008)            # Binance taker, Kraken maker, Kraken taker
SLIPPAGE = 0.0002
STOP = 0.10                              # F7, as live
W = 0.5
WARMUP = 200                             # M3: bars skipped before comparing signals
URLS = {
    "dexusuk.csv": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXUSUK",
    "kraken_XBTGBP.json": "https://api.kraken.com/0/public/OHLC?pair=XBTGBP&interval=1440",
    "kraken_XBTUSD.json": "https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440",
    "binance_BTCUSDT.json": "https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=1000",
}


def fetch(cache: pathlib.Path, name: str) -> pathlib.Path:
    path = cache / name
    if not path.exists():
        req = urllib.request.Request(URLS[name], headers={"User-Agent": "tradepulse-research"})
        path.write_bytes(urllib.request.urlopen(req, timeout=30).read())
    return path


def fx_usd_per_gbp(cache: pathlib.Path) -> pd.Series:
    fx = pd.read_csv(fetch(cache, "dexusuk.csv"), na_values=".")
    fx = fx.set_index(pd.to_datetime(fx["observation_date"], utc=True))["DEXUSUK"].dropna()
    return fx


def in_gbp(df: pd.DataFrame, fx: pd.Series) -> pd.DataFrame:
    rate = fx.reindex(fx.index.union(df.index)).ffill().reindex(df.index)
    out = df.copy()
    for col in ("open", "high", "low", "close"):
        out[col] = df[col] / rate
    return out.dropna(subset=["close"])


def kraken_ohlc(cache: pathlib.Path, pair: str) -> pd.DataFrame:
    raw = json.loads(fetch(cache, f"kraken_{pair}.json").read_text())
    rows = next(v for k, v in raw["result"].items() if k != "last")
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "vwap", "volume", "count"])
    df = df.set_index(pd.to_datetime(df["t"], unit="s", utc=True))
    return df[["open", "high", "low", "close", "volume"]].astype(float).iloc[:-1]  # last bar is open


def binance_klines(cache: pathlib.Path) -> pd.DataFrame:
    rows = json.loads(fetch(cache, "binance_BTCUSDT.json").read_text())
    df = pd.DataFrame([r[:6] for r in rows], columns=["t", "open", "high", "low", "close", "volume"])
    df = df.set_index(pd.to_datetime(df["t"], unit="ms", utc=True))
    return df[["open", "high", "low", "close", "volume"]].astype(float).iloc[:-1]


def signal(df: pd.DataFrame) -> pd.Series:
    return EmaCrossover(LIVE_FAST, LIVE_SLOW, allow_short=False).target_positions(df)


# --------------------------------------------------------------------------- #

def m1(df_usd: pd.DataFrame, df_gbp: pd.DataFrame) -> int:
    print("\nM1 — continuous OOS per layout, EMA20/100 + F7 vs buy & hold (Sharpe | maxDD)")
    wins_at_08 = 0
    for label, df in (("GBP", df_gbp), ("USD", df_usd)):
        for fee in FEES:
            base = dict(fee_rate=fee, slippage=SLIPPAGE, allow_short=False, stop_loss_pct=STOP)
            cells, wins = [], 0
            for train, test in LAYOUTS:
                folds = fold_indices(df, train, test)
                s = fixed_params_continuous(df, LIVE_FAST, LIVE_SLOW, folds, base)
                span = df.index[folds[0][1]:folds[-1][2]]
                h = buy_and_hold(df, span, {**base, "stop_loss_pct": None})
                wins += s.sharpe >= h.sharpe
                cells.append(f"{train}/{test}: {s.sharpe:.2f} {s.max_drawdown:.0%} vs {h.sharpe:.2f} {h.max_drawdown:.0%}")
            print(f"  {label} fee {fee:.2%}: wins {wins}/4 | " + " | ".join(cells))
            if label == "GBP" and fee == 0.008:
                wins_at_08 = wins
    return wins_at_08


def daily_returns(df: pd.DataFrame, fee: float) -> np.ndarray:
    from app.backend.backtesting.engine import BacktestConfig, run_backtest
    cfg = BacktestConfig(fee_rate=fee, slippage=SLIPPAGE, allow_short=False, stop_loss_pct=STOP)
    eq = run_backtest(df, signal(df), cfg, "live", "1d").equity_curve
    r = eq.pct_change().fillna(0.0)
    return r[r.index >= "2018-01-01"].to_numpy()


def m2(df_gbp: pd.DataFrame) -> tuple[float, float]:
    print("\nM2 — account = 0.5 × strategy + 0.5 × cash at 0%, GBP, fee 0.80%")
    x = W * daily_returns(df_gbp, 0.008)
    print(f"  full sample from 2018: maxDD {max_drawdown(x):.1%}, "
          f"CAGR {np.prod(1 + x) ** (365 / len(x)) - 1:+.1%}")
    share = {}
    for win in (365, 730):
        dds = np.array([max_drawdown(x[s:s + win]) for s in range(0, len(x) - win, 7)])
        share[win] = float(np.mean(dds >= -0.25))
        print(f"  {win}d windows ({len(dds)}): DD<=25% in {share[win]:.0%}, median DD {np.median(dds):.1%}")
    return share[365], share[730]


def agreement(a: pd.DataFrame, b: pd.DataFrame, name: str) -> float:
    idx = a.index.intersection(b.index)
    sa, sb = signal(a.loc[idx]).iloc[WARMUP:], signal(b.loc[idx]).iloc[WARMUP:]
    ra, rb = a.loc[idx, "close"].pct_change(), b.loc[idx, "close"].pct_change()
    diff_bps = (a.loc[idx, "close"] / b.loc[idx, "close"] - 1).abs() * 1e4
    agree = float((sa == sb).mean())
    print(f"  {name}: {len(idx)} common days, corr(returns) {ra.corr(rb):.4f}, "
          f"median |close diff| {diff_bps.median():.1f} bps, "
          f"signal agreement {agree:.1%} over {len(sa)} days (after {WARMUP} warm-up)")
    return agree


def m3(cache: pathlib.Path, fx: pd.Series) -> float:
    print("\nM3 — data fidelity over Kraken's last 720 days")
    k_gbp, k_usd, b_usd = kraken_ohlc(cache, "XBTGBP"), kraken_ohlc(cache, "XBTUSD"), binance_klines(cache)
    print(f"  FX last observation {fx.index[-1].date()} (forward-filled after it)")
    a1 = agreement(k_gbp, in_gbp(b_usd, fx), "Kraken XBTGBP vs Binance BTCUSDT / DEXUSUK")
    a2 = agreement(k_usd, b_usd, "Kraken XBTUSD vs Binance BTCUSDT")
    return min(a1, a2)


def m4() -> float:
    print("\nM4 — Kraken XBTGBP book: buy cost vs mid (half spread + walk)")
    costs = []
    for i in range(5):
        req = urllib.request.Request("https://api.kraken.com/0/public/Depth?pair=XBTGBP&count=200",
                                     headers={"User-Agent": "tradepulse-research"})
        book = next(iter(json.loads(urllib.request.urlopen(req, timeout=30).read())["result"].values()))
        asks = [(float(p), float(v)) for p, v, _ in book["asks"]]
        bid = float(book["bids"][0][0])
        mid = (asks[0][0] + bid) / 2
        row = [f"spread {(asks[0][0] - bid) / mid * 1e4:.2f} bps"]
        for gbp in (100, 1000):
            left, qty = gbp, 0.0
            for price, vol in asks:
                take = min(left, price * vol)
                qty, left = qty + take / price, left - take
                if left <= 0:
                    break
            cost = gbp / qty / mid - 1
            row.append(f"£{gbp}: {cost * 1e4:.2f} bps")
            if gbp == 100:
                costs.append(cost)
        print(f"  snapshot {i + 1}: " + ", ".join(row))
        if i < 4:
            time.sleep(60)
    return float(np.median(costs))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cache", required=True, type=pathlib.Path)
    p.add_argument("--skip-m4", action="store_true")
    args = p.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    print(f"design {DESIGN.name} sha256 {hashlib.sha256(DESIGN.read_bytes()).hexdigest()}")

    fx = fx_usd_per_gbp(args.cache)
    df_usd = load_csv(ROOT / "data/ml/historical/BTCUSDT_1d.csv")
    df_usd = df_usd[df_usd.index < HOLDOUT]
    df_gbp = in_gbp(df_usd, fx)
    print(f"BTCUSDT 1d {df_usd.index[0].date()}..{df_usd.index[-1].date()} ({len(df_usd)} bars), "
          f"GBP {len(df_gbp)} bars")

    r1 = m1(df_usd, df_gbp)
    r2 = m2(df_gbp)
    r3 = m3(args.cache, fx)
    r4 = None if args.skip_m4 else m4()

    print("\nDECISION (design rule)")
    print(f"  R1 Sharpe >= B&H at 0.80% in >=3/4 layouts (GBP): {r1}/4 -> {'PASS' if r1 >= 3 else 'FAIL'}")
    print(f"  R2 account DD<=25%: 730d {r2[1]:.0%} (>=75%), 365d {r2[0]:.0%} (>=90%) -> "
          f"{'PASS' if r2[1] >= 0.75 and r2[0] >= 0.90 else 'FAIL'}")
    print(f"  R3 signal agreement >=95%: {r3:.1%} -> {'PASS' if r3 >= 0.95 else 'FAIL'}")
    if r4 is not None:
        print(f"  R4 median buy cost for £100 <=0.10%: {r4:.3%} -> {'PASS' if r4 <= 0.001 else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
