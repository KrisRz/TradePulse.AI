"""Partial exposure with a rebalance band (2026-10-30, Kraken pilot).

The book holds ``exposure`` of its equity in the position and pulls it back when
the share leaves ``exposure ± band``. The full-equity book is guarded by the
golden master; these tests guard the new path against an independent reference
written from the definition in docs/KRAKEN_SIZING_DESIGN_2026-10-30.md.
"""

from __future__ import annotations

import math

import pytest

from app.backend.backtesting.sizing import rebalance_amount
from app.backend.paper_trading.execution import SimulatedExecutor
from app.backend.paper_trading.portfolio import PaperPortfolio

FEE, SLIP = 0.008, 0.0002
W, BAND, MIN_ORDER, CAPITAL = 0.5, 0.15, 5.0, 200.0


def _book(**kw) -> PaperPortfolio:
    params = dict(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL,
                  exposure=W, rebalance_band=BAND, min_rebalance=MIN_ORDER)
    params.update(kw)
    return PaperPortfolio(**params)


def _reference(steps, w=W, band=BAND, min_order=MIN_ORDER):
    """The rule written out by hand: decide and trade at the bar's close."""
    cash, qty, side, equity_curve, rebalances = CAPITAL, 0.0, 0, [], 0
    for target, price in steps:
        if target != side and side == 1:
            cash += qty * price * (1 - SLIP) * (1 - FEE)
            qty, side = 0.0, 0
        if target != side and target == 1:
            invest = cash * w
            cash -= invest
            qty = invest * (1 - FEE) / (price * (1 + SLIP))
            side = 1
        if side == 1:
            total = cash + qty * price
            if abs(qty * price / total - w) > band:
                d = w * total - qty * price
                if abs(d) >= min_order:
                    qty += d / price
                    cash -= d + abs(d) * FEE
                    rebalances += 1
        equity_curve.append(cash + qty * price)
    return equity_curve, rebalances


def _wave():
    """A rally (share drifts up), a crash (share drifts down), flat spells between."""
    prices = [100.0 * (1.03 ** i) for i in range(40)]
    prices += [prices[-1] * (0.96 ** i) for i in range(1, 50)]
    prices += [prices[-1] * (1.01 ** i) for i in range(1, 30)]
    targets = [0] * 3 + [1] * 70 + [0] * 10 + [1] * (len(prices) - 83)
    return list(zip(targets, prices))


def _replay(book, steps):
    curve = []
    for i, (target, price) in enumerate(steps):
        book.reconcile(target, price, f"t{i}")
        curve.append(book.equity(price))
    return curve


def test_book_matches_the_hand_written_rule_bar_by_bar():
    steps = _wave()
    expected, n_expected = _reference(steps)
    book = _book()
    got = _replay(book, steps)
    assert n_expected >= 2, "scenario must actually exercise the band"
    assert len(book.rebalances) == n_expected
    for e, g in zip(expected, got):
        assert math.isclose(g, e, rel_tol=1e-12), (g, e)


def test_rally_pulls_the_share_back_to_the_weight_and_pays_the_fee():
    book = _book()
    book.reconcile(1, 100.0, "t0")
    action = book.reconcile(1, 300.0, "t1")         # share ~0.75 > 0.65
    assert action["from"] == action["to"] == 1
    rb = action["rebalance"]
    assert rb["amount"] < 0, "a rally is rebalanced by selling"
    assert rb["fee"] == pytest.approx(abs(rb["amount"]) * FEE)
    share = book.qty * 300.0 / book.equity(300.0)
    assert share == pytest.approx(W / (1 - FEE * abs(rb["amount"]) / book.equity(300.0)), rel=1e-3)
    assert abs(share - W) < 0.01


def test_inside_the_band_nothing_trades():
    book = _book()
    book.reconcile(1, 100.0, "t0")
    assert book.reconcile(1, 150.0, "t1") is None   # share ~0.6 < 0.65
    assert book.rebalances == []


def test_below_the_minimum_order_nothing_trades():
    book = _book(initial_capital=10.0, cash=10.0, realized=10.0)
    book.reconcile(1, 100.0, "t0")
    assert book.reconcile(1, 300.0, "t1") is None   # due ~£2.5 < £5 minimum
    assert book.rebalances == []


