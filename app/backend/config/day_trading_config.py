"""
Day Trading Configuration - Bitcoin Focus
Adaptive parameters for 24/7 crypto day trading

Author: TradePulse.AI Development Team
Version: 1.0.0 - Professional Adaptive Configuration
"""

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class DayTradingConfig:
    """
    Simple adaptive config for Bitcoin day trading
    
    Integrates with:
    - Intelligent Entry Engine (Kelly Criterion, adaptive thresholds)
    - Intelligent Exit Engine (ATR stops, adaptive timing)
    - Day Trading Validator (dynamic parameters)
    - Historical Context Service (adaptive S/R)
    """
    
    # Analysis timing (adaptive to volatility)
    base_analysis_interval: int = 8  # seconds
    min_analysis_interval: int = 5   # minimum (high volatility)
    max_analysis_interval: int = 15  # maximum (low volatility)
    
    # Session awareness (Bitcoin trades 24/7, minimal but useful)
    session_boost_enabled: bool = True
    
    def get_analysis_interval(
        self, 
        current_volatility: float, 
        avg_volatility: float = 0.015
    ) -> int:
        """
        Adaptive interval based on market volatility
        
        Formula: base / sqrt(vol_ratio)
        - High volatility (2x avg): 8s / sqrt(2) ≈ 5.7s (faster analysis)
        - Normal volatility (1x): 8s / sqrt(1) = 8s (baseline)
        - Low volatility (0.5x): 8s / sqrt(0.5) ≈ 11.3s (slower, save resources)
        
        Args:
            current_volatility: Current market volatility (0-1 scale)
            avg_volatility: Historical average volatility (default: 1.5%)
            
        Returns:
            Adaptive analysis interval in seconds (clamped to 5-15s)
        """
        if avg_volatility <= 0:
            return self.base_analysis_interval
        
        # Calculate volatility ratio
        vol_ratio = current_volatility / avg_volatility
        
        # Adaptive interval: faster when volatile, slower when calm
        # sqrt() provides smooth, non-linear adjustment
        adaptive_interval = int(
            self.base_analysis_interval / math.sqrt(max(0.5, min(3.0, vol_ratio)))
        )
        
        # Clamp to reasonable bounds
        result = max(self.min_analysis_interval, min(self.max_analysis_interval, adaptive_interval))
        
        logger.debug(
            f"📊 Adaptive interval: {result}s "
            f"(vol={current_volatility:.4f}, avg={avg_volatility:.4f}, ratio={vol_ratio:.2f}x)"
        )
        
        return result
    
    def get_session_multiplier(self, hour_utc: Optional[int] = None) -> float:
        """
        Session-based confidence multiplier for Bitcoin trading
        
        Bitcoin trades 24/7, but certain sessions show higher liquidity:
        - US market hours (14:00-21:00 UTC): Peak volume, slight boost
        - EU market hours (7:00-15:00 UTC): High volume, standard
        - Asian/off-peak: Lower volume, slight reduction
        
        These are SUBTLE adjustments (0.95-1.10) because crypto is global.
        Traditional forex session effects are much weaker in crypto.
        
        Args:
            hour_utc: Current UTC hour (0-23). If None, uses current time.
            
        Returns:
            Session multiplier (0.95 - 1.10)
        """
        if not self.session_boost_enabled:
            return 1.0
        
        if hour_utc is None:
            hour_utc = datetime.now(timezone.utc).hour
        
        # US market hours (14:00-21:00 UTC): Peak Bitcoin trading
        if 14 <= hour_utc < 21:
            return 1.10
        
        # EU market hours (7:00-15:00 UTC): High activity
        elif 7 <= hour_utc < 15:
            return 1.05
        
        # EU/US overlap (12:00-16:00 UTC): Highest liquidity
        elif 12 <= hour_utc < 16:
            return 1.12
        
        # Asian/off-peak hours: Still active (crypto never sleeps!)
        else:
            return 0.95


# Singleton instance
_day_trading_config = DayTradingConfig()


def get_day_trading_config() -> DayTradingConfig:
    """
    Get global day trading configuration
    
    Returns:
        Singleton DayTradingConfig instance
    """
    return _day_trading_config


# Export
__all__ = ["DayTradingConfig", "get_day_trading_config"]

