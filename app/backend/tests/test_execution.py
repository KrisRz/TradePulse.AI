"""Tests for the execution seam.

The load-bearing test here is ``test_slipped_price_matches_the_shared_cost_model``:
the executor expresses adverse slippage per *order* side, while
``backtesting.costs`` — which the backtest engine also imports — expresses it
per *position* side. If those two ever disagree, live execution and the backtest
diverge silently, which is the one failure this project is built to prevent.
"""

from __future__ import annotations

import pytest

from app.backend.backtesting.costs import entry_fill_price, exit_fill_price
from app.backend.paper_trading.execution import (
    BUY,
    SELL,
    Fill,
    Order,
    SimulatedExecutor,
    closing_order_side,
    opening_order_side,
    slipped_price,
)
from app.backend.paper_trading.portfolio import PaperPortfolio

SLIPPAGES = [0.0, 0.0002, 0.001, 0.05]
PRICES = [1.0, 100.0, 64_106.56, 1e-6, 1e9]


# --------------------------------------------------------------- equivalence --
@pytest.mark.parametrize("price", PRICES)
@pytest.mark.parametrize("slippage", SLIPPAGES)
@pytest.mark.parametrize("position_side", [1, -1])
def test_slipped_price_matches_the_shared_cost_model(price, slippage, position_side):
    """Order-side slippage == position-side slippage, to the last bit."""
    assert slipped_price(price, opening_order_side(position_side), slippage) == \
        entry_fill_price(price, position_side, slippage)
    assert slipped_price(price, closing_order_side(position_side), slippage) == \
        exit_fill_price(price, position_side, slippage)


def test_order_side_mapping_is_the_exchange_view():
    assert opening_order_side(1) == BUY      # open a long by buying
    assert closing_order_side(1) == SELL     # close a long by selling
    assert opening_order_side(-1) == SELL    # open a short by selling
    assert closing_order_side(-1) == BUY     # close a short by buying


@pytest.mark.parametrize("slippage", SLIPPAGES)
def test_slippage_is_always_adverse(slippage):
    ref = 100.0
    assert slipped_price(ref, BUY, slippage) >= ref     # buying never gets cheaper
    assert slipped_price(ref, SELL, slippage) <= ref    # selling never gets richer


# ------------------------------------------------------------------- orders --
@pytest.mark.parametrize("bad_side", [0, 2, -3])
def test_order_rejects_a_side_no_exchange_would_accept(bad_side):
    with pytest.raises(ValueError, match="side"):
        Order(side=bad_side, reference_price=100.0, time="t0")


@pytest.mark.parametrize("bad_price", [0.0, -1.0])
def test_order_rejects_a_non_positive_price(bad_price):
    with pytest.raises(ValueError, match="price"):
        Order(side=BUY, reference_price=bad_price, time="t0")


@pytest.mark.parametrize("bad_qty", [0.0, -0.5])
def test_order_rejects_a_non_positive_quantity(bad_qty):
    with pytest.raises(ValueError, match="quantity"):
        Order(side=BUY, reference_price=100.0, time="t0", qty=bad_qty)


def test_order_allows_unset_quantity():
    """Simulation sizes by fraction of equity and never names a quantity."""
    assert Order(side=BUY, reference_price=100.0, time="t0").qty is None


# ---------------------------------------------------------------- executor --
def test_simulated_executor_rejects_negative_slippage():
    with pytest.raises(ValueError, match="slippage"):
        SimulatedExecutor(slippage=-0.001)


def test_simulated_executor_is_deterministic():
    ex = SimulatedExecutor(slippage=0.0002)
    order = Order(side=BUY, reference_price=100.0, time="t0")
    assert ex.execute(order) == ex.execute(order)


def test_simulated_executor_reports_the_order_it_filled():
    ex = SimulatedExecutor(slippage=0.001)
    fill = ex.execute(Order(side=SELL, reference_price=200.0, time="t7",
                            symbol="BTCUSDT", qty=0.5))
    assert fill.side == SELL
    assert fill.time == "t7"
    assert fill.qty == 0.5
    assert fill.price == 200.0 * (1.0 - 0.001)


def test_simulated_executor_leaves_venue_fields_unset():
    """Simulation must not invent an order id or a fee it never paid."""
    fill = SimulatedExecutor().execute(Order(side=BUY, reference_price=100.0,
                                             time="t0"))
    assert fill.fee_paid is None
    assert fill.fee_asset is None
    assert fill.order_id is None
    assert fill.raw is None


# --------------------------------------------------------- portfolio wiring --
def test_portfolio_defaults_to_simulation_and_tracks_current_slippage():
    """A book restored with different slippage must not execute on the old one."""
    port = PaperPortfolio(fee_rate=0.0, slippage=0.0002)
    port.reconcile(1, 100.0, "t0")
    assert port.entry_fill == 100.0 * (1.0 + 0.0002)

    restored = PaperPortfolio.from_dict({**port.to_dict(), "slippage": 0.01,
                                         "side": 0, "entry_fill": 0.0})
    restored.reconcile(1, 100.0, "t1")
    assert restored.entry_fill == 100.0 * (1.0 + 0.01)


def test_executor_is_not_part_of_the_persisted_book():
    """The state goes to DynamoDB — an executor in there would break the round trip."""
    port = PaperPortfolio()
    port.set_executor(SimulatedExecutor(slippage=0.09))
    state = port.to_dict()
    assert "_executor" not in state and "executor" not in state
    assert PaperPortfolio.from_dict(state).to_dict() == state


def test_injected_executor_overrides_the_slippage_model():
    """The seam works: a venue that fills elsewhere is booked at its price."""

    class FixedPriceExecutor:
        def __init__(self):
            self.seen = []

        def execute(self, order: Order) -> Fill:
            self.seen.append(order)
            return Fill(price=123.45, side=order.side, time=order.time,
                        qty=1.0, fee_paid=0.5, fee_asset="USDT",
                        order_id="abc-1")

    venue = FixedPriceExecutor()
    port = PaperPortfolio(fee_rate=0.0, slippage=0.0002)
    port.set_executor(venue)
    port.reconcile(1, 100.0, "t0")

    assert port.entry_fill == 123.45, "portfolio ignored the venue's fill price"
    assert [o.side for o in venue.seen] == [BUY]
    assert venue.seen[0].reference_price == 100.0


def test_injected_executor_sees_both_legs_of_a_round_trip():
    class RecordingExecutor(SimulatedExecutor):
        def __init__(self):
            super().__init__(slippage=0.0)
            self.sides = []

        def execute(self, order: Order) -> Fill:
            self.sides.append(order.side)
            return super().execute(order)

    venue = RecordingExecutor()
    port = PaperPortfolio(fee_rate=0.0, slippage=0.0)
    port.set_executor(venue)
    port.reconcile(1, 100.0, "t0")    # open long  -> BUY
    port.reconcile(-1, 110.0, "t1")   # flip short -> SELL (close) + SELL (open)
    port.reconcile(0, 90.0, "t2")     # close short -> BUY

    assert venue.sides == [BUY, SELL, SELL, BUY]


def test_clearing_the_executor_restores_simulation():
    port = PaperPortfolio(fee_rate=0.0, slippage=0.0002)
    port.set_executor(SimulatedExecutor(slippage=0.5))
    port.set_executor(None)
    port.reconcile(1, 100.0, "t0")
    assert port.entry_fill == 100.0 * (1.0 + 0.0002)
