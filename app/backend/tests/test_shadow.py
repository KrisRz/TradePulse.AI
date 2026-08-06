"""Tests for the daily execution heartbeat.

Two cases here are the reason this file exists, and both are about state that
survives a failure:

* **EventBridge retries three times.** Without the per-day guard, one transient
  timeout after a filled order becomes four round-trips.
* **The buy can fill and the sell can fail.** That strands a position on the
  venue. The next run must flatten it *before* trading again, and must never
  report a run that ended holding as a success.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.backend.paper_trading.binance_demo import BinanceAPIError, OrderTooSmall
from app.backend.paper_trading.execution import BUY, SELL, Fill
from app.backend.paper_trading.shadow import SHADOW_PK, ShadowRunner

NOW = datetime(2026, 8, 7, 0, 20, tzinfo=timezone.utc)


class FakeStore:
    def __init__(self):
        self.state = None
        self.decisions = []
        self.saves = 0

    def load(self):
        return dict(self.state) if self.state else None

    def save(self, state):
        self.state = dict(state)
        self.saves += 1

    def append_decision(self, record):
        self.decisions.append(record)

    def has_decision(self, bar):
        return any(d.get("bar") == bar for d in self.decisions)


class FakeExecutor:
    """Stands in for the venue: records orders, fills them from a script."""

    base_url = "https://demo-api.binance.com"
    assumed_slippage = 0.0002

    def __init__(self, price=64_500.0, fail_on=None, qty=Decimal("0.00015")):
        self.price = price
        self.fail_on = fail_on or {}
        self.qty = qty
        self._position_qty = Decimal("0")
        self.orders = []
        self._recs = []

    def mark_price(self):
        return self.price

    def plan_quantity(self, side, reference_price):
        if side == BUY and "plan" in self.fail_on:
            raise self.fail_on["plan"]
        return self.qty

    def execute(self, order):
        self.orders.append(order)
        if order.side == BUY and "buy" in self.fail_on:
            raise self.fail_on["buy"]
        if order.side == SELL and "sell" in self.fail_on:
            raise self.fail_on["sell"]

        if order.side == BUY:
            self._position_qty += self.qty
        else:
            self._position_qty = max(Decimal("0"), self._position_qty - self.qty)

        order_id = f"order-{len(self.orders)}"
        # Stands in for a Reconciliation: the runner reads these fields off it.
        self._recs.append(SimpleNamespace(
            slippage_actual=0.0001, actual_price=self.price, qty=float(self.qty),
            order_id=order_id, fee_paid=1e-6, fee_asset="BNB",
        ))
        return Fill(price=self.price, side=order.side, time=order.time,
                    qty=float(self.qty), fee_paid=1e-6, fee_asset="BNB",
                    base_asset="BTC", order_id=order_id)

    def reconciliations(self):
        return self._recs

    @property
    def position_qty(self):
        return self._position_qty


def make_runner(**kwargs):
    ex = FakeExecutor(**kwargs)
    store = FakeStore()
    return ShadowRunner(ex, store), ex, store


# --------------------------------------------------------------- happy path --
def test_a_heartbeat_is_a_complete_round_trip_that_ends_flat():
    runner, ex, store = make_runner()
    result = runner.run_once(now=NOW)

    assert result["status"] == "ok"
    assert [o.side for o in ex.orders] == [BUY, SELL]
    assert result["flat"] is True
    assert ex.position_qty == Decimal("0")


def test_the_run_is_recorded_for_the_day_it_ran():
    runner, _ex, store = make_runner()
    runner.run_once(now=NOW)
    assert store.decisions[0]["bar"] == "2026-08-07"
    assert store.decisions[0]["kind"] == "heartbeat"


def test_it_records_both_fills_and_the_measured_slippage():
    runner, _ex, store = make_runner()
    result = runner.run_once(now=NOW)
    assert result["entry"]["order_id"] == "order-1"
    assert result["exit"]["order_id"] == "order-2"
    assert result["slippage"] == [0.0001, 0.0001]
    assert result["slippage_assumed"] == 0.0002
    assert result["fee_asset"] == "BNB"


def test_the_heartbeat_exercises_the_quantity_backed_book():
    """The path M6 depends on must be proven daily on real fills, not only in tests."""
    runner, _ex, store = make_runner()
    result = runner.run_once(now=NOW)

    book = result["book"]
    assert book["quantity_backed"] is True      # venue fills drove the accounting
    assert book["qty_after"] == pytest.approx(0.0)
    assert book["net_return"] is not None
    # The fake bills BNB, so the cost is recorded but deliberately not in equity.
    assert book["fees_external"]["BNB"] == pytest.approx(2e-6)
    assert book["fees_quote"] == 0.0


def test_the_handler_only_forces_when_explicitly_asked():
    """EventBridge sends {} — a scheduled run must never bypass the daily guard."""
    from app.backend.paper_trading import shadow_handler

    seen = []

    class Runner:
        def run_once(self, force=False):
            seen.append(force)
            return {"status": "ok", "flat": True}

    original_build = shadow_handler.build_shadow_runner
    original_creds = shadow_handler.load_credentials_from_ssm
    shadow_handler.build_shadow_runner = lambda **kw: Runner()
    shadow_handler.load_credentials_from_ssm = lambda prefix: {}
    try:
        shadow_handler.handler({}, None)                 # the scheduler's payload
        shadow_handler.handler(None, None)               # a manual empty invoke
        shadow_handler.handler({"force": True}, None)    # deliberate override
    finally:
        shadow_handler.build_shadow_runner = original_build
        shadow_handler.load_credentials_from_ssm = original_creds

    assert seen == [False, False, True]


def test_the_partition_key_keeps_it_out_of_the_paper_bots_book():
    """The M5 book is untouchable; a different key is what guarantees that."""
    key = SHADOW_PK.format(symbol="BTCUSDT", timeframe="1d")
    assert key == "SHADOW_BTCUSDT_1d"
    assert not key.startswith("BTCUSDT")


# ------------------------------------------------------------- idempotency --
def test_a_second_run_on_the_same_day_places_no_orders():
    """EventBridge retries 3×; without this, one timeout becomes four round-trips."""
    runner, ex, _store = make_runner()
    runner.run_once(now=NOW)
    assert len(ex.orders) == 2

    second = runner.run_once(now=NOW)
    assert second["status"] == "already_done"
    assert len(ex.orders) == 2          # nothing new was sent


def test_a_retry_later_the_same_day_is_still_the_same_day():
    runner, ex, _store = make_runner()
    runner.run_once(now=NOW)
    later = NOW.replace(hour=23, minute=59)
    assert runner.run_once(now=later)["status"] == "already_done"
    assert len(ex.orders) == 2


def test_the_next_day_runs_again():
    runner, ex, _store = make_runner()
    runner.run_once(now=NOW)
    tomorrow = NOW.replace(day=8)
    assert runner.run_once(now=tomorrow)["status"] == "ok"
    assert len(ex.orders) == 4


def test_force_overrides_the_daily_guard():
    runner, ex, _store = make_runner()
    runner.run_once(now=NOW)
    assert runner.run_once(now=NOW, force=True)["status"] == "ok"
    assert len(ex.orders) == 4


# ------------------------------------------------------- stranded positions --
def test_a_failed_sell_leaves_the_position_recorded_not_lost():
    """The one way this runner can leave state behind — it must be written down."""
    runner, ex, store = make_runner(fail_on={"sell": BinanceAPIError(-1001, "boom")})
    result = runner.run_once(now=NOW)

    assert result["status"] == "venue_error"
    assert store.state["open_qty"] == pytest.approx(0.00015)


def test_the_next_run_flattens_a_stranded_position_before_trading_again():
    runner, ex, store = make_runner(fail_on={"sell": BinanceAPIError(-1001, "boom")})
    runner.run_once(now=NOW)

    ex.fail_on = {}                       # venue recovers
    result = runner.run_once(now=NOW.replace(day=8))

    assert result["recovery"]["recovered_qty"] == pytest.approx(0.00015)
    # day 1: buy, then the sell that failed (attempted, so recorded);
    # day 2: the recovery sell FIRST, only then the day's own buy and sell.
    assert [o.side for o in ex.orders] == [BUY, SELL, SELL, BUY, SELL]
    assert store.state["open_qty"] == 0.0
    assert result["status"] == "ok"


def test_a_run_that_ends_holding_is_never_reported_as_success():
    class StickyExecutor(FakeExecutor):
        def execute(self, order):
            fill = super().execute(order)
            if order.side == SELL:
                self._position_qty = Decimal("0.00001")   # venue kept part of it
            return fill

    ex = StickyExecutor()
    store = FakeStore()
    result = ShadowRunner(ex, store).run_once(now=NOW)
    assert result["status"] == "not_flat"
    assert result["flat"] is False


# -------------------------------------------------------------- failure modes --
def test_a_venue_error_on_entry_is_recorded_with_its_code():
    runner, _ex, store = make_runner(fail_on={"buy": BinanceAPIError(-2010, "no funds")})
    result = runner.run_once(now=NOW)
    assert result["status"] == "venue_error"
    assert result["code"] == -2010
    assert store.decisions[-1]["status"] == "venue_error"


def test_an_unsizeable_order_is_recorded_rather_than_crashing():
    runner, ex, _store = make_runner(fail_on={"plan": OrderTooSmall("below minNotional")})
    result = runner.run_once(now=NOW)
    assert result["status"] == "too_small"
    assert ex.orders == []


def test_a_failure_still_marks_the_day_so_retries_do_not_pile_on():
    """A failed venue call must not invite three more attempts at a live order."""
    runner, ex, _store = make_runner(fail_on={"buy": BinanceAPIError(-2010, "no funds")})
    runner.run_once(now=NOW)
    assert runner.run_once(now=NOW)["status"] == "already_done"
