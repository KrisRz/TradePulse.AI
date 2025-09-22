"""
Market Snapshot (SSOT) - immutable snapshot of live indicators used across engines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
import hashlib
import json
from time import time


@dataclass(frozen=True)
class Indicators:
    rsi: float
    macd: float
    bb_pos: float
    volatility: float
    trend_strength: float


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    asof: float
    timeframe: str
    window_spec: str
    source: str
    config_version: str
    hash: str
    price: float
    volume: float
    indicators: Indicators

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "asof": self.asof,
            "timeframe": self.timeframe,
            "window_spec": self.window_spec,
            "source": self.source,
            "config_version": self.config_version,
            "hash": self.hash,
            "price": self.price,
            "volume": self.volume,
            "rsi": self.indicators.rsi,
            "macd": self.indicators.macd,
            "bollinger_position": self.indicators.bb_pos,
            "volatility": self.indicators.volatility,
            "trend_strength": self.indicators.trend_strength,
        }


def _stable_hash(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_snapshot_from_market_data(market_data: Dict[str, Any], symbol: str = "BTCUSDT",
                                   timeframe: str = "1m",
                                   window_spec: str = "RSI14|MACD12,26,9|BB20,2",
                                   source: str = "LiveMarketData",
                                   config_version: str = "v1") -> MarketSnapshot:
    asof_ts = market_data.get("timestamp_epoch", time())
    indicators = Indicators(
        rsi=float(market_data.get("rsi", 50.0)),
        macd=float(market_data.get("macd", 0.0)),
        bb_pos=float(market_data.get("bollinger_position", market_data.get("bb_position", 0.5))),
        volatility=float(market_data.get("volatility", 0.02)),
        trend_strength=float(market_data.get("trend_strength", 0.0)),
    )
    base = {
        "symbol": symbol,
        "asof": asof_ts,
        "timeframe": timeframe,
        "window_spec": window_spec,
        "source": source,
        "config_version": config_version,
        "price": float(market_data.get("price", market_data.get("current_price", 0.0))),
        "volume": float(market_data.get("volume", 0.0)),
        "rsi": indicators.rsi,
        "macd": indicators.macd,
        "bb_pos": indicators.bb_pos,
        "volatility": indicators.volatility,
        "trend_strength": indicators.trend_strength,
    }
    h = _stable_hash(base)
    return MarketSnapshot(
        symbol=symbol,
        asof=asof_ts,
        timeframe=timeframe,
        window_spec=window_spec,
        source=source,
        config_version=config_version,
        hash=h,
        price=base["price"],
        volume=base["volume"],
        indicators=indicators,
    )


