"""
TradePulse.AI Signal Performance Tracker
=======================================

Professional signal performance tracking service for enterprise trading system.
Tracks signal accuracy and performance metrics using real live data.

Author: TradePulse.AI Development Team
Version: 1.0.0 (Production)
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import statistics

from app.backend.core.database import get_database_client
from app.backend.core.config import get_settings
from app.backend.services.live_market_data import get_live_bitcoin_price

logger = logging.getLogger(__name__)
settings = get_settings()

class SignalOutcome(Enum):
    """Signal outcome classification"""
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PENDING = "pending"
    EXPIRED = "expired"

@dataclass
class SignalPerformanceMetric:
    """Signal performance metric data"""
    signal_id: str
    timestamp: int
    symbol: str
    signal_type: str
    confidence: float
    entry_price: float
    target_price: Optional[float] = None
    exit_price: Optional[float] = None
    outcome: SignalOutcome = SignalOutcome.PENDING
    pnl: float = 0.0
    pnl_percentage: float = 0.0
    duration_minutes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'signal_id': self.signal_id,
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'signal_type': self.signal_type,
            'confidence': self.confidence,
            'entry_price': self.entry_price,
            'target_price': self.target_price,
            'exit_price': self.exit_price,
            'outcome': self.outcome.value,
            'pnl': self.pnl,
            'pnl_percentage': self.pnl_percentage,
            'duration_minutes': self.duration_minutes,
            'metadata': self.metadata
        }

class SignalPerformanceTracker:
    """
    Professional signal performance tracker for TradePulse.AI
    Tracks signal accuracy and performance with real data only
    """
    
    def __init__(self):
        self.db_client = get_database_client()
        self.active_signals: Dict[str, SignalPerformanceMetric] = {}
        self.performance_stats = {
            'total_signals': 0,
            'correct_signals': 0,
            'incorrect_signals': 0,
            'pending_signals': 0,
            'accuracy_rate': 0.0,
            'avg_pnl': 0.0,
            'avg_duration_minutes': 0.0
        }
        logger.info("🔧 SignalPerformanceTracker initialized")
    
    async def track_signal(self, signal_data: Dict[str, Any]) -> str:
        """
        Start tracking a trading signal's performance
        
        Args:
            signal_data: Signal data to track
            
        Returns:
            str: Signal tracking ID
        """
        try:
            signal_id = f"perf_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
            
            # Get current price as entry price
            entry_price = await get_live_bitcoin_price()
            
            # Create performance metric
            metric = SignalPerformanceMetric(
                signal_id=signal_id,
                timestamp=int(datetime.now(timezone.utc).timestamp()),
                symbol=signal_data.get('symbol', 'BTCUSDT'),
                signal_type=signal_data.get('action', 'hold'),
                confidence=float(signal_data.get('confidence', 0.0)),
                entry_price=entry_price,
                metadata={
                    'original_signal': signal_data,
                    'tracking_start': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Store in active signals
            self.active_signals[signal_id] = metric
            
            # Store in database
            await self._store_performance_metric(metric)
            
            logger.info(f"📊 Started tracking signal: {signal_id} type={metric.signal_type} confidence={metric.confidence:.3f}")
            
            return signal_id
            
        except Exception as e:
            logger.error(f"❌ Error starting signal tracking: {e}")
            raise
    
    async def update_signal_performance(self, signal_id: str, current_price: Optional[float] = None) -> None:
        """
        Update signal performance based on current market conditions
        
        Args:
            signal_id: Signal tracking ID
            current_price: Current market price (optional, will fetch if not provided)
        """
        try:
            if signal_id not in self.active_signals:
                return
            
            metric = self.active_signals[signal_id]
            
            # Get current price if not provided
            if current_price is None:
                current_price = await get_live_bitcoin_price()
            
            # Calculate duration
            current_time = int(datetime.now(timezone.utc).timestamp())
            metric.duration_minutes = (current_time - metric.timestamp) // 60
            
            # Calculate PnL based on signal type
            if metric.signal_type.lower() == 'buy':
                metric.pnl = current_price - metric.entry_price
                metric.pnl_percentage = (metric.pnl / metric.entry_price) * 100
                
                # Determine outcome (simple logic - can be enhanced)
                if metric.pnl_percentage > 0.5:  # 0.5% profit threshold
                    metric.outcome = SignalOutcome.CORRECT
                elif metric.pnl_percentage < -0.5:  # 0.5% loss threshold
                    metric.outcome = SignalOutcome.INCORRECT
                    
            elif metric.signal_type.lower() == 'sell':
                metric.pnl = metric.entry_price - current_price
                metric.pnl_percentage = (metric.pnl / metric.entry_price) * 100
                
                # Determine outcome
                if metric.pnl_percentage > 0.5:
                    metric.outcome = SignalOutcome.CORRECT
                elif metric.pnl_percentage < -0.5:
                    metric.outcome = SignalOutcome.INCORRECT
            
            # Check if signal should expire (after 4 hours)
            if metric.duration_minutes > 240:
                metric.outcome = SignalOutcome.EXPIRED
                self._finalize_signal(signal_id)
            
            # Update in database
            await self._store_performance_metric(metric)
            
        except Exception as e:
            logger.error(f"❌ Error updating signal performance: {e}")
    
    def _finalize_signal(self, signal_id: str) -> None:
        """Finalize signal tracking and update statistics"""
        if signal_id not in self.active_signals:
            return
        
        metric = self.active_signals[signal_id]
        
        # Update performance statistics
        self.performance_stats['total_signals'] += 1
        
        if metric.outcome == SignalOutcome.CORRECT:
            self.performance_stats['correct_signals'] += 1
        elif metric.outcome == SignalOutcome.INCORRECT:
            self.performance_stats['incorrect_signals'] += 1
        else:
            self.performance_stats['pending_signals'] += 1
        
        # Calculate accuracy rate
        total_resolved = self.performance_stats['correct_signals'] + self.performance_stats['incorrect_signals']
        if total_resolved > 0:
            self.performance_stats['accuracy_rate'] = (self.performance_stats['correct_signals'] / total_resolved) * 100
        
        # Remove from active signals
        del self.active_signals[signal_id]
        
        logger.info(f"📊 Finalized signal tracking: {signal_id} outcome={metric.outcome.value} pnl={metric.pnl_percentage:.2f}%")
    
    async def _store_performance_metric(self, metric: SignalPerformanceMetric) -> None:
        """Store performance metric in database"""
        try:
            item = {
                'PK': f'SIGNAL_PERF#{metric.symbol}',
                'SK': f'{metric.timestamp}#{metric.signal_id}',
                'signal_id': metric.signal_id,
                'timestamp': metric.timestamp,
                'symbol': metric.symbol,
                'signal_type': metric.signal_type,
                'confidence': metric.confidence,
                'entry_price': metric.entry_price,
                'target_price': metric.target_price,
                'exit_price': metric.exit_price,
                'outcome': metric.outcome.value,
                'pnl': metric.pnl,
                'pnl_percentage': metric.pnl_percentage,
                'duration_minutes': metric.duration_minutes,
                'metadata': json.dumps(metric.metadata),
                'date': datetime.fromtimestamp(metric.timestamp, tz=timezone.utc).strftime('%Y-%m-%d'),
                'TTL': metric.timestamp + (90 * 24 * 60 * 60)  # 90 days retention
            }
            
            table = self.db_client.get_table('signal_accuracy_tracking')
            table.put_item(Item=item)
            
        except Exception as e:
            logger.error(f"❌ Error storing performance metric: {e}")
    
    async def update_all_active_signals(self) -> None:
        """Update all active signals with current market data"""
        if not self.active_signals:
            return
        
        try:
            current_price = await get_live_bitcoin_price()
            
            for signal_id in list(self.active_signals.keys()):
                await self.update_signal_performance(signal_id, current_price)
                
        except Exception as e:
            logger.error(f"❌ Error updating all active signals: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get signal performance statistics"""
        stats = self.performance_stats.copy()
        stats['active_signals_count'] = len(self.active_signals)
        return stats
    
    def get_active_signals(self) -> List[Dict[str, Any]]:
        """Get all active signals being tracked"""
        return [metric.to_dict() for metric in self.active_signals.values()]
    
    async def get_historical_performance(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get historical performance data"""
        try:
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            table = self.db_client.get_table('signal_accuracy_tracking')
            
            # Query historical data
            response = table.scan(
                FilterExpression='#ts BETWEEN :start_ts AND :end_ts',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':start_ts': int(start_date.timestamp()),
                    ':end_ts': int(end_date.timestamp())
                }
            )
            
            return response.get('Items', [])
            
        except Exception as e:
            logger.error(f"❌ Error getting historical performance: {e}")
            return []

# Global instance
_signal_performance_tracker = None

def get_signal_performance_tracker() -> SignalPerformanceTracker:
    """Get global signal performance tracker instance"""
    global _signal_performance_tracker
    if _signal_performance_tracker is None:
        _signal_performance_tracker = SignalPerformanceTracker()
    return _signal_performance_tracker

# Export for backward compatibility
signal_performance_tracker = get_signal_performance_tracker()
