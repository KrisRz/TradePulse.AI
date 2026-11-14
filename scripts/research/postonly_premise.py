"""Premise for the post-only candidate (plan 2026-11-14, position 7).

Question: if the bot rested a post-only limit at the touch at its decision time
(00:10 UTC) instead of paying the taker fee, how often and how fast would it
fill, and what does waiting cost when it does not?

Public Kraken trade tape only (no orders, no key). For each of the last N days:
reference = first trade at/after 00:10 UTC. A BUY limit one tick under the
reference counts as filled when a later trade prints STRICTLY below it (a trade
through the level fills it whatever the queue; a print AT the level may not).
SELL is the mirror. Not filled by the deadline -> taker at the last print.

Usage: PYTHONPATH=. python scripts/research/postonly_premise.py [days]
"""

import sys
import time
from datetime import datetime, timedelta, timezone

import requests

PAIR, TICK = "XBTGBP", 0.1
MAKER, TAKER = 0.0040, 0.0080
DEADLINES_MIN = (5, 15, 60, 240)


def tape(since: datetime, minutes: int) -> list:
    """Trades from ``since`` for ``minutes``: (time, price, side)."""
    out, cursor = [], int(since.timestamp() * 1e9)
    end = since.timestamp() + minutes * 60
    for _ in range(12):
        r = requests.get("https://api.kraken.com/0/public/Trades",
                         params={"pair": PAIR, "since": cursor}, timeout=15).json()
        if r["error"]:
            raise RuntimeError(r["error"])
        rows = next(v for k, v in r["result"].items() if k != "last")
        out += [(float(t[2]), float(t[0]), t[3]) for t in rows]
        cursor = int(r["result"]["last"])
        if not rows or out[-1][0] >= end or len(rows) < 1000:
            break
        time.sleep(1.2)
    return [t for t in out if t[0] <= end]


def main(days: int) -> None:
    today = datetime.now(timezone.utc).replace(hour=0, minute=10, second=0, microsecond=0)
    rows = []
    for d in range(1, days + 1):
        t0 = today - timedelta(days=d)
        trades = tape(t0, max(DEADLINES_MIN))
        time.sleep(1.2)
        if len(trades) < 2:
            continue
        ref = trades[0][1]
        for side, sign in (("buy", 1), ("sell", -1)):
            limit = ref - sign * TICK
            fill_at = next((t for t, p, _ in trades[1:] if sign * (limit - p) > 0), None)
            rec = {"day": t0.date(), "side": side, "n_trades": len(trades),
                   "fill_min": (fill_at - trades[0][0]) / 60 if fill_at else None}
            for dl in DEADLINES_MIN:
                cutoff = trades[0][0] + dl * 60
                if fill_at is not None and fill_at <= cutoff:
                    cost = MAKER + sign * (limit / ref - 1)          # filled as maker
                else:
                    last = [p for t, p, _ in trades if t <= cutoff][-1]
                    cost = TAKER + sign * (last / ref - 1)           # taker after waiting
                rec[dl] = cost
            rows.append(rec)
    n = len(rows)
    print(f"{n} decisions ({n // 2} days x 2 sides), median trades in 4h window: "
          f"{sorted(r['n_trades'] for r in rows)[n // 2]}")
    print(f"taker now: {TAKER:.2%} per side (reference)")
    print("deadline | filled as maker | mean cost/side | worst cost | saving vs taker")
    for dl in DEADLINES_MIN:
        filled = sum(1 for r in rows if r["fill_min"] is not None and r["fill_min"] <= dl)
        costs = [r[dl] for r in rows]
        mean = sum(costs) / n
        print(f"{dl:5d} min | {filled:3d}/{n} = {filled / n:5.1%} | {mean:8.3%} | "
              f"{max(costs):7.3%} | {TAKER - mean:+.3%}")
    fills = sorted(r["fill_min"] for r in rows if r["fill_min"] is not None)
    if fills:
        print(f"time to fill (when filled within 4h): median {fills[len(fills) // 2]:.1f} min, "
              f"p90 {fills[int(len(fills) * 0.9) - 1]:.1f} min")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 30)
