"""Tests for the dead-man switch (audit §10 KROK 4).

The failure this guards against cannot be caught by anything inside the account:
if the region or the account goes away, no exception is thrown, no metric moves,
and every CloudWatch alarm we own stays green because it is gone too. Silence is
indistinguishable from health. So the tests here are mostly about the two
properties that make an outside-in signal trustworthy:

* the ping can never break the bot (a monitoring outage must not become a
  trading outage);
* the absence of configuration is not an error — most people running this code
  will not have a dead-man service, and the bot must trade perfectly well anyway.

Plus the one that is easy to get backwards: a HALT must ping the *failure*
endpoint. A halted channel returns 200, keeps being invoked and moves no error
metric, so the firing of the kill switch is otherwise invisible from outside.
"""

from __future__ import annotations

import pytest

from app.backend.paper_trading import deadman, shadow_handler, venue_handler
from app.backend.paper_trading.portfolio import PaperPortfolio
from test_execution_safety import BotStub, VenueStub


class Recorder:
    """A requests-like object that records what it was asked to fetch."""

    def __init__(self, explode=False):
        self.calls = []
        self.explode = explode

    def get(self, url, timeout=None):
        self.calls.append((url, timeout))
        if self.explode:
            raise ConnectionError("the monitoring service is down")
        return object()


# ------------------------------------------------------------------ the ping --
def test_no_url_means_the_feature_is_simply_off():
    rec = Recorder()
    assert deadman.ping("", session=rec) is False
    assert deadman.ping(None, session=rec) is False
    assert rec.calls == []


def test_a_healthy_run_pings_the_plain_url():
    rec = Recorder()
    assert deadman.ping("https://hc.example/abc", session=rec) is True
    assert rec.calls[0][0] == "https://hc.example/abc"


def test_a_halt_pings_the_failure_endpoint():
    """The kill switch firing is invisible from outside AWS unless it is said."""
    rec = Recorder()
    deadman.ping("https://hc.example/abc", failed=True, session=rec)
    assert rec.calls[0][0] == "https://hc.example/abc/fail"


def test_a_trailing_slash_does_not_produce_a_double_slash():
    rec = Recorder()
    deadman.ping("https://hc.example/abc/", failed=True, session=rec)
    assert rec.calls[0][0] == "https://hc.example/abc/fail"


def test_a_dead_monitoring_service_cannot_break_the_bot():
    """The whole point: this call is not allowed to propagate anything."""
    rec = Recorder(explode=True)
    assert deadman.ping("https://hc.example/abc", session=rec) is False


def test_the_ping_is_bounded_in_time():
    """An unbounded request inside a run that holds a position is not monitoring."""
    rec = Recorder()
    deadman.ping("https://hc.example/abc", session=rec)
    assert rec.calls[0][1] == deadman.PING_TIMEOUT


# ------------------------------------------------------- optional SSM lookup --
class FakeSSM:
    def __init__(self, available):
        self.available = available
        self.asked = None

    def get_parameters(self, Names=None, WithDecryption=None):
        self.asked = list(Names)
        return {"Parameters": [{"Name": n, "Value": self.available[n]}
                               for n in Names if n in self.available],
                "InvalidParameters": [n for n in Names if n not in self.available]}


@pytest.fixture
def patched_boto(monkeypatch):
    holder = {}

    class FakeBoto3:
        @staticmethod
        def client(_name):
            return holder["ssm"]

    import sys
    monkeypatch.setitem(sys.modules, "boto3", FakeBoto3)
    return holder


def test_credentials_load_without_any_healthcheck_configured(patched_boto):
    patched_boto["ssm"] = FakeSSM({"/p/key": "k", "/p/secret": "s"})
    out = shadow_handler.load_credentials_from_ssm("/p")

    assert out["BINANCE_API_KEY"] == "k"
    assert "HEALTHCHECK_URL" not in out


def test_a_missing_healthcheck_parameter_is_not_an_error(patched_boto):
    """Configuration that does not exist must not stop the bot from trading."""
    ssm = FakeSSM({"/p/key": "k", "/p/secret": "s"})
    patched_boto["ssm"] = ssm
    out = shadow_handler.load_credentials_from_ssm("/p", "/hc/venue")

    assert out["BINANCE_API_KEY"] == "k"
    assert "HEALTHCHECK_URL" not in out
    assert "/hc/venue" in ssm.asked          # asked for, in the same call


def test_the_healthcheck_url_is_read_in_the_same_call(patched_boto):
    ssm = FakeSSM({"/p/key": "k", "/p/secret": "s", "/hc/venue": "https://hc/x"})
    patched_boto["ssm"] = ssm
    out = shadow_handler.load_credentials_from_ssm("/p", "/hc/venue")

    assert out["HEALTHCHECK_URL"] == "https://hc/x"
    assert len(ssm.asked) == 3               # one request, not two


def test_missing_credentials_still_raise(patched_boto):
    patched_boto["ssm"] = FakeSSM({"/p/key": "k"})
    with pytest.raises(RuntimeError, match="secret"):
        shadow_handler.load_credentials_from_ssm("/p")


# ------------------------------------------------------------- in the handler --
def _run(monkeypatch, bot, venue, pings):
    monkeypatch.setenv("TRADING_TIMEFRAME", "4h")
    monkeypatch.setenv("PAPER_CAPITAL", "200")
    monkeypatch.setattr(venue_handler, "load_credentials_from_ssm",
                        lambda prefix, hc="": {"BINANCE_API_KEY": "k",
                                               "BINANCE_API_SECRET": "s",
                                               "HEALTHCHECK_URL": "https://hc/x"})
    monkeypatch.setattr(venue_handler, "BinanceDemoExecutor", lambda **kw: venue)
    monkeypatch.setattr(venue_handler, "build_bot", lambda **kw: bot)
    monkeypatch.setattr(venue_handler.deadman, "ping",
                        lambda url, failed=False, **kw: pings.append((url, failed)))
    return venue_handler.handler({}, None)


def test_a_completed_run_reports_itself_alive(monkeypatch):
    pings = []
    bot = BotStub(PaperPortfolio(initial_capital=200.0), last_bar="bar-1",
                  extra={"venue": {"last_order_id": 100}})
    bot.step = lambda: {"status": "held", "bar": "bar-1"}
    _run(monkeypatch, bot, VenueStub(), pings)

    assert pings == [("https://hc/x", False)]


def test_a_halt_reports_a_failure_not_a_heartbeat(monkeypatch):
    """Get this backwards and a halted bot looks healthy to the outside world."""
    pings = []
    book = PaperPortfolio(initial_capital=200.0)
    bot = BotStub(book, last_bar="bar-1", extra={
        "venue": {"last_order_id": 100},
        "killswitch": {"start_equity": 1000.0, "peak_equity": 1000.0},
    })
    bot.step = lambda: pytest.fail("a halted channel must not step")
    result = _run(monkeypatch, bot, VenueStub(), pings)

    assert result["status"] == "HALTED"
    assert pings == [("https://hc/x", True)]


def test_a_run_that_never_finished_reports_nothing(monkeypatch):
    """Silence is the signal. A run that dies must NOT have pinged on the way in."""
    pings = []
    book = PaperPortfolio(initial_capital=200.0)
    bot = BotStub(book, last_bar="bar-1", extra={"venue": {"last_order_id": 100}})

    def explode():
        raise RuntimeError("feed is down")

    bot.step = explode
    with pytest.raises(RuntimeError):
        _run(monkeypatch, bot, VenueStub(), pings)

    assert pings == []
