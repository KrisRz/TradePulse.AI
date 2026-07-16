"""Live market data feed — Binance public klines (no API key required)."""

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
