"""Tests for the execution-safety fixes of 2026-09-05 (audit 2026-09-04, KROK 1).

Every test here is written to FAIL against the code as it stood on 2026-09-04.
That is the point: the audit found four ways this channel could trade twice, or
trade on a book that no longer described the account, and none of them would have
shown up as an error. A test that merely passes proves nothing about a failure
mode; each of these reproduces the failure first.

The failures, in the order the audit ranked them:

CRITICAL-1  an order POST that timed out was retried blindly, with no client
            order id, so the venue had no way to recognise the second copy;
CRITICAL-2  the order went out before ``last_bar`` was saved, so a retried
            invocation re-traded the bar;
HIGH-1      the kill switch's execution drag was computed BEFORE the step that
            produced the fill, so T2 could never accumulate and stood at 0.0 on
            production after three real fills;
HIGH-2      a book that disagreed with the account only logged a warning.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import parse_qsl, urlparse

import pytest
import requests

from app.backend.paper_trading import venue_handler
from app.backend.paper_trading.binance_demo import (
    BinanceAPIError,
    BinanceDemoExecutor,
    OrderSubmissionUncertain,
    Reconciliation,
)
from app.backend.paper_trading.execution import BUY, SELL, Order
from app.backend.paper_trading.killswitch import KillSwitchState
from app.backend.paper_trading.portfolio import PaperPortfolio
from app.backend.paper_trading.shadow import ShadowRunner
from app.backend.paper_trading.state_store import (
    ConcurrentStateWrite,
    DynamoDBStateStore,
)
from app.backend.paper_trading.venue_handler import BookOutOfSync, attach_venue

ORDER_PATH = "/api/v3/order"

EXCHANGE_INFO = {
    "symbols": [{
        "symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT",
        "status": "TRADING",
        "filters": [
            {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
            {"filterType": "LOT_SIZE", "minQty": "0.00001", "maxQty": "9000",
             "stepSize": "0.00001"},
            {"filterType": "NOTIONAL", "minNotional": "5", "applyMinToMarket": True},
        ],
    }]
}

ACCOUNT = {"balances": [{"asset": "BTC", "free": "0.05", "locked": "0"},
                        {"asset": "USDT", "free": "5000", "locked": "0"}]}


class Response:
    def __init__(self, payload, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class Session:
    """Fake transport keyed by (method, path) — a GET and a POST on the same
    path are different things here, which is exactly the distinction the
    recovery logic depends on."""

    def __init__(self, routes):
        self.routes = {k: list(v) for k, v in routes.items()}
        self.log = []

    def request(self, method, url, headers=None, timeout=None):
        parsed = urlparse(url)
        self.log.append((method, parsed.path, dict(parse_qsl(parsed.query))))
        queue = self.routes.get((method, parsed.path))
        if not queue:
            raise AssertionError(f"unexpected {method} {parsed.path}")
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, Exception):
            raise item
        return item if isinstance(item, Response) else Response(item)

    def count(self, method, path):
        return sum(1 for m, p, _q in self.log if m == method and p == path)

    def sent(self, method, path):
        return [q for m, p, q in self.log if m == method and p == path]


def filled_order(order_id=999, client_id=None, qty="0.0031", price="64000.00",
                 with_fills=True):
    executed = Decimal(qty)
    body = {
        "symbol": "BTCUSDT", "orderId": order_id, "status": "FILLED",
        "executedQty": str(executed),
        "cummulativeQuoteQty": str(executed * Decimal(price)),
    }
    if client_id:
        body["clientOrderId"] = client_id
    if with_fills:
        body["fills"] = [{"price": price, "qty": qty, "commission": "0.0002",
                          "commissionAsset": "BNB"}]
    return body


def make_executor(routes, **kwargs):
    routes.setdefault(("GET", "/api/v3/exchangeInfo"), [EXCHANGE_INFO])
    routes.setdefault(("GET", "/api/v3/account"), [ACCOUNT])
    routes.setdefault(("GET", "/api/v3/time"), [{"serverTime": 1_786_045_000_000}])
    session = Session(routes)
    kwargs.setdefault("sleep", lambda _s: None)
    kwargs.setdefault("client_prefix", "tpv4h")
    return BinanceDemoExecutor("k", "s", session=session, **kwargs), session


# ------------------------------------------------------- the idempotency key --
def test_the_id_depends_on_the_decision_not_on_when_it_was_sent():
    """Two runs of the same bar must produce the same id, or the venue cannot
    tell a retry from a second trade."""
    a, _ = make_executor({})
    b, _ = make_executor({})
    bar = "2026-09-05 12:00:00+00:00"
    assert a.client_order_id(BUY, bar) == b.client_order_id(BUY, bar)
    assert a.client_order_id(BUY, bar) != a.client_order_id(SELL, bar)
    assert a.client_order_id(BUY, bar) != a.client_order_id(BUY, "2026-09-05 16:00:00+00:00")


def test_the_id_fits_what_binance_accepts():
    """``^[\\.A-Za-z0-9_-]{1,36}$`` — a bar timestamp does not, hence the hash."""
    import re

    ex, _ = make_executor({})
    cid = ex.client_order_id(BUY, "2026-09-05 12:00:00+00:00")
    assert re.match(r"^[.A-Za-z0-9_-]{1,36}$", cid), cid


def test_a_channel_can_recognise_its_own_orders_on_a_shared_account():
    """The demo account also carries the heartbeat's daily round-trips."""
    venue, _ = make_executor({}, client_prefix="tpv4h")
    assert venue.is_ours(venue.client_order_id(BUY, "bar"))
    assert not venue.is_ours("tpsh-0123456789abcdef0123")   # the heartbeat's
    assert not venue.is_ours("x-HNA2TXFJ")                  # Binance's own


