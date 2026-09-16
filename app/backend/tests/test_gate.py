"""M5 gate tests — DSR/MinTRL math properties + pre-registered verdict rules.

Synthetic series only (sanctioned exception): the math is checked against
known properties from Bailey & López de Prado, the verdict logic against the
pre-registered precedence (report-only -> activity rule -> hard gates).
"""

from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.backend.paper_trading.gate import (
    EARLIEST_EVAL, WINDOW_START, GateInputs, _inputs_from_records,
    buy_and_hold_equity, deflated_sharpe, evaluate, expected_max_sharpe,
    min_track_record_length, norm_cdf, norm_ppf, probabilistic_sharpe)
from app.backend.paper_trading.portfolio import PaperPortfolio


# --------------------------------------------------------------------------- #
# Normal distribution helpers
# --------------------------------------------------------------------------- #
def test_norm_ppf_inverts_cdf():
    for p in [0.001, 0.025, 0.5, 0.95, 0.999]:
        assert norm_cdf(norm_ppf(p)) == pytest.approx(p, abs=1e-7)


def test_norm_ppf_known_values():
    assert norm_ppf(0.975) == pytest.approx(1.959964, abs=1e-4)
    assert norm_ppf(0.5) == pytest.approx(0.0, abs=1e-9)


# --------------------------------------------------------------------------- #
# PSR / DSR / MinTRL properties
# --------------------------------------------------------------------------- #
def test_psr_is_half_at_zero_skill():
    # Observed SR equal to the benchmark -> 50/50 by construction.
    assert probabilistic_sharpe(0.0, 0.0, 100, 0.0, 3.0) == pytest.approx(0.5)


def test_psr_grows_with_observations():
    a = probabilistic_sharpe(0.1, 0.0, 30, 0.0, 3.0)
    b = probabilistic_sharpe(0.1, 0.0, 300, 0.0, 3.0)
    assert b > a > 0.5


def test_psr_penalizes_fat_tails():
    thin = probabilistic_sharpe(0.1, 0.0, 100, 0.0, 3.0)
    fat = probabilistic_sharpe(0.1, 0.0, 100, -1.0, 10.0)
    assert fat < thin


def test_expected_max_sharpe_grows_with_trials():
    e2 = expected_max_sharpe(2, 0.3)
    e30 = expected_max_sharpe(30, 0.3)
    e300 = expected_max_sharpe(300, 0.3)
    assert 0 < e2 < e30 < e300
    assert expected_max_sharpe(1, 0.3) == 0.0


def test_dsr_below_psr():
    # Deflation for multiple trials can only lower the probability.
    sr, n, skew, kurt = 0.15, 100, -0.5, 5.0
    assert deflated_sharpe(sr, n, skew, kurt) < \
        probabilistic_sharpe(sr, 0.0, n, skew, kurt)


def test_min_trl_shrinks_with_higher_sharpe():
    lo = min_track_record_length(0.05, 0.0, 0.0, 3.0)
    hi = min_track_record_length(0.20, 0.0, 0.0, 3.0)
    assert hi < lo


def test_min_trl_infinite_without_edge():
    assert math.isinf(min_track_record_length(0.0, 0.0, 0.0, 3.0))
    assert math.isinf(min_track_record_length(-0.1, 0.0, 0.0, 3.0))


def test_min_trl_consistent_with_psr():
    # After exactly MinTRL observations, PSR should sit at the confidence level.
    sr, skew, kurt = 0.12, -0.3, 4.0
    n = min_track_record_length(sr, 0.0, skew, kurt, confidence=0.95)
    psr = probabilistic_sharpe(sr, 0.0, int(round(n)), skew, kurt)
    assert psr == pytest.approx(0.95, abs=0.005)


# --------------------------------------------------------------------------- #
# Verdict rules
# --------------------------------------------------------------------------- #
def _mk_inputs(equity_values, trades=None, open_days=0, start="2026-07-15"):
    idx = pd.date_range(start, periods=len(equity_values), freq="1D", tz="UTC")
    return GateInputs(
        equity=pd.Series([float(v) for v in equity_values], index=idx),
        trades=trades or [],
        initial_capital=10_000.0,
        open_position_days=open_days,
    )


