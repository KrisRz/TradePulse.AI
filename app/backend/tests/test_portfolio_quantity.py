"""Tests for the quantity-aware side of the book.

The book now counts two ways — fractionally when the fill is modelled, in
quantities when it comes from a venue. Two paths through the same accounting is
exactly the shape that drifts silently, so the load-bearing test here is
``test_the_two_paths_agree_...``: it feeds the quantity path a fill carrying
precisely what the model would have produced and asserts the books match. If
someone changes one path and not the other, that test fails before anything
reaches an exchange.

The rest pins the things a venue does that a model never had to think about:
commission charged in the asset you just bought, commission charged in a third
asset entirely (BNB — measured on the live demo venue 2026-08-06), and reloading
a book written before any of these fields existed.
"""

from __future__ import annotations

import json
import math

import pytest

from app.backend.paper_trading.execution import BUY, SELL, Fill, Order
from app.backend.paper_trading.portfolio import PaperPortfolio

FEE = 0.001
SLIP = 0.0002
CAPITAL = 10_000.0


class ModelEquivalentExecutor:
    """Emits venue-shaped fills that encode exactly what the model would do.

    Same fill price as ``SimulatedExecutor``, and a quantity/fee pair chosen so
    the quantity-backed arithmetic must land on the modelled numbers. Any
    disagreement is then a real divergence, not a difference of inputs.
    """

    def __init__(self, portfolio: PaperPortfolio):
        self.book = portfolio

    def execute(self, order: Order) -> Fill:
        price = order.reference_price * (1.0 + order.side * SLIP)
        if self.book.side == 0:                      # opening
            equity = self.book.realized
            fee = equity * FEE
            qty = (equity - fee) / price
        else:                                        # closing
            qty = abs(self.book.qty)
            fee = qty * price * FEE
        return Fill(price=price, side=order.side, time=order.time,
                    qty=qty, fee_paid=fee, fee_asset="USDT", base_asset="BTC")


class ScriptedExecutor:
    """Returns fills from a list, for pinning specific venue behaviours."""

    def __init__(self, fills):
        self.fills = list(fills)
        self.orders = []

    def execute(self, order: Order) -> Fill:
        self.orders.append(order)
        spec = self.fills.pop(0)
        return Fill(price=spec["price"], side=order.side, time=order.time,
                    qty=spec["qty"], fee_paid=spec.get("fee", 0.0),
                    fee_asset=spec.get("asset", "USDT"), base_asset="BTC")


#: Long-only, which is what the live strategy trades and all a spot venue can do.
LONG_STEPS = [(1, 30_000.0), (1, 31_500.0), (0, 29_800.0), (1, 28_000.0),
              (1, 27_000.0), (0, 27_900.0), (1, 30_100.0), (0, 33_000.0)]


# ------------------------------------------------------- the equivalence --
def test_the_two_paths_agree_when_fed_the_same_trade():
    """Quantity-backed accounting must land where the model lands."""
    modelled = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    quantity = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    quantity.set_executor(ModelEquivalentExecutor(quantity))

    worst = 0.0
    for i, (target, price) in enumerate(LONG_STEPS):
        modelled.reconcile(target, price, f"t{i}")
        quantity.reconcile(target, price, f"t{i}")

        a, b = modelled.equity(price), quantity.equity(price)
        worst = max(worst, abs(a - b) / abs(a))
        assert a == pytest.approx(b, rel=1e-9), f"step {i}: {a} vs {b}"

    # Discrete outcomes must match EXACTLY — a reassociated float is tolerable,
    # a different number of trades is not.
    assert len(modelled.trades) == len(quantity.trades)
    for m, q in zip(modelled.trades, quantity.trades):
        assert m["side"] == q["side"]
        assert m["entry_time"] == q["entry_time"]
        assert m["exit_time"] == q["exit_time"]
        assert m["exit_reason"] == q["exit_reason"]
        assert m["net_return"] == pytest.approx(q["net_return"], rel=1e-9)

    # The divergence is float reassociation, nothing more: worst case must sit
    # far below the cent that Gate A tolerates on a $10k book.
    assert worst < 1e-12, f"paths diverged by {worst:.2e} relative — not just rounding"
    assert abs(modelled.realized - quantity.realized) < 0.01


