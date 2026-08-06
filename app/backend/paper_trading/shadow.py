"""Daily proof that the execution path still works.

The problem this solves
-----------------------
On 2026-08-06 the order path was proven end to end against a real matching
engine — and from that moment it starts rotting. Keys expire, permissions get
revoked, Binance changes a filter, a dependency bump breaks the signing code.
None of that announces itself. The strategy trades 1.69 round-trips a *year*, so
the live bot will not exercise the path either: the first order after M6 opens
could be the first order in months, with real money on it.

So this runs a complete round-trip every day — buy, fill, sell, flat, reconcile
— on the demo venue. If anything in that chain breaks, we find out the next
morning for $0, instead of on the day it matters.

Why it does not follow the strategy signal
------------------------------------------
It could: demo carries live prices (verified — same ticker, same kline opens), so
mirroring the production signal would be coherent. But a signal-following shadow
would sit flat for months at a time, which is precisely the situation this exists
to avoid.

So each run is deliberately **self-contained**: it opens and closes within the
same invocation and always ends flat. Nothing to carry, nothing to drift out of
sync with the venue — except the one case where the sell fails, which is exactly
why :meth:`ShadowRunner.run_once` checks for a stranded position first.

The round-trip is driven through a throwaway :class:`PaperPortfolio`, not the
executor alone. That way the daily heartbeat also exercises the book's
**quantity-backed** accounting against real fills — real quantities, venue
prices, and whatever asset the commission happens to arrive in. Without that,
the path M6 depends on would be proven only by tests until the day money rides
on it, which is the same mistake this whole track exists to avoid.

What it costs
-------------
Fake money on a practice venue, and about 4 API calls a day. The real cost is one
Lambda invocation: rounding error against the bot's $0.60/month.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from .binance_demo import BinanceAPIError, BinanceDemoExecutor, OrderTooSmall
from .execution import BUY, SELL, Order
from .portfolio import PaperPortfolio

logger = logging.getLogger(__name__)

#: Partition key for the shadow log. Shares the paper bot's table — same cost,
#: same deletion protection, and a different key keeps the M5 book untouchable.
SHADOW_PK = "SHADOW_{symbol}_{timeframe}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ShadowRunner:
    """Runs one heartbeat round-trip per day and records what the venue did.

    Parameters
    ----------
    executor:
        A live :class:`BinanceDemoExecutor`. Its ``max_notional`` caps the size.
    store:
        Anything with the paper bot's state-store interface (``load``/``save``/
        ``append_decision``/``has_decision``) — the same class, different key.
    """

    def __init__(self, executor: BinanceDemoExecutor, store,
                 symbol: str = "BTCUSDT", timeframe: str = "1d") -> None:
        self.executor = executor
        self.store = store
        self.symbol = symbol
        self.timeframe = timeframe

    # ------------------------------------------------------------------ helpers --
    @staticmethod
    def _day(now: datetime) -> str:
        return now.strftime("%Y-%m-%d")

    def _close_stranded_position(self, state: dict) -> Optional[dict]:
        """Flatten a position a previous run opened but failed to close.

        The one way this runner can leave state behind: the buy filled and the
        sell did not. Retrying the buy on top of that would compound the problem,
        so a stranded position is dealt with *before* anything else — and if it
        cannot be, the run fails loudly rather than trading around it.
        """
        stranded = Decimal(str(state.get("open_qty", 0) or 0))
        if stranded <= 0:
            return None

        logger.warning("found stranded position of %s, closing before anything else",
                       stranded)
        self.executor._position_qty = stranded      # restore what we are holding
        price = self.executor.mark_price()
        fill = self.executor.execute(
            Order(side=SELL, reference_price=price, time=_utc_now().isoformat())
        )
        state["open_qty"] = 0.0
        self.store.save(state)
        return {"recovered_qty": float(stranded), "exit_price": fill.price}

    # --------------------------------------------------------------------- run --
    def run_once(self, now: Optional[datetime] = None, force: bool = False) -> dict:
        """One heartbeat. Idempotent per UTC day unless ``force``.

        Idempotency is not decoration: EventBridge retries a failed invocation
        three times, and without this guard a transient timeout after a filled
        order would place three more round-trips.
        """
        now = now or _utc_now()
        day = self._day(now)

        if not force and self.store.has_decision(day):
            logger.info("heartbeat for %s already recorded, skipping", day)
            return {"status": "already_done", "day": day}

        state = self.store.load() or {"open_qty": 0.0}
        record: dict[str, Any] = {
            "bar": day, "time": now.isoformat(), "symbol": self.symbol,
            "venue": self.executor.base_url, "kind": "heartbeat",
        }

        try:
            recovery = self._close_stranded_position(state)
            if recovery:
                record["recovery"] = recovery

            entry_ref = self.executor.mark_price()
            qty = self.executor.plan_quantity(BUY, entry_ref)

            # Drive the round-trip through a throwaway PaperPortfolio rather
            # than the executor alone. The heartbeat then exercises the
            # QUANTITY-BACKED accounting path with real fills every day —
            # partial quantities, venue prices, whatever asset the commission
            # arrives in — instead of that path only ever being proven by
            # tests until the day M6 depends on it.
            book = PaperPortfolio(fee_rate=0.001,
                                  slippage=self.executor.assumed_slippage,
                                  initial_capital=10_000.0)
            book.set_executor(self.executor)

            book.reconcile(1, entry_ref, now.isoformat())
            entry = self.executor.reconciliations()[-1]
            # Persist immediately: if the sell now fails, the next run must know
            # there is something to flatten.
            state["open_qty"] = float(self.executor.position_qty)
            self.store.save(state)

            exit_ref = self.executor.mark_price()
            book.reconcile(0, exit_ref, now.isoformat())
            exit_rec = self.executor.reconciliations()[-1]
            state["open_qty"] = float(self.executor.position_qty)
            self.store.save(state)

            trade = book.trades[-1] if book.trades else {}
            record.update({
                "status": "ok",
                "planned_qty": float(qty),
                "entry": {"price": entry.actual_price, "qty": entry.qty,
                          "order_id": entry.order_id, "reference": entry_ref},
                "exit": {"price": exit_rec.actual_price, "qty": exit_rec.qty,
                         "order_id": exit_rec.order_id, "reference": exit_ref},
                "fee_paid": entry.fee_paid + exit_rec.fee_paid,
                "fee_asset": entry.fee_asset,
                "slippage": [entry.slippage_actual, exit_rec.slippage_actual],
                "slippage_assumed": self.executor.assumed_slippage,
                "flat": float(self.executor.position_qty) == 0.0,
                # Evidence that the quantity path itself works on live fills.
                "book": {
                    "quantity_backed": book.quantity_backed,
                    "net_return": trade.get("net_return"),
                    "realized": book.realized,
                    "qty_after": book.qty,
                    "fees_quote": book.fees_quote,
                    "fees_external": book.fees_external,
                },
            })
            if not record["flat"]:
                # Loud, not fatal: the position is recorded and the next run
                # clears it, but this must never pass silently as a success.
                record["status"] = "not_flat"
                logger.error("heartbeat finished holding %s — next run will flatten",
                             self.executor.position_qty)

        except OrderTooSmall as exc:
            record.update({"status": "too_small", "error": str(exc)})
            logger.error("cannot size the heartbeat: %s", exc)
        except BinanceAPIError as exc:
            record.update({"status": "venue_error", "error": str(exc),
                           "code": exc.code})
            logger.error("venue rejected the heartbeat: %s", exc)

        self.store.append_decision(record)
        return record


def build_shadow_runner(symbol: str = "BTCUSDT", timeframe: str = "1d",
                        notional: float = 10.0, state_path: str = "data/shadow.json",
                        credentials: Optional[dict] = None) -> ShadowRunner:
    """Wire a runner from the environment, mirroring ``paper_trading.run``."""
    from .state_store import make_state_store

    executor = BinanceDemoExecutor.from_env(
        env=credentials,
        symbol=symbol,
        max_notional=notional,
    )
    store = make_state_store(
        state_path=state_path,
        partition_key=SHADOW_PK.format(symbol=symbol, timeframe=timeframe),
    )
    return ShadowRunner(executor, store, symbol=symbol, timeframe=timeframe)
