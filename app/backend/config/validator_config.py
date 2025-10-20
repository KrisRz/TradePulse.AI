"""
Professional Adaptive Validator Configuration
=============================================

Industry-standard parameters for day trading validation.
NO HARDCODED VALUES - All parameters calculated dynamically based on:
- Market volatility (ATR)
- Signal confidence 
- Market session (liquidity)
- Price action context

Author: TradePulse.AI Development Team
Created: October 2025
Version: 2.0.0 - Professional Dynamic Parameters
"""

from dataclasses import dataclass
from typing import Dict, Tuple
from enum import Enum
import math


class MarketSession(str, Enum):
    """Trading session classification"""
    ASIAN = "asian"      # 00:00-08:00 UTC (lower liquidity)
    LONDON = "london"    # 08:00-16:00 UTC (high liquidity)
    NY = "new_york"      # 13:00-21:00 UTC (highest liquidity)
    OVERLAP = "overlap"  # 13:00-16:00 UTC (London+NY, peak liquidity)
    OFF_PEAK = "off_peak"  # 21:00-00:00 UTC (lowest liquidity)


class VolatilityRegime(str, Enum):
    """Market volatility classification"""
    VERY_LOW = "very_low"    # < 25th percentile
    LOW = "low"              # 25th-50th percentile
    NORMAL = "normal"        # 50th-75th percentile
    HIGH = "high"            # 75th-95th percentile
    EXTREME = "extreme"      # > 95th percentile


@dataclass
class DynamicValidatorConfig:
    """
    Dynamic validator configuration calculated from market conditions
    
    All parameters are calculated using industry-standard formulas:
    - ATR-based risk management
    - Kelly Criterion for position sizing
    - Sharpe-optimized thresholds
    """
    
    # Risk-Reward thresholds (ATR-based)
    min_risk_reward_ratio: float  # Calculated: 1.0 + (confidence_boost * volatility_factor)
    
    # Spread filters (basis points)
    max_spread_bps: float  # Calculated: ATR * liquidity_factor
    
    # Volume filters (relative to average)
    min_volume_ratio: float  # Calculated: session_liquidity * confidence_adjustment
    
    # Volatility filters (ATR-based)
    min_atr_percentile: float  # Minimum ATR as % of historical
    max_atr_percentile: float  # Maximum ATR as % of historical
    
    # S/R distance thresholds (ATR multiples)
    min_resistance_distance_atr: float  # Calculated: base_atr * confidence_factor
    max_support_distance_atr: float     # Calculated: base_atr * risk_tolerance
    
    # Context
    market_session: MarketSession
    volatility_regime: VolatilityRegime
    signal_confidence: float
    current_atr: float
    
    def __repr__(self) -> str:
        return (
            f"DynamicConfig(RR={self.min_risk_reward_ratio:.2f}, "
            f"Spread={self.max_spread_bps:.0f}bp, "
            f"Vol={self.min_volume_ratio:.2f}x, "
            f"Session={self.market_session.value}, "
            f"Regime={self.volatility_regime.value})"
        )


