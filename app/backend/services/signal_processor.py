"""
TradePulse.AI Signal Processor Service
=====================================

Professional signal processing and analysis service for enterprise trading system.
Processes and analyzes trading signals using real live data.

Author: TradePulse.AI Development Team
Version: 1.0.0 (Production)
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

from app.backend.core.database import get_database_client
from app.backend.core.config import get_settings
from app.backend.services.live_market_data import get_live_bitcoin_price

logger = logging.getLogger(__name__)
settings = get_settings()

class SignalType(Enum):
    """Signal type classification"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

class SignalQuality(Enum):
    """Signal quality rating"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"

@dataclass
class ProcessedSignal:
    """Processed trading signal with metadata"""
    signal_id: str
    timestamp: int
    symbol: str
    signal_type: SignalType
    confidence: float
    quality: SignalQuality
    price: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'signal_id': self.signal_id,
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'signal_type': self.signal_type.value,
            'confidence': self.confidence,
            'quality': self.quality.value,
            'price': self.price,
            'metadata': self.metadata
        }

class SignalProcessor:
    """
    Professional signal processor for TradePulse.AI
    Processes and analyzes trading signals with real data only
    """
    
    def __init__(self):
        self.db_client = get_database_client()
        self.processed_signals: List[ProcessedSignal] = []
        self.signal_stats = {
            'total_processed': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'hold_signals': 0,
            'avg_confidence': 0.0
        }
        logger.info("🔧 SignalProcessor initialized")
    
    async def process_signal(self, raw_signal: Dict[str, Any]) -> ProcessedSignal:
        """
        Process a raw trading signal
        
        Args:
            raw_signal: Raw signal data from trading engine
            
        Returns:
            ProcessedSignal: Processed signal with metadata
        """
        try:
            # Extract signal data
            signal_type = SignalType(raw_signal.get('action', 'hold').lower())
            confidence = float(raw_signal.get('confidence', 0.0))
            symbol = raw_signal.get('symbol', 'BTCUSDT')
            
            # Get current price
            current_price = await get_live_bitcoin_price()
            
            # Determine signal quality based on confidence
            if confidence >= 0.8:
                quality = SignalQuality.EXCELLENT
            elif confidence >= 0.6:
                quality = SignalQuality.GOOD
            elif confidence >= 0.4:
                quality = SignalQuality.FAIR
            else:
                quality = SignalQuality.POOR
            
            # Create processed signal
            processed_signal = ProcessedSignal(
                signal_id=f"sig_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                timestamp=int(datetime.now(timezone.utc).timestamp()),
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                quality=quality,
                price=current_price,
                metadata={
                    'raw_signal': raw_signal,
                    'processing_time': datetime.now(timezone.utc).isoformat(),
                    'processor_version': '1.0.0'
                }
            )
            
            # Update statistics
            self._update_stats(processed_signal)
            
            # Store processed signal
            self.processed_signals.append(processed_signal)
            
            # Store in database
            await self._store_signal(processed_signal)
            
            logger.info(f"📊 Processed signal: {signal_type.value.upper()} confidence={confidence:.3f} quality={quality.value}")
            
            return processed_signal
            
        except Exception as e:
            logger.error(f"❌ Error processing signal: {e}")
            raise
    
    def _update_stats(self, signal: ProcessedSignal) -> None:
        """Update signal processing statistics"""
        self.signal_stats['total_processed'] += 1
        
        if signal.signal_type == SignalType.BUY:
            self.signal_stats['buy_signals'] += 1
        elif signal.signal_type == SignalType.SELL:
            self.signal_stats['sell_signals'] += 1
        else:
            self.signal_stats['hold_signals'] += 1
        
        # Update average confidence
        total_confidence = sum(s.confidence for s in self.processed_signals)
        self.signal_stats['avg_confidence'] = total_confidence / len(self.processed_signals)
    
    async def _store_signal(self, signal: ProcessedSignal) -> None:
        """Store processed signal in database"""
        try:
            # Store in signals table
            item = {
                'PK': f'SIGNAL#{signal.symbol}',
                'SK': f'{signal.timestamp}#{signal.signal_id}',
                'signal_id': signal.signal_id,
                'timestamp': signal.timestamp,
                'symbol': signal.symbol,
                'signal_type': signal.signal_type.value,
                'confidence': signal.confidence,
                'quality': signal.quality.value,
                'price': signal.price,
                'metadata': json.dumps(signal.metadata),
                'date': datetime.fromtimestamp(signal.timestamp, tz=timezone.utc).strftime('%Y-%m-%d'),
                'TTL': signal.timestamp + (30 * 24 * 60 * 60)  # 30 days retention
            }
            
            table = self.db_client.get_table('signals')
            table.put_item(Item=item)
            
        except Exception as e:
            logger.error(f"❌ Error storing signal: {e}")
    
    def get_recent_signals(self, limit: int = 50) -> List[ProcessedSignal]:
        """Get recent processed signals"""
        return self.processed_signals[-limit:]
    
    def get_signal_stats(self) -> Dict[str, Any]:
        """Get signal processing statistics"""
        return self.signal_stats.copy()
    
    async def get_signals_by_type(self, signal_type: SignalType, limit: int = 100) -> List[Dict[str, Any]]:
        """Get signals by type from database"""
        try:
            table = self.db_client.get_table('signals')
            
            # Query recent signals of specified type
            response = table.scan(
                FilterExpression='signal_type = :signal_type',
                ExpressionAttributeValues={
                    ':signal_type': signal_type.value
                },
                Limit=limit
            )
            
            return response.get('Items', [])
            
        except Exception as e:
            logger.error(f"❌ Error querying signals by type: {e}")
            return []

# Global instance
_signal_processor = None

def get_signal_processor() -> SignalProcessor:
    """Get global signal processor instance"""
    global _signal_processor
    if _signal_processor is None:
        _signal_processor = SignalProcessor()
    return _signal_processor

# Export for backward compatibility
SignalProcessor = SignalProcessor
