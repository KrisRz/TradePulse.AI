"""Market regime detection — trend / range / volatile.

Used to *route* strategies: a trend-follower should only trade in trends, a
mean-reverter only in ranges, and nobody should fight a volatility spike. All
inputs are backward-looking (ADX, ATR relative to its own rolling median), so
the classification at bar t never peeks at the future.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .indicators import adx as _adx, atr as _atr

TREND = "trend"
RANGE = "range"
VOLATILE = "volatile"


def classify(
    df: pd.DataFrame,
    adx_period: int = 14,
    adx_threshold: float = 25.0,
    vol_window: int = 100,
    vol_mult: float = 1.8,
) -> pd.Series:
    """Return a Series of {'trend','range','volatile'} aligned to df.index.

    Rules (priority order):
    1. VOLATILE if normalised ATR (ATR/close) exceeds ``vol_mult`` times its
       own rolling median over ``vol_window`` bars — a relative spike.
    2. TREND if ADX >= ``adx_threshold``.
    3. RANGE otherwise.

    Bars before the indicators warm up are labelled RANGE (the neutral default).
    """
    adx_df = _adx(df["high"], df["low"], df["close"], adx_period)
    atr_norm = _atr(df["high"], df["low"], df["close"], adx_period) / df["close"]
    atr_median = atr_norm.rolling(window=vol_window, min_periods=vol_window // 2).median()

    is_volatile = atr_norm > (vol_mult * atr_median)
    is_trend = adx_df["adx"] >= adx_threshold

    regime = pd.Series(RANGE, index=df.index, dtype=object)
    regime = regime.mask(is_trend.fillna(False), TREND)
    regime = regime.mask(is_volatile.fillna(False), VOLATILE)  # volatile wins
    return regime


def regime_stats(regime: pd.Series) -> dict:
    """Fraction of bars spent in each regime (for reporting)."""
    counts = regime.value_counts(normalize=True)
    return {r: float(counts.get(r, 0.0)) for r in (TREND, RANGE, VOLATILE)}
