"""
TradePulse.AI Portfolio Showcase Engine
======================================

Professional portfolio showcase engine for enterprise trading system.
Showcases portfolio performance and analytics using real data only.

Author: TradePulse.AI Development Team
Version: 1.0.0 (Production)
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import statistics

from app.backend.core.database import get_database_client
from app.backend.core.config import get_settings
from app.backend.services.live_market_data import get_live_bitcoin_price
from app.backend.core.lazy import LazyProxy

logger = logging.getLogger(__name__)
settings = get_settings()

@dataclass
class PortfolioSnapshot:
    """Portfolio performance snapshot"""
    portfolio_id: str
    timestamp: int
    total_value: float
    total_pnl: float
    pnl_percentage: float
    active_positions: int
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    metadata: Dict[str, Any]

class PortfolioShowcaseEngine:
    """
    Professional portfolio showcase engine for TradePulse.AI
    Showcases portfolio performance with real data only
    """
    
    def __init__(self):
        self.db_client = get_database_client()
        self.portfolio_snapshots: Dict[str, List[PortfolioSnapshot]] = {}
        logger.info("🔧 PortfolioShowcaseEngine initialized")
    
    async def create_portfolio_snapshot(self, portfolio_id: str, portfolio_data: Dict[str, Any]) -> PortfolioSnapshot:
        """Create a portfolio performance snapshot"""
        try:
            current_price = await get_live_bitcoin_price()
            
            snapshot = PortfolioSnapshot(
                portfolio_id=portfolio_id,
                timestamp=int(datetime.now(timezone.utc).timestamp()),
                total_value=float(portfolio_data.get('total_value', 0)),
                total_pnl=float(portfolio_data.get('total_pnl', 0)),
                pnl_percentage=float(portfolio_data.get('pnl_percentage', 0)),
                active_positions=int(portfolio_data.get('active_positions', 0)),
                win_rate=float(portfolio_data.get('win_rate', 0)),
                sharpe_ratio=float(portfolio_data.get('sharpe_ratio', 0)),
                max_drawdown=float(portfolio_data.get('max_drawdown', 0)),
                metadata={
                    'current_btc_price': current_price,
                    'snapshot_time': datetime.now(timezone.utc).isoformat(),
                    'portfolio_data': portfolio_data
                }
            )
            
            # Store snapshot
            if portfolio_id not in self.portfolio_snapshots:
                self.portfolio_snapshots[portfolio_id] = []
            
            self.portfolio_snapshots[portfolio_id].append(snapshot)
            await self._store_snapshot(snapshot)
            
            logger.info(f"📊 Created portfolio snapshot: {portfolio_id} value=${snapshot.total_value:.2f}")
            return snapshot
            
        except Exception as e:
            logger.error(f"❌ Error creating portfolio snapshot: {e}")
            raise
    
    async def _store_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        """Store portfolio snapshot in database"""
        try:
            item = {
                'PK': f'PORTFOLIO_SHOWCASE#{snapshot.portfolio_id}',
                'SK': f'{snapshot.timestamp}',
                'portfolio_id': snapshot.portfolio_id,
                'timestamp': snapshot.timestamp,
                'total_value': snapshot.total_value,
                'total_pnl': snapshot.total_pnl,
                'pnl_percentage': snapshot.pnl_percentage,
                'active_positions': snapshot.active_positions,
                'win_rate': snapshot.win_rate,
                'sharpe_ratio': snapshot.sharpe_ratio,
                'max_drawdown': snapshot.max_drawdown,
                'metadata': json.dumps(snapshot.metadata),
                'date': datetime.fromtimestamp(snapshot.timestamp, tz=timezone.utc).strftime('%Y-%m-%d'),
                'TTL': snapshot.timestamp + (365 * 24 * 60 * 60)  # 1 year retention
            }
            
            # Using virtual portfolios table for now
            table = self.db_client.get_table('tradepulse-virtual-portfolios')
            table.put_item(Item=item)
            
        except Exception as e:
            logger.error(f"❌ Error storing portfolio snapshot: {e}")
    
    def get_portfolio_snapshots(self, portfolio_id: str, limit: int = 100) -> List[PortfolioSnapshot]:
        """Get portfolio snapshots"""
        if portfolio_id in self.portfolio_snapshots:
            return self.portfolio_snapshots[portfolio_id][-limit:]
        return []
    
    async def generate_performance_report(self, portfolio_id: str, days: int = 30) -> Dict[str, Any]:
        """Generate portfolio performance report"""
        try:
            snapshots = self.get_portfolio_snapshots(portfolio_id)
            
            if not snapshots:
                return {'error': 'No snapshots available'}
            
            # Calculate performance metrics
            recent_snapshots = [s for s in snapshots if s.timestamp > (datetime.now(timezone.utc).timestamp() - days * 24 * 3600)]
            
            if not recent_snapshots:
                return {'error': f'No snapshots in last {days} days'}
            
            values = [s.total_value for s in recent_snapshots]
            pnl_values = [s.total_pnl for s in recent_snapshots]
            
            report = {
                'portfolio_id': portfolio_id,
                'period_days': days,
                'snapshots_count': len(recent_snapshots),
                'current_value': values[-1] if values else 0,
                'starting_value': values[0] if values else 0,
                'total_return': values[-1] - values[0] if len(values) > 1 else 0,
                'total_return_pct': ((values[-1] - values[0]) / values[0] * 100) if len(values) > 1 and values[0] != 0 else 0,
                'avg_daily_return': statistics.mean(pnl_values) if pnl_values else 0,
                'max_value': max(values) if values else 0,
                'min_value': min(values) if values else 0,
                'volatility': statistics.stdev(values) if len(values) > 1 else 0,
                'latest_snapshot': recent_snapshots[-1].__dict__ if recent_snapshots else None
            }
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Error generating performance report: {e}")
            return {'error': str(e)}

# Global instance
_portfolio_showcase_engine = None

def get_portfolio_showcase_engine():
    """Get global portfolio showcase engine instance"""
    global _portfolio_showcase_engine
    if _portfolio_showcase_engine is None:
        _portfolio_showcase_engine = PortfolioShowcaseEngine()
    return _portfolio_showcase_engine

# Export for backward compatibility
portfolio_showcase_engine = LazyProxy(get_portfolio_showcase_engine)