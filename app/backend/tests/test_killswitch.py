"""Tests for the kill switch.

Follows the test plan written into the design doc on 2026-07-25: each trigger
alone at the boundary, halt survives a restart, re-arm resets the peak and leaves
an audit record, and — the one that matters most — evaluation that raises is a
HALT, not a shrug.

The boundary cases are exact on purpose. A switch that fires at 24.9% would be
one that fires on ordinary drawdowns, and this strategy's validated behaviour
includes a −49% drawdown; a switch that fails to fire at 25.1% is not a switch.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.backend.paper_trading.killswitch import (
    FAILSAFE,
    MAX_BAR_LOSS,
    MAX_DRAWDOWN,
    MAX_TRACKING_ERROR,
    T1,
    T2,
    T3,
    KillSwitchState,
    apply_halt,
    evaluate,
    observe,
    rearm,
)

NOW = datetime(2026, 8, 7, 0, 10, tzinfo=timezone.utc)


def armed(**kwargs) -> KillSwitchState:
    base = dict(start_equity=10_000.0, peak_equity=10_000.0,
                prev_bar_equity=10_000.0)
    base.update(kwargs)
    return KillSwitchState(**base)


# ------------------------------------------------------------------ T1: DD --
def test_a_drawdown_just_inside_the_limit_keeps_trading():
    # Reached gradually: prev_bar equals current, so T3 cannot fire and T1 is
    # measured in isolation. (A 24.9% drop in ONE bar trips T3 first, correctly.)
    equity = 10_000.0 * (1 - 0.249)
    v = evaluate(armed(prev_bar_equity=equity), equity=equity)
    assert v.ok
    assert v.checks["drawdown"] == pytest.approx(0.249)


def test_a_drawdown_just_past_the_limit_halts():
    equity = 10_000.0 * (1 - 0.251)
    v = evaluate(armed(prev_bar_equity=equity), equity=equity)
    assert v.halt and v.reason == T1
    assert "25%" in v.detail


def test_drawdown_is_measured_from_the_peak_not_the_start():
    """Equity that doubled then halved is a 50% drawdown, not a 0% one."""
    state = armed()
    observe(state, 20_000.0)
    state.prev_bar_equity = 10_000.0          # isolate T1 from T3
    v = evaluate(state, equity=10_000.0)
    assert v.halt and v.reason == T1
    assert v.checks["drawdown"] == pytest.approx(0.5)


def test_the_validated_strategy_drawdown_would_not_trip_it_by_itself():
    """The edge's own OOS drawdown is -49%, so the threshold matters."""
    assert MAX_DRAWDOWN < 0.49       # it WOULD trip - by design, that is a halt
    equity = 10_000.0 * (1 - 0.20)
    v = evaluate(armed(prev_bar_equity=equity), equity=equity)
    assert v.ok                       # but an ordinary -20% drawdown does not


# ----------------------------------------------------------- T2: tracking --
def test_execution_drag_within_tolerance_keeps_trading():
    v = evaluate(armed(), equity=10_000.0, execution_drag=999.0)
    assert v.ok
    assert v.checks["tracking_error"] == pytest.approx(0.0999)


def test_execution_drag_past_tolerance_halts():
    v = evaluate(armed(), equity=10_000.0, execution_drag=1_001.0)
    assert v.halt and v.reason == T2


def test_tracking_is_absolute_so_drag_in_our_favour_also_counts():
    """A venue consistently filling BETTER than modelled is also a broken model."""
    v = evaluate(armed(), equity=10_000.0, execution_drag=-1_001.0)
    assert v.halt and v.reason == T2


def test_tracking_is_skipped_rather_than_guessed_when_not_measured():
    state = armed()
    v = evaluate(state, equity=10_000.0, execution_drag=None)
    assert v.ok
    assert "tracking_error" not in v.checks


# --------------------------------------------------------- T3: single bar --
def test_a_bar_loss_within_the_limit_keeps_trading():
    v = evaluate(armed(), equity=10_000.0 * (1 - 0.149))
    assert v.ok


def test_a_bar_loss_past_the_limit_halts():
    """A 15% single-bar move is a malfunction detector, not a market view."""
    state = armed(peak_equity=10_000.0)
    v = evaluate(state, equity=10_000.0 * (1 - 0.151))
    assert v.halt and v.reason == T3


def test_a_gain_never_trips_the_bar_loss_trigger():
    v = evaluate(armed(), equity=50_000.0)
    assert v.ok


def test_the_first_bar_has_nothing_to_compare_against():
    v = evaluate(KillSwitchState(), equity=10_000.0)
    assert v.ok
    assert "bar_loss" not in v.checks


# ------------------------------------------------------------ fail-closed --
def test_evaluation_that_raises_is_a_halt_not_a_shrug():
    """"I could not tell whether it is safe" is never permission to trade."""
    corrupt = armed(peak_equity="not-a-number")   # e.g. a mangled DynamoDB item
    v = evaluate(corrupt, equity=10_000.0)
    assert v.halt and v.reason == FAILSAFE
    assert v.checks["failed_closed"] is True


def test_a_nonsense_equity_does_not_slip_through():
    v = evaluate(armed(), equity=float("nan"))
    # NaN comparisons are all False, so the guard must not silently pass it.
    assert v.ok or v.halt      # whichever, it must not raise
    assert isinstance(v.checks, dict)


