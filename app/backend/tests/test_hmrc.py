"""Tests for the HMRC share-identification rules.

The volume here will always be tiny — under two round trips a year on the
measured channel — so nothing is tested for scale. What is tested is the part
that produces a plausible-looking wrong number if it is subtly off: the ORDER in
which a disposal is matched. Same day first, then acquisitions in the 30 days
*after* the disposal, and only then the pool. Get the precedence wrong and every
figure still looks reasonable.

The 30-day rule is the one worth staring at: it matches forward in time, against
purchases that had not happened yet when the sale was made. A trend-following bot
that exits on a signal and re-enters three weeks later triggers it without anyone
intending to.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.backend.reporting.hmrc import (
    ACQUISITION,
    DISPOSAL,
    Transaction,
    match,
    transactions_from_fills,
    write_csv,
)


def t(day, side, qty, price, fee="0", fee_asset="USDT", hour=12, order_id=""):
    return Transaction(
        when=datetime(2026, 1, day, hour, tzinfo=timezone.utc),
        side=side, qty=Decimal(str(qty)), price=Decimal(str(price)),
        fee=Decimal(str(fee)) if fee_asset in ("USDT", "USD", "GBP") else Decimal("0"),
        fee_raw=Decimal(str(fee)), fee_asset=fee_asset, order_id=order_id,
    )


# ------------------------------------------------------------ Section 104 pool --
def test_the_pool_costs_a_disposal_at_the_average_of_what_is_in_it():
    """Two buys at different prices, one sale: cost is the pooled average."""
    reports, summary = match([
        t(1, ACQUISITION, 1, 100),
        t(2, ACQUISITION, 1, 200),
        t(20, DISPOSAL, 1, 300),
    ])

    assert [m.rule for m in reports[0].matches] == ["s104"]
    assert reports[0].cost == Decimal("150")        # not 100, not 200
    assert reports[0].gain == Decimal("150")
    assert summary["pool_qty"] == Decimal("1")
    assert summary["pool_unit_cost"] == Decimal("150")


def test_the_pool_keeps_its_average_after_a_partial_disposal():
    reports, summary = match([
        t(1, ACQUISITION, 2, 100),
        t(2, ACQUISITION, 2, 200),
        t(20, DISPOSAL, 1, 400),
    ])

    assert reports[0].cost == Decimal("150")
    assert summary["pool_qty"] == Decimal("3")
    assert summary["pool_unit_cost"] == Decimal("150")   # unchanged by the sale


# ------------------------------------------------------------- the same-day rule --
def test_a_purchase_on_the_day_of_the_sale_wins_over_the_pool():
    """Precedence, not chronology: the same-day buy is matched first."""
    reports, _ = match([
        t(1, ACQUISITION, 1, 100),                       # goes to the pool
        t(20, DISPOSAL, 1, 300, hour=9),
        t(20, ACQUISITION, 1, 250, hour=15),             # same day, AFTER the sale
    ])

    assert [m.rule for m in reports[0].matches] == ["same-day"]
    assert reports[0].cost == Decimal("250")             # not the pool's 100
    assert reports[0].gain == Decimal("50")


def test_same_day_uses_UK_days_not_UTC_days():
    """During BST a 23:30 UTC fill belongs to the NEXT UK day.

    Truncating the UTC timestamp would put these two on the same day and match
    them; in UK time they are a day apart and must not be.
    """
    sale = Transaction(when=datetime(2026, 7, 10, 23, 30, tzinfo=timezone.utc),
                       side=DISPOSAL, qty=Decimal("1"), price=Decimal("300"))
    buy = Transaction(when=datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc),
                      side=ACQUISITION, qty=Decimal("1"), price=Decimal("250"))

    assert sale.uk_day != buy.uk_day                     # 11 July vs 10 July
    reports, _ = match([buy, sale])
    assert [m.rule for m in reports[0].matches] == ["s104"]


# ------------------------------------------------- the bed-and-breakfast rule --
def test_a_repurchase_within_thirty_days_is_matched_against_the_sale():
    """The counter-intuitive one: it matches an acquisition that came LATER."""
    reports, _ = match([
        t(1, ACQUISITION, 1, 100),                       # pool
        t(10, DISPOSAL, 1, 300),
        t(25, ACQUISITION, 1, 280),                      # 15 days later
    ])

    assert [m.rule for m in reports[0].matches] == ["30-day"]
    assert reports[0].cost == Decimal("280")
    assert reports[0].gain == Decimal("20")


def test_a_repurchase_after_thirty_days_falls_through_to_the_pool():
    """One day past the window changes which cost is used — and by a lot."""
    reports, _ = match([
        t(1, ACQUISITION, 1, 100),
        t(2, DISPOSAL, 1, 300),
        Transaction(when=datetime(2026, 2, 2, 12, tzinfo=timezone.utc),   # +31 days
                    side=ACQUISITION, qty=Decimal("1"), price=Decimal("280")),
    ])

    assert [m.rule for m in reports[0].matches] == ["s104"]
    assert reports[0].cost == Decimal("100")


def test_the_boundary_day_is_inside_the_window():
    reports, _ = match([
        t(1, DISPOSAL, 1, 300),
        Transaction(when=datetime(2026, 1, 31, 12, tzinfo=timezone.utc),   # +30 days
                    side=ACQUISITION, qty=Decimal("1"), price=Decimal("280")),
    ])
    assert [m.rule for m in reports[0].matches] == ["30-day"]


# ------------------------------------------------------------------ precedence --
def test_one_disposal_can_span_all_three_rules_in_order():
    """The whole point of the tool, in one case."""
    reports, _ = match([
        t(1, ACQUISITION, 1, 100),          # pool
        t(20, DISPOSAL, 3, 300, hour=9),
        t(20, ACQUISITION, 1, 250, hour=15),  # same day
        t(30, ACQUISITION, 1, 280),           # within 30 days
    ])

    assert [m.rule for m in reports[0].matches] == ["same-day", "30-day", "s104"]
    assert [m.qty for m in reports[0].matches] == [Decimal("1")] * 3
    assert reports[0].cost == Decimal("630")   # 250 + 280 + 100


# ------------------------------------------------------------------------ fees --
def test_fees_widen_the_cost_and_narrow_the_proceeds():
    """A buy fee is an allowable cost; a sell fee comes off the proceeds."""
    reports, _ = match([
        t(1, ACQUISITION, 1, 100, fee="2"),
        t(20, DISPOSAL, 1, 300, fee="3"),
    ])

    assert reports[0].cost == Decimal("102")
    assert reports[0].proceeds == Decimal("297")
    assert reports[0].gain == Decimal("195")


def test_a_fee_billed_in_another_asset_is_flagged_with_its_amount():
    """Paying in BNB is a disposal of BNB — reported, never silently dropped."""
    reports, _ = match([
        t(1, ACQUISITION, 1, 100, fee="0.0002", fee_asset="BNB"),
        t(20, DISPOSAL, 1, 300, fee="0.0003", fee_asset="BNB"),
    ])

    assert reports[0].cost == Decimal("100")     # BNB not folded into the cost
    assert reports[0].proceeds == Decimal("300")
    assert reports[0].fee_asset == "BNB"
    assert reports[0].fee_other_asset == Decimal("0.0003")


# ------------------------------------------------------------- honest failures --
def test_selling_more_than_was_ever_acquired_is_reported_not_swallowed():
    _reports, summary = match([
        t(1, ACQUISITION, 1, 100),
        t(20, DISPOSAL, 3, 300),
    ])
    assert summary["unmatched_disposals"] == [{"order_id": "", "qty": "2"}]


# --------------------------------------------------------- fills -> the report --
def test_the_real_fill_log_shape_is_understood():
    """Exactly what persist_execution_evidence writes into DynamoDB."""
    fills = [
        {"time": "2026-08-06 16:00:00+00:00", "side": 1, "qty": 0.0031,
         "actual_price": 64474.17, "fee_paid": 0.00025326, "fee_asset": "BNB",
         "order_id": "54510109086"},
        {"time": "2026-08-12 00:00:00+00:00", "side": -1, "qty": 0.0031,
         "actual_price": 63807.54, "fee_paid": 0.00024206, "fee_asset": "BNB",
         "order_id": "55900375232"},
    ]
    reports, summary = match(transactions_from_fills(fills))

    assert len(reports) == 1
    assert reports[0].order_id == "55900375232"
    assert reports[0].gain < 0                   # the real trade lost money
    assert summary["pool_qty"] == Decimal("0")   # bought 0.0031, sold 0.0031


def test_the_csv_says_which_currency_it_is_in(tmp_path):
    """A column headed "gain" that is quietly in USDT is worse than no column."""
    reports, _ = match([t(1, ACQUISITION, 1, 100), t(20, DISPOSAL, 1, 300)])
    out = tmp_path / "r.csv"
    write_csv(out, reports, currency="USDT")

    rows = list(csv.reader(out.open()))
    assert "USDT" in rows[0][0] and "NOT converted" in rows[0][0]
    assert rows[1][0] == "date_uk"
    assert rows[2][8] == "200.00"


def test_an_fx_rate_converts_every_money_column(tmp_path):
    reports, _ = match([t(1, ACQUISITION, 1, 100), t(20, DISPOSAL, 1, 300)])
    out = tmp_path / "r.csv"
    write_csv(out, reports, currency="USDT", fx=lambda _day: Decimal("0.8"))

    rows = list(csv.reader(out.open()))
    assert "GBP" in rows[0][0] and "NOT converted" not in rows[0][0]
    assert rows[2][6] == "240.00"    # 300 * 0.8
    assert rows[2][8] == "160.00"    # 200 * 0.8
