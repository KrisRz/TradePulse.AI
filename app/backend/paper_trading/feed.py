"""Live market data feeds — public candles, no API key required.

Binance klines feed the original channels. Kraken OHLC feeds the Kraken channel
(2026-10-30, KRAKEN.md): the bot trades XBT/GBP there, so it must decide on
Kraken's own bars. Measured before switching: EMA20/100 on Kraken XBT/GBP agrees
with the Binance-derived series on 99.6% of days
(docs/KRAKEN_VENUE_RESULTS_2026-10-30.md, M3).
"""

from __future__ import annotations

import pandas as pd
import requests

_BASE = "https://api.binance.com/api/v3/klines"
_OHLCV = ["open", "high", "low", "close", "volume"]

# Strategy timeframe -> Binance interval string.
_INTERVAL = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h", "1d": "1d",
}


def fetch_klines(
    symbol: str = "BTCUSDT",
    timeframe: str = "1d",
    limit: int = 500,
    include_open_bar: bool = False,
    timeout: float = 10.0,
) -> pd.DataFrame:
    """Fetch recent OHLCV bars, normalised like ``backtesting.data``.

    By default the still-forming current bar is dropped (``include_open_bar``),
    so the strategy only ever sees *closed* bars — matching the backtest, where
    every bar is complete.
    """
    if timeframe not in _INTERVAL:
        raise ValueError(f"Unsupported timeframe {timeframe!r}")
    resp = requests.get(
        _BASE,
        params={"symbol": symbol, "interval": _INTERVAL[timeframe], "limit": limit},
        timeout=timeout,
    )
    resp.raise_for_status()
    rows = resp.json()
    if not rows:
        raise RuntimeError("Binance returned no klines")

    df = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore",
    ])
    idx = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.set_index(idx)[_OHLCV].astype(float)
    df.index.name = "time"

    if not include_open_bar:
        # The last kline from Binance is the current, still-open bar.
        df = df.iloc[:-1]
    return df


_KRAKEN_BASE = "https://api.kraken.com/0/public/OHLC"
# Strategy timeframe -> Kraken interval in minutes.
_KRAKEN_INTERVAL = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
#: Kraken keeps only the most recent 720 candles per interval.
KRAKEN_MAX_BARS = 720


def fetch_kraken_ohlc(
    pair: str = "XBTGBP",
    timeframe: str = "1d",
    limit: int = 500,
    include_open_bar: bool = False,
    timeout: float = 10.0,
) -> pd.DataFrame:
    """Recent Kraken candles, normalised like :func:`fetch_klines`.

    ``limit`` means what it means for Binance — bars *including* the open one —
    so ``limit=400`` yields 399 closed bars on either venue and the bot's
    truncated-history guard works unchanged. Kraken returns at most 720 candles
    whatever is asked; the last one is the still-forming bar.
    """
    if timeframe not in _KRAKEN_INTERVAL:
        raise ValueError(f"Unsupported timeframe {timeframe!r}")
    resp = requests.get(
        _KRAKEN_BASE,
        params={"pair": pair, "interval": _KRAKEN_INTERVAL[timeframe]},
        timeout=timeout,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("error"):
        raise RuntimeError(f"Kraken OHLC error: {body['error']}")
    result = body.get("result") or {}
    rows = next((v for k, v in result.items() if k != "last"), None)
    if not rows:
        raise RuntimeError("Kraken returned no candles")

    df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close",
                                     "vwap", "volume", "count"])
    idx = pd.to_datetime(df["time"].astype(int), unit="s", utc=True)
    df = df.set_index(idx)[_OHLCV].astype(float)
    df.index.name = "time"

    if not include_open_bar:
        df = df.iloc[:-1]
        return df.iloc[-(limit - 1):] if limit > 1 else df.iloc[0:0]
    return df.iloc[-limit:]


def fetch_bars(source: str, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    """Closed bars from the named venue's public feed."""
    if source == "binance":
        return fetch_klines(symbol, timeframe, limit=limit)
    if source == "kraken":
        return fetch_kraken_ohlc(symbol, timeframe, limit=limit)
    raise ValueError(f"Unknown feed source {source!r}")