def test_on_a_short_the_two_paths_deliberately_disagree():
    """A real difference in the cost model, pinned here so it cannot surprise us.

    Closing a position, the fractional model charges the exit fee on the
    RESULTING EQUITY (``apply_fee(entry_equity * (1 + gross))``); an exchange
    charges it on the TRADED NOTIONAL. For a long those are the same number —
    closing equity *is* the notional — which is why the equivalence above holds
    to float noise. For a short they are not: equity is
    ``2E − qty·exit`` while the notional is ``qty·exit``.

    Measured: ~$0.07 on a $10k book, in the *fractional* model's favour, i.e.
    the fractional model understates the cost of shorting.

    This bites nothing today — the live strategy is ``allow_short=False`` and a
    spot venue cannot short at all — but ``backtesting.engine`` defaults to
    ``allow_short=True``, so any future short research carries the
    approximation. Whoever validates a short strategy must decide which model
    to trust; the quantity path is the one a venue would actually apply.
    """
    modelled = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    quantity = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    quantity.set_executor(ModelEquivalentExecutor(quantity))

    for book in (modelled, quantity):
        book.reconcile(-1, 28_000.0, "t0")
        book.reconcile(0, 27_900.0, "t1")

    difference = quantity.realized - modelled.realized
    assert difference > 0.0, "the venue model should cost no less than the shortcut"
    assert 0.05 < difference < 0.10, f"unexpected magnitude: {difference}"

    # The entry legs DO agree — only the exit fee basis differs.
    assert modelled.trades[0]["entry_price"] == quantity.trades[0]["entry_price"]


def test_the_reparameterisation_is_exact_for_both_sides():
    """cash + qty*p == E*(1 + side*(p/entry - 1)), long and short alike."""
    for side in (1, -1):
        book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
        book.reconcile(side, 30_000.0, "t0")
        for price in (25_000.0, 30_000.0, 36_000.0):
            fractional = book.entry_equity * (1.0 + side * (price / book.entry_fill - 1.0))
            quantitative = book.cash + book.qty * price
            assert quantitative == pytest.approx(fractional, rel=1e-12)


# ------------------------------------------------------------ modelled path --
def test_the_modelled_path_still_reports_a_quantity():
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    book.reconcile(1, 30_000.0, "t0")
    assert book.qty > 0
    assert book.qty == pytest.approx(book.entry_equity / book.entry_fill)
    assert book.cash == 0.0                      # a long holds no quote
    assert book.quantity_backed is False         # nothing came from a venue


def test_a_short_holds_negative_quantity_and_twice_the_cash():
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    book.reconcile(-1, 30_000.0, "t0")
    assert book.qty < 0
    assert book.cash == pytest.approx(2 * book.entry_equity)


def test_closing_returns_the_book_to_cash():
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    book.reconcile(1, 30_000.0, "t0")
    book.reconcile(0, 31_000.0, "t1")
    assert book.qty == 0.0
    assert book.cash == book.realized


def test_the_modelled_equity_never_reads_back_the_derived_quantity():
    """Corrupting the reported qty must not move modelled equity by a cent."""
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    book.reconcile(1, 30_000.0, "t0")
    before = book.equity(32_000.0)
    book.qty = 999.0                             # nonsense, reporting only
    assert book.equity(32_000.0) == before


# ------------------------------------------------------- quantity-backed path --
def test_a_venue_fill_flips_the_book_into_quantity_mode():
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    book.set_executor(ScriptedExecutor([{"price": 30_000.0, "qty": 0.3, "fee": 9.0}]))
    book.reconcile(1, 30_000.0, "t0")
    assert book.quantity_backed is True
    assert book.qty == pytest.approx(0.3)
    assert book.cash == pytest.approx(CAPITAL - 0.3 * 30_000.0 - 9.0)


def test_equity_in_quantity_mode_is_cash_plus_marked_position():
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    book.set_executor(ScriptedExecutor([{"price": 30_000.0, "qty": 0.3, "fee": 9.0}]))
    book.reconcile(1, 30_000.0, "t0")
    assert book.equity(31_000.0) == pytest.approx(book.cash + 0.3 * 31_000.0)


def test_a_venue_round_trip_books_the_actual_profit():
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    book.set_executor(ScriptedExecutor([
        {"price": 30_000.0, "qty": 0.3, "fee": 9.0},
        {"price": 31_000.0, "qty": 0.3, "fee": 9.3},
    ]))
    book.reconcile(1, 30_000.0, "t0")
    book.reconcile(0, 31_000.0, "t1")
    # 0.3 BTC * 1000 gain = 300, less 18.30 of commission
    assert book.realized == pytest.approx(CAPITAL + 300.0 - 18.3)
    assert book.qty == 0.0


def test_a_partial_fill_leaves_the_book_holding_what_it_actually_got():
    """Ask for 0.3, get 0.21 — the book must carry 0.21, not the intent."""
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    book.set_executor(ScriptedExecutor([{"price": 30_000.0, "qty": 0.21, "fee": 6.3}]))
    book.reconcile(1, 30_000.0, "t0")
    assert book.qty == pytest.approx(0.21)
    assert book.equity(30_000.0) == pytest.approx(CAPITAL - 6.3)


# ---------------------------------------------------------------------- fees --
def test_commission_in_the_bought_asset_reduces_the_position():
    """Buy 0.3 BTC, pay 0.1% in BTC, own 0.2997 — sell that, not 0.3."""
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    book.set_executor(ScriptedExecutor([
        {"price": 30_000.0, "qty": 0.3, "fee": 0.0003, "asset": "BTC"},
    ]))
    book.reconcile(1, 30_000.0, "t0")
    assert book.qty == pytest.approx(0.2997)
    assert book.fees_quote == 0.0


