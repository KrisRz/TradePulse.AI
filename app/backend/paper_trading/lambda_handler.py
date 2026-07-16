"""AWS Lambda entrypoint for the paper bot (M2/E4).

EventBridge Scheduler invokes this once per day after the 1d close.
Configuration comes from the environment:
    PAPER_STATE_BACKEND=dynamodb
    PAPER_STATE_TABLE=tradepulse_paper_bot
    TRADING_SYMBOL / TRADING_TIMEFRAME (optional, default BTCUSDT 1d)

Dependencies: numpy/pandas from the AWS managed pandas layer, requests
vendored in the zip, boto3 from the runtime. No TF/DynamoDB-monolith
imports — the paper_trading + backtesting packages are dependency-light
by design.
"""

from __future__ import annotations

import json
import logging
import os

from .run import build_bot

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    symbol = os.environ.get("TRADING_SYMBOL", "BTCUSDT")
    timeframe = os.environ.get("TRADING_TIMEFRAME", "1d")

    bot = build_bot(symbol=symbol, timeframe=timeframe)
    result = bot.step()

    logger.info("paper bot step: %s", json.dumps(result, default=str))
    return result
