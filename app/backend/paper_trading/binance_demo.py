"""A real :class:`~.execution.Executor` backed by Binance Demo Trading.

This is the other half of the seam opened in ``execution.py``. ``SimulatedExecutor``
answers "what would a fill look like?" from a slippage model; this module submits
an actual signed order to an actual matching engine and reports what came back.
Everything the exchange makes us care about — request signing, clock skew, lot
sizes, minimum notionals, fills arriving in pieces at different prices, typed
errors, rate limits — lives here, so that the day the base URL is swapped for the
live one, none of it is being written for the first time.

Which venue is this
-------------------
Binance runs *two* unrelated practice environments, and they do not share keys:

* the classic Spot Testnet at ``testnet.binance.vision`` (separate GitHub signup)
* **Demo Trading** at ``demo.binance.com``, whose API is ``demo-api.binance.com``

Keys minted in the Demo Trading UI authenticate only against the latter — the
testnet host answers a signed request with ``-2015 Invalid API-key``. This module
targets Demo Trading; :data:`DEMO_BASE_URL` is the only thing that needs to change
to point it elsewhere.

Sizing, and what is deliberately NOT solved here
------------------------------------------------
``PaperPortfolio`` sizes positions as a *fraction of equity* and has no concept of
quantity; an exchange deals only in quantities. Rather than rewrite the book — a
change that would have to be re-frozen against the golden master and re-verified
through gate A — this executor derives a quantity at the boundary: a BUY spends a
configured share of the quote balance, and a SELL returns exactly the base asset
that this executor's own BUYs acquired. It never touches coins it did not buy,
which matters because the demo account is pre-funded with BTC that is not ours.

The consequence is honest and worth stating: the book stays fractional and the
exchange stays quantitative, with this class translating between them. Making the
book itself quantity-aware is separate work, and it is what M6 will actually need.

What this class is for
----------------------
Validating the execution path, and measuring the one number the paper bot has so
far only assumed: slippage. Every fill is reconciled against what the book would
have booked (``reference * (1 + side * slippage)``), and the difference is
recorded on the :class:`Fill` and surfaced by :meth:`reconciliations`.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import time as _time
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from .execution import BUY, SELL, Fill, Order, slipped_price

logger = logging.getLogger(__name__)

#: Binance Demo Trading REST API. NOT ``testnet.binance.vision`` — see module docstring.
DEMO_BASE_URL = "https://demo-api.binance.com"

#: Binance error codes we handle rather than merely report.
_ERR_TIMESTAMP_OUTSIDE_RECV_WINDOW = -1021
_ERR_INVALID_TIMESTAMP = -1022
#: "Order does not exist" — the venue is stating it never accepted the order.
#: The one answer that makes resending safe rather than reckless.
_ERR_ORDER_DOES_NOT_EXIST = -2013

#: HTTP statuses that mean "slow down" (429) or "you have been IP-banned" (418).
_RATE_LIMITED = (429, 418)

#: A client order id must fit ``^[\.A-Za-z0-9_-]{1,36}$``; the prefix is the part
#: we choose per channel, so it is kept plainly alphanumeric and short.
_CLIENT_PREFIX_RE = re.compile(r"^[A-Za-z0-9]{1,12}$")


class BinanceAPIError(RuntimeError):
    """An error the exchange reported, carrying its own vocabulary.

    Binance answers failures with a numeric ``code`` that is far more actionable
    than the HTTP status — ``-2010`` (insufficient balance) and ``-1013`` (filter
    failure) both arrive as HTTP 400. Callers that need to branch should branch on
    :attr:`code`.
    """

    def __init__(self, code: int, msg: str, http_status: Optional[int] = None,
                 endpoint: str = "") -> None:
        self.code = code
        self.msg = msg
        self.http_status = http_status
        self.endpoint = endpoint
        super().__init__(f"[{code}] {msg} (HTTP {http_status}, {endpoint})")


class SymbolNotTradable(RuntimeError):
    """The symbol exists but the venue will not accept orders for it right now."""


class OrderTooSmall(ValueError):
    """The order fails the venue's minimum quantity or minimum notional filter.

    Raised *before* anything is sent. The exchange would reject it as ``-1013``
    anyway; failing locally keeps the reason legible and costs no rate limit.
    """


class OrderSubmissionUncertain(RuntimeError):
    """A submit failed without saying whether the order landed.

    A timeout or a 5xx is not "the order was rejected": the request may have
    reached the matching engine and only the answer got lost. Resending on that
    evidence is how a bot ends up holding twice the position it decided on —
    the single most common way small live bots lose money (audit 2026-09-04,
    CRITICAL-1). Raised only after the venue has been *asked*, by
    ``origClientOrderId``, and still could not settle the question.
    """


@dataclass(frozen=True)
class SymbolRules:
    """The subset of ``exchangeInfo`` filters that constrain an order.

    Fetched once per symbol and cached: these change rarely, and re-reading them
    on every order would spend request weight for nothing.
    """

    symbol: str
    base_asset: str
    quote_asset: str
    status: str
    step_size: Decimal        # LOT_SIZE — quantity must be a multiple of this
    min_qty: Decimal
    max_qty: Decimal
    tick_size: Decimal        # PRICE_FILTER — price granularity
    min_notional: Decimal     # NOTIONAL — price * qty floor
    min_notional_applies_to_market: bool

    @property
    def tradable(self) -> bool:
        return self.status == "TRADING"


@dataclass(frozen=True)
class Reconciliation:
    """What the book assumed versus what the venue actually did.

    ``slippage_actual`` is signed the same way the cost model signs it: positive
    means adverse (a buy paid more than reference, a sell received less), so it is
    directly comparable to the ``slippage`` constant the paper bot has been
    assuming since day one.
    """

    time: str
    side: int
    reference_price: float
    assumed_price: float
    actual_price: float
    slippage_assumed: float
    slippage_actual: float
    qty: float
    fee_paid: float
    fee_asset: str
    order_id: str
    fill_count: int
    status: str
    #: Market price observed immediately before submitting, when measured.
    #: Without it, ``slippage_actual`` conflates two different costs — see below.
    mark_at_order: Optional[float] = None
    #: Quantity the order asked for, after lot-size flooring. Gate C's partial
    #: fill criterion compares this against what actually executed.
    requested_qty: Optional[float] = None
    #: The id WE gave the order. Deterministic per (symbol, side, decision), so
    #: it is also how a later run recognises a fill the book already contains.
    client_order_id: Optional[str] = None

    @property
    def price_error(self) -> float:
        """Actual minus assumed, in quote units. Positive = worse than assumed."""
        return (self.actual_price - self.assumed_price) * self.side

    @property
    def drift(self) -> Optional[float]:
        """Market movement between the decision and the order, signed adversely.

        The strategy decides on a bar's CLOSE, but the order reaches the venue
        minutes later at whatever the market is doing by then. That gap is a real
        cost of live trading and the backtest does not model it — but it is not
        slippage, and lumping the two together makes both unmeasurable.
        """
        if self.mark_at_order is None:
            return None
        return self.side * (self.mark_at_order / self.reference_price - 1.0)

    @property
    def execution_slippage(self) -> Optional[float]:
        """Cost of crossing the book, measured from the price we could see.

        THIS is the quantity ``slippage`` models in ``costs.py``, and the one
        Gate C's threshold was written for.
        """
        if self.mark_at_order is None:
            return None
        return self.side * (self.actual_price / self.mark_at_order - 1.0)

    def as_dict(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        d["price_error"] = self.price_error
        d["drift"] = self.drift
        d["execution_slippage"] = self.execution_slippage
        return d


class BinanceDemoExecutor:
    """Places real orders on Binance Demo Trading and reports real fills.

    Satisfies the :class:`~.execution.Executor` protocol, so it can be handed to
    ``PaperPortfolio.set_executor`` and the accounting above the seam does not
    change at all.

    Parameters
    ----------
    api_key, api_secret:
        Demo Trading credentials. Never hardcode these — read them from the
        environment (see :meth:`from_env`).
    symbol:
        Trading pair. Orders whose own ``symbol`` disagrees are rejected rather
        than silently routed to the wrong market.
    quote_fraction:
        Share of the free quote balance a BUY commits, mirroring the book's
        full-equity positions. ``1.0`` is the default the paper bot implies.
    max_notional:
        Hard ceiling per order, in quote units. The demo account is pre-funded
        with 5000 USDT and a full-equity BUY would commit all of it; a ceiling
        keeps a session's worth of round-trips affordable and is a habit worth
        having before this code ever sees a live venue.
    assumed_slippage:
        The book's slippage constant, used only to compute the reconciliation.
        It never influences the order.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        symbol: str = "BTCUSDT",
        base_url: str = DEMO_BASE_URL,
        quote_fraction: float = 1.0,
        max_notional: Optional[float] = None,
        assumed_slippage: float = 0.0002,
        client_prefix: str = "tp",
        measure_drift: bool = False,
        recv_window: int = 5000,
        timeout: float = 15.0,
        max_retries: int = 4,
        session: Optional[requests.Session] = None,
        sleep=_time.sleep,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret are required")
        if not 0.0 < quote_fraction <= 1.0:
            raise ValueError(f"quote_fraction must be in (0, 1], got {quote_fraction}")
        if recv_window <= 0 or recv_window > 60_000:
            raise ValueError(f"recv_window must be in (0, 60000] ms, got {recv_window}")
        if not _CLIENT_PREFIX_RE.match(client_prefix or ""):
            raise ValueError(
                f"client_prefix must be 1-12 alphanumeric characters, got {client_prefix!r}"
            )

        self.api_key = api_key
        self._api_secret = api_secret.encode()
        self.symbol = symbol.upper()
        self.base_url = base_url.rstrip("/")
        self.quote_fraction = quote_fraction
        self.max_notional = max_notional
        self.assumed_slippage = assumed_slippage
        # Namespaces this channel's orders on an account several bots share, and
        # is the first half of every client order id it ever sends. Changing it
        # would make old orders unrecognisable, so it belongs in code, not config.
        self.client_prefix = client_prefix
        # Costs one extra public request per order. Off by default so nothing
        # pays for it unnecessarily; on wherever a decision price and an order
        # are separated in time, which is every strategy-driven channel.
        self.measure_drift = measure_drift
        self.recv_window = recv_window
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = session or requests.Session()
        self._sleep = sleep

        self._time_offset_ms = 0            # exchange clock minus ours
        self._rules: Optional[SymbolRules] = None
        self._position_qty = Decimal("0")   # base asset acquired by OUR buys
        self._reconciliations: list[Reconciliation] = []
        self._rejections: list[dict[str, Any]] = []

    # ------------------------------------------------------------ construction --
    @classmethod
    def from_env(cls, env: Optional[dict] = None, **kwargs) -> "BinanceDemoExecutor":
        """Build from ``BINANCE_API_KEY`` / ``BINANCE_API_SECRET``.

        The older ``BINANCE_DEMO_*`` spelling is still accepted, but it is not
        the name to grow into: this same code path is the one that will hold
        live keys, and a variable called "DEMO" on that path invites exactly the
        wrong assumption at exactly the wrong moment (audit 2026-09-04, HIGH-3).

        Credentials belong in the environment, never in the repository: CI runs
        gitleaks, and a key committed once is a key that must be rotated.
        """
        import os

        env = os.environ if env is None else env
        key = env.get("BINANCE_API_KEY") or env.get("BINANCE_DEMO_KEY", "")
        secret = env.get("BINANCE_API_SECRET") or env.get("BINANCE_DEMO_SECRET", "")
        if not key or not secret:
            raise ValueError(
                "set BINANCE_API_KEY and BINANCE_API_SECRET "
                "(exchange → API Management); never commit them"
            )
        return cls(api_key=key, api_secret=secret, **kwargs)

    # ------------------------------------------------------------- HTTP plumbing --
    def _sign(self, params: dict[str, Any]) -> str:
        """HMAC-SHA256 over the exact query string that will be sent.

        The signature covers the *encoded* string, so it must be built from the
        same bytes the request carries — re-encoding afterwards, or letting the
        HTTP layer reorder parameters, invalidates it.
        """
        query = urlencode(params)
        signature = hmac.new(self._api_secret, query.encode(), hashlib.sha256).hexdigest()
        return f"{query}&signature={signature}"

    def _timestamp(self) -> int:
        return int(_time.time() * 1000) + self._time_offset_ms

    def sync_time(self) -> int:
        """Measure the exchange's clock against ours and keep the offset.

        A signed request carries a timestamp the venue rejects if it falls outside
        ``recvWindow``. Laptops drift, containers suspend, and the failure looks
        like a credentials problem (``-1021``) unless the offset is measured. The
        round-trip is halved out so a slow link does not read as skew.
        """
        sent = _time.time() * 1000
        payload = self._request("GET", "/api/v3/time", signed=False)
        received = _time.time() * 1000
        latency_half = (received - sent) / 2.0
        self._time_offset_ms = int(payload["serverTime"] - (sent + latency_half))
        logger.info("binance clock offset: %+d ms", self._time_offset_ms)
        return self._time_offset_ms

    def _request(self, method: str, path: str, params: Optional[dict] = None,
                 signed: bool = False, retry_transport: bool = True) -> Any:
        """One REST call, with the retries the venue's contract calls for.

        Retries cover three distinct failures, each for its own reason:
        transport errors and 5xx (the venue is briefly unwell), 429/418 (we are
        being rate limited and must honour ``Retry-After``), and ``-1021``
        (our clock drifted — resync once and try again rather than fail a trade
        over a few milliseconds). Everything else is raised immediately: an
        insufficient-balance error will not fix itself by being sent again.

        ``retry_transport=False`` withdraws the first of those, and only the
        first, for requests that are not safe to repeat blindly. A timeout or a
        5xx on ``POST /order`` does not mean the order was refused — it means
        the answer was lost — so that case is handed back to the caller, which
        asks the venue what actually happened. The unambiguous failures keep
        their retries: a rate limit and a rejected timestamp both mean the
        matching engine never saw the order.
        """
        params = dict(params or {})
        url = f"{self.base_url}{path}"
        headers = {"X-MBX-APIKEY": self.api_key} if signed else {}
        resynced = False

        for attempt in range(self.max_retries):
            if signed:
                params["timestamp"] = self._timestamp()
                params["recvWindow"] = self.recv_window
                query = self._sign(params)
            else:
                query = urlencode(params)
            full_url = f"{url}?{query}" if query else url

            try:
                resp = self._session.request(method, full_url, headers=headers,
                                             timeout=self.timeout)
            except requests.RequestException as exc:
                if not retry_transport or attempt == self.max_retries - 1:
                    raise
                delay = 2.0 ** attempt
                logger.warning("%s %s failed (%s), retrying in %.0fs", method, path, exc, delay)
                self._sleep(delay)
                continue

            if resp.status_code in _RATE_LIMITED:
                retry_after = float(resp.headers.get("Retry-After", 2.0 ** attempt))
                if resp.status_code == 418 or attempt == self.max_retries - 1:
                    raise BinanceAPIError(resp.status_code, "rate limited / IP banned",
                                          resp.status_code, path)
                logger.warning("rate limited on %s, sleeping %.0fs", path, retry_after)
                self._sleep(retry_after)
                continue

            if resp.status_code >= 500:
                if not retry_transport or attempt == self.max_retries - 1:
                    raise BinanceAPIError(resp.status_code, resp.text[:200],
                                          resp.status_code, path)
                self._sleep(2.0 ** attempt)
                continue

            try:
                payload = resp.json()
            except ValueError:
                raise BinanceAPIError(-1, f"non-JSON response: {resp.text[:200]}",
                                      resp.status_code, path)

            if isinstance(payload, dict) and "code" in payload and "msg" in payload:
                code = int(payload["code"])
                skew = code in (_ERR_TIMESTAMP_OUTSIDE_RECV_WINDOW, _ERR_INVALID_TIMESTAMP)
                if skew and not resynced:
                    logger.warning("clock skew reported (%d), resyncing", code)
                    resynced = True
                    self.sync_time()
                    continue
                raise BinanceAPIError(code, str(payload["msg"]), resp.status_code, path)

            if resp.status_code != 200:
                raise BinanceAPIError(resp.status_code, resp.text[:200],
                                      resp.status_code, path)
            return payload

        raise BinanceAPIError(-1, f"exhausted {self.max_retries} attempts", None, path)

    # ------------------------------------------------------------------- market --
    def rules(self, refresh: bool = False) -> SymbolRules:
        """Order constraints for the configured symbol, cached after first read."""
        if self._rules is not None and not refresh:
            return self._rules

        payload = self._request("GET", "/api/v3/exchangeInfo",
                                {"symbol": self.symbol}, signed=False)
        symbols = payload.get("symbols") or []
        if not symbols:
            raise SymbolNotTradable(f"{self.symbol} is unknown to {self.base_url}")
        info = symbols[0]
        filters = {f["filterType"]: f for f in info["filters"]}

        lot = filters.get("LOT_SIZE", {})
        price_filter = filters.get("PRICE_FILTER", {})
        # Binance renamed MIN_NOTIONAL to NOTIONAL; venues differ on which they serve.
        notional = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL") or {}

        self._rules = SymbolRules(
            symbol=info["symbol"],
            base_asset=info["baseAsset"],
            quote_asset=info["quoteAsset"],
            status=info["status"],
            step_size=Decimal(lot.get("stepSize", "0.00000001")),
            min_qty=Decimal(lot.get("minQty", "0")),
            max_qty=Decimal(lot.get("maxQty", "9" * 12)),
            tick_size=Decimal(price_filter.get("tickSize", "0.01")),
            min_notional=Decimal(notional.get("minNotional", "0")),
            min_notional_applies_to_market=bool(notional.get("applyMinToMarket", True)),
        )
        return self._rules

    def balances(self) -> dict[str, Decimal]:
        """Free balance per asset — only assets with something in them."""
        account = self._request("GET", "/api/v3/account", signed=True)
        return {b["asset"]: Decimal(b["free"]) for b in account["balances"]
                if Decimal(b["free"]) > 0}

    def free_balance(self, asset: str) -> Decimal:
        return self.balances().get(asset, Decimal("0"))

    def mark_price(self) -> float:
        """Last traded price — the reference a decision would be taken on.

        The bot's own feed reads klines from the *live* venue; this reads the
        price of the market the orders will actually hit. On a practice venue
        those two are not the same number, and reconciling a fill against the
        wrong reference would manufacture slippage that does not exist.
        """
        payload = self._request("GET", "/api/v3/ticker/price",
                                {"symbol": self.symbol}, signed=False)
        return float(payload["price"])

    # -------------------------------------------------------------- quantities --
    @staticmethod
    def _floor_to_step(qty: Decimal, step: Decimal) -> Decimal:
        """Round *down* to a multiple of ``step``.

        Down, never nearest: rounding up can push an order past the balance that
        funds it, and the exchange rejects the whole thing. Decimal throughout —
        ``0.1 + 0.2`` in binary floats is not a valid BTC quantity and Binance
        rejects the extra digits as ``-1013``.
        """
        if step <= 0:
            return qty
        return (qty / step).to_integral_value(rounding=ROUND_DOWN) * step

    def plan_quantity(self, side: int, reference_price: float) -> Decimal:
        """Quantity for one order, respecting every filter the venue enforces.

        A BUY derives its size from the quote balance — the exchange-side echo of
        the book's full-equity position. A SELL unwinds exactly what our own BUYs
        acquired, never the account's pre-existing coins.
        """
        rules = self.rules()
        price = Decimal(str(reference_price))

        if side == BUY:
            budget = self.free_balance(rules.quote_asset) * Decimal(str(self.quote_fraction))
            if self.max_notional is not None:
                budget = min(budget, Decimal(str(self.max_notional)))
            raw_qty = budget / price
        else:
            raw_qty = self._position_qty
            if raw_qty <= 0:
                raise OrderTooSmall(
                    "nothing to sell: this executor holds no position it opened "
                    "(it will not sell the demo account's pre-funded balance)"
                )

        qty = self._floor_to_step(raw_qty, rules.step_size)
        qty = min(qty, rules.max_qty)

        if qty < rules.min_qty or qty <= 0:
            raise OrderTooSmall(
                f"quantity {qty} is below LOT_SIZE minQty {rules.min_qty} "
                f"for {rules.symbol} at reference {reference_price}"
            )
        if rules.min_notional_applies_to_market and qty * price < rules.min_notional:
            raise OrderTooSmall(
                f"notional {qty * price} is below the venue minimum "
                f"{rules.min_notional} {rules.quote_asset}"
            )
        return qty

    # -------------------------------------------------------------- idempotency --
    def client_order_id(self, side: int, key: str) -> str:
        """The id this order will carry however many times it is sent.

        Binance enforces uniqueness of ``newClientOrderId`` per symbol, so an id
        derived from *what the order is* rather than *when it was sent* makes the
        exchange itself the duplicate guard: a resubmit — ours, the Lambda's or
        the scheduler's — is refused instead of opening a second position. The
        key is the decision (normally the bar), so one bar can produce at most
        one BUY and one SELL, forever.

        Hashed rather than spelled out because a bar timestamp contains spaces
        and colons, which the venue's id alphabet does not allow.
        """
        digest = hashlib.sha256(f"{self.symbol}|{int(side)}|{key}".encode()).hexdigest()
        return f"{self.client_prefix}-{digest[:20]}"

    def is_ours(self, client_order_id: Optional[str]) -> bool:
        """True for orders this channel placed — the account is shared.

        The demo account carries the heartbeat's daily round-trips as well as
        this channel's, and one day a live account may carry more still. Without
        this, another bot's order would read as our own unbooked fill.
        """
        return bool(client_order_id) and client_order_id.startswith(f"{self.client_prefix}-")

    def lookup_order(self, client_order_id: str) -> Optional[dict[str, Any]]:
        """What became of an order, asked by OUR id. ``None`` = the venue never saw it.

        ``GET /api/v3/order`` reports the aggregate but not the per-fill
        commissions, so for an order that executed the trades are fetched too and
        shaped like the ``fills`` array a submit would have returned. Everything
        downstream then cannot tell a recovered order from a fresh one.
        """
        try:
            order = self._request("GET", "/api/v3/order",
                                  {"symbol": self.symbol,
                                   "origClientOrderId": client_order_id},
                                  signed=True)
        except BinanceAPIError as exc:
            if exc.code == _ERR_ORDER_DOES_NOT_EXIST:
                return None
            raise
        order = dict(order)
        if not order.get("fills") and Decimal(str(order.get("executedQty", "0"))) > 0:
            order["fills"] = self._trades_for_order(order.get("orderId"))
        return order

    def _trades_for_order(self, order_id: Any) -> list[dict[str, Any]]:
        """The individual trades of one order, in ``fills`` shape."""
        trades = self._request("GET", "/api/v3/myTrades",
                               {"symbol": self.symbol, "orderId": order_id},
                               signed=True)
        return [{"price": t["price"], "qty": t["qty"],
                 "commission": t.get("commission", "0"),
                 "commissionAsset": t.get("commissionAsset", "")}
                for t in (trades or [])]

    def orders_since(self, order_id: Optional[int] = None,
                     limit: Optional[int] = None) -> list[dict[str, Any]]:
        """Orders on this symbol from ``order_id`` onwards, or the newest few.

        This is how a fill that reached the venue but never reached the book gets
        found. The idempotency key cannot prevent that failure — the order was
        legitimate and unique — it can only be revealed by asking the account.

        ``limit`` is left unset when scanning forward from an id, deliberately.
        Binance answers ``orderId`` with the *oldest* matching orders, so a small
        limit would return a window that ends before the newest order — the one
        an orphan would be — and the check would look clean while missing it.
        """
        params: dict[str, Any] = {"symbol": self.symbol}
        if limit is not None:
            params["limit"] = int(limit)
        if order_id is not None:
            params["orderId"] = int(order_id)
        payload = self._request("GET", "/api/v3/allOrders", params, signed=True)
        return list(payload or [])

    # ---------------------------------------------------------------- execution --
    @staticmethod
    def _average_fill_price(response: dict) -> tuple[float, float, int]:
        """Collapse a possibly-partial, multi-price fill into one number.

        A market order rarely clears at a single price: it walks the book and
        comes back as several fills. The price the position was really opened at
        is the quantity-weighted average, which is also exactly what
        ``cummulativeQuoteQty / executedQty`` reports — preferred here because the
        venue computes it and the two cannot disagree.
        """
        executed = Decimal(response.get("executedQty", "0"))
        quote = Decimal(response.get("cummulativeQuoteQty", "0"))
        fills = response.get("fills") or []

        if executed > 0 and quote > 0:
            return float(quote / executed), float(executed), len(fills)

        # No aggregate reported (some response types omit it) — weight by hand.
        total_qty = sum(Decimal(f["qty"]) for f in fills)
        if total_qty <= 0:
            raise BinanceAPIError(-1, f"order reports no executed quantity: {response}",
                                  None, "/api/v3/order")
        weighted = sum(Decimal(f["price"]) * Decimal(f["qty"]) for f in fills)
        return float(weighted / total_qty), float(total_qty), len(fills)

    @staticmethod
    def _commission(response: dict, base_asset: str) -> tuple[float, str, Decimal]:
        """Total commission, plus how much of it was taken out of the base asset.

        Binance can charge in the asset received, or in BNB when the account holds
        it. That distinction is not cosmetic: a BUY charged in BTC leaves us
        holding *less BTC than we bought*, and selling the un-netted quantity later
        fails on insufficient balance.
        """
        fills = response.get("fills") or []
        if not fills:
            return 0.0, "", Decimal("0")
        total = Decimal("0")
        base_taken = Decimal("0")
        assets = set()
        for f in fills:
            amount = Decimal(f.get("commission", "0"))
            asset = f.get("commissionAsset", "")
            total += amount
            assets.add(asset)
            if asset == base_asset:
                base_taken += amount
        return float(total), "/".join(sorted(a for a in assets if a)), base_taken

    def _submit(self, params: dict[str, Any], client_order_id: str,
                order: Order, qty: Decimal) -> dict[str, Any]:
        """Send the order once, and let the venue settle anything ambiguous.

        Three outcomes are possible and only one of them is "rejected":

        * the submit answers — that is the fill;
        * the submit fails ambiguously (timeout, 5xx) — the order may be live, so
          the venue is asked by ``origClientOrderId`` before anything else, and
          only if it truly never arrived is it sent again, with the same id;
        * the venue refuses it — if it refuses because it already holds an order
          with this id, then this run is a repeat of one that already traded and
          that existing fill is the honest answer; anything else is a real
          rejection and propagates.

        The duplicate case is not detected by parsing the error message. The
        venue is asked instead: "duplicate" and "insufficient balance" arrive as
        the same ``-2010``, and a bot that guessed wrong here would either trade
        twice or swallow a genuine failure.
        """
        try:
            try:
                return self._request("POST", "/api/v3/order", params, signed=True,
                                     retry_transport=False)
            except requests.RequestException as exc:
                logger.error("order submit did not answer (%s) — asking the venue", exc)
                return self._settle_uncertain_submit(params, client_order_id, exc)
            except BinanceAPIError as exc:
                if exc.http_status and exc.http_status >= 500:
                    logger.error("order submit answered HTTP %s — asking the venue",
                                 exc.http_status)
                    return self._settle_uncertain_submit(params, client_order_id, exc)
                raise
        except BinanceAPIError as exc:
            existing = None
            try:
                existing = self.lookup_order(client_order_id)
            except (BinanceAPIError, requests.RequestException) as probe:
                # The question could not be asked. Treat the rejection as final
                # and keep the evidence: losing the C3 record because a second
                # request also failed would hide the rejection entirely.
                logger.error("could not ask the venue about %s (%s) — treating the "
                             "rejection as final", client_order_id, probe)
            if existing is not None:
                logger.warning("venue already holds %s (%s) — using its own copy "
                               "instead of trading again", client_order_id, exc)
                return existing
            # Gate C criterion C3 counts venue rejections against submissions.
            # Only a failed order POST is a rejection — errors from public GETs
            # (rules, mark price) never reach this handler.
            self._rejections.append({
                "time": order.time,
                "side": order.side,
                "requested_qty": float(qty),
                "reference_price": order.reference_price,
                "client_order_id": client_order_id,
                "code": exc.code,
                "message": exc.msg,
                "http_status": exc.http_status,
            })
            raise

    def _settle_uncertain_submit(self, params: dict[str, Any], client_order_id: str,
                                 cause: Exception) -> dict[str, Any]:
        """Decide what an unanswered submit actually did, by asking the venue."""
        existing = self.lookup_order(client_order_id)
        if existing is not None:
            logger.warning("the order did land as %s despite %r — no second order sent",
                           client_order_id, cause)
            return existing
        logger.warning("the venue has no %s after %r — sending it once more, same id",
                       client_order_id, cause)
        try:
            return self._request("POST", "/api/v3/order", params, signed=True,
                                 retry_transport=False)
        except requests.RequestException as exc:
            # Twice unanswered. Guessing now is exactly the failure this whole
            # path exists to prevent, so stop and say what is unknown.
            raise OrderSubmissionUncertain(
                f"{client_order_id} could not be confirmed: the first attempt failed "
                f"({cause!r}), the venue reported no such order, and the resend failed "
                f"too ({exc!r}) — reconcile against the account before trading again"
            ) from exc

    def execute(self, order: Order) -> Fill:
        """Submit ``order`` as a MARKET order and report what the venue gave back.

        This is the whole point of the module: from here down it is a real signed
        request against a real matching engine, and the returned :class:`Fill`
        carries the venue's price rather than a modelled one.
        """
        if order.symbol and order.symbol.upper() != self.symbol:
            raise ValueError(
                f"order is for {order.symbol} but this executor trades {self.symbol}"
            )
        rules = self.rules()
        if not rules.tradable:
            raise SymbolNotTradable(f"{self.symbol} status is {rules.status}, not TRADING")

        qty = Decimal(str(order.qty)) if order.qty is not None \
            else self.plan_quantity(order.side, order.reference_price)
        qty = self._floor_to_step(qty, rules.step_size)

        client_order_id = self.client_order_id(
            order.side, order.idempotency_key or order.time)
        params = {
            "symbol": self.symbol,
            "side": "BUY" if order.side == BUY else "SELL",
            "type": "MARKET",
            "quantity": format(qty.normalize(), "f"),
            "newClientOrderId": client_order_id,
            "newOrderRespType": "FULL",   # we need the individual fills
        }
        mark_at_order = self.mark_price() if self.measure_drift else None

        logger.info("submitting %s %s %s as %s", params["side"], params["quantity"],
                    self.symbol, client_order_id)
        response = self._submit(params, client_order_id, order, qty)

        avg_price, executed_qty, fill_count = self._average_fill_price(response)
        fee_paid, fee_asset, base_fee = self._commission(response, rules.base_asset)
        status = response.get("status", "")

        if status not in ("FILLED", "PARTIALLY_FILLED"):
            logger.warning("order %s came back %s, not filled",
                           response.get("orderId"), status)

        # Track only what we can actually sell later: bought quantity net of any
        # commission taken in the base asset, less whatever a SELL just unwound.
        if order.side == BUY:
            self._position_qty += Decimal(str(executed_qty)) - base_fee
        else:
            self._position_qty = max(Decimal("0"),
                                     self._position_qty - Decimal(str(executed_qty)))

        assumed = slipped_price(order.reference_price, order.side, self.assumed_slippage)
        actual_slippage = order.side * (avg_price / order.reference_price - 1.0)
        record = Reconciliation(
            time=order.time,
            side=order.side,
            reference_price=order.reference_price,
            assumed_price=assumed,
            actual_price=avg_price,
            slippage_assumed=self.assumed_slippage,
            slippage_actual=actual_slippage,
            qty=executed_qty,
            fee_paid=fee_paid,
            fee_asset=fee_asset,
            order_id=str(response.get("orderId", "")),
            fill_count=fill_count,
            status=status,
            mark_at_order=mark_at_order,
            requested_qty=float(qty),
            client_order_id=str(response.get("clientOrderId") or client_order_id),
        )
        self._reconciliations.append(record)
        logger.info("filled %s @ %.2f (assumed %.2f, slippage %.5f%% vs %.5f%% assumed)",
                    executed_qty, avg_price, assumed,
                    actual_slippage * 100, self.assumed_slippage * 100)

        return Fill(
            price=avg_price,
            side=order.side,
            time=order.time,
            qty=executed_qty,
            fee_paid=fee_paid,
            fee_asset=fee_asset or None,
            order_id=str(response.get("orderId", "")) or None,
            raw=response,
            base_asset=rules.base_asset,
        )

    # ----------------------------------------------------------------- reporting --
    def reconciliations(self) -> list[Reconciliation]:
        """Every fill so far, against what the book assumed it would be."""
        return list(self._reconciliations)

    def rejections(self) -> list[dict[str, Any]]:
        """Every order the venue refused, with its error code — Gate C's C3."""
        return list(self._rejections)

    @property
    def position_qty(self) -> Decimal:
        """Base asset this executor is currently holding from its own buys."""
        return self._position_qty

    def set_position(self, qty) -> None:
        """Tell the executor what it is already holding.

        The position is tracked in memory, which is fine for a process that
        opens and closes in one breath. A strategy bot is not that: it runs as a
        Lambda that lives for seconds, and may hold a position for weeks. Without
        restoring this, the exit leg would fail with "nothing to sell" — the
        position would be stranded on the venue with no code able to close it.

        The book is the source of truth: ``PaperPortfolio.qty`` is persisted, so
        the caller restores from there rather than from the account balance,
        which cannot distinguish our position from coins the account already had.
        """
        value = Decimal(str(abs(float(qty))))
        if value < 0:
            raise ValueError(f"position must not be negative, got {qty}")
        self._position_qty = value

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (f"BinanceDemoExecutor(symbol={self.symbol}, base_url={self.base_url}, "
                f"position={self._position_qty})")
