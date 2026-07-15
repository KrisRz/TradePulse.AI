"""Technical indicators for the backtesting layer.

Pure pandas/numpy functions — no app, DynamoDB or TensorFlow imports, so the
backtester stays fast and standalone. All functions are backward-looking only
(no look-ahead): the value at index t depends solely on data up to and
including t. Conventions match common industry defaults (Wilder's RSI/ATR,
classic 12/26/9 MACD).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential moving average (span convention)."""
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window=period, min_periods=period).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index using Wilder's smoothing (RMA).

    Returns values in [0, 100]. The first `period` values are NaN.
    """
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    # Wilder's smoothing == EMA with alpha = 1/period
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    # When avg_loss == 0 (only gains) RSI is 100; when avg_gain == 0 it is 0.
    out = out.where(avg_loss != 0.0, 100.0)
    out = out.where(avg_gain != 0.0, out.where(avg_loss == 0.0, 0.0))
    return out


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """True Range: max of the three classic ranges."""
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range using Wilder's smoothing."""
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Classic MACD. Returns columns: macd, signal, hist."""
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def bollinger(close: pd.Series, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """Bollinger Bands. Returns columns: mid, upper, lower, pctb.

    `pctb` is the %B position of price within the bands (0 = lower, 1 = upper).
    """
    mid = sma(close, period)
    std = close.rolling(window=period, min_periods=period).std(ddof=0)
    upper = mid + num_std * std
    lower = mid - num_std * std
    width = (upper - lower).replace(0.0, np.nan)
    pctb = (close - lower) / width
    return pd.DataFrame({"mid": mid, "upper": upper, "lower": lower, "pctb": pctb})


def donchian(high: pd.Series, low: pd.Series, period: int = 20) -> pd.DataFrame:
    """Donchian channel over the PRIOR `period` bars (excludes current bar).

    Excluding the current bar is what makes a breakout test meaningful:
    `upper` is the highest high of the last `period` COMPLETED bars, so
    `close > upper` genuinely means "broke above the recent range".
    """
    upper = high.rolling(window=period, min_periods=period).max().shift(1)
    lower = low.rolling(window=period, min_periods=period).min().shift(1)
    mid = (upper + lower) / 2.0
    return pd.DataFrame({"upper": upper, "lower": lower, "mid": mid})


def realized_volatility(close: pd.Series, period: int = 20) -> pd.Series:
    """Rolling std of log returns — a simple volatility proxy per bar."""
    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(window=period, min_periods=period).std(ddof=0)
