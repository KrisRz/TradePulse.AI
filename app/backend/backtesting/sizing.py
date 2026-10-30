"""Hold a fixed share of the account in the position, pulled back inside a band.

Decided 2026-10-30 (docs/KRAKEN_SIZING_RESULTS_2026-10-30.md): the drawdown limit
is measured on the whole account, so the bot holds ``w`` of it in BTC and the
rest in cash. Sizing only at entry is not enough — after a long rally the BTC
share drifts to ~0.9 and a crash inside the same trade hits nearly everything
(measured: DD -40.7%). Pulling the share back to ``w`` whenever it leaves
``w ± band`` fixes that at ~0.6 trades a year.

This module is the one place that rule lives. The paper book and the research
harness both call it, so the backtest and the bot cannot drift apart on it.
"""

from __future__ import annotations

from typing import Optional


def rebalance_amount(cash: float, position_value: float, weight: float,
                     band: float, min_order: float) -> Optional[float]:
    """Quote amount to buy (> 0) or sell (< 0) to bring the position back to
    ``weight`` of the account, or None when no trade is due.

    No trade while the share stays within ``weight ± band`` (inclusive), and none
    smaller than ``min_order``: the venue would refuse it (Kraken XBT/GBP takes
    0.00006 BTC at minimum, ~£3.5 in 2026-10).
    """
    total = cash + position_value
    if total <= 0:
        return None
    if abs(position_value / total - weight) <= band:
        return None
    amount = weight * total - position_value
    if abs(amount) < min_order:
        return None
    return amount
