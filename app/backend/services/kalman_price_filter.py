"""
Kalman Price Filter - Real-time noise reduction for trading signals
===================================================================

Uses Kalman filtering to smooth price data while maintaining responsiveness
to real market movements. Removes micro-noise from WebSocket ticks without
introducing significant lag.

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import numpy as np
import logging
from typing import Optional, Tuple
from datetime import datetime, timezone
from collections import deque

logger = logging.getLogger(__name__)


class KalmanPriceFilter:
    """
    Kalman Filter for real-time price smoothing
    
    Features:
    - Dynamic noise reduction
    - Fast response to real movements
    - Minimal lag (< 1 tick)
    - Optimized for Bitcoin day trading
    
    Theory:
    - Process noise: How much we expect price to change (volatility)
    - Measurement noise: Tick-to-tick random fluctuations
    - Kalman gain: Dynamic weight between prediction and observation
    """
    
    def __init__(
        self,
        process_variance: float = 1e-5,  # How much price can move (volatility)
        measurement_variance: float = 1e-3,  # Tick noise level
        initial_value: Optional[float] = None,
        smoothing_strength: float = 1.0  # 1.0 = standard, 0.5 = less smooth, 2.0 = more smooth
    ):
        """
        Initialize Kalman Filter
        
        Args:
            process_variance: Expected price movement variance (lower = smoother)
            measurement_variance: Tick noise variance (lower = trust ticks more)
            initial_value: Starting price (None = use first observation)
            smoothing_strength: Multiplier for noise reduction (1.0 = standard)
        """
        # Kalman filter state
        self.process_variance = process_variance * smoothing_strength
        self.measurement_variance = measurement_variance * smoothing_strength
        
        self.posterior_estimate = initial_value  # Current estimate
        self.posterior_error = 1.0  # Estimate uncertainty
        
        # Statistics
        self.observation_count = 0
        self.last_raw_price = None
        self.last_smoothed_price = None
        self.last_update_time = None
        
        # History for debugging
        self.history = deque(maxlen=100)
        
        logger.info(f"🔧 Kalman Filter initialized: process_var={process_variance:.2e}, "
                   f"measurement_var={measurement_variance:.2e}, smoothing={smoothing_strength:.1f}")
    
    def update(self, observed_price: float, timestamp: Optional[datetime] = None) -> float:
        """
        Update filter with new price observation
        
        Args:
            observed_price: Raw price from market
            timestamp: Observation timestamp (optional)
            
        Returns:
            Smoothed price estimate
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # First observation - initialize
        if self.posterior_estimate is None:
            self.posterior_estimate = observed_price
            self.posterior_error = self.measurement_variance
            self.last_raw_price = observed_price
            self.last_smoothed_price = observed_price
            self.last_update_time = timestamp
            self.observation_count = 1
            return observed_price
        
        # PREDICTION STEP
        # Prior estimate = previous posterior (no external model)
        prior_estimate = self.posterior_estimate
        prior_error = self.posterior_error + self.process_variance
        
        # UPDATE STEP
        # Kalman gain: how much to trust new observation vs prediction
        kalman_gain = prior_error / (prior_error + self.measurement_variance)
        
        # Update estimate with observation
        innovation = observed_price - prior_estimate  # Difference from prediction
        self.posterior_estimate = prior_estimate + kalman_gain * innovation
        self.posterior_error = (1 - kalman_gain) * prior_error
        
        # Statistics
        self.observation_count += 1
        self.last_raw_price = observed_price
        self.last_smoothed_price = self.posterior_estimate
        self.last_update_time = timestamp
        
        # Store history for debugging
        self.history.append({
            "timestamp": timestamp,
            "raw": observed_price,
            "smoothed": self.posterior_estimate,
            "gain": kalman_gain,
            "innovation": innovation
        })
        
        # Debug log every 100 observations
        if self.observation_count % 100 == 0:
            noise_reduction_pct = (1 - abs(innovation / (observed_price if observed_price != 0 else 1))) * 100
            logger.debug(f"📊 Kalman stats: observations={self.observation_count}, "
                        f"noise_reduction={noise_reduction_pct:.1f}%, "
                        f"gain={kalman_gain:.4f}")
        
        return self.posterior_estimate
    
    def get_current_estimate(self) -> Optional[float]:
        """Get current smoothed price estimate"""
        return self.posterior_estimate
    
    def get_noise_reduction(self) -> Optional[float]:
        """
        Calculate noise reduction percentage
        
        Returns:
            Percentage of noise removed (0-100)
        """
        if self.last_raw_price is None or self.last_smoothed_price is None:
            return None
        
        if len(self.history) < 2:
            return None
        
        # Calculate variance of raw vs smoothed prices
        raw_prices = [h["raw"] for h in self.history]
        smoothed_prices = [h["smoothed"] for h in self.history]
        
        raw_variance = np.var(raw_prices) if len(raw_prices) > 1 else 0
        smoothed_variance = np.var(smoothed_prices) if len(smoothed_prices) > 1 else 0
        
        if raw_variance == 0:
            return 0.0
        
        reduction_pct = (1 - smoothed_variance / raw_variance) * 100
        return max(0.0, min(reduction_pct, 100.0))  # Clamp to 0-100%
    
    def reset(self):
        """Reset filter state (useful for regime changes)"""
        self.posterior_estimate = None
        self.posterior_error = 1.0
        self.observation_count = 0
        self.last_raw_price = None
        self.last_smoothed_price = None
        self.last_update_time = None
        self.history.clear()
        logger.info("🔄 Kalman Filter reset")
    
    def get_statistics(self) -> dict:
        """Get filter statistics"""
        return {
            "observations": self.observation_count,
            "current_estimate": self.posterior_estimate,
            "posterior_error": self.posterior_error,
            "last_raw": self.last_raw_price,
            "last_smoothed": self.last_smoothed_price,
            "noise_reduction_pct": self.get_noise_reduction(),
            "last_update": self.last_update_time.isoformat() if self.last_update_time else None
        }