def test_every_order_carries_its_id_to_the_venue():
    """Without ``newClientOrderId`` nothing downstream can deduplicate anything."""
    ex, session = make_executor({("POST", ORDER_PATH): [filled_order()]})
    bar = "2026-09-05 12:00:00+00:00"
    ex.execute(Order(side=BUY, reference_price=64_000.0, time=bar, qty=0.0031))

    sent = session.sent("POST", ORDER_PATH)[0]
    assert sent["newClientOrderId"] == ex.client_order_id(BUY, bar)


def test_the_key_can_be_given_explicitly_for_a_trade_that_is_not_bar_driven():
    """A kill-switch flatten happens at the clock, so it names its own key."""
    ex, session = make_executor({("POST", ORDER_PATH): [filled_order()]})
    ex.execute(Order(side=SELL, reference_price=64_000.0, time="2026-09-05T12:34:56",
                     qty=0.0031, idempotency_key="halt@2026-09-05 12:00:00+00:00"))

    sent = session.sent("POST", ORDER_PATH)[0]
    assert sent["newClientOrderId"] == ex.client_order_id(
        SELL, "halt@2026-09-05 12:00:00+00:00")


# --------------------------------------------- CRITICAL-1: the unanswered POST --
def test_a_timeout_after_the_order_filled_does_not_send_a_second_one():
    """The failure that costs real money: the order landed, the answer did not.

    The old code retried the POST inside ``_request`` — with no client order id,
    so the venue had no way to refuse the copy — and the bot ended up holding
    twice what it decided to hold.
    """
    ex, session = make_executor({
        ("POST", ORDER_PATH): [requests.ConnectionError("connection reset")],
        ("GET", ORDER_PATH): [filled_order(order_id=999, with_fills=False)],
        ("GET", "/api/v3/myTrades"): [[
            {"price": "64000.00", "qty": "0.0031", "commission": "0.0002",
             "commissionAsset": "BNB"}]],
    })
    fill = ex.execute(Order(side=BUY, reference_price=64_000.0, time="bar-1",
                            qty=0.0031))

    assert session.count("POST", ORDER_PATH) == 1      # exactly one order exists
    assert fill.order_id == "999"
    assert fill.qty == pytest.approx(0.0031)
    assert fill.price == pytest.approx(64_000.0)
    assert fill.fee_paid == pytest.approx(0.0002)      # recovered from myTrades
    assert ex.rejections() == []                       # it filled; nothing was refused


