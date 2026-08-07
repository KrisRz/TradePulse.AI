"""Gate C (cost fidelity) — every criterion must CATCH its own failure.

The evaluator guards the assumption real money will lean on: that the cost
model the backtest uses (0.02% slippage, 0.1% fee) matches what the venue
actually does. A criterion that only ever passes proves nothing, so each one
here is fed the exact failure it exists to detect, plus the honest-evidence
edges: fills that cannot be verified must surface as SKIPPED/unverifiable,
never as silent passes, and no PASS/FAIL verdict may appear before the
pre-registered 20-fill minimum.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.backend.paper_trading.gate import (
    GATE_C_MIN_FILLS,
    CostFidelityInputs,
    check_book_venue_divergence,
    check_decision_drift,
    check_fill_log_completeness,
    check_median_exec_slippage,
    check_p90_exec_slippage,
    check_partial_fills,
    check_rejection_rate,
    evaluate_cost_fidelity,
    load_cost_records_local,
)
from app.backend.paper_trading.state_store import LocalJsonStateStore

AS_OF = date(2026, 8, 7)


def make_fill(i: int = 0, **over) -> dict:
    """A fully-verifiable, threshold-passing fill record."""
    qty = 0.0031
    fill = {
        "bar": f"2026-08-{6 + i:02d} 00:00:00+00:00",
        "time": f"2026-08-{6 + i:02d} 00:00:00+00:00",
        "side": 1,
        "reference_price": 64_446.0,
        "assumed_price": 64_458.89,
        "actual_price": 64_452.4,
        "slippage_assumed": 0.0002,
        "slippage_actual": 0.0001,
        "qty": qty,
        "requested_qty": qty,
        "fee_paid": 0.0,
        "fee_asset": "USDT",
        "order_id": str(54_508_851_440 + i),
        "fill_count": 1,
        "status": "FILLED",
        "mark_at_order": 64_446.0,
        "drift": 0.0,
        "execution_slippage": 0.0001,
        "price_error": -0.649,
        "symbol": "BTCUSDT",
        "timeframe": "4h",
        "book_qty_after": qty,
        "venue_free_base_before": 0.05,
        "venue_free_base_after": 0.05 + qty,
        "base_asset": "BTC",
        "step_size": 0.00001,
        "venue_delta_attributable": True,
    }
    fill.update(over)
    return fill


def make_inputs(fills=None, rejections=None, decisions=None) -> CostFidelityInputs:
    return CostFidelityInputs(fills=fills or [], rejections=rejections or [],
                              decisions=decisions or [])


# --------------------------------------------------------- C0: completeness --
def test_completeness_catches_a_traded_bar_with_no_fill_record():
    """A lost fill silently shrinks the sample — it must fail, not vanish."""
    decisions = [
        {"bar": "2026-08-06 00:00:00+00:00", "action": {"from": 0, "to": 1}},
        {"bar": "2026-08-07 00:00:00+00:00", "action": None},
    ]
    res = check_fill_log_completeness(make_inputs(decisions=decisions))
    assert res["status"] == "FAIL"
    assert "2026-08-06" in str(res["missing"])


def test_completeness_passes_when_every_traded_bar_left_evidence():
    decisions = [{"bar": "2026-08-06 00:00:00+00:00", "action": {"from": 0, "to": 1}}]
    res = check_fill_log_completeness(
        make_inputs(fills=[make_fill(bar="2026-08-06 00:00:00+00:00")],
                    decisions=decisions))
    assert res["status"] == "PASS"


def test_completeness_tolerates_extra_fills_without_decisions():
    """A kill-switch flatten trades outside the decision path by design."""
    res = check_fill_log_completeness(
        make_inputs(fills=[make_fill()],
                    decisions=[{"bar": "x", "action": None}]))
    assert res["status"] == "PASS"


# ------------------------------------------------------- C1: median slippage --
def test_c1_catches_a_median_above_the_model_assumption():
    fills = [make_fill(i, execution_slippage=0.0004) for i in range(5)]
    res = check_median_exec_slippage(make_inputs(fills=fills))
    assert res["status"] == "FAIL"


def test_c1_passes_at_the_modelled_slippage():
    fills = [make_fill(i, execution_slippage=0.0001) for i in range(5)]
    res = check_median_exec_slippage(make_inputs(fills=fills))
    assert res["status"] == "PASS"
    assert res["median"] == pytest.approx(0.0001)


def test_c1_is_skipped_when_no_fill_separates_slippage_from_drift():
    fills = [make_fill(mark_at_order=None, execution_slippage=None, drift=None)]
    res = check_median_exec_slippage(make_inputs(fills=fills))
    assert res["status"] == "SKIPPED"
    assert res["unverifiable"]


# ----------------------------------------------------------- C2: p90 slippage --
def test_c2_catches_a_fat_tail_the_median_hides():
    """Nine clean fills and one catastrophe: C1 passes, C2 must not."""
    fills = [make_fill(i, execution_slippage=0.0001) for i in range(8)]
    fills += [make_fill(8, execution_slippage=0.004),
              make_fill(9, execution_slippage=0.004)]
    assert check_median_exec_slippage(make_inputs(fills=fills))["status"] == "PASS"
    res = check_p90_exec_slippage(make_inputs(fills=fills))
    assert res["status"] == "FAIL"


def test_c2_passes_when_the_tail_is_bounded():
    fills = [make_fill(i, execution_slippage=0.0003) for i in range(10)]
    res = check_p90_exec_slippage(make_inputs(fills=fills))
    assert res["status"] == "PASS"


# ------------------------------------------------------------ C3: rejections --
def test_c3_catches_a_rejection_rate_above_two_percent():
    fills = [make_fill(i) for i in range(10)]
    rejections = [{"time": "t", "code": -2010, "message": "insufficient balance"}]
    res = check_rejection_rate(make_inputs(fills=fills, rejections=rejections))
    assert res["status"] == "FAIL"          # 1/11 ≈ 9%
    assert "-2010" in str(res["rejections"])


def test_c3_passes_when_rejections_are_rare():
    fills = [make_fill(i) for i in range(99)]
    rejections = [{"time": "t", "code": -1013, "message": "filter failure"}]
    res = check_rejection_rate(make_inputs(fills=fills, rejections=rejections))
    assert res["status"] == "PASS"          # 1/100 = 1%


def test_c3_is_skipped_before_any_submission():
    assert check_rejection_rate(make_inputs())["status"] == "SKIPPED"


# ---------------------------------------------------------- C4: partial fills --
def test_c4_catches_a_partially_filled_status():
    fills = [make_fill(status="PARTIALLY_FILLED")]
    res = check_partial_fills(make_inputs(fills=fills))
    assert res["status"] == "FAIL"


def test_c4_catches_an_execution_short_of_the_order():
    fills = [make_fill(requested_qty=0.0031, qty=0.0020)]
    res = check_partial_fills(make_inputs(fills=fills))
    assert res["status"] == "FAIL"


def test_c4_passes_full_executions_and_reports_unverifiable_backfills():
    """Backfilled fills predate requested_qty — verifiable by status only."""
    fills = [make_fill(0), make_fill(1, requested_qty=None)]
    res = check_partial_fills(make_inputs(fills=fills))
    assert res["status"] == "PASS"
    assert len(res["unverifiable"]) == 1


# ------------------------------------------------- C5: book<->venue divergence --
def test_c5_catches_a_venue_balance_that_did_not_move_with_the_fill():
    fills = [make_fill(venue_free_base_after=0.05)]     # bought, balance froze
    res = check_book_venue_divergence(make_inputs(fills=fills))
    assert res["status"] == "FAIL"


def test_c5_catches_the_impossible_state_book_exceeding_the_account():
    fills = [make_fill(book_qty_after=0.9)]
    res = check_book_venue_divergence(make_inputs(fills=fills))
    assert res["status"] == "FAIL"
    assert "book holds" in str(res["divergences"])


def test_c5_nets_a_base_asset_commission_out_of_the_expected_delta():
    """A BUY charged in BTC leaves less BTC than bought — that is not drift."""
    fills = [make_fill(fee_paid=0.0000031, fee_asset="BTC",
                       venue_free_base_after=0.05 + 0.0031 - 0.0000031)]
    res = check_book_venue_divergence(make_inputs(fills=fills))
    assert res["status"] == "PASS"


def test_c5_reconciles_a_sell_by_the_quantity_leaving():
    fills = [make_fill(side=-1, book_qty_after=0.0,
                       venue_free_base_before=0.0531,
                       venue_free_base_after=0.05)]
    res = check_book_venue_divergence(make_inputs(fills=fills))
    assert res["status"] == "PASS"


def test_c5_treats_missing_snapshots_as_unverifiable_not_passing():
    fills = [make_fill(venue_free_base_before=None, venue_free_base_after=None)]
    res = check_book_venue_divergence(make_inputs(fills=fills))
    assert res["status"] == "SKIPPED"
    assert res["unverifiable"]


# ----------------------------------------------------------------- C6: drift --
def test_c6_reports_drift_without_ever_gating():
    """Pre-registered: drift has NO threshold — even an ugly one must not FAIL."""
    fills = [make_fill(i, drift=0.005) for i in range(GATE_C_MIN_FILLS)]
    res = check_decision_drift(make_inputs(fills=fills))
    assert res["status"] == "PASS"
    assert res["gating"] is False
    assert res["median"] == pytest.approx(0.005)


def test_c6_is_skipped_without_drift_measurements():
    fills = [make_fill(drift=None)]
    assert check_decision_drift(make_inputs(fills=fills))["status"] == "SKIPPED"


# ------------------------------------------------------------------- verdicts --
def _decisions_for(fills):
    return [{"bar": f["bar"], "action": {"from": 0, "to": 1}} for f in fills]


def test_no_verdict_before_twenty_fills_even_when_everything_passes():
    fills = [make_fill(i) for i in range(GATE_C_MIN_FILLS - 1)]
    report = evaluate_cost_fidelity(
        make_inputs(fills=fills, decisions=_decisions_for(fills)), AS_OF)
    assert report["verdict"] == "COLLECTING"
    assert f"{GATE_C_MIN_FILLS - 1}/{GATE_C_MIN_FILLS}" in report["verdict_reason"]


def test_collecting_still_names_criteria_that_are_already_failing():
    """A broken pipe must be visible at fill 3, not at fill 20."""
    fills = [make_fill(i, status="PARTIALLY_FILLED") for i in range(3)]
    report = evaluate_cost_fidelity(
        make_inputs(fills=fills, decisions=_decisions_for(fills)), AS_OF)
    assert report["verdict"] == "COLLECTING"
    assert "c4_partial_fills" in report["verdict_reason"]


def test_pass_at_twenty_clean_fills():
    fills = [make_fill(i) for i in range(GATE_C_MIN_FILLS)]
    report = evaluate_cost_fidelity(
        make_inputs(fills=fills, decisions=_decisions_for(fills)), AS_OF)
    assert report["verdict"] == "PASS"


def test_fail_beats_incomplete_at_the_minimum():
    fills = [make_fill(i, execution_slippage=0.001) for i in range(GATE_C_MIN_FILLS)]
    report = evaluate_cost_fidelity(
        make_inputs(fills=fills, decisions=_decisions_for(fills)), AS_OF)
    assert report["verdict"] == "FAIL"
    assert "c1" in report["verdict_reason"]


def test_missing_evidence_yields_incomplete_never_pass():
    fills = [make_fill(i) for i in range(GATE_C_MIN_FILLS)]
    report = evaluate_cost_fidelity(make_inputs(fills=fills, decisions=[]), AS_OF)
    assert report["verdict"] == "INCOMPLETE"
    assert "fill_log_completeness" in report["verdict_reason"]


# ------------------------------------------------- durable store round-trip --
def test_fill_and_rejection_records_survive_a_local_round_trip(tmp_path):
    store = LocalJsonStateStore(str(tmp_path / "BTCUSDT_4h.json"))
    fill = make_fill()
    store.append_fill(fill)
    store.append_rejection({"time": "t", "code": -2010, "message": "no balance",
                            "recorded_at": "2026-08-07T00:00:00+00:00"})

    fills, rejections = load_cost_records_local(str(tmp_path / "BTCUSDT_4h.json"))
    assert len(fills) == 1 and len(rejections) == 1
    assert fills[0]["order_id"] == fill["order_id"]
    assert rejections[0]["code"] == -2010
