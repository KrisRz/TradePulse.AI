"""AWS Lambda entrypoint for the Kraken paper channel (2026-10-30).

What this is
------------
The bot that will trade real money on Kraken, run first on paper: Kraken's own
XBT/GBP daily candles, Kraken's taker fee, half the account in the position with
the rebalance band, F7 and the account kill switch. Every rule here was fixed
before any of it ran — docs/KRAKEN_PILOT_PREREGISTRATION_2026-10-30.md and
docs/KRAKEN_SIZING_RESULTS_2026-10-30.md. The pilot starts only when this
channel meets P1–P4 (KRAKEN.md).

How the kill switch differs from the venue channel's
----------------------------------------------------
The venue channel checks the switch before the bar and flattens outside the
decision log, because a real order is at stake. Here nothing leaves the book, so
the switch runs inside the target overlay instead: evaluated on this bar's price
before the book reconciles, a halt simply turns the target to 0. The flatten is
then an ordinary decision record, and Gate A's replay of the log still adds up.

    PAPER_STATE_BACKEND=dynamodb
    PAPER_STATE_TABLE=tradepulse_paper_bot   # pk = XBTGBP_1d
    TRADING_SYMBOL=XBTGBP
    PAPER_CAPITAL=200
    HEALTHCHECK_PARAM=/tradepulse/healthcheck/paper-kraken   # optional
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from . import deadman, position_risk
from .killswitch import KillSwitchState, apply_halt, evaluate, observe
from .run import build_bot

#: Same keys as the venue channel, so ``run.py rearm`` works here unchanged.
KILLSWITCH_KEY = "killswitch"
POSITION_RISK_KEY = "position_risk"

#: Pre-registered (docs/KRAKEN_PILOT_PREREGISTRATION_2026-10-30.md). Changing one
#: is a new pre-registration, never a runtime knob.
TIMEFRAME = "1d"
FEE_RATE = 0.008            # Kraken taker, lowest tier
SLIPPAGE = 0.0002           # measured book cost is ~0.2 bps; kept at the model's 2 bps
EXPOSURE = 0.5
REBALANCE_BAND = 0.15
MIN_REBALANCE = 5.0         # GBP; Kraken minimum is 0.00006 BTC (~£3.5)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _healthcheck_url(param: str) -> Optional[str]:
    """The dead-man URL from SSM, or None. Missing must never stop the bot."""
    if not param:
        return None
    try:
        import boto3  # provided by the Lambda runtime

        resp = boto3.client("ssm").get_parameter(Name=param, WithDecryption=True)
        return resp["Parameter"]["Value"]
    except Exception as exc:  # noqa: BLE001 - monitoring must not become an outage
        logger.warning("dead-man URL unavailable (%s): %s", param, exc)
        return None


def build_kraken_bot(capital: float, symbol: str = "XBTGBP"):
    return build_bot(symbol=symbol, timeframe=TIMEFRAME, fee=FEE_RATE,
                     slippage=SLIPPAGE, capital=capital, source="kraken",
                     exposure=EXPOSURE, rebalance_band=REBALANCE_BAND,
                     min_rebalance=MIN_REBALANCE)


def run_step(bot) -> dict:
    """One daily step with the kill switch and F7 in front of the book."""
    switch = KillSwitchState.from_dict(bot.extra.get(KILLSWITCH_KEY))
    risk_state = position_risk.PositionRiskState.from_dict(bot.extra.get(POSITION_RISK_KEY))
    risk_state.last_events = []
    seen: dict = {}

    def overlay(target, portfolio, price, bar_time):
        equity = portfolio.equity(price)
        verdict = evaluate(switch, equity)
        if verdict.halt:
            if not switch.halted:
                logger.error("KILL SWITCH: %s — %s", verdict.reason, verdict.detail)
            apply_halt(switch, verdict)
            bot.extra[KILLSWITCH_KEY] = switch.as_dict()
            seen["halt"] = verdict
            return 0
        allowed = position_risk.apply(risk_state, target, portfolio, price, bar_time)
        bot.extra[POSITION_RISK_KEY] = risk_state.as_dict()
        for event in risk_state.last_events:
            logger.warning("position risk: %s", event)
        seen["price"] = price
        return allowed

    bot.target_overlay = overlay
    result = bot.step()

    if "halt" in seen:
        verdict = seen["halt"]
        result["status"] = "HALTED"
        result["killswitch"] = {"halted": True, "reason": verdict.reason,
                                "detail": verdict.detail}
        bot._save()
        return result

    if "price" in seen:
        # Folded in AFTER the book traded, as on the venue channel: the peak and
        # the previous-bar equity describe the book that now exists.
        observe(switch, bot.portfolio.equity(seen["price"]))
        bot.extra[KILLSWITCH_KEY] = switch.as_dict()
        bot._save()
        result["killswitch"] = {"halted": False,
                                "peak_equity": switch.peak_equity}
    if risk_state.last_events:
        result["position_risk"] = risk_state.last_events
    return result


def handler(event, context):
    capital = float(os.environ.get("PAPER_CAPITAL", "200"))
    symbol = os.environ.get("TRADING_SYMBOL", "XBTGBP")
    healthcheck_url = _healthcheck_url(os.environ.get("HEALTHCHECK_PARAM", ""))

    bot = build_kraken_bot(capital, symbol)
    result = run_step(bot)

    halted = result.get("status") == "HALTED" or \
        KillSwitchState.from_dict(bot.extra.get(KILLSWITCH_KEY)).halted
    # The ping means "this run completed"; a halted channel reports failure on
    # every run until a person re-arms it.
    deadman.ping(healthcheck_url, failed=halted)
    logger.info("kraken paper step: %s", json.dumps(result, default=str))
    return result