def test_entry_puts_only_the_weight_at_risk():
    book = _book(rebalance_band=None)
    book.reconcile(1, 100.0, "t0")
    assert book.cash == pytest.approx(CAPITAL * (1 - W))
    assert book.qty * 100.0 * (1 + SLIP) == pytest.approx(CAPITAL * W * (1 - FEE))
    book.reconcile(1, 0.01, "t1")                   # BTC to (almost) zero
    assert book.equity(0.01) >= CAPITAL * (1 - W), "without a band the cash half is untouched"


def test_a_crash_is_rebalanced_by_buying_from_the_cash_half():
    """The band is symmetric: after a fall it tops the position up from cash.

    So the cash half is NOT untouchable once a band is set; in a long slide the
    book keeps buying, and only the account kill-switch (25% from the peak)
    stops it. That is what the sizing study measured, and it is the rule.
    """
    book = _book()
    book.reconcile(1, 100.0, "t0")
    action = book.reconcile(1, 40.0, "t1")          # share ~0.29 < 0.35
    assert action["rebalance"]["amount"] > 0
    assert book.cash < CAPITAL * (1 - W)


def test_close_books_the_trade_with_both_fees():
    book = _book(rebalance_band=None)
    book.reconcile(1, 100.0, "t0")
    book.reconcile(0, 110.0, "t1")
    invest = CAPITAL * W
    proceeds = invest * (1 - FEE) / (100 * (1 + SLIP)) * 110 * (1 - SLIP) * (1 - FEE)
    assert book.side == 0 and book.qty == 0.0
    assert book.realized == pytest.approx(CAPITAL * (1 - W) + proceeds, rel=1e-12)
    assert book.trades[-1]["net_return"] == pytest.approx(book.realized / CAPITAL - 1)


def test_full_exposure_ignores_the_band():
    book = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL,
                          rebalance_band=BAND, min_rebalance=MIN_ORDER)
    for i, (t, p) in enumerate(_wave()):
        action = book.reconcile(t, p, f"t{i}")
        assert action is None or "rebalance" not in action
    assert book.rebalances == []


@pytest.mark.parametrize("bad", [0.0, -0.1, 1.5])
def test_exposure_outside_unit_interval_is_refused(bad):
    with pytest.raises(ValueError):
        PaperPortfolio(exposure=bad)


def test_partial_exposure_is_long_only():
    with pytest.raises(ValueError):
        _book().reconcile(-1, 100.0, "t0")


def test_partial_exposure_on_a_venue_is_refused_until_the_executor_exists():
    book = _book()
    book.set_executor(SimulatedExecutor(slippage=SLIP))
    with pytest.raises(NotImplementedError):
        book.reconcile(1, 100.0, "t0")


def test_state_round_trip_keeps_exposure_band_and_history():
    book = _book()
    _replay(book, _wave()[:60])
    again = PaperPortfolio.from_dict(book.to_dict())
    assert again.exposure == W and again.rebalance_band == BAND
    assert again.min_rebalance == MIN_ORDER
    assert again.rebalances == book.rebalances
    assert again.equity(250.0) == book.equity(250.0)


def test_a_state_saved_before_partial_exposure_loads_as_full_equity():
    old = PaperPortfolio().to_dict()
    for key in ("exposure", "rebalance_band", "min_rebalance", "rebalances"):
        old.pop(key)
    book = PaperPortfolio.from_dict(old)
    assert book.exposure == 1.0 and book.rebalance_band is None


def test_rebalance_amount_rule():
    assert rebalance_amount(100.0, 100.0, 0.5, 0.15, 5.0) is None          # exactly at weight
    assert rebalance_amount(36.0, 64.0, 0.5, 0.15, 5.0) is None            # inside the band
    assert rebalance_amount(30.0, 70.0, 0.5, 0.15, 5.0) == pytest.approx(-20.0)
    assert rebalance_amount(70.0, 30.0, 0.5, 0.15, 5.0) == pytest.approx(20.0)
    assert rebalance_amount(3.0, 7.0, 0.5, 0.15, 5.0) is None              # 2 < min order
    assert rebalance_amount(0.0, 0.0, 0.5, 0.15, 5.0) is None