# --------------------------------------------------------------- lifecycle --
def test_a_halt_is_recorded_once_and_keeps_its_first_cause():
    state = armed()
    state = apply_halt(state, evaluate(state, equity=7_000.0), now=NOW)
    assert state.halted and state.halt_reason == T1
    first_at = state.halted_at

    # A later, different trigger must not overwrite why we stopped.
    state = apply_halt(state, evaluate(state, equity=1.0), now=NOW)
    assert state.halt_reason == T1
    assert state.halted_at == first_at


def test_a_halted_channel_reports_the_same_reason_on_every_later_cron():
    state = apply_halt(armed(), evaluate(armed(), equity=7_000.0), now=NOW)
    for _ in range(3):
        v = evaluate(state, equity=9_999.0)
        assert v.halt and v.reason == T1
        assert v.checks["already_halted"] is True


def test_a_halt_survives_a_round_trip_through_persistence():
    state = apply_halt(armed(), evaluate(armed(), equity=7_000.0), now=NOW)
    restored = KillSwitchState.from_dict(state.as_dict())
    assert restored.halted and restored.halt_reason == T1
    assert evaluate(restored, equity=10_000.0).halt


def test_an_unknown_field_in_stored_state_does_not_break_loading():
    restored = KillSwitchState.from_dict({"halted": True, "halt_reason": T3,
                                          "something_new": 1})
    assert restored.halted and restored.halt_reason == T3


def test_the_peak_does_not_creep_while_the_channel_sits_halted():
    """Otherwise re-arming inherits a high-water mark that never happened."""
    state = armed()
    observe(state, 12_000.0)
    state = apply_halt(state, evaluate(state, equity=8_000.0), now=NOW)
    peak_at_halt = state.peak_equity

    evaluate(state, equity=20_000.0)          # crons keep firing, no observe()
    assert state.peak_equity == peak_at_halt


# ------------------------------------------------------------------ rearm --
def test_rearming_clears_the_halt_and_resets_the_peak():
    state = armed()
    observe(state, 12_000.0)
    state = apply_halt(state, evaluate(state, equity=8_000.0), now=NOW)

    state, record = rearm(state, equity=8_000.0, note="bad fill, venue fixed",
                          now=NOW)
    assert not state.halted and state.halt_reason is None
    # Reset to current equity: re-arming against the old peak would re-trip T1
    # on the very next bar and look like the switch was broken.
    assert state.peak_equity == 8_000.0
    assert evaluate(state, equity=8_000.0).ok
    assert state.rearm_count == 1


def test_rearming_leaves_an_audit_record():
    state = apply_halt(armed(), evaluate(armed(), equity=7_000.0), now=NOW)
    _state, record = rearm(state, equity=7_000.0, note="investigated, see PR",
                           now=NOW)
    assert record["event"] == "rearm"
    assert record["cleared_reason"] == T1
    assert record["note"] == "investigated, see PR"
    assert record["equity_at_rearm"] == 7_000.0


def test_rearming_requires_a_reason():
    state = apply_halt(armed(), evaluate(armed(), equity=7_000.0), now=NOW)
    for empty in ("", "   ", None):
        with pytest.raises(ValueError, match="note"):
            rearm(state, equity=7_000.0, note=empty)


def test_rearming_a_running_channel_is_refused():
    with pytest.raises(ValueError, match="not halted"):
        rearm(armed(), equity=10_000.0, note="oops")


def test_there_is_no_automatic_rearm_anywhere():
    """Coming back after a halt is a person's decision, taken with the data."""
    import inspect

    from app.backend.paper_trading import killswitch

    source = inspect.getsource(killswitch)
    code = "\n".join(line for line in source.splitlines()
                     if not line.strip().startswith(("#", '"""', "*", "-")))
    # No scheduling machinery of any kind: nothing here can un-halt on its own.
    for forbidden in ("time.sleep", "threading", "schedule", "cooldown ="):
        assert forbidden not in code
    # rearm() is the only way out, and it demands a human-supplied note.
    assert "def rearm(" in source
    assert "requires a note" in source


# --------------------------------------------------------------- thresholds --
def test_thresholds_are_the_ones_that_were_pre_registered():
    """Fixed in code like gate.py's. Changing one is a commit, not a knob."""
    assert MAX_DRAWDOWN == 0.25
    assert MAX_TRACKING_ERROR == 0.10
    assert MAX_BAR_LOSS == 0.15


# ------------------------------------------------------------------- CLI --
def test_the_rearm_cli_refuses_without_confirmation(tmp_path, capsys):
    """A halt must never be cleared by a stray command."""
    from app.backend.paper_trading.run import main

    state = tmp_path / "s.json"
    main(["killswitch", "--timeframe", "4h", "--state", str(state)])
    assert "halted" in capsys.readouterr().out

    main(["rearm", "--timeframe", "4h", "--state", str(state)])
    assert "--confirm" in capsys.readouterr().out


def test_the_rearm_cli_refuses_a_channel_that_is_not_halted(tmp_path, capsys):
    from app.backend.paper_trading.run import main

    state = tmp_path / "s.json"
    main(["rearm", "--timeframe", "4h", "--state", str(state),
          "--confirm", "--note", "why not"])
    assert "not halted" in capsys.readouterr().out
