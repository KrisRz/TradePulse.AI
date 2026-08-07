"""Pluggable persistence for the paper bot: local JSON (cron/dev) or DynamoDB (Lambda).

Selected via environment:
    PAPER_STATE_BACKEND = "local" (default) | "dynamodb"
    PAPER_STATE_TABLE   = DynamoDB table name (default "tradepulse_paper_bot")

DynamoDB layout (single on-demand table):
    pk = "<symbol>_<timeframe>"            e.g. "BTCUSDT_1d"
    sk = "state"                           latest bot state (one item)
    sk = "decision#<bar>"                  one item per processed bar
    sk = "fill#<bar>#<order_id>"           one item per real venue fill
    sk = "reject#<recorded_at>"            one item per venue-rejected order

The decision log is the raw material for the M5 gate metrics (Sharpe, max
drawdown, profit factor, net P&L, fee drag, trade count) and for the
live-vs-paper tracking-error check — every processed bar appends exactly
one record with the decision, price, position, equity and cost model.

The fill/reject log is the raw material for Gate C (cost fidelity,
docs/VENUE_4H_CHANNEL_2026-08-06.md §2). It MUST be durable: the gate is
decidable after >=20 fills (~10 months at ~12 round trips/year) while the
Lambda's CloudWatch log group keeps 30 days — evidence living only in logs
would evaporate long before the gate can be evaluated.
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

    @property
    def fills_path(self) -> Path:
        return self.state_path.with_suffix(".fills.jsonl")

    @property
    def rejections_path(self) -> Path:
        return self.state_path.with_suffix(".rejections.jsonl")

    def append_fill(self, record: Dict[str, Any]) -> None:
        self.fills_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.fills_path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def append_rejection(self, record: Dict[str, Any]) -> None:
        self.rejections_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.rejections_path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def has_decision(self, bar: str) -> bool:
        if not self.decisions_path.exists():
            return False
        with open(self.decisions_path) as f:
            for line in f:
                try:
                    if json.loads(line).get("bar") == bar:
                        return True
                except json.JSONDecodeError:  # torn line from a crashed append
                    continue
        return False


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

    def has_decision(self, bar: str) -> bool:
        resp = self.table.get_item(Key={"pk": self.pk, "sk": f"decision#{bar}"})
        return "Item" in resp

    def append_fill(self, record: Dict[str, Any]) -> None:
        # order_id in the key makes the put idempotent per venue order: a
        # retried Lambda re-persisting the same fill overwrites, never dupes.
        self.table.put_item(Item={
            "pk": self.pk,
            "sk": f"fill#{record.get('bar', 'unknown')}#{record.get('order_id', '?')}",
            **self._to_ddb(record),
        })

    def append_rejection(self, record: Dict[str, Any]) -> None:
        self.table.put_item(Item={
            "pk": self.pk,
            "sk": f"reject#{record.get('recorded_at', 'unknown')}",
            **self._to_ddb(record),
        })


def make_state_store(state_path: str, partition_key: str):
    backend = os.environ.get("PAPER_STATE_BACKEND", "local").lower()
    if backend == "dynamodb":
        table = os.environ.get("PAPER_STATE_TABLE", "tradepulse_paper_bot")
        return DynamoDBStateStore(table, partition_key)
    return LocalJsonStateStore(state_path)
