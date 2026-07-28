"""Gate A tests — execution fidelity, the M5 criterion decidable in 8 weeks.

Each criterion is tested twice: it must PASS on a faithful log, and it must
catch the specific corruption it exists to catch. A fidelity check that cannot
fail is worse than no check — it would certify the window as honest without
looking. Synthetic bars only (sanctioned exception for unit tests).
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from app.backend.backtesting.strategies import EmaCrossover
from app.backend.paper_trading.gate import (
    FidelityInputs, check_accounting_parity, check_infrastructure,
    check_log_completeness, check_no_lookahead, check_price_parity,
    check_signal_parity, evaluate_fidelity)
from app.backend.paper_trading.portfolio import PaperPortfolio

AS_OF = date(2026, 9, 10)
LOOKBACK = 30          # decision window = LOOKBACK - 1 = 29 bars, as the bot does
FEE, SLIP, CAPITAL = 0.001, 0.0002, 10_000.0


# --------------------------------------------------------------------------- #
# Fixtures — a bar history plus the decision log a faithful bot would produce
# --------------------------------------------------------------------------- #
def make_bars(n: int = 60, start: str = "2026-06-01") -> pd.DataFrame:
    """Flat → rally → decline, so the log contains a full closed round trip.

    A fixture where the bot never takes a position would let the parity and
    accounting checks pass trivially — they would never touch entry/exit
    accounting or a non-zero target.
    """
    idx = pd.date_range(start, periods=n, freq="D", tz="UTC")
    flat, rally, decline = 20, 20, n - 40
    closes = [100.0] * flat
    closes += [100.0 + (i + 1) * 5.0 for i in range(rally)]          # 105 → 200
    closes += [closes[-1] - (i + 1) * 4.0 for i in range(decline)]   # 196 → …
    return pd.DataFrame(
        {"open": closes, "high": [c * 1.01 for c in closes],
         "low": [c * 0.99 for c in closes], "close": closes,
         "volume": [1.0] * n},
        index=idx,
    ).rename_axis("time")


def make_faithful_log(bars: pd.DataFrame, strategy, n_decisions: int = 25) -> tuple[list[dict], dict]:
    """Exactly what a correct bot would have written for the last n bars."""
    window = max(LOOKBACK - 1, 1)
    portfolio = PaperPortfolio(fee_rate=FEE, slippage=SLIP, initial_capital=CAPITAL)
    decisions = []
    positions = range(len(bars) - n_decisions, len(bars))

    for pos in positions:
        bar = bars.index[pos]
        history = bars.iloc[max(0, pos + 1 - window): pos + 1]
        target = int(strategy.target_positions(history).iloc[-1])
        price = float(bars["close"].iloc[pos])
        portfolio.reconcile(target, price, str(bar))
        decisions.append({
            "bar": str(bar),
            "processed_at": (bar + pd.Timedelta(days=1, minutes=10)).isoformat(),
            "symbol": "BTCUSDT", "timeframe": "1d", "strategy": strategy.name,
            "price": price, "target": target, "position": portfolio.side,
            "equity": round(portfolio.equity(price), 2),
            "realized": round(portfolio.realized, 2),
            "fee_rate": FEE, "slippage": SLIP,
        })

    state = {"portfolio": portfolio.to_dict()}
    return decisions, state


@pytest.fixture
def faithful():
    bars = make_bars()
    strategy = EmaCrossover(fast=3, slow=8, allow_short=False)
    decisions, state = make_faithful_log(bars, strategy)
    return FidelityInputs(
        decisions=decisions, state=state, bars=bars, strategy=strategy,
        timeframe="1d", lookback_bars=LOOKBACK,
        infra={"days_checked": 15, "days_without_invocation": [],
               "dlq_messages_max": 0.0, "alarms_fired": []},
    )


def corrupt(inputs: FidelityInputs, **changes) -> FidelityInputs:
    """Copy with individual fields replaced — keeps each test isolated."""
    fields = {"decisions": [dict(d) for d in inputs.decisions],
              "state": inputs.state, "bars": inputs.bars,
              "strategy": inputs.strategy, "timeframe": inputs.timeframe,
              "lookback_bars": inputs.lookback_bars, "infra": inputs.infra}
    fields.update(changes)
    return FidelityInputs(**fields)


# --------------------------------------------------------------------------- #
# The faithful log passes everything
# --------------------------------------------------------------------------- #
def test_fixture_actually_exercises_a_round_trip(faithful):
    """Guard the guards: a flat fixture would make most checks vacuous."""
    assert len(faithful.state["portfolio"]["trades"]) >= 1, "fixture never closed a trade"
    targets = {int(d["target"]) for d in faithful.decisions}
    assert targets == {0, 1}, f"fixture should go long and flat, saw {targets}"


def test_faithful_log_passes_all_six(faithful):
    report = evaluate_fidelity(faithful, AS_OF)
    assert report["verdict"] == "PASS", report
    assert all(c["status"] == "PASS" for c in report["criteria"].values())
    assert len(report["criteria"]) == 6


def test_gate_a_never_claims_to_unlock_money(faithful):
    assert "does not unlock real money" in evaluate_fidelity(faithful, AS_OF)["note"]


# --------------------------------------------------------------------------- #
# 1. Log completeness
# --------------------------------------------------------------------------- #
def test_completeness_catches_a_missing_bar(faithful):
    dropped = faithful.decisions[:5] + faithful.decisions[6:]
    res = check_log_completeness(corrupt(faithful, decisions=dropped))
    assert res["status"] == "FAIL"
    assert res["missing"], res


def test_completeness_catches_a_duplicate_bar(faithful):
    doubled = faithful.decisions + [dict(faithful.decisions[3])]
    res = check_log_completeness(corrupt(faithful, decisions=doubled))
    assert res["status"] == "FAIL"
    assert res["duplicates"], res


def test_completeness_catches_a_bar_the_exchange_never_had(faithful):
    ghost = dict(faithful.decisions[-1])
    ghost["bar"] = str(pd.Timestamp(str(ghost["bar"])) + pd.Timedelta(hours=7))
    res = check_log_completeness(corrupt(faithful, decisions=faithful.decisions + [ghost]))
    assert res["status"] == "FAIL"
    assert res["unknown_bars"], res


def test_completeness_fails_on_empty_log(faithful):
    assert check_log_completeness(corrupt(faithful, decisions=[]))["status"] == "FAIL"


# --------------------------------------------------------------------------- #
# 2. Signal parity — the check that a different strategy went live
# --------------------------------------------------------------------------- #
def test_signal_parity_catches_a_flipped_target(faithful):
    tampered = [dict(d) for d in faithful.decisions]
    tampered[7]["target"] = 1 - int(tampered[7]["target"])
    res = check_signal_parity(corrupt(faithful, decisions=tampered))
    assert res["status"] == "FAIL"
    assert len(res["mismatches"]) == 1


def test_signal_parity_catches_the_wrong_strategy_running(faithful):
    """Verifying against different EMA periods than the bot used must fail."""
    res = check_signal_parity(
        corrupt(faithful, strategy=EmaCrossover(fast=8, slow=20, allow_short=False)))
    assert res["status"] == "FAIL"


def test_signal_parity_reports_unverifiable_bars_without_passing_silently(faithful):
    """Too little reference history to rebuild the window -> SKIPPED, not PASS."""
    res = check_signal_parity(corrupt(faithful, lookback_bars=10_000))
    assert res["status"] == "SKIPPED"
    assert res["unverifiable"]


# --------------------------------------------------------------------------- #
# 3. Price parity
# --------------------------------------------------------------------------- #
def test_price_parity_catches_a_wrong_price(faithful):
    tampered = [dict(d) for d in faithful.decisions]
    tampered[2]["price"] = float(tampered[2]["price"]) * 1.001
    res = check_price_parity(corrupt(faithful, decisions=tampered))
    assert res["status"] == "FAIL"
    assert len(res["mismatches"]) == 1


def test_price_parity_tolerates_float_noise(faithful):
    tampered = [dict(d) for d in faithful.decisions]
    tampered[2]["price"] = float(tampered[2]["price"]) * (1 + 1e-12)
    assert check_price_parity(corrupt(faithful, decisions=tampered))["status"] == "PASS"


# --------------------------------------------------------------------------- #
# 4. No look-ahead — the most important one: acting on an unclosed bar
# --------------------------------------------------------------------------- #
def test_lookahead_catches_a_decision_made_before_the_bar_closed(faithful):
    tampered = [dict(d) for d in faithful.decisions]
    bar = pd.Timestamp(str(tampered[4]["bar"]))
    tampered[4]["processed_at"] = (bar + pd.Timedelta(hours=6)).isoformat()
    res = check_no_lookahead(corrupt(faithful, decisions=tampered))
    assert res["status"] == "FAIL"
    assert len(res["violations"]) == 1


def test_lookahead_accepts_a_decision_exactly_at_bar_close(faithful):
    tampered = [dict(d) for d in faithful.decisions]
    bar = pd.Timestamp(str(tampered[4]["bar"]))
    tampered[4]["processed_at"] = (bar + pd.Timedelta(days=1)).isoformat()
    assert check_no_lookahead(corrupt(faithful, decisions=tampered))["status"] == "PASS"


def test_lookahead_handles_naive_timestamps_as_utc(faithful):
    tampered = [dict(d) for d in faithful.decisions]
    bar = pd.Timestamp(str(tampered[4]["bar"]))
    tampered[4]["processed_at"] = str((bar + pd.Timedelta(days=1, hours=2)).tz_localize(None))
    assert check_no_lookahead(corrupt(faithful, decisions=tampered))["status"] == "PASS"


def test_lookahead_skips_on_unknown_timeframe(faithful):
    assert check_no_lookahead(corrupt(faithful, timeframe="7d"))["status"] == "SKIPPED"


# --------------------------------------------------------------------------- #
# 5. Accounting parity — replay must reproduce the recorded book
# --------------------------------------------------------------------------- #
def test_accounting_parity_catches_tampered_equity(faithful):
    tampered = [dict(d) for d in faithful.decisions]
    tampered[9]["equity"] = float(tampered[9]["equity"]) + 5.0
    res = check_accounting_parity(corrupt(faithful, decisions=tampered))
    assert res["status"] == "FAIL"
    assert res["drifts"]


def test_accounting_parity_catches_a_wrong_fee_rate_in_the_book(faithful):
    """A live book charging different fees than the backtest breaks parity."""
    book = dict(faithful.state["portfolio"])
    book["fee_rate"] = 0.01
    res = check_accounting_parity(corrupt(faithful, state={"portfolio": book}))
    assert res["status"] == "FAIL"


def test_accounting_parity_catches_a_lost_trade_in_the_state(faithful):
    book = dict(faithful.state["portfolio"])
    book["trades"] = []
    res = check_accounting_parity(corrupt(faithful, state={"portfolio": book}))
    assert res["status"] == "FAIL"
    assert any("closed trades" in d for d in res["drifts"])


def test_accounting_parity_tolerates_cent_rounding(faithful):
    """Records store cents; the check must not fail on the rounding itself."""
    assert check_accounting_parity(faithful)["status"] == "PASS"


# --------------------------------------------------------------------------- #
# 6. Infrastructure continuity
# --------------------------------------------------------------------------- #
def test_infrastructure_catches_a_day_the_scheduler_never_ran(faithful):
    res = check_infrastructure(corrupt(faithful, infra={
        "days_checked": 15, "days_without_invocation": [date(2026, 8, 1)],
        "dlq_messages_max": 0.0, "alarms_fired": []}))
    assert res["status"] == "FAIL"
    assert res["days_without_invocation"]


def test_infrastructure_catches_dlq_messages(faithful):
    res = check_infrastructure(corrupt(faithful, infra={
        "days_checked": 15, "days_without_invocation": [],
        "dlq_messages_max": 3.0, "alarms_fired": []}))
    assert res["status"] == "FAIL"


def test_infrastructure_catches_a_fired_alarm(faithful):
    res = check_infrastructure(corrupt(faithful, infra={
        "days_checked": 15, "days_without_invocation": [],
        "dlq_messages_max": 0.0, "alarms_fired": ["tradepulse-paper-bot-errors @ x"]}))
    assert res["status"] == "FAIL"


def test_infrastructure_skips_when_aws_was_not_queried(faithful):
    assert check_infrastructure(corrupt(faithful, infra=None))["status"] == "SKIPPED"


# --------------------------------------------------------------------------- #
# Verdict precedence — the honesty rules of Gate A
# --------------------------------------------------------------------------- #
def test_missing_evidence_yields_incomplete_never_pass(faithful):
    report = evaluate_fidelity(corrupt(faithful, infra=None), AS_OF)
    assert report["verdict"] == "INCOMPLETE"
    assert "infrastructure" in report["verdict_reason"]


def test_a_failure_outranks_missing_evidence(faithful):
    tampered = [dict(d) for d in faithful.decisions]
    tampered[3]["target"] = 1 - int(tampered[3]["target"])
    report = evaluate_fidelity(corrupt(faithful, decisions=tampered, infra=None), AS_OF)
    assert report["verdict"] == "FAIL"
    assert "signal_parity" in report["verdict_reason"]


def test_verdict_is_computable_before_the_earliest_evaluation_date(faithful):
    """Unlike Gate B, Gate A is not date-gated — it can run any day."""
    early = evaluate_fidelity(faithful, date(2026, 8, 1))
    assert early["verdict"] == "PASS"
    assert early["window_days"] == (date(2026, 8, 1) - date(2026, 7, 16)).days


# --------------------------------------------------------------------------- #
# Discriminating power — a PASS earned in a flat window must say so
# --------------------------------------------------------------------------- #
def _flatten(inputs: FidelityInputs) -> FidelityInputs:
    """A log where every target is 0 — what a bear-market M5 window looks like."""
    flat_bars = inputs.bars.copy()
    flat_bars[["open", "high", "low", "close"]] = 100.0
    strategy = inputs.strategy
    decisions, state = make_faithful_log(flat_bars, strategy)
    return corrupt(inputs, decisions=decisions, state=state, bars=flat_bars)


def test_flat_window_parity_passes_but_flags_low_power(faithful):
    res = check_signal_parity(_flatten(faithful))
    assert res["status"] == "PASS"
    assert res["discriminating"] is False
    assert "cannot distinguish" in res["detail"]


def test_active_window_parity_is_marked_discriminating(faithful):
    res = check_signal_parity(faithful)
    assert res["status"] == "PASS"
    assert res["discriminating"] is True


def test_flat_window_caveat_reaches_the_verdict(faithful):
    report = evaluate_fidelity(_flatten(faithful), AS_OF)
    assert report["verdict"] == "PASS"
    assert report["caveats"], "a flat-window PASS must carry its caveat"
    assert "with caveats" in report["verdict_reason"]


def test_active_window_has_no_caveats(faithful):
    assert evaluate_fidelity(faithful, AS_OF)["caveats"] == []