def test_a_timeout_before_the_order_arrived_is_resent_once_with_the_same_id():
    """Having *asked*, resending is safe — and must reuse the id, not mint a new one."""
    ex, session = make_executor({
        ("POST", ORDER_PATH): [requests.ConnectTimeout("timed out"), filled_order()],
        ("GET", ORDER_PATH): [Response({"code": -2013, "msg": "Order does not exist."}, 400)],
    })
    ex.execute(Order(side=BUY, reference_price=64_000.0, time="bar-1", qty=0.0031))

    posts = session.sent("POST", ORDER_PATH)
    assert len(posts) == 2
    assert posts[0]["newClientOrderId"] == posts[1]["newClientOrderId"]


def test_twice_unanswered_stops_the_run_instead_of_guessing():
    ex, session = make_executor({
        ("POST", ORDER_PATH): [requests.ConnectTimeout("timed out")],
        ("GET", ORDER_PATH): [Response({"code": -2013, "msg": "Order does not exist."}, 400)],
    })
    with pytest.raises(OrderSubmissionUncertain, match="reconcile"):
        ex.execute(Order(side=BUY, reference_price=64_000.0, time="bar-1", qty=0.0031))

    assert session.count("POST", ORDER_PATH) == 2      # never a third


def test_a_server_error_on_the_order_is_not_retried_blindly():
    """A 5xx used to be retried up to ``max_retries`` times, four orders deep."""
    ex, session = make_executor({
        ("POST", ORDER_PATH): [Response({"code": -1000, "msg": "boom"}, 503)],
        ("GET", ORDER_PATH): [filled_order(order_id=1001)],
    })
    fill = ex.execute(Order(side=BUY, reference_price=64_000.0, time="bar-1",
                            qty=0.0031))

    assert session.count("POST", ORDER_PATH) == 1
    assert fill.order_id == "1001"


def test_a_duplicate_rejection_resolves_to_the_order_the_venue_already_has():
    """The retried-bar case: the venue refuses the copy, and its fill is the answer.

    Not decided by reading the message — "duplicate" and "insufficient balance"
    are both ``-2010``. The venue is asked instead.
    """
    ex, session = make_executor({
        ("POST", ORDER_PATH): [Response({"code": -2010, "msg": "Duplicate order sent."}, 400)],
        ("GET", ORDER_PATH): [filled_order(order_id=777)],
    })
    fill = ex.execute(Order(side=BUY, reference_price=64_000.0, time="bar-1",
                            qty=0.0031))

    assert fill.order_id == "777"
    assert session.count("POST", ORDER_PATH) == 1
    assert ex.rejections() == []          # nothing was actually refused


def test_a_real_rejection_is_still_a_rejection():
    """The duplicate check must not swallow a genuine refusal (Gate C's C3)."""
    ex, _session = make_executor({
        ("POST", ORDER_PATH): [Response(
            {"code": -2010, "msg": "Account has insufficient balance."}, 400)],
        ("GET", ORDER_PATH): [Response({"code": -2013, "msg": "Order does not exist."}, 400)],
    })
    with pytest.raises(BinanceAPIError) as err:
        ex.execute(Order(side=BUY, reference_price=64_000.0, time="bar-1", qty=0.0031))

    assert err.value.code == -2010
    assert ex.rejections()[-1]["code"] == -2010
    assert ex.rejections()[-1]["client_order_id"] == ex.client_order_id(BUY, "bar-1")


