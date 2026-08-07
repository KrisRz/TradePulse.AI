"""Research: does an ensemble of EMA speeds improve on the single EMA(20/100)?

#1 of the corrected adoption queue (docs/RESEARCH_ULEPSZEN_2026-08-07.md):
averaging across trend speeds reduces single-parameter luck (evidenced in
channel-ensemble literature). Same methodology and cost convention as the
M4/F2 vol-targeting study, so results are directly comparable — and the same
bar applies: adoption only if it beats the single EMA out-of-sample on the M4
walk-forward harness; this study is the cheaper GO/NO-GO before that.

Two ensemble forms, because they differ in adoption cost:
- AVERAGE: w = mean of member signals (fractional exposure 0, .2, .4 … 1) —
  would require fractional-position support in the engine and the book;
- MAJORITY: w = 1 if >= 3/5 members long else 0 — drop-in compatible with the
  existing +-1/0 engine and PaperPortfolio, no book changes at all.

The member set is a PRE-SPECIFIED family around the validated 20/100 (same
1:5 ratio, standard speeds), written down before looking at any result:
(10/50, 15/75, 20/100, 30/150, 40/200). Nothing here is optimized.

Usage: PYTHONPATH=. python scripts/research/ema_ensemble_study.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FEE_PLUS_SLIP = 0.0012  # 0.1% fee + 0.02% slippage per unit turnover (= M4/F2)
ANNUALIZE = np.sqrt(365)
MEMBERS = [(10, 50), (15, 75), (20, 100), (30, 150), (40, 200)]


def load(path="data/ml/historical/BTCUSDT_1d.csv"):
    return pd.read_csv(path, parse_dates=["timestamp"], index_col="timestamp")


def ema_signal(close: pd.Series, fast: int, slow: int) -> pd.Series:
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


def simulate_weight(df: pd.DataFrame, w: pd.Series) -> tuple[pd.Series, float]:
    """Weight series -> net returns, same conventions as vol_targeting_study."""
    r_bar = df["open"].pct_change().shift(-2)   # decision close(t) -> o(t+1)->o(t+2)
    w = w.fillna(0.0)
    net = ((w * r_bar).fillna(0.0) - FEE_PLUS_SLIP * w.diff().abs().fillna(0.0)).iloc[:-2]
    return net, float(w.diff().abs().sum())


def main() -> None:
    df = load()
    close = df["close"]
    signals = pd.DataFrame({f"{f}/{s}": ema_signal(close, f, s)
                            for f, s in MEMBERS})

    variants = {
        "EMA20/100 (baseline)": signals["20/100"],
        "ensemble AVERAGE 5x": signals.mean(axis=1),
        "ensemble MAJORITY>=3/5": (signals.sum(axis=1) >= 3).astype(float),
    }

    rows = []
    for period, dfx in [("full 2017-2026", df), ("recent 2022-2026", df.loc["2022":])]:
        for name, w in variants.items():
            net, turn = simulate_weight(dfx, w.loc[dfx.index])
            rows.append(metrics(net, f"{name:24s} [{period}]", turn))
        bh = dfx["open"].pct_change().shift(-2).fillna(0.0).iloc[:-2]
        rows.append(metrics(bh, f"{'Buy&Hold':24s} [{period}]", 0.0))
    print(pd.DataFrame(rows).to_string(index=False))

    # Per-member readout: is 20/100 privileged, or just one of a robust family?
    print("\nPer-member (full history):")
    rows = []
    for col in signals.columns:
        net, turn = simulate_weight(df, signals[col])
        rows.append(metrics(net, f"EMA{col}", turn))
    print(pd.DataFrame(rows).to_string(index=False))

    # Year-by-year robustness: an aggregate win hiding in one lucky year is
    # not a win. Measured 2026-08-07: AVERAGE >= baseline in 6 of 9 years
    # (loses 2020, 2022, 2025) — consistent-ish, modest, not a silver bullet.
    print("\nYear-by-year Sharpe (baseline vs AVERAGE):")
    base = simulate_weight(df, variants["EMA20/100 (baseline)"])[0]
    avg = simulate_weight(df, variants["ensemble AVERAGE 5x"])[0]
    for year in range(df.index[0].year + 1, df.index[-1].year + 1):
        b, a = base.loc[str(year)], avg.loc[str(year)]
        sb = b.mean() / b.std() * ANNUALIZE if b.std() > 0 else 0.0
        sa = a.mean() / a.std() * ANNUALIZE if a.std() > 0 else 0.0
        print(f"  {year}: {sb:+.2f} vs {sa:+.2f} {'<-- AVG' if sa >= sb else ''}")


if __name__ == "__main__":
    main()
