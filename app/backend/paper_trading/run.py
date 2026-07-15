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


def build_bot(args) -> PaperBot:
    # Default = the walk-forward-validated edge: long-only EMA trend-following.
    strategy = EmaCrossover(fast=args.fast, slow=args.slow, allow_short=False)
    config = BotConfig(
        symbol=args.symbol,
        timeframe=args.timeframe,
        fee_rate=args.fee,
        slippage=args.slippage,
        initial_capital=args.capital,
        state_path=args.state or f"paper_state/{args.symbol}_{args.timeframe}.json",
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

    bot = build_bot(args)
    result = bot.step() if args.command == "step" else bot.status()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
