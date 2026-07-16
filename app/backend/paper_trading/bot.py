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
        self._load()

    # -- persistence ----------------------------------------------------- #
    def _load(self) -> None:
        state = self.store.load()
        if not state:
            return
        self.portfolio = PaperPortfolio.from_dict(state["portfolio"])
        self.last_bar = state.get("last_bar")

    def _save(self) -> None:
        self.store.save({
            "symbol": self.config.symbol,
            "timeframe": self.config.timeframe,
            "strategy": self.strategy.name,
            "last_bar": self.last_bar,
            "portfolio": self.portfolio.to_dict(),
        })

    # -- run ------------------------------------------------------------- #
    def step(self) -> dict:
        """Process the latest closed bar. Returns a status dict."""
        df = fetch_klines(self.config.symbol, self.config.timeframe,
                          limit=self.config.lookback_bars)
        latest_time = str(df.index[-1])
        latest_price = float(df["close"].iloc[-1])

        if self.last_bar == latest_time:
            return {"status": "skipped", "reason": "bar already processed",
                    "bar": latest_time, "position": self.portfolio.side,
                    "equity": round(self.portfolio.equity(latest_price), 2)}

        target = int(self.strategy.target_positions(df).iloc[-1])
        action = self.portfolio.reconcile(target, latest_price, latest_time)
        self.last_bar = latest_time
        self._save()

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
        # live-vs-paper tracking check.
        try:
            self.store.append_decision({
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
            })
        except Exception as e:  # the log must never break the trading step
            logger.error("Failed to append decision record: %s", e)

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
