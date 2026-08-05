"""Virtual portfolio for paper trading.

Accounting mirrors the backtest engine exactly (same shared cost model in
``backtesting.costs``): full-equity positions, compounding, per-side fees and
adverse slippage. Fed the same prices in the same order, this produces the same
equity curve as ``backtesting.engine.run_backtest`` — see the equivalence test.
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

    def __post_init__(self) -> None:
        if self.realized is None:
            self.realized = self.initial_capital
        # Plain attribute, deliberately NOT a dataclass field: ``to_dict`` uses
        # ``asdict`` and this state is persisted to DynamoDB, so the executor
        # must stay out of the serialised book.
        self._executor: Optional[Executor] = None

    # -- execution ------------------------------------------------------- #
    def set_executor(self, executor: Optional[Executor]) -> None:
        """Route fills through ``executor`` (None restores the slippage model).

        This is how a real venue — Binance's test network, later the live
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

    def _open(self, new_side: int, price: float, time: str) -> None:
        fill = self._fill(opening_order_side(new_side), price, time)
        self.equity_before_entry = self.realized
        self.realized = apply_fee(self.realized, self.fee_rate)   # entry fee
        self.side = new_side
        self.entry_fill = fill.price
        self.entry_equity = self.realized
        self.entry_time = time

    def _close(self, price: float, time: str, reason: str) -> None:
        exit_fill = self._fill(closing_order_side(self.side), price, time).price
        gross = self.side * (exit_fill / self.entry_fill - 1.0)
        self.realized = apply_fee(self.entry_equity * (1.0 + gross), self.fee_rate)
        net = self.realized / self.equity_before_entry - 1.0
        self.trades.append(PaperTrade(
            entry_time=self.entry_time, exit_time=time, side=self.side,
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
        gross = self.side * (price / self.entry_fill - 1.0)
        return self.entry_equity * (1.0 + gross)

    def total_return(self, mark_price: Optional[float] = None) -> float:
        return self.equity(mark_price) / self.initial_capital - 1.0

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
        return p
