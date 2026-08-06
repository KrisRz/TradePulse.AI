"""Paper-trading bot: fetch live bars → strategy signal → reconcile portfolio.

The bot is stateless between runs except for a small JSON state file, so it can
be driven by cron ("run once after each daily close") or a loop. Each ``step``
is idempotent per bar: if the latest closed bar was already processed, it does
nothing — safe to run more often than the bar interval.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from ..backtesting.strategy import Strategy
from .feed import fetch_klines
from .portfolio import PaperPortfolio
from .state_store import make_state_store

logger = logging.getLogger("paper_bot")


@dataclass
class BotConfig:
    symbol: str = "BTCUSDT"
    timeframe: str = "1d"
    fee_rate: float = 0.001
    slippage: float = 0.0002
    initial_capital: float = 10_000.0
    lookback_bars: int = 400
    state_path: str = "paper_state/BTCUSDT_1d.json"


class PaperBot:
    def __init__(self, strategy: Strategy, config: BotConfig) -> None:
        self.strategy = strategy
        self.config = config
        self.store = make_state_store(
            config.state_path, f"{config.symbol}_{config.timeframe}")
        self.portfolio = PaperPortfolio(
            fee_rate=config.fee_rate,
            slippage=config.slippage,
            initial_capital=config.initial_capital,
        )
        self.last_bar: Optional[str] = None
        self.last_decision: Optional[dict] = None
        # Somewhere for a channel to persist state of its own beside the book,
        # without every channel's concerns leaking into this class. The kill
        # switch lives here for the venue-backed channel; the 1d bot never
        # writes it and loading a state without it is a no-op.
        self.extra: dict = {}
        self._load()

    # -- persistence ----------------------------------------------------- #
    def _load(self) -> None:
        state = self.store.load()
        if not state:
            return
        self.portfolio = PaperPortfolio.from_dict(state["portfolio"])
        self.last_bar = state.get("last_bar")
        self.last_decision = state.get("last_decision")
        self.extra = state.get("extra") or {}

    def _save(self) -> None:
        self.store.save({
            "symbol": self.config.symbol,
            "timeframe": self.config.timeframe,
            "strategy": self.strategy.name,
            "last_bar": self.last_bar,
            "last_decision": self.last_decision,
            "portfolio": self.portfolio.to_dict(),
            "extra": self.extra,
        })

    def _heal_decision_log(self) -> bool:
        """Re-append the last decision if a crash lost it after the state save."""
        rec = self.last_decision
        if not rec or self.store.has_decision(str(rec.get("bar", ""))):
            return False
        self.store.append_decision(rec)
        return True

    # -- run ------------------------------------------------------------- #
    def step(self) -> dict:
        """Process the latest closed bar. Returns a status dict."""
        df = fetch_klines(self.config.symbol, self.config.timeframe,
                          limit=self.config.lookback_bars)
        # Binance returns `limit` klines including the still-open one we drop.
        # A shorter response means truncated history: the EMAs would differ
        # from the backtest and the zeroed warmup could force-flatten a live
        # position — refuse loudly so the run is retried/alarmed instead.
        min_bars = self.config.lookback_bars - 1
        if len(df) < min_bars:
            raise RuntimeError(
                f"Feed returned {len(df)} closed bars, expected >= {min_bars} "
                f"— refusing to trade on truncated history")
        latest_time = str(df.index[-1])
        latest_price = float(df["close"].iloc[-1])

        if self.last_bar == latest_time:
            out = {"status": "skipped", "reason": "bar already processed",
                   "bar": latest_time, "position": self.portfolio.side,
                   "equity": round(self.portfolio.equity(latest_price), 2)}
            if self._heal_decision_log():
                out["decision_backfilled"] = True
            return out

        target = int(self.strategy.target_positions(df).iloc[-1])
        action = self.portfolio.reconcile(target, latest_price, latest_time)

        status = {
            "status": "traded" if action else "held",
            "bar": latest_time,
            "price": latest_price,
            "target": target,
            "position": self.portfolio.side,
            "equity": round(self.portfolio.equity(latest_price), 2),
            "total_return_pct": round(self.portfolio.total_return(latest_price) * 100, 2),
            "trades": len(self.portfolio.trades),
        }

        # One decision record per processed bar — the raw data for the M5
        # gate metrics (Sharpe/DD/profit factor/net P&L/fee drag) and the
        # live-vs-paper tracking check. It is load-bearing: the record is
        # persisted inside the state (atomically with last_bar), the append
        # is allowed to raise (-> Lambda error -> alarm), and a lost append
        # is healed by the skipped path on the next run. Silent gaps here
        # would corrupt the gate metrics.
        record = {
            "bar": latest_time,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "symbol": self.config.symbol,
            "timeframe": self.config.timeframe,
            "strategy": self.strategy.name,
            "price": latest_price,
            "target": target,
            "action": action,
            "position": self.portfolio.side,
            "equity": status["equity"],
            "realized": round(self.portfolio.realized, 2),
            "total_return_pct": status["total_return_pct"],
            "trades_count": status["trades"],
            "fee_rate": self.config.fee_rate,
            "slippage": self.config.slippage,
        }
        self.last_bar = latest_time
        self.last_decision = record
        self._save()
        self.store.append_decision(record)

        if action:
            logger.info("Paper trade: %s -> %s @ %.2f (%s)",
                        action["from"], action["to"], action["price"], latest_time)
        return status

    def status(self) -> dict:
        return {
            "symbol": self.config.symbol,
            "timeframe": self.config.timeframe,
            "strategy": self.strategy.name,
            "last_bar": self.last_bar,
            "position": self.portfolio.side,
            "equity": round(self.portfolio.equity(), 2),
            "total_return_pct": round(self.portfolio.total_return() * 100, 2),
            "trades": len(self.portfolio.trades),
        }
