"""Tests for the paper bot state store (M1.4 / M2 groundwork)."""

import json

from app.backend.paper_trading.state_store import (
    DynamoDBStateStore,
    LocalJsonStateStore,
    make_state_store,
)


def test_local_store_roundtrip(tmp_path):
    store = LocalJsonStateStore(str(tmp_path / "s.json"))
    assert store.load() is None
    state = {"last_bar": "2026-07-15", "portfolio": {"realized": 10000.0}}
    store.save(state)
    assert store.load() == state


def test_local_store_appends_decisions(tmp_path):
    store = LocalJsonStateStore(str(tmp_path / "s.json"))
    store.append_decision({"bar": "b1", "price": 1.0})
    store.append_decision({"bar": "b2", "price": 2.0})
    lines = (tmp_path / "s.decisions.jsonl").read_text().strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["bar"] == "b1"
    assert json.loads(lines[1])["price"] == 2.0


def test_make_state_store_defaults_to_local(tmp_path, monkeypatch):
    monkeypatch.delenv("PAPER_STATE_BACKEND", raising=False)
    store = make_state_store(str(tmp_path / "s.json"), "BTCUSDT_1d")
    assert isinstance(store, LocalJsonStateStore)


def test_ddb_float_decimal_conversion():
    """DynamoDB rejects float; state must survive the Decimal round-trip."""
    state = {"portfolio": {"realized": 10123.45, "trades": [{"net_return": -0.012}]},
             "last_bar": "2026-07-15"}
    ddb = DynamoDBStateStore._to_ddb(state)
    back = DynamoDBStateStore._from_ddb(ddb)
    assert back["portfolio"]["realized"] == 10123.45
    assert back["portfolio"]["trades"][0]["net_return"] == -0.012
    assert isinstance(back["portfolio"]["realized"], float)
