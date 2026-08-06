"""Virtual portfolio for paper trading.

Accounting mirrors the backtest engine exactly (same shared cost model in
``backtesting.costs``): full-equity positions, compounding, per-side fees and
adverse slippage. Fed the same prices in the same order, this produces the same
equity curve as ``backtesting.engine.run_backtest`` — see the equivalence test.

Two ways of counting, and why
-----------------------------
The book was born *fractional*: a position is "all of the equity", and a trade's
result is a return applied to that equity. An exchange knows nothing of
fractions — it deals in quantities of an asset. Until M6 that gap did not matter,
because nothing here ever spoke to an exchange.

Rather than convert the whole book and re-bless the golden master, the two live
side by side and the **fill decides which one is used**:

* a fill without ``qty`` (``SimulatedExecutor``) takes the *modelled* path, whose
  arithmetic is untouched, statement for statement, from the version the M5
  window is being measured on. It reproduces bit-for-bit.
* a fill *with* ``qty`` (a real venue) takes the *quantity-backed* path: equity
  is ``cash + qty * price``, and the fee that gets booked is the one the venue
  actually charged, not the modelled rate.

The two are not allowed to drift apart: ``test_portfolio_quantity.py`` feeds the
quantity path a fill carrying exactly what the model would have produced and
asserts both paths agree. That is the same guard that keeps ``slipped_price`` and
``costs.py`` honest.

The reparameterisation is exact, shorts included. At entry with equity ``E``::

    qty  = side * E / entry_fill
    cash = E * (1 - side)          # 0 for a long, 2E for a short

so ``cash + qty * p == E * (1 + side * (p / entry_fill - 1))`` — algebraically
the fractional formula, which is why one can replace the other at all.

Fees the model cannot express
-----------------------------
A venue may charge commission in the asset bought, in the quote currency, or in
a third asset entirely (Binance bills BNB when the account holds it — measured
2026-08-06). The first two are booked exactly. The third cannot be converted
without a price for that asset, so it is accumulated in ``fees_external`` and
deliberately left out of equity: silently ignoring it would overstate results,
and guessing a conversion rate would be worse. See ``docs/`` for the
recommendation to disable BNB fee payment so that backtest and live stay
comparable.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from ..backtesting.costs import apply_fee
from .execution import (
    Executor,
    Order,
    SimulatedExecutor,
    closing_order_side,
    opening_order_side,
)


@dataclass
class PaperTrade:
    entry_time: str
    exit_time: str
    side: int
    entry_price: float
    exit_price: float
    net_return: float
    exit_reason: str = "signal"


@dataclass
class PaperPortfolio:
    fee_rate: float = 0.001
    slippage: float = 0.0002
    initial_capital: float = 10_000.0

    # mutable state
    realized: float = None            # equity booked on closed trades
    side: int = 0                     # -1 / 0 / +1
    entry_fill: float = 0.0           # entry price after slippage
    entry_equity: float = 0.0         # equity at entry (after entry fee)
    equity_before_entry: float = 0.0  # equity just before entry fee
    entry_time: Optional[str] = None
    last_price: float = 0.0
    trades: list = field(default_factory=list)

    # -- quantity-aware state (M6) --------------------------------------- #
    # Always maintained, but only load-bearing once fills carry real
    # quantities. On the modelled path these are derived for reporting and
    # never feed back into equity, so the legacy arithmetic stays exact.
    qty: float = 0.0                  # signed base-asset units, 0 when flat
    cash: float = 0.0                 # quote currency held
    quantity_backed: bool = False     # True once a venue fill drove the book
    fees_quote: float = 0.0           # commission actually charged, in quote
    fees_external: dict = field(default_factory=dict)  # {asset: amount}, unbooked

    def __post_init__(self) -> None:
        if self.realized is None:
            self.realized = self.initial_capital
        if not self.cash:
            self.cash = self.realized
        # Plain attribute, deliberately NOT a dataclass field: ``to_dict`` uses
        # ``asdict`` and this state is persisted to DynamoDB, so the executor
        # must stay out of the serialised book.
        self._executor: Optional[Executor] = None

    # -- execution ------------------------------------------------------- #
    def set_executor(self, executor: Optional[Executor]) -> None:
        """Route fills through ``executor`` (None restores the slippage model).

        This is how a real venue — Binance's demo network, later the live
        exchange — gets substituted for simulation without the accounting
        below knowing the difference.
        """
        self._executor = executor

    def _fill(self, order_side: int, price: float, time: str):
        """Obtain a fill for one order leg.

        Defaults to a :class:`SimulatedExecutor` built from the portfolio's
        *current* slippage, so restoring a book from disk can never execute
        against a stale cost model.
        """
        executor = self._executor or SimulatedExecutor(slippage=self.slippage)
        return executor.execute(Order(side=order_side, reference_price=price,
                                      time=time))

    # -- fee handling ---------------------------------------------------- #
    def _book_actual_fee(self, fill) -> tuple[float, float]:
        """Split a venue commission into (quote cost, base-asset units taken).

        Returns what must come off cash and off quantity respectively. Which
        one applies is decided by the asset the venue billed, and the fill
        carries the base asset so this does not have to be configured:

        * billed in the asset just traded  -> comes off the position
        * billed in the quote currency     -> comes off cash
        * billed in anything else (BNB)    -> recorded, not booked

        The third case is a real cost that cannot be converted without a price
        this book does not have. Guessing a rate would be worse than showing it
        separately, and silently dropping it would overstate every result.
        """
        amount = fill.fee_paid or 0.0
        if not amount:
            return 0.0, 0.0
        asset = (fill.fee_asset or "").upper()
        base = (fill.base_asset or "").upper()

        if asset and base and asset == base:
            return 0.0, amount
        if asset in ("", "USDT", "USD", "BUSD", "USDC", "FDUSD"):
            self.fees_quote += amount
            return amount, 0.0

        self.fees_external[asset] = self.fees_external.get(asset, 0.0) + amount
        return 0.0, 0.0

    # -- opening and closing --------------------------------------------- #
    def _open(self, new_side: int, price: float, time: str) -> None:
        fill = self._fill(opening_order_side(new_side), price, time)
        self.equity_before_entry = self.realized

        if fill.qty is None:
            # ---- modelled path: untouched, statement for statement --------
            self.realized = apply_fee(self.realized, self.fee_rate)   # entry fee
            self.side = new_side
            self.entry_fill = fill.price
            self.entry_equity = self.realized
            self.entry_time = time
            # Derived for reporting only; never read back into equity.
            self.qty = new_side * self.entry_equity / fill.price
            self.cash = self.entry_equity * (1.0 - new_side)
            return

        # ---- quantity-backed path: the venue's numbers, not the model's ----
        self.quantity_backed = True
        fee_quote, fee_base = self._book_actual_fee(fill)
        signed_qty = new_side * fill.qty
        notional = fill.qty * fill.price

        self.qty = signed_qty - (new_side * fee_base)
        self.cash = self.cash - (new_side * notional) - fee_quote
        self.side = new_side
        self.entry_fill = fill.price
        self.entry_time = time
        self.realized = self.cash + self.qty * fill.price
        self.entry_equity = self.realized

    def _close(self, price: float, time: str, reason: str) -> None:
        fill = self._fill(closing_order_side(self.side), price, time)
        exit_fill = fill.price

        if fill.qty is None:
            # ---- modelled path: untouched, statement for statement --------
            gross = self.side * (exit_fill / self.entry_fill - 1.0)
            self.realized = apply_fee(self.entry_equity * (1.0 + gross), self.fee_rate)
            net = self.realized / self.equity_before_entry - 1.0
            self.trades.append(PaperTrade(
                entry_time=self.entry_time, exit_time=time, side=self.side,
                entry_price=self.entry_fill, exit_price=exit_fill,
                net_return=net, exit_reason=reason,
            ).__dict__)
            self.side = 0
            self.qty = 0.0
            self.cash = self.realized
            return

        # ---- quantity-backed path -----------------------------------------
        self.quantity_backed = True
        fee_quote, fee_base = self._book_actual_fee(fill)
        closed_side = self.side
        proceeds = fill.qty * exit_fill

        self.cash = self.cash + (closed_side * proceeds) - fee_quote
        self.qty = self.qty - (closed_side * fill.qty) - fee_base
        self.realized = self.cash + self.qty * exit_fill
        net = self.realized / self.equity_before_entry - 1.0
        self.trades.append(PaperTrade(
            entry_time=self.entry_time, exit_time=time, side=closed_side,
            entry_price=self.entry_fill, exit_price=exit_fill,
            net_return=net, exit_reason=reason,
        ).__dict__)
        self.side = 0

    def reconcile(self, target_side: int, price: float, time: str) -> Optional[dict]:
        """Move the portfolio to ``target_side``, trading at ``price`` if needed.

        Returns a dict describing the action taken (or None if already there).
        """
        self.last_price = price
        target_side = int(target_side)
        if target_side == self.side:
            return None
        action: dict[str, Any] = {"time": time, "price": price,
                                  "from": self.side, "to": target_side}
        if self.side != 0:
            self._close(price, time, reason="signal")
        if target_side != 0:
            self._open(target_side, price, time)
        return action

    # -- reporting ------------------------------------------------------- #
    def equity(self, mark_price: Optional[float] = None) -> float:
        """Mark-to-market equity at ``mark_price`` (or last seen price)."""
        if self.side == 0:
            return self.realized
        price = mark_price if mark_price is not None else self.last_price
        if self.quantity_backed:
            return self.cash + self.qty * price
        gross = self.side * (price / self.entry_fill - 1.0)
        return self.entry_equity * (1.0 + gross)

    def total_return(self, mark_price: Optional[float] = None) -> float:
        return self.equity(mark_price) / self.initial_capital - 1.0

    def position_value(self, mark_price: Optional[float] = None) -> float:
        """Mark-to-market value of the held quantity alone, without cash."""
        price = mark_price if mark_price is not None else self.last_price
        return self.qty * price

    # -- persistence ----------------------------------------------------- #
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PaperPortfolio":
        p = cls(
            fee_rate=d.get("fee_rate", 0.001),
            slippage=d.get("slippage", 0.0002),
            initial_capital=d.get("initial_capital", 10_000.0),
        )
        for k, v in d.items():
            setattr(p, k, v)

        # A book written before the quantity fields existed (every state the M5
        # Lambda has persisted) carries neither. Rebuild them from what it does
        # have, so loading an old state cannot leave the position looking flat.
        if "qty" not in d:
            p.qty = p.side * p.entry_equity / p.entry_fill if p.side and p.entry_fill else 0.0
        if "cash" not in d:
            p.cash = p.entry_equity * (1.0 - p.side) if p.side else p.realized
        if "fees_external" not in d or p.fees_external is None:
            p.fees_external = {}
        return p
