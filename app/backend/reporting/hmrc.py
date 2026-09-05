"""UK capital-gains matching for the bot's fill log (HMRC share-identification rules).

Why this exists before it is needed
-----------------------------------
The bot closes about 1.7 round trips a year on the 1d channel and a dozen on the
4h one, so the arithmetic will always be small. That is exactly why it is worth
writing now rather than in a hurry next January: the hard part is not the volume,
it is the *matching rules*, and getting them wrong produces a number that looks
perfectly reasonable and is wrong. The fill log already carries everything needed
(`fill#<bar>#<order_id>` in DynamoDB), and it is fresh in mind today.

The rules, in the order HMRC applies them (CG51560 / CRYPTO22200)
-----------------------------------------------------------------
A disposal is matched against acquisitions in this precedence, and only what is
left over touches the pool:

1. **Same day.** Acquisitions of the same token on the same day as the disposal.
2. **Bed and breakfast.** Acquisitions in the **30 days after** the disposal.
   This one is counter-intuitive — it matches *forward in time* — and it exists
   to stop a disposal-and-repurchase from crystallising a loss. A bot that sells
   on a signal and buys back three weeks later is doing this without meaning to.
3. **Section 104 pool.** Everything else, at the pooled average cost.

Costs and proceeds follow the ordinary rule: fees paid on an acquisition are part
of its allowable cost, fees paid on a disposal reduce the proceeds.

What this tool does NOT decide for you
--------------------------------------
* **Currency.** Fills are priced in the quote asset (USDT). HMRC wants sterling
  at the rate on the day of each transaction. Pass ``--fx`` (one rate) or
  ``--fx-csv`` (date,rate) and every money column is converted; pass neither and
  the report stays in the quote currency and says so in the header. It will not
  quietly imply that USDT figures are pounds.
* **Fees billed in another asset.** Binance charges commission in BNB when the
  account holds it. Paying a fee in BNB is itself a disposal of BNB, which is a
  second computation this tool does not attempt. Such fees are reported in their
  own column and flagged, never silently dropped or silently converted. The
  standing recommendation stands: turn BNB fee payment OFF on a live account.
* **Whether any of this is your final position.** It is a working paper.

Day boundary
------------
UK tax days are UK days, and the fill log is UTC. During British Summer Time a
fill at 23:30 UTC belongs to the *next* UK day, which can move it across a
same-day match. The conversion is done properly via ``Europe/London`` rather than
by truncating the UTC timestamp.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

UK = ZoneInfo("Europe/London")

#: The bed-and-breakfast window, in days after the disposal.
BNB_WINDOW_DAYS = 30

ACQUISITION = 1
DISPOSAL = -1


def _dec(value: Any) -> Decimal:
    """Decimal from anything the fill log might hold, never via binary float."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value if value is not None else 0))


@dataclass
class Transaction:
    """One acquisition or disposal, in the terms the matching rules need."""

    when: datetime                 # UTC
    side: int                      # ACQUISITION / DISPOSAL
    qty: Decimal
    price: Decimal                 # per unit, quote currency
    fee: Decimal = Decimal("0")    # quote currency; see fee_asset
    fee_raw: Decimal = Decimal("0")  # as billed, whatever the asset
    fee_asset: str = ""
    order_id: str = ""
    asset: str = "BTC"
    remaining: Decimal = field(init=False)

    def __post_init__(self) -> None:
        self.remaining = self.qty

    @property
    def uk_day(self) -> date:
        return self.when.astimezone(UK).date()

    @property
    def unit_cost(self) -> Decimal:
        """Acquisition cost per unit, fees included."""
        return (self.qty * self.price + self.fee) / self.qty if self.qty else Decimal("0")

    @property
    def unit_proceeds(self) -> Decimal:
        """Disposal proceeds per unit, net of fees."""
        return (self.qty * self.price - self.fee) / self.qty if self.qty else Decimal("0")


@dataclass
class Match:
    """One piece of a disposal, matched under one rule."""

    rule: str                      # "same-day" | "30-day" | "s104"
    qty: Decimal
    proceeds: Decimal
    cost: Decimal
    acquisition_ids: list = field(default_factory=list)

    @property
    def gain(self) -> Decimal:
        return self.proceeds - self.cost


@dataclass
class DisposalReport:
    when: datetime
    uk_day: date
    asset: str
    order_id: str
    qty: Decimal
    matches: list = field(default_factory=list)
    fee_other_asset: Decimal = Decimal("0")
    fee_asset: str = ""

    @property
    def proceeds(self) -> Decimal:
        return sum((m.proceeds for m in self.matches), Decimal("0"))

    @property
    def cost(self) -> Decimal:
        return sum((m.cost for m in self.matches), Decimal("0"))

    @property
    def gain(self) -> Decimal:
        return self.proceeds - self.cost


def transactions_from_fills(fills: Iterable[dict], asset: str = "BTC",
                            quote: str = "USDT") -> list:
    """Turn fill-log records into transactions, in chronological order.

    Accepts the shape ``persist_execution_evidence`` writes: ``time``, ``side``,
    ``qty``, ``actual_price``, ``fee_paid``, ``fee_asset``, ``order_id``.
    """
    out = []
    for f in fills:
        when = f.get("time") or f.get("bar")
        if isinstance(when, str):
            when = datetime.fromisoformat(when.replace("Z", "+00:00"))
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)

        fee_asset = (f.get("fee_asset") or "").upper()
        fee = _dec(f.get("fee_paid"))
        # A fee billed in the quote currency is an ordinary allowable cost. One
        # billed in anything else is a separate disposal in its own right and is
        # carried through untouched rather than converted on a guess.
        quote_fee = fee if fee_asset in ("", quote, "USD", "GBP") else Decimal("0")

        out.append(Transaction(
            when=when,
            side=ACQUISITION if int(f.get("side", 1)) > 0 else DISPOSAL,
            qty=_dec(f.get("qty")),
            price=_dec(f.get("actual_price") or f.get("price")),
            fee=quote_fee,
            fee_raw=fee,
            fee_asset=fee_asset,
            order_id=str(f.get("order_id", "")),
            asset=asset,
        ))
    return sorted(out, key=lambda t: t.when)