def test_the_rejection_survives_a_probe_that_also_fails():
    """Evidence must not evaporate because the second request failed too."""
    ex, _session = make_executor({
        ("POST", ORDER_PATH): [Response({"code": -1013, "msg": "Filter failure"}, 400)],
        ("GET", ORDER_PATH): [requests.ConnectionError("down")],
    })
    with pytest.raises(BinanceAPIError):
        ex.execute(Order(side=BUY, reference_price=64_000.0, time="bar-1", qty=0.0031))

    assert ex.rejections()[-1]["code"] == -1013


# ----------------------------------------------- the book drives the same key --
def test_the_book_hands_the_bar_through_as_the_order_key():
    """The whole chain has to carry it: bot -> book -> order -> venue."""
    ex, session = make_executor({("POST", ORDER_PATH): [filled_order()]})
    book = PaperPortfolio(initial_capital=200.0)
    book.set_executor(ex)
    bar = "2026-09-05 12:00:00+00:00"
    book.reconcile(1, 64_000.0, bar)

    assert session.sent("POST", ORDER_PATH)[0]["newClientOrderId"] == \
        ex.client_order_id(BUY, bar)


def test_replaying_the_same_bar_books_the_venue_fill_exactly_once():
    """CRITICAL-2 end to end: the retry of a bar that already traded.

    The first run fills and is lost before its state is saved. The second run
    starts from the *pre-trade* book, decides the same thing, and must end up
    with one position and one venue order — not two.
    """
    bar = "2026-09-05 12:00:00+00:00"
    before = PaperPortfolio(initial_capital=200.0).to_dict()

    first_ex, first_session = make_executor({("POST", ORDER_PATH): [filled_order(order_id=555)]})
    first_book = PaperPortfolio.from_dict(before)
    first_book.set_executor(first_ex)
    first_book.reconcile(1, 64_000.0, bar)

    # Same bar again, from the state the crash left behind. The venue refuses
    # the duplicate and reports the order it already holds.
    retry_ex, retry_session = make_executor({
        ("POST", ORDER_PATH): [Response({"code": -2010, "msg": "Duplicate order sent."}, 400)],
        ("GET", ORDER_PATH): [filled_order(order_id=555)],
    })
    retry_book = PaperPortfolio.from_dict(before)
    retry_book.set_executor(retry_ex)
    retry_book.reconcile(1, 64_000.0, bar)

    assert first_session.count("POST", ORDER_PATH) == 1
    assert retry_session.count("POST", ORDER_PATH) == 1
    assert retry_book.qty == pytest.approx(first_book.qty)
    assert retry_book.cash == pytest.approx(first_book.cash)
    assert retry_ex.reconciliations()[-1].order_id == "555"


# ------------------------------------------- CRITICAL-2: the book vs the venue --
class VenueStub:
    base_url = "https://demo-api.binance.com"
    client_prefix = "tpv4h"
    symbol = "BTCUSDT"

    class Rules:
        base_asset = "BTC"
        quote_asset = "USDT"
        step_size = Decimal("0.00001")
        min_notional = Decimal("5")

    def __init__(self, orders=(), free_base=0.05, free_quote=5000.0):
        self._orders = list(orders)
        self.free_base = free_base
        self.free_quote = free_quote
        self.position = None
        self.recs = []
        self.rejs = []
        self.scans = []

    # -- the parts attach_venue uses --
    def set_position(self, qty):
        self.position = Decimal(str(abs(float(qty))))

    def rules(self):
        return self.Rules()

    def balances(self):
        return {"BTC": Decimal(str(self.free_base)),
                "USDT": Decimal(str(self.free_quote))}

    def free_balance(self, asset):
        return self.balances().get(asset, Decimal("0"))

    def orders_since(self, order_id=None, limit=None):
        self.scans.append((order_id, limit))
        if order_id is None:
            return self._orders[-(limit or len(self._orders)):]
        return [o for o in self._orders if int(o["orderId"]) >= int(order_id)]

    def is_ours(self, client_order_id):
        return bool(client_order_id) and client_order_id.startswith("tpv4h-")

    def client_order_id(self, side, key):
        return f"tpv4h-{side}-{key}"

    # -- the parts the handler uses --
    def sync_time(self):
        return 0

    def mark_price(self):
        return 64_000.0

    def reconciliations(self):
        return list(self.recs)

    def rejections(self):
        return list(self.rejs)


