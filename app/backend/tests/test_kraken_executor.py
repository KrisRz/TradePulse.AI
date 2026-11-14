"""Kraken executor (kraken_executor.py) against an in-memory exchange.

The fake below behaves like Kraken where it matters for rules R1–R13: orders
are found by client id, a resting stop RESERVES the coins it would sell, a
market order fills at the touch and pays its fee in the quote currency, and a
write can be made to "time out" either before or after it took effect.
"""

from decimal import Decimal

import pytest

from app.backend.paper_trading.execution import BUY, SELL
from app.backend.paper_trading.kraken_api import (
    KrakenAPIError, KrakenOutcomeUnknown, PairRules,
)
from app.backend.paper_trading.kraken_executor import (
    ALLOWED_PERMISSIONS, ExecutorHalt, KrakenExecutor, KrakenTrader,
    OrderOutcomeUnknown, TraderState, emergency_stop_price,
)

D = Decimal
RULES = PairRules("XXBTZGBP", "XBTGBP", "XXBT", "ZGBP", D("0.00006"), D("0.43"),
                  D("0.1"), 8, "online")
FEE = D("0.008")


class FakeKraken:
    def __init__(self, gbp="10", btc="0", bid="49990", ask="50000"):
        self.gbp, self.btc = D(gbp), D(btc)
        self.bid, self.ask = D(bid), D(ask)
        self.orders: dict[str, dict] = {}
        self.permissions = sorted(ALLOWED_PERMISSIONS)
        self.status = "online"
        self.fail_next_write = None      # "before" | "after"
        self.query_lag = 0               # QueryOrders answers "unknown" this many times
        self.writes = []
        self._n = 0
        self._t = 1_800_000_000.0

    # -- public ----------------------------------------------------------- #
    def system_status(self):
        return self.status

    def pair_rules(self, pair):
        return RULES

    def best_bid_ask(self, pair):
        return self.bid, self.ask

    def balance(self):
        return {"ZGBP": self.gbp, "XXBT": self.btc}

    # -- private ---------------------------------------------------------- #
    def private_read(self, name, params=None):
        params = params or {}
        if name == "GetApiKeyInfo":
            return {"permissions": list(self.permissions)}
        if name == "TradeVolume":
            return {"fees": {"XXBTZGBP": {"fee": "0.8000"}}}
        if name in ("OpenOrders", "ClosedOrders"):
            want_open = name == "OpenOrders"
            cid = params.get("cl_ord_id")
            out = {t: o for t, o in self.orders.items()
                   if (o["status"] in ("open", "pending")) == want_open
                   and (cid is None or o["cl_ord_id"] == cid)}
            return {"open": out} if want_open else {"closed": out, "count": len(out)}
        if name == "QueryOrders":
            t = params["txid"]
            if self.query_lag > 0:
                self.query_lag -= 1
                raise KrakenAPIError(["EOrder:Unknown order"], name)
            return {t: self.orders[t]} if t in self.orders else {}
        raise AssertionError(f"unexpected read {name}")

    def _reserved(self):
        return sum((D(o["vol"]) for o in self.orders.values()
                    if o["status"] == "open" and o["descr"]["type"] == "sell"), D("0"))

    def _fill(self, order, price):
        vol = D(order["vol"])
        cost = vol * price
        fee = cost * FEE
        if order["descr"]["type"] == "buy":
            self.gbp -= cost + fee
            self.btc += vol
        else:
            self.gbp += cost - fee
            self.btc -= vol
        self._t += 1
        order.update(status="closed", vol_exec=str(vol), cost=str(cost), fee=str(fee),
                     price=str(price), closetm=self._t)

    def _add(self, p):
        if p["volume"] and D(p["volume"]) < RULES.ordermin:
            raise KrakenAPIError(["EGeneral:Invalid arguments:volume minimum not met"], "AddOrder")
        if any(o["cl_ord_id"] == p["cl_ord_id"] and o["status"] == "open"
               for o in self.orders.values()):
            raise KrakenAPIError(["EOrder:Duplicate cl_ord_id"], "AddOrder")
        vol = D(p["volume"])
        if p["type"] == "buy" and vol * self.ask * (1 + FEE) > self.gbp:
            raise KrakenAPIError(["EOrder:Insufficient funds"], "AddOrder")
        if p["type"] == "sell" and vol > self.btc - self._reserved():
            raise KrakenAPIError(["EOrder:Insufficient funds"], "AddOrder")
        self._n += 1
        txid = f"O{self._n:05d}"
        order = {"status": "open", "cl_ord_id": p["cl_ord_id"], "vol": p["volume"],
                 "vol_exec": "0", "cost": "0", "fee": "0", "price": "0",
                 "descr": {"type": p["type"], "ordertype": p["ordertype"],
                           "price": p.get("price", "0")}}
        self.orders[txid] = order
        if p["ordertype"] == "market":
            self._fill(order, self.ask if p["type"] == "buy" else self.bid)
        return {"txid": [txid]}

    def private_write(self, name, params=None):
        params = dict(params or {})
        self.writes.append((name, params))
        fail, self.fail_next_write = self.fail_next_write, None
        if fail == "before":
            raise KrakenOutcomeUnknown(name, "Timeout")
        if name == "AddOrder":
            assert "deadline" in params and len(params["cl_ord_id"]) <= 18
            result = self._add(params)
        elif name == "CancelOrder":
            order = self.orders.get(params["txid"])
            if order is None or order["status"] != "open":
                raise KrakenAPIError(["EOrder:Unknown order"], name)
            self._t += 1
            order.update(status="canceled", closetm=self._t)
            result = {"count": 1}
        else:
            raise AssertionError(f"unexpected write {name}")
        if fail == "after":
            raise KrakenOutcomeUnknown(name, "Timeout")
        return result

    # -- test helpers ----------------------------------------------------- #
    def trigger_stops(self, last):
        for order in self.orders.values():
            if (order["status"] == "open" and order["descr"]["ordertype"] == "stop-loss"
                    and D(last) <= D(order["descr"]["price"])):
                self._fill(order, D(last))

    def open_stops(self):
        return [o for o in self.orders.values()
                if o["status"] == "open" and o["descr"]["ordertype"] == "stop-loss"]

    def adds(self):
        return [p for n, p in self.writes if n == "AddOrder"]


