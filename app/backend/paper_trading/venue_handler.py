"""AWS Lambda entrypoint for a paper channel whose fills come from a real venue.

What this is
------------
The BTC 1d channel is pure simulation: the strategy decides, and a slippage model
invents the fill. This handler runs the *same* bot, on the *same* validated
strategy, but routes every fill through :class:`BinanceDemoExecutor` — real signed
orders against a real matching engine, with fake money behind them.

Why bother, given 4h is not a shortcut
--------------------------------------
The original case for a 4h channel was "7.2x faster proof". That was **wrong**:
the precision of an annualised Sharpe depends on calendar span, not on how finely
the span is sliced (simulated 2026-08-06 — the ratio is 1.00x, not sqrt(6)).

What survives is the thing 1d can never give us. The live channel produces
1.69 round-trips a *year*; this one produces about twelve. Slippage, fee drag,
partial fills, rounding, and how the book copes with a real fill are exactly the
quantities M6 depends on, they converge with the number of TRADES, and twelve a
year measures them where 1.69 cannot. The shadow bot proves the path still works;
this measures what it costs when a strategy — not a heartbeat — is driving.

The trap this handler exists to avoid
-------------------------------------
``BinanceDemoExecutor`` tracks its position in memory. A Lambda lives for seconds
and this bot may hold for weeks, so a restored bot would try to sell a position
it does not think it has and fail with "nothing to sell" — stranding real coins
with no code able to close them. The book is the cure: ``PaperPortfolio.qty`` is
persisted, so the executor's position is restored from the book on every run.

    PAPER_STATE_BACKEND=dynamodb
    PAPER_STATE_TABLE=tradepulse_paper_bot   # same table, pk = BTCUSDT_4h
    TRADING_SYMBOL=BTCUSDT
    TRADING_TIMEFRAME=4h
    VENUE_MAX_NOTIONAL=200                   # ceiling per order, quote units
    PAPER_CAPITAL=200                        # book capital, kept ~= the ceiling
    SHADOW_CREDENTIALS_PATH=/tradepulse/demo
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from .binance_demo import BinanceDemoExecutor
from .killswitch import KillSwitchState, apply_halt, evaluate, observe
from .run import build_bot
from .shadow_handler import load_credentials_from_ssm

#: Where the kill-switch state lives inside the bot's persisted state.
KILLSWITCH_KEY = "killswitch"

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def attach_venue(bot, executor: BinanceDemoExecutor) -> dict:
    """Wire the executor to the book and restore what it is holding.

    Returns a small reconciliation record. The venue's balance is reported
    alongside the book's position on every run: they should move together, and
    if they ever stop doing so we want the evidence in the log rather than a
    surprise months later.
    """
    executor.set_position(bot.portfolio.qty)
    bot.portfolio.set_executor(executor)

    rules = executor.rules()
    venue_free = float(executor.free_balance(rules.base_asset))
    book_qty = float(bot.portfolio.qty)

    record = {
        "book_qty": book_qty,
        "venue_free_base": venue_free,
        "base_asset": rules.base_asset,
        "venue": executor.base_url,
    }
    # The account is pre-funded with coins this channel never bought, so the two
    # numbers are not expected to be equal — only to move together. A book that
    # thinks it holds more than the account contains is the one impossible case.
    if book_qty > venue_free + float(rules.step_size):
        record["warning"] = (
            f"book holds {book_qty} {rules.base_asset} but the account only has "
            f"{venue_free} free — the exit leg cannot fill"
        )
        logger.error(record["warning"])
    return record


def _execution_drag(executor: BinanceDemoExecutor,
                    switch: KillSwitchState) -> float:
    """Cumulative quote-currency cost of fills landing away from the model.

    This is what T2 watches. It measures the plumbing — execution and costs —
    never the strategy: a strategy that simply loses money must not trip a switch
    meant for broken pipes.
    """
    drag = switch.execution_drag or 0.0
    for rec in executor.reconciliations():
        drag += rec.price_error * rec.qty
    return drag


def handler(event, context):
    symbol = os.environ.get("TRADING_SYMBOL", "BTCUSDT")
    timeframe = os.environ.get("TRADING_TIMEFRAME", "4h")
    max_notional = float(os.environ.get("VENUE_MAX_NOTIONAL", "200"))
    capital = float(os.environ.get("PAPER_CAPITAL", "200"))
    ssm_prefix = os.environ.get("SHADOW_CREDENTIALS_PATH", "/tradepulse/demo")

    credentials = load_credentials_from_ssm(ssm_prefix)
    executor = BinanceDemoExecutor(
        api_key=credentials["BINANCE_DEMO_KEY"],
        api_secret=credentials["BINANCE_DEMO_SECRET"],
        symbol=symbol,
        max_notional=max_notional,
        # The strategy decides on a bar close; the order lands minutes later.
        # Without this the two costs are indistinguishable.
        measure_drift=True,
    )
    executor.sync_time()

    # The book's capital tracks the order ceiling so a "full equity" position in
    # the book maps onto an order of roughly that size at the venue. Let them
    # drift apart and the book would report a strategy sitting 99% in cash.
    bot = build_bot(symbol=symbol, timeframe=timeframe, capital=capital)
    reconciliation = attach_venue(bot, executor)

    # --- kill switch -------------------------------------------------------
    # Checked on the state BEFORE this bar is reconciled, exactly as the design
    # specifies: a switch that evaluates after trading has already happened is
    # not a circuit breaker, it is a post-mortem.
    switch = KillSwitchState.from_dict(bot.extra.get(KILLSWITCH_KEY))
    mark = executor.mark_price()
    equity_now = bot.portfolio.equity(mark)
    drag = _execution_drag(executor, switch)
    verdict = evaluate(switch, equity_now, execution_drag=drag)

    if verdict.halt:
        was_halted = switch.halted
        switch = apply_halt(switch, verdict)
        result = {
            "status": "HALTED",
            "reason": verdict.reason,
            "detail": verdict.detail,
            "equity": round(equity_now, 2),
            "checks": verdict.checks,
            "position": bot.portfolio.side,
        }
        if not was_halted and bot.portfolio.side != 0:
            # Flatten through the ordinary path, then stop. Leaving a position
            # open after halting would mean the switch protects the book but not
            # the money.
            bot.portfolio.reconcile(0, mark, datetime.now(timezone.utc).isoformat())
            result["flattened_at"] = mark
        bot.extra[KILLSWITCH_KEY] = switch.as_dict()
        bot._save()
        logger.error("KILL SWITCH: %s — %s", verdict.reason, verdict.detail)
        result["venue"] = reconciliation
        return result

    result = bot.step()
    observe(switch, bot.portfolio.equity(mark), execution_drag=drag)
    bot.extra[KILLSWITCH_KEY] = switch.as_dict()
    bot._save()
    result["killswitch"] = {"halted": False, **verdict.checks}
    result["venue"] = reconciliation
    if executor.reconciliations():
        last = executor.reconciliations()[-1]
        result["fill"] = {
            "price": last.actual_price,
            "reference": last.reference_price,
            "slippage_total": last.slippage_actual,
            "slippage_execution": last.execution_slippage,
            "drift_decision_to_order": last.drift,
            "mark_at_order": last.mark_at_order,
            "slippage_assumed": last.slippage_assumed,
            "qty": last.qty,
            "fee_paid": last.fee_paid,
            "fee_asset": last.fee_asset,
            "order_id": last.order_id,
        }

    logger.info("venue channel step: %s", json.dumps(result, default=str))
    return result