def match(transactions: list) -> tuple:
    """Apply the three rules in order. Returns (disposal reports, pool summary).

    The passes are separate on purpose. Same-day and bed-and-breakfast matching
    both look FORWARD from a disposal, so neither can be decided while walking
    the timeline once — and an acquisition consumed by one of them must never
    also enter the pool. Doing it in three passes is what keeps that honest.
    """
    acquisitions = [t for t in transactions if t.side == ACQUISITION]
    disposals = [t for t in transactions if t.side == DISPOSAL]
    reports = {id(d): DisposalReport(when=d.when, uk_day=d.uk_day, asset=d.asset,
                                     order_id=d.order_id, qty=d.qty)
               for d in disposals}

    for d in disposals:
        r = reports[id(d)]
        if d.fee_asset and d.fee_asset not in ("USDT", "USD", "GBP"):
            # Carried through with its amount intact. Paying a fee in BNB is a
            # disposal of BNB in its own right; reporting it as zero would be a
            # quiet error, and converting it would be a guess.
            r.fee_asset = d.fee_asset
            r.fee_other_asset = d.fee_raw

    def consume(disposal, candidates, rule):
        r = reports[id(disposal)]
        for a in candidates:
            if disposal.remaining <= 0:
                break
            if a.remaining <= 0:
                continue
            take = min(disposal.remaining, a.remaining)
            r.matches.append(Match(
                rule=rule, qty=take,
                proceeds=take * disposal.unit_proceeds,
                cost=take * a.unit_cost,
                acquisition_ids=[a.order_id],
            ))
            disposal.remaining -= take
            a.remaining -= take

    # 1. Same day.
    for d in disposals:
        consume(d, [a for a in acquisitions if a.uk_day == d.uk_day], "same-day")

    # 2. Bed and breakfast: acquisitions in the 30 days AFTER the disposal.
    for d in disposals:
        window_end = d.uk_day + timedelta(days=BNB_WINDOW_DAYS)
        consume(d, [a for a in acquisitions
                    if d.uk_day < a.uk_day <= window_end], "30-day")

    # 3. Section 104 pool: replay what is left, chronologically.
    pool_qty = Decimal("0")
    pool_cost = Decimal("0")
    for t in sorted(transactions, key=lambda x: x.when):
        if t.remaining <= 0:
            continue
        if t.side == ACQUISITION:
            pool_qty += t.remaining
            pool_cost += t.remaining * t.unit_cost
            t.remaining = Decimal("0")
            continue

        take = min(t.remaining, pool_qty)
        if take <= 0:
            continue
        unit_pool_cost = pool_cost / pool_qty
        reports[id(t)].matches.append(Match(
            rule="s104", qty=take,
            proceeds=take * t.unit_proceeds,
            cost=take * unit_pool_cost,
        ))
        pool_cost -= take * unit_pool_cost
        pool_qty -= take
        t.remaining -= take

    unmatched = [t for t in disposals if t.remaining > 0]
    summary = {
        "pool_qty": pool_qty,
        "pool_cost": pool_cost,
        "pool_unit_cost": (pool_cost / pool_qty) if pool_qty else Decimal("0"),
        "total_proceeds": sum((r.proceeds for r in reports.values()), Decimal("0")),
        "total_cost": sum((r.cost for r in reports.values()), Decimal("0")),
        "total_gain": sum((r.gain for r in reports.values()), Decimal("0")),
        "disposals": len(disposals),
        "unmatched_disposals": [
            {"order_id": t.order_id, "qty": str(t.remaining)} for t in unmatched],
    }
    return sorted(reports.values(), key=lambda r: r.when), summary


def write_csv(path, reports, currency: str, fx=None) -> None:
    """One row per (disposal, rule) piece — the granularity a return needs.

    ``fx`` maps a UK date to a rate multiplying the quote currency into sterling.
    Absent, the amounts stay in ``currency`` and the header says so, because a
    column headed "gain" that is silently in USDT is worse than no column.
    """
    unit = "GBP" if fx else currency
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([f"# amounts in {unit}"
                    + ("" if fx else " — NOT converted to GBP; apply HMRC rates before filing")])
        w.writerow(["date_uk", "time_utc", "asset", "order_id", "rule", "quantity",
                    f"proceeds_{unit}", f"allowable_cost_{unit}", f"gain_{unit}",
                    "fee_asset_other"])
        for r in reports:
            rate = fx(r.uk_day) if fx else Decimal("1")
            for m in r.matches:
                w.writerow([
                    r.uk_day.isoformat(),
                    r.when.astimezone(timezone.utc).isoformat(),
                    r.asset, r.order_id, m.rule, f"{m.qty:f}",
                    f"{m.proceeds * rate:.2f}", f"{m.cost * rate:.2f}",
                    f"{m.gain * rate:.2f}",
                    f"{r.fee_other_asset:f} {r.fee_asset}".strip() if r.fee_asset else "",
                ])