def make(venue=None, state=None, fault=None, max_notional="1000"):
    venue = venue or FakeKraken()
    ex = KrakenExecutor(venue, max_notional=D(max_notional), sleep=lambda _s: None,
                        poll_attempts=3)
    ex.preflight()
    saved, fills = [], []
    trader = KrakenTrader(ex, state or TraderState(), save=saved.append,
                          on_fill=fills.append, fault=fault)
    return venue, ex, trader, saved, fills


# --------------------------------------------------------------------------- #
# R1–R3 preflight
# --------------------------------------------------------------------------- #
def test_preflight_reads_rules_and_fee():
    venue = FakeKraken()
    pre = KrakenExecutor(venue, max_notional=D("1000")).preflight()
    assert pre.taker_fee == D("0.008") and pre.rules == RULES


@pytest.mark.parametrize("extra", ["withdraw-funds", "deposit-funds", "earn-funds", "export-data"])
def test_r1_a_key_that_can_do_more_stops_everything(extra):
    venue = FakeKraken()
    venue.permissions.append(extra)
    with pytest.raises(ExecutorHalt, match="R1"):
        KrakenExecutor(venue, max_notional=D("1000")).preflight()


def test_r1_a_key_whose_permissions_cannot_be_read_stops_everything():
    venue = FakeKraken()
    venue.permissions = []
    with pytest.raises(ExecutorHalt, match="R1"):
        KrakenExecutor(venue, max_notional=D("1000")).preflight()


def test_r2_no_order_when_the_exchange_is_not_online():
    venue = FakeKraken()
    venue.status = "cancel_only"
    with pytest.raises(ExecutorHalt, match="R2"):
        KrakenExecutor(venue, max_notional=D("1000")).preflight()


def test_no_order_without_preflight():
    ex = KrakenExecutor(FakeKraken(), max_notional=D("1000"))
    with pytest.raises(ExecutorHalt, match="preflight"):
        ex.buy(D("5"), "k")


# --------------------------------------------------------------------------- #
# R4 identity
# --------------------------------------------------------------------------- #
def test_client_id_is_stable_distinct_and_fits_krakens_limit():
    ex = KrakenExecutor(FakeKraken(), max_notional=D("1"))
    a = ex.client_order_id("b", "enter#2026-11-15 00:00:00+00:00")
    assert a == ex.client_order_id("b", "enter#2026-11-15 00:00:00+00:00")
    assert len(a) == 18 and a.startswith("tpkb")
    assert a != ex.client_order_id("s", "enter#2026-11-15 00:00:00+00:00")
    assert a != ex.client_order_id("b", "enter#2026-11-16 00:00:00+00:00")
    other = KrakenExecutor(FakeKraken(), max_notional=D("1"), channel="XBTGBP_pilot")
    assert a != other.client_order_id("b", "enter#2026-11-15 00:00:00+00:00")


