"""
TradePulse.AI AI vs Random Performance Tracker
=============================================

Professional comparison tracker between AI signals and random signals.
Tracks performance differences using real live data.

Author: TradePulse.AI Development Team
Version: 1.0.0 (Production)
"""

import asyncio
import logging
import random
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

class ExperimentType(Enum):
    """Experiment type classification"""
    AI_SIGNAL = "ai_signal"
    RANDOM_SIGNAL = "random_signal"

class ExperimentOutcome(Enum):
    """Experiment outcome classification"""
    WIN = "win"
    LOSS = "loss"
    PENDING = "pending"
    EXPIRED = "expired"

@dataclass
class ExperimentResult:
    """AI vs Random experiment result"""
    experiment_id: str
    timestamp: int
    experiment_type: ExperimentType
    symbol: str
    signal_type: str
    confidence: float
    entry_price: float
    exit_price: Optional[float] = None
    outcome: ExperimentOutcome = ExperimentOutcome.PENDING
    pnl: float = 0.0
    pnl_percentage: float = 0.0
    duration_minutes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'experiment_id': self.experiment_id,
            'timestamp': self.timestamp,
            'experiment_type': self.experiment_type.value,
            'symbol': self.symbol,
            'signal_type': self.signal_type,
            'confidence': self.confidence,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'outcome': self.outcome.value,
            'pnl': self.pnl,
            'pnl_percentage': self.pnl_percentage,
            'duration_minutes': self.duration_minutes,
            'metadata': self.metadata
        }