class AdaptiveKalmanFilter(KalmanPriceFilter):
    """
    Adaptive Kalman Filter that adjusts parameters based on market volatility
    
    Automatically increases smoothing during high volatility (lots of noise)
    and decreases smoothing during low volatility (preserve signal).
    """
    
    def __init__(
        self,
        base_process_variance: float = 1e-5,
        base_measurement_variance: float = 1e-3,
        volatility_window: int = 20,
        **kwargs
    ):
        super().__init__(
            process_variance=base_process_variance,
            measurement_variance=base_measurement_variance,
            **kwargs
        )
        
        self.base_process_variance = base_process_variance
        self.base_measurement_variance = base_measurement_variance
        self.volatility_window = volatility_window
        self.recent_prices = deque(maxlen=volatility_window)
        
        logger.info(f"🔧 Adaptive Kalman Filter initialized (volatility_window={volatility_window})")
    
    def update(self, observed_price: float, timestamp: Optional[datetime] = None) -> float:
        """Update with adaptive variance based on recent volatility"""
        
        # Store for volatility calculation
        self.recent_prices.append(observed_price)
        
        # Calculate recent volatility
        if len(self.recent_prices) >= 5:
            prices_array = np.array(self.recent_prices)
            returns = np.diff(prices_array) / prices_array[:-1]
            current_volatility = np.std(returns)
            
            # Adjust variances based on volatility
            # High volatility → more smoothing (higher measurement noise)
            # Low volatility → less smoothing (lower measurement noise)
            volatility_multiplier = max(0.5, min(2.0, current_volatility * 100))  # Scale to 0.5-2.0x
            
            self.measurement_variance = self.base_measurement_variance * volatility_multiplier
            
            # Debug log periodically
            if self.observation_count % 50 == 0:
                logger.debug(f"📊 Adaptive Kalman: vol={current_volatility:.4f}, "
                           f"multiplier={volatility_multiplier:.2f}x")
        
        # Call parent update with adjusted variances
        return super().update(observed_price, timestamp)


# Global instance
_kalman_filter: Optional[KalmanPriceFilter] = None
_kalman_enabled = False


def get_kalman_filter(
    adaptive: bool = True,
    smoothing_strength: float = 1.0,
    reset: bool = False
) -> Optional[KalmanPriceFilter]:
    """
    Get or create global Kalman Filter instance
    
    Args:
        adaptive: Use adaptive filter (adjusts to volatility)
        smoothing_strength: Smoothing multiplier (1.0 = standard)
        reset: Force reset of existing filter
        
    Returns:
        KalmanPriceFilter instance or None if disabled
    """
    global _kalman_filter, _kalman_enabled
    
    if not _kalman_enabled:
        return None
    
    if _kalman_filter is None or reset:
        if adaptive:
            _kalman_filter = AdaptiveKalmanFilter(
                smoothing_strength=smoothing_strength
            )
        else:
            _kalman_filter = KalmanPriceFilter(
                smoothing_strength=smoothing_strength
            )
        logger.info(f"✅ Kalman Filter created: adaptive={adaptive}, strength={smoothing_strength}")
    
    return _kalman_filter


def enable_kalman_filter(enabled: bool = True):
    """Enable or disable Kalman filtering globally"""
    global _kalman_enabled
    _kalman_enabled = enabled
    logger.info(f"🔧 Kalman Filter: {'ENABLED' if enabled else 'DISABLED'}")


def is_kalman_enabled() -> bool:
    """Check if Kalman filtering is enabled"""
    return _kalman_enabled


# Export
__all__ = [
    "KalmanPriceFilter",
    "AdaptiveKalmanFilter",
    "get_kalman_filter",
    "enable_kalman_filter",
    "is_kalman_enabled"
]

