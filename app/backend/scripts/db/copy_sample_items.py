#!/usr/bin/env python3
"""
Copy a small sample of items from AWS DynamoDB to DynamoDB Local for parity testing.
"""

from __future__ import annotations

import os
from typing import List

import boto3
import decimal


AWS_REGION: str = os.environ.get("AWS_DEFAULT_REGION", "eu-west-2")
LOCAL_ENDPOINT: str = os.environ.get("DYNAMODB_ENDPOINT", "http://localhost:8000")


SRC = boto3.resource("dynamodb", region_name=AWS_REGION)
DST = boto3.resource(
    "dynamodb",
    region_name="us-east-1",
    endpoint_url=LOCAL_ENDPOINT,
    aws_access_key_id="dummy",
    aws_secret_access_key="dummy",
)


TABLES: List[str] = [
    "tradepulse-users-production",
    "tradepulse-virtual_portfolios-production",
    "tradepulse-positions-production",
    "tradepulse-trading_signals-production",
    "tradepulse-live_candles-production",
]


def copy_some(table_name: str, limit: int = 50) -> None:
    src = SRC.Table(table_name)
    dst = DST.Table(table_name)
    resp = src.scan(Limit=limit)
    items = resp.get("Items", [])
    for item in items:
        # Decimal is supported natively by boto3 for DynamoDB; write as-is
        dst.put_item(Item=item)
    print(f"copied {len(items)} items: {table_name}")


def main() -> None:
    for t in TABLES:
        try:
            copy_some(t, limit=50)
        except Exception as e:
            print(f"error copying {t}: {e}")


if __name__ == "__main__":
    main()


