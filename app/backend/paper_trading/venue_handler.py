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

from . import position_risk
from .binance_demo import DEMO_BASE_URL, BinanceDemoExecutor
from .execution import BUY, SELL
from .killswitch import KillSwitchState, apply_halt, evaluate, observe
from .run import build_bot
from .shadow_handler import load_credentials_from_ssm

#: Where the kill-switch state lives inside the bot's persisted state.
KILLSWITCH_KEY = "killswitch"
#: Where the F7 position-risk state lives (docs/F7_POSITION_RISK_2026-08-07.md).
POSITION_RISK_KEY = "position_risk"
#: Where this channel's execution bookkeeping lives — currently the id of the
#: newest venue order the book has accounted for.
VENUE_KEY = "venue"

#: Prefix on every client order id this channel sends. It identifies our orders
#: on an account that also carries the heartbeat's, and it is part of a
#: deterministic id, so changing it would orphan every order already placed.
CLIENT_PREFIX = "tpv4h"
#: How far back to look when the book has no watermark yet (first run only).
SEED_ORDER_PAGE = 50

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class BookOutOfSync(RuntimeError):
    """The account holds something the book does not know about.

    Raised before any decision is taken. A book that is behind the account is
    not a reporting problem: the next target would be computed from a position
    that is not the real one, and the order that followed would be sized against
    a fiction. Stopping is the only safe answer, and it is loud by design — the
    Lambda fails, the errors alarm fires, and a person looks.
    """


def _halt_order_key(bar) -> str:
    """Idempotency key for a kill-switch flatten.

    Deliberately derived from the last processed bar rather than the clock: a
    halt that dies mid-flatten must produce the SAME order id when the run is
    retried, or the retry would sell the position a second time.
    """
    return f"halt@{bar}"


def attach_venue(bot, executor: BinanceDemoExecutor) -> dict:
    """Wire the executor to the book, restore what it holds, and refuse to trade
    on a book the account disagrees with.

    Returns a reconciliation record. Until 2026-09-05 the disagreements were only
    logged, in one direction, which meant the single state that makes an exit
    impossible would have been discovered by the exit failing (audit 2026-09-04,
    HIGH-2). Now every check here is fail-closed: it raises, the invocation
    fails, and the errors alarm mails. Trading through a mismatch is never the
    cheaper option — it is how a book and an account drift apart for months.
    """
    executor.set_position(bot.portfolio.qty)
    bot.portfolio.set_executor(executor)

    rules = executor.rules()
    balances = executor.balances()
    venue_free = float(balances.get(rules.base_asset, 0))
    venue_free_quote = float(balances.get(rules.quote_asset, 0))
    book_qty = float(bot.portfolio.qty)
    book_cash = float(bot.portfolio.cash)

    record = {
        "book_qty": book_qty,
        "venue_free_base": venue_free,
        "book_cash": book_cash,
        "venue_free_quote": venue_free_quote,
        "base_asset": rules.base_asset,
        "quote_asset": rules.quote_asset,
        "venue": executor.base_url,
    }

    # Direction 1 — base asset. The account is pre-funded with coins this channel
    # never bought, so the two numbers are not expected to be equal, only to move
    # together. A book holding more than the account contains is the one
    # impossible case: the exit leg could not fill even in principle.
    if book_qty > venue_free + float(rules.step_size):
        record["error"] = (
            f"book holds {book_qty} {rules.base_asset} but the account only has "
            f"{venue_free} free — the exit leg cannot fill"
        )
        logger.error(record["error"])
        raise BookOutOfSync(record["error"])

    # Direction 2 — quote currency. Inert while sizing comes from the account
    # (the book's cash is presently negative for exactly that reason, audit
    # HIGH-4), and load-bearing the moment a BUY is sized from ``book.cash``:
    # an order the account cannot fund would be rejected mid-decision.
    if book_cash > venue_free_quote + float(rules.min_notional):
        record["error"] = (
            f"book thinks it holds {book_cash} {rules.quote_asset} but the account "
            f"has {venue_free_quote} free — an entry could not be funded"
        )
        logger.error(record["error"])
        raise BookOutOfSync(record["error"])

    record.update(_check_for_unbooked_orders(bot, executor))
    return record


