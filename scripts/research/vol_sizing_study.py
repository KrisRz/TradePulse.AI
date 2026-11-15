"""Candidate #12: position size scaled by volatility, with a no-trade band.

Implements docs/VOL_SIZING_DESIGN_2026-11-15.md exactly; prints the design's
SHA-256 first. Same account model, price series and strategy as the benchmark
(kraken_sizing_study.py: w=0.5, band 0.15), which it must reproduce bit for bit
at a constant target before any candidate number is printed.

    PYTHONPATH=. .venv/bin/python scripts/research/vol_sizing_study.py --cache <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import urllib.request

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from app.backend.backtesting.data import load_csv  # noqa: E402
from gate_b_power import max_drawdown, sharpe  # noqa: E402
from kraken_sizing_study import CAPITAL, FEE, MIN_ORDER, START, account, strategy_days  # noqa: E402
from kraken_venue_study import HOLDOUT, fx_usd_per_gbp, in_gbp  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
DESIGN = ROOT / "docs/VOL_SIZING_DESIGN_2026-11-15.md"
W_BASE, W_MIN, W_MAX = 0.5, 0.25, 0.65
MIN_HISTORY = 60
BANDS = (0.10, 0.15)
BENCH_BAND = 0.15
HALVES = (("2018-2021", "2018-01-01", "2022-01-01"), ("2022-2026", "2022-01-01", "2027-01-01"))
DVOL_URL = ("https://www.deribit.com/api/v2/public/get_volatility_index_data"
            "?currency=BTC&resolution=1D&start_timestamp=1609459200000&end_timestamp={end}")


def dvol(cache: pathlib.Path) -> pd.Series:
    """Daily close of Deribit's BTC DVOL index, paged backwards from the holdout."""
    path = cache / "deribit_dvol_btc_1d.json"
    if not path.exists():
        rows, end = [], int(HOLDOUT.timestamp() * 1000)
        while end:
            req = urllib.request.Request(DVOL_URL.format(end=end),
                                         headers={"User-Agent": "tradepulse-research"})
            result = json.loads(urllib.request.urlopen(req, timeout=30).read())["result"]
            rows = result["data"] + rows
            end = result.get("continuation")
        path.write_text(json.dumps(rows))
    rows = json.loads(path.read_text())
    s = pd.Series({pd.Timestamp(r[0], unit="ms", tz="UTC"): float(r[4]) for r in rows}).sort_index()
    return s[s.index < HOLDOUT]


def realized(close: pd.Series, days: int) -> pd.Series:
    return np.log(close).diff().rolling(days).std(ddof=1) * np.sqrt(365)


def target(sigma: pd.Series) -> pd.Series:
    """w_t, known after the close of day t: 0.5 x (expanding median) / sigma, clipped."""
    sigma = sigma.dropna()
    median = sigma.expanding(min_periods=MIN_HISTORY).median()
    return (W_BASE * median / sigma).clip(W_MIN, W_MAX).dropna()


def account_var(ret: np.ndarray, tid: np.ndarray, w_entry: np.ndarray, w_reb: np.ndarray,
                band: float) -> tuple[np.ndarray, int, float]:
    """kraken_sizing_study.account with a target that moves: w_entry[t] is the
    target known before day t, w_reb[t] the one known after its close."""
    cash, inv, fees, n = CAPITAL, 0.0, 0.0, 0
    out = np.empty(len(ret))
    for t in range(len(ret)):
        if tid[t] >= 0 and (t == 0 or tid[t] != tid[t - 1]):
            w = w_entry[t]
            total = cash + inv
            inv, cash = w * total, total - w * total
        if tid[t] >= 0:
            inv *= 1 + ret[t]
        last_day = tid[t] >= 0 and (t + 1 == len(ret) or tid[t + 1] != tid[t])
        if tid[t] >= 0 and not last_day:
            w = w_reb[t]
            total = cash + inv
            if abs(inv / total - w) > band:
                d = w * total - inv
                if abs(d) >= MIN_ORDER:
                    fee = FEE * abs(d)
                    inv, cash, fees, n = inv + d, cash - d - fee, fees + fee, n + 1
        if last_day:
            cash, inv = cash + inv, 0.0
        out[t] = cash + inv
    return out, n, fees


def stats(eq: np.ndarray, n: int, fees: float, idx: pd.DatetimeIndex) -> dict:
    x = np.diff(eq, prepend=CAPITAL) / np.concatenate(([CAPITAL], eq[:-1]))
    years = len(x) / 365
    out = {"maxdd": max_drawdown(x), "cagr": (eq[-1] / CAPITAL) ** (1 / years) - 1,
           "sharpe": sharpe(x), "reb": n / years, "cost": fees / years / float(np.mean(eq))}
    for win in (365, 730):
        dds = np.array([max_drawdown(x[s:s + win]) for s in range(0, len(x) - win, 7)])
        out[f"share{win}"] = float(np.mean(dds >= -0.25)) if len(dds) else float("nan")
        out[f"median{win}"] = float(np.median(dds)) if len(dds) else float("nan")
    for name, lo, hi in HALVES:
        part = x[(idx >= lo) & (idx < hi)]
        out[f"dd_{name}"] = max_drawdown(part) if len(part) else float("nan")
    return out


