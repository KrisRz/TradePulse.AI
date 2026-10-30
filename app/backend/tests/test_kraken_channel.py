"""The Kraken paper channel: feed, configuration, kill switch, Gate A replay.

Runs the channel the way the Lambda does — a fresh bot loaded from the store
every day, one new closed bar each time — over a market that first trends and
then crashes far enough to fire the account kill switch.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from app.backend.backtesting.strategies import EmaCrossover
from app.backend.paper_trading import bot as bot_module
from app.backend.paper_trading import feed
from app.backend.paper_trading import kraken_paper_handler as kph
from app.backend.paper_trading.gate import FidelityInputs, check_accounting_parity
from app.backend.paper_trading.killswitch import KillSwitchState
from app.backend.tests.test_paper_bot import MemoryStore


# --------------------------------------------------------------------------- #
# feed
# --------------------------------------------------------------------------- #

class _Resp:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


def _kraken_body(n: int, error=None):
    t0 = 1_700_000_000 - 1_700_000_000 % 86_400
    rows = [[t0 + i * 86_400, f"{100 + i}.0", f"{101 + i}.0", f"{99 + i}.0",
             f"{100.5 + i}", f"{100.2 + i}", "1.5", 10] for i in range(n)]
    return {"error": error or [], "result": {"XXBTZGBP": rows, "last": rows[-1][0]}}


def test_kraken_feed_drops_the_open_bar_and_honours_limit(monkeypatch):
    seen = {}

    def fake_get(url, params, timeout):
        seen.update(url=url, params=params)
        return _Resp(_kraken_body(10))

    monkeypatch.setattr(feed.requests, "get", fake_get)
    df = feed.fetch_kraken_ohlc("XBTGBP", "1d", limit=5)
    assert seen["params"] == {"pair": "XBTGBP", "interval": 1440}
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 4, "limit counts the open bar, as on Binance"
    assert df["close"].iloc[-1] == 100.5 + 8, "the 10th (open) bar must be gone"
    assert str(df.index.tz) == "UTC"


def test_kraken_feed_raises_on_api_error(monkeypatch):
    monkeypatch.setattr(feed.requests, "get",
                        lambda *a, **k: _Resp(_kraken_body(3, error=["EQuery:Unknown asset pair"])))
    with pytest.raises(RuntimeError, match="Unknown asset pair"):
        feed.fetch_kraken_ohlc("NOPE", "1d")


def test_kraken_feed_cannot_serve_a_lookback_it_does_not_keep(monkeypatch):
    monkeypatch.setattr(feed.requests, "get", lambda *a, **k: _Resp(_kraken_body(720)))
    assert len(feed.fetch_kraken_ohlc("XBTGBP", "1d", limit=400)) == 399
    assert len(feed.fetch_kraken_ohlc("XBTGBP", "1d", limit=900)) == 719


# --------------------------------------------------------------------------- #
# the channel, day by day
# --------------------------------------------------------------------------- #

def _market() -> pd.DataFrame:
    """Flat, a long rally, then a slide that halves the account's BTC sleeve twice."""
    flat = [100.0] * 150
    rally = [100.0 * 1.012 ** i for i in range(1, 120)]
    crash = [rally[-1] * 0.97 ** i for i in range(1, 60)]
    close = np.array(flat + rally + crash)
    idx = pd.date_range("2025-01-01", periods=len(close), freq="1D", tz="UTC")
    return pd.DataFrame({"open": close, "high": close * 1.002, "low": close * 0.998,
                         "close": close, "volume": 1.0}, index=idx)


def _run_days(monkeypatch, store, df, start: int, end: int, lookback: int = 120):
    monkeypatch.setattr(bot_module, "make_state_store", lambda *a, **k: store)
    monkeypatch.setattr(bot_module, "fetch_klines",
                        lambda *a, **k: pytest.fail("the Kraken channel read Binance"))
    results = []
    for day in range(start, end):
        visible = df.iloc[:day]
        monkeypatch.setattr(bot_module, "fetch_kraken_ohlc",
                            lambda *a, _v=visible, **k: _v.iloc[-(lookback - 1):].copy())
        bot = kph.build_kraken_bot(200.0)
        bot.strategy = EmaCrossover(fast=20, slow=100, allow_short=False)
        bot.config.lookback_bars = lookback
        results.append(kph.run_step(bot))
    return results


