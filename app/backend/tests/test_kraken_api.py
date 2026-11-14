"""Kraken REST transport (kraken_api.py): signature, nonce, retry discipline.

The rule these tests pin hardest: a read may be repeated, a write is sent once
and an unclear answer becomes ``KrakenOutcomeUnknown`` — never a second order.
"""

from decimal import Decimal

import pytest
import requests

from app.backend.paper_trading.kraken_api import (
    KrakenAPIError, KrakenClient, KrakenOutcomeUnknown, PairRules, sign,
)

# Published example from Kraken's REST authentication guide.
DOC_SECRET = ("kQH5HW/8p1uGOVjbgWA7FunAmGO8lsSUXNsu3eow76sz84Q18fWxnyRzBHCd3pd5"
              "nE9qa99HAZtuZuj6F1huXg==")
DOC_NONCE = "1616492376594"
DOC_POSTDATA = ("nonce=1616492376594&ordertype=limit&pair=XBTUSD&price=37500"
                "&type=buy&volume=1.25")
DOC_SIGNATURE = ("4/dpxb3iT4tp/ZCVEwSnEsLxx0bqyhLpdfOpc6fn7OR8+UClSV5n9E6aSS8MPtnR"
                 "fp32bAb0nmbRn6H8ndwLUQ==")


class FakeResponse:
    def __init__(self, body=None, status=200, raises_json=False):
        self._body, self.status_code, self._raises = body, status, raises_json

    def json(self):
        if self._raises:
            raise ValueError("not json")
        return self._body


