"""Tests for the Binance Demo Trading executor.

Every exchange-facing rule this module implements is a rule that, if got wrong,
costs money at a venue rather than failing a unit test — so each one is pinned
here against a fake transport. No network: CI must be deterministic, and a test
suite that needs live credentials is a test suite that gets skipped.

The load-bearing cases are the ones where the exchange's arithmetic differs from
naive Python: quantity flooring in Decimal (a float quantity is rejected as
``-1013``), commission charged in the base asset (buy 1 BTC, own 0.999), and a
market order that walks the book and comes back as several fills at several
prices.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal
from urllib.parse import parse_qsl, urlparse

import pytest

from app.backend.paper_trading.binance_demo import (
    DEMO_BASE_URL,
    BinanceAPIError,
    BinanceDemoExecutor,
    OrderTooSmall,
    Reconciliation,
    SymbolNotTradable,
)
from app.backend.paper_trading.execution import BUY, SELL, Order
from app.backend.paper_trading.portfolio import PaperPortfolio

KEY = "test-key"
SECRET = "test-secret"

EXCHANGE_INFO = {
    "symbols": [{
        "symbol": "BTCUSDT",
        "baseAsset": "BTC",
        "quoteAsset": "USDT",
        "status": "TRADING",
        "filters": [
            {"filterType": "PRICE_FILTER", "minPrice": "0.01", "tickSize": "0.01"},
            {"filterType": "LOT_SIZE", "minQty": "0.00001", "maxQty": "9000",
             "stepSize": "0.00001"},
            {"filterType": "NOTIONAL", "minNotional": "5.00000000",
             "applyMinToMarket": True},
        ],
    }]
}

ACCOUNT = {
    "canTrade": True,
    "accountType": "SPOT",
    "balances": [
        {"asset": "BTC", "free": "0.05000000", "locked": "0.00000000"},
        {"asset": "USDT", "free": "5000.00000000", "locked": "0.00000000"},
        {"asset": "ETH", "free": "0.00000000", "locked": "0.00000000"},
    ],
}


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.text = json.dumps(payload) if not isinstance(payload, str) else payload

    def json(self):
        if isinstance(self._payload, str):
            raise ValueError("not json")
        return self._payload


class FakeSession:
    """Records every request and answers from a queue keyed by path."""

    def __init__(self, responses: dict[str, list]):
        self.responses = {k: list(v) for k, v in responses.items()}
        self.requests: list[tuple[str, str, dict]] = []

    def request(self, method, url, headers=None, timeout=None):
        parsed = urlparse(url)
        params = dict(parse_qsl(parsed.query))
        self.requests.append((method, parsed.path, params))
        self.requests[-1][2]["__headers__"] = headers or {}
        queue = self.responses.get(parsed.path)
        if not queue:
            raise AssertionError(f"unexpected request to {parsed.path}")
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        return item if isinstance(item, FakeResponse) else FakeResponse(item)


def order_response(fills, status="FILLED", order_id=12345):
    executed = sum(Decimal(f["qty"]) for f in fills)
    quote = sum(Decimal(f["price"]) * Decimal(f["qty"]) for f in fills)
    return {
        "symbol": "BTCUSDT", "orderId": order_id, "status": status,
        "executedQty": str(executed), "cummulativeQuoteQty": str(quote),
        "fills": fills,
    }


def make_executor(responses=None, **kwargs):
    responses = responses or {}
    responses.setdefault("/api/v3/exchangeInfo", [EXCHANGE_INFO])
    responses.setdefault("/api/v3/account", [ACCOUNT])
    responses.setdefault("/api/v3/time", [{"serverTime": 1_786_045_000_000}])
    session = FakeSession(responses)
    kwargs.setdefault("sleep", lambda _s: None)
    ex = BinanceDemoExecutor(KEY, SECRET, session=session, **kwargs)
    return ex, session


# ------------------------------------------------------------------- signing --
def test_signature_covers_the_exact_query_that_is_sent():
    """The HMAC must match the bytes on the wire, not a re-encoding of them."""
    ex, session = make_executor()
    ex.balances()
    _method, path, params = session.requests[-1]
    assert path == "/api/v3/account"

    signature = params.pop("signature")
    params.pop("__headers__")
    # Rebuild in the order the executor sent them; parse_qsl preserves it.
    query = "&".join(f"{k}={v}" for k, v in params.items())
    expected = hmac.new(SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    assert signature == expected


def test_signed_requests_carry_the_api_key_header():
    ex, session = make_executor()
    ex.balances()
    assert session.requests[-1][2]["__headers__"]["X-MBX-APIKEY"] == KEY


def test_public_requests_are_not_signed():
    ex, session = make_executor()
    ex.rules()
    _method, path, params = session.requests[-1]
    assert path == "/api/v3/exchangeInfo"
    assert "signature" not in params and "X-MBX-APIKEY" not in params["__headers__"]


def test_recv_window_is_sent_on_signed_requests():
    ex, session = make_executor(recv_window=8000)
    ex.balances()
    assert session.requests[-1][2]["recvWindow"] == "8000"


@pytest.mark.parametrize("bad", [0, -1, 60_001])
def test_absurd_recv_window_is_refused(bad):
    with pytest.raises(ValueError, match="recv_window"):
        BinanceDemoExecutor(KEY, SECRET, recv_window=bad)


def test_missing_credentials_are_refused():
    with pytest.raises(ValueError, match="required"):
        BinanceDemoExecutor("", SECRET)


def test_from_env_reads_credentials_and_refuses_when_absent():
    ex = BinanceDemoExecutor.from_env({"BINANCE_DEMO_KEY": "k", "BINANCE_DEMO_SECRET": "s"})
    assert ex.api_key == "k"
    with pytest.raises(ValueError, match="BINANCE_DEMO_KEY"):
        BinanceDemoExecutor.from_env({})


# --------------------------------------------------------------- clock skew --
def test_clock_offset_is_measured_and_applied():
    ex, session = make_executor()
    ex._time_offset_ms = 0
    ex.sync_time()
    assert ex._time_offset_ms != 0          # our clock is not the exchange's
    ex.balances()
    sent = int(session.requests[-1][2]["timestamp"])
    assert abs(sent - 1_786_045_000_000) < 60_000


def test_timestamp_rejection_resyncs_and_retries_once():
    """-1021 is a clock problem, not a credentials problem: fix it and proceed."""
    ex, session = make_executor(responses={
        "/api/v3/account": [
            FakeResponse({"code": -1021, "msg": "Timestamp for this request is "
                                                "outside of the recvWindow."}, 400),
            ACCOUNT,
        ],
        "/api/v3/time": [{"serverTime": 1_786_045_000_000}],
    })
    balances = ex.balances()
    assert balances["USDT"] == Decimal("5000")
    paths = [p for _m, p, _q in session.requests]
    assert paths.count("/api/v3/time") == 1     # resynced exactly once
    assert paths.count("/api/v3/account") == 2  # then retried


def test_repeated_skew_is_eventually_reported_not_looped():
    ex, _session = make_executor(responses={
        "/api/v3/account": [FakeResponse({"code": -1021, "msg": "skew"}, 400)],
        "/api/v3/time": [{"serverTime": 1_786_045_000_000}],
    })
    with pytest.raises(BinanceAPIError) as err:
        ex.balances()
    assert err.value.code == -1021


# -------------------------------------------------------------- rate limits --
def test_rate_limit_honours_retry_after_then_succeeds():
    slept = []
    ex, session = make_executor(
        responses={"/api/v3/account": [
            FakeResponse({"code": -1003, "msg": "Too many requests"}, 429,
                         {"Retry-After": "3"}),
            ACCOUNT,
        ]},
        sleep=slept.append,
    )
    assert ex.balances()["USDT"] == Decimal("5000")
    assert slept == [3.0]


def test_ip_ban_is_not_retried():
    """418 means we are already banned; hammering it makes matters worse."""
    slept = []
    ex, _session = make_executor(
        responses={"/api/v3/account": [FakeResponse({"code": -1003, "msg": "banned"}, 418)]},
        sleep=slept.append,
    )
    with pytest.raises(BinanceAPIError) as err:
        ex.balances()
    assert err.value.http_status == 418
    assert slept == []


def test_server_errors_are_retried_then_surface():
    ex, session = make_executor(responses={
        "/api/v3/account": [FakeResponse("gateway timeout", 502), ACCOUNT],
    })
    assert ex.balances()["USDT"] == Decimal("5000")
    assert [p for _m, p, _q in session.requests].count("/api/v3/account") == 2


def test_business_errors_are_raised_immediately_with_the_venue_code():
    """-2010 will not fix itself on a retry; report it with its own vocabulary."""
    ex, session = make_executor(responses={
        "/api/v3/order": [FakeResponse({"code": -2010, "msg": "Account has "
                                                             "insufficient balance"}, 400)],
    })
    with pytest.raises(BinanceAPIError) as err:
        ex.execute(Order(side=BUY, reference_price=100_000.0, time="2026-08-06T00:00:00Z"))
    assert err.value.code == -2010
    assert "insufficient" in err.value.msg
    assert [p for _m, p, _q in session.requests].count("/api/v3/order") == 1


# ------------------------------------------------------------------- filters --
def test_rules_are_parsed_from_exchange_info():
    ex, _session = make_executor()
    rules = ex.rules()
    assert rules.step_size == Decimal("0.00001")
    assert rules.min_notional == Decimal("5.00000000")
    assert rules.base_asset == "BTC" and rules.quote_asset == "USDT"
    assert rules.tradable


def test_rules_are_cached_after_the_first_read():
    ex, session = make_executor()
    ex.rules(); ex.rules(); ex.rules()
    assert [p for _m, p, _q in session.requests].count("/api/v3/exchangeInfo") == 1


def test_legacy_min_notional_filter_name_is_accepted():
    """Binance renamed MIN_NOTIONAL to NOTIONAL; both must parse."""
    info = json.loads(json.dumps(EXCHANGE_INFO))
    info["symbols"][0]["filters"][2] = {"filterType": "MIN_NOTIONAL",
                                        "minNotional": "10.0", "applyToMarket": True}
    ex, _session = make_executor(responses={"/api/v3/exchangeInfo": [info]})
    assert ex.rules().min_notional == Decimal("10.0")


def test_a_halted_symbol_is_never_traded():
    info = json.loads(json.dumps(EXCHANGE_INFO))
    info["symbols"][0]["status"] = "BREAK"
    ex, _session = make_executor(responses={"/api/v3/exchangeInfo": [info]})
    with pytest.raises(SymbolNotTradable, match="BREAK"):
        ex.execute(Order(side=BUY, reference_price=100_000.0, time="t"))


def test_unknown_symbol_is_reported_clearly():
    ex, _session = make_executor(responses={"/api/v3/exchangeInfo": [{"symbols": []}]})
    with pytest.raises(SymbolNotTradable):
        ex.rules()


# ---------------------------------------------------------------- quantities --
@pytest.mark.parametrize("raw, step, expected", [
    ("0.0500049", "0.00001", "0.05000"),
    ("0.049999999", "0.00001", "0.04999"),
    ("1.0", "0.00001", "1.0"),
    ("0.000009", "0.00001", "0"),
    ("123.456789", "0.001", "123.456"),
])
def test_quantity_is_floored_to_the_lot_step(raw, step, expected):
    """Down, never nearest: rounding up can exceed the balance funding the order."""
    got = BinanceDemoExecutor._floor_to_step(Decimal(raw), Decimal(step))
    assert got == Decimal(expected)


def test_flooring_is_exact_where_binary_floats_are_not():
    """0.1 + 0.2 is not a valid BTC quantity; Decimal keeps it exact."""
    qty = BinanceDemoExecutor._floor_to_step(Decimal("0.1") + Decimal("0.2"),
                                             Decimal("0.00001"))
    assert qty == Decimal("0.30000")
    assert float(0.1 + 0.2) != 0.3          # the trap this avoids


def test_buy_size_comes_from_the_quote_balance():
    ex, _session = make_executor()
    qty = ex.plan_quantity(BUY, 100_000.0)
    # 5000 USDT / 100k = 0.05 BTC exactly, and it is a whole number of steps.
    assert qty == Decimal("0.05000")


def test_quote_fraction_scales_the_commitment():
    ex, _session = make_executor(quote_fraction=0.1)
    assert ex.plan_quantity(BUY, 100_000.0) == Decimal("0.00500")


def test_max_notional_caps_the_order():
    ex, _session = make_executor(max_notional=50.0)
    assert ex.plan_quantity(BUY, 100_000.0) == Decimal("0.00050")


@pytest.mark.parametrize("bad", [0.0, -0.5, 1.5])
def test_absurd_quote_fraction_is_refused(bad):
    with pytest.raises(ValueError, match="quote_fraction"):
        BinanceDemoExecutor(KEY, SECRET, quote_fraction=bad)


def test_order_below_min_notional_is_refused_before_it_is_sent():
    """Fail locally: the venue would answer -1013 and charge us request weight."""
    ex, session = make_executor(max_notional=4.0)      # venue floor is 5 USDT
    with pytest.raises(OrderTooSmall, match="notional"):
        ex.plan_quantity(BUY, 100_000.0)
    assert not [p for _m, p, _q in session.requests if p == "/api/v3/order"]


def test_order_below_min_qty_is_refused():
    ex, _session = make_executor(max_notional=0.5)
    with pytest.raises(OrderTooSmall, match="minQty|notional"):
        ex.plan_quantity(BUY, 100_000.0)


def test_selling_without_a_position_refuses_to_touch_pre_funded_coins():
    """The demo account is pre-funded with 0.05 BTC that this executor did not buy."""
    ex, _session = make_executor()
    with pytest.raises(OrderTooSmall, match="nothing to sell"):
        ex.plan_quantity(SELL, 100_000.0)


# --------------------------------------------------------------------- fills --
def test_market_order_walking_the_book_averages_by_quantity():
    """A market order rarely clears at one price; the fill price is the VWAP."""
    fills = [
        {"price": "100000.00", "qty": "0.02", "commission": "0", "commissionAsset": "BNB"},
        {"price": "100100.00", "qty": "0.02", "commission": "0", "commissionAsset": "BNB"},
        {"price": "100400.00", "qty": "0.01", "commission": "0", "commissionAsset": "BNB"},
    ]
    ex, _session = make_executor(responses={"/api/v3/order": [order_response(fills)]})
    fill = ex.execute(Order(side=BUY, reference_price=100_000.0, time="t"))
    # (100000*.02 + 100100*.02 + 100400*.01) / 0.05
    assert fill.price == pytest.approx(100_120.0)
    assert fill.qty == pytest.approx(0.05)
    assert fill.raw["fills"] == fills            # venue response kept for audit


def test_commission_in_the_base_asset_reduces_what_we_can_sell():
    """Buy 0.05 BTC paying 0.1% in BTC and you own 0.04995 — sell that, not 0.05."""
    fills = [{"price": "100000.00", "qty": "0.05000000",
              "commission": "0.00005000", "commissionAsset": "BTC"}]
    ex, _session = make_executor(responses={"/api/v3/order": [order_response(fills)]})
    ex.execute(Order(side=BUY, reference_price=100_000.0, time="t"))
    assert ex.position_qty == Decimal("0.04995")


def test_commission_in_bnb_leaves_the_position_whole():
    fills = [{"price": "100000.00", "qty": "0.05000000",
              "commission": "0.00075000", "commissionAsset": "BNB"}]
    ex, _session = make_executor(responses={"/api/v3/order": [order_response(fills)]})
    fill = ex.execute(Order(side=BUY, reference_price=100_000.0, time="t"))
    assert ex.position_qty == Decimal("0.05")
    assert fill.fee_asset == "BNB"
    assert fill.fee_paid == pytest.approx(0.00075)


def test_a_round_trip_returns_the_position_to_flat():
    buy = order_response([{"price": "100000.00", "qty": "0.05", "commission": "0",
                           "commissionAsset": "BNB"}])
    sell = order_response([{"price": "101000.00", "qty": "0.05", "commission": "0",
                            "commissionAsset": "BNB"}], order_id=999)
    ex, _session = make_executor(responses={"/api/v3/order": [buy, sell]})
    ex.execute(Order(side=BUY, reference_price=100_000.0, time="t1"))
    assert ex.position_qty == Decimal("0.05")
    ex.execute(Order(side=SELL, reference_price=101_000.0, time="t2"))
    assert ex.position_qty == Decimal("0")


def test_sell_sizes_itself_from_the_tracked_position():
    buy = order_response([{"price": "100000.00", "qty": "0.05000000",
                           "commission": "0.00005000", "commissionAsset": "BTC"}])
    sell = order_response([{"price": "101000.00", "qty": "0.04995", "commission": "0",
                            "commissionAsset": "BNB"}], order_id=999)
    ex, session = make_executor(responses={"/api/v3/order": [buy, sell]})
    ex.execute(Order(side=BUY, reference_price=100_000.0, time="t1"))
    ex.execute(Order(side=SELL, reference_price=101_000.0, time="t2"))
    sell_request = [q for _m, p, q in session.requests if p == "/api/v3/order"][-1]
    assert sell_request["side"] == "SELL"
    assert Decimal(sell_request["quantity"]) == Decimal("0.04995")


def test_quantity_is_sent_without_scientific_notation():
    """Decimal renders 5E-5 by default; the venue rejects that as an invalid number."""
    fills = [{"price": "100000.00", "qty": "0.00005", "commission": "0",
              "commissionAsset": "BNB"}]
    ex, session = make_executor(responses={"/api/v3/order": [order_response(fills)]},
                                max_notional=5.0)
    ex.execute(Order(side=BUY, reference_price=100_000.0, time="t"))
    sent = [q for _m, p, q in session.requests if p == "/api/v3/order"][-1]["quantity"]
    assert "E" not in sent and "e" not in sent
    assert Decimal(sent) == Decimal("0.00005")


def test_order_reporting_no_execution_is_an_error_not_a_silent_zero():
    empty = {"symbol": "BTCUSDT", "orderId": 1, "status": "EXPIRED",
             "executedQty": "0", "cummulativeQuoteQty": "0", "fills": []}
    ex, _session = make_executor(responses={"/api/v3/order": [empty]})
    with pytest.raises(BinanceAPIError, match="no executed quantity"):
        ex.execute(Order(side=BUY, reference_price=100_000.0, time="t"))


def test_average_price_falls_back_to_the_fills_when_no_aggregate_is_reported():
    response = {"symbol": "BTCUSDT", "orderId": 7, "status": "FILLED",
                "fills": [{"price": "100.0", "qty": "1", "commission": "0",
                           "commissionAsset": "BNB"},
                          {"price": "200.0", "qty": "3", "commission": "0",
                           "commissionAsset": "BNB"}]}
    price, qty, count = BinanceDemoExecutor._average_fill_price(response)
    assert price == pytest.approx(175.0)      # (100*1 + 200*3) / 4
    assert qty == pytest.approx(4.0)
    assert count == 2


# ----------------------------------------------------------- reconciliation --
def test_reconciliation_measures_actual_slippage_against_the_assumed_constant():
    """The number the paper bot has assumed since day one, finally measured."""
    fills = [{"price": "100050.00", "qty": "0.05", "commission": "0",
              "commissionAsset": "BNB"}]
    ex, _session = make_executor(responses={"/api/v3/order": [order_response(fills)]},
                                 assumed_slippage=0.0002)
    ex.execute(Order(side=BUY, reference_price=100_000.0, time="t"))

    rec = ex.reconciliations()[-1]
    assert isinstance(rec, Reconciliation)
    assert rec.assumed_price == pytest.approx(100_020.0)   # 100k * 1.0002
    assert rec.actual_price == pytest.approx(100_050.0)
    assert rec.slippage_actual == pytest.approx(0.0005)    # 5 bps, worse than assumed
    assert rec.price_error == pytest.approx(30.0)          # paid 30 USDT more


def test_reconciliation_signs_a_sell_the_same_way_the_cost_model_does():
    """Adverse means adverse on both sides: a sell receiving less is positive."""
    buy = order_response([{"price": "100000.00", "qty": "0.05", "commission": "0",
                           "commissionAsset": "BNB"}])
    sell = order_response([{"price": "99950.00", "qty": "0.05", "commission": "0",
                            "commissionAsset": "BNB"}], order_id=2)
    ex, _session = make_executor(responses={"/api/v3/order": [buy, sell]})
    ex.execute(Order(side=BUY, reference_price=100_000.0, time="t1"))
    ex.execute(Order(side=SELL, reference_price=100_000.0, time="t2"))

    rec = ex.reconciliations()[-1]
    assert rec.slippage_actual == pytest.approx(0.0005)    # received less => adverse
    assert rec.price_error == pytest.approx(30.0)


def test_a_fill_exactly_on_the_model_reconciles_to_zero_error():
    fills = [{"price": "100020.00", "qty": "0.05", "commission": "0",
              "commissionAsset": "BNB"}]
    ex, _session = make_executor(responses={"/api/v3/order": [order_response(fills)]},
                                 assumed_slippage=0.0002)
    ex.execute(Order(side=BUY, reference_price=100_000.0, time="t"))
    assert ex.reconciliations()[-1].price_error == pytest.approx(0.0)


# ------------------------------------------------------------------- the seam --
def test_it_satisfies_the_executor_protocol_the_portfolio_expects():
    """The whole point of PR #24: the book cannot tell which executor it has."""
    fills = [{"price": "100050.00", "qty": "0.05", "commission": "0",
              "commissionAsset": "BNB"}]
    ex, _session = make_executor(responses={"/api/v3/order": [order_response(fills)]})

    book = PaperPortfolio(fee_rate=0.001, slippage=0.0002, initial_capital=10_000.0)
    book.set_executor(ex)
    action = book.reconcile(target_side=1, price=100_000.0, time="2026-08-06T00:00:00Z")

    assert action["to"] == 1
    # The book booked the VENUE's price, not the modelled one.
    assert book.entry_fill == pytest.approx(100_050.0)
    assert book.entry_fill != pytest.approx(100_020.0)


