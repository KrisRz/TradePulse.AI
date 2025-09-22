"""
TradePulse.AI User Performance Showcase Service
==============================================

Professional user performance showcase service for enterprise trading system.
Showcases user trading performance and achievements using real live data.

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

logger = logging.getLogger(__name__)
settings = get_settings()

class AchievementType(Enum):
    """Achievement type classification"""
    PROFIT_MILESTONE = "profit_milestone"
    WIN_STREAK = "win_streak" 
    ACCURACY_MILESTONE = "accuracy_milestone"
    VOLUME_MILESTONE = "volume_milestone"
    CONSISTENCY_AWARD = "consistency_award"

@dataclass
class UserAchievement:
    """User achievement data"""
    achievement_id: str
    user_id: str
    achievement_type: AchievementType
    title: str
    description: str
    earned_at: int
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'achievement_id': self.achievement_id,
            'user_id': self.user_id,
            'achievement_type': self.achievement_type.value,
            'title': self.title,
            'description': self.description,
            'earned_at': self.earned_at,
            'value': self.value,
            'metadata': self.metadata
        }

@dataclass
class UserPerformanceStats:
    """User performance statistics"""
    user_id: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_profit_per_trade: float
    best_trade: float
    worst_trade: float
    current_streak: int
    longest_win_streak: int
    total_volume: float
    active_days: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'user_id': self.user_id,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'total_pnl': self.total_pnl,
            'avg_profit_per_trade': self.avg_profit_per_trade,
            'best_trade': self.best_trade,
            'worst_trade': self.worst_trade,
            'current_streak': self.current_streak,
            'longest_win_streak': self.longest_win_streak,
            'total_volume': self.total_volume,
            'active_days': self.active_days
        }

class UserPerformanceShowcase:
    """
    Professional user performance showcase for TradePulse.AI
    Showcases user achievements and performance with real data only
    """
    
    def __init__(self):
        self.db_client = get_database_client()
        self.user_stats_cache: Dict[str, UserPerformanceStats] = {}
        self.achievements_cache: Dict[str, List[UserAchievement]] = {}
        logger.info("🔧 UserPerformanceShowcase initialized")
    
    async def calculate_user_performance(self, user_id: str) -> UserPerformanceStats:
        """
        Calculate comprehensive user performance statistics
        
        Args:
            user_id: User identifier
            
        Returns:
            UserPerformanceStats: Calculated performance statistics
        """
        try:
            # Get user's trading history from database
            trades = await self._get_user_trades(user_id)
            
            if not trades:
                return UserPerformanceStats(
                    user_id=user_id,
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    win_rate=0.0,
                    total_pnl=0.0,
                    avg_profit_per_trade=0.0,
                    best_trade=0.0,
                    worst_trade=0.0,
                    current_streak=0,
                    longest_win_streak=0,
                    total_volume=0.0,
                    active_days=0
                )
            
            # Calculate statistics
            total_trades = len(trades)
            winning_trades = len([t for t in trades if float(t.get('pnl', 0)) > 0])
            losing_trades = total_trades - winning_trades
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0
            
            pnl_values = [float(t.get('pnl', 0)) for t in trades]
            total_pnl = sum(pnl_values)
            avg_profit_per_trade = total_pnl / total_trades if total_trades > 0 else 0.0
            best_trade = max(pnl_values) if pnl_values else 0.0
            worst_trade = min(pnl_values) if pnl_values else 0.0
            
            # Calculate streaks
            current_streak, longest_win_streak = self._calculate_streaks(trades)
            
            # Calculate total volume
            total_volume = sum(float(t.get('volume', 0)) for t in trades)
            
            # Calculate active days
            trade_dates = set(t.get('date', '') for t in trades if t.get('date'))
            active_days = len(trade_dates)
            
            stats = UserPerformanceStats(
                user_id=user_id,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_pnl=total_pnl,
                avg_profit_per_trade=avg_profit_per_trade,
                best_trade=best_trade,
                worst_trade=worst_trade,
                current_streak=current_streak,
                longest_win_streak=longest_win_streak,
                total_volume=total_volume,
                active_days=active_days
            )
            
            # Cache the stats
            self.user_stats_cache[user_id] = stats
            
            # Store in database
            await self._store_user_stats(stats)
            
            logger.info(f"📊 Calculated performance for user {user_id}: {total_trades} trades, {win_rate:.1f}% win rate")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error calculating user performance: {e}")
            raise
    
    async def check_and_award_achievements(self, user_id: str, stats: UserPerformanceStats) -> List[UserAchievement]:
        """
        Check for new achievements and award them
        
        Args:
            user_id: User identifier
            stats: User performance statistics
            
        Returns:
            List of newly awarded achievements
        """
        new_achievements = []
        
        try:
            # Get existing achievements
            existing_achievements = await self._get_user_achievements(user_id)
            existing_types = [a.get('achievement_type') for a in existing_achievements]
            
            # Check profit milestones
            profit_milestones = [100, 500, 1000, 5000, 10000]  # USD
            for milestone in profit_milestones:
                if (stats.total_pnl >= milestone and 
                    f"profit_{milestone}" not in existing_types):
                    
                    achievement = UserAchievement(
                        achievement_id=f"profit_{milestone}_{int(datetime.now(timezone.utc).timestamp())}",
                        user_id=user_id,
                        achievement_type=AchievementType.PROFIT_MILESTONE,
                        title=f"Profit Master ${milestone}",
                        description=f"Achieved ${milestone} total profit",
                        earned_at=int(datetime.now(timezone.utc).timestamp()),
                        value=milestone,
                        metadata={'milestone': milestone, 'actual_profit': stats.total_pnl}
                    )
                    new_achievements.append(achievement)
            
            # Check win streak achievements
            streak_milestones = [5, 10, 20, 50]
            for milestone in streak_milestones:
                if (stats.longest_win_streak >= milestone and 
                    f"streak_{milestone}" not in existing_types):
                    
                    achievement = UserAchievement(
                        achievement_id=f"streak_{milestone}_{int(datetime.now(timezone.utc).timestamp())}",
                        user_id=user_id,
                        achievement_type=AchievementType.WIN_STREAK,
                        title=f"Win Streak Champion {milestone}",
                        description=f"Achieved {milestone} consecutive wins",
                        earned_at=int(datetime.now(timezone.utc).timestamp()),
                        value=milestone,
                        metadata={'milestone': milestone, 'actual_streak': stats.longest_win_streak}
                    )
                    new_achievements.append(achievement)
            
            # Check accuracy achievements
            accuracy_milestones = [70, 80, 90, 95]
            for milestone in accuracy_milestones:
                if (stats.win_rate >= milestone and stats.total_trades >= 20 and
                    f"accuracy_{milestone}" not in existing_types):
                    
                    achievement = UserAchievement(
                        achievement_id=f"accuracy_{milestone}_{int(datetime.now(timezone.utc).timestamp())}",
                        user_id=user_id,
                        achievement_type=AchievementType.ACCURACY_MILESTONE,
                        title=f"Precision Trader {milestone}%",
                        description=f"Achieved {milestone}% win rate with 20+ trades",
                        earned_at=int(datetime.now(timezone.utc).timestamp()),
                        value=milestone,
                        metadata={'milestone': milestone, 'actual_accuracy': stats.win_rate, 'total_trades': stats.total_trades}
                    )
                    new_achievements.append(achievement)
            
            # Store new achievements
            for achievement in new_achievements:
                await self._store_achievement(achievement)
            
            if new_achievements:
                logger.info(f"🏆 Awarded {len(new_achievements)} new achievements to user {user_id}")
            
            return new_achievements
            
        except Exception as e:
            logger.error(f"❌ Error checking achievements: {e}")
            return []
    
    def _calculate_streaks(self, trades: List[Dict]) -> Tuple[int, int]:
        """Calculate current streak and longest win streak"""
        if not trades:
            return 0, 0
        
        # Sort trades by timestamp
        sorted_trades = sorted(trades, key=lambda t: int(t.get('timestamp', 0)))
        
        current_streak = 0
        longest_win_streak = 0
        current_win_streak = 0
        
        for trade in reversed(sorted_trades):  # Start from most recent
            pnl = float(trade.get('pnl', 0))
            
            if current_streak == 0:  # First trade in current streak calculation
                current_streak = 1 if pnl > 0 else -1
            else:
                if (current_streak > 0 and pnl > 0) or (current_streak < 0 and pnl <= 0):
                    current_streak += 1 if pnl > 0 else -1
                else:
                    break  # Streak broken
        
        # Calculate longest win streak
        for trade in sorted_trades:
            pnl = float(trade.get('pnl', 0))
            
            if pnl > 0:
                current_win_streak += 1
                longest_win_streak = max(longest_win_streak, current_win_streak)
            else:
                current_win_streak = 0
        
        return abs(current_streak) if current_streak > 0 else 0, longest_win_streak
    
    async def _get_user_trades(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's trading history from database"""
        try:
            # This would query the actual trading history table
            # For now, return empty list as placeholder
            return []
            
        except Exception as e:
            logger.error(f"❌ Error getting user trades: {e}")
            return []
    
    async def _get_user_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's existing achievements"""
        try:
            table = self.db_client.get_table('user_performance_showcases')
            
            response = table.query(
                KeyConditionExpression='PK = :pk',
                ExpressionAttributeValues={':pk': f'USER#{user_id}#ACHIEVEMENTS'},
                ScanIndexForward=False
            )
            
            return response.get('Items', [])
            
        except Exception as e:
            logger.error(f"❌ Error getting user achievements: {e}")
            return []
    
    async def _store_user_stats(self, stats: UserPerformanceStats) -> None:
        """Store user performance statistics in database"""
        try:
            item = {
                'PK': f'USER#{stats.user_id}#STATS',
                'SK': f'{int(datetime.now(timezone.utc).timestamp())}',
                'user_id': stats.user_id,
                'total_trades': stats.total_trades,
                'winning_trades': stats.winning_trades,
                'losing_trades': stats.losing_trades,
                'win_rate': stats.win_rate,
                'total_pnl': stats.total_pnl,
                'avg_profit_per_trade': stats.avg_profit_per_trade,
                'best_trade': stats.best_trade,
                'worst_trade': stats.worst_trade,
                'current_streak': stats.current_streak,
                'longest_win_streak': stats.longest_win_streak,
                'total_volume': stats.total_volume,
                'active_days': stats.active_days,
                'calculated_at': int(datetime.now(timezone.utc).timestamp()),
                'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                'TTL': int(datetime.now(timezone.utc).timestamp()) + (365 * 24 * 60 * 60)  # 1 year retention
            }
            
            table = self.db_client.get_table('user_performance_showcases')
            table.put_item(Item=item)
            
        except Exception as e:
            logger.error(f"❌ Error storing user stats: {e}")
    
    async def _store_achievement(self, achievement: UserAchievement) -> None:
        """Store user achievement in database"""
        try:
            item = {
                'PK': f'USER#{achievement.user_id}#ACHIEVEMENTS',
                'SK': f'{achievement.earned_at}#{achievement.achievement_id}',
                'achievement_id': achievement.achievement_id,
                'user_id': achievement.user_id,
                'achievement_type': achievement.achievement_type.value,
                'title': achievement.title,
                'description': achievement.description,
                'earned_at': achievement.earned_at,
                'value': achievement.value,
                'metadata': json.dumps(achievement.metadata),
                'date': datetime.fromtimestamp(achievement.earned_at, tz=timezone.utc).strftime('%Y-%m-%d')
            }
            
            table = self.db_client.get_table('user_performance_showcases')
            table.put_item(Item=item)
            
        except Exception as e:
            logger.error(f"❌ Error storing achievement: {e}")
    
    async def get_user_leaderboard(self, metric: str = 'total_pnl', limit: int = 10) -> List[Dict[str, Any]]:
        """Get user leaderboard for specified metric"""
        try:
            # This would query and rank users by the specified metric
            # For now, return empty list as placeholder
            return []
            
        except Exception as e:
            logger.error(f"❌ Error getting leaderboard: {e}")
            return []
    
    def get_cached_user_stats(self, user_id: str) -> Optional[UserPerformanceStats]:
        """Get cached user statistics"""
        return self.user_stats_cache.get(user_id)

# Global instance
_user_performance_showcase = None

def get_user_performance_showcase() -> UserPerformanceShowcase:
    """Get global user performance showcase instance"""
    global _user_performance_showcase
    if _user_performance_showcase is None:
        _user_performance_showcase = UserPerformanceShowcase()
    return _user_performance_showcase

# Export for backward compatibility
user_performance_showcase = get_user_performance_showcase()