def test_channel_is_configured_as_preregistered(monkeypatch):
    assert (kph.FEE_RATE, kph.EXPOSURE, kph.REBALANCE_BAND, kph.MIN_REBALANCE) == \
        (0.008, 0.5, 0.15, 5.0)
    monkeypatch.setattr(bot_module, "make_state_store", lambda *a, **k: MemoryStore())
    bot = kph.build_kraken_bot(200.0)
    assert (bot.config.symbol, bot.config.timeframe, bot.config.source) == ("XBTGBP", "1d", "kraken")
    book = bot.portfolio
    assert (book.fee_rate, book.initial_capital) == (0.008, 200.0)
    assert (book.exposure, book.rebalance_band, book.min_rebalance) == (0.5, 0.15, 5.0), \
        "the book must carry every sizing parameter, not just the headline ones"


def test_daily_runs_trade_rebalance_and_halt_on_the_account_drawdown(monkeypatch):
    store, df = MemoryStore(), _market()
    results = _run_days(monkeypatch, store, df, 121, len(df) + 1)

    statuses = [r["status"] for r in results]
    assert "traded" in statuses, "the rally must open the position"
    state = store.state
    book = state["portfolio"]
    assert book["exposure"] == 0.5 and book["rebalance_band"] == 0.15
    assert book["rebalances"], "the rally must push the share out of the band"

    switch = KillSwitchState.from_dict(state["extra"]["killswitch"])
    assert switch.halted and switch.halt_reason == "T1_MAX_DD"
    assert book["side"] == 0, "a halt must leave the book flat"
    first_halt = statuses.index("HALTED")
    assert all(s in ("HALTED",) for s in statuses[first_halt:]), "halted stays halted"

    records = sorted(store.decisions.values(), key=lambda r: r["bar"])
    assert all(r["source"] == "kraken" and r["exposure"] == 0.5 for r in records)
    halt_rec = records[first_halt]
    assert halt_rec["target"] == 0 and halt_rec.get("strategy_target") == 1


def test_gate_a_replays_the_kraken_book_to_the_cent(monkeypatch):
    store, df = MemoryStore(), _market()
    _run_days(monkeypatch, store, df, 121, len(df) + 1)
    inputs = FidelityInputs(decisions=list(store.decisions.values()),
                            state=json.loads(json.dumps(store.state)),
                            bars=df, strategy=EmaCrossover(20, 100, allow_short=False))
    out = check_accounting_parity(inputs)
    assert out["status"] == "PASS", out


def test_gate_a_catches_a_book_replayed_without_its_band(monkeypatch):
    store, df = MemoryStore(), _market()
    _run_days(monkeypatch, store, df, 121, len(df) + 1)
    state = json.loads(json.dumps(store.state))
    state["portfolio"]["rebalance_band"] = None          # what the old replay assumed
    inputs = FidelityInputs(decisions=list(store.decisions.values()), state=state,
                            bars=df, strategy=EmaCrossover(20, 100, allow_short=False))
    assert check_accounting_parity(inputs)["status"] == "FAIL"


def test_a_quiet_long_window_is_not_described_as_flat(monkeypatch):
    """Day 0 of the live Kraken channel sat LONG; the caveat said "target 0"."""
    from app.backend.paper_trading.gate import check_signal_parity

    store, df = MemoryStore(), _market()
    _run_days(monkeypatch, store, df, 230, 236)
    records = list(store.decisions.values())
    assert {r["target"] for r in records} == {1}
    inputs = FidelityInputs(decisions=records, state=store.state, bars=df,
                            strategy=EmaCrossover(20, 100, allow_short=False),
                            lookback_bars=120)
    out = check_signal_parity(inputs)
    assert out["status"] == "PASS" and out["discriminating"] is False
    assert "stayed in the market" in out["detail"] and "flat" not in out["detail"]
