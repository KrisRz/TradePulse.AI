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
    EARLIEST_EVAL, GateInputs, deflated_sharpe, evaluate, expected_max_sharpe,
    min_track_record_length, norm_cdf, norm_ppf, probabilistic_sharpe)


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


def test_active_profitable_window_passes():
    equity = list(np.linspace(10_000, 11_000, 60))
    trades = [_mk_trade(0.05, "2026-07-20", "2026-08-05"),
              _mk_trade(0.04, "2026-08-10", "2026-08-30")]
    rep = evaluate(_mk_inputs(equity, trades), as_of=EARLIEST_EVAL)
    assert rep["verdict"] == "PASS"
    assert rep["gates"]["net_pnl>0"] and rep["gates"]["profit_factor>=1.3"]
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
    assert rep_open["verdict"] in ("PASS", "FAIL")


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
    assert stats["min_trl_days_vs_zero"] > 0
