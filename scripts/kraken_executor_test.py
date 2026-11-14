#!/usr/bin/env python3
"""Drive the Kraken executor through the pre-registered test T0–T8.

docs/KRAKEN_EXECUTOR_PREREGISTRATION_2026-11-14.md. Real orders, smallest size.

    scripts/kraken_executor_test.py t0                    # no order reaches the book
    scripts/kraken_executor_test.py status                # read only
    scripts/kraken_executor_test.py enter --gbp 6.20 --bar T1 --confirm
    scripts/kraken_executor_test.py sync --bar T3 --confirm
    scripts/kraken_executor_test.py adjust --sell 0.00006 --bar T5 --confirm [--crash-after-submit]
    scripts/kraken_executor_test.py tighten-stop --pct 0.3 --confirm
    scripts/kraken_executor_test.py exit --bar T7 --confirm
    scripts/kraken_executor_test.py unblock --confirm
    scripts/kraken_executor_test.py maker-open --kind entry --gbp 3.20 --bar M01 --confirm
    scripts/kraken_executor_test.py maker-settle --confirm        # 15 minutes later
    scripts/kraken_executor_test.py maker-cycles --start 2 --count 9 --confirm   # unattended

Every command that can place, cancel or trade needs ``--confirm``; without it
the command prints what it would do and stops. State and fills live in DynamoDB
under their own partition key, so the HMRC export reads them like any channel:

    scripts/hmrc_export.py --pk XBTGBP_exectest --out disposals.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.backend.paper_trading.kraken_api import (  # noqa: E402
    KrakenAPIError, KrakenClient, KrakenOutcomeUnknown,
)
from app.backend.paper_trading.kraken_executor import (  # noqa: E402
    ExecutorHalt, KrakenExecutor, KrakenTrader, OrderOutcomeUnknown, TraderState,
)
from app.backend.paper_trading.state_store import DynamoDBStateStore  # noqa: E402

PK = "XBTGBP_exectest"
TABLE = "tradepulse_paper_bot"
SSM_PREFIX = "/tradepulse/kraken"
MAX_NOTIONAL = Decimal("7")          # the test never needs a larger order
LOSS_BUDGET = Decimal("3")           # pre-registered: stop the test beyond this
START_BALANCE = Decimal("10")


class SimulatedCrash(RuntimeError):
    """T4: the run dies after the order was sent and before it was booked."""


def credentials(region: str) -> tuple[str, str]:
    import boto3
    ssm = boto3.client("ssm", region_name=region)
    get = lambda name: ssm.get_parameter(  # noqa: E731
        Name=f"{SSM_PREFIX}/{name}", WithDecryption=True)["Parameter"]["Value"].strip()
    return get("key"), get("secret")


def build(args, fault=None):
    key, secret = credentials(args.region)
    client = KrakenClient(key, secret)
    executor = KrakenExecutor(client, "XBTGBP", max_notional=MAX_NOTIONAL, channel=PK)
    pre = executor.preflight()
    store = DynamoDBStateStore(TABLE, PK)
    state = TraderState.from_dict(store.load())
    trader = KrakenTrader(executor, state, save=store.save,
                          on_fill=lambda rec: (store.append_fill(rec), print("FILL", json.dumps(rec))),
                          fault=fault)
    return client, executor, trader, pre


def snapshot(executor, trader) -> dict:
    quote, base = executor.balances()
    bid, ask = executor.client.best_bid_ask(executor.pair)
    equity = quote + base * bid
    return {"gbp": str(quote), "btc": str(base), "bid": str(bid), "ask": str(ask),
            "equity_gbp": f"{equity:.4f}", "test_loss_gbp": f"{START_BALANCE - equity:.4f}",
            "book": trader.state.as_dict(),
            "open_orders": [{"txid": o.txid, "type": o.ordertype, "vol": str(o.volume),
                             "stop": str(o.stop_price), "cl_ord_id": o.cl_ord_id}
                            for o in executor.open_orders()]}


def guard_budget(executor) -> None:
    quote, base = executor.balances()
    bid, _ = executor.client.best_bid_ask(executor.pair)
    loss = START_BALANCE - (quote + base * bid)
    if loss > LOSS_BUDGET:
        raise ExecutorHalt(f"test loss £{loss:.2f} is over the pre-registered budget £{LOSS_BUDGET}")


def need_confirm(args, what: str) -> bool:
    if args.confirm:
        return True
    print(f"DRY: would {what}. Re-run with --confirm to do it.")
    return False


# --------------------------------------------------------------------------- #
def cmd_t0(args) -> int:
    """Everything that can be proven without an order reaching the book."""
    results = []

    def check(name, fn):
        try:
            detail = fn()
            results.append((name, True, detail))
        except Exception as exc:  # noqa: BLE001 — the report must list every failure
            results.append((name, False, f"{type(exc).__name__}: {exc}"))

    key, secret = credentials(args.region)
    client = KrakenClient(key, secret)
    executor = KrakenExecutor(client, "XBTGBP", max_notional=MAX_NOTIONAL, channel=PK)
    holder = {}

    def preflight():
        holder["pre"] = executor.preflight()
        return f"permissions {list(holder['pre'].permissions)}, taker fee {holder['pre'].taker_fee}"
    check("R1-R3 preflight (no withdraw, online, pair, fee)", preflight)
    check("balance readable", lambda: {k: str(v) for k, v in client.balance().items()})

    def denied(name, params):
        try:
            client.private_read(name, params)
        except KrakenAPIError as exc:
            if exc.has("EGeneral:Permission denied"):
                return "Permission denied"
            raise
        raise AssertionError(f"{name} was ALLOWED")
    check("withdrawal methods denied", lambda: denied("WithdrawMethods", {"asset": "ZGBP"}))
    check("deposit methods denied", lambda: denied("DepositMethods", {"asset": "ZGBP"}))

    def validate(side, ordertype, kind, **extra):
        rules = executor.rules
        bid, ask = client.best_bid_ask("XBTGBP")
        volume = rules.floor_volume(Decimal("6.20") / ask)
        params = {"pair": "XBTGBP", "validate": "true", "type": side, "ordertype": ordertype,
                  "volume": str(volume), "cl_ord_id": executor.client_order_id(kind, "t0"),
                  "deadline": executor._deadline(), **extra}
        if ordertype == "stop-loss":
            params["price"] = str(rules.floor_price(bid * Decimal("0.8")))
            params["trigger"] = "last"
        return client.private_write("AddOrder", params)["descr"]["order"]
    check("validate: market buy (executor's id and deadline format)", lambda: validate("buy", "market", "b"))
    check("validate: market sell", lambda: validate("sell", "market", "s"))
    check("validate: stop-loss sell, trigger last", lambda: validate("sell", "stop-loss", "p"))

    def bad_signature():
        import base64, os
        calls = []
        bad = KrakenClient(key, base64.b64encode(os.urandom(64)).decode(), sleep=lambda s: calls.append(s))
        try:
            bad.balance()
        except KrakenAPIError as exc:
            assert not calls, f"retried {len(calls)} time(s)"
            return f"{exc.errors}, no retry"
        raise AssertionError("a wrong secret was accepted")
    check("wrong secret: clear refusal, not retried", bad_signature)

    def stale_nonce():
        sleeps = []
        stale = KrakenClient(key, secret, clock=lambda: 1.0, sleep=lambda s: sleeps.append(s))
        try:
            stale.balance()
        except KrakenAPIError as exc:
            assert exc.has("EAPI:Invalid nonce"), exc.errors
            return f"{exc.errors} after {len(sleeps) + 1} bounded attempts"
        raise AssertionError("a stale nonce was accepted")
    check("stale nonce: clear refusal, bounded attempts", stale_nonce)

    def quiet_sync():
        store = DynamoDBStateStore(TABLE, PK)
        state = TraderState.from_dict(store.load())
        assert Decimal(state.qty) == 0, f"test book is not empty: {state.as_dict()}"
        trader = KrakenTrader(executor, state, save=lambda s: None, on_fill=lambda r: None)
        report = trader.sync("T0")
        assert report["protected"] and not executor.open_orders()
        return report
    check("R11 reconciliation on the empty book", quiet_sync)

    def nothing_created():
        closed = client.private_read("ClosedOrders") or {}
        opened = (client.private_read("OpenOrders") or {}).get("open") or {}
        assert not opened and int(closed.get("count", 0)) == 0, (opened, closed.get("count"))
        return "0 open, 0 closed orders on the account"
    check("no order reached the book", nothing_created)

    for name, ok, detail in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    passed = all(ok for _, ok, _ in results)
    print(f"T0 VERDICT: {'PASS' if passed else 'FAIL'} — as of {datetime.now(timezone.utc).isoformat()}")
    return 0 if passed else 1


def cmd_status(args) -> int:
    _client, executor, trader, pre = build(args)
    print(json.dumps({"fee": str(pre.taker_fee), **snapshot(executor, trader)}, indent=1))
    return 0


def cmd_enter(args) -> int:
    _c, executor, trader, _pre = build(args)
    if not need_confirm(args, f"BUY £{args.gbp} of BTC at market and rest a stop 20% under the fill"):
        return 0
    guard_budget(executor)
    before = snapshot(executor, trader)
    order = trader.enter(Decimal(args.gbp), args.bar)
    after = snapshot(executor, trader)
    spent = Decimal(before["gbp"]) - Decimal(after["gbp"])
    print(json.dumps({"order": order.txid, "status": order.status, "vol_exec": str(order.vol_exec),
                      "avg_price": str(order.avg_price), "cost": str(order.cost), "fee": str(order.fee),
                      "gbp_spent_on_account": str(spent),
                      "cost_plus_fee": str(order.cost + order.fee),
                      "fee_matches_balance": abs(spent - (order.cost + order.fee)) <= Decimal("0.01"),
                      "btc_book_equals_account": trader.state.qty == str(Decimal(after["btc"]).normalize())
                      or Decimal(trader.state.qty) == Decimal(after["btc"]),
                      "after": after}, indent=1))
    return 0


def cmd_sync(args) -> int:
    _c, executor, trader, _pre = build(args)
    if not need_confirm(args, "reconcile the book with the account (may book a filled stop or place a missing one)"):
        return 0
    adds_before = len(executor.open_orders())
    report = trader.sync(args.bar)
    print(json.dumps({"report": report, "open_orders_before": adds_before,
                      "after": snapshot(executor, trader)}, indent=1))
    return 0


def cmd_adjust(args) -> int:
    def fault(point):
        if args.crash_after_submit and point == "after_submit":
            raise SimulatedCrash("order sent, booking skipped on purpose (T4)")
    _c, executor, trader, _pre = build(args, fault=fault)
    if not need_confirm(args, f"cancel the stop, SELL {args.sell} BTC at market, rest a new stop"):
        return 0
    guard_budget(executor)
    try:
        order = trader.adjust(-Decimal(args.sell), args.bar)
    except SimulatedCrash as exc:
        print(f"CRASHED AS ASKED: {exc}")
        print(json.dumps(snapshot(executor, trader), indent=1))
        return 0
    print(json.dumps({"order": order.txid, "status": order.status, "vol_exec": str(order.vol_exec),
                      "avg_price": str(order.avg_price), "fee": str(order.fee),
                      "after": snapshot(executor, trader)}, indent=1))
    return 0


def cmd_tighten_stop(args) -> int:
    """T6: replace the 20% stop with one just under the market so it fires."""
    _c, executor, trader, _pre = build(args)
    if not need_confirm(args, f"cancel the stop and rest one {args.pct}% under the last price (it is meant to fire)"):
        return 0
    if trader.qty == 0:
        raise ExecutorHalt("no position to protect")
    trader._clear_stop(args.bar)
    bid, _ask = executor.client.best_bid_ask(executor.pair)
    trigger = bid * (1 - Decimal(args.pct) / 100)
    trader.state.stop_seq += 1
    trader._persist()
    order = executor.place_stop(trader.qty, trigger, f"stop#{trader.state.stop_seq}")
    trader.state.stop_txid = order.txid
    trader._persist()
    print(json.dumps({"stop": order.txid, "trigger": str(order.stop_price), "bid": str(bid),
                      "after": snapshot(executor, trader)}, indent=1))
    return 0


def cmd_exit(args) -> int:
    _c, executor, trader, _pre = build(args)
    if not need_confirm(args, f"cancel the stop and SELL the bot's {trader.state.qty} BTC at market"):
        return 0
    order = trader.exit(args.bar)
    print(json.dumps({"order": order.txid if order else None,
                      "vol_exec": str(order.vol_exec) if order else None,
                      "avg_price": str(order.avg_price) if order else None,
                      "fee": str(order.fee) if order else None,
                      "after": snapshot(executor, trader)}, indent=1))
    return 0


def cmd_maker_open(args) -> int:
    """Post-only measurement (docs/POSTONLY_DESIGN_2026-11-14.md): rest one order."""
    _c, executor, trader, _pre = build(args)
    what = (f"rest a post-only BUY for £{args.gbp} at the bid" if args.kind == "entry"
            else "lift the stop and rest a post-only SELL of the whole position at the ask")
    if not need_confirm(args, what):
        return 0
    guard_budget(executor)
    order = trader.maker_open(args.kind, Decimal(args.gbp or "0"), args.bar)
    print(json.dumps({"order": order.txid, "status": order.status, "limit": order.raw["descr"]["price"],
                      "volume": str(order.volume), "pending": trader.state.pending,
                      "settle_after_utc": "15 minutes from placed_at"}, indent=1))
    return 0


def cmd_maker_settle(args) -> int:
    _c, executor, trader, _pre = build(args)
    if not need_confirm(args, "take what filled, cancel the rest, finish the remainder at market, restore the stop"):
        return 0
    result = trader.maker_settle()
    print(json.dumps({"result": result, "after": snapshot(executor, trader)}, indent=1))
    return 0


def _wait_for(executor, txid: str, minutes: float) -> None:
    """Block until the order is final or the deadline has passed (read-only)."""
    import time
    end = time.time() + minutes * 60
    while time.time() < end:
        if executor.query(txid).is_final:
            return
        time.sleep(20)


def _maker_leg(trader, executor, kind: str, gbp: str, bar: str, wait_min: float) -> dict:
    """One measured order: rest it, wait, settle. A post-only order the book
    moved away from places nothing and is simply tried again."""
    import time
    for attempt in range(5):
        try:
            order = trader.maker_open(kind, Decimal(gbp), bar)
            break
        except ExecutorHalt as exc:
            if "would have taken" not in str(exc) or attempt == 4:
                raise
            time.sleep(5)
    print(f"[{datetime.now(timezone.utc):%H:%M:%S}] {bar} {kind}: resting {order.volume} @ "
          f"{order.raw['descr']['price']} ({order.txid})", flush=True)
    _wait_for(executor, order.txid, wait_min)
    result = trader.maker_settle()
    print(f"[{datetime.now(timezone.utc):%H:%M:%S}] {bar} {kind}: maker {result['maker']} "
          f"taker {result['taker']} dust {result['dust']}", flush=True)
    return result


def cmd_maker_cycles(args) -> int:
    """Run whole measurement cycles unattended: buy -> settle -> sell -> settle,
    then a pause, ``--count`` times. Stops on the first thing it cannot explain."""
    import time
    _c, executor, trader, _pre = build(args)
    if not need_confirm(args, f"run {args.count} post-only cycle(s) of £{args.gbp} "
                              f"(deadline {args.wait_min} min per order, {args.gap_min} min between cycles)"):
        return 0
    for n in range(args.start, args.start + args.count):
        guard_budget(executor)
        report = trader.sync(f"M{n:02d}")
        if trader.state.pending:
            raise ExecutorHalt("a maker order is pending — run maker-settle first")
        if trader.qty == 0:
            _maker_leg(trader, executor, "entry", args.gbp, f"M{n:02d}", args.wait_min)
        if trader.qty > 0:
            _maker_leg(trader, executor, "exit", "0", f"M{n:02d}x", args.wait_min)
        snap = snapshot(executor, trader)
        print(f"[{datetime.now(timezone.utc):%H:%M:%S}] cycle {n} done: £{snap['gbp']}, "
              f"{snap['btc']} BTC, open orders {len(snap['open_orders'])}, "
              f"test loss £{snap['test_loss_gbp']}", flush=True)
        if n + 1 < args.start + args.count:
            time.sleep(args.gap_min * 60)
    print("ALL CYCLES DONE")
    return 0


def cmd_unblock(args) -> int:
    _c, executor, trader, _pre = build(args)
    if not need_confirm(args, "clear the stop-out block on the test book"):
        return 0
    trader.unblock()
    print(json.dumps(snapshot(executor, trader), indent=1))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--region", default="eu-west-2")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("t0").set_defaults(fn=cmd_t0)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    for name, fn in (("enter", cmd_enter), ("sync", cmd_sync), ("adjust", cmd_adjust),
                     ("tighten-stop", cmd_tighten_stop), ("exit", cmd_exit), ("unblock", cmd_unblock),
                     ("maker-open", cmd_maker_open), ("maker-settle", cmd_maker_settle),
                     ("maker-cycles", cmd_maker_cycles)):
        sp = sub.add_parser(name)
        sp.set_defaults(fn=fn)
        sp.add_argument("--confirm", action="store_true")
        sp.add_argument("--bar", default=name.upper())
        if name == "enter":
            sp.add_argument("--gbp", required=True)
        if name == "adjust":
            sp.add_argument("--sell", required=True)
            sp.add_argument("--crash-after-submit", action="store_true")
        if name == "maker-cycles":
            sp.add_argument("--count", type=int, required=True)
            sp.add_argument("--start", type=int, required=True, help="number of the first cycle (bar M<start>)")
            sp.add_argument("--gbp", default="3.20")
            sp.add_argument("--wait-min", type=float, default=15)
            sp.add_argument("--gap-min", type=float, default=20)
        if name == "maker-open":
            sp.add_argument("--kind", choices=["entry", "exit"], required=True)
            sp.add_argument("--gbp")
        if name == "tighten-stop":
            sp.add_argument("--pct", default="0.3")
    args = p.parse_args()
    try:
        return args.fn(args)
    except (ExecutorHalt, OrderOutcomeUnknown, KrakenAPIError, KrakenOutcomeUnknown) as exc:
        print(f"STOPPED: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
