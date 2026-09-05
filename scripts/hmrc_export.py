#!/usr/bin/env python3
"""Export the bot's real fills as a UK capital-gains working paper.

    # everything the venue channel has ever filled, in quote currency
    scripts/hmrc_export.py --pk BTCUSDT_4h --out disposals.csv

    # one tax year, converted at a single rate (or per-day from a CSV)
    scripts/hmrc_export.py --pk BTCUSDT_4h --from 2026-04-06 --to 2027-04-05 \
        --fx 0.79 --out disposals_2026_27.csv
    scripts/hmrc_export.py --pk BTCUSDT_4h --fx-csv rates.csv --out disposals.csv

The matching rules live in ``app.backend.reporting.hmrc`` and are tested there;
this file only fetches, filters and prints. It is a working paper, not a return —
see the module docstring for what it deliberately does not decide for you.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.backend.reporting.hmrc import match, transactions_from_fills, write_csv  # noqa: E402


def fills_from_dynamodb(table_name: str, pk: str, region: str) -> list:
    """Every ``fill#`` item for one channel. Small by construction — no paging games."""
    import boto3
    from boto3.dynamodb.conditions import Key

    table = boto3.resource("dynamodb", region_name=region).Table(table_name)
    items, kwargs = [], {}
    while True:
        resp = table.query(
            KeyConditionExpression=Key("pk").eq(pk) & Key("sk").begins_with("fill#"),
            **kwargs)
        items += resp["Items"]
        if "LastEvaluatedKey" not in resp:
            return items
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]


def fills_from_jsonl(path: str) -> list:
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def fx_from_csv(path: str):
    """date,rate -> a lookup. A missing day is an error, never a silent 1.0."""
    rates = {}
    with open(path) as fh:
        for row in csv.reader(fh):
            if not row or row[0].startswith("#") or row[0].strip() == "date":
                continue
            rates[date.fromisoformat(row[0].strip())] = Decimal(row[1].strip())

    def lookup(day: date) -> Decimal:
        if day not in rates:
            raise SystemExit(
                f"no FX rate for {day} in {path} — add it rather than guessing; "
                f"HMRC expects the rate on the day of the transaction")
        return rates[day]

    return lookup


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group()
    src.add_argument("--pk", default="BTCUSDT_4h", help="DynamoDB partition key")
    src.add_argument("--jsonl", help="read a local fill log instead of DynamoDB")
    p.add_argument("--table", default=os.environ.get("PAPER_STATE_TABLE",
                                                     "tradepulse_paper_bot"))
    p.add_argument("--region", default=os.environ.get("AWS_DEFAULT_REGION", "eu-west-2"))
    p.add_argument("--asset", default="BTC")
    p.add_argument("--quote", default="USDT")
    p.add_argument("--from", dest="date_from", help="UK date, inclusive (YYYY-MM-DD)")
    p.add_argument("--to", dest="date_to", help="UK date, inclusive (YYYY-MM-DD)")
    p.add_argument("--fx", type=Decimal, help="single quote->GBP rate")
    p.add_argument("--fx-csv", help="date,rate per line — the correct way")
    p.add_argument("--out", default="disposals.csv")
    args = p.parse_args(argv)

    raw = fills_from_jsonl(args.jsonl) if args.jsonl \
        else fills_from_dynamodb(args.table, args.pk, args.region)
    if not raw:
        raise SystemExit("no fills found — nothing to report")

    transactions = transactions_from_fills(raw, asset=args.asset, quote=args.quote)
    reports, summary = match(transactions)

    # Filtering happens AFTER matching, never before: a disposal in this tax year
    # can be matched against an acquisition in the next one (the 30-day rule), so
    # cutting the input to a date range would change the answer.
    if args.date_from:
        start = date.fromisoformat(args.date_from)
        reports = [r for r in reports if r.uk_day >= start]
    if args.date_to:
        end = date.fromisoformat(args.date_to)
        reports = [r for r in reports if r.uk_day <= end]

    if args.fx_csv:
        fx = fx_from_csv(args.fx_csv)
    elif args.fx is not None:
        fx = lambda _day: args.fx          # noqa: E731 - a one-line constant rate
    else:
        fx = None

    write_csv(args.out, reports, currency=args.quote, fx=fx)

    unit = "GBP" if fx else args.quote
    print(f"fills read          : {len(raw)}")
    print(f"disposals reported  : {len(reports)} of {summary['disposals']} total")
    print(f"proceeds ({unit:<4})     : {summary['total_proceeds']:.2f}")
    print(f"allowable cost      : {summary['total_cost']:.2f}")
    print(f"gain / (loss)       : {summary['total_gain']:.2f}")
    print(f"pool left           : {summary['pool_qty']:f} {args.asset} "
          f"at {summary['pool_unit_cost']:.2f} {args.quote}/unit")
    if summary["unmatched_disposals"]:
        print(f"⚠️  UNMATCHED disposals: {summary['unmatched_disposals']} — the log "
              f"shows selling more than it ever bought; check before filing")
    if not fx:
        print(f"⚠️  amounts are in {args.quote}, NOT sterling — apply HMRC rates "
              f"(--fx / --fx-csv) before this goes near a return")
    print(f"written             : {args.out}")


if __name__ == "__main__":
    main()