def _mk_trade(net, entry="2026-07-20", exit="2026-08-05", gross_extra=0.003):
    # exit/entry fills chosen so gross > net by ~costs.
    entry_price = 100.0
    exit_price = entry_price * (1.0 + net + gross_extra)
    return {"entry_time": entry, "exit_time": exit, "side": 1,
            "entry_price": entry_price, "exit_price": exit_price,
            "net_return": net, "exit_reason": "signal"}


def test_before_earliest_eval_is_report_only():
    inp = _mk_inputs([10_000] * 10)
    rep = evaluate(inp, as_of=date(2026, 8, 1))
    assert rep["verdict"] == "WINDOW_RUNNING"
    assert "gates" not in rep


def test_flat_window_is_inconclusive_not_fail():
    # 8+ weeks, zero trades -> no evidence either way, never a FAIL.
    inp = _mk_inputs([10_000] * 60)
    rep = evaluate(inp, as_of=EARLIEST_EVAL)
    assert rep["verdict"] == "INCONCLUSIVE_EXTEND"
    assert "no return variance" in rep["statistics"]["note"]


def test_the_original_gates_alone_earn_only_a_provisional_pass():
    """Eight weeks of profit is not evidence (pre-registration 2026-09-05)."""
    equity = list(np.linspace(10_000, 11_000, 60))
    trades = [_mk_trade(0.05, "2026-07-20", "2026-08-05"),
              _mk_trade(0.04, "2026-08-10", "2026-08-30")]
    rep = evaluate(_mk_inputs(equity, trades), as_of=EARLIEST_EVAL)
    assert rep["verdict"] == "PROVISIONAL_PASS"
    assert all(rep["gates"].values())
    assert not rep["tightened_gates"]["B7 window_days>=365"]
    assert not rep["tightened_gates"]["B6 sharpe>=buy&hold"]   # no prices supplied
    assert "does NOT authorize M6" in rep["verdict_reason"]
    assert any("tracking_error" in g for g in rep["skipped_gates"])


def test_drawdown_breach_fails():
    equity = [10_000] * 10 + [12_000] + [8_000] * 30 + [12_100] * 19  # -33% DD
    trades = [_mk_trade(0.05, "2026-07-20", "2026-08-05"),
              _mk_trade(0.04, "2026-08-10", "2026-08-30")]
    rep = evaluate(_mk_inputs(equity, trades), as_of=EARLIEST_EVAL)
    assert rep["verdict"] == "FAIL"
    assert not rep["gates"]["max_drawdown<=25%"]
    assert "max_drawdown" in rep["verdict_reason"]


def test_single_trade_is_inconclusive():
    equity = list(np.linspace(10_000, 10_500, 60))
    trades = [_mk_trade(0.05, "2026-07-20", "2026-08-25")]
    rep = evaluate(_mk_inputs(equity, trades), as_of=EARLIEST_EVAL)
    assert rep["verdict"] == "INCONCLUSIVE_EXTEND"


def test_open_position_counts_toward_activity():
    equity = list(np.linspace(10_000, 10_800, 60))
    trades = [_mk_trade(0.04, "2026-07-20", "2026-07-24"),
              _mk_trade(0.03, "2026-07-25", "2026-07-29")]  # 8 closed days
    # closed days alone (8) < 10 -> inconclusive; +5 open days -> evaluable
    rep_closed = evaluate(_mk_inputs(equity, trades, open_days=0),
                          as_of=EARLIEST_EVAL)
    rep_open = evaluate(_mk_inputs(equity, trades, open_days=5),
                        as_of=EARLIEST_EVAL)
    assert rep_closed["verdict"] == "INCONCLUSIVE_EXTEND"
    assert rep_open["verdict"] in ("PASS", "PROVISIONAL_PASS", "FAIL")


def test_tracking_error_gate_when_supplied():
    equity = list(np.linspace(10_000, 11_000, 60))
    trades = [_mk_trade(0.05, "2026-07-20", "2026-08-05"),
              _mk_trade(0.04, "2026-08-10", "2026-08-30")]
    inp = _mk_inputs(equity, trades)
    inp.tracking_error = 0.15
    rep = evaluate(inp, as_of=EARLIEST_EVAL)
    assert rep["verdict"] == "FAIL"
    assert not rep["gates"]["tracking_error<10%"]