class BotStub:
    def __init__(self, portfolio, last_bar="bar-1", extra=None):
        self.portfolio = portfolio
        self.last_bar = last_bar
        self.extra = dict(extra or {})
        self.store = StoreStub()
        self.target_overlay = None
        self.saves = []
        self.events = []

    def _save(self):
        self.saves.append(dict(self.extra))
        self.events.append("save")


class StoreStub:
    def __init__(self):
        self.fills = []
        self.rejections = []

    def append_fill(self, record):
        self.fills.append(record)

    def append_rejection(self, record):
        self.rejections.append(record)


def a_reconciliation(order_id="999", client_order_id="tpv4h-1-bar-2"):
    """One fill whose price error is 0.50 on 2.0 units — a drag of 1.00."""
    return Reconciliation(
        time="bar-2", side=1, reference_price=100.0, assumed_price=100.02,
        actual_price=100.52, slippage_assumed=0.0002, slippage_actual=0.0052,
        qty=2.0, fee_paid=0.0, fee_asset="BNB", order_id=order_id,
        fill_count=1, status="FILLED", client_order_id=client_order_id,
    )


def test_an_executed_order_the_book_never_recorded_stops_the_run():
    """The half the idempotency key cannot fix: a fill that outlived its run."""
    book = PaperPortfolio(initial_capital=200.0)
    bot = BotStub(book, last_bar="bar-1", extra={"venue": {"last_order_id": 100}})
    venue = VenueStub(orders=[
        {"orderId": 101, "clientOrderId": "tpv4h-1-bar-2", "executedQty": "0.0031"},
    ])
    with pytest.raises(BookOutOfSync, match="never recorded"):
        attach_venue(bot, venue)


def test_the_order_of_the_last_processed_bar_is_not_an_orphan():
    """``bot.step`` saves the book and the bar in one write, after the fill — so
    the newest order matching the saved bar is by construction already booked."""
    book = PaperPortfolio(initial_capital=200.0)
    bot = BotStub(book, last_bar="bar-2", extra={"venue": {"last_order_id": 100}})
    venue = VenueStub(orders=[
        {"orderId": 101, "clientOrderId": "tpv4h-1-bar-2", "executedQty": "0.0031"},
    ])
    record = attach_venue(bot, venue)          # must not raise
    assert record["last_order_id"] == 101      # and it carries the watermark on


def test_a_halt_flatten_is_recognised_too():
    book = PaperPortfolio(initial_capital=200.0)
    bot = BotStub(book, last_bar="bar-2", extra={"venue": {"last_order_id": 100}})
    venue = VenueStub(orders=[
        {"orderId": 101, "clientOrderId": "tpv4h--1-halt@bar-2", "executedQty": "0.0031"},
    ])
    attach_venue(bot, venue)                   # must not raise


def test_another_bots_order_on_the_same_account_is_not_our_orphan():
    book = PaperPortfolio(initial_capital=200.0)
    bot = BotStub(book, last_bar="bar-1", extra={"venue": {"last_order_id": 100}})
    venue = VenueStub(orders=[
        {"orderId": 101, "clientOrderId": "tpsh-heartbeat", "executedQty": "0.0031"},
    ])
    attach_venue(bot, venue)                   # the heartbeat's, not ours