class AIvsRandomTracker:
    """
    Professional AI vs Random performance tracker for TradePulse.AI
    Compares AI signal performance against random signals with real data only
    """
    
    def __init__(self):
        self.db_client = get_database_client()
        self.active_experiments: Dict[str, ExperimentResult] = {}
        self.comparison_stats = {
            'ai_experiments': 0,
            'random_experiments': 0,
            'ai_wins': 0,
            'random_wins': 0,
            'ai_avg_pnl': 0.0,
            'random_avg_pnl': 0.0,
            'ai_win_rate': 0.0,
            'random_win_rate': 0.0,
            'ai_advantage': 0.0
        }
        logger.info("🔧 AIvsRandomTracker initialized")
    
    async def start_ai_experiment(self, ai_signal: Dict[str, Any]) -> str:
        """
        Start an AI signal experiment
        
        Args:
            ai_signal: AI signal data
            
        Returns:
            str: Experiment ID
        """
        try:
            experiment_id = f"ai_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
            
            # Get current price as entry price
            entry_price = await get_live_bitcoin_price()
            
            # Create AI experiment
            experiment = ExperimentResult(
                experiment_id=experiment_id,
                timestamp=int(datetime.now(timezone.utc).timestamp()),
                experiment_type=ExperimentType.AI_SIGNAL,
                symbol=ai_signal.get('symbol', 'BTCUSDT'),
                signal_type=ai_signal.get('action', 'hold'),
                confidence=float(ai_signal.get('confidence', 0.0)),
                entry_price=entry_price,
                metadata={
                    'original_signal': ai_signal,
                    'experiment_start': datetime.now(timezone.utc).isoformat(),
                    'source': 'enterprise_trading_engine'
                }
            )
            
            # Store in active experiments
            self.active_experiments[experiment_id] = experiment
            
            # Store in database
            await self._store_experiment(experiment)
            
            # Also start a random experiment for comparison
            await self._start_random_experiment(experiment.symbol)
            
            logger.info(f"🤖 Started AI experiment: {experiment_id} type={experiment.signal_type} confidence={experiment.confidence:.3f}")
            
            return experiment_id
            
        except Exception as e:
            logger.error(f"❌ Error starting AI experiment: {e}")
            raise
    
    async def _start_random_experiment(self, symbol: str) -> str:
        """
        Start a random signal experiment for comparison
        
        Args:
            symbol: Trading symbol
            
        Returns:
            str: Random experiment ID
        """
        try:
            experiment_id = f"random_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
            
            # Generate random signal
            random_actions = ['buy', 'sell', 'hold']
            random_signal_type = random.choice(random_actions)
            random_confidence = random.uniform(0.3, 0.9)  # Random confidence between 30-90%
            
            # Get current price as entry price
            entry_price = await get_live_bitcoin_price()
            
            # Create random experiment
            experiment = ExperimentResult(
                experiment_id=experiment_id,
                timestamp=int(datetime.now(timezone.utc).timestamp()),
                experiment_type=ExperimentType.RANDOM_SIGNAL,
                symbol=symbol,
                signal_type=random_signal_type,
                confidence=random_confidence,
                entry_price=entry_price,
                metadata={
                    'experiment_start': datetime.now(timezone.utc).isoformat(),
                    'source': 'random_generator',
                    'random_seed': random.randint(1000, 9999)
                }
            )
            
            # Store in active experiments
            self.active_experiments[experiment_id] = experiment
            
            # Store in database
            await self._store_experiment(experiment)
            
            logger.info(f"🎲 Started random experiment: {experiment_id} type={experiment.signal_type} confidence={experiment.confidence:.3f}")
            
            return experiment_id
            
        except Exception as e:
            logger.error(f"❌ Error starting random experiment: {e}")
            raise
    
    async def update_experiment(self, experiment_id: str, current_price: Optional[float] = None) -> None:
        """
        Update experiment performance based on current market conditions
        
        Args:
            experiment_id: Experiment ID
            current_price: Current market price (optional)
        """
        try:
            if experiment_id not in self.active_experiments:
                return
            
            experiment = self.active_experiments[experiment_id]
            
            # Get current price if not provided
            if current_price is None:
                current_price = await get_live_bitcoin_price()
            
            # Calculate duration
            current_time = int(datetime.now(timezone.utc).timestamp())
            experiment.duration_minutes = (current_time - experiment.timestamp) // 60
            
            # Calculate PnL based on signal type
            if experiment.signal_type.lower() == 'buy':
                experiment.pnl = current_price - experiment.entry_price
                experiment.pnl_percentage = (experiment.pnl / experiment.entry_price) * 100
                
                # Determine outcome
                if experiment.pnl_percentage > 0.3:  # 0.3% profit threshold
                    experiment.outcome = ExperimentOutcome.WIN
                elif experiment.pnl_percentage < -0.3:  # 0.3% loss threshold
                    experiment.outcome = ExperimentOutcome.LOSS
                    
            elif experiment.signal_type.lower() == 'sell':
                experiment.pnl = experiment.entry_price - current_price
                experiment.pnl_percentage = (experiment.pnl / experiment.entry_price) * 100
                
                # Determine outcome
                if experiment.pnl_percentage > 0.3:
                    experiment.outcome = ExperimentOutcome.WIN
                elif experiment.pnl_percentage < -0.3:
                    experiment.outcome = ExperimentOutcome.LOSS
            
            # Check if experiment should expire (after 2 hours)
            if experiment.duration_minutes > 120:
                experiment.outcome = ExperimentOutcome.EXPIRED
                self._finalize_experiment(experiment_id)
            
            # Update in database
            await self._store_experiment(experiment)
            
        except Exception as e:
            logger.error(f"❌ Error updating experiment: {e}")
    
    def _finalize_experiment(self, experiment_id: str) -> None:
        """Finalize experiment and update comparison statistics"""
        if experiment_id not in self.active_experiments:
            return
        
        experiment = self.active_experiments[experiment_id]
        
        # Update comparison statistics
        if experiment.experiment_type == ExperimentType.AI_SIGNAL:
            self.comparison_stats['ai_experiments'] += 1
            if experiment.outcome == ExperimentOutcome.WIN:
                self.comparison_stats['ai_wins'] += 1
        else:
            self.comparison_stats['random_experiments'] += 1
            if experiment.outcome == ExperimentOutcome.WIN:
                self.comparison_stats['random_wins'] += 1
        
        # Calculate win rates
        if self.comparison_stats['ai_experiments'] > 0:
            self.comparison_stats['ai_win_rate'] = (self.comparison_stats['ai_wins'] / self.comparison_stats['ai_experiments']) * 100
        
        if self.comparison_stats['random_experiments'] > 0:
            self.comparison_stats['random_win_rate'] = (self.comparison_stats['random_wins'] / self.comparison_stats['random_experiments']) * 100
        
        # Calculate AI advantage
        self.comparison_stats['ai_advantage'] = self.comparison_stats['ai_win_rate'] - self.comparison_stats['random_win_rate']
        
        # Remove from active experiments
        del self.active_experiments[experiment_id]
        
        logger.info(f"📊 Finalized experiment: {experiment_id} type={experiment.experiment_type.value} outcome={experiment.outcome.value}")
    
    async def _store_experiment(self, experiment: ExperimentResult) -> None:
        """Store experiment in database"""
        try:
            item = {
                'PK': f'AI_VS_RANDOM#{experiment.symbol}',
                'SK': f'{experiment.timestamp}#{experiment.experiment_id}',
                'experiment_id': experiment.experiment_id,
                'timestamp': experiment.timestamp,
                'experiment_type': experiment.experiment_type.value,
                'symbol': experiment.symbol,
                'signal_type': experiment.signal_type,
                'confidence': experiment.confidence,
                'entry_price': experiment.entry_price,
                'exit_price': experiment.exit_price,
                'outcome': experiment.outcome.value,
                'pnl': experiment.pnl,
                'pnl_percentage': experiment.pnl_percentage,
                'duration_minutes': experiment.duration_minutes,
                'metadata': json.dumps(experiment.metadata),
                'date': datetime.fromtimestamp(experiment.timestamp, tz=timezone.utc).strftime('%Y-%m-%d'),
                'TTL': experiment.timestamp + (90 * 24 * 60 * 60)  # 90 days retention
            }
            
            table = self.db_client.get_table('ai_vs_random_experiments')
            table.put_item(Item=item)
            
        except Exception as e:
            logger.error(f"❌ Error storing experiment: {e}")
    
    async def update_all_active_experiments(self) -> None:
        """Update all active experiments with current market data"""
        if not self.active_experiments:
            return
        
        try:
            current_price = await get_live_bitcoin_price()
            
            for experiment_id in list(self.active_experiments.keys()):
                await self.update_experiment(experiment_id, current_price)
                
        except Exception as e:
            logger.error(f"❌ Error updating all active experiments: {e}")
    
    def get_comparison_stats(self) -> Dict[str, Any]:
        """Get AI vs Random comparison statistics"""
        stats = self.comparison_stats.copy()
        stats['active_experiments_count'] = len(self.active_experiments)
        return stats
    
    def get_active_experiments(self) -> List[Dict[str, Any]]:
        """Get all active experiments"""
        return [experiment.to_dict() for experiment in self.active_experiments.values()]
    
    async def get_historical_comparison(self, days: int = 30) -> Dict[str, Any]:
        """Get historical AI vs Random comparison data"""
        try:
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            table = self.db_client.get_table('ai_vs_random_experiments')
            
            # Query historical data
            response = table.scan(
                FilterExpression='#ts BETWEEN :start_ts AND :end_ts',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                ExpressionAttributeValues={
                    ':start_ts': int(start_date.timestamp()),
                    ':end_ts': int(end_date.timestamp())
                }
            )
            
            items = response.get('Items', [])
            
            # Analyze results
            ai_results = [item for item in items if item['experiment_type'] == 'ai_signal']
            random_results = [item for item in items if item['experiment_type'] == 'random_signal']
            
            ai_wins = len([item for item in ai_results if item['outcome'] == 'win'])
            random_wins = len([item for item in random_results if item['outcome'] == 'win'])
            
            ai_avg_pnl = statistics.mean([float(item['pnl_percentage']) for item in ai_results]) if ai_results else 0.0
            random_avg_pnl = statistics.mean([float(item['pnl_percentage']) for item in random_results]) if random_results else 0.0
            
            return {
                'period_days': days,
                'ai_experiments': len(ai_results),
                'random_experiments': len(random_results),
                'ai_wins': ai_wins,
                'random_wins': random_wins,
                'ai_win_rate': (ai_wins / len(ai_results) * 100) if ai_results else 0.0,
                'random_win_rate': (random_wins / len(random_results) * 100) if random_results else 0.0,
                'ai_avg_pnl': ai_avg_pnl,
                'random_avg_pnl': random_avg_pnl,
                'ai_advantage': ai_avg_pnl - random_avg_pnl,
                'raw_data': items
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting historical comparison: {e}")
            return {}

# Global instance
_ai_vs_random_tracker = None

def get_ai_vs_random_tracker() -> AIvsRandomTracker:
    """Get global AI vs Random tracker instance"""
    global _ai_vs_random_tracker
    if _ai_vs_random_tracker is None:
        _ai_vs_random_tracker = AIvsRandomTracker()
    return _ai_vs_random_tracker

# Export for backward compatibility
ai_vs_random_tracker = get_ai_vs_random_tracker()