def test_an_order_carrying_another_client_id_is_never_taken_for_ours():
    venue, ex, *_ = make()
    venue.orders["OX"] = {"status": "closed", "cl_ord_id": "someone-else", "vol": "1",
                          "vol_exec": "1", "cost": "1", "fee": "0",
                          "descr": {"type": "buy", "ordertype": "market"}}
    venue.private_read = (lambda orig: lambda name, params=None:
                          ({"closed": venue.orders} if name == "ClosedOrders" else orig(name, params))
                          )(venue.private_read)   # an exchange that ignores the filter
    assert ex.find_order(ex.client_order_id("b", "k")) is None


# --------------------------------------------------------------------------- #
# Entry, stop, R7
# --------------------------------------------------------------------------- #
def test_enter_buys_books_the_venue_fill_and_rests_a_stop_20pct_under_entry():
    venue, ex, trader, saved, fills = make()
    order = trader.enter(D("6.20"), "bar1")
    assert order.side == BUY and order.vol_exec == D("0.00012400")
    assert trader.qty == venue.btc == D("0.000124")
    assert D(trader.state.entry_price) == D("50000")
    (stop,) = venue.open_stops()
    assert D(stop["vol"]) == trader.qty
    assert D(stop["descr"]["price"]) == emergency_stop_price(D("50000")) == D("40000")
    (fill,) = fills
    assert fill["kind"] == "entry" and D(fill["fee_paid"]) == D("6.2") * FEE
    assert D(fill["cost"]) + D(fill["fee_paid"]) == D("10") - venue.gbp     # fee paid in GBP
    assert saved[-1]["stop_txid"] == trader.state.stop_txid


def test_r7_a_buy_that_would_pass_65pct_of_the_account_is_not_sent():
    venue, ex, trader, *_ = make()
    with pytest.raises(ExecutorHalt, match="R7"):
        trader.enter(D("6.60"), "bar1")
    assert venue.adds() == []


def test_r7_per_order_ceiling():
    venue, ex, trader, *_ = make(FakeKraken(gbp="1000"), max_notional="5")
    with pytest.raises(ExecutorHalt, match="ceiling"):
        trader.enter(D("6"), "bar1")
    assert venue.adds() == []


def test_r3_an_order_below_the_pair_minimum_is_not_sent():
    venue, ex, trader, *_ = make()
    with pytest.raises(ExecutorHalt, match="R3"):
        trader.enter(D("2"), "bar1")          # 0.00004 BTC < 0.00006
    assert venue.adds() == []


# --------------------------------------------------------------------------- #
# R4/R5 idempotency and unclear answers
# --------------------------------------------------------------------------- #
def test_the_same_bar_twice_sends_one_order():
    venue, ex, trader, saved, fills = make()
    trader.enter(D("6.20"), "bar1")
    again = ex.buy(D("6.20"), "enter#bar1", bot_base=D("0"))
    assert len([p for p in venue.adds() if p["type"] == "buy"]) == 1
    assert again.txid == "O00001"


def test_timeout_after_the_order_took_effect_is_found_not_resent():
    venue, ex, trader, saved, fills = make()
    venue.fail_next_write = "after"
    trader.enter(D("6.20"), "bar1")
    assert len([p for p in venue.adds() if p["type"] == "buy"]) == 1
    assert trader.qty == D("0.000124") and len(fills) == 1


def test_timeout_before_the_order_existed_raises_and_the_rerun_sends_it_once():
    venue, ex, trader, saved, fills = make()
    venue.fail_next_write = "before"
    with pytest.raises(OrderOutcomeUnknown):
        trader.enter(D("6.20"), "bar1")
    assert trader.qty == 0 and venue.btc == 0
    trader.enter(D("6.20"), "bar1")
    assert venue.btc == trader.qty == D("0.000124")


def test_t4_run_that_died_after_the_buy_is_completed_not_repeated():
    class Crash(RuntimeError):
        pass

    def fault(point):
        raise Crash(point)

    venue, ex, trader, saved, fills = make(fault=fault)
    with pytest.raises(Crash):
        trader.enter(D("6.20"), "bar1")
    assert venue.btc == D("0.000124") and trader.qty == 0 and not fills   # bought, not booked

    # next run: fresh objects, the persisted (empty) state, no fault
    venue, ex, trader, saved, fills = make(venue, TraderState())
    report = trader.sync("bar1")
    assert any("more than the book" in e for e in report["events"])
    trader.enter(D("6.20"), "bar1")       # cash is now too low to size it again — must not matter
    assert len([p for p in venue.adds() if p["type"] == "buy"]) == 1
    assert trader.qty == D("0.000124") and len(fills) == 1
    assert len(venue.open_stops()) == 1