class FakeSession:
    """Plays back a script of responses / exceptions and records the calls."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def ok(result):
    return FakeResponse({"error": [], "result": result})


def err(*errors):
    return FakeResponse({"error": list(errors)})


def client(script, **kwargs):
    session = FakeSession(script)
    kwargs.setdefault("sleep", lambda _s: None)
    return KrakenClient("key", DOC_SECRET, session=session, **kwargs), session


def test_signature_matches_krakens_published_example():
    assert sign("/0/private/AddOrder", DOC_NONCE, DOC_POSTDATA, DOC_SECRET) == DOC_SIGNATURE


def test_signed_request_carries_key_signature_and_nonce_first():
    c, s = client([ok({"ZGBP": "20.0000"})], clock=lambda: 1616492376.594)
    assert c.balance() == {"ZGBP": Decimal("20.0000")}
    method, url, kw = s.calls[0]
    assert (method, url) == ("POST", "https://api.kraken.com/0/private/Balance")
    assert kw["data"] == "nonce=1616492376594"
    assert kw["headers"]["API-Key"] == "key"
    assert kw["headers"]["API-Sign"] == sign("/0/private/Balance", "1616492376594",
                                             kw["data"], DOC_SECRET)


def test_nonce_strictly_increases_even_when_the_clock_does_not():
    c, s = client([ok({}), ok({}), ok({})], clock=lambda: 1000.0)
    for _ in range(3):
        c.balance()
    nonces = [int(kw["data"].split("=")[1]) for _, _, kw in s.calls]
    assert nonces == [1_000_000, 1_000_001, 1_000_002]


def test_private_call_without_credentials_is_refused_locally():
    c = KrakenClient(session=FakeSession([]))
    with pytest.raises(RuntimeError, match="without credentials"):
        c.balance()


def test_read_is_retried_on_transport_trouble_then_succeeds():
    c, s = client([requests.Timeout(), FakeResponse(status=502), ok({"status": "online"})])
    assert c.system_status() == "online"
    assert len(s.calls) == 3


def test_read_gives_up_after_the_bounded_number_of_attempts():
    c, s = client([requests.Timeout()] * 3)
    with pytest.raises(requests.Timeout):
        c.system_status()
    assert len(s.calls) == 3


def test_read_does_not_retry_a_real_refusal():
    c, s = client([err("EGeneral:Permission denied")])
    with pytest.raises(KrakenAPIError) as exc:
        c.balance()
    assert exc.value.has("EGeneral:Permission denied")
    assert len(s.calls) == 1


def test_read_retries_an_invalid_nonce_with_a_fresh_one():
    c, s = client([err("EAPI:Invalid nonce"), ok({})], clock=lambda: 5.0)
    c.balance()
    first, second = (kw["data"] for _, _, kw in s.calls)
    assert first != second


@pytest.mark.parametrize("failure", [
    requests.Timeout(), requests.ConnectionError(), FakeResponse(status=520),
    FakeResponse(raises_json=True), err("EService:Unavailable"), err("EService:Busy"),
    FakeResponse({"unexpected": 1}),
])
def test_write_is_sent_once_and_an_unclear_answer_is_outcome_unknown(failure):
    c, s = client([failure, ok({"txid": ["SHOULD-NOT-BE-REACHED"]})])
    with pytest.raises(KrakenOutcomeUnknown):
        c.private_write("AddOrder", {"pair": "XBTGBP"})
    assert len(s.calls) == 1, "a write must never be resent blind"


def test_write_refused_cleanly_is_an_api_error_not_unknown():
    c, s = client([err("EOrder:Insufficient funds")])
    with pytest.raises(KrakenAPIError) as exc:
        c.private_write("AddOrder", {"pair": "XBTGBP"})
    assert exc.value.has("EOrder:Insufficient funds")
    assert len(s.calls) == 1


def test_write_returns_the_result_on_success():
    c, _ = client([ok({"txid": ["OABC-1"]})])
    assert c.private_write("AddOrder", {"pair": "XBTGBP"}) == {"txid": ["OABC-1"]}


ASSET_PAIRS = {"XXBTZGBP": {
    "altname": "XBTGBP", "base": "XXBT", "quote": "ZGBP", "lot_decimals": 8,
    "ordermin": "0.00006", "costmin": "0.43", "tick_size": "0.1", "status": "online"}}


def test_pair_rules_parse_the_live_shape():
    c, _ = client([ok(ASSET_PAIRS)])
    r = c.pair_rules("XBTGBP")
    assert r == PairRules(key="XXBTZGBP", altname="XBTGBP", base="XXBT", quote="ZGBP",
                          ordermin=Decimal("0.00006"), costmin=Decimal("0.43"),
                          tick_size=Decimal("0.1"), lot_decimals=8, status="online")
    assert r.tradable


def test_pair_rules_refuse_an_ambiguous_answer():
    c, _ = client([ok({**ASSET_PAIRS, "XETHZGBP": ASSET_PAIRS["XXBTZGBP"]})])
    with pytest.raises(RuntimeError, match="expected one pair"):
        c.pair_rules("XBTGBP")


def test_volume_is_floored_never_rounded_up():
    r = PairRules("XXBTZGBP", "XBTGBP", "XXBT", "ZGBP", Decimal("0.00006"),
                  Decimal("0.43"), Decimal("0.1"), 8, "online")
    assert r.floor_volume(Decimal("0.000100009999")) == Decimal("0.00010000")
    assert r.floor_price(Decimal("49744.79")) == Decimal("49744.7")


def test_minimums_block_an_order_that_is_too_small():
    r = PairRules("XXBTZGBP", "XBTGBP", "XXBT", "ZGBP", Decimal("0.00006"),
                  Decimal("0.43"), Decimal("0.1"), 8, "online")
    assert r.allows(Decimal("0.0001"), Decimal("50000"))
    assert not r.allows(Decimal("0.00005"), Decimal("50000"))      # below ordermin
    assert not r.allows(Decimal("0.00006"), Decimal("5000"))       # below costmin


def test_best_bid_ask():
    c, _ = client([ok({"XXBTZGBP": {"a": ["49744.7", "1", "1"], "b": ["49740.2", "1", "1"]}})])
    assert c.best_bid_ask("XBTGBP") == (Decimal("49740.2"), Decimal("49744.7"))
