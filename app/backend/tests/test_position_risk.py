"""F7 position risk — every trigger tested AT its boundary, per the kill-switch
test discipline: 9.9% must not fire where 10.1% must, both sides of each edge.

Thresholds are pre-registered (docs/F7_POSITION_RISK_2026-08-07.md) from
pre-holdout measurement; these tests pin the semantics that measurement
assumed: close-evaluated stop against the entry fill, re-entry blocked until
the strategy's own signal resets (the engine's ``blocked_side`` rule), and a
daily limit anchored to the first processed bar of the UTC day that clears
itself at midnight.
"""

from __future__ import annotations

import pytest

from app.backend.paper_trading.portfolio import PaperPortfolio
from app.backend.paper_trading.position_risk import (
    DAILY_LOSS_PCT,
    STOP_LOSS_PCT,
    PositionRiskState,
    apply,
)

ENTRY = 64_000.0


def long_book() -> PaperPortfolio:
    book = PaperPortfolio(initial_capital=200.0)
    book.reconcile(1, ENTRY, "2026-08-07 00:00:00+00:00")
    return book


def bar(hour: int, day: int = 7) -> str:
    return f"2026-08-{day:02d} {hour:02d}:00:00+00:00"


# ------------------------------------------------------------- pre-registered --
def test_thresholds_are_the_preregistered_ones():
    assert STOP_LOSS_PCT == 0.10
    assert DAILY_LOSS_PCT == 0.10


# ----------------------------------------------------------------- stop-loss --
def test_stop_does_not_fire_just_above_the_line():
    book = long_book()
    state = PositionRiskState()
    price = book.entry_fill * (1 - 0.099)
    assert apply(state, 1, book, price, bar(4)) == 1
    assert state.stop_blocked is False


def test_stop_fires_just_below_the_line_and_flattens():
    book = long_book()
    state = PositionRiskState()
    price = book.entry_fill * (1 - 0.101)
    assert apply(state, 1, book, price, bar(4)) == 0
    assert state.stop_blocked is True
    assert any("STOP" in e for e in state.last_events)


def test_stop_fires_exactly_at_the_line():
    """<= is the pre-registered comparison — the boundary itself triggers."""
    book = long_book()
    state = PositionRiskState()
    assert apply(state, 1, book, book.entry_fill * (1 - STOP_LOSS_PCT), bar(4)) == 0


def test_stopped_position_stays_blocked_while_signal_still_says_long():
    """The engine's blocked_side rule: no re-entry until the target flattens."""
    book = long_book()
    state = PositionRiskState()
    apply(state, 1, book, book.entry_fill * 0.85, bar(4))     # stopped out
    book.reconcile(0, book.entry_fill * 0.85, bar(4))          # book flattened
    assert apply(state, 1, book, ENTRY, bar(8)) == 0           # still long? no.
    assert state.stop_blocked is True


def test_signal_reset_clears_the_stop_block_and_allows_reentry():
    book = long_book()
    state = PositionRiskState()
    apply(state, 1, book, book.entry_fill * 0.85, bar(4))
    book.reconcile(0, book.entry_fill * 0.85, bar(4))
    assert apply(state, 0, book, ENTRY, bar(8)) == 0           # signal flat
    assert state.stop_blocked is False
    assert apply(state, 1, book, ENTRY, bar(12)) == 1          # fresh entry OK


def test_stop_is_inert_while_flat():
    state = PositionRiskState()
    book = PaperPortfolio(initial_capital=200.0)
    assert apply(state, 1, book, 1.0, bar(4)) == 1             # any price, flat book
    assert state.stop_blocked is False


# ------------------------------------------------------------- daily limit ----
# For a full-equity long, a 10% equity drop from the ENTRY equals the stop —
# so these tests anchor the day AFTER the price has risen: the daily limit
# then fires on a fall from the day's anchor while the stop (measured from
# the entry fill) stays silent, isolating the trigger under test.
HIGH = ENTRY * 1.20            # day-start anchor, +20% above entry
FALL = ENTRY * 1.06            # -11.7% from anchor, +6% above entry (no stop)


def test_daily_limit_does_not_fire_just_above_the_line():
    book = long_book()
    state = PositionRiskState()
    apply(state, 1, book, HIGH, bar(0))                        # anchors the day
    assert apply(state, 1, book, HIGH * (1 - 0.098), bar(4)) == 1
    assert state.daily_blocked is False