def test_an_unfilled_order_is_not_an_orphan():
    book = PaperPortfolio(initial_capital=200.0)
    bot = BotStub(book, last_bar="bar-1", extra={"venue": {"last_order_id": 100}})
    venue = VenueStub(orders=[
        {"orderId": 101, "clientOrderId": "tpv4h-1-bar-2", "executedQty": "0"},
    ])
    attach_venue(bot, venue)


def test_a_clean_scan_carries_the_watermark_past_everyone_elses_orders():
    """The venue channel fills about twice a year; the heartbeat trades daily.

    A watermark that only moved on OUR fills would leave the scan reaching back
    over thousands of someone else's orders, and eventually past the page the
    venue returns — a check that reports "clean" because it can no longer see.
    """
    book = PaperPortfolio(initial_capital=200.0)
    bot = BotStub(book, last_bar="bar-1", extra={"venue": {"last_order_id": 100}})
    venue = VenueStub(orders=[
        {"orderId": 140, "clientOrderId": "tpsh-heartbeat", "executedQty": "0.0031"},
        {"orderId": 141, "clientOrderId": "tpsh-heartbeat", "executedQty": "0.0031"},
    ])
    attach_venue(bot, venue)

    assert bot.extra["venue"]["last_order_id"] == 141


def test_scanning_forward_is_not_capped_to_a_page():
    """Binance answers ``orderId`` with the OLDEST matching orders, so a limit
    would return a window that ends before the newest order — exactly the one an
    orphan would be."""
    book = PaperPortfolio(initial_capital=200.0)
    bot = BotStub(book, last_bar="bar-1", extra={"venue": {"last_order_id": 100}})
    venue = VenueStub(orders=[])
    attach_venue(bot, venue)

    assert venue.scans == [(100, None)]


def test_seeding_still_refuses_an_orphan_of_our_own():
    """The narrow window the seed path used to swallow: the very first run
    places an order and dies before it can save a watermark, so the run after it
    seeds ABOVE its own orphan and adopts a position the book never booked.

    Nothing on the account carried our prefix before this code existed, so an
    order of ours in the seed page can only be exactly that.
    """
    book = PaperPortfolio(initial_capital=200.0)
    bot = BotStub(book, last_bar="bar-1", extra={})
    venue = VenueStub(orders=[
        {"orderId": 90, "clientOrderId": "x-OLD", "executedQty": "0.0031"},
        {"orderId": 96, "clientOrderId": "tpv4h-1-bar-2", "executedQty": "0.0031"},
    ])
    with pytest.raises(BookOutOfSync, match="never recorded"):
        attach_venue(bot, venue)


def test_the_first_run_seeds_the_watermark_instead_of_alarming():
    """Everything already on the account is history; the check starts from now."""
    book = PaperPortfolio(initial_capital=200.0)
    bot = BotStub(book, extra={})
    venue = VenueStub(orders=[
        {"orderId": 90, "clientOrderId": "x-OLD", "executedQty": "0.0031"},
        {"orderId": 95, "clientOrderId": "x-OLDER", "executedQty": "0.0031"},
    ])
    record = attach_venue(bot, venue)

    assert record["watermark_seeded"] is True
    assert bot.extra["venue"]["last_order_id"] == 95


# ------------------------------------------------- HIGH-1: the T2 drag, alive --
def test_the_handler_folds_this_runs_fill_into_the_kill_switch(monkeypatch):
    """Drag was computed BEFORE the step that produced the fill, so it could
    never accumulate: production read 0.0 after three real fills.

    With the pre-step ordering this test sees 0.0 and fails.
    """
    venue = VenueStub()
    book = PaperPortfolio(initial_capital=200.0)
    bot = BotStub(book, last_bar="bar-1", extra={"venue": {"last_order_id": 100}})

    def step():
        # What a real step does to the executor: it fills.
        venue.recs.append(a_reconciliation(order_id="999"))
        bot.last_bar = "bar-2"
        return {"status": "traded", "bar": "bar-2"}

    bot.step = step
    _run_handler(monkeypatch, bot, venue)

    assert bot.extra["killswitch"]["execution_drag"] == pytest.approx(1.0)
    # ... and the watermark moved with it, or the next run would call it an orphan.
    assert bot.extra["venue"]["last_order_id"] == 999


