"""Kraken executor: real orders, an exchange-side emergency stop, reconciliation.

Implements rules R1–R13 of docs/KRAKEN_EXECUTOR_PREREGISTRATION_2026-11-14.md
on top of the transport in ``kraken_api``. Two layers:

* :class:`KrakenExecutor` — one venue action at a time (buy, sell, stop,
  cancel, look up), each idempotent by client order id.
* :class:`KrakenTrader` — the bot's position on the venue: enter, adjust, exit,
  and the start-of-run reconciliation. It owns the order of operations
  (cancel stop -> confirm -> trade -> new stop) and persists after every venue
  effect, so a run that dies half-way is finished by the next one instead of
  being repeated.

What the venue taught us before this was written (validate=true, 2026-11-14):
client ids are at most 18 characters; ``validate`` does not check balances; a
write whose answer is unclear must be looked up, never resent.
"""

from __future__ import annotations

import hashlib
import logging
import time as _time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Callable, Optional

from .execution import BUY, SELL
from .kraken_api import KrakenAPIError, KrakenOutcomeUnknown, PairRules

logger = logging.getLogger(__name__)

#: R1 — the key may hold these and nothing else. Anything more (withdraw,
#: deposit, earn, export) stops the run before any order.
ALLOWED_PERMISSIONS = frozenset({
    "query-funds", "query-open-trades", "query-closed-trades",
    "modify-trades", "close-trades"})
#: R8 — pre-registered. The exchange stop is a catastrophe guard, wider than F7.
EMERGENCY_STOP_PCT = Decimal("0.20")
#: R7 — the bot's BTC may never exceed this share of account equity after a buy.
MAX_EXPOSURE = Decimal("0.65")
#: R5 — how long the matching engine may take before it must drop the order.
DEADLINE_SECONDS = 30
CLIENT_PREFIX = "tpk"
_CLIENT_ID_MAX = 18
_FINAL = frozenset({"closed", "canceled", "expired"})


class ExecutorHalt(RuntimeError):
    """A precondition failed (R1, R2, R3, R7, R11). No order was sent by the
    step that raised; a human reads the reason before anything continues."""


class OrderOutcomeUnknown(RuntimeError):
    """An order was sent, its answer was unclear and the lookup has not found it
    yet. The next run's lookup by client id settles it (R4, R5)."""


@dataclass(frozen=True)
class VenueOrder:
    """One order as the exchange reports it."""

    txid: str
    cl_ord_id: Optional[str]
    status: str               # pending | open | closed | canceled | expired
    side: int                 # BUY / SELL
    ordertype: str
    volume: Decimal
    vol_exec: Decimal
    cost: Decimal             # quote currency, fee not included
    fee: Decimal              # quote currency
    stop_price: Optional[Decimal]
    closed_at: Optional[str]  # ISO-8601 UTC
    raw: dict = field(repr=False, default_factory=dict)

    @property
    def is_final(self) -> bool:
        return self.status in _FINAL

    @property
    def executed(self) -> bool:
        """Anything traded — a cancelled order may still have a partial fill."""
        return self.vol_exec > 0

    @property
    def avg_price(self) -> Optional[Decimal]:
        return self.cost / self.vol_exec if self.vol_exec > 0 else None

    @classmethod
    def parse(cls, txid: str, raw: dict) -> "VenueOrder":
        descr = raw.get("descr") or {}
        closetm = raw.get("closetm")
        stop = descr.get("price") if descr.get("ordertype") == "stop-loss" else None
        return cls(
            txid=txid, cl_ord_id=raw.get("cl_ord_id"), status=str(raw["status"]),
            side=BUY if descr.get("type") == "buy" else SELL,
            ordertype=str(descr.get("ordertype")),
            volume=Decimal(str(raw["vol"])), vol_exec=Decimal(str(raw["vol_exec"])),
            cost=Decimal(str(raw.get("cost", "0"))), fee=Decimal(str(raw.get("fee", "0"))),
            stop_price=Decimal(str(stop)) if stop not in (None, "", "0") else None,
            closed_at=(datetime.fromtimestamp(float(closetm), tz=timezone.utc).isoformat()
                       if closetm else None),
            raw=raw)


