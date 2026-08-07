"""Parsers for non-price research data (funding / metrics / Coin Metrics).

Each trap observed in the real archives is pinned here against synthetic zips:
header rows present or absent, ms vs µs timestamps, and the duplicated rows
the 2020-09-01 metrics archive actually ships. No network — CI stays
deterministic.
"""

from __future__ import annotations

import io
import zipfile

import pandas as pd
import pytest

from app.backend.backtesting.external_data import (
    parse_funding_archive,
    parse_metrics_archive,
)


def _zip_bytes(csv_text: str, name: str = "data.csv") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(name, csv_text)
    return buf.getvalue()


# ------------------------------------------------------------------ funding --
def test_funding_parses_real_layout_with_header():
    payload = _zip_bytes(
        "calc_time,funding_interval_hours,last_funding_rate\n"
        "1577836800000,8,-0.00012359\n"
        "1577865600000,8,0.00010000\n")
    df = parse_funding_archive(payload)
    assert len(df) == 2
    assert df.index[0] == pd.Timestamp("2020-01-01 00:00:00", tz="UTC")
    assert df["funding_rate"].iloc[0] == pytest.approx(-0.00012359)
    assert df["funding_interval_hours"].iloc[0] == 8


def test_funding_parses_headerless_and_microsecond_variants():
    """Older files may drop the header; 2025+ kline files stamp µs — the same
    magnitude detection must hold here."""
    us = 1_577_836_800_000_000     # 2020-01-01 in microseconds
    payload = _zip_bytes(f"{us},8,0.0001\n")
    df = parse_funding_archive(payload)
    assert df.index[0] == pd.Timestamp("2020-01-01 00:00:00", tz="UTC")


# ------------------------------------------------------------------ metrics --
_METRICS_HEADER = ("create_time,symbol,sum_open_interest,sum_open_interest_value,"
                   "count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,"
                   "count_long_short_ratio,sum_taker_long_short_vol_ratio\n")
_METRICS_ROW = "2020-09-01 00:00:00,BTCUSDT,39080.231,456144339.23,1.17,1.23,1.35,0.78\n"


def test_metrics_deduplicates_the_doubled_rows_the_real_archive_ships():
    payload = _zip_bytes(_METRICS_HEADER + _METRICS_ROW + _METRICS_ROW)
    df = parse_metrics_archive(payload)
    assert len(df) == 1
    assert df.index[0] == pd.Timestamp("2020-09-01 00:00:00", tz="UTC")
    assert df["sum_open_interest"].iloc[0] == pytest.approx(39080.231)


def test_metrics_drops_symbol_and_keeps_all_numeric_columns():
    payload = _zip_bytes(_METRICS_HEADER + _METRICS_ROW)
    df = parse_metrics_archive(payload)
    assert "symbol" not in df.columns
    assert list(df.columns) == [
        "sum_open_interest", "sum_open_interest_value",
        "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio",
        "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]
