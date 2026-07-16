"""M4/F2 research: does volatility-targeting sizing improve the EMA edge?

Return-level simulation (not the trade engine): weights applied to next-bar
open-to-open returns, costs charged on turnover. This answers WHETHER sizing
adds risk-adjusted value before we invest in fractional-position support in
the shared backtest engine.

Method
------
- Signal: EMA(20/100) crossover, long-only (fixed params — the robust
  walk-forward choice; nothing is fitted here, so the whole history is
  effectively out-of-sample for the SIZING question).
- Decision at close(t) -> exposure over bar t+1 (open(t+1) -> open(t+2)),
  same next-bar-open convention as the engine.
- Baseline: w = signal (0/1).
- Vol target: w = signal * min(1, vol_target / realized_vol) — long-only,
  no leverage. Realized vol = 20-bar std of daily returns, annualized.
- Costs: (fee + slippage) per unit of |Δw| turnover.

Usage: python scripts/research/vol_targeting_study.py
"""

import numpy as np
import pandas as pd

FEE_PLUS_SLIP = 0.0012  # 0.1% fee + 0.02% slippage per unit turnover
VOL_WINDOW = 20
ANNUALIZE = np.sqrt(365)


def load(path="data/ml/historical/BTCUSDT_1d.csv"):
    df = pd.read_csv(path, parse_dates=["timestamp"], index_col="timestamp")
    return df


def ema_signal(close: pd.Series, fast=20, slow=100) -> pd.Series:
    f = close.ewm(span=fast, adjust=False).mean()
    s = close.ewm(span=slow, adjust=False).mean()
    return (f > s).astype(float)


def metrics(returns: pd.Series, label: str, turnover: float) -> dict:
    eq = (1 + returns).cumprod()
    years = len(returns) / 365
    cagr = eq.iloc[-1] ** (1 / years) - 1
    sharpe = returns.mean() / returns.std() * ANNUALIZE if returns.std() > 0 else 0.0
    dd = (eq / eq.cummax() - 1).min()
    return {"label": label, "CAGR": f"{cagr:+.1%}", "Sharpe": f"{sharpe:.2f}",
            "maxDD": f"{dd:.0%}", "turnover/yr": f"{turnover / years:.1f}"}


def simulate(df: pd.DataFrame, vol_target: float | None) -> tuple[pd.Series, float]:
    close, open_ = df["close"], df["open"]
    sig = ema_signal(close)

    w = sig.copy()
    if vol_target is not None:
        realized = close.pct_change().rolling(VOL_WINDOW).std() * ANNUALIZE
        scale = (vol_target / realized).clip(upper=1.0).fillna(0.0)
        w = sig * scale

    # decision at close(t) -> exposure over open(t+1) -> open(t+2)
    r_bar = open_.pct_change().shift(-2)  # return earned by weight set at t
    w_shift = w.fillna(0.0)
    strat_r = (w_shift * r_bar).fillna(0.0)
    costs = FEE_PLUS_SLIP * w_shift.diff().abs().fillna(0.0)
    net = (strat_r - costs).iloc[:-2]
    turnover = float(w_shift.diff().abs().sum())
    return net, turnover


def main():
    df = load()
    rows = []
    for half, dfx in [("full 2017-2026", df), ("recent 2022-2026", df.loc["2022":])]:
        base, t0 = simulate(dfx, None)
        rows.append({**metrics(base, f"EMA baseline  [{half}]", t0)})
        for vt in (0.30, 0.40, 0.50, 0.60):
            r, t = simulate(dfx, vt)
            rows.append({**metrics(r, f"vol-target {vt:.0%} [{half}]", t)})
        bh = dfx["open"].pct_change().shift(-2).fillna(0.0).iloc[:-2]
        rows.append({**metrics(bh, f"Buy&Hold      [{half}]", 0.0)})
    print(pd.DataFrame(rows).to_string(index=False))


def regime_filter_study():
    """❓D9 helper: do simple 1d regime filters improve the EMA edge OOS?"""
    df = load()
    close = df["close"]
    sig = ema_signal(close)
    sma200 = close.rolling(200).mean()
    filters = {
        "no filter": pd.Series(1.0, index=df.index),
        "price>SMA200": (close > sma200).astype(float),
        "SMA200 rising": (sma200.diff(20) > 0).astype(float),
    }
    rows = []
    for half, sl in [("full", slice(None)), ("2022+", slice("2022", None))]:
        for name, f in filters.items():
            w = (sig * f).fillna(0.0)
            r_bar = df["open"].pct_change().shift(-2)
            net = ((w * r_bar).fillna(0.0) - FEE_PLUS_SLIP * w.diff().abs().fillna(0.0))
            net = net.loc[sl].iloc[:-2] if half == "full" else net.loc[sl]
            turn = float(w.loc[sl].diff().abs().sum())
            rows.append(metrics(net, f"EMA + {name} [{half}]", turn))
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
    print()
    regime_filter_study()