@dataclass(frozen=True)
class Preflight:
    rules: PairRules
    taker_fee: Decimal        # as a fraction, 0.008 = 0.80%
    permissions: tuple


class KrakenExecutor:
    """Venue actions for one pair. Stateless between calls: everything it needs
    to be idempotent is the client order id it is handed."""

    def __init__(self, client, pair: str = "XBTGBP", *, max_notional: Decimal,
                 channel: str = "XBTGBP_1d", clock: Callable[[], float] = _time.time,
                 sleep: Callable[[float], None] = _time.sleep,
                 poll_attempts: int = 10, poll_interval: float = 1.0) -> None:
        self.client = client
        self.pair = pair
        self.channel = channel
        self.max_notional = Decimal(str(max_notional))
        self._clock = clock
        self._sleep = sleep
        self._poll_attempts = poll_attempts
        self._poll_interval = poll_interval
        self._preflight: Optional[Preflight] = None

    # -- R1–R3 ------------------------------------------------------------ #
    def preflight(self) -> Preflight:
        """Everything that must be true before an order may exist."""
        info = self.client.private_read("GetApiKeyInfo") or {}
        permissions = tuple(sorted(info.get("permissions") or ()))
        if not permissions:
            raise ExecutorHalt("R1: the key reports no permissions — cannot verify it")
        extra = set(permissions) - ALLOWED_PERMISSIONS
        if extra:
            raise ExecutorHalt(f"R1: the key holds permissions it must not have: {sorted(extra)}")
        status = self.client.system_status()
        if status != "online":
            raise ExecutorHalt(f"R2: Kraken status is {status!r}, not online")
        rules = self.client.pair_rules(self.pair)
        if not rules.tradable:
            raise ExecutorHalt(f"R3: pair {self.pair} status is {rules.status!r}")
        volume = self.client.private_read("TradeVolume", {"pair": self.pair})
        fee_pct = Decimal(str(volume["fees"][rules.key]["fee"]))
        self._preflight = Preflight(rules=rules, taker_fee=fee_pct / 100,
                                    permissions=permissions)
        return self._preflight

    @property
    def rules(self) -> PairRules:
        if self._preflight is None:
            raise ExecutorHalt("preflight() has not run — no order may be sent")
        return self._preflight.rules

    # -- R4: identity ----------------------------------------------------- #
    def client_order_id(self, kind: str, key: str) -> str:
        """Stable id for one decision: same (channel, kind, key) -> same id.

        ``kind`` is one letter: b(uy), s(ell), p(rotective stop). The rest is a
        hash, because Kraken allows 18 characters and a bar timestamp alone is
        longer than that.
        """
        if len(kind) != 1 or not kind.isalnum():
            raise ValueError(f"kind must be one alphanumeric character, got {kind!r}")
        digest = hashlib.sha256(f"{self.channel}|{kind}|{key}".encode()).hexdigest()
        cid = f"{CLIENT_PREFIX}{kind}{digest[:_CLIENT_ID_MAX - len(CLIENT_PREFIX) - 1]}"
        assert len(cid) == _CLIENT_ID_MAX
        return cid

    def _matching(self, listing: dict, cl_ord_id: str) -> list[VenueOrder]:
        """Orders in a listing that really carry our id. The filter is applied
        here too: an exchange that ignored the parameter must not hand us
        somebody else's order as ours."""
        return [VenueOrder.parse(txid, raw) for txid, raw in (listing or {}).items()
                if raw.get("cl_ord_id") == cl_ord_id]

    def find_order(self, cl_ord_id: str) -> Optional[VenueOrder]:
        """The order with this client id, open or closed, or None."""
        found = self._matching(
            (self.client.private_read("OpenOrders", {"cl_ord_id": cl_ord_id}) or {}).get("open"),
            cl_ord_id)
        found += self._matching(
            (self.client.private_read("ClosedOrders", {"cl_ord_id": cl_ord_id}) or {}).get("closed"),
            cl_ord_id)
        if len(found) > 1:
            raise ExecutorHalt(f"R4: {len(found)} orders carry client id {cl_ord_id} "
                               f"({[o.txid for o in found]})")
        return found[0] if found else None

    def _query(self, txid: str) -> Optional[VenueOrder]:
        """The order, or None while the exchange does not show it. Seen live on
        2026-11-14 (T1): ``QueryOrders`` answered "unknown order" for a txid
        that ``AddOrder`` had returned a moment earlier — the order existed and
        had filled. Not-yet-visible is a state to wait out, not a verdict."""
        try:
            result = self.client.private_read("QueryOrders", {"txid": txid}) or {}
        except KrakenAPIError as exc:
            if exc.has("EOrder:Unknown order") or exc.has("EOrder:Invalid order"):
                return None
            raise
        return VenueOrder.parse(txid, result[txid]) if txid in result else None

    def query(self, txid: str) -> VenueOrder:
        """An order that must exist (one the book already knows)."""
        for attempt in range(self._poll_attempts):
            order = self._query(txid)
            if order is not None:
                return order
            if attempt + 1 < self._poll_attempts:
                self._sleep(self._poll_interval)
        raise OrderOutcomeUnknown(f"order {txid} is not visible on the exchange after "
                                  f"{self._poll_attempts} checks")

    def open_orders(self) -> list[VenueOrder]:
        listing = (self.client.private_read("OpenOrders") or {}).get("open") or {}
        return [VenueOrder.parse(txid, raw) for txid, raw in listing.items()]

    # -- balances --------------------------------------------------------- #
    def balances(self) -> tuple[Decimal, Decimal]:
        """(quote, base) held on the account."""
        held = self.client.balance()
        return (held.get(self.rules.quote, Decimal("0")),
                held.get(self.rules.base, Decimal("0")))

    # -- R4–R6: submission ------------------------------------------------ #
    def _deadline(self) -> str:
        at = datetime.fromtimestamp(self._clock(), tz=timezone.utc) + timedelta(seconds=DEADLINE_SECONDS)
        return at.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def _await(self, txid: str, until_final: bool) -> VenueOrder:
        order = self.query(txid)
        for _ in range(self._poll_attempts):
            if order.is_final or (not until_final and order.status == "open"):
                return order
            self._sleep(self._poll_interval)
            order = self.query(txid)
        if until_final:
            raise OrderOutcomeUnknown(f"order {txid} still {order.status!r} after "
                                      f"{self._poll_attempts} checks")
        return order

    def _existing(self, cl_ord_id: str, until_final: bool) -> Optional[VenueOrder]:
        """R4: the order this client id already produced, if any. Checked BEFORE
        any sizing or balance check — after a run that died mid-way the account
        no longer looks the way it did when the order was sized."""
        existing = self.find_order(cl_ord_id)
        if existing is None:
            return None
        logger.info("order %s already exists as %s (%s) — not resending",
                    cl_ord_id, existing.txid, existing.status)
        return self._await(existing.txid, until_final)

    def _submit(self, params: dict, cl_ord_id: str, *, until_final: bool) -> VenueOrder:
        """Send one order at most once per client id."""
        existing = self._existing(cl_ord_id, until_final)
        if existing is not None:
            return existing
        request = {"pair": self.pair, "cl_ord_id": cl_ord_id,
                   "deadline": self._deadline(), **params}
        try:
            result = self.client.private_write("AddOrder", request)
        except KrakenOutcomeUnknown as exc:
            for _ in range(self._poll_attempts):
                self._sleep(self._poll_interval)
                found = self.find_order(cl_ord_id)
                if found is not None:
                    return self._await(found.txid, until_final)
            raise OrderOutcomeUnknown(f"{cl_ord_id}: {exc}") from exc
        txids = (result or {}).get("txid") or []
        if len(txids) != 1:
            raise OrderOutcomeUnknown(f"{cl_ord_id}: AddOrder answered without one txid: {result}")
        return self._await(txids[0], until_final)

    def buy(self, budget: Decimal, key: str, *, bot_base: Decimal = Decimal("0")) -> VenueOrder:
        """Market buy worth ``budget`` quote. ``bot_base`` is what the bot
        already holds, for the R7 exposure ceiling."""
        budget = Decimal(str(budget))
        rules = self.rules
        cid = self.client_order_id("b", key)
        existing = self._existing(cid, until_final=True)
        if existing is not None:
            return existing
        _bid, ask = self.client.best_bid_ask(self.pair)
        volume = self._sized_buy(budget, ask, bot_base)
        return self._submit({"type": "buy", "ordertype": "market", "volume": str(volume)},
                            cid, until_final=True)

    def _sized_buy(self, budget: Decimal, price: Decimal, bot_base: Decimal) -> Decimal:
        """Volume for a buy of ``budget`` at ``price``, after R3 and R7."""
        rules = self.rules
        volume = rules.floor_volume(budget / price)
        if not rules.allows(volume, price):
            raise ExecutorHalt(f"R3: buy of {volume} {rules.base} (£{budget}) is below the pair minimum")
        if budget > self.max_notional:
            raise ExecutorHalt(f"R7: order £{budget} exceeds the per-order ceiling £{self.max_notional}")
        quote, base = self.balances()
        equity = quote + base * price
        exposure_after = (Decimal(str(bot_base)) * price + budget) / equity if equity > 0 else Decimal("1")
        if exposure_after > MAX_EXPOSURE:
            raise ExecutorHalt(f"R7: exposure after the buy would be {exposure_after:.3f} "
                               f"> {MAX_EXPOSURE} of account equity £{equity:.2f}")
        if budget > quote:
            raise ExecutorHalt(f"buy £{budget} exceeds the cash on the account £{quote}")
        return volume

    def post_only(self, side: int, amount: Decimal, key: str, *,
                  bot_base: Decimal = Decimal("0")) -> VenueOrder:
        """A resting limit at the touch that may only add liquidity (maker fee).

        ``amount`` is a quote budget for a BUY and a base volume for a SELL. The
        order rests on our own side of the book — a buy at the bid, a sell at
        the ask — so it cannot cross. If the book moves in the instant between
        the quote and the order, Kraken refuses a ``post`` order that would
        take; that refusal is a clean "nothing happened" (docs/POSTONLY_DESIGN_2026-11-14.md).
        """
        rules = self.rules
        cid = self.client_order_id("m", key)
        existing = self._existing(cid, until_final=False)
        if existing is not None:
            return existing
        amount = Decimal(str(amount))
        bid, ask = self.client.best_bid_ask(self.pair)
        if side == BUY:
            price = rules.floor_price(bid)
            volume = self._sized_buy(amount, price, bot_base)
        else:
            price = rules.floor_price(ask)
            volume = rules.floor_volume(amount)
            if not rules.allows(volume, price):
                raise ExecutorHalt(f"R3: sell of {volume} {rules.base} is below the pair minimum")
        return self._submit({"type": "buy" if side == BUY else "sell", "ordertype": "limit",
                             "price": str(price), "volume": str(volume), "oflags": "post"},
                            cid, until_final=False)

    def sell(self, volume: Decimal, key: str) -> VenueOrder:
        """Market sell of exactly ``volume`` base — the bot's own quantity (R13)."""
        rules = self.rules
        cid = self.client_order_id("s", key)
        existing = self._existing(cid, until_final=True)
        if existing is not None:
            return existing
        volume = rules.floor_volume(Decimal(str(volume)))
        bid, _ask = self.client.best_bid_ask(self.pair)
        if not rules.allows(volume, bid):
            raise ExecutorHalt(f"R3: sell of {volume} {rules.base} is below the pair minimum")
        return self._submit({"type": "sell", "ordertype": "market", "volume": str(volume)},
                            cid, until_final=True)

    # -- R8–R9: the emergency stop ---------------------------------------- #
    def place_stop(self, volume: Decimal, trigger_price: Decimal, key: str) -> VenueOrder:
        """A resting stop-loss sell for the bot's whole quantity."""
        rules = self.rules
        volume = rules.floor_volume(Decimal(str(volume)))
        trigger = rules.floor_price(Decimal(str(trigger_price)))
        if not rules.allows(volume, trigger):
            raise ExecutorHalt(f"R3: stop for {volume} {rules.base} at £{trigger} is below the pair minimum")
        order = self._submit({"type": "sell", "ordertype": "stop-loss", "volume": str(volume),
                              "price": str(trigger), "trigger": "last"},
                             self.client_order_id("p", key), until_final=False)
        if order.status not in ("open", "pending") and not order.executed:
            raise ExecutorHalt(f"R8: stop {order.txid} is {order.status!r} straight after placement")
        return order

    def cancel(self, txid: str) -> VenueOrder:
        """Cancel and confirm (R9). Returns the order's final state — which may
        be ``closed`` if it filled before the cancel arrived."""
        try:
            self.client.private_write("CancelOrder", {"txid": txid})
        except KrakenAPIError as exc:
            if not exc.has("EOrder:Unknown order"):   # already final is fine; check below
                raise
        except KrakenOutcomeUnknown:
            pass                                      # the confirmation below decides
        order = self._await(txid, until_final=True)
        return order


