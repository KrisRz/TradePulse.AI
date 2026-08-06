"""Drive a full entry→exit round-trip against Binance Demo Trading.

Written 2026-08-06 to close unknown B — *can the bot correctly execute a trade?*
The paper bot has been proving unknown A (does the strategy make money) for three
weeks and will need a year more; B was untouched until PR #24, blocks M6 just as
hard, and is closable in an afternoon. This is the script that closes it.

Why a forced signal
-------------------
The live strategy trades 1.69 round-trips a *year*. Waiting for a real EMA cross
to exercise the order path would mean waiting months to find out whether the
signing code works. ``--force-signal`` drives the same ``PaperPortfolio`` through
the same seam with a synthetic decision, so the whole path — sign, size, round to
LOT_SIZE, clear MIN_NOTIONAL, submit, average the fills, net the commission, book
the fill, reconcile — runs end to end in about a minute.

What it does NOT do
-------------------
It does not touch the M5 Lambda, the production book in DynamoDB, or any
strategy parameter. It builds a throwaway portfolio in memory and trades a demo
account with fake money. The M5 window is not disturbed by anything here.

    export BINANCE_DEMO_KEY=... BINANCE_DEMO_SECRET=...
    python scripts/demo_roundtrip.py --check            # connectivity only
    python scripts/demo_roundtrip.py --dry-run          # plan, send nothing
    python scripts/demo_roundtrip.py --force-signal --notional 20
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import pathlib
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.backend.paper_trading.binance_demo import (  # noqa: E402
    DEMO_BASE_URL,
    BinanceAPIError,
    BinanceDemoExecutor,
    OrderTooSmall,
)
from app.backend.paper_trading.execution import BUY, SELL  # noqa: E402
from app.backend.paper_trading.portfolio import PaperPortfolio  # noqa: E402


def load_env_file(path: pathlib.Path) -> None:
    """Read ``KEY=value`` lines into the environment, without overwriting it.

    Credentials live outside the repository. This exists so a gitignored file can
    hold them for a local session; it deliberately does not overwrite variables
    that are already set, so an explicit export always wins.
    """
    if not path.exists():
        raise SystemExit(f"no such env file: {path}")
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def report_environment(executor: BinanceDemoExecutor) -> None:
    offset = executor.sync_time()
    rules = executor.rules()
    balances = executor.balances()
    price = executor.mark_price()

    print(f"venue          {executor.base_url}")
    print(f"clock offset   {offset:+d} ms (recvWindow {executor.recv_window} ms)")
    print(f"symbol         {rules.symbol} status={rules.status}")
    print(f"  LOT_SIZE     step={rules.step_size} min={rules.min_qty}")
    print(f"  NOTIONAL     min={rules.min_notional} {rules.quote_asset}")
    print(f"  PRICE_FILTER tick={rules.tick_size}")
    print(f"mark price     {price:,.2f} {rules.quote_asset}")
    print("balances       " + ", ".join(f"{v} {k}" for k, v in sorted(balances.items())))


def print_reconciliation(executor: BinanceDemoExecutor) -> None:
    records = executor.reconciliations()
    if not records:
        return
    print("\n─── reconciliation: what the book assumed vs what the venue did ───")
    header = f"{'side':>5} {'reference':>12} {'assumed':>12} {'actual':>12} " \
             f"{'slip_act':>9} {'slip_ass':>9} {'err':>8} {'fills':>5}"
    print(header)
    for r in records:
        side = "BUY" if r.side == BUY else "SELL"
        print(f"{side:>5} {r.reference_price:>12,.2f} {r.assumed_price:>12,.2f} "
              f"{r.actual_price:>12,.2f} {r.slippage_actual * 100:>8.4f}% "
              f"{r.slippage_assumed * 100:>8.4f}% {r.price_error:>8,.2f} "
              f"{r.fill_count:>5}")

    worst = max(abs(r.slippage_actual) for r in records)
    assumed = records[0].slippage_assumed
    print(f"\nworst measured slippage {worst * 100:.4f}% vs {assumed * 100:.4f}% assumed "
          f"→ the model is {'CONSERVATIVE' if worst <= assumed else 'OPTIMISTIC'}")
    if worst > assumed:
        print("  note: demo has its own matching engine, so treat this as indicative,\n"
              "        not as a live measurement. Fees and filters ARE real.")


def run_roundtrip(executor: BinanceDemoExecutor, hold_seconds: float,
                  dry_run: bool) -> int:
    """Take the book from flat → long → flat through the real venue."""
    rules = executor.rules()
    price = executor.mark_price()

    try:
        planned = executor.plan_quantity(BUY, price)
    except OrderTooSmall as exc:
        print(f"\ncannot size an order: {exc}")
        return 1
    print(f"\nplanned entry  {planned} {rules.base_asset} "
          f"(~{float(planned) * price:,.2f} {rules.quote_asset}) at {price:,.2f}")

    if dry_run:
        print("dry run — nothing sent.")
        return 0

    book = PaperPortfolio(fee_rate=0.001, slippage=executor.assumed_slippage,
                          initial_capital=10_000.0)
    book.set_executor(executor)

    print("\n→ ENTRY")
    book.reconcile(target_side=1, price=price, time=now_iso())
    print(f"  book entry_fill {book.entry_fill:,.2f}  equity {book.equity(price):,.2f}")
    print(f"  executor holds  {executor.position_qty} {rules.base_asset}")

    if hold_seconds:
        print(f"\n  holding {hold_seconds:.0f}s …")
        time.sleep(hold_seconds)

    exit_price = executor.mark_price()
    print(f"\n→ EXIT at {exit_price:,.2f}")
    book.reconcile(target_side=0, price=exit_price, time=now_iso())

    trade = book.trades[-1]
    print(f"  entry {trade['entry_price']:,.2f} → exit {trade['exit_price']:,.2f}")
    print(f"  net return {trade['net_return'] * 100:+.4f}%  "
          f"equity {book.equity(exit_price):,.2f}")
    print(f"  executor holds {executor.position_qty} {rules.base_asset} (expect 0)")

    if executor.position_qty != Decimal("0"):
        print("  ⚠ position did not return to flat — investigate before trusting this path")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="connectivity, credentials and filters only")
    parser.add_argument("--force-signal", action="store_true",
                        help="drive a synthetic entry→exit round-trip now")
    parser.add_argument("--dry-run", action="store_true",
                        help="size the order and stop before submitting it")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--notional", type=float, default=20.0,
                        help="ceiling per order in quote units (default: 20)")
    parser.add_argument("--quote-fraction", type=float, default=1.0)
    parser.add_argument("--hold", type=float, default=5.0,
                        help="seconds to stay in the position (default: 5)")
    parser.add_argument("--assumed-slippage", type=float, default=0.0002,
                        help="the book's constant, for reconciliation only")
    parser.add_argument("--base-url", default=DEMO_BASE_URL)
    parser.add_argument("--env-file", type=pathlib.Path,
                        help="file of KEY=value credentials (keep it out of git)")
    parser.add_argument("--json", action="store_true",
                        help="emit reconciliations as JSON on stdout")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    if args.env_file:
        load_env_file(args.env_file)

    try:
        executor = BinanceDemoExecutor.from_env(
            symbol=args.symbol,
            base_url=args.base_url,
            quote_fraction=args.quote_fraction,
            max_notional=args.notional,
            assumed_slippage=args.assumed_slippage,
        )
    except ValueError as exc:
        print(exc)
        return 2

    try:
        report_environment(executor)
        status = 0
        if args.force_signal or args.dry_run:
            status = run_roundtrip(executor, args.hold, args.dry_run)
            print_reconciliation(executor)
            if args.json:
                print(json.dumps([r.as_dict() for r in executor.reconciliations()],
                                 indent=2))
        elif not args.check:
            print("\nnothing to do — pass --check, --dry-run or --force-signal")
        return status
    except BinanceAPIError as exc:
        print(f"\nvenue rejected the request: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
