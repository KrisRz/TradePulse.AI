"""Kraken REST transport: signing, nonces, typed errors, pair rules.

The bottom layer of the Kraken executor
(docs/KRAKEN_EXECUTOR_PREREGISTRATION_2026-11-14.md). It knows how to talk to
the exchange and nothing about positions, books or strategy. Everything that
decides *whether* to trade lives above it.

Two rules shape this module:

* **A read may be repeated, a write may not.** A timeout on ``Balance`` is
  retried here. A timeout on ``AddOrder`` is not: the order may exist, so the
  call raises :class:`KrakenOutcomeUnknown` and the caller looks the order up by
  its client id before doing anything else (rule R5). Retrying blind is how a
  bot buys twice.
* **Kraken answers HTTP 200 with an error list.** Success is ``error == []``,
  never the status code.

There is no spot sandbox. Private calls are exercised with ``validate=true``
and then with the smallest real orders (T0–T8 in the pre-registration).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import threading
import time as _time
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Any, Optional
from urllib.parse import urlencode

import requests

BASE_URL = "https://api.kraken.com"

#: Errors after which the request did not take effect and may be sent again.
_NOT_PROCESSED = ("EAPI:Rate limit exceeded", "EGeneral:Temporary lockout",
                  "EAPI:Invalid nonce")
#: Errors after which nobody knows whether the request took effect.
_UNCERTAIN = ("EService:Unavailable", "EService:Busy", "EService:Deadline elapsed",
              "EGeneral:Internal error")


class KrakenAPIError(RuntimeError):
    """The exchange refused the request and said why."""

    def __init__(self, errors: list[str], endpoint: str) -> None:
        self.errors = list(errors)
        self.endpoint = endpoint
        super().__init__(f"Kraken {endpoint}: {', '.join(self.errors)}")

    def has(self, prefix: str) -> bool:
        return any(e.startswith(prefix) for e in self.errors)


class KrakenOutcomeUnknown(RuntimeError):
    """A write was sent and its fate is unknown — look it up, never resend."""

    def __init__(self, endpoint: str, cause: str) -> None:
        self.endpoint = endpoint
        self.cause = cause
        super().__init__(f"Kraken {endpoint}: outcome unknown ({cause})")


class PairNotTradable(RuntimeError):
    """The pair is not ``online`` — no order may be sent."""


@dataclass(frozen=True)
class PairRules:
    """What the exchange allows on one pair, read fresh each run (rule R3)."""

    key: str              # Kraken's own name, e.g. XXBTZGBP
    altname: str          # XBTGBP
    base: str             # XXBT
    quote: str            # ZGBP
    ordermin: Decimal     # minimum order, base units
    costmin: Decimal      # minimum order, quote units
    tick_size: Decimal    # price step
    lot_decimals: int     # volume precision
    status: str

    @property
    def tradable(self) -> bool:
        return self.status == "online"

    def floor_volume(self, volume: Decimal) -> Decimal:
        """Round a volume DOWN to the pair's precision — never buy or sell more
        than intended."""
        step = Decimal(1).scaleb(-self.lot_decimals)
        return volume.quantize(step, rounding=ROUND_DOWN)

    def floor_price(self, price: Decimal) -> Decimal:
        return (price / self.tick_size).to_integral_value(ROUND_DOWN) * self.tick_size

    def allows(self, volume: Decimal, price: Decimal) -> bool:
        """True when an order of ``volume`` at ``price`` clears both minimums."""
        return volume >= self.ordermin and volume * price >= self.costmin


def sign(path: str, nonce: str, postdata: str, secret_b64: str) -> str:
    """Kraken's request signature: HMAC-SHA512 of ``path + SHA256(nonce +
    postdata)`` under the base64-decoded secret, base64-encoded."""
    digest = hashlib.sha256((nonce + postdata).encode()).digest()
    mac = hmac.new(base64.b64decode(secret_b64), path.encode() + digest, hashlib.sha512)
    return base64.b64encode(mac.digest()).decode()


class KrakenClient:
    """Signed and public calls against Kraken's REST API."""

    def __init__(self, api_key: str = "", api_secret: str = "", *,
                 session: Optional[requests.Session] = None,
                 base_url: str = BASE_URL, timeout: float = 10.0,
                 read_attempts: int = 3, backoff: float = 1.0,
                 clock=_time.time, sleep=_time.sleep) -> None:
        self._key = api_key
        self._secret = api_secret
        self._session = session or requests.Session()
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._read_attempts = max(1, read_attempts)
        self._backoff = backoff
        self._clock = clock
        self._sleep = sleep
        self._last_nonce = 0
        self._nonce_lock = threading.Lock()

    # -- plumbing --------------------------------------------------------- #
    def _nonce(self) -> str:
        """Strictly increasing, millisecond-based. Kraken rejects a nonce that
        is not greater than the last one seen for the key."""
        with self._nonce_lock:
            self._last_nonce = max(self._last_nonce + 1, int(self._clock() * 1000))
            return str(self._last_nonce)

    @staticmethod
    def _unwrap(body: Any, endpoint: str) -> Any:
        if not isinstance(body, dict) or "error" not in body:
            raise KrakenOutcomeUnknown(endpoint, "malformed response")
        if body["error"]:
            raise KrakenAPIError(body["error"], endpoint)
        return body.get("result")

    def _send(self, method: str, path: str, *, params: Optional[dict] = None,
              signed: bool = False) -> Any:
        """One attempt. Raises ``requests.RequestException`` on transport
        failure, :class:`KrakenAPIError` on a refusal."""
        url = self._base + path
        if not signed:
            resp = self._session.request(method, url, params=params, timeout=self._timeout)
        else:
            if not (self._key and self._secret):
                raise RuntimeError("Kraken private call without credentials")
            nonce = self._nonce()
            postdata = urlencode({"nonce": nonce, **(params or {})})
            headers = {"API-Key": self._key,
                       "API-Sign": sign(path, nonce, postdata, self._secret),
                       "Content-Type": "application/x-www-form-urlencoded"}
            resp = self._session.request(method, url, data=postdata, headers=headers,
                                         timeout=self._timeout)
        if resp.status_code >= 500:
            raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
        try:
            body = resp.json()
        except ValueError as exc:
            raise requests.RequestException(f"non-JSON response (HTTP {resp.status_code})") from exc
        return self._unwrap(body, path)

    def _read(self, method: str, path: str, *, params: Optional[dict] = None,
              signed: bool = False) -> Any:
        """A call that changes nothing: retried on transport trouble and on the
        exchange's "try again" answers, a bounded number of times."""
        last: Exception = RuntimeError("no attempt made")
        for attempt in range(self._read_attempts):
            try:
                return self._send(method, path, params=params, signed=signed)
            except KrakenAPIError as exc:
                if not any(exc.has(p) for p in _NOT_PROCESSED + _UNCERTAIN):
                    raise
                last = exc
            except KrakenOutcomeUnknown as exc:
                last = exc
            except requests.RequestException as exc:
                last = exc
            if attempt + 1 < self._read_attempts:
                self._sleep(self._backoff * (2 ** attempt))
        raise last

    def public(self, name: str, params: Optional[dict] = None) -> Any:
        return self._read("GET", f"/0/public/{name}", params=params)

    def private_read(self, name: str, params: Optional[dict] = None) -> Any:
        """A signed call that only reads (Balance, OpenOrders, ClosedOrders…)."""
        return self._read("POST", f"/0/private/{name}", params=params, signed=True)

    def private_write(self, name: str, params: Optional[dict] = None) -> Any:
        """A signed call that changes state (AddOrder, CancelOrder). Sent ONCE.

        A clean refusal raises :class:`KrakenAPIError` — nothing happened. A
        timeout, a 5xx or a "service unavailable" answer raises
        :class:`KrakenOutcomeUnknown` — the caller must look the order up.
        """
        path = f"/0/private/{name}"
        try:
            return self._send("POST", path, params=params, signed=True)
        except KrakenAPIError as exc:
            if any(exc.has(p) for p in _UNCERTAIN):
                raise KrakenOutcomeUnknown(path, ", ".join(exc.errors)) from exc
            raise
        except requests.RequestException as exc:
            raise KrakenOutcomeUnknown(path, type(exc).__name__) from exc

    # -- public data ------------------------------------------------------ #
    def system_status(self) -> str:
        """``online`` when orders may be placed (rule R2). Other values seen in
        Kraken's docs: maintenance, cancel_only, post_only."""
        return str(self.public("SystemStatus")["status"])

    def pair_rules(self, pair: str) -> PairRules:
        result = self.public("AssetPairs", {"pair": pair})
        if not result or len(result) != 1:
            raise RuntimeError(f"Kraken AssetPairs: expected one pair for {pair!r}, "
                               f"got {sorted(result or {})}")
        key, raw = next(iter(result.items()))
        return PairRules(
            key=key, altname=raw["altname"], base=raw["base"], quote=raw["quote"],
            ordermin=Decimal(str(raw["ordermin"])), costmin=Decimal(str(raw["costmin"])),
            tick_size=Decimal(str(raw["tick_size"])), lot_decimals=int(raw["lot_decimals"]),
            status=str(raw["status"]))

    def best_bid_ask(self, pair: str) -> tuple[Decimal, Decimal]:
        result = self.public("Ticker", {"pair": pair})
        raw = next(iter(result.values()))
        return Decimal(raw["b"][0]), Decimal(raw["a"][0])

    # -- account ---------------------------------------------------------- #
    def balance(self) -> dict[str, Decimal]:
        """Balances by Kraken asset code (``ZGBP``, ``XXBT``). An empty account
        returns an empty mapping."""
        return {asset: Decimal(str(amount))
                for asset, amount in (self.private_read("Balance") or {}).items()}

    def __repr__(self) -> str:  # pragma: no cover - never leak the key
        return f"KrakenClient(base_url={self._base!r}, authenticated={bool(self._key)})"