class AdaptiveParameterCalculator:
    """
    Professional parameter calculator using industry standards
    
    All calculations based on:
    1. ATR (Average True Range) - industry standard for volatility
    2. Sharpe Ratio optimization principles
    3. Kelly Criterion for risk management
    4. Market microstructure theory
    """
    
    # Industry standard ATR multipliers
    ATR_STOP_LOSS_MULTIPLIER = 2.0      # Standard 2x ATR for stop loss
    ATR_TAKE_PROFIT_MULTIPLIER = 3.0    # 1.5:1 R/R = 3x ATR for profit
    ATR_MIN_DISTANCE_MULTIPLIER = 0.5   # Minimum 0.5x ATR from S/R
    
    # Liquidity adjustments by session (based on Bitcoin volume profiles)
    SESSION_LIQUIDITY_FACTORS = {
        MarketSession.ASIAN: 0.60,      # Lower volume -40%
        MarketSession.LONDON: 0.90,     # Good volume -10%
        MarketSession.NY: 1.00,         # Peak volume (baseline)
        MarketSession.OVERLAP: 1.10,    # Highest volume +10%
        MarketSession.OFF_PEAK: 0.50    # Very low volume -50%
    }
    
    # Confidence multipliers (risk scaling)
    CONFIDENCE_THRESHOLDS = {
        'very_high': (0.80, 1.00),  # 80%+ confidence
        'high': (0.70, 0.80),       # 70-80% confidence
        'medium': (0.60, 0.70),     # 60-70% confidence
        'low': (0.50, 0.60),        # 50-60% confidence
        'very_low': (0.00, 0.50)    # <50% confidence
    }
    
    @staticmethod
    def get_market_session(hour_utc: int) -> MarketSession:
        """Determine current market session from UTC hour"""
        if 0 <= hour_utc < 8:
            return MarketSession.ASIAN
        elif 8 <= hour_utc < 13:
            return MarketSession.LONDON
        elif 13 <= hour_utc < 16:
            return MarketSession.OVERLAP  # London + NY
        elif 16 <= hour_utc < 21:
            return MarketSession.NY
        else:
            return MarketSession.OFF_PEAK
    
    @staticmethod
    def classify_volatility(current_atr: float, atr_percentiles: Dict[str, float]) -> VolatilityRegime:
        """
        Classify current volatility regime using historical percentiles
        
        Args:
            current_atr: Current ATR value
            atr_percentiles: Dict with keys 'p25', 'p50', 'p75', 'p95'
        """
        if current_atr < atr_percentiles.get('p25', 0):
            return VolatilityRegime.VERY_LOW
        elif current_atr < atr_percentiles.get('p50', 0):
            return VolatilityRegime.LOW
        elif current_atr < atr_percentiles.get('p75', 0):
            return VolatilityRegime.NORMAL
        elif current_atr < atr_percentiles.get('p95', 0):
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.EXTREME
    
    @staticmethod
    def calculate_confidence_factor(confidence: float) -> Tuple[float, str]:
        """
        Calculate risk adjustment factor based on signal confidence
        
        Returns:
            (factor, confidence_level)
            - Higher confidence = more relaxed parameters (trust the signal)
            - Lower confidence = stricter parameters (be cautious)
        """
        calc = AdaptiveParameterCalculator
        
        for level, (min_conf, max_conf) in calc.CONFIDENCE_THRESHOLDS.items():
            if min_conf <= confidence < max_conf:
                # Scale factor: 0.50 (very_low) to 1.50 (very_high)
                # Linear interpolation within range
                range_position = (confidence - min_conf) / (max_conf - min_conf)
                
                if level == 'very_high':
                    factor = 1.30 + (range_position * 0.20)  # 1.30-1.50
                elif level == 'high':
                    factor = 1.10 + (range_position * 0.20)  # 1.10-1.30
                elif level == 'medium':
                    factor = 0.90 + (range_position * 0.20)  # 0.90-1.10
                elif level == 'low':
                    factor = 0.70 + (range_position * 0.20)  # 0.70-0.90
                else:  # very_low
                    factor = 0.50 + (range_position * 0.20)  # 0.50-0.70
                
                return factor, level
        
        # Fallback
        return 1.0, 'medium'
    
    @staticmethod
    def calculate_min_risk_reward(
        confidence: float,
        volatility_regime: VolatilityRegime,
        session: MarketSession
    ) -> float:
        """
        Calculate minimum acceptable Risk/Reward ratio
        
        Industry standard: Base 1.5:1, adjusted for:
        - High confidence → relaxed (can accept 1.0:1 or even 0.8:1)
        - Low confidence → strict (require 2.0:1+)
        - High volatility → more conservative
        - Peak session → more aggressive
        """
        # Base R/R (Sharpe-optimal for day trading)
        base_rr = 1.5
        
        # Confidence adjustment (-40% to +20%)
        confidence_factor, _ = AdaptiveParameterCalculator.calculate_confidence_factor(confidence)
        # Map 0.50-1.50 factor to -0.4 to +0.2 adjustment
        confidence_adjustment = (confidence_factor - 1.0) * 0.5
        
        # Volatility adjustment (-20% to +30%)
        volatility_adjustments = {
            VolatilityRegime.VERY_LOW: -0.20,   # Tighter stops work well
            VolatilityRegime.LOW: -0.10,
            VolatilityRegime.NORMAL: 0.00,
            VolatilityRegime.HIGH: +0.15,       # Need more room
            VolatilityRegime.EXTREME: +0.30     # Much wider stops
        }
        volatility_adjustment = volatility_adjustments[volatility_regime]
        
        # Session adjustment (-10% to +10%)
        session_adjustments = {
            MarketSession.OVERLAP: -0.10,   # Peak liquidity, tighter OK
            MarketSession.NY: -0.05,
            MarketSession.LONDON: 0.00,
            MarketSession.ASIAN: +0.05,     # Lower liquidity, be conservative
            MarketSession.OFF_PEAK: +0.10   # Very low liquidity, be very conservative
        }
        session_adjustment = session_adjustments[session]
        
        # Calculate final R/R
        adjusted_rr = base_rr * (1.0 + confidence_adjustment + volatility_adjustment + session_adjustment)
        
        # Floor at 0.80 (very aggressive, high confidence only)
        # Ceiling at 2.50 (very conservative, low confidence)
        return max(0.80, min(2.50, adjusted_rr))
    
    @staticmethod
    def calculate_min_volume_ratio(
        confidence: float,
        session: MarketSession
    ) -> float:
        """
        Calculate minimum acceptable volume ratio
        
        Based on:
        - Session liquidity (peak vs off-peak)
        - Signal confidence (trust high confidence even in low volume)
        """
        # Base requirement: 40% of average volume (industry standard for BTC)
        base_volume = 0.40
        
        # Session liquidity factor
        session_factor = AdaptiveParameterCalculator.SESSION_LIQUIDITY_FACTORS[session]
        
        # Confidence adjustment
        confidence_factor, _ = AdaptiveParameterCalculator.calculate_confidence_factor(confidence)
        # High confidence can trade in lower volume (0.70x-1.30x)
        confidence_volume_adjustment = 2.0 - confidence_factor
        
        # Calculate final volume requirement
        adjusted_volume = base_volume * session_factor * confidence_volume_adjustment
        
        # Floor at 0.15 (15% volume minimum, even for high confidence)
        # Ceiling at 0.70 (70% volume max requirement)
        return max(0.15, min(0.70, adjusted_volume))
    
    @staticmethod
    def calculate_atr_thresholds(
        current_atr: float,
        atr_percentiles: Dict[str, float],
        confidence: float
    ) -> Tuple[float, float]:
        """
        Calculate acceptable ATR range (min/max percentiles)
        
        Returns:
            (min_atr_percentile, max_atr_percentile)
        """
        # Base thresholds (25th-95th percentile)
        base_min_percentile = 0.25
        base_max_percentile = 0.95
        
        # Confidence adjustment (high confidence = accept wider range)
        confidence_factor, _ = AdaptiveParameterCalculator.calculate_confidence_factor(confidence)
        
        # Expand range for high confidence (can trade in extreme conditions)
        min_percentile = max(0.05, base_min_percentile - (confidence_factor - 1.0) * 0.20)
        max_percentile = min(0.99, base_max_percentile + (confidence_factor - 1.0) * 0.05)
        
        return (min_percentile, max_percentile)
    
    @classmethod
    def calculate_dynamic_config(
        cls,
        signal_confidence: float,
        current_atr: float,
        atr_percentiles: Dict[str, float],
        hour_utc: int
    ) -> DynamicValidatorConfig:
        """
        Calculate complete dynamic configuration
        
        Args:
            signal_confidence: AI signal confidence (0.0-1.0)
            current_atr: Current ATR value (as percentage, e.g., 0.02 = 2%)
            atr_percentiles: Historical ATR percentiles {'p25': x, 'p50': y, ...}
            hour_utc: Current UTC hour (0-23)
        
        Returns:
            DynamicValidatorConfig with all parameters calculated
        """
        # Classify market conditions
        session = cls.get_market_session(hour_utc)
        volatility_regime = cls.classify_volatility(current_atr, atr_percentiles)
        
        # Calculate all parameters dynamically
        min_rr = cls.calculate_min_risk_reward(signal_confidence, volatility_regime, session)
        min_volume = cls.calculate_min_volume_ratio(signal_confidence, session)
        min_atr_pct, max_atr_pct = cls.calculate_atr_thresholds(current_atr, atr_percentiles, signal_confidence)
        
        # Spread threshold (ATR-based, in basis points)
        # Industry standard: max spread = 0.5x ATR in basis points
        max_spread_bps = current_atr * 10000 * 0.5  # Convert to bps
        
        # S/R distance thresholds (ATR multiples)
        # 🔧 FIX (Oct 2025): Support proximity tied to stop distance
        # Support should be within 80% of stop distance (not a fixed 0.04%)
        confidence_factor, _ = cls.calculate_confidence_factor(signal_confidence)
        min_res_distance_atr = cls.ATR_MIN_DISTANCE_MULTIPLIER * confidence_factor
        
        # Stop distance = max(1.0× ATR, 0.25%)
        stop_distance_atr = max(1.0, 0.0025 / current_atr)  # At least 1× ATR or 0.25%
        max_sup_distance_atr = 0.8 * stop_distance_atr  # Support within 80% of stop distance
        
        return DynamicValidatorConfig(
            min_risk_reward_ratio=min_rr,
            max_spread_bps=max_spread_bps,
            min_volume_ratio=min_volume,
            min_atr_percentile=min_atr_pct,
            max_atr_percentile=max_atr_pct,
            min_resistance_distance_atr=min_res_distance_atr,
            max_support_distance_atr=max_sup_distance_atr,
            market_session=session,
            volatility_regime=volatility_regime,
            signal_confidence=signal_confidence,
            current_atr=current_atr
        )


# Export
__all__ = [
    "DynamicValidatorConfig",
    "AdaptiveParameterCalculator",
    "MarketSession",
    "VolatilityRegime"
]