def line(name: str, s: dict, extra: str = "") -> None:
    print(f"  {name:<22} maxDD {s['maxdd']:.1%}  CAGR {s['cagr']:+.1%}  Sharpe {s['sharpe']:.2f}  "
          f"365d {s['share365']:.0%} (med {s['median365']:.1%})  730d {s['share730']:.0%} "
          f"(med {s['median730']:.1%})  reb {s['reb']:.1f}/yr cost {s['cost']:.2%}/yr  "
          f"halves {s['dd_2018-2021']:.1%} / {s['dd_2022-2026']:.1%}{extra}")


def rule(c: dict, bench: dict, ctrl: dict) -> list[bool]:
    return [
        c["maxdd"] >= bench["maxdd"] + 0.02 and c["share365"] >= bench["share365"]
        and c["share730"] >= bench["share730"],
        c["sharpe"] >= bench["sharpe"] - 0.10,
        c["maxdd"] >= ctrl["maxdd"] + 0.01 and c["cagr"] >= ctrl["cagr"] - 0.005,
        all(np.isnan(bench[f"dd_{h}"]) or c[f"dd_{h}"] >= bench[f"dd_{h}"] for h, _, _ in HALVES),
    ]


def evaluate(label: str, ret, tid, idx, w: pd.Series, bench: dict) -> dict:
    """One estimator on one span: both bands, each with its equal-exposure control."""
    w_reb = w.reindex(idx).to_numpy()
    w_entry = w.shift(1).reindex(idx).to_numpy()
    assert not np.isnan(w_reb).any() and not np.isnan(w_entry).any(), f"{label}: target has gaps"
    held = w_reb[tid >= 0]
    results = {}
    for band in BANDS:
        cand = stats(*account_var(ret, tid, w_entry, w_reb, band), idx)
        w_ctrl = float(held.mean())
        ctrl = stats(*account(ret, tid, w_ctrl, band), idx)
        checks = rule(cand, bench, ctrl)
        name = f"{label} b={band}"
        line(name, cand, f"  w mean {held.mean():.3f} min {held.min():.2f} max {held.max():.2f}")
        line(f"  control w={w_ctrl:.3f}", ctrl)
        print(f"    rule 1 DD {checks[0]}  2 Sharpe {checks[1]}  3 beats control {checks[2]}  "
              f"4 halves {checks[3]}  -> {'PASS' if all(checks) else 'FAIL'}")
        results[name] = (cand, ctrl, checks)
    return results


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cache", required=True, type=pathlib.Path)
    args = p.parse_args()
    print(f"design {DESIGN.name} sha256 {hashlib.sha256(DESIGN.read_bytes()).hexdigest()}")
    df = load_csv(ROOT / "data/ml/historical/BTCUSDT_1d.csv")
    df = in_gbp(df[df.index < HOLDOUT], fx_usd_per_gbp(args.cache))
    ret, tid, idx = strategy_days(df)
    print(f"GBP 1d {idx[0].date()}..{idx[-1].date()}, {len(ret)} days, {tid.max() + 1} trades, fee {FEE:.2%}")

    # Harness check: a constant 0.5 target must be the benchmark, bit for bit.
    ref = account(ret, tid, W_BASE, BENCH_BAND)
    flat = np.full(len(ret), W_BASE)
    same = account_var(ret, tid, flat, flat, BENCH_BAND)
    assert np.array_equal(ref[0], same[0]) and ref[1:] == same[1:], "harness does not reproduce the benchmark"
    print("harness: constant target 0.5, band 0.15 == benchmark account, bit for bit")

    bench = stats(*ref, idx)
    print("\nFULL SAMPLE")
    line("benchmark w=0.5 b=0.15", bench)
    targets = {"RV20": target(realized(df["close"], 20)), "RV60": target(realized(df["close"], 60))}
    full = {}
    for label, w in targets.items():
        full.update(evaluate(label, ret, tid, idx, w, bench))

    w_dvol = target(dvol(args.cache))
    keep = idx >= w_dvol.index[1]                      # entry needs the previous day's target
    r2, t2, i2 = ret[keep], tid[keep], idx[keep]
    print(f"\nCOMMON SPAN (DVOL exists) {i2[0].date()}..{i2[-1].date()}, {len(r2)} days")
    bench2 = stats(*account(r2, t2, W_BASE, BENCH_BAND), i2)
    line("benchmark w=0.5 b=0.15", bench2)
    common = {}
    for label, w in {**targets, "DVOL": w_dvol}.items():
        common.update(evaluate(label, r2, t2, i2, w, bench2))

    print("\nDECISION (design rule)")
    passed = [k for k, (_, _, c) in full.items() if all(c)]
    print(f"  RV variants passing on the full sample: {len(passed)}/4 {passed}")
    if len(passed) >= 2:
        best = max(passed, key=lambda k: (float(k.split("b=")[1]), int(k[2:4])))
        print(f"  #12 ACCEPTED (model): {best}")
    else:
        print("  #12 REJECTED: w=0.5 with band 0.15 stays")
    best_rv = max(c["maxdd"] for k, (c, _, _) in common.items() if k.startswith("RV"))
    for k, (c, _, checks) in common.items():
        if k.startswith("DVOL"):
            promising = all(checks[:3]) and c["maxdd"] >= best_rv + 0.01
            print(f"  {k}: {'PROMISING (paper side-by-side design only)' if promising else 'rejected as an input'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