def test_commission_in_a_third_asset_is_recorded_but_not_booked():
    """Binance bills BNB when the account holds it — measured live 2026-08-06.

    It is a real cost, but converting it needs a BNB price this book does not
    have. Guessing would be worse than showing it separately.
    """
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    book.set_executor(ScriptedExecutor([
        {"price": 30_000.0, "qty": 0.3, "fee": 0.012, "asset": "BNB"},
    ]))
    book.reconcile(1, 30_000.0, "t0")

    assert book.fees_external == {"BNB": pytest.approx(0.012)}
    assert book.fees_quote == 0.0
    assert book.qty == pytest.approx(0.3)                    # position untouched
    assert book.equity(30_000.0) == pytest.approx(CAPITAL)   # cost not in equity


def test_external_fees_accumulate_per_asset():
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    book.set_executor(ScriptedExecutor([
        {"price": 30_000.0, "qty": 0.3, "fee": 0.012, "asset": "BNB"},
        {"price": 31_000.0, "qty": 0.3, "fee": 0.013, "asset": "BNB"},
    ]))
    book.reconcile(1, 30_000.0, "t0")
    book.reconcile(0, 31_000.0, "t1")
    assert book.fees_external["BNB"] == pytest.approx(0.025)


def test_quote_commission_accumulates_where_it_can_be_booked():
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    book.set_executor(ScriptedExecutor([
        {"price": 30_000.0, "qty": 0.3, "fee": 9.0},
        {"price": 31_000.0, "qty": 0.3, "fee": 9.3},
    ]))
    book.reconcile(1, 30_000.0, "t0")
    book.reconcile(0, 31_000.0, "t1")
    assert book.fees_quote == pytest.approx(18.3)


def test_a_fill_without_a_fee_costs_nothing():
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    book.set_executor(ScriptedExecutor([{"price": 30_000.0, "qty": 0.3, "fee": 0.0}]))
    book.reconcile(1, 30_000.0, "t0")
    assert book.equity(30_000.0) == pytest.approx(CAPITAL)
    assert book.fees_quote == 0.0 and book.fees_external == {}


# ------------------------------------------------------------- persistence --
def test_the_book_still_serialises_for_dynamodb():
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    book.set_executor(ScriptedExecutor([
        {"price": 30_000.0, "qty": 0.3, "fee": 0.012, "asset": "BNB"},
    ]))
    book.reconcile(1, 30_000.0, "t0")
    d = book.to_dict()
    assert "_executor" not in d
    json.dumps(d)                                # must stay serialisable
    assert d["qty"] == pytest.approx(0.3)
    assert d["fees_external"] == {"BNB": pytest.approx(0.012)}


def test_a_book_written_before_these_fields_existed_still_loads():
    """Every state the M5 Lambda has persisted looks like this."""
    legacy = {
        "fee_rate": FEE, "slippage": SLIP, "initial_capital": CAPITAL,
        "realized": 9_990.0, "side": 1, "entry_fill": 30_006.0,
        "entry_equity": 9_990.0, "equity_before_entry": 10_000.0,
        "entry_time": "2026-07-20", "last_price": 31_000.0, "trades": [],
    }
    book = PaperPortfolio.from_dict(legacy)

    assert book.side == 1
    assert book.qty == pytest.approx(9_990.0 / 30_006.0)      # rebuilt, not zero
    assert book.cash == 0.0
    assert book.fees_external == {}
    assert book.quantity_backed is False
    # And the legacy equity formula is what it still answers with.
    assert book.equity(31_000.0) == pytest.approx(9_990.0 * (31_000.0 / 30_006.0))


def test_a_legacy_flat_book_loads_as_cash():
    legacy = {"realized": 10_500.0, "side": 0, "entry_fill": 0.0,
              "entry_equity": 0.0, "trades": []}
    book = PaperPortfolio.from_dict(legacy)
    assert book.qty == 0.0
    assert book.cash == pytest.approx(10_500.0)
    assert book.equity() == pytest.approx(10_500.0)


def test_a_round_trip_through_dict_preserves_the_quantity_book():
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    book.set_executor(ScriptedExecutor([{"price": 30_000.0, "qty": 0.3, "fee": 9.0}]))
    book.reconcile(1, 30_000.0, "t0")

    restored = PaperPortfolio.from_dict(json.loads(json.dumps(book.to_dict())))
    assert restored.qty == pytest.approx(book.qty)
    assert restored.cash == pytest.approx(book.cash)
    assert restored.quantity_backed is True
    assert restored.equity(31_500.0) == pytest.approx(book.equity(31_500.0))


def test_position_value_marks_only_the_holding():
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    book.reconcile(1, 30_000.0, "t0")
    assert book.position_value(31_000.0) == pytest.approx(book.qty * 31_000.0)
    assert not math.isclose(book.position_value(31_000.0), book.equity(31_000.0)) \
        or book.cash == 0.0