def emergency_stop_price(entry_price: Decimal) -> Decimal:
    return Decimal(str(entry_price)) * (1 - EMERGENCY_STOP_PCT)


# --------------------------------------------------------------------------- #
# The bot's position on the venue
# --------------------------------------------------------------------------- #
@dataclass
class TraderState:
    """What the bot believes it holds on the venue. Persisted after every venue
    effect; decimals as strings so no float ever touches a quantity."""

    qty: str = "0"                       # base the bot owns
    entry_price: Optional[str] = None    # average price of the entry fill
    stop_txid: Optional[str] = None
    stop_seq: int = 0                    # makes each stop's client id unique
    blocked: bool = False                # stopped out — no entry until the signal returns to 0
    booked: list = field(default_factory=list)   # client ids already booked
    # A resting post-only order waiting for its deadline:
    # {"txid", "kind", "bar", "side", "ref_price", "placed_at"}
    pending: Optional[dict] = None
    # Fill records booked in the state but not yet handed to ``on_fill``. Saved
    # in the same write as ``booked``, so a fill can be late but never lost.
    outbox: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: Optional[dict]) -> "TraderState":
        state = cls(**(raw or {}))
        state.stop_seq = int(state.stop_seq)      # DynamoDB hands numbers back as floats
        state.booked = list(state.booked)
        state.outbox = list(state.outbox)
        return state

    def as_dict(self) -> dict:
        return asdict(self)


