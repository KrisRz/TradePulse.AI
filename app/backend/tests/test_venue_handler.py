"""Tests for the venue-backed paper channel.

The one that matters is ``test_the_executor_position_is_restored_from_the_book``.
The executor tracks its position in memory; a Lambda lives for seconds and this
bot may hold for weeks. Get that wrong and the exit leg fails with "nothing to
sell", stranding real coins on the venue with no code able to close them — and it
would only show up the first time the strategy tried to exit, possibly months in.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.backend.paper_trading.binance_demo import BinanceDemoExecutor
from app.backend.paper_trading.portfolio import PaperPortfolio
from app.backend.paper_trading.venue_handler import attach_venue


class FakeRules:
    base_asset = "BTC"
    quote_asset = "USDT"
    step_size = Decimal("0.00001")


class FakeExecutor:
    base_url = "https://demo-api.binance.com"

    def __init__(self, free_base=0.05):
        self.free_base = free_base
        self.position = None

    def set_position(self, qty):
        self.position = Decimal(str(abs(float(qty))))

    def rules(self):
        return FakeRules()

    def free_balance(self, asset):
        return Decimal(str(self.free_base))


class Bot:
    def __init__(self, portfolio):
        self.portfolio = portfolio


# ------------------------------------------------------ position restoration --
def test_the_executor_position_is_restored_from_the_book():
    """A bot resumed from DynamoDB must be able to sell what it is holding."""
    book = PaperPortfolio(initial_capital=200.0)
    book.reconcile(1, 64_000.0, "t0")           # opens a long, book records qty
    restored = PaperPortfolio.from_dict(book.to_dict())

    ex = FakeExecutor()
    attach_venue(Bot(restored), ex)

    assert ex.position == pytest.approx(Decimal(str(restored.qty)))
    assert ex.position > 0


def test_a_flat_book_restores_a_flat_executor():
    ex = FakeExecutor()
    attach_venue(Bot(PaperPortfolio(initial_capital=200.0)), ex)
    assert ex.position == Decimal("0")


def test_a_short_book_restores_the_magnitude_not_the_sign():
    """An exchange position is a quantity; the direction lives in the book."""
    book = PaperPortfolio(initial_capital=200.0)
    book.reconcile(-1, 64_000.0, "t0")
    assert book.qty < 0

    ex = FakeExecutor()
    attach_venue(Bot(book), ex)
    assert ex.position == Decimal(str(abs(book.qty)))


def test_set_position_rejects_nothing_and_normalises_sign():
    ex = BinanceDemoExecutor("k", "s")
    ex.set_position(-0.25)
    assert ex.position_qty == Decimal("0.25")
    ex.set_position(0)
    assert ex.position_qty == Decimal("0")


# ------------------------------------------------------------ reconciliation --
def test_the_executor_is_wired_to_the_book():
    book = PaperPortfolio(initial_capital=200.0)
    ex = FakeExecutor()
    attach_venue(Bot(book), ex)
    assert book._executor is ex


def test_every_run_records_the_venue_balance_beside_the_book():
    book = PaperPortfolio(initial_capital=200.0)
    book.reconcile(1, 64_000.0, "t0")
    record = attach_venue(Bot(book), FakeExecutor(free_base=0.05))

    assert record["book_qty"] == pytest.approx(book.qty)
    assert record["venue_free_base"] == pytest.approx(0.05)
    assert record["base_asset"] == "BTC"
    assert "warning" not in record          # pre-funded coins are not a mismatch


def test_a_book_holding_more_than_the_account_has_is_flagged_loudly():
    """The one impossible state: the exit leg could not fill even in principle."""
    book = PaperPortfolio(initial_capital=200.0)
    book.reconcile(1, 64_000.0, "t0")       # ~0.0031 BTC on 200 capital
    record = attach_venue(Bot(book), FakeExecutor(free_base=0.0000001))

    assert "warning" in record
    assert "cannot fill" in record["warning"]


def test_pre_funded_coins_are_not_mistaken_for_our_position():
    """The demo account holds 0.05 BTC this channel never bought."""
    book = PaperPortfolio(initial_capital=200.0)   # flat
    ex = FakeExecutor(free_base=0.05)
    record = attach_venue(Bot(book), ex)

    assert ex.position == Decimal("0")             # not 0.05
    assert record["venue_free_base"] == pytest.approx(0.05)
    assert "warning" not in record