def test_a_quiet_bar_leaves_the_accumulated_drag_alone(monkeypatch):
    venue = VenueStub()
    book = PaperPortfolio(initial_capital=200.0)
    bot = BotStub(book, last_bar="bar-1",
                  extra={"venue": {"last_order_id": 100},
                         "killswitch": {"execution_drag": 3.0, "start_equity": 200.0,
                                        "peak_equity": 200.0}})
    bot.step = lambda: {"status": "held", "bar": "bar-2"}
    _run_handler(monkeypatch, bot, venue)

    assert bot.extra["killswitch"]["execution_drag"] == pytest.approx(3.0)


def test_a_halt_is_persisted_before_the_flattening_order_goes_out(monkeypatch):
    """MEDIUM-4: a flatten that dies in flight must not leave the halt unsaved."""
    venue = VenueStub()
    book = PaperPortfolio(initial_capital=200.0)
    book.reconcile(1, 64_000.0, "bar-1")          # long, so the halt flattens
    bot = BotStub(book, last_bar="bar-1", extra={
        "venue": {"last_order_id": 100},
        # A peak far above the mark trips T1 on this bar.
        "killswitch": {"start_equity": 1000.0, "peak_equity": 1000.0},
    })
    bot.step = lambda: pytest.fail("a halted channel must not step")

    order_keys = []

    def watching_reconcile(target, price, time, order_key=None):
        order_keys.append(order_key)
        bot.events.append("order")
        return {"time": time, "price": price, "from": 1, "to": 0}

    book.reconcile = watching_reconcile
    result = _run_handler(monkeypatch, bot, venue)

    assert result["status"] == "HALTED"
    # The halt reached storage before the order was sent, not after it.
    assert bot.events.index("save") < bot.events.index("order")
    assert bot.saves[0]["killswitch"]["halted"] is True
    # And the flatten is named after the halt, so a retried halt cannot sell twice.
    assert order_keys == ["halt@bar-1"]


def _run_handler(monkeypatch, bot, venue):
    """Drive ``venue_handler.handler`` against stubs, as the Lambda would."""
    monkeypatch.setenv("TRADING_SYMBOL", "BTCUSDT")
    monkeypatch.setenv("TRADING_TIMEFRAME", "4h")
    monkeypatch.setenv("VENUE_MAX_NOTIONAL", "200")
    monkeypatch.setenv("PAPER_CAPITAL", "200")
    monkeypatch.setattr(venue_handler, "load_credentials_from_ssm",
                        lambda prefix: {"BINANCE_API_KEY": "k",
                                        "BINANCE_API_SECRET": "s"})
    monkeypatch.setattr(venue_handler, "BinanceDemoExecutor",
                        lambda **kwargs: venue)
    monkeypatch.setattr(venue_handler, "build_bot", lambda **kwargs: bot)
    return venue_handler.handler({}, None)


def test_the_venue_channel_reads_its_own_credentials_path(monkeypatch):
    """HIGH-3: shadow and venue sharing one secret means one leak is two bots."""
    seen = {}
    venue = VenueStub()
    book = PaperPortfolio(initial_capital=200.0)
    bot = BotStub(book, last_bar="bar-1", extra={"venue": {"last_order_id": 100}})
    bot.step = lambda: {"status": "held", "bar": "bar-1"}

    monkeypatch.setenv("VENUE_CREDENTIALS_PATH", "/tradepulse/venue")
    monkeypatch.setenv("SHADOW_CREDENTIALS_PATH", "/tradepulse/shadow")
    monkeypatch.setattr(venue_handler, "load_credentials_from_ssm",
                        lambda prefix: seen.setdefault("prefix", prefix) and None
                        or {"BINANCE_API_KEY": "k", "BINANCE_API_SECRET": "s"})
    monkeypatch.setattr(venue_handler, "BinanceDemoExecutor", lambda **kwargs: venue)
    monkeypatch.setattr(venue_handler, "build_bot", lambda **kwargs: bot)
    venue_handler.handler({}, None)

    assert seen["prefix"] == "/tradepulse/venue"