class KrakenTrader:
    """Enter, adjust, exit — with the stop handled in the pre-registered order.

    ``save(state_dict)`` is called after every venue effect and
    ``on_fill(record)`` at least once per executed order: the record waits in
    the saved state until ``on_fill`` has returned, so ``on_fill`` must be
    idempotent per ``order_id`` (the DynamoDB store is). ``fault(point)`` is called at
    named points and may raise, which is how the interrupted-run test (T4)
    proves that a half-finished run is completed, not repeated.
    """

    def __init__(self, executor: KrakenExecutor, state: TraderState, *,
                 save: Callable[[dict], None], on_fill: Callable[[dict], None],
                 fault: Optional[Callable[[str], None]] = None) -> None:
        self.ex = executor
        self.state = state
        self._save = save
        self._on_fill = on_fill
        self._fault = fault or (lambda _point: None)

    # -- bookkeeping ------------------------------------------------------ #
    @property
    def qty(self) -> Decimal:
        return Decimal(self.state.qty)

    def _persist(self) -> None:
        self._save(self.state.as_dict())

    def fill_record(self, order: VenueOrder, kind: str, bar: str,
                    extra: Optional[dict] = None) -> dict:
        return {
            **(extra or {}),
            "bar": bar, "time": order.closed_at, "kind": kind,
            "side": order.side, "qty": str(order.vol_exec),
            "actual_price": str(order.avg_price), "cost": str(order.cost),
            "fee_paid": str(order.fee), "fee_asset": "GBP", "base_asset": "BTC",
            "order_id": order.txid, "client_order_id": order.cl_ord_id,
            "ordertype": order.ordertype, "status": order.status,
            "symbol": self.ex.pair, "book_qty_after": self.state.qty,
        }

    def _book(self, order: VenueOrder, kind: str, bar: str,
              extra: Optional[dict] = None) -> bool:
        """Apply an executed order to the state exactly once."""
        cid = order.cl_ord_id or order.txid
        if cid in self.state.booked:
            return False
        if order.executed:
            delta = order.vol_exec if order.side == BUY else -order.vol_exec
            new_qty = self.qty + delta
            if new_qty < 0:
                raise ExecutorHalt(f"R13: booking {order.txid} would make the bot's quantity negative")
            if order.side == BUY and self.qty == 0:
                self.state.entry_price = str(order.avg_price)
            self.state.qty = str(new_qty) if new_qty else "0"     # not "0E-8"
            if new_qty == 0:
                self.state.entry_price = None
        self.state.booked.append(cid)
        if order.executed:
            self.state.outbox.append(self.fill_record(order, kind, bar, extra))
        self._persist()                       # booked and its record, in one write
        self._flush_fills()
        return True

    def _flush_fills(self) -> None:
        """Hand over the records still waiting — including any a run that died
        (or whose ``on_fill`` failed) left behind."""
        while self.state.outbox:
            self._on_fill(self.state.outbox[0])
            self.state.outbox.pop(0)
            self._persist()

    # -- the stop --------------------------------------------------------- #
    def _clear_stop(self, bar: str) -> None:
        """R9 step one: cancel the resting stop and confirm it is gone. If it
        filled first, that fill is booked and the position is flat and blocked."""
        if not self.state.stop_txid:
            return
        final = self.ex.cancel(self.state.stop_txid)
        self.state.stop_txid = None
        if final.executed:
            self._book(final, "stop", bar)
            self.state.blocked = True
        self._persist()

    def _set_stop(self) -> None:
        """R8: a stop for the whole quantity, 20% under the entry price."""
        if self.qty == 0 or self.state.stop_txid:
            return
        self.state.stop_seq += 1
        self._persist()                       # the sequence number is the stop's identity
        self._place_current_stop()

    def _place_current_stop(self) -> None:
        trigger = emergency_stop_price(Decimal(self.state.entry_price))
        order = self.ex.place_stop(self.qty, trigger, f"stop#{self.state.stop_seq}")
        self.state.stop_txid = order.txid
        self._persist()

    def _ensure_stop(self) -> None:
        """A position must have a stop. If the last run died between choosing
        the stop's identity and placing it, finish that one; if that stop
        already lived and died (cancelled, expired), place a fresh one."""
        if self.state.stop_seq > 0:
            cid = self.ex.client_order_id("p", f"stop#{self.state.stop_seq}")
            previous = self.ex.find_order(cid)
            if previous is None or not previous.is_final:
                self._place_current_stop()
                return
        self._set_stop()

    # -- R11 -------------------------------------------------------------- #
    def sync(self, bar: str) -> dict:
        """Start-of-run reconciliation. Returns a report; raises
        :class:`ExecutorHalt` on anything it cannot explain."""
        report: dict[str, Any] = {"stop": None, "events": []}
        self._flush_fills()
        self._recover_stop(report)
        if self.state.stop_txid:
            stop = self.ex.query(self.state.stop_txid)
            report["stop"] = stop.status
            if stop.executed and not stop.is_final:
                # Triggered and still selling: booking now would lose the rest.
                raise ExecutorHalt(f"stop {stop.txid} is executing ({stop.vol_exec} of "
                                   f"{stop.volume} sold) — run the reconciliation again")
            if stop.executed:
                self._book(stop, "stop", bar)
                self.state.stop_txid = None
                self.state.blocked = True
                self._persist()
                report["events"].append(f"stop {stop.txid} filled {stop.vol_exec} @ {stop.avg_price}")
            elif stop.is_final:
                self.state.stop_txid = None
                self._persist()
                report["events"].append(f"stop {stop.txid} is {stop.status} without a fill")
        quote, base = self.ex.balances()
        step = Decimal(1).scaleb(-self.ex.rules.lot_decimals)
        report.update(venue_quote=str(quote), venue_base=str(base), book_qty=self.state.qty)
        # What the pending maker order has already traded is not booked yet.
        expected_base = self.qty
        if self.state.pending:
            resting = self.ex.query(self.state.pending["txid"])
            expected_base += resting.vol_exec if resting.side == BUY else -resting.vol_exec
        if base + step < expected_base:
            raise ExecutorHalt(f"R11: the book holds {expected_base} but the account only {base}")
        if base > expected_base + step:
            report["events"].append(f"account holds {base - expected_base} more than the book (not ours, untouched)")
        expected = {self.state.stop_txid} if self.state.stop_txid else set()
        if self.state.pending:
            expected.add(self.state.pending["txid"])
            report["events"].append(f"maker order {self.state.pending['txid']} is pending — settle it")
        strangers = [o.txid for o in self.ex.open_orders() if o.txid not in expected]
        if strangers:
            raise ExecutorHalt(f"R11: open orders the book does not know: {strangers}")
        if self.qty > 0 and not self.state.stop_txid and not self.state.pending:
            report["events"].append("position without a stop — placing one")
            self._ensure_stop()
        report["protected"] = self.qty == 0 or bool(self.state.stop_txid)
        return report

    def _recover_stop(self, report: dict) -> None:
        """A run that died after the exchange took the stop but before its txid
        was saved: find that stop by its client id and take it back, so it is
        neither mistaken for a stranger's order nor left unbooked if it fired."""
        if self.state.stop_txid or self.state.stop_seq == 0 or self.qty == 0:
            return
        cid = self.ex.client_order_id("p", f"stop#{self.state.stop_seq}")
        found = self.ex.find_order(cid)
        if found is None:
            return
        if not found.is_final or (found.executed and cid not in self.state.booked):
            self.state.stop_txid = found.txid
            self._persist()
            report["events"].append(f"stop {found.txid} recovered by its client id")

    def _own_base(self, volume: Decimal) -> None:
        """R13 before anything is cancelled or sent: never sell more than the
        bot's own quantity, whatever else the account holds."""
        if volume > self.qty:
            raise ExecutorHalt(f"R13: sell of {volume} exceeds the bot's own quantity {self.qty}")

    # -- trading ---------------------------------------------------------- #
    def enter(self, budget: Decimal, bar: str) -> VenueOrder:
        if self.state.blocked:
            raise ExecutorHalt("entry is blocked after a stop-out until the signal returns to 0")
        if self.qty > 0:
            raise ExecutorHalt("enter() with a position already open — use adjust()")
        order = self.ex.buy(budget, f"enter#{bar}", bot_base=self.qty)
        self._fault("after_submit")
        self._book(order, "entry", bar)
        self._set_stop()
        return order

    def adjust(self, delta: Decimal, bar: str) -> VenueOrder:
        """Rebalance: ``delta`` > 0 buys that much quote, < 0 sells that much
        base. Cancel stop -> confirm -> trade -> new stop."""
        delta = Decimal(str(delta))
        if self.qty == 0:
            raise ExecutorHalt("adjust() without a position")
        if delta < 0:
            self._own_base(-delta)
        self._clear_stop(bar)
        if self.qty == 0:                      # the stop filled while we were cancelling it
            raise ExecutorHalt("the stop filled before the rebalance — position is flat")
        try:
            order = (self.ex.buy(delta, f"adjust#{bar}", bot_base=self.qty) if delta > 0
                     else self.ex.sell(-delta, f"adjust#{bar}"))
        except (ExecutorHalt, KrakenAPIError):
            self._ensure_position_stop()       # refused: nothing traded, protect again
            raise
        self._fault("after_submit")
        self._book(order, "adjust", bar)
        self._set_stop()
        return order

    def exit(self, bar: str) -> Optional[VenueOrder]:
        """Close the bot's whole quantity. Cancel stop -> confirm -> sell."""
        self._clear_stop(bar)
        if self.qty == 0:
            return None
        try:
            order = self.ex.sell(self.qty, f"exit#{bar}")
        except (ExecutorHalt, KrakenAPIError):
            self._ensure_position_stop()       # refused: still holding, protect again
            raise
        self._fault("after_submit")
        self._book(order, "exit", bar)
        return order

    # -- post-only (docs/POSTONLY_DESIGN_2026-11-14.md) -------------------- #
    def maker_open(self, kind: str, amount: Decimal, bar: str) -> VenueOrder:
        """Rest a post-only order for a signal-driven entry, adjust or exit.

        ``amount``: quote budget for a buy (entry, adjust > 0), base volume for
        a sell (adjust < 0); ignored for an exit, which sells the whole
        quantity. Forced exits (F7, kill switch) never come through here.
        """
        if self.state.pending:
            raise ExecutorHalt(f"maker order {self.state.pending['txid']} is still pending — settle it first")
        amount = Decimal(str(amount))
        if kind == "entry":
            if self.state.blocked:
                raise ExecutorHalt("entry is blocked after a stop-out until the signal returns to 0")
            if self.qty > 0:
                raise ExecutorHalt("entry with a position already open")
            side = BUY
        elif kind == "adjust":
            if self.qty == 0:
                raise ExecutorHalt("adjust without a position")
            side, amount = (BUY, amount) if amount > 0 else (SELL, -amount)
            if side == SELL:
                self._own_base(amount)
        elif kind == "exit":
            if self.qty == 0:
                raise ExecutorHalt("exit without a position")
            side, amount = SELL, self.qty
        else:
            raise ValueError(f"unknown kind {kind!r}")
        if kind != "entry":
            self._clear_stop(bar)              # the quantity is about to change / coins get reserved
            if self.qty == 0:
                raise ExecutorHalt("the stop filled before the order — position is flat")
            if kind == "exit":
                amount = self.qty
        bid, ask = self.ex.client.best_bid_ask(self.ex.pair)
        try:
            order = self.ex.post_only(side, amount, f"{kind}#{bar}", bot_base=self.qty)
        except (ExecutorHalt, KrakenAPIError) as exc:
            self._ensure_position_stop()       # refused: nothing rests, protect again
            if isinstance(exc, KrakenAPIError) and exc.has("EOrder:Post only"):
                raise ExecutorHalt("the book moved and the post-only order would have taken — "
                                   "nothing was placed, run the step again") from exc
            raise
        self.state.pending = {"txid": order.txid, "kind": kind, "bar": bar, "side": side,
                              "ref_price": str((bid + ask) / 2),
                              "placed_at": datetime.now(timezone.utc).isoformat()}
        self._persist()
        return order

    def _ensure_position_stop(self) -> None:
        """Put the stop back if there is a position large enough to carry one."""
        if self.qty == 0 or self.state.stop_txid:
            return
        if self.ex.rules.allows(self.qty, emergency_stop_price(Decimal(self.state.entry_price))):
            self._set_stop()

    def maker_settle(self) -> dict:
        """The deadline has passed: take what filled, cancel the rest, finish
        the remainder as a taker, put the stop back. Idempotent."""
        pending = self.state.pending
        if not pending:
            return {"settled": False, "reason": "nothing pending"}
        kind, bar, side = pending["kind"], pending["bar"], int(pending["side"])
        ref = {"ref_price": pending["ref_price"], "placed_at": pending["placed_at"]}
        order = self.ex.query(pending["txid"])
        if not order.is_final:
            order = self.ex.cancel(order.txid)
        result = {"settled": True, "maker": str(order.vol_exec), "taker": "0", "dust": "0",
                  "maker_txid": order.txid, "taker_txid": None}
        self._book(order, kind, bar, {**ref, "liquidity": "maker"})
        remaining = order.volume - order.vol_exec
        if remaining > 0:
            rules = self.ex.rules
            bid, ask = self.ex.client.best_bid_ask(self.ex.pair)
            touch = ask if side == BUY else bid
            if rules.allows(rules.floor_volume(remaining), touch):
                taker = (self.ex.buy(remaining * ask, f"{kind}#{bar}#taker", bot_base=self.qty)
                         if side == BUY else self.ex.sell(remaining, f"{kind}#{bar}#taker"))
                self._book(taker, kind, bar, {**ref, "liquidity": "taker"})
                result.update(taker=str(taker.vol_exec), taker_txid=taker.txid)
            else:
                result["dust"] = str(remaining)      # below the pair minimum — left as is, reported
        self.state.pending = None
        self._persist()
        self._ensure_position_stop()
        return result

    def unblock(self) -> None:
        """The strategy's target went back to 0 — entries are allowed again."""
        if self.state.blocked:
            self.state.blocked = False
            self._persist()
