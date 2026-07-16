"""Read-only status endpoint for the paper bot (❓D7: minimal dashboard).

A separate Lambda (same zip as the bot) behind a public function URL.
Serves paper-trading state from DynamoDB — no secrets, no write access:
    GET /            → small self-contained HTML dashboard
    GET /?format=json → raw JSON (state + recent decisions)

Deliberately NOT the monolith frontend: one user, one strategy, ~$0/mo.
"""

from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

TABLE = os.environ.get("PAPER_STATE_TABLE", "tradepulse_paper_bot")
PK = os.environ.get("PAPER_STATE_PK", "BTCUSDT_1d")


def _plain(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        f = float(obj)
        return int(f) if f.is_integer() else f
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_plain(v) for v in obj]
    return obj


def _fetch() -> dict:
    table = boto3.resource("dynamodb").Table(TABLE)
    state_item = table.get_item(Key={"pk": PK, "sk": "state"}).get("Item") or {}
    decisions = table.query(
        KeyConditionExpression=Key("pk").eq(PK) & Key("sk").begins_with("decision#"),
        ScanIndexForward=False,
        Limit=30,
    ).get("Items", [])
    state = _plain(state_item.get("state") or {})
    portfolio = state.get("portfolio", {})
    equity = portfolio.get("realized", 0.0)
    initial = portfolio.get("initial_capital", 10_000.0)
    return {
        "symbol": state.get("symbol", PK),
        "strategy": state.get("strategy"),
        "last_bar": state.get("last_bar"),
        "position": portfolio.get("side", 0),
        "equity": round(equity, 2),
        "total_return_pct": round((equity / initial - 1) * 100, 2) if initial else 0.0,
        "trades": portfolio.get("trades", []),
        "recent_decisions": [_plain(d) for d in decisions],
        "updated_at": state_item.get("updated_at"),
    }


def _html(data: dict) -> str:
    pos = {1: "LONG", 0: "FLAT", -1: "SHORT"}.get(int(data["position"]), "?")
    ret = data["total_return_pct"]
    ret_color = "#16a34a" if ret >= 0 else "#dc2626"
    rows = "".join(
        f"<tr><td>{d.get('bar','')[:10]}</td><td>{d.get('price','')}</td>"
        f"<td>{'TRADE' if d.get('action') else 'hold'}</td>"
        f"<td>{d.get('position','')}</td><td>{d.get('equity','')}</td></tr>"
        for d in data["recent_decisions"]
    )
    trades = "".join(
        f"<tr><td>{t.get('entry_time','')[:10]}</td><td>{t.get('exit_time','')[:10]}</td>"
        f"<td>{t.get('entry_price','')}</td><td>{t.get('exit_price','')}</td>"
        f"<td style='color:{'#16a34a' if t.get('net_return',0)>=0 else '#dc2626'}'>"
        f"{t.get('net_return',0)*100:+.2f}%</td></tr>"
        for t in data["trades"]
    ) or "<tr><td colspan=5>no closed trades yet</td></tr>"
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TradePulse paper bot</title>
<style>
 body{{font:15px/1.5 -apple-system,system-ui,sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;color:#111}}
 h1{{font-size:1.3rem}} .kpi{{display:flex;gap:1.5rem;flex-wrap:wrap;margin:1rem 0}}
 .kpi div{{background:#f5f5f5;border-radius:8px;padding:.7rem 1.1rem}}
 .kpi b{{display:block;font-size:1.25rem}}
 table{{border-collapse:collapse;width:100%;margin:.5rem 0 1.5rem}}
 td,th{{border-bottom:1px solid #e5e5e5;padding:.35rem .5rem;text-align:left;font-size:.9rem}}
 caption{{text-align:left;font-weight:600;padding:.3rem 0}}
 footer{{color:#888;font-size:.8rem}}
</style></head><body>
<h1>🤖 TradePulse — paper bot ({data['symbol']}, {data['strategy'] or ''})</h1>
<div class="kpi">
 <div><b>${data['equity']:,.2f}</b>equity</div>
 <div><b style="color:{ret_color}">{ret:+.2f}%</b>total return</div>
 <div><b>{pos}</b>position</div>
 <div><b>{len(data['trades'])}</b>closed trades</div>
</div>
<table><caption>Closed trades</caption>
<tr><th>entry</th><th>exit</th><th>entry px</th><th>exit px</th><th>net</th></tr>{trades}</table>
<table><caption>Recent decisions (bar / price / action / pos / equity)</caption>
<tr><th>bar</th><th>price</th><th>action</th><th>pos</th><th>equity</th></tr>{rows}</table>
<footer>last bar: {data['last_bar']} · state updated: {data['updated_at']} · read-only, paper trading</footer>
</body></html>"""


def handler(event, context):
    params = (event or {}).get("queryStringParameters") or {}
    data = _fetch()
    if params.get("format") == "json":
        return {
            "statusCode": 200,
            "headers": {
                "content-type": "application/json",
                "cache-control": "no-store",
                # landing page reads the live ledger cross-origin
                "access-control-allow-origin": "*",
            },
            "body": json.dumps(data, default=str),
        }
    return {
        "statusCode": 200,
        "headers": {"content-type": "text/html; charset=utf-8", "cache-control": "no-store"},
        "body": _html(data),
    }
