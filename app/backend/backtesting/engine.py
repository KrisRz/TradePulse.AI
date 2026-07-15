"""Event-driven backtest engine.

Design goals (in priority order): correctness, then clarity, then speed.

Anti-look-ahead rule
--------------------
A target position is decided at the CLOSE of bar ``t`` and executed at the
OPEN of bar ``t+1``. A strategy can therefore never trade on information it
would not have had in real time.

Chronological order within a bar
--------------------------------
For each bar we process events in the order they happen in reality:
1. the OPEN prints  -> execute any pending target change here;
2. the bar trades between its HIGH and LOW -> check stop-loss / take-profit.

Costs
-----
Every fill pays ``slippage`` (price moves against us) and ``fee_rate`` (charged
on entry and on exit). Positions are full-equity and compound. Shorts are
modelled symmetrically to longs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from .costs import apply_fee, entry_fill_price, exit_fill_price


@dataclass
class BacktestConfig:
    fee_rate: float = 0.001        # 0.1% Binance spot taker, per side
    slippage: float = 0.0002       # 2 bps adverse fill
    initial_capital: float = 10_000.0
    stop_loss_pct: Optional[float] = None    # e.g. 0.005 = 0.5% adverse move
    take_profit_pct: Optional[float] = None  # e.g. 0.01 = 1.0% favourable move
    max_hold_bars: Optional[int] = None      # force-exit after N bars
    allow_short: bool = True


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    side: int                 # +1 long, -1 short
    entry_price: float        # fill after slippage
    exit_price: float         # fill after slippage
    gross_return: float       # before fees, signed for side
    net_return: float         # after entry+exit fees
    bars_held: int
    exit_reason: str          # 'signal' | 'stop' | 'take_profit' | 'max_hold' | 'end'


@dataclass
class BacktestResult:
    strategy_name: str
    timeframe: str
    equity_curve: pd.Series
    trades: list[Trade] = field(default_factory=list)
    config: BacktestConfig = field(default_factory=BacktestConfig)
    bars: int = 0
    start: Optional[pd.Timestamp] = None
    end: Optional[pd.Timestamp] = None

    @property
    def trades_frame(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame(
                columns=[
                    "entry_time", "exit_time", "side", "entry_price", "exit_price",
                    "gross_return", "net_return", "bars_held", "exit_reason",
                ]
            )
        return pd.DataFrame([t.__dict__ for t in self.trades])


def run_backtest(
    df: pd.DataFrame,
    target: pd.Series,
    config: BacktestConfig,
    strategy_name: str = "strategy",
    timeframe: str = "?",
) -> BacktestResult:
    """Run ``target`` (a -1/0/+1 Series) over ``df`` and return the result."""
    o = df["open"].to_numpy(dtype=float)
    h = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    c = df["close"].to_numpy(dtype=float)
    tgt = target.reindex(df.index).fillna(0.0).round().astype(int).to_numpy()
    idx = df.index
    n = len(df)

    fee = config.fee_rate
    slip = config.slippage
    sl = config.stop_loss_pct
    tp = config.take_profit_pct
    max_hold = config.max_hold_bars

    realized = config.initial_capital     # equity booked on closed trades
    equity_curve = np.empty(n, dtype=float)

    side = 0                 # current position: -1/0/+1
    entry_fill = 0.0         # entry price after slippage
    entry_equity = realized  # equity at entry (after entry fee)
    entry_i = 0
    equity_before_entry = realized   # equity just before entry fee (for trade P&L)
    blocked_side = 0         # suppress re-entry into this side until target flattens
    pending = 0              # target to execute at the *next* bar's open

    trades: list[Trade] = []

    def open_position(new_side: int, fill_price: float, i: int) -> None:
        nonlocal side, entry_fill, entry_equity, entry_i, equity_before_entry, realized
        equity_before_entry = realized
        realized = apply_fee(realized, fee)   # entry fee
        side = new_side
        entry_fill = entry_fill_price(fill_price, new_side, slip)  # adverse slippage
        entry_equity = realized
        entry_i = i

    def close_position(exit_price_raw: float, i: int, reason: str) -> None:
        nonlocal side, realized, blocked_side
        exit_fill = exit_fill_price(exit_price_raw, side, slip)   # adverse slippage
        gross = side * (exit_fill / entry_fill - 1.0)
        realized = apply_fee(entry_equity * (1.0 + gross), fee)  # exit fee
        net = realized / equity_before_entry - 1.0
        trades.append(
            Trade(
                entry_time=idx[entry_i],
                exit_time=idx[i],
                side=side,
                entry_price=entry_fill,
                exit_price=exit_fill,
                gross_return=gross,
                net_return=net,
                bars_held=i - entry_i,
                exit_reason=reason,
            )
        )
        blocked_side = side if reason in ("stop", "take_profit", "max_hold") else 0
        side = 0

    for i in range(n):
        # 1) Execute pending target change at THIS bar's open.
        if pending != side:
            if side != 0 and pending != side:
                close_position(o[i], i, reason="signal")
            if pending != 0 and side == 0:
                open_position(pending, o[i], i)

        # 2) Intrabar stop-loss / take-profit on the (possibly new) position.
        if side != 0 and (sl is not None or tp is not None):
            if side == 1:
                stop_price = entry_fill * (1.0 - sl) if sl is not None else None
                tp_price = entry_fill * (1.0 + tp) if tp is not None else None
                hit_stop = stop_price is not None and low[i] <= stop_price
                hit_tp = tp_price is not None and h[i] >= tp_price
            else:  # short
                stop_price = entry_fill * (1.0 + sl) if sl is not None else None
                tp_price = entry_fill * (1.0 - tp) if tp is not None else None
                hit_stop = stop_price is not None and h[i] >= stop_price
                hit_tp = tp_price is not None and low[i] <= tp_price
            # Pessimistic: if both could trigger in the same bar, assume stop.
            if hit_stop:
                close_position(stop_price, i, reason="stop")
            elif hit_tp:
                close_position(tp_price, i, reason="take_profit")

        # 3) Max-hold force exit (checked at bar close).
        if side != 0 and max_hold is not None and (i - entry_i) >= max_hold:
            close_position(c[i], i, reason="max_hold")

        # 4) Mark-to-market equity for this bar's close.
        if side != 0:
            gross = side * (c[i] / entry_fill - 1.0)
            equity_curve[i] = entry_equity * (1.0 + gross)
        else:
            equity_curve[i] = realized

        # 5) Decide the target to execute NEXT bar, honouring re-entry blocks.
        want = tgt[i]
        if not config.allow_short and want < 0:
            want = 0
        if want == 0:
            blocked_side = 0            # signal flattened -> clear the block
        elif want == blocked_side:
            want = side                 # stay put; don't re-enter a stopped side
        pending = want

    # Close any position still open at the end of the data.
    if side != 0:
        close_position(c[n - 1], n - 1, reason="end")
        equity_curve[n - 1] = realized

    return BacktestResult(
        strategy_name=strategy_name,
        timeframe=timeframe,
        equity_curve=pd.Series(equity_curve, index=idx, name="equity"),
        trades=trades,
        config=config,
        bars=n,
        start=idx[0] if n else None,
        end=idx[-1] if n else None,
    )