# --------------------------------------------------------------------------- #
# R9 adjust and exit
# --------------------------------------------------------------------------- #
def test_a_resting_stop_reserves_the_coins_so_cancel_must_come_first():
    venue, ex, trader, *_ = make()
    trader.enter(D("6.20"), "bar1")
    with pytest.raises(KrakenAPIError, match="Insufficient funds"):
        ex.sell(D("0.00006"), "naive")


def test_adjust_cancels_the_stop_trades_and_rests_a_new_stop_for_the_new_quantity():
    venue, ex, trader, saved, fills = make()
    trader.enter(D("6.20"), "bar1")
    first_stop = trader.state.stop_txid
    trader.adjust(D("-0.00006"), "bar2")
    assert venue.orders[first_stop]["status"] == "canceled"
    assert trader.qty == venue.btc == D("0.000064")
    (stop,) = venue.open_stops()
    assert D(stop["vol"]) == D("0.000064") and D(stop["descr"]["price"]) == D("40000")
    kinds = [(n, p.get("ordertype")) for n, p in venue.writes]
    assert kinds == [("AddOrder", "market"), ("AddOrder", "stop-loss"), ("CancelOrder", None),
                     ("AddOrder", "market"), ("AddOrder", "stop-loss")]
    assert [f["kind"] for f in fills] == ["entry", "adjust"]


def test_adjust_interrupted_after_the_sell_resumes_without_a_second_sell():
    class Crash(RuntimeError):
        pass

    venue, ex, trader, saved, fills = make()
    trader.enter(D("6.20"), "bar1")
    trader._fault = lambda point: (_ for _ in ()).throw(Crash(point))
    with pytest.raises(Crash):
        trader.adjust(D("-0.00006"), "bar2")
    state = TraderState.from_dict(saved[-1])
    assert state.stop_txid is None and D(state.qty) == D("0.000124")   # sold, not booked

    venue, ex, trader, saved2, fills2 = make(venue, state)
    with pytest.raises(ExecutorHalt, match="R11"):
        trader.sync("bar2")               # book says more than the account holds: stop and look
    trader.adjust(D("-0.00006"), "bar2")  # the operator reruns the same step
    assert len([p for p in venue.adds() if p["type"] == "sell" and p["ordertype"] == "market"]) == 1
    assert trader.qty == venue.btc == D("0.000064")
    assert len(venue.open_stops()) == 1 and [f["kind"] for f in fills2] == ["adjust"]


def test_exit_cancels_the_stop_sells_the_bots_quantity_and_leaves_nothing_open():
    venue, ex, trader, saved, fills = make(FakeKraken(gbp="10", btc="0.5"))   # 0.5 BTC is not ours
    trader.enter(D("6.20"), "bar1")
    order = trader.exit("bar2")
    assert order.side == SELL and order.vol_exec == D("0.000124")
    assert trader.qty == 0 and venue.btc == D("0.5")          # R13: only our quantity
    assert venue.open_stops() == [] and trader.state.stop_txid is None
    assert trader.state.entry_price is None
    assert trader.exit("bar2") is None                        # idempotent


# --------------------------------------------------------------------------- #
# R11 reconciliation
# --------------------------------------------------------------------------- #
def test_stop_that_fired_between_runs_is_booked_and_blocks_reentry():
    venue, ex, trader, saved, fills = make()
    trader.enter(D("6.20"), "bar1")
    venue.trigger_stops("39900")
    venue, ex, trader, saved, fills = make(venue, TraderState.from_dict(saved[-1]))
    report = trader.sync("bar2")
    assert report["stop"] == "closed" and trader.qty == 0 and venue.btc == 0
    assert trader.state.blocked and trader.state.stop_txid is None
    (fill,) = fills
    assert fill["kind"] == "stop" and D(fill["actual_price"]) == D("39900")
    with pytest.raises(ExecutorHalt, match="blocked"):
        trader.enter(D("3.20"), "bar2")
    trader.unblock()
    trader.enter(D("3.20"), "bar3")
    assert trader.qty > 0