def test_statistics_reported_for_active_window():
    rng = np.random.default_rng(7)
    rets = rng.normal(0.002, 0.01, 59)
    equity = 10_000 * np.cumprod(np.concatenate([[1.0], 1 + rets]))
    rep = evaluate(_mk_inputs(equity), as_of=date(2026, 8, 1))
    stats = rep["statistics"]
    assert 0.0 < stats["psr_vs_zero"] < 1.0
    assert stats["dsr"] < stats["psr_vs_zero"]
    assert stats["min_trl_bars_vs_zero"] > 0


# --------------------------------------------------------------------------- #
# Tightening B5-B7 (docs/GATE_B_PREREGISTRATION_2026-09-05.md)
# --------------------------------------------------------------------------- #
A_YEAR_IN = date(2027, 7, 20)       # 369 days after WINDOW_START


def _strong_year(n=420, seed=11, bh_drift=0.0):
    """A strategy with a clear edge over a year, and prices for buy & hold."""
    rng = np.random.default_rng(seed)
    strat = 10_000 * np.cumprod(np.concatenate([[1.0], 1 + rng.normal(0.002, 0.01, n - 1)]))
    px = 100 * np.cumprod(np.concatenate([[1.0], 1 + rng.normal(bh_drift, 0.03, n - 1)]))
    inp = _mk_inputs(strat, [_mk_trade(0.05, "2026-08-01", "2026-10-01"),
                             _mk_trade(0.08, "2026-11-01", "2027-03-01")])
    inp.prices = pd.Series(px, index=inp.equity.index)
    return inp


def test_all_three_tightened_criteria_met_is_a_pass():
    rep = evaluate(_strong_year(), as_of=A_YEAR_IN)
    assert all(rep["tightened_gates"].values()), rep["tightened_gates"]
    assert rep["verdict"] == "PASS"


def test_a_short_window_withholds_the_pass_b7():
    rep = evaluate(_strong_year(), as_of=date(2027, 7, 1))       # 350 days
    assert not rep["tightened_gates"]["B7 window_days>=365"]
    assert rep["verdict"] == "PROVISIONAL_PASS"


def test_losing_to_buy_and_hold_withholds_the_pass_b6():
    inp = _strong_year()
    # the market rose faster and more smoothly than the strategy did
    inp.prices = pd.Series(100 * np.cumprod(np.full(len(inp.equity), 1.004)),
                           index=inp.equity.index)
    inp.prices.iloc[::7] *= 0.999          # a little variance so B&H Sharpe is finite
    rep = evaluate(inp, as_of=A_YEAR_IN)
    assert not rep["tightened_gates"]["B6 sharpe>=buy&hold"]
    assert rep["benchmark"]["excess_return"] < 0
    assert rep["verdict"] == "PROVISIONAL_PASS"


def test_weak_statistics_withhold_the_pass_b5():
    rng = np.random.default_rng(3)
    inp = _strong_year()
    noisy = 10_000 * np.cumprod(np.concatenate(
        [[1.0], 1 + rng.normal(0.0004, 0.03, len(inp.equity) - 1)]))
    inp.equity = pd.Series(np.maximum(noisy, 9_000), index=inp.equity.index)
    inp.equity.iloc[-1] = 10_500           # still net positive, drawdown in bounds
    rep = evaluate(inp, as_of=A_YEAR_IN)
    assert rep["statistics"]["psr_vs_zero"] < 0.95
    assert not rep["tightened_gates"]["B5 psr_vs_zero>=0.95"]
    assert rep["verdict"] in ("PROVISIONAL_PASS", "FAIL")
    assert rep["verdict"] != "PASS"


def test_an_undefined_psr_does_not_meet_b5():
    rep = evaluate(_mk_inputs([10_000] * 400), as_of=A_YEAR_IN)
    assert not rep["tightened_gates"]["B5 psr_vs_zero>=0.95"]


