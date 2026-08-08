"""Feature table for the 128 pooled EMA events — the meta-labeler's dataset.

One row per event from pooled_events_census (entry of EMA20/100 long on one
of the 8 majors), columns = the state of the world AT THE ENTRY DECISION plus
the label (net return after costs). This is step 1 of the pre-registered D11
path; the model itself comes later and must beat plain EMA20/100 on the M4
harness (bar set 2026-08-08, docs/REGIME_FILTER_2026-08-08.md).

Feature design, declared before looking at any correlation with labels:

ASSET-LEVEL (from the asset's own 1d bars, all 128 events):
- vol20            realized vol of daily returns, 20d
- vol_pctl_1y      that vol's percentile within its trailing 365d (calm-vol
                   feature from REGIME_FILTER_2026-08-08 — kept as a FEATURE)
- trend_gap        (EMA20-EMA100)/EMA100 at the signal bar
- ret20            20d price return into the entry
- dd_from_1y_high  close vs trailing 365d max close

MARKET-LEVEL (BTC series as the crypto-cycle proxy for ALL assets — funding/
OI/on-chain history exists only for BTC; the cycle they describe is shared):
- btc_vol20, btc_trend_gap    same constructions on BTC
- funding_last                last settled 8h funding at decision time
- funding_cum30               sum of settlements over prior 30d
- doi7, doi30                 % change of BTC open interest over 7d/30d
- mvrv_z                      z-score of CapMVRVCur over its trailing 4y

POINT-IN-TIME DISCIPLINE:
- decision time = close of signal bar t (= 00:00 UTC of t+1); entry fills at
  the next open — features may use nothing later than the decision time;
- funding: settlements with timestamp <= decision time (exact, timestamped);
- daily external series (OI daily-last, MVRV): value for calendar day t-1,
  i.e. shifted one full day, so end-of-day publication lag cannot leak;
- mvrv_z uses a TRAILING 1460d window (no full-sample statistics).

Coverage is honest, not imputed: events before a series starts (funding
2020-01, OI 2020-09, MVRV 2011) carry NaN — the model stage decides handling.
Output CSV is gitignored (regenerable); the doc records the summary.

Usage: PYTHONPATH=. python scripts/research/event_feature_table.py
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.research.pooled_events_census import (  # noqa: E402
    ASSETS, events, load,
)

EXT = ROOT / "data" / "ml" / "external"
OUT = ROOT / "data" / "ml" / "events_features.csv"
MVRV_WINDOW = 1460


def asset_features(df: pd.DataFrame) -> pd.DataFrame:
    close = df["close"]
    ret = close.pct_change()
    vol20 = ret.rolling(20).std()
    feats = pd.DataFrame(index=df.index)
    feats["vol20"] = vol20
    feats["vol_pctl_1y"] = vol20.rolling(365).rank(pct=True)
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema100 = close.ewm(span=100, adjust=False).mean()
    feats["trend_gap"] = (ema20 - ema100) / ema100
    feats["ret20"] = close.pct_change(20)
    feats["dd_from_1y_high"] = close / close.rolling(365).max() - 1
    return feats


def market_features() -> pd.DataFrame:
    """Daily BTC market frame, ALREADY shifted to what is known at day t's
    close: daily external values are lagged one day inside this function."""
    btc = load("BTCUSDT")
    out = asset_features(btc)[["vol20", "trend_gap"]]
    out.columns = ["btc_vol20", "btc_trend_gap"]

    fund = pd.read_csv(EXT / "BTCUSDT_funding.csv", index_col="timestamp")
    fund.index = pd.to_datetime(fund.index, utc=True, format="mixed")
    # decision time for signal bar t is t+1 00:00 UTC; settlements strictly
    # before that boundary are known. Resample gives day t the settlements
    # stamped within [t, t+1) — exactly the known set. No extra shift needed.
    daily_rate = fund["funding_rate"].resample("1D").last()
    daily_sum = fund["funding_rate"].resample("1D").sum()
    out["funding_last"] = daily_rate.reindex(out.index)
    out["funding_cum30"] = daily_sum.rolling(30, min_periods=20).sum().reindex(out.index)

    met = pd.read_csv(EXT / "BTCUSDT_metrics.csv", index_col="timestamp")
    met.index = pd.to_datetime(met.index, utc=True, format="mixed")
    oi = met["sum_open_interest"].resample("1D").last().shift(1)   # day t-1
    oi = oi.replace(0.0, np.nan)        # zero-base pct change is undefined
    out["doi7"] = oi.pct_change(7, fill_method=None).reindex(out.index)
    out["doi30"] = oi.pct_change(30, fill_method=None).reindex(out.index)

    cm = pd.read_csv(EXT / "coinmetrics_btc_snapshot_2026-08-07.csv",
                     index_col="time")
    cm.index = pd.to_datetime(cm.index, utc=True, format="mixed")
    mvrv = cm["CapMVRVCur"].astype(float).shift(1)                 # day t-1
    mu = mvrv.rolling(MVRV_WINDOW, min_periods=730).mean()
    sd = mvrv.rolling(MVRV_WINDOW, min_periods=730).std()
    out["mvrv_z"] = ((mvrv - mu) / sd).reindex(out.index)
    return out


def main() -> int:
    market = market_features()
    rows = []
    for sym in ASSETS:
        df = load(sym)
        feats = asset_features(df)
        ev = events(df)
        for _, e in ev.iterrows():
            # entry fills at e["entry"]; the signal bar (decision) is the bar
            # BEFORE it — features must come from there, not from the fill bar
            sig_bar = df.index[df.index.get_loc(e["entry"]) - 1]
            row = {"asset": sym, "entry": e["entry"], "exit": e["exit"],
                   "hold_days": e["hold_days"],
                   "net_return": e["net_return"], "win": e["win"]}
            row.update(feats.loc[sig_bar].to_dict())
            mkt_bar = sig_bar if sig_bar in market.index else None
            row.update(market.loc[mkt_bar].to_dict() if mkt_bar is not None
                       else {c: np.nan for c in market.columns})
            rows.append(row)

    table = pd.DataFrame(rows).sort_values("entry").reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False)

    feat_cols = [c for c in table.columns
                 if c not in ("asset", "entry", "exit", "hold_days",
                              "net_return", "win")]
    print(f"events: {len(table)}  features: {len(feat_cols)}  -> {OUT}")
    print(f"\n{'feature':<16}{'coverage':>9}{'min':>10}{'median':>10}{'max':>10}")
    for c in feat_cols:
        s = table[c]
        print(f"{c:<16}{s.notna().mean():>8.0%}{s.min():>10.3f}"
              f"{s.median():>10.3f}{s.max():>10.3f}")
    full = table[feat_cols].notna().all(axis=1).sum()
    print(f"\nevents with EVERY feature present: {full}/{len(table)}")
    print("(missing = series not yet existing at entry date — by design, "
          "never imputed here)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
