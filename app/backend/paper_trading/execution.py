"""Execution seam: the one place where an intent to trade becomes a fill.

Until now the paper bot had no notion of an order at all — ``PaperPortfolio``
computed a fill price from a slippage model and booked it in the same breath.
That is fine for simulation, but it means the code that talks to an exchange
does not exist yet, and the day real money arrives it would be brand-new,
never-executed code. This module introduces the seam so that path can be built
and exercised against Binance's test network long before it matters.

The abstraction is deliberately the one an exchange actually offers: you submit
an order to BUY or to SELL, and you learn what you got. Everything about
positions, sides and equity stays on the portfolio's side of the seam.

Adverse slippage, unified
-------------------------
``backtesting.costs`` models entry and exit separately, keyed by the *position*
side. Expressed as an *order* side the two collapse into one rule — a buy pays
more, a sell receives less:

    fill = reference * (1 + order_side * slippage)

which is arithmetically identical to the ``costs`` helpers in all four cases
(open/close × long/short). ``test_execution.py`` pins that equivalence, so this
module cannot drift from the shared cost model the backtest engine uses.

Scope
-----
``SimulatedExecutor`` reproduces today's behaviour exactly and carries no
quantity: the portfolio sizes positions as a fraction of equity, never in BTC.
A real executor deals in quantities, lot-size rounding and per-fill fees —
hence the optional ``qty``/``fee_paid`` fields, which simulation leaves unset.
Quantity-aware accounting is a separate piece of work and is NOT solved here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol

BUY = 1
SELL = -1


@dataclass(frozen=True)
class Order:
    """An intent to trade, in the terms an exchange understands."""

    side: int                      # BUY (+1) or SELL (-1)
    reference_price: float         # the quote the decision was taken on
    time: str
    symbol: str = ""
    qty: Optional[float] = None    # None = size not modelled (fraction of equity)
    # Stable name for *this* decision, so that sending the order twice cannot
    # open the position twice. A real executor derives the venue's client order
    # id from it (``binance_demo.client_order_id``); simulation ignores it.
    # Defaults to the bar time, which is already what a decision belongs to — a
    # caller passes something else only where a trade is not bar-driven, such as
    # the kill switch flattening a position.
    idempotency_key: Optional[str] = None

    def __post_init__(self) -> None:
        if self.side not in (BUY, SELL):
            raise ValueError(f"order side must be +1 (buy) or -1 (sell), got {self.side}")
        if self.reference_price <= 0:
            raise ValueError(f"reference price must be positive, got {self.reference_price}")
        if self.qty is not None and self.qty <= 0:
            raise ValueError(f"quantity must be positive when given, got {self.qty}")


@dataclass(frozen=True)
class Fill:
    """What the execution venue actually gave us."""

    price: float
    side: int
    time: str
    qty: Optional[float] = None
    fee_paid: Optional[float] = None      # in fee_asset; None = caller's own model
    fee_asset: Optional[str] = None
    order_id: Optional[str] = None
    raw: Optional[dict[str, Any]] = None  # venue response, kept for audit
    # Which asset ``qty`` is denominated in. The book needs it to tell a
    # commission billed in the asset just bought (which reduces the position)
    # from one billed in something else (which does not).
    base_asset: Optional[str] = None


class Executor(Protocol):
    """Anything that can turn an :class:`Order` into a :class:`Fill`."""

    def execute(self, order: Order) -> Fill:  # pragma: no cover - protocol
        ...


def slipped_price(reference_price: float, order_side: int, slippage: float) -> float:
    """Fill price after adverse slippage: a buy pays more, a sell receives less."""
    return reference_price * (1.0 + order_side * slippage)


def opening_order_side(position_side: int) -> int:
    """Order that OPENS ``position_side``: long is opened by buying."""
    return position_side


def closing_order_side(position_side: int) -> int:
    """Order that CLOSES ``position_side``: a long is closed by selling."""
    return -position_side


class SimulatedExecutor:
    """Fills from a slippage model — the behaviour the paper bot has always had.

    Stateless and deterministic: the same order always produces the same fill,
    which is what lets the golden-master replay be exact. It ignores
    ``Order.idempotency_key`` deliberately: nothing here can be sent twice, and
    a model that started reading the key could no longer reproduce the frozen
    M5 book statement for statement.
    """

    def __init__(self, slippage: float = 0.0002) -> None:
        if slippage < 0:
            raise ValueError(f"slippage must not be negative, got {slippage}")
        self.slippage = slippage

    def execute(self, order: Order) -> Fill:
        return Fill(
            price=slipped_price(order.reference_price, order.side, self.slippage),
            side=order.side,
            time=order.time,
            qty=order.qty,
        )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"SimulatedExecutor(slippage={self.slippage})"
