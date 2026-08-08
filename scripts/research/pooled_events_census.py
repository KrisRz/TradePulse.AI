"""Census of pooled EMA20/100 events across majors — is >100 reachable NOW?

The meta-labeler (pre-registered path D11) needs >100 labeled events; BTC+ETH
history yields 31 and live trading adds ~3-4/yr. The 2026-08-07 research doc
pre-registered the remedy: pool more majors under the IDENTICAL rule. This
script measures whether that actually clears the bar.

Universe declared by RULE before counting (no cherry-picking): Binance USDT
spot pairs, top market cap, non-stablecoin, listed >= 5 years — BNB, XRP,
LTC, ADA, DOGE + SOL (largest of the ~6y cohort). Data: bulk archives,
integrity-validated, truncated at the M5 holdout (<2026-07-16).

An EVENT is one long entry (signal 0->1): entry at next bar open, exit at the
bar open after the signal turns off, net of (fee+slip) both ways — the label
the meta-labeler would learn ("did THIS signal pay after costs?"). Events
still open at the holdout are dropped (no label yet). This is a census, not a
strategy verdict: profitability of the pool is NOT the question and carries
no decision rule; the deliverable is the sample size and label balance.

Usage: PYTHONPATH=. python scripts/research/pooled_events_census.py
"""

from __future__ import annotations

import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "ml" / "historical"

HOLDOUT_START = "2026-07-16"
FEE = 0.001
SLIPPAGE = 0.0002
ASSETS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "LTCUSDT",
          "ADAUSDT", "DOGEUSDT", "SOLUSDT"]


def load(symbol: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / f"{symbol}_1d.csv",
                     parse_dates=["timestamp"], index_col="timestamp")
    cutoff = pd.Timestamp(HOLDOUT_START)
    if getattr(df.index, "tz", None) is not None:
        cutoff = cutoff.tz_localize(df.index.tz)
    return df[df.index < cutoff]


def events(df: pd.DataFrame) -> pd.DataFrame:
    close, open_ = df["close"], df["open"]
    sig = (close.ewm(span=20, adjust=False).mean()
           > close.ewm(span=100, adjust=False).mean()).astype(int)
    sig.iloc[:100] = 0                      # EMA warmup: no tradable signal yet
    turns = sig.diff().fillna(0)
    rows = []
    entry_i = None
    for i, t in enumerate(turns):
        if t == 1:
            entry_i = i
        elif t == -1 and entry_i is not None:
            if i + 1 < len(df):             # exit fills at next open
                entry_px = open_.iloc[entry_i + 1]
                exit_px = open_.iloc[i + 1]
                gross = exit_px / entry_px - 1
                net = (1 + gross) * (1 - FEE - SLIPPAGE) ** 2 - 1
                rows.append({"entry": df.index[entry_i + 1],
                             "exit": df.index[i + 1],
                             "hold_days": i - entry_i,
                             "net_return": net,
                             "win": net > 0})
            entry_i = None
    # an entry still open at the holdout has no label -> excluded by design
    return pd.DataFrame(rows)


def main() -> int:
    total, wins = 0, 0
    print(f"{'asset':<10}{'bars':>7}{'events':>8}{'wins':>6}{'win%':>7}"
          f"{'med hold':>9}{'med net':>9}")
    per_asset = {}
    for sym in ASSETS:
        df = load(sym)
        ev = events(df)
        n, w = len(ev), int(ev["win"].sum()) if len(ev) else 0
        total += n
        wins += w
        per_asset[sym] = n
        print(f"{sym:<10}{len(df):>7}{n:>8}{w:>6}"
              f"{(w / n * 100 if n else 0):>6.0f}%"
              f"{ev['hold_days'].median() if n else 0:>9.0f}"
              f"{ev['net_return'].median() * 100 if n else 0:>8.1f}%")

    print("-" * 56)
    print(f"{'POOLED':<10}{'':>7}{total:>8}{wins:>6}{wins / total * 100:>6.0f}%")
    print(f"\nthreshold for the meta-labeler: >100 labeled events")
    print(f"pooled sample: {total} -> {'CLEARED' if total > 100 else 'NOT met'}")
    print("note: pooling imports cross-asset distribution shift — the model")
    print("learns 'crypto majors', not 'BTC specifically'. Known, accepted,")
    print("and the reason validation must be grouped per-asset (leave-one-")
    print("asset-out or purged by time across ALL assets simultaneously).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