def test_the_executor_stays_out_of_the_serialised_book():
    """``to_dict`` goes to DynamoDB through asdict; an executor there would break it."""
    ex, _session = make_executor()
    book = PaperPortfolio()
    book.set_executor(ex)
    assert "_executor" not in book.to_dict()
    json.dumps(book.to_dict())      # must stay serialisable


def test_an_order_for_another_market_is_refused():
    ex, _session = make_executor()
    with pytest.raises(ValueError, match="ETHUSDT"):
        ex.execute(Order(side=BUY, reference_price=3_000.0, time="t", symbol="ETHUSDT"))


def test_the_default_base_url_is_demo_trading_not_the_spot_testnet():
    """These are different venues with different keys — see the module docstring."""
    assert DEMO_BASE_URL == "https://demo-api.binance.com"
    assert "testnet.binance.vision" not in DEMO_BASE_URL


def test_mark_price_reads_the_market_the_orders_will_hit():
    """Reconciling against the wrong venue's price invents slippage that isn't there."""
    ex, session = make_executor(responses={
        "/api/v3/ticker/price": [{"symbol": "BTCUSDT", "price": "64431.72"}],
    })
    assert ex.mark_price() == pytest.approx(64_431.72)
    _method, path, params = session.requests[-1]
    assert path == "/api/v3/ticker/price"
    assert "signature" not in params          # public endpoint, nothing to sign