def test_daily_limit_fires_below_the_line_and_blocks_for_the_day():
    book = long_book()
    state = PositionRiskState()
    apply(state, 1, book, HIGH, bar(0))
    assert apply(state, 1, book, FALL, bar(4)) == 0
    assert state.daily_blocked is True
    assert state.stop_blocked is False                         # isolated trigger
    assert any("DAILY LIMIT" in e for e in state.last_events)
    # ... and stays blocked for the rest of the UTC day
    assert apply(state, 1, book, HIGH, bar(8)) == 0


def test_daily_block_clears_itself_at_utc_midnight():
    book = long_book()
    state = PositionRiskState()
    apply(state, 1, book, HIGH, bar(0))
    apply(state, 1, book, FALL, bar(4))
    assert state.daily_blocked is True
    assert apply(state, 1, book, HIGH, bar(0, day=8)) == 1     # new day, new anchor
    assert state.daily_blocked is False
    assert any("cleared" in e for e in state.last_events)


def test_day_anchor_is_the_first_processed_bar_of_the_day():
    book = long_book()
    state = PositionRiskState()
    apply(state, 1, book, ENTRY, bar(4))                       # first bar seen today
    anchor = state.day_start_equity
    apply(state, 1, book, ENTRY * 1.05, bar(8))                # later, higher
    assert state.day_start_equity == anchor                    # anchor unmoved


# ------------------------------------------------------------- persistence ----
def test_state_survives_a_dict_round_trip():
    state = PositionRiskState(stop_blocked=True, day="2026-08-07",
                              day_start_equity=200.0, daily_blocked=True)
    restored = PositionRiskState.from_dict(state.as_dict())
    assert restored == state


def test_from_dict_tolerates_missing_and_unknown_fields():
    restored = PositionRiskState.from_dict({"stop_blocked": True, "junk": 1})
    assert restored.stop_blocked is True
    assert restored.daily_blocked is False


# ------------------------------------------------------- bot integration ------
def test_bot_records_both_targets_when_the_overlay_overrides(monkeypatch, tmp_path):
    """The book reconciles the ALLOWED target; the strategy's own word is kept
    in the record so Gate A signal parity stays judgeable."""
    import pandas as pd

    from app.backend.paper_trading.bot import BotConfig, PaperBot

    class FlatLongStrategy:
        name = "always-long"

        def target_positions(self, df):
            return pd.Series(1, index=df.index)

    idx = pd.date_range("2026-08-01", periods=10, freq="4h", tz="UTC")
    df = pd.DataFrame({"open": 64_000.0, "high": 64_100.0, "low": 63_900.0,
                       "close": 64_000.0, "volume": 1.0}, index=idx)
    monkeypatch.setattr("app.backend.paper_trading.bot.fetch_klines",
                        lambda *a, **k: df)

    bot = PaperBot(FlatLongStrategy(),
                   BotConfig(symbol="BTCUSDT", timeframe="4h", lookback_bars=5,
                             initial_capital=200.0,
                             state_path=str(tmp_path / "s.json")))
    bot.target_overlay = lambda target, portfolio, price, time: 0

    status = bot.step()
    assert status["target"] == 0                     # what the book was allowed
    assert bot.last_decision["target"] == 0
    assert bot.last_decision["strategy_target"] == 1  # what the strategy said
    assert bot.portfolio.side == 0


def test_bot_without_overlay_is_byte_identical_to_before(monkeypatch, tmp_path):
    """The M5 1d path never sets the overlay — the seam must be invisible."""
    import pandas as pd

    from app.backend.paper_trading.bot import BotConfig, PaperBot

    class FlatLongStrategy:
        name = "always-long"

        def target_positions(self, df):
            return pd.Series(1, index=df.index)

    idx = pd.date_range("2026-08-01", periods=10, freq="1D", tz="UTC")
    df = pd.DataFrame({"open": 64_000.0, "high": 64_100.0, "low": 63_900.0,
                       "close": 64_000.0, "volume": 1.0}, index=idx)
    monkeypatch.setattr("app.backend.paper_trading.bot.fetch_klines",
                        lambda *a, **k: df)

    bot = PaperBot(FlatLongStrategy(),
                   BotConfig(lookback_bars=5, initial_capital=200.0,
                             state_path=str(tmp_path / "s.json")))
    status = bot.step()
    assert status["target"] == 1
    assert "strategy_target" not in bot.last_decision
    assert bot.portfolio.side == 1
