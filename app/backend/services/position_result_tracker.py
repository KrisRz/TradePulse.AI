"""
TradePulse.AI - Position Result Tracker
=======================================

REAL POSITION RESULT TRACKING SYSTEM - NO MOCKS!

Features:
- Real-time position outcome tracking
- Pattern performance analysis
- Statistical significance testing
- Success rate calculations
- P&L performance metrics
- Position duration analysis

Author: TradePulse.AI Development Team
Created: August 2025
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
import statistics

from app.backend.core.database import get_database_client

logger = logging.getLogger(__name__)

class PositionOutcome(str, Enum):
    """Position outcome types"""
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    MANUAL_CLOSE = "manual_close"
    TIME_STOP = "time_stop"
    EMERGENCY_CLOSE = "emergency_close"

@dataclass
class PositionResult:
    """Position result data"""
    position_id: str
    symbol: str
    outcome: PositionOutcome
    was_successful: bool
    pnl_absolute: float
    pnl_percentage: float
    time_in_position_minutes: int
    entry_price: float
    exit_price: float
    ai_confidence: float
    risk_assessment: str
    patterns_detected: List[str]
    closed_at: datetime
    pattern_analysis_enabled: bool = False
    # CRITICAL: Add signal info for learning
    signal_action: Optional[str] = None  # BUY/SELL signal that opened position
    signal_confidence: Optional[float] = None  # Original signal confidence
    position_type: Optional[str] = None  # long/short

class PositionResultTracker:
    """
    Real-time position result tracking and analysis system
    
    Tracks all position outcomes and provides performance analytics
    for the continuous learning system.
    """
    
    def __init__(self):
        self.db_client = get_database_client()
        self.total_positions_tracked = 0
        self.successful_positions = 0
        self.total_pnl = 0.0
        self.pattern_performance_cache: Dict[str, Dict[str, Any]] = {}
        
        # Load existing statistics
        asyncio.create_task(self._load_statistics())
    
    async def _load_statistics(self):
        """Load existing statistics from database"""
        try:
            if not self.db_client:
                return
                
            # Load summary statistics
            items = self.db_client.scan_table('position_tracker_stats')
            for item in items:
                if item.get('tracker_id') == 'main_tracker':
                    self.total_positions_tracked = item.get('total_positions_tracked', 0)
                    self.successful_positions = item.get('successful_positions', 0)
                    self.total_pnl = float(item.get('total_pnl', 0))
                    logger.info(f"📊 Loaded tracker stats: {self.total_positions_tracked} positions, {self.successful_positions} successful")
                    return
                    
            # Initialize if no stats found
            await self._save_statistics()
            logger.info("🆕 Initialized new position tracker statistics")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to load tracker statistics: {e}")
    
    async def _save_statistics(self):
        """Save statistics to database"""
        try:
            if not self.db_client:
                return
                
            stats_data = {
                'tracker_id': 'main_tracker',
                'total_positions_tracked': self.total_positions_tracked,
                'successful_positions': self.successful_positions,
                'total_pnl': str(self.total_pnl),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            self.db_client.put_item('position_tracker_stats', stats_data)
            logger.debug("💾 Position tracker statistics saved")
            
        except Exception as e:
            logger.error(f"❌ Failed to save tracker statistics: {e}")
    
    async def record_position_result(self, result: PositionResult):
        """Record a position result for tracking and analysis"""
        try:
            # Update running statistics
            self.total_positions_tracked += 1
            if result.was_successful:
                self.successful_positions += 1
            self.total_pnl += result.pnl_absolute
            
            # Save to database - FIXED: Convert float to Decimal for DynamoDB
            from decimal import Decimal
            result_data = {
                'position_id': result.position_id,
                'symbol': result.symbol,
                'outcome': result.outcome.value,
                'was_successful': result.was_successful,
                'pnl_absolute': Decimal(str(result.pnl_absolute)),  # FIXED: Decimal
                'pnl_percentage': Decimal(str(result.pnl_percentage)),  # FIXED: Decimal
                'time_in_position_minutes': result.time_in_position_minutes,
                'entry_price': Decimal(str(result.entry_price)),  # FIXED: Decimal
                'exit_price': Decimal(str(result.exit_price)),  # FIXED: Decimal
                'ai_confidence': Decimal(str(result.ai_confidence)),  # FIXED: Decimal
                'risk_assessment': result.risk_assessment,
                'patterns_detected': result.patterns_detected,
                'pattern_analysis_enabled': result.pattern_analysis_enabled,
                'closed_at': int(result.closed_at.timestamp() * 1000),  # REQUIRED RANGE KEY: milliseconds since epoch (Number)
                'recorded_at': datetime.now(timezone.utc).isoformat(),
                # CRITICAL: Save signal info for learning
                'signal_action': result.signal_action,
                'signal_confidence': Decimal(str(result.signal_confidence)) if result.signal_confidence is not None else None,
                'position_type': result.position_type
            }
            
            if self.db_client:
                self.db_client.put_item('position_results', result_data)
                logger.info(f"📊 Position result recorded: {result.position_id} - {'✅' if result.was_successful else '❌'}")
            
            # Update pattern performance cache
            await self._update_pattern_cache(result)
            
            # Save updated statistics
            await self._save_statistics()
            
        except Exception as e:
            logger.error(f"❌ Failed to record position result: {e}")
    
    async def _update_pattern_cache(self, result: PositionResult):
        """Update pattern performance cache"""
        try:
            for pattern in result.patterns_detected:
                if pattern not in self.pattern_performance_cache:
                    self.pattern_performance_cache[pattern] = {
                        'total_positions': 0,
                        'successful_positions': 0,
                        'total_pnl': 0.0,
                        'success_rate': 0.0,
                        'avg_pnl': 0.0
                    }
                
                cache_entry = self.pattern_performance_cache[pattern]
                cache_entry['total_positions'] += 1
                if result.was_successful:
                    cache_entry['successful_positions'] += 1
                cache_entry['total_pnl'] += result.pnl_absolute
                
                # Recalculate rates
                cache_entry['success_rate'] = cache_entry['successful_positions'] / cache_entry['total_positions']
                cache_entry['avg_pnl'] = cache_entry['total_pnl'] / cache_entry['total_positions']
                
        except Exception as e:
            logger.error(f"❌ Failed to update pattern cache: {e}")
    
    async def _load_recent_results(self, days: int = 7) -> List[Dict[str, Any]]:
        """Load recent position results"""
        try:
            if not self.db_client:
                return []
            
            # Get all results
            all_results = self.db_client.scan_table('position_results')
            
            # Filter to recent results
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_results = []
            
            for result in all_results:
                try:
                    result_date = datetime.fromisoformat(result.get('closed_at', ''))
                    if result_date >= cutoff_date:
                        recent_results.append(result)
                except (ValueError, TypeError):
                    continue
            
            # Sort by date (most recent first)
            recent_results.sort(key=lambda x: x.get('closed_at', ''), reverse=True)
            
            logger.info(f"📊 Loaded {len(recent_results)} recent position results")
            return recent_results
            
        except Exception as e:
            logger.error(f"❌ Failed to load recent results: {e}")
            return []
    
    async def get_pattern_performance_stats(self, min_samples: int = 5) -> Dict[str, Dict[str, Any]]:
        """Get pattern performance statistics"""
        try:
            # Load fresh data from database
            all_results = self.db_client.scan_table('position_results') if self.db_client else []
            
            # Group by patterns
            pattern_stats = {}
            for result in all_results:
                patterns = result.get('patterns_detected', [])
                for pattern in patterns:
                    if pattern not in pattern_stats:
                        pattern_stats[pattern] = {
                            'total_positions': 0,
                            'successful_positions': 0,
                            'total_pnl': 0.0,
                            'pnl_values': []
                        }
                    
                    stats = pattern_stats[pattern]
                    stats['total_positions'] += 1
                    if result.get('was_successful', False):
                        stats['successful_positions'] += 1
                    
                    pnl = result.get('pnl_absolute', 0)
                    stats['total_pnl'] += pnl
                    stats['pnl_values'].append(pnl)
            
            # Calculate final statistics and filter by minimum samples
            final_stats = {}
            for pattern, stats in pattern_stats.items():
                if stats['total_positions'] >= min_samples:
                    final_stats[pattern] = {
                        'total_positions': stats['total_positions'],
                        'successful_positions': stats['successful_positions'],
                        'success_rate': stats['successful_positions'] / stats['total_positions'],
                        'total_pnl': stats['total_pnl'],
                        'avg_pnl': stats['total_pnl'] / stats['total_positions'],
                        'pnl_std': statistics.stdev(stats['pnl_values']) if len(stats['pnl_values']) > 1 else 0.0,
                        'best_pnl': max(stats['pnl_values']) if stats['pnl_values'] else 0.0,
                        'worst_pnl': min(stats['pnl_values']) if stats['pnl_values'] else 0.0
                    }
            
            logger.info(f"📊 Calculated pattern stats for {len(final_stats)} patterns")
            return final_stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get pattern performance stats: {e}")
            return {}
    
    async def get_success_rate_by_risk(self) -> Dict[str, float]:
        """Get success rates by risk assessment level"""
        try:
            recent_results = await self._load_recent_results(days=30)
            
            risk_stats = {}
            for result in recent_results:
                risk = result.get('risk_assessment', 'MEDIUM')
                if risk not in risk_stats:
                    risk_stats[risk] = {'total': 0, 'successful': 0}
                
                risk_stats[risk]['total'] += 1
                if result.get('was_successful', False):
                    risk_stats[risk]['successful'] += 1
            
            # Calculate success rates
            success_rates = {}
            for risk, stats in risk_stats.items():
                success_rates[risk] = stats['successful'] / stats['total'] if stats['total'] > 0 else 0.0
            
            return success_rates
            
        except Exception as e:
            logger.error(f"❌ Failed to get success rates by risk: {e}")
            return {}
    
    async def get_performance_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get performance trends over time"""
        try:
            recent_results = await self._load_recent_results(days=days)
            
            if not recent_results:
                return {}
            
            # Group by day
            daily_stats = {}
            for result in recent_results:
                try:
                    result_date = datetime.fromisoformat(result.get('closed_at', '')).date()
                    date_str = result_date.isoformat()
                    
                    if date_str not in daily_stats:
                        daily_stats[date_str] = {'total': 0, 'successful': 0, 'pnl': 0.0}
                    
                    daily_stats[date_str]['total'] += 1
                    if result.get('was_successful', False):
                        daily_stats[date_str]['successful'] += 1
                    daily_stats[date_str]['pnl'] += result.get('pnl_absolute', 0)
                    
                except (ValueError, TypeError):
                    continue
            
            # Calculate daily success rates and trends
            dates = sorted(daily_stats.keys())
            success_rates = []
            daily_pnls = []
            
            for date in dates:
                stats = daily_stats[date]
                success_rate = stats['successful'] / stats['total'] if stats['total'] > 0 else 0.0
                success_rates.append(success_rate)
                daily_pnls.append(stats['pnl'])
            
            # Calculate trends (simple linear trend)
            success_trend = 0.0
            pnl_trend = 0.0
            
            if len(success_rates) >= 2:
                success_trend = success_rates[-1] - success_rates[0]
                pnl_trend = daily_pnls[-1] - daily_pnls[0]
            
            return {
                'daily_stats': daily_stats,
                'success_rate_trend': success_trend,
                'pnl_trend': pnl_trend,
                'avg_daily_success_rate': statistics.mean(success_rates) if success_rates else 0.0,
                'avg_daily_pnl': statistics.mean(daily_pnls) if daily_pnls else 0.0,
                'total_days_analyzed': len(dates)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get performance trends: {e}")
            return {}

# Global instance
_position_result_tracker: Optional[PositionResultTracker] = None

async def get_position_result_tracker() -> PositionResultTracker:
    """Get the global position result tracker instance"""
    global _position_result_tracker
    
    if _position_result_tracker is None:
        _position_result_tracker = PositionResultTracker()
        logger.info("📊 Position Result Tracker initialized")
    
    return _position_result_tracker