def test_fee_charged_in_bnb_is_reported_as_such_not_as_quote_currency():
    """Measured live 2026-08-06: the demo account holds BNB, so Binance bills it
    there rather than in USDT. The book models the fee as a fraction of equity in
    quote terms, so the two are NOT the same currency — quantity-aware accounting
    (step 4) has to resolve this, and until then it must at least be visible."""
    fills = [{"price": "64454.71", "qty": "0.00009",
              "commission": "0.00000736", "commissionAsset": "BNB"}]
    ex, _session = make_executor(responses={"/api/v3/order": [order_response(fills)]})
    fill = ex.execute(Order(side=BUY, reference_price=64_454.71, time="t"))
    assert fill.fee_asset == "BNB"
    assert ex.reconciliations()[-1].fee_asset == "BNB"
    # The position is whole: a BNB-billed commission takes nothing off the BTC.
    assert ex.position_qty == Decimal("0.00009")


def test_commission_split_across_assets_is_reported_without_losing_either():
    fills = [
        {"price": "64000", "qty": "0.001", "commission": "0.000001", "commissionAsset": "BTC"},
        {"price": "64100", "qty": "0.001", "commission": "0.00005", "commissionAsset": "BNB"},
    ]
    ex, _session = make_executor(responses={"/api/v3/order": [order_response(fills)]})
    fill = ex.execute(Order(side=BUY, reference_price=64_000.0, time="t"))
    assert fill.fee_asset == "BNB/BTC"                      # both, sorted
    assert ex.position_qty == Decimal("0.002") - Decimal("0.000001")   # only BTC nets off