def test_the_dsr_benchmark_is_in_annualized_units():
    """0.3 is a variance of annualized Sharpe ratios; the bar must be ~1.14/yr.

    Applied per bar unconverted it was ~21.7 a year, and DSR printed 0.000 for
    any record a strategy could ever produce (audit 2026-09-04, MEDIUM-4).
    """
    rep = evaluate(_strong_year(), as_of=A_YEAR_IN)
    stats = rep["statistics"]
    # sqrt(0.3) * ((1-g)*z(1-1/30) + g*z(1-1/(30e))) = 0.5477 * (0.4228*1.8339 + 0.5772*2.2482)
    assert stats["expected_max_sr_of_trials_annualized"] == pytest.approx(1.136, abs=0.002)
    assert stats["dsr"] > 0.5
    assert deflated_sharpe(0.2, 400, 0.0, 3.0) > 0.5     # default is per-bar for 1d


def test_sharpe_is_annualized_by_the_channel_timeframe():
    rng = np.random.default_rng(5)
    values = 200 * np.cumprod(np.concatenate([[1.0], 1 + rng.normal(0.0005, 0.005, 299)]))
    daily = _mk_inputs(values)
    four_hourly = GateInputs(
        equity=pd.Series(values, index=pd.date_range("2026-08-06", periods=300,
                                                     freq="4h", tz="UTC")),
        trades=[], initial_capital=200.0, open_position_days=0, timeframe="4h")
    d = evaluate(daily, as_of=date(2026, 8, 1))["performance"]["sharpe_annualized"]
    h = evaluate(four_hourly, as_of=date(2026, 8, 1))["performance"]["sharpe_annualized"]
    assert h / d == pytest.approx(math.sqrt(6.0))


def test_buy_and_hold_pays_costs_on_the_way_in_and_out():
    prices = pd.Series([100.0] * 5, index=pd.date_range("2026-07-15", periods=5, tz="UTC"))
    bh = buy_and_hold_equity(prices, 10_000.0, fee_rate=0.001, slippage=0.0002)
    expected_final = 10_000 * 0.999 * (1 - 0.0002) / (1 + 0.0002) * 0.999
    assert bh.iloc[-1] == pytest.approx(expected_final)
    assert bh.iloc[1] == pytest.approx(10_000 * 0.999 / 1.0002)


def test_an_open_losing_position_cannot_hide_behind_closed_winners():
    """MEDIUM-5: the verdict must not depend on the day the evaluation runs."""
    inp = _strong_year()
    inp.open_trade = {"entry_time": "2027-06-01", "exit_time": "2027-07-20", "side": 1,
                      "entry_price": 100.0, "exit_price": 60.0,
                      "net_return": -0.40, "exit_reason": "open_at_evaluation"}
    rep = evaluate(inp, as_of=A_YEAR_IN)
    assert rep["gates"]["profit_factor>=1.3"]
    assert not rep["gates"]["profit_factor>=1.3 (incl. open)"]
    assert rep["verdict"] == "FAIL"


def test_a_quantity_backed_book_cannot_pass_on_fee_drag():
    """Its commission sits in fees_external, so gross minus net says nothing."""
    inp = _strong_year()
    inp.quantity_backed = True
    rep = evaluate(inp, as_of=A_YEAR_IN)
    assert rep["performance"]["fee_drag"] is None
    assert not rep["gates"]["fee_drag<20%"]
    assert any("fees_external" in n for n in rep["notes"])
    assert rep["verdict"] == "FAIL"


def test_the_log_carries_prices_timeframe_and_the_open_position():
    book = PaperPortfolio(initial_capital=10_000.0)
    decisions = []
    for i, (bar, price, target) in enumerate([
            ("2026-07-15 00:00:00+00:00", 100.0, 0),
            ("2026-07-16 00:00:00+00:00", 101.0, 1),
            ("2026-07-17 00:00:00+00:00", 104.0, 1)]):
        book.reconcile(target, price, bar)
        decisions.append({"bar": bar, "price": price, "target": target,
                          "equity": round(book.equity(price), 2), "timeframe": "1d"})
    state = {"timeframe": "1d", "portfolio": book.to_dict()}

    inp = _inputs_from_records(decisions, state)

    assert list(inp.prices) == [100.0, 101.0, 104.0]
    assert inp.timeframe == "1d" and not inp.quantity_backed
    closed = PaperPortfolio.from_dict(book.to_dict())
    closed.reconcile(0, 104.0, "2026-07-17 00:00:00+00:00")
    assert inp.open_trade["net_return"] == closed.trades[-1]["net_return"]
    assert inp.open_trade["exit_reason"] == "open_at_evaluation"
    assert WINDOW_START == date(2026, 7, 16)
