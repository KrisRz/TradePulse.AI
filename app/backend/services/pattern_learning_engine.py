"""
TradePulse.AI Pattern Learning Engine
===================================

Professional pattern recognition and learning service for enterprise trading system.
Learns and identifies trading patterns using real live data.

Author: TradePulse.AI Development Team
Version: 1.0.0 (Production)
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import defaultdict

from app.backend.core.database import get_database_client
from app.backend.core.config import get_settings
from app.backend.services.live_market_data import get_live_bitcoin_price, get_live_candlestick_data
from app.backend.core.lazy import LazyProxy

logger = logging.getLogger(__name__)
settings = get_settings()

class PatternType(Enum):
    """Trading pattern types"""
    BULLISH_ENGULFING = "bullish_engulfing"
    BEARISH_ENGULFING = "bearish_engulfing"
    HAMMER = "hammer"
    DOJI = "doji"
    ASCENDING_TRIANGLE = "ascending_triangle"
    DESCENDING_TRIANGLE = "descending_triangle"
    HEAD_SHOULDERS = "head_shoulders"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    SUPPORT_BOUNCE = "support_bounce"
    RESISTANCE_BREAK = "resistance_break"

@dataclass
class TradingPattern:
    """Trading pattern data structure"""
    pattern_id: str
    pattern_type: PatternType
    timestamp: int
    symbol: str
    confidence: float
    price_at_detection: float
    timeframe: str
    pattern_data: Dict[str, Any] = field(default_factory=dict)
    success_rate: float = 0.0
    avg_profit: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'pattern_id': self.pattern_id,
            'pattern_type': self.pattern_type.value,
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'confidence': self.confidence,
            'price_at_detection': self.price_at_detection,
            'timeframe': self.timeframe,
            'pattern_data': self.pattern_data,
            'success_rate': self.success_rate,
            'avg_profit': self.avg_profit,
            'metadata': self.metadata
        }

class PatternLearningEngine:
    """
    Professional pattern learning engine for TradePulse.AI
    Identifies and learns from trading patterns using real data only
    """
    
    def __init__(self):
        self.db_client = get_database_client()
        self.detected_patterns: List[TradingPattern] = []
        self.pattern_stats = defaultdict(lambda: {
            'count': 0,
            'success_count': 0,
            'success_rate': 0.0,
            'avg_profit': 0.0,
            'total_profit': 0.0
        })
        logger.info("🔧 PatternLearningEngine initialized")
    
    async def analyze_patterns(self, timeframe: str = '1h') -> List[TradingPattern]:
        """
        Analyze market data for trading patterns
        
        Args:
            timeframe: Timeframe for pattern analysis
            
        Returns:
            List of detected patterns
        """
        try:
            # Get recent candlestick data
            candles = await get_live_candlestick_data('BTCUSDT', timeframe, limit=100)
            
            if len(candles) < 20:  # Need minimum data for pattern analysis
                logger.warning("Insufficient data for pattern analysis")
                return []
            
            detected_patterns = []
            current_price = await get_live_bitcoin_price()
            
            # Analyze different pattern types
            patterns = [
                await self._detect_engulfing_patterns(candles, current_price, timeframe),
                await self._detect_doji_patterns(candles, current_price, timeframe),
                await self._detect_hammer_patterns(candles, current_price, timeframe),
                await self._detect_support_resistance_patterns(candles, current_price, timeframe)
            ]
            
            # Flatten and filter patterns
            for pattern_list in patterns:
                if pattern_list:
                    detected_patterns.extend(pattern_list)
            
            # Store detected patterns
            for pattern in detected_patterns:
                await self._store_pattern(pattern)
                self.detected_patterns.append(pattern)
            
            logger.info(f"📊 Detected {len(detected_patterns)} patterns in {timeframe} timeframe")
            
            return detected_patterns
            
        except Exception as e:
            logger.error(f"❌ Error analyzing patterns: {e}")
            return []
    
    async def _detect_engulfing_patterns(self, candles: List[Dict], current_price: float, timeframe: str) -> List[TradingPattern]:
        """Detect bullish/bearish engulfing patterns"""
        patterns = []
        
        try:
            for i in range(1, len(candles)):
                prev_candle = candles[i-1]
                curr_candle = candles[i]
                
                prev_open = float(prev_candle['open'])
                prev_close = float(prev_candle['close'])
                curr_open = float(curr_candle['open'])
                curr_close = float(curr_candle['close'])
                
                # Bullish engulfing
                if (prev_close < prev_open and  # Previous candle bearish
                    curr_close > curr_open and  # Current candle bullish
                    curr_open < prev_close and  # Current opens below previous close
                    curr_close > prev_open):    # Current closes above previous open
                    
                    pattern = TradingPattern(
                        pattern_id=f"engulf_bull_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                        pattern_type=PatternType.BULLISH_ENGULFING,
                        timestamp=int(curr_candle['timestamp']) // 1000,
                        symbol='BTCUSDT',
                        confidence=self._calculate_engulfing_confidence(prev_candle, curr_candle),
                        price_at_detection=current_price,
                        timeframe=timeframe,
                        pattern_data={
                            'prev_candle': prev_candle,
                            'curr_candle': curr_candle,
                            'engulfing_ratio': abs(curr_close - curr_open) / abs(prev_close - prev_open)
                        }
                    )
                    patterns.append(pattern)
                
                # Bearish engulfing
                elif (prev_close > prev_open and  # Previous candle bullish
                      curr_close < curr_open and  # Current candle bearish
                      curr_open > prev_close and  # Current opens above previous close
                      curr_close < prev_open):    # Current closes below previous open
                    
                    pattern = TradingPattern(
                        pattern_id=f"engulf_bear_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                        pattern_type=PatternType.BEARISH_ENGULFING,
                        timestamp=int(curr_candle['timestamp']) // 1000,
                        symbol='BTCUSDT',
                        confidence=self._calculate_engulfing_confidence(prev_candle, curr_candle),
                        price_at_detection=current_price,
                        timeframe=timeframe,
                        pattern_data={
                            'prev_candle': prev_candle,
                            'curr_candle': curr_candle,
                            'engulfing_ratio': abs(curr_close - curr_open) / abs(prev_close - prev_open)
                        }
                    )
                    patterns.append(pattern)
            
        except Exception as e:
            logger.error(f"❌ Error detecting engulfing patterns: {e}")
        
        return patterns
    
    async def _detect_doji_patterns(self, candles: List[Dict], current_price: float, timeframe: str) -> List[TradingPattern]:
        """Detect doji patterns"""
        patterns = []
        
        try:
            for candle in candles[-5:]:  # Check last 5 candles
                open_price = float(candle['open'])
                close_price = float(candle['close'])
                high_price = float(candle['high'])
                low_price = float(candle['low'])
                
                body_size = abs(close_price - open_price)
                total_range = high_price - low_price
                
                # Doji: small body relative to range
                if total_range > 0 and body_size / total_range < 0.1:
                    confidence = 1.0 - (body_size / total_range * 10)  # Higher confidence for smaller body
                    
                    pattern = TradingPattern(
                        pattern_id=f"doji_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                        pattern_type=PatternType.DOJI,
                        timestamp=int(candle['timestamp']) // 1000,
                        symbol='BTCUSDT',
                        confidence=confidence,
                        price_at_detection=current_price,
                        timeframe=timeframe,
                        pattern_data={
                            'candle': candle,
                            'body_size': body_size,
                            'total_range': total_range,
                            'body_ratio': body_size / total_range if total_range > 0 else 0
                        }
                    )
                    patterns.append(pattern)
            
        except Exception as e:
            logger.error(f"❌ Error detecting doji patterns: {e}")
        
        return patterns
    
    async def _detect_hammer_patterns(self, candles: List[Dict], current_price: float, timeframe: str) -> List[TradingPattern]:
        """Detect hammer patterns"""
        patterns = []
        
        try:
            for candle in candles[-5:]:  # Check last 5 candles
                open_price = float(candle['open'])
                close_price = float(candle['close'])
                high_price = float(candle['high'])
                low_price = float(candle['low'])
                
                body_top = max(open_price, close_price)
                body_bottom = min(open_price, close_price)
                
                upper_shadow = high_price - body_top
                lower_shadow = body_bottom - low_price
                body_size = abs(close_price - open_price)
                
                # Hammer: long lower shadow, small body, minimal upper shadow
                if (lower_shadow > body_size * 2 and  # Lower shadow at least 2x body
                    upper_shadow < body_size * 0.5 and  # Upper shadow less than half body
                    body_size > 0):  # Some body size
                    
                    confidence = min(lower_shadow / (body_size * 2), 1.0)
                    
                    pattern = TradingPattern(
                        pattern_id=f"hammer_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                        pattern_type=PatternType.HAMMER,
                        timestamp=int(candle['timestamp']) // 1000,
                        symbol='BTCUSDT',
                        confidence=confidence,
                        price_at_detection=current_price,
                        timeframe=timeframe,
                        pattern_data={
                            'candle': candle,
                            'body_size': body_size,
                            'upper_shadow': upper_shadow,
                            'lower_shadow': lower_shadow,
                            'shadow_ratio': lower_shadow / body_size if body_size > 0 else 0
                        }
                    )
                    patterns.append(pattern)
            
        except Exception as e:
            logger.error(f"❌ Error detecting hammer patterns: {e}")
        
        return patterns
    
    async def _detect_support_resistance_patterns(self, candles: List[Dict], current_price: float, timeframe: str) -> List[TradingPattern]:
        """Detect support and resistance patterns"""
        patterns = []
        
        try:
            if len(candles) < 20:
                return patterns
            
            # Calculate support and resistance levels
            lows = [float(candle['low']) for candle in candles]
            highs = [float(candle['high']) for candle in candles]
            
            # Find support levels (local minima)
            support_levels = self._find_support_levels(lows)
            resistance_levels = self._find_resistance_levels(highs)
            
            # Check for support bounce
            recent_low = min(lows[-5:])  # Lowest in last 5 candles
            for support in support_levels:
                if abs(recent_low - support) / support < 0.01:  # Within 1% of support
                    pattern = TradingPattern(
                        pattern_id=f"support_bounce_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                        pattern_type=PatternType.SUPPORT_BOUNCE,
                        timestamp=int(datetime.now(timezone.utc).timestamp()),
                        symbol='BTCUSDT',
                        confidence=0.7,
                        price_at_detection=current_price,
                        timeframe=timeframe,
                        pattern_data={
                            'support_level': support,
                            'recent_low': recent_low,
                            'distance_pct': abs(recent_low - support) / support * 100
                        }
                    )
                    patterns.append(pattern)
                    break
            
            # Check for resistance break
            recent_high = max(highs[-5:])  # Highest in last 5 candles
            for resistance in resistance_levels:
                if recent_high > resistance and (recent_high - resistance) / resistance < 0.02:  # Within 2% above resistance
                    pattern = TradingPattern(
                        pattern_id=f"resistance_break_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                        pattern_type=PatternType.RESISTANCE_BREAK,
                        timestamp=int(datetime.now(timezone.utc).timestamp()),
                        symbol='BTCUSDT',
                        confidence=0.75,
                        price_at_detection=current_price,
                        timeframe=timeframe,
                        pattern_data={
                            'resistance_level': resistance,
                            'recent_high': recent_high,
                            'break_distance_pct': (recent_high - resistance) / resistance * 100
                        }
                    )
                    patterns.append(pattern)
                    break
            
        except Exception as e:
            logger.error(f"❌ Error detecting support/resistance patterns: {e}")
        
        return patterns
    
    def _calculate_engulfing_confidence(self, prev_candle: Dict, curr_candle: Dict) -> float:
        """Calculate confidence for engulfing pattern"""
        try:
            prev_body = abs(float(prev_candle['close']) - float(prev_candle['open']))
            curr_body = abs(float(curr_candle['close']) - float(curr_candle['open']))
            
            if prev_body == 0:
                return 0.5
            
            engulfing_ratio = curr_body / prev_body
            confidence = min(engulfing_ratio / 2.0, 1.0)  # Max confidence when current body is 2x previous
            
            return max(confidence, 0.3)  # Minimum confidence of 30%
            
        except Exception:
            return 0.5
    
    def _find_support_levels(self, lows: List[float]) -> List[float]:
        """Find support levels from price lows"""
        if len(lows) < 10:
            return []
        
        support_levels = []
        window = 5
        
        for i in range(window, len(lows) - window):
            if lows[i] == min(lows[i-window:i+window+1]):
                # Check if this level has been tested multiple times
                level = lows[i]
                test_count = sum(1 for low in lows if abs(low - level) / level < 0.02)
                
                if test_count >= 2:  # Level tested at least twice
                    support_levels.append(level)
        
        # Remove duplicate levels (within 1% of each other)
        filtered_levels = []
        for level in sorted(set(support_levels)):
            if not any(abs(level - existing) / existing < 0.01 for existing in filtered_levels):
                filtered_levels.append(level)
        
        return filtered_levels[-5:]  # Return top 5 support levels
    
    def _find_resistance_levels(self, highs: List[float]) -> List[float]:
        """Find resistance levels from price highs"""
        if len(highs) < 10:
            return []
        
        resistance_levels = []
        window = 5
        
        for i in range(window, len(highs) - window):
            if highs[i] == max(highs[i-window:i+window+1]):
                # Check if this level has been tested multiple times
                level = highs[i]
                test_count = sum(1 for high in highs if abs(high - level) / level < 0.02)
                
                if test_count >= 2:  # Level tested at least twice
                    resistance_levels.append(level)
        
        # Remove duplicate levels (within 1% of each other)
        filtered_levels = []
        for level in sorted(set(resistance_levels), reverse=True):
            if not any(abs(level - existing) / existing < 0.01 for existing in filtered_levels):
                filtered_levels.append(level)
        
        return filtered_levels[-5:]  # Return top 5 resistance levels
    
    async def _store_pattern(self, pattern: TradingPattern) -> None:
        """Store detected pattern in database"""
        try:
            item = {
                'PK': f'PATTERN#{pattern.symbol}',
                'SK': f'{pattern.timestamp}#{pattern.pattern_id}',
                'pattern_id': pattern.pattern_id,
                'pattern_type': pattern.pattern_type.value,
                'timestamp': pattern.timestamp,
                'symbol': pattern.symbol,
                'confidence': pattern.confidence,
                'price_at_detection': pattern.price_at_detection,
                'timeframe': pattern.timeframe,
                'pattern_data': json.dumps(pattern.pattern_data),
                'success_rate': pattern.success_rate,
                'avg_profit': pattern.avg_profit,
                'metadata': json.dumps(pattern.metadata),
                'date': datetime.fromtimestamp(pattern.timestamp, tz=timezone.utc).strftime('%Y-%m-%d'),
                'TTL': pattern.timestamp + (90 * 24 * 60 * 60)  # 90 days retention
            }
            
            table = self.db_client.get_table('trading_patterns')
            table.put_item(Item=item)
            
        except Exception as e:
            logger.error(f"❌ Error storing pattern: {e}")
    
    def get_recent_patterns(self, limit: int = 20) -> List[TradingPattern]:
        """Get recent detected patterns"""
        return self.detected_patterns[-limit:]
    
    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get pattern detection statistics"""
        return dict(self.pattern_stats)
    
    async def get_patterns_by_type(self, pattern_type: PatternType, days: int = 7) -> List[Dict[str, Any]]:
        """Get patterns by type from database"""
        try:
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            table = self.db_client.get_table('trading_patterns')
            
            response = table.scan(
                FilterExpression='pattern_type = :pattern_type AND #ts BETWEEN :start_ts AND :end_ts',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':pattern_type': pattern_type.value,
                    ':start_ts': int(start_date.timestamp()),
                    ':end_ts': int(end_date.timestamp())
                }
            )
            
            return response.get('Items', [])
            
        except Exception as e:
            logger.error(f"❌ Error querying patterns by type: {e}")
            return []

# Global instance
_pattern_learning_engine = None

def get_pattern_learning_engine() -> PatternLearningEngine:
    """Get global pattern learning engine instance"""
    global _pattern_learning_engine
    if _pattern_learning_engine is None:
        _pattern_learning_engine = PatternLearningEngine()
    return _pattern_learning_engine

# Export for backward compatibility
pattern_learning_engine = LazyProxy(get_pattern_learning_engine)