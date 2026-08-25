"""Tests for the public status API behind `tradepulseai.co.uk/api/state`.

The one that matters is ``test_open_position_is_marked_to_market``. The paper
bot's ``realized`` field is equity booked on *closed* trades, so while a
position is open it lags by exactly the open profit. Serving it as "equity"
was harmless for as long as that bot sat flat — which it did from May until
2026-08-22, when it opened its first position and the two numbers silently
separated by 2.5% within three days.

The module under test lives in ``infra-site/lambda``, a separate Terraform root
with no package of its own, so it is loaded by path rather than imported.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[3] / "infra-site" / "lambda" / "venue_status.py"
_spec = importlib.util.spec_from_file_location("venue_status", _SRC)
venue_status = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(venue_status)


class FakeTable:
    """Stands in for the DynamoDB table; returns one prepared state item."""

    def __init__(self, portfolio: dict, last_bar: str = "2026-08-24 00:00:00+00:00"):
        self._item = {
            "pk": venue_status.PAPER_PK,
            "sk": "state",
            "updated_at": "2026-08-25T00:10:34.685994+00:00",
            "state": {"portfolio": portfolio, "last_bar": last_bar},
        }

    def get_item(self, Key):  # noqa: N803 - boto3 spells it this way
        return {"Item": self._item}


FLAT = {
    "side": 0,
    "realized": 9990.0,
    "initial_capital": 10000.0,
    "last_price": 78992.75,
    "trades": [],
}

# The real book as of 2026-08-25: long since 2026-08-22, nothing closed yet.
OPEN_LONG = {
    "side": 1,
    "realized": 9990.0,
    "entry_equity": 9990.0,
    "entry_fill": 77090.344986,
    "last_price": 78992.75,
    "initial_capital": 10000.0,
    "entry_time": "2026-08-22 00:00:00+00:00",
    "trades": [],
}


def test_open_position_is_marked_to_market():
    """Equity must include the open profit, not just what has been banked."""
    out = venue_status._paper(FakeTable(OPEN_LONG))

    expected = 9990.0 * (78992.75 / 77090.344986)
    assert out["equity"] == pytest.approx(expected)
    assert out["equity"] == pytest.approx(10236.53, abs=0.01)  # the bot's own number
    assert out["realized"] == 9990.0                            # banked, still exposed
    assert out["equity"] > out["realized"]


def test_flat_book_reports_realized_unchanged():
    """With no position open the two numbers coincide, and must stay coincident."""
    out = venue_status._paper(FakeTable(FLAT))

    assert out["equity"] == 9990.0
    assert out["realized"] == 9990.0
    assert out["position_label"] == "FLAT"


def test_marking_inputs_are_published_for_the_page():
    """The page re-marks to a live price, so it needs the parts, not just a total."""
    out = venue_status._paper(FakeTable(OPEN_LONG))

    for field in ("entry_fill", "entry_equity", "last_price", "position"):
        assert out[field] is not None, f"{field} missing - page cannot re-mark"


def test_incomplete_state_falls_back_to_realized_instead_of_crashing():
    """A half-written book must not take the public endpoint down."""
    broken = {"side": 1, "realized": 9990.0, "initial_capital": 10000.0, "trades": []}

    out = venue_status._paper(FakeTable(broken))

    assert out["equity"] == 9990.0