# ---------------------------------------------- the heartbeat's own retry path --
def test_the_heartbeat_names_its_legs_so_a_retry_cannot_double_trade():
    """A scheduled retry must reuse the day's keys; the recovery leg is its own."""
    now = datetime(2026, 9, 5, 0, 25, tzinfo=timezone.utc)
    first = ShadowRunner._order_keys("2026-09-05", now, force=False)
    again = ShadowRunner._order_keys("2026-09-05", datetime(2026, 9, 5, 0, 31,
                                                            tzinfo=timezone.utc),
                                     force=False)

    assert first == again                       # a retry asks about the same order
    assert first["recover"] != first["trip"]    # different orders, same day, same side


def test_a_forced_heartbeat_gets_fresh_keys_so_it_really_trades():
    """``force`` exists to verify a deploy; resolving to the morning's fills
    would report a success that never happened."""
    now = datetime(2026, 9, 5, 14, 3, 9, tzinfo=timezone.utc)
    scheduled = ShadowRunner._order_keys("2026-09-05", now, force=False)
    forced = ShadowRunner._order_keys("2026-09-05", now, force=True)

    assert forced["trip"] != scheduled["trip"]


# ------------------------------------------ MEDIUM-3: one writer at a time --
class FakeTable:
    """Enough DynamoDB to exercise a conditional put."""

    def __init__(self):
        self.item = None

    def get_item(self, Key=None, ConsistentRead=False):
        return {"Item": self.item} if self.item else {}

    def put_item(self, Item=None, ConditionExpression=None,
                 ExpressionAttributeValues=None):
        from botocore.exceptions import ClientError

        current = (self.item or {}).get("state_version")
        if ConditionExpression == "attribute_not_exists(state_version)":
            ok = current is None
        else:
            ok = current == (ExpressionAttributeValues or {}).get(":expected")
        if not ok:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}},
                              "PutItem")
        self.item = Item


def a_store(table):
    store = object.__new__(DynamoDBStateStore)
    store.table = table
    store.pk = "BTCUSDT_4h"
    store._state_version = None
    return store


def test_a_second_writer_cannot_overwrite_what_it_never_read():
    """Two runs, both holding the book they loaded: the loser must fail loudly."""
    table = FakeTable()
    first, second = a_store(table), a_store(table)
    first.load()
    second.load()

    first.save({"last_bar": "bar-2"})
    with pytest.raises(ConcurrentStateWrite, match="state_version"):
        second.save({"last_bar": "bar-2-from-the-other-run"})

    assert table.item["state"]["last_bar"] == "bar-2"


def test_the_same_run_may_save_more_than_once():
    """The halt path saves, trades, then saves again — that must still work."""
    table = FakeTable()
    store = a_store(table)
    store.load()
    store.save({"n": 1})
    store.save({"n": 2})

    assert table.item["state"]["n"] == 2
    assert table.item["state_version"] == 2


def test_an_unversioned_item_is_adopted_exactly_once():
    """The state this channel is running on today has no version yet."""
    table = FakeTable()
    table.item = {"pk": "BTCUSDT_4h", "sk": "state", "state": {"n": 0}}
    store, other = a_store(table), a_store(table)
    store.load()
    other.load()

    store.save({"n": 1})
    with pytest.raises(ConcurrentStateWrite):
        other.save({"n": 99})
