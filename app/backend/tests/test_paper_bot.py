"""Tests for PaperBot.step — the live orchestration loop.

Covers: the truncated-history guard, per-bar idempotency, the load-bearing
decision log (persisted with state, loud on failure, healed on the skipped
path), and the mark-to-market status summary.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from app.backend.backtesting.strategies import EmaCrossover
from app.backend.paper_trading import bot as bot_module
from app.backend.paper_trading.bot import BotConfig, PaperBot
from app.backend.paper_trading.portfolio import PaperPortfolio
from app.backend.paper_trading.state_store import LocalJsonStateStore
from app.backend.paper_trading.status_handler import _summarize


class MemoryStore:
    """In-memory stand-in with the same contract as the real stores."""

    def __init__(self) -> None:
        self.state = None
        self.decisions = {}
        self.fail_append = False

    def load(self):
        return json.loads(json.dumps(self.state)) if self.state else None

    def save(self, state):
        self.state = json.loads(json.dumps(state, default=str))

    def append_decision(self, record):
        if self.fail_append:
            raise RuntimeError("append failed")
        self.decisions[record["bar"]] = json.loads(json.dumps(record, default=str))

    def has_decision(self, bar):
        return bar in self.decisions


def _feed_df(n: int) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="1D", tz="UTC")
    base = np.linspace(100.0, 200.0, n)
    return pd.DataFrame({
        "open": base, "high": base * 1.01, "low": base * 0.99, "close": base,
    }, index=idx)


def _make_bot(monkeypatch, store, df) -> PaperBot:
    monkeypatch.setattr(bot_module, "make_state_store", lambda *a, **k: store)
    monkeypatch.setattr(bot_module, "fetch_klines", lambda *a, **k: df.copy())
    strategy = EmaCrossover(fast=5, slow=20, allow_short=False)
    return PaperBot(strategy, BotConfig(lookback_bars=len(df) + 1))


def test_step_refuses_truncated_history(monkeypatch):
    store = MemoryStore()
    df = _feed_df(150)
    bot = _make_bot(monkeypatch, store, df)
    monkeypatch.setattr(bot_module, "fetch_klines", lambda *a, **k: df.iloc[:80])
    with pytest.raises(RuntimeError, match="truncated history"):
        bot.step()
    assert store.state is None            # nothing was traded or persisted
    assert store.decisions == {}


def test_step_trades_logs_and_is_idempotent(monkeypatch):
    store = MemoryStore()
    df = _feed_df(150)
    bot = _make_bot(monkeypatch, store, df)

    first = bot.step()
    assert first["status"] == "traded"    # rising series -> long
    assert first["position"] == 1
    bar = first["bar"]
    assert store.has_decision(bar)
    assert store.state["last_bar"] == bar
    assert store.state["last_decision"]["bar"] == bar

    second = bot.step()                   # same bar again
    assert second["status"] == "skipped"
    assert len(store.decisions) == 1      # no duplicate record


def test_skipped_path_heals_missing_decision(monkeypatch):
    store = MemoryStore()
    df = _feed_df(150)
    _make_bot(monkeypatch, store, df).step()
    bar = store.state["last_bar"]
    del store.decisions[bar]              # simulate crash between save and append

    fresh = _make_bot(monkeypatch, store, df)   # new process, same store
    out = fresh.step()
    assert out["status"] == "skipped"
    assert out.get("decision_backfilled") is True
    assert store.decisions[bar] == store.state["last_decision"]


def test_append_failure_raises_then_heals(monkeypatch):
    store = MemoryStore()
    store.fail_append = True
    df = _feed_df(150)
    with pytest.raises(RuntimeError, match="append failed"):
        _make_bot(monkeypatch, store, df).step()   # loud failure -> alarm path
    bar = store.state["last_bar"]                  # state itself was saved
    assert bar is not None and not store.has_decision(bar)

    store.fail_append = False
    out = _make_bot(monkeypatch, store, df).step() # scheduler retry
    assert out["status"] == "skipped"
    assert out.get("decision_backfilled") is True
    assert store.has_decision(bar)


def test_local_store_has_decision(tmp_path):
    store = LocalJsonStateStore(str(tmp_path / "s.json"))
    assert store.has_decision("2026-01-01") is False
    store.append_decision({"bar": "2026-01-01", "target": 1})
    assert store.has_decision("2026-01-01") is True
    assert store.has_decision("2026-01-02") is False


def test_status_summary_marks_open_position_to_market():
    port = PaperPortfolio(fee_rate=0.001, slippage=0.0002, initial_capital=10_000.0)
    port.reconcile(1, 100.0, "t0")        # open long at 100
    port.reconcile(1, 130.0, "t1")        # bar processed at 130, still long
    state_item = {
        "state": {"symbol": "BTCUSDT", "strategy": "EMA20/100",
                  "last_bar": "t1", "portfolio": port.to_dict()},
        "updated_at": "2026-07-21T00:10:00+00:00",
    }
    data = _summarize(state_item)
    assert data["position"] == 1
    assert abs(data["equity"] - round(port.equity(130.0), 2)) < 1e-9
    assert data["equity"] > data["realized_equity"] * 1.2   # frozen realized misses the rally


def test_status_summary_flat_equals_realized():
    port = PaperPortfolio()
    port.reconcile(1, 100.0, "t0")
    port.reconcile(0, 110.0, "t1")        # one closed trade, now flat
    data = _summarize({"state": {"portfolio": port.to_dict()}})
    assert data["position"] == 0
    assert abs(data["equity"] - round(port.realized, 2)) < 1e-9