def _explained_client_ids(bot, executor: BinanceDemoExecutor) -> set:
    """Ids whose fills the saved book is already known to contain.

    ``bot.step`` saves the book and ``last_bar`` in one write, after the fill.
    So an order whose id is the one this channel generates for the last bar the
    book processed is, by construction, an order the saved book has booked —
    even if the run later died before writing its evidence to DynamoDB. Anything
    else newer than the watermark has no such explanation.
    """
    last_bar = getattr(bot, "last_bar", None)
    if not last_bar:
        return set()
    keys = (str(last_bar), _halt_order_key(last_bar))
    return {executor.client_order_id(side, key)
            for key in keys for side in (BUY, SELL)}


def _check_for_unbooked_orders(bot, executor: BinanceDemoExecutor) -> dict:
    """Stop if the venue holds one of our fills that the book never recorded.

    The idempotency key closes one half of the duplicate-order failure: the same
    decision cannot be ordered twice. It cannot close the other half — an order
    that filled while the run died before the book was saved. Then the account
    holds a position the book does not know about, the next decision is taken on
    a fiction, and nothing in the system would ever say so (audit 2026-09-04,
    CRITICAL-2). This is the check that turns that into a loud stop.
    """
    state = dict(bot.extra.get(VENUE_KEY) or {})
    watermark = state.get("last_order_id")
    seeding = watermark is None

    if seeding:
        # First run under this check. Everything already on the account is
        # history, reconciled by hand when this shipped, and none of it carries
        # our prefix — so the page is still scanned rather than trusted: an
        # order of OURS here could only come from a run that died before it
        # could save its own watermark.
        seen = executor.orders_since(limit=SEED_ORDER_PAGE)
        floor = 0
    else:
        seen = executor.orders_since(int(watermark))
        floor = int(watermark)

    explained = _explained_client_ids(bot, executor)
    unbooked = [
        o for o in seen
        if int(o.get("orderId", 0)) > floor
        and executor.is_ours(o.get("clientOrderId"))
        and float(o.get("executedQty", 0) or 0) > 0
        and o.get("clientOrderId") not in explained
    ]
    if unbooked:
        listed = ", ".join(f"{o.get('orderId')}/{o.get('clientOrderId')}"
                           for o in unbooked)
        message = (
            f"the venue holds {len(unbooked)} executed order(s) this book never "
            f"recorded ({listed}); refusing to decide on a book that is behind "
            f"the account"
        )
        logger.error(message)
        raise BookOutOfSync(message)

    # Nothing outstanding, so everything up to here is accounted for: carry the
    # watermark forward past the other bots' orders too. Without this it would
    # only move on OUR fills — roughly twice a year — and the scan window would
    # grow to thousands of the heartbeat's orders, eventually past the page the
    # venue will return, which is how a check like this goes quietly blind.
    newest = max([int(o.get("orderId", 0)) for o in seen] + [floor])
    state["last_order_id"] = newest
    if seeding:
        state["seeded_at"] = datetime.now(timezone.utc).isoformat()
        logger.warning("no order watermark in the book — seeding it at %s", newest)
    bot.extra[VENUE_KEY] = state

    record = {"last_order_id": newest}
    if seeding:
        record["watermark_seeded"] = True
    return record


