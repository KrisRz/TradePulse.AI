#!/usr/bin/env python3
"""
Backfill missing position_type in portfolio_closed_positions.

Logic:
- If position_type already present: skip
- Else infer:
  1) From ai_reasoning text: contains 'SHORT'/'SELL' -> SHORT; 'LONG'/'BUY' -> LONG
  2) Else from price relation and realized_pnl sign:
     - If (exit_price - entry_price) and realized_pnl share sign -> LONG
     - Else -> SHORT

Runs against DynamoDB Local when DYNAMODB_ENDPOINT is set; otherwise uses default client.
"""

import os
import sys
import re
from decimal import Decimal
from typing import Optional

from app.backend.core.database import DynamoDBClient


def infer_position_type(
    ai_reasoning: Optional[str],
    entry_price: Optional[Decimal],
    exit_price: Optional[Decimal],
    realized_pnl: Optional[Decimal],
) -> Optional[str]:
    """Infer LONG/SHORT from reasoning text or price/PnL relationship."""
    text = (ai_reasoning or "").upper()
    if any(tok in text for tok in ("SHORT", "SELL")):
        return "SHORT"
    if any(tok in text for tok in ("LONG", "BUY")):
        return "LONG"

    try:
        if entry_price is None or exit_price is None or realized_pnl is None:
            return None
        entry = Decimal(str(entry_price))
        exit_ = Decimal(str(exit_price))
        pnl = Decimal(str(realized_pnl))

        price_delta = exit_ - entry
        # If price moved up and PnL is positive -> LONG; if moved down and PnL is positive -> SHORT
        if price_delta >= 0 and pnl >= 0:
            return "LONG"
        if price_delta < 0 and pnl < 0:
            return "LONG"
        return "SHORT"
    except Exception:
        return None


def main() -> int:
    # Prefer local endpoint for safety in dev
    os.environ.setdefault("ENVIRONMENT", "development")
    # Do not override DYNAMODB_ENDPOINT if user already configured one
    # When running in AWS, this stays unset and client will use IAM creds

    client = DynamoDBClient()
    table = client.get_table("portfolio_closed_positions")

    print("\n🔍 Scanning portfolio_closed_positions for missing position_type...")
    items = client.scan_table("portfolio_closed_positions")

    total = len(items)
    missing = 0
    updated = 0
    long_count = 0
    short_count = 0

    for item in items:
        pt = item.get("position_type")
        if isinstance(pt, str) and pt.strip():
            if pt.upper() == "LONG":
                long_count += 1
            elif pt.upper() == "SHORT":
                short_count += 1
            continue

        missing += 1

        inferred = infer_position_type(
            ai_reasoning=item.get("ai_reasoning"),
            entry_price=item.get("entry_price"),
            exit_price=item.get("exit_price"),
            realized_pnl=item.get("realized_pnl"),
        )

        if inferred is None:
            # Last resort: try pnl_percentage and prices if present
            try:
                entry = Decimal(str(item.get("entry_price", 0)))
                exit_ = Decimal(str(item.get("exit_price", entry)))
                pnl_pct = Decimal(str(item.get("pnl_percentage", 0)))
                price_delta = exit_ - entry
                if price_delta >= 0 and pnl_pct >= 0:
                    inferred = "LONG"
                elif price_delta < 0 and pnl_pct < 0:
                    inferred = "LONG"
                else:
                    inferred = "SHORT"
            except Exception:
                inferred = None

        if inferred is None:
            # Skip if cannot infer reliably
            continue

        # Update item
        key = {"user_id": item["user_id"], "position_id": item["position_id"]}
        try:
            table.update_item(
                Key=key,
                UpdateExpression="SET position_type = :pt",
                ExpressionAttributeValues={":pt": inferred},
            )
            updated += 1
            if inferred == "LONG":
                long_count += 1
            else:
                short_count += 1
        except Exception as e:
            print(f"❌ Failed to update {key}: {e}")

    print("\n📊 Backfill Summary")
    print(f"  Total items:            {total}")
    print(f"  Missing before:         {missing}")
    print(f"  Updated now:            {updated}")
    print(f"  LONG count (post):      {long_count}")
    print(f"  SHORT count (post):     {short_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())