# ------------------------------------------------- drift vs true slippage --
def test_slippage_splits_into_drift_and_execution_when_measured():
    """Two different costs, and only one of them is what `slippage` models.

    The strategy decides on a bar CLOSE; the order reaches the venue minutes
    later. Measured live 2026-08-06: the same reference produced 0.0189% on one
    order and 0.0437% on another — not because execution changed, but because
    the market moved in between. Gate C's threshold is written for the execution
    part, so the two must be separable.
    """
    fills = [{"price": "64474.17", "qty": "0.0031", "commission": "0",
              "commissionAsset": "BNB"}]
    ex, _session = make_executor(
        responses={"/api/v3/order": [order_response(fills)],
                   "/api/v3/ticker/price": [{"symbol": "BTCUSDT", "price": "64470.00"}]},
        measure_drift=True,
    )
    ex.execute(Order(side=BUY, reference_price=64_446.0, time="t"))
    rec = ex.reconciliations()[-1]

    assert rec.mark_at_order == pytest.approx(64_470.0)
    # Total is what a naive reading reports...
    assert rec.slippage_actual == pytest.approx((64_474.17 / 64_446.0) - 1.0)
    # ...and it decomposes into market drift plus the cost of crossing the book.
    assert rec.drift == pytest.approx((64_470.0 / 64_446.0) - 1.0)
    assert rec.execution_slippage == pytest.approx((64_474.17 / 64_470.0) - 1.0)
    assert rec.drift + rec.execution_slippage == pytest.approx(rec.slippage_actual,
                                                               rel=1e-3)
    # The part Gate C cares about is far smaller than the conflated figure.
    assert rec.execution_slippage < rec.slippage_actual