def persist_execution_evidence(bot, executor: BinanceDemoExecutor,
                               attach_record: dict) -> list[dict]:
    """Write this invocation's fills and rejections to the durable store.

    Gate C (docs/VENUE_4H_CHANNEL_2026-08-06.md §2) is decidable after >=20
    fills — about ten months — while the Lambda's log group keeps 30 days.
    Evidence that only exists in CloudWatch would be gone long before the gate
    can be evaluated, so every fill and every venue rejection becomes a
    DynamoDB item next to the decision log.
    """
    recorded_at = datetime.now(timezone.utc).isoformat()
    persisted: list[dict] = []
    common = {
        "symbol": executor.symbol,
        "timeframe": os.environ.get("TRADING_TIMEFRAME", "4h"),
        "recorded_at": recorded_at,
    }

    fills = executor.reconciliations()
    if fills:
        rules = executor.rules()
        venue_free_after = float(executor.free_balance(rules.base_asset))
        for rec in fills:
            record = {
                **rec.as_dict(),
                **common,
                "bar": rec.time,
                "book_qty_after": float(bot.portfolio.qty),
                "venue_free_base_before": attach_record.get("venue_free_base"),
                "venue_free_base_after": venue_free_after,
                "base_asset": rules.base_asset,
                "step_size": float(rules.step_size),
                # The before/after balance pair brackets the whole invocation,
                # so it can only be pinned to a single fill when there was
                # exactly one. More than one per run cannot happen for a
                # long-only single leg, but the evaluator must not guess.
                "venue_delta_attributable": len(fills) == 1,
            }
            bot.store.append_fill(record)
            persisted.append(record)

        # Advance the watermark together with the book. Without this the orders
        # this very run placed would read as orphans on the next invocation.
        # It is only a cheap filter for the ``allOrders`` query — correctness
        # rests on ``_explained_client_ids``, which needs no bookkeeping at all.
        booked = [int(rec.order_id) for rec in fills if str(rec.order_id).isdigit()]
        if booked:
            state = dict(bot.extra.get(VENUE_KEY) or {})
            state["last_order_id"] = max(booked + [int(state.get("last_order_id") or 0)])
            bot.extra[VENUE_KEY] = state

    for rej in executor.rejections():
        bot.store.append_rejection({**rej, **common})
    return persisted


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
    # Its own SSM prefix, falling back to the shared one until the separate
    # parameters exist. Two channels reading one credential means one leaked key
    # is two compromised bots, and it is the live path that inherits this
    # arrangement (audit 2026-09-04, HIGH-3).
    ssm_prefix = (os.environ.get("VENUE_CREDENTIALS_PATH")
                  or os.environ.get("SHADOW_CREDENTIALS_PATH")
                  or "/tradepulse/demo")

    credentials = load_credentials_from_ssm(ssm_prefix)
    executor = BinanceDemoExecutor(
        api_key=credentials["BINANCE_API_KEY"],
        api_secret=credentials["BINANCE_API_SECRET"],
        symbol=symbol,
        # The venue is configuration, not a constant: this handler is the one
        # that will point at a live endpoint one day, and that must be a deploy
        # rather than an edit to a module called "demo".
        base_url=os.environ.get("BINANCE_BASE_URL", DEMO_BASE_URL),
        max_notional=max_notional,
        client_prefix=CLIENT_PREFIX,
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
        bot.extra[KILLSWITCH_KEY] = switch.as_dict()
        # The halt is persisted BEFORE any order goes out. If the flatten below
        # dies in flight, the next invocation must already know this channel is
        # halted rather than re-deciding as though nothing had happened
        # (audit 2026-09-04, MEDIUM-4).
        bot._save()
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
            # the money. The order key is the halt, not the clock, so a retried
            # halt asks the venue about the same order instead of selling twice.
            try:
                bot.portfolio.reconcile(0, mark, datetime.now(timezone.utc).isoformat(),
                                        order_key=_halt_order_key(bot.last_bar))
            finally:
                persist_execution_evidence(bot, executor, reconciliation)
                bot._save()
            result["flattened_at"] = mark
        logger.error("KILL SWITCH: %s — %s", verdict.reason, verdict.detail)
        result["venue"] = reconciliation
        return result

    # --- F7 position risk (stop-loss + daily loss limit) -------------------
    # Runs AFTER the kill switch (which halts everything) and INSIDE the
    # ordinary step: the overlay sees the strategy's target before the book
    # reconciles it. State mutates in bot.extra, so bot.step()'s _save()
    # persists it atomically with last_bar. Fail-closed: an overlay exception
    # kills the run before any trade.
    risk_state = position_risk.PositionRiskState.from_dict(
        bot.extra.get(POSITION_RISK_KEY))
    # Events describe THIS run only; without this a skipped (already-processed)
    # bar would echo the previous run's events into the result.
    risk_state.last_events = []

    def overlay(target, portfolio, price, bar_time):
        allowed = position_risk.apply(risk_state, target, portfolio, price, bar_time)
        bot.extra[POSITION_RISK_KEY] = risk_state.as_dict()
        for event in risk_state.last_events:
            logger.warning("position risk: %s", event)
        return allowed

    bot.target_overlay = overlay

    try:
        result = bot.step()
    finally:
        # Evidence outlives the run: a fill that happened before a crash moved
        # real coins, and a venue rejection is exactly what C3 counts.
        persist_execution_evidence(bot, executor, reconciliation)
    if risk_state.last_events:
        result["position_risk"] = risk_state.last_events
    # Recomputed AFTER the step, never before it: a drag that still excluded this
    # run's own fill can never accumulate, which is exactly why T2 read 0.0 on
    # production after three real fills (audit 2026-09-04, HIGH-1).
    observe(switch, bot.portfolio.equity(mark),
            execution_drag=_execution_drag(executor, switch))
    bot.extra[KILLSWITCH_KEY] = switch.as_dict()
    bot._save()
    result["killswitch"] = {"halted": False, **verdict.checks,
                            "execution_drag": switch.execution_drag}
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
