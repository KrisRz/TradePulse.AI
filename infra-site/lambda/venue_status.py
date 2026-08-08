"""Read-only public status for the portfolio site.

Deliberately standalone: it shares no code with `app/backend/paper_trading`,
which is frozen for the M5 evaluation window. It only ever reads DynamoDB, so
it cannot affect what the bots do. Pure boto3 — no pandas layer needed.

Serves three bots at once, because the system genuinely has three:
  BTCUSDT_4h         — the one that executes on the Binance demo venue
  BTCUSDT_1d         — the paper bot, pure accounting, no venue
  SHADOW_BTCUSDT_1d  — daily micro round-trips that measure venue behaviour

Equity is returned as its parts (cash + qty) rather than a single number, so
the page can mark it to the live price instead of the last bar's close.
"""

from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

TABLE = os.environ.get("TABLE_NAME", "tradepulse_paper_bot")
VENUE_PK = "BTCUSDT_4h"
PAPER_PK = "BTCUSDT_1d"
SHADOW_PK = "SHADOW_BTCUSDT_1d"

# Gate C needs 20 observed fills before execution quality can be judged.
GATE_REQUIRED = 20

POS_LABEL = {1: "LONG", 0: "FLAT", -1: "SHORT"}


def _plain(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        f = float(obj)
        return int(f) if f.is_integer() else f
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_plain(v) for v in obj]
    return obj


def _table():
    return boto3.resource("dynamodb").Table(TABLE)


def _state(table, pk: str) -> dict:
    item = table.get_item(Key={"pk": pk, "sk": "state"}).get("Item") or {}
    return _plain(item)


def _query(table, pk: str, prefix: str, limit: int, newest_first: bool = True) -> list:
    res = table.query(
        KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with(prefix),
        ScanIndexForward=not newest_first,
        Limit=limit,
    )
    return [_plain(i) for i in res.get("Items", [])]


def _venue(table) -> dict:
    item = _state(table, VENUE_PK)
    st = item.get("state") or {}
    port = st.get("portfolio") or {}
    extra = st.get("extra") or {}
    kill = extra.get("killswitch") or {}
    risk = extra.get("position_risk") or {}

    side = int(port.get("side") or 0)
    return {
        "symbol": st.get("symbol"),
        "timeframe": st.get("timeframe"),
        "strategy": st.get("strategy"),
        "position": side,
        "position_label": POS_LABEL.get(side, "?"),
        # parts, so the browser can mark to the live price
        "cash": port.get("cash"),
        "qty": port.get("qty"),
        "initial_capital": port.get("initial_capital"),
        "last_price": port.get("last_price"),
        "entry_time": port.get("entry_time"),
        "entry_fill": port.get("entry_fill"),
        "closed_trades": len(port.get("trades") or []),
        "fees_external": port.get("fees_external") or {},
        "last_bar": st.get("last_bar"),
        "updated_at": item.get("updated_at"),
        "killswitch": {
            "halted": bool(kill.get("halted")),
            "halt_reason": kill.get("halt_reason"),
            "peak_equity": kill.get("peak_equity"),
            "start_equity": kill.get("start_equity"),
        },
        "risk": {
            "stop_blocked": bool(risk.get("stop_blocked")),
            "daily_blocked": bool(risk.get("daily_blocked")),
            "day_start_equity": risk.get("day_start_equity"),
        },
    }


def _fills(table) -> list:
    rows = _query(table, VENUE_PK, "fill#", 20)
    out = []
    for f in rows:
        out.append({
            "order_id": f.get("order_id"),
            "time": f.get("time") or f.get("bar"),
            "status": f.get("status"),
            "side": f.get("side"),
            "qty": f.get("qty"),
            "actual_price": f.get("actual_price"),
            "assumed_price": f.get("assumed_price"),
            "reference_price": f.get("reference_price"),
            "slippage_assumed": f.get("slippage_assumed"),
            "slippage_actual": f.get("slippage_actual"),
            "fee_paid": f.get("fee_paid"),
            "fee_asset": f.get("fee_asset"),
        })
    return out


def _paper(table) -> dict:
    item = _state(table, PAPER_PK)
    st = item.get("state") or {}
    port = st.get("portfolio") or {}
    initial = port.get("initial_capital") or 0
    realized = port.get("realized")
    return {
        "position": int(port.get("side") or 0),
        "position_label": POS_LABEL.get(int(port.get("side") or 0), "?"),
        "equity": realized,
        "initial_capital": initial,
        "closed_trades": len(port.get("trades") or []),
        "last_bar": st.get("last_bar"),
        "updated_at": item.get("updated_at"),
    }


def _decisions(table) -> list:
    rows = _query(table, VENUE_PK, "decision#", 30)
    out = []
    for d in rows:
        action = d.get("action")
        if not action:
            label = "HOLD"
        else:
            label = "BUY" if (action.get("to") or 0) > (action.get("from") or 0) else "SELL"
        out.append({
            "bar": d.get("bar"),
            "price": d.get("price"),
            "action": label,
            "position": d.get("position"),
            "equity": d.get("equity"),
        })
    return out


def handler(event, context):
    table = _table()
    shadow = _query(table, SHADOW_PK, "decision#", 30)
    fills = _fills(table)

    body = {
        "venue": _venue(table),
        "fills": fills,
        "gate": {"collected": len(fills), "required": GATE_REQUIRED},
        "paper": _paper(table),
        "shadow": {
            "probes": len(shadow),
            "last_bar": shadow[0].get("bar") if shadow else None,
        },
        "decisions": _decisions(table),
    }

    return {
        "statusCode": 200,
        "headers": {
            "content-type": "application/json",
            # served same-origin through CloudFront, but harmless and useful
            "access-control-allow-origin": "*",
            "cache-control": "public, max-age=30",
        },
        "body": json.dumps(body, default=str),
    }
