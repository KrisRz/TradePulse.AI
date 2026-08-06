"""Max-drawdown kill switch — the circuit breaker between a bug and a loss.

Designed 2026-07-25 (``docs/KILL_SWITCH_DESIGN_2026-07-25.md``) with the note
"implement at M6". Built 2026-08-06 instead, for the reason that drove this whole
track: at M6 this would be brand-new, never-fired code guarding real money. The
4h channel already places real orders, so it can fire here first, for free.

Three triggers, thresholds fixed in code exactly as ``gate.py`` fixes its own.
Changing one is a commit with a justification, never a runtime knob.

============  =====================================  =========
Trigger       Measures                               Threshold
============  =====================================  =========
T1_MAX_DD     drawdown from the peak since start     > 25%
T2_TRACKING   execution drag vs what the model said  > 10%
T3_DAILY_LOSS single-bar loss                        > 15%
============  =====================================  =========

T1 is "the envelope is broken" — consistent with the pre-registered gate. T3 is a
malfunction detector: a 15% move in one bar is far outside how this strategy
behaves, so it means a bad fill, an API fault or a fat finger, not a market view.

T2 deserves its own note. The design specifies "live vs paper divergence", and
for this channel that is measurable without running a parallel book: every fill
already carries what the venue did *and* what the model said it would do, so the
accumulated difference between them IS the tracking error. It measures execution
and cost quality, never the strategy — a strategy that simply loses money must
not trip a switch meant for broken plumbing.

Two properties the design calls out, and this module guarantees:

* **Fail-closed.** If evaluation raises, that is a HALT. "I could not work out
  whether it is safe, so I kept trading" is the failure mode this exists to
  prevent.
* **Idempotent.** Evaluating a halted state changes nothing and re-reports the
  original reason, so every subsequent cron is a no-op rather than a new event.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

#: Drawdown from the peak equity recorded since the channel started.
MAX_DRAWDOWN = 0.25
#: Accumulated execution drag (venue vs model), as a fraction of starting equity.
MAX_TRACKING_ERROR = 0.10
#: Loss within a single bar. Well outside p99 of how this strategy behaves.
MAX_BAR_LOSS = 0.15

T1 = "T1_MAX_DD"
T2 = "T2_TRACKING"
T3 = "T3_DAILY_LOSS"
FAILSAFE = "T0_EVALUATION_FAILED"


@dataclass
class KillSwitchState:
    """Everything the switch needs, persisted beside the book.

    ``peak_equity`` is the high-water mark since the channel started (or since
    the last re-arm), which is what makes T1 a drawdown rather than a loss.
    """

    halted: bool = False
    halt_reason: Optional[str] = None
    halt_detail: Optional[str] = None
    halted_at: Optional[str] = None
    start_equity: Optional[float] = None
    peak_equity: Optional[float] = None
    prev_bar_equity: Optional[float] = None
    execution_drag: float = 0.0          # cumulative, in quote units
    rearm_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "KillSwitchState":
        if not d:
            return cls()
        known = {f: d[f] for f in cls().__dict__ if f in d}
        return cls(**known)


@dataclass
class Verdict:
    """Outcome of one evaluation."""

    halt: bool
    reason: Optional[str] = None
    detail: Optional[str] = None
    checks: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.halt


def _drawdown(equity: float, peak: float) -> float:
    if peak <= 0:
        return 0.0
    return max(0.0, (peak - equity) / peak)


def evaluate(state: KillSwitchState, equity: float,
             execution_drag: Optional[float] = None) -> Verdict:
    """Decide whether trading may continue, given the state BEFORE this bar.

    ``equity`` is marked-to-market at the current price. ``execution_drag`` is
    the cumulative quote-currency cost of fills landing away from what the model
    predicted; pass ``None`` on channels that do not execute against a venue and
    T2 is skipped rather than guessed.

    Deliberately pure: no clock, no I/O, no persistence. The caller decides what
    to do with a halt, which is what makes every branch here testable.
    """
    try:
        if state.halted:
            # Idempotent: a halted channel stays halted with its original reason.
            return Verdict(halt=True, reason=state.halt_reason,
                           detail=state.halt_detail,
                           checks={"already_halted": True})

        checks: dict[str, Any] = {}
        start = state.start_equity if state.start_equity is not None else equity
        peak = state.peak_equity if state.peak_equity is not None else equity

        drawdown = _drawdown(equity, peak)
        checks["drawdown"] = drawdown
        if drawdown > MAX_DRAWDOWN:
            return Verdict(True, T1,
                           f"drawdown {drawdown:.1%} from peak {peak:,.2f} "
                           f"exceeds {MAX_DRAWDOWN:.0%}", checks)

        if execution_drag is not None and start > 0:
            tracking = abs(execution_drag) / start
            checks["tracking_error"] = tracking
            if tracking > MAX_TRACKING_ERROR:
                return Verdict(True, T2,
                               f"execution drag {execution_drag:,.2f} is "
                               f"{tracking:.1%} of starting equity, over "
                               f"{MAX_TRACKING_ERROR:.0%}", checks)

        if state.prev_bar_equity:
            bar_loss = (state.prev_bar_equity - equity) / state.prev_bar_equity
            checks["bar_loss"] = bar_loss
            if bar_loss > MAX_BAR_LOSS:
                return Verdict(True, T3,
                               f"lost {bar_loss:.1%} in one bar "
                               f"({state.prev_bar_equity:,.2f} -> {equity:,.2f}), "
                               f"over {MAX_BAR_LOSS:.0%}", checks)

        return Verdict(False, checks=checks)

    except Exception as exc:  # noqa: BLE001 - deliberately broad, see docstring
        # Fail-closed. Not being able to establish safety is not permission to
        # keep trading.
        return Verdict(True, FAILSAFE,
                       f"kill-switch evaluation raised {type(exc).__name__}: {exc}",
                       {"failed_closed": True})


def apply_halt(state: KillSwitchState, verdict: Verdict,
               now: Optional[datetime] = None) -> KillSwitchState:
    """Record a halt. Never overwrites an earlier one — the first cause is the cause."""
    if not verdict.halt or state.halted:
        return state
    state.halted = True
    state.halt_reason = verdict.reason
    state.halt_detail = verdict.detail
    state.halted_at = (now or datetime.now(timezone.utc)).isoformat()
    return state


def observe(state: KillSwitchState, equity: float,
            execution_drag: Optional[float] = None) -> KillSwitchState:
    """Fold this bar into the state, after a clean evaluation.

    Only called when trading was allowed: a halted channel's peak must not creep
    upward while it sits idle, or re-arming would inherit a meaningless
    high-water mark.
    """
    if state.start_equity is None:
        state.start_equity = equity
    state.peak_equity = equity if state.peak_equity is None \
        else max(state.peak_equity, equity)
    state.prev_bar_equity = equity
    if execution_drag is not None:
        state.execution_drag = execution_drag
    return state


def rearm(state: KillSwitchState, equity: float, note: str,
          now: Optional[datetime] = None) -> tuple[KillSwitchState, dict]:
    """Clear a halt, deliberately and with a record.

    The peak resets to current equity: re-arming against the old high-water mark
    would re-trip T1 on the next bar, which would look like the switch was broken
    rather than doing exactly what it was told.

    Returns the new state and an audit record for the decision log. There is no
    auto-rearm and no timer anywhere in this module — coming back after a halt is
    a person's decision, taken while looking at the data.
    """
    if not state.halted:
        raise ValueError("channel is not halted — nothing to re-arm")
    if not note or not note.strip():
        raise ValueError("re-arming requires a note explaining why")

    record = {
        "event": "rearm",
        "at": (now or datetime.now(timezone.utc)).isoformat(),
        "cleared_reason": state.halt_reason,
        "cleared_detail": state.halt_detail,
        "halted_at": state.halted_at,
        "equity_at_rearm": equity,
        "note": note.strip(),
    }
    state.halted = False
    state.halt_reason = None
    state.halt_detail = None
    state.halted_at = None
    state.peak_equity = equity
    state.prev_bar_equity = equity
    state.execution_drag = 0.0
    state.rearm_count += 1
    return state, record