def test_sync_is_quiet_when_book_and_venue_agree():
    venue, ex, trader, saved, fills = make()
    trader.enter(D("6.20"), "bar1")
    report = trader.sync("bar2")
    assert report["events"] == [] and report["protected"] and report["stop"] == "open"


def test_sync_halts_when_the_account_holds_less_than_the_book():
    venue, ex, trader, *_ = make(state=TraderState(qty="0.001", entry_price="50000"))
    with pytest.raises(ExecutorHalt, match="R11"):
        trader.sync("bar1")


def test_sync_halts_on_an_open_order_the_book_does_not_know():
    venue, ex, trader, *_ = make(FakeKraken(btc="0.001"))
    venue.private_write("AddOrder", {"cl_ord_id": "manual", "type": "sell", "ordertype": "stop-loss",
                                     "volume": "0.001", "price": "1", "deadline": "x"})
    with pytest.raises(ExecutorHalt, match="open orders the book does not know"):
        trader.sync("bar1")


def test_a_stop_cancelled_by_hand_is_replaced_by_a_fresh_one():
    venue, ex, trader, saved, fills = make()
    trader.enter(D("6.20"), "bar1")
    venue.private_write("CancelOrder", {"txid": trader.state.stop_txid})
    report = trader.sync("bar2")
    assert report["protected"] and len(venue.open_stops()) == 1
    assert trader.state.stop_seq == 2 and not fills[1:]


def test_run_that_died_before_placing_the_stop_gets_its_stop_on_sync():
    venue, ex, trader, saved, fills = make()
    trader.enter(D("6.20"), "bar1")
    venue.private_write("CancelOrder", {"txid": trader.state.stop_txid})
    del venue.orders[trader.state.stop_txid]          # as if it had never been placed
    state = TraderState.from_dict({**saved[-1], "stop_txid": None})
    venue, ex, trader, saved, fills = make(venue, state)
    trader.sync("bar2")
    assert len(venue.open_stops()) == 1 and trader.state.stop_seq == 1


def test_stop_that_fills_while_being_cancelled_is_booked_and_the_rebalance_stops():
    venue, ex, trader, saved, fills = make()
    trader.enter(D("6.20"), "bar1")
    venue.trigger_stops("39000")
    with pytest.raises(ExecutorHalt, match="stop filled"):
        trader.adjust(D("-0.00006"), "bar2")
    assert trader.qty == 0 and trader.state.blocked
    assert [f["kind"] for f in fills] == ["entry", "stop"]


def test_an_order_is_booked_once_however_often_the_step_is_rerun():
    venue, ex, trader, saved, fills = make()
    trader.enter(D("6.20"), "bar1")
    trader.adjust(D("-0.00006"), "bar2")
    trader.adjust(D("-0.00006"), "bar2")      # same step again: same order, no second booking
    assert len([p for p in venue.adds() if p["type"] == "sell" and p["ordertype"] == "market"]) == 1
    assert trader.qty == venue.btc == D("0.000064")
    assert [f["kind"] for f in fills] == ["entry", "adjust"]
    assert len(venue.open_stops()) == 1


def test_state_survives_a_dynamodb_round_trip():
    state = TraderState.from_dict({"qty": "0.000124", "entry_price": "50000", "stop_txid": "O1",
                                   "stop_seq": 2.0, "blocked": False, "booked": ["a"]})
    assert state.stop_seq == 2 and isinstance(state.stop_seq, int)


def test_t1_live_bug_order_not_yet_visible_right_after_submit_is_waited_out():
    """2026-11-14, first real order: AddOrder returned a txid, QueryOrders said
    "unknown order" a moment later, the run stopped with the coins bought, the
    book empty and no stop. The order must be waited for, booked and protected."""
    venue, ex, trader, saved, fills = make()
    venue.query_lag = 2
    trader.enter(D("6.20"), "bar1")
    assert trader.qty == venue.btc == D("0.000124")
    assert len(fills) == 1 and len(venue.open_stops()) == 1


def test_an_order_that_never_becomes_visible_is_outcome_unknown_not_a_halt():
    venue, ex, trader, saved, fills = make()
    venue.query_lag = 99
    with pytest.raises(OrderOutcomeUnknown):
        trader.enter(D("6.20"), "bar1")
    venue.query_lag = 0
    trader.enter(D("6.20"), "bar1")           # the rerun finds it by client id and finishes
    assert len([p for p in venue.adds() if p["type"] == "buy"]) == 1
    assert trader.qty == D("0.000124") and len(venue.open_stops()) == 1