def test_drift_is_signed_adversely_for_a_sell():
    fills = [{"price": "64400.00", "qty": "0.0031", "commission": "0",
              "commissionAsset": "BNB"}]
    ex, _session = make_executor(
        responses={"/api/v3/order": [order_response(fills)],
                   "/api/v3/ticker/price": [{"symbol": "BTCUSDT", "price": "64420.00"}]},
        measure_drift=True,
    )
    ex.set_position(Decimal("0.0031"))
    ex.execute(Order(side=SELL, reference_price=64_446.0, time="t"))
    rec = ex.reconciliations()[-1]
    # Selling into a market that fell since the decision is adverse => positive.
    assert rec.drift > 0
    assert rec.execution_slippage > 0


def test_drift_is_not_measured_unless_asked():
    """One extra public request per order — nobody pays for it by accident."""
    fills = [{"price": "64474.17", "qty": "0.0031", "commission": "0",
              "commissionAsset": "BNB"}]
    ex, session = make_executor(responses={"/api/v3/order": [order_response(fills)]})
    ex.execute(Order(side=BUY, reference_price=64_446.0, time="t"))
    rec = ex.reconciliations()[-1]

    assert rec.mark_at_order is None
    assert rec.drift is None and rec.execution_slippage is None
    assert not [p for _m, p, _q in session.requests if p == "/api/v3/ticker/price"]
