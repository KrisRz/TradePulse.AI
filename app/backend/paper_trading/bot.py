"""Paper-trading bot: fetch live bars → strategy signal → reconcile portfolio.

The bot is stateless between runs except for a small JSON state file, so it can
be driven by cron ("run once after each daily close") or a loop. Each ``step``
is idempotent per bar: if the latest closed bar was already processed, it does
nothing — safe to run more often than the bar interval.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..backtesting.strategy import Strategy
from .feed import fetch_klines
from .portfolio import PaperPortfolio

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
        self.portfolio = PaperPortfolio(
            fee_rate=config.fee_rate,
            slippage=config.slippage,
            initial_capital=config.initial_capital,
        )
        self.last_bar: Optional[str] = None
        self._load()

    # -- persistence ----------------------------------------------------- #
    def _load(self) -> None:
        p = Path(self.config.state_path)
        if not p.exists():
            return
        state = json.loads(p.read_text())
        self.portfolio = PaperPortfolio.from_dict(state["portfolio"])
        self.last_bar = state.get("last_bar")

    def _save(self) -> None:
        p = Path(self.config.state_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "symbol": self.config.symbol,
            "timeframe": self.config.timeframe,
            "strategy": self.strategy.name,
            "last_bar": self.last_bar,
            "portfolio": self.portfolio.to_dict(),
        }, indent=2, default=str))

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
