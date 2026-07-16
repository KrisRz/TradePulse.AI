"""Pluggable persistence for the paper bot: local JSON (cron/dev) or DynamoDB (Lambda).

Selected via environment:
    PAPER_STATE_BACKEND = "local" (default) | "dynamodb"
    PAPER_STATE_TABLE   = DynamoDB table name (default "tradepulse_paper_bot")

DynamoDB layout (single on-demand table):
    pk = "<symbol>_<timeframe>"            e.g. "BTCUSDT_1d"
    sk = "state"                           latest bot state (one item)
    sk = "decision#<bar>"                  one item per processed bar

The decision log is the raw material for the M5 gate metrics (Sharpe, max
drawdown, profit factor, net P&L, fee drag, trade count) and for the
live-vs-paper tracking-error check — every processed bar appends exactly
one record with the decision, price, position, equity and cost model.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional


class LocalJsonStateStore:
    """State in a JSON file; decisions appended to a JSONL file next to it."""

    def __init__(self, state_path: str) -> None:
        self.state_path = Path(state_path)
        self.decisions_path = self.state_path.with_suffix(".decisions.jsonl")

    def load(self) -> Optional[Dict[str, Any]]:
        if not self.state_path.exists():
            return None
        return json.loads(self.state_path.read_text())

    def save(self, state: Dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2, default=str))

    def append_decision(self, record: Dict[str, Any]) -> None:
        self.decisions_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.decisions_path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")


class DynamoDBStateStore:
    """State + decision log in one on-demand DynamoDB table (Lambda path)."""

    def __init__(self, table_name: str, partition_key: str) -> None:
        import boto3  # provided by the Lambda runtime

        self.table = boto3.resource("dynamodb").Table(table_name)
        self.pk = partition_key

    @staticmethod
    def _to_ddb(obj: Any) -> Any:
        """DynamoDB rejects float — convert to Decimal via JSON round-trip."""
        return json.loads(json.dumps(obj, default=str), parse_float=Decimal)

    @staticmethod
    def _from_ddb(obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, dict):
            return {k: DynamoDBStateStore._from_ddb(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [DynamoDBStateStore._from_ddb(v) for v in obj]
        return obj

    def load(self) -> Optional[Dict[str, Any]]:
        resp = self.table.get_item(Key={"pk": self.pk, "sk": "state"},
                                   ConsistentRead=True)
        item = resp.get("Item")
        if not item:
            return None
        return self._from_ddb(item.get("state"))

    def save(self, state: Dict[str, Any]) -> None:
        self.table.put_item(Item={
            "pk": self.pk,
            "sk": "state",
            "state": self._to_ddb(state),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

    def append_decision(self, record: Dict[str, Any]) -> None:
        self.table.put_item(Item={
            "pk": self.pk,
            "sk": f"decision#{record.get('bar', 'unknown')}",
            **self._to_ddb(record),
        })


def make_state_store(state_path: str, partition_key: str):
    backend = os.environ.get("PAPER_STATE_BACKEND", "local").lower()
    if backend == "dynamodb":
        table = os.environ.get("PAPER_STATE_TABLE", "tradepulse_paper_bot")
        return DynamoDBStateStore(table, partition_key)
    return LocalJsonStateStore(state_path)
