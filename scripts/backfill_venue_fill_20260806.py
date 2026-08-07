"""One-time backfill: the first venue-channel fill, from CloudWatch into DynamoDB.

Why this exists
---------------
Durable fill persistence (Gate C evidence) shipped on 2026-08-07, but the
channel's first real fill happened on 2026-08-06 — order ``54510109086``, the
BUY that opened the position the book is still holding. Its only record lives
in the Lambda's CloudWatch log group, which keeps 30 days; without this
backfill the fill would evaporate from the sample months before Gate C's
20-fill minimum is reached.

Every value below is copied verbatim from the log line of invocation
``910072f9-019d-43b1-89c3-6e9234038e74`` (2026-08-06T21:11:41Z). Fields the
old handler did not measure are stored as None, NOT reconstructed: the
deployed code predated the drift/slippage split, so ``mark_at_order`` was
never observed and this fill is honestly unverifiable for C1/C2. The second
order of that day (``54508851440``) is deliberately NOT backfilled — it was a
local verification round-trip outside this book's history.

Idempotent: the fill's sort key embeds the order id, so re-running overwrites
the same item.

Usage:
    python -m scripts.backfill_venue_fill_20260806            # writes
    python -m scripts.backfill_venue_fill_20260806 --dry-run  # prints only
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from app.backend.paper_trading.state_store import DynamoDBStateStore

TABLE = "tradepulse_paper_bot"
PK = "BTCUSDT_4h"

FILL = {
    # --- copied from the CloudWatch log line, verbatim -------------------- #
    "bar": "2026-08-06 16:00:00+00:00",
    "time": "2026-08-06 16:00:00+00:00",
    "side": 1,
    "reference_price": 64446.0,
    "actual_price": 64474.17,
    "slippage_assumed": 0.0002,
    "slippage_actual": 0.00043711013872083093,
    "qty": 0.0031,
    "requested_qty": 0.0031,          # "submitting BUY 0.0031 BTCUSDT"
    "fee_paid": 0.00025326,
    "fee_asset": "BNB",
    "order_id": "54510109086",
    "status": "FILLED",               # executed == submitted quantity
    "venue_free_base_before": 0.05,   # "venue_free_base": 0.05 in the same line
    # --- derived exactly as the executor derives them --------------------- #
    "assumed_price": 64446.0 * (1.0 + 0.0002),
    "price_error": 64474.17 - 64446.0 * (1.0 + 0.0002),
    # --- not measured by the deployed (pre-drift-split) handler ----------- #
    "mark_at_order": None,
    "drift": None,
    "execution_slippage": None,
    "fill_count": None,
    "venue_free_base_after": None,
    "venue_delta_attributable": False,
    # --- context ----------------------------------------------------------- #
    "symbol": "BTCUSDT",
    "timeframe": "4h",
    "book_qty_after": 0.0031,
    "base_asset": "BTC",
    "step_size": 0.00001,
    "backfilled_from": ("cloudwatch:/aws/lambda/tradepulse-venue-4h "
                        "910072f9-019d-43b1-89c3-6e9234038e74"),
}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    record = {**FILL, "recorded_at": datetime.now(timezone.utc).isoformat()}
    print(json.dumps(record, indent=2, default=str))
    if args.dry_run:
        print("dry run — nothing written")
        return
    DynamoDBStateStore(TABLE, PK).append_fill(record)
    print(f"written: pk={PK} sk=fill#{record['bar']}#{record['order_id']}")


if __name__ == "__main__":
    main()
