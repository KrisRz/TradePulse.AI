"""Integrity validator tests — every defect class is caught, clean data passes.

Synthetic frames only (the sanctioned exception to the no-mocks rule): each
test builds the smallest dataset exhibiting exactly one defect.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.backend.backtesting.integrity import (
    infer_spacing, validate_file, validate_frame)

HOUR = pd.Timedelta(hours=1)


def make_frame(n: int = 48, start: str = "2021-01-01") -> pd.DataFrame:
    idx = pd.date_range(start, periods=n, freq="1h", tz="UTC")
    close = 100.0 + np.arange(n, dtype=float)
    df = pd.DataFrame({
        "open": close - 0.5,
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
        "volume": np.full(n, 10.0),
    }, index=idx)
    df.index.name = "timestamp"
    return df


def test_clean_frame_passes():
    rep = validate_frame(make_frame(), HOUR)
    assert rep.ok and not rep.gaps
    assert rep.bars == 48


def test_gap_reported_not_failed():
    df = make_frame()
    df = df.drop(df.index[10:13])   # 3 missing bars
    rep = validate_frame(df, HOUR)
    assert rep.ok                    # gaps are findings, not hard failures
    assert len(rep.gaps) == 1 and "3 bar(s) missing" in rep.gaps[0]


def test_nan_fails():
    df = make_frame()
    df.iloc[5, df.columns.get_loc("close")] = np.nan
    rep = validate_frame(df, HOUR)
    assert not rep.ok and any("NaN" in f for f in rep.failures)


def test_duplicate_timestamps_fail():
    df = make_frame()
    df = pd.concat([df, df.iloc[[7]]]).sort_index()
    rep = validate_frame(df, HOUR)
    assert not rep.ok and any("duplicated" in f for f in rep.failures)


def test_unsorted_index_fails():
    df = make_frame().iloc[::-1]
    rep = validate_frame(df, HOUR)
    assert not rep.ok and any("monotonically" in f for f in rep.failures)


def test_ohlc_violations_fail():
    df = make_frame()
    df.iloc[3, df.columns.get_loc("high")] = 0.5    # high < close
    df.iloc[4, df.columns.get_loc("low")] = 9999.0  # low > open
    rep = validate_frame(df, HOUR)
    assert any("high <" in f for f in rep.failures)
    assert any("low >" in f for f in rep.failures)


def test_nonpositive_price_and_negative_volume_fail():
    df = make_frame()
    df.iloc[2, df.columns.get_loc("open")] = 0.0
    df.iloc[3, df.columns.get_loc("volume")] = -1.0
    rep = validate_frame(df, HOUR)
    assert any("non-positive prices" in f for f in rep.failures)
    assert any("negative volume" in f for f in rep.failures)


def test_naive_index_fails():
    df = make_frame()
    df.index = df.index.tz_localize(None)
    rep = validate_frame(df, HOUR)
    assert any("timezone" in f for f in rep.failures)


def test_infer_spacing_from_filename(tmp_path):
    df = make_frame()
    assert infer_spacing(df, tmp_path / "BTCUSDT_1h.csv") == HOUR
    assert infer_spacing(df, tmp_path / "BTCUSDT_1d.csv") == pd.Timedelta(days=1)
    # No token in the name -> falls back to the modal observed delta.
    assert infer_spacing(df, tmp_path / "mystery.csv") == HOUR


def test_validate_file_roundtrip(tmp_path):
    path = tmp_path / "BTCUSDT_1h.csv"
    make_frame().to_csv(path)
    rep = validate_file(path)
    assert rep.ok and not rep.gaps and rep.bars == 48


def test_validate_file_catches_source_duplicates(tmp_path):
    df = make_frame()
    path = tmp_path / "BTCUSDT_1h.csv"
    pd.concat([df, df.iloc[[7]]]).sort_index().to_csv(path)
    # load_csv silently dedupes, so only the raw-source check can catch this.
    rep = validate_file(path)
    assert not rep.ok
    assert any("source file" in f for f in rep.failures)
