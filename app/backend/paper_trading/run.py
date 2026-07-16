"""CLI for the paper-trading bot.

Examples
--------
    # Process the latest closed daily bar (run this once a day, e.g. via cron)
    python -m app.backend.paper_trading.run step

    # Show current portfolio status without trading
    python -m app.backend.paper_trading.run status
"""

from __future__ import annotations

import argparse
import json
import logging

from ..backtesting.strategies import EmaCrossover
from .bot import BotConfig, PaperBot


def build_bot(symbol: str = "BTCUSDT", timeframe: str = "1d",
              fast: int = 20, slow: int = 100, fee: float = 0.001,
              slippage: float = 0.0002, capital: float = 10_000.0,
              state: str | None = None) -> PaperBot:
    # Default = the walk-forward-validated edge: long-only EMA trend-following.
    strategy = EmaCrossover(fast=fast, slow=slow, allow_short=False)
    config = BotConfig(
        symbol=symbol,
        timeframe=timeframe,
        fee_rate=fee,
        slippage=slippage,
        initial_capital=capital,
        state_path=state or f"paper_state/{symbol}_{timeframe}.json",
    )
    return PaperBot(strategy, config)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Paper-trading bot (backtest-validated strategy).")
    p.add_argument("command", choices=["step", "status"])
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--timeframe", default="1d")
    p.add_argument("--fast", type=int, default=20)
    p.add_argument("--slow", type=int, default=100)
    p.add_argument("--fee", type=float, default=0.001)
    p.add_argument("--slippage", type=float, default=0.0002)
    p.add_argument("--capital", type=float, default=10_000.0)
    p.add_argument("--state", default=None, help="Path to state JSON")
    args = p.parse_args(argv)

    bot = build_bot(symbol=args.symbol, timeframe=args.timeframe,
                    fast=args.fast, slow=args.slow, fee=args.fee,
                    slippage=args.slippage, capital=args.capital,
                    state=args.state)
    result = bot.step() if args.command == "step" else bot.status()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
