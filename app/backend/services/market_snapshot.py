"""
Market Snapshot (SSOT) - immutable snapshot of live indicators used across engines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import hashlib
import json
from time import time

# Lightweight in-process SSOT cache (TTL + versioned)
_SSOT_CACHE: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
SSOT_TTL_S = 5
SSOT_VER = "v4"  # BUMPED: 2025-11-01 - Added volume_ratio + price_change_24h to Indicators (Layer 5 v2.0 fix)


def _ok(a: float, b: float, eps: float) -> bool:
	try:
		return abs(float(a) - float(b)) <= float(eps)
	except Exception:
		return False


@dataclass(frozen=True)
class Indicators:
	 rsi: float
	 macd: float
	 bb_pos: float
	 volatility: float
	 trend_strength: float
	 volume_ratio: float  # CRITICAL: Required for Layer 5 v2.0
	 price_change_24h: float  # CRITICAL: Required for Layer 5 v2.0


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
			 "bb_position": self.indicators.bb_pos,  # Alias for consistency
			 "volatility": self.indicators.volatility,
			 "trend_strength": self.indicators.trend_strength,
			 "volume_ratio": self.indicators.volume_ratio,  # CRITICAL: Layer 5 v2.0
			 "price_change_24h": self.indicators.price_change_24h,  # CRITICAL: Layer 5 v2.0
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
		 volume_ratio=float(market_data.get("volume_ratio", 1.0)),  # CRITICAL: Layer 5 v2.0
		 price_change_24h=float(market_data.get("price_change_24h", market_data.get("price_change_percent_24h", 0.0))),  # CRITICAL: Layer 5 v2.0
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
		 "volume_ratio": indicators.volume_ratio,  # CRITICAL: Include in hash
		 "price_change_24h": indicators.price_change_24h,  # CRITICAL: Include in hash
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


def get_validated_snapshot(symbol: str, timeframe: str, live_market_data: Dict[str, Any]) -> MarketSnapshot:
	 """Return a versioned, TTL-cached SSOT snapshot validated against live indicators.
	 If cache is absent/stale/misaligned vs live, rebuild from live_market_data.
	 """
	 key = (symbol, timeframe, SSOT_VER)
	 now_ts = float(live_market_data.get("timestamp_epoch", time()))

	 # Compute live baseline from provided market_data
	 live = {
		 "rsi": float(live_market_data.get("rsi", 50.0)),
		 "bb_pos": float(live_market_data.get("bollinger_position", live_market_data.get("bb_position", 0.5))),
		 "macd_norm": float(live_market_data.get("macd", 0.0)),  # already normalized in our pipeline
	 }

	 snap_entry = _SSOT_CACHE.get(key)
	 should_rebuild = True

	 if snap_entry is not None:
		 age = now_ts - float(snap_entry.get("ts", 0))
		 if age <= SSOT_TTL_S:
			 # Sanity validation against live
			 if (_ok(snap_entry.get("rsi", 50.0), live["rsi"], 5.0) and
				 _ok(snap_entry.get("bb_pos", 0.5), live["bb_pos"], 0.15) and
				 _ok(snap_entry.get("macd_norm", 0.0), live["macd_norm"], 0.10)):
				 should_rebuild = False

	 if should_rebuild:
		 # Rebuild fresh snapshot from live
		 snapshot = build_snapshot_from_market_data(live_market_data, symbol=symbol, timeframe=timeframe, config_version=SSOT_VER)
		 snap_dict = {
			 "ts": now_ts,
			 "rsi": live["rsi"],
			 "bb_pos": live["bb_pos"],
			 "macd_norm": live["macd_norm"],
		 }
		 _SSOT_CACHE[key] = snap_dict
		 return snapshot

	 # Use cached, but return as MarketSnapshot object built from last good market_data
	 return build_snapshot_from_market_data(live_market_data, symbol=symbol, timeframe=timeframe, config_version=SSOT_VER)


