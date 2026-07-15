"""Shared execution cost model — the single source of truth for fills.

Both the backtest engine and the live paper-trading broker import these helpers,
so a trade is priced identically whether it is simulated on history or executed
on the live paper account. That shared code path is what guarantees the backtest
and the live bot cannot silently diverge.
"""

from __future__ import annotations


def entry_fill_price(price: float, side: int, slippage: float) -> float:
    """Fill price when OPENING a position, with adverse slippage.

    A long (side=+1) buys slightly above the quoted price; a short (side=-1)
    sells slightly below it.
    """
    return price * (1.0 + side * slippage)


def exit_fill_price(price: float, side: int, slippage: float) -> float:
    """Fill price when CLOSING a position, with adverse slippage.

    Closing a long sells slightly below; closing a short buys slightly above.
    """
    return price * (1.0 - side * slippage)


def apply_fee(equity: float, fee_rate: float) -> float:
    """Equity after paying a per-side fee on a full-equity notional."""
    return equity * (1.0 - fee_rate)
