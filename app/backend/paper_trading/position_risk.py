"""F7: position-level risk controls — stop-loss + daily loss limit.

The kill switch protects the BOOK (halt + manual re-arm on catastrophe);
these controls protect the POSITION and recover automatically by rules
written down in advance (docs/F7_POSITION_RISK_2026-08-07.md — thresholds
pre-registered from measurement, 2026-08-07, before this module existed).

Semantics mirror the backtest engine deliberately (backtest = live):

- Stop-loss: evaluated on the CLOSED bar's price against the entry fill;
  when hit the target is forced flat and re-entry stays blocked until the
  strategy's own target returns to 0 — the engine's ``blocked_side`` rule.
  (Known, pre-registered divergence: the engine models intrabar stops on
  ``low``; a live 4h channel only sees closes. Measured: 7 vs 2 events in
  7.5 years at the 10% threshold.)
- Daily loss limit: equity vs the day's starting equity (UTC); when
  breached the position is flattened and NEW entries stay blocked until
  the next UTC day. No manual re-arm — machinery catastrophes are the
  kill switch's job, and it runs first.

Pure state machine: ``apply`` takes the strategy's target and returns the
target the book is allowed to reconcile. All I/O stays in the caller.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional

import pandas as pd

#: Pre-registered thresholds (docs/F7_POSITION_RISK_2026-08-07.md). Do not
#: tune after seeing live outcomes — that is fitting a safety control.
STOP_LOSS_PCT = 0.10
DAILY_LOSS_PCT = 0.10


@dataclass
class PositionRiskState:
    """Everything F7 needs, persisted beside the book (extra.position_risk)."""

    stop_blocked: bool = False           # stopped out; wait for target == 0
    day: Optional[str] = None            # UTC date the daily anchor belongs to
    day_start_equity: Optional[float] = None
    daily_blocked: bool = False          # daily limit hit; blocked until next day
    last_events: list = None             # what happened on the last evaluation

    def __post_init__(self) -> None:
        if self.last_events is None:
            self.last_events = []

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "PositionRiskState":
        if not d:
            return cls()
        known = {f: d[f] for f in cls().__dict__ if f in d}
        return cls(**known)


def _utc_day(bar_time: str) -> str:
    ts = pd.Timestamp(bar_time)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return str(ts.tz_convert("UTC").date())


def apply(state: PositionRiskState, target: int, portfolio,
          price: float, bar_time: str) -> int:
    """Return the target the book may reconcile; mutates ``state`` in place.

    ``portfolio`` is the live ``PaperPortfolio`` — read-only here (side,
    entry_fill, equity). Raising is fail-closed: the caller lets the run
    die loudly and no trade happens.
    """
    events: list[str] = []
    equity = float(portfolio.equity(price))

    # -- daily anchor rollover (before any judgement) ----------------------- #
    today = _utc_day(bar_time)
    if state.day != today:
        state.day = today
        state.day_start_equity = equity
        if state.daily_blocked:
            events.append("daily block cleared (new UTC day)")
        state.daily_blocked = False

    # -- stop re-arm: the strategy's own signal reset clears the block ------ #
    if state.stop_blocked and target == 0:
        state.stop_blocked = False
        events.append("stop block cleared (signal reset)")

    # -- stop-loss on the open position, close-evaluated -------------------- #
    if portfolio.side == 1 and portfolio.entry_fill > 0:
        stop_price = portfolio.entry_fill * (1.0 - STOP_LOSS_PCT)
        if price <= stop_price:
            events.append(
                f"STOP: close {price:.2f} <= {stop_price:.2f} "
                f"(entry {portfolio.entry_fill:.2f} -{STOP_LOSS_PCT:.0%})")
            state.stop_blocked = True

    # -- daily loss limit --------------------------------------------------- #
    if (not state.daily_blocked and state.day_start_equity
            and equity <= state.day_start_equity * (1.0 - DAILY_LOSS_PCT)):
        events.append(
            f"DAILY LIMIT: equity {equity:.2f} <= "
            f"{state.day_start_equity * (1.0 - DAILY_LOSS_PCT):.2f} "
            f"(day start {state.day_start_equity:.2f} -{DAILY_LOSS_PCT:.0%})")
        state.daily_blocked = True

    # -- verdict ------------------------------------------------------------ #
    allowed = target
    if state.stop_blocked or state.daily_blocked:
        allowed = 0
    if allowed != target:
        events.append(f"target {target} -> {allowed}")
    state.last_events = events
    return allowed
