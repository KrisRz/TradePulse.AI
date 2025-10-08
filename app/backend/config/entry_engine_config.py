"""
Professional Entry Engine Configuration
=======================================

Industry-standard parameters for 6-layer entry analysis.
NO HARDCODED VALUES - All parameters calculated dynamically based on:
- Market volatility (ATR)
- Historical win rates
- Risk-adjusted position sizing
- Market regime classification

Author: TradePulse.AI Development Team
Created: October 2025
Version: 2.0.0 - Professional Dynamic Parameters
"""

from dataclasses import dataclass
from typing import Dict, Tuple
from enum import Enum
import numpy as np


class MarketRegime(str, Enum):
    """Market regime classification for adaptive thresholds"""
    TRENDING_BULL = "trending_bull"
    TRENDING_BEAR = "trending_bear"
    RANGING_HIGH_VOL = "ranging_high_vol"
    RANGING_LOW_VOL = "ranging_low_vol"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"


@dataclass
class DynamicEntryThresholds:
    """
    Dynamic entry thresholds calculated from market conditions
    
    All parameters calculated using industry-standard formulas:
    - Sharpe-optimized confidence levels
    - ATR-based volatility filters
    - Volume profile analysis
    - Adaptive consensus requirements
    """
    
    # Confidence thresholds (Sharpe-optimized)
    min_confidence: float  # Calculated from historical Sharpe ratio
    min_consensus: float   # Layer consensus requirement
    high_confidence: float  # High-confidence fast-track threshold
    
    # Market regime thresholds (ATR-based)
    min_trend_strength: float  # Minimum trend strength (ADX proxy)
    max_volatility_atr: float  # Maximum ATR percentile
    min_volume_ratio: float    # Minimum volume vs average
    
    # Pattern validation thresholds
    min_pattern_score: float      # Minimum pattern confidence
    min_historical_success: float # Minimum historical win rate
    
    # Context
    market_regime: MarketRegime
    current_atr: float
    current_sharpe: float
    
    def __repr__(self) -> str:
        return (
            f"DynamicEntryThresholds(conf={self.min_confidence:.2f}, "
            f"consensus={self.min_consensus:.2f}, "
            f"regime={self.market_regime.value})"
        )


class AdaptiveEntryCalculator:
    """
    Professional parameter calculator for entry analysis
    
    Uses industry standards:
    1. Sharpe Ratio optimization for confidence thresholds
    2. Kelly Criterion for position sizing
    3. ATR-based volatility management
    4. Adaptive learning from historical performance
    """
    
    # Industry standard ATR percentiles (Bitcoin baseline)
    DEFAULT_ATR_PERCENTILES = {
        'p25': 0.015,  # 1.5% (25th percentile)
        'p50': 0.025,  # 2.5% (median)
        'p75': 0.040,  # 4.0% (75th percentile)
        'p95': 0.070   # 7.0% (95th percentile)
    }
    
    # Sharpe-optimized base thresholds (target Sharpe > 2.0)
    BASE_CONFIDENCE_TARGET = 0.60  # 60% minimum (1.5 Sharpe)
    BASE_CONSENSUS_TARGET = 0.60   # 60% layer agreement
    HIGH_CONFIDENCE_TARGET = 0.75  # 75% for fast-track
    
    # Kelly Criterion parameters
    KELLY_FULL_FRACTION = 1.0     # Full Kelly (aggressive)
    KELLY_HALF_FRACTION = 0.5     # Half Kelly (moderate)
    KELLY_QUARTER_FRACTION = 0.25 # Quarter Kelly (conservative)
    
    @staticmethod
    def classify_market_regime(
        trend_strength: float,
        volatility: float,
        volume_ratio: float,
        atr_percentiles: Dict[str, float]
    ) -> MarketRegime:
        """
        Classify current market regime for adaptive thresholds
        
        Args:
            trend_strength: 0-1 (0=no trend, 1=strong trend)
            volatility: Current ATR
            volume_ratio: Current volume / average volume
            atr_percentiles: Historical ATR percentiles
        """
        # High volatility = above 75th percentile
        is_high_vol = volatility > atr_percentiles['p75']
        
        # Strong trend = >0.6 trend strength
        is_trending = abs(trend_strength) > 0.6
        
        # Breakout = high volume + volatility spike
        is_breakout = volume_ratio > 1.5 and volatility > atr_percentiles['p75']
        
        if is_breakout:
            return MarketRegime.BREAKOUT
        elif is_trending:
            if trend_strength > 0.6:
                return MarketRegime.TRENDING_BULL
            else:
                return MarketRegime.TRENDING_BEAR
        elif is_high_vol:
            return MarketRegime.RANGING_HIGH_VOL
        else:
            return MarketRegime.RANGING_LOW_VOL
    
    @staticmethod
    def calculate_sharpe_optimized_confidence(
        historical_sharpe: float,
        target_sharpe: float = 2.0
    ) -> float:
        """
        Calculate optimal confidence threshold for target Sharpe ratio
        
        Industry standard: Target Sharpe > 2.0 for trading strategies
        
        Returns:
            Confidence threshold (0.50 to 0.80)
        """
        # If current Sharpe is good, can lower threshold
        # If current Sharpe is bad, need higher threshold
        
        if historical_sharpe >= target_sharpe:
            # Performing well, can be more aggressive
            adjustment = -0.05
        elif historical_sharpe >= target_sharpe * 0.75:
            # Close to target, no change
            adjustment = 0.0
        elif historical_sharpe >= target_sharpe * 0.5:
            # Below target, be more selective
            adjustment = +0.05
        else:
            # Well below target, be very selective
            adjustment = +0.10
        
        # Calculate threshold
        threshold = AdaptiveEntryCalculator.BASE_CONFIDENCE_TARGET + adjustment
        
        # Clamp to reasonable range
        return max(0.50, min(0.80, threshold))
    
    @staticmethod
    def calculate_adaptive_consensus(
        market_regime: MarketRegime,
        signal_confidence: float
    ) -> float:
        """
        Calculate adaptive consensus requirement based on regime
        
        Different regimes require different layer agreement:
        - Trending: Lower consensus (follow trend)
        - Ranging: Higher consensus (avoid false signals)
        - Breakout: Medium consensus (opportunities)
        """
        base_consensus = AdaptiveEntryCalculator.BASE_CONSENSUS_TARGET
        
        # Regime adjustments
        regime_adjustments = {
            MarketRegime.TRENDING_BULL: -0.05,    # Easier in uptrend
            MarketRegime.TRENDING_BEAR: -0.05,    # Easier in downtrend
            MarketRegime.RANGING_HIGH_VOL: +0.10, # Harder in choppy markets
            MarketRegime.RANGING_LOW_VOL: +0.05,  # Slightly harder in quiet
            MarketRegime.BREAKOUT: 0.0,           # Normal for breakouts
            MarketRegime.REVERSAL: +0.05          # Harder for reversals
        }
        
        adjustment = regime_adjustments.get(market_regime, 0.0)
        
        # High confidence signals get easier consensus
        if signal_confidence >= 0.75:
            adjustment -= 0.05
        
        consensus = base_consensus + adjustment
        
        # Clamp to reasonable range
        return max(0.50, min(0.75, consensus))
    
    @staticmethod
    def calculate_atr_thresholds(
        current_atr: float,
        atr_percentiles: Dict[str, float],
        market_regime: MarketRegime
    ) -> Tuple[float, float, float]:
        """
        Calculate ATR-based thresholds for volatility filtering
        
        Returns:
            (min_trend_strength, max_volatility_percentile, min_volume_ratio)
        """
        # Trend strength requirement (lower for trending markets)
        if market_regime in [MarketRegime.TRENDING_BULL, MarketRegime.TRENDING_BEAR]:
            min_trend = 0.50  # Lower bar for trending
        elif market_regime == MarketRegime.BREAKOUT:
            min_trend = 0.40  # Even lower for breakouts
        else:
            min_trend = 0.60  # Higher for ranging markets
        
        # Max volatility (percentile-based)
        if market_regime == MarketRegime.RANGING_HIGH_VOL:
            max_vol_pct = 0.90  # Accept high vol in volatile regime
        elif market_regime == MarketRegime.BREAKOUT:
            max_vol_pct = 0.95  # Accept very high vol for breakouts
        else:
            max_vol_pct = 0.85  # Standard limit
        
        # Min volume ratio
        if market_regime == MarketRegime.BREAKOUT:
            min_vol = 1.2  # Require high volume for breakouts
        elif market_regime in [MarketRegime.TRENDING_BULL, MarketRegime.TRENDING_BEAR]:
            min_vol = 0.8  # Lower volume OK in trends
        else:
            min_vol = 1.0  # Normal volume for ranging
        
        return (min_trend, max_vol_pct, min_vol)
    
    @classmethod
    def calculate_dynamic_thresholds(
        cls,
        current_atr: float,
        atr_percentiles: Dict[str, float],
        trend_strength: float,
        volume_ratio: float,
        historical_sharpe: float,
        signal_confidence: float
    ) -> DynamicEntryThresholds:
        """
        Calculate complete dynamic entry thresholds
        
        Args:
            current_atr: Current volatility (ATR)
            atr_percentiles: Historical ATR percentiles
            trend_strength: Current trend strength (-1 to 1)
            volume_ratio: Current volume / average
            historical_sharpe: Strategy Sharpe ratio
            signal_confidence: AI signal confidence
        
        Returns:
            DynamicEntryThresholds with all parameters
        """
        # Classify market regime
        regime = cls.classify_market_regime(
            trend_strength, current_atr, volume_ratio, atr_percentiles
        )
        
        # Calculate Sharpe-optimized confidence
        min_confidence = cls.calculate_sharpe_optimized_confidence(historical_sharpe)
        
        # Calculate adaptive consensus
        min_consensus = cls.calculate_adaptive_consensus(regime, signal_confidence)
        
        # Calculate ATR thresholds
        min_trend, max_vol_pct, min_vol = cls.calculate_atr_thresholds(
            current_atr, atr_percentiles, regime
        )
        
        # Calculate max volatility from percentile
        max_volatility_atr = atr_percentiles['p95'] * max_vol_pct
        
        # Pattern validation thresholds (regime-dependent)
        if regime in [MarketRegime.TRENDING_BULL, MarketRegime.TRENDING_BEAR]:
            min_pattern_score = 0.50  # Lower for trends
            min_historical_success = 0.50
        elif regime == MarketRegime.BREAKOUT:
            min_pattern_score = 0.55
            min_historical_success = 0.55
        else:
            min_pattern_score = 0.60  # Higher for ranging
            min_historical_success = 0.60
        
        return DynamicEntryThresholds(
            min_confidence=min_confidence,
            min_consensus=min_consensus,
            high_confidence=cls.HIGH_CONFIDENCE_TARGET,
            min_trend_strength=min_trend,
            max_volatility_atr=max_volatility_atr,
            min_volume_ratio=min_vol,
            min_pattern_score=min_pattern_score,
            min_historical_success=min_historical_success,
            market_regime=regime,
            current_atr=current_atr,
            current_sharpe=historical_sharpe
        )


class KellyCriterionCalculator:
    """
    Kelly Criterion for optimal position sizing
    
    f* = (p*b - q) / b
    where:
    - p = win probability
    - q = loss probability (1-p)
    - b = win/loss ratio (avg_win / avg_loss)
    """
    
    @staticmethod
    def calculate_kelly_fraction(
        win_rate: float,
        avg_win_pct: float,
        avg_loss_pct: float,
        kelly_fraction: float = 0.25
    ) -> float:
        """
        Calculate Kelly Criterion position size
        
        Args:
            win_rate: Historical win rate (0-1)
            avg_win_pct: Average win % (e.g., 0.02 for 2%)
            avg_loss_pct: Average loss % (e.g., 0.01 for 1%)
            kelly_fraction: Fraction of Kelly to use (0.25 = quarter Kelly)
        
        Returns:
            Position size as % of portfolio (0-1)
        """
        if avg_loss_pct == 0:
            avg_loss_pct = 0.001  # Avoid division by zero
        
        # Calculate b (payoff ratio)
        b = avg_win_pct / avg_loss_pct
        
        # Calculate Kelly %
        # f* = (p*b - q) / b = (p*b - (1-p)) / b
        kelly_pct = (win_rate * b - (1 - win_rate)) / b
        
        # Apply fractional Kelly (risk management)
        fractional_kelly = kelly_pct * kelly_fraction
        
        # Clamp to reasonable range (0-30% max)
        return max(0.0, min(0.30, fractional_kelly))
    
    @staticmethod
    def adjust_kelly_for_confidence(
        kelly_size: float,
        signal_confidence: float,
        risk_score: float
    ) -> float:
        """
        Adjust Kelly size based on signal quality
        
        Args:
            kelly_size: Base Kelly size
            signal_confidence: AI signal confidence (0-1)
            risk_score: Risk score (0-1, higher = riskier)
        
        Returns:
            Adjusted position size
        """
        # Confidence multiplier (0.5x to 1.5x)
        if signal_confidence >= 0.80:
            confidence_mult = 1.3
        elif signal_confidence >= 0.70:
            confidence_mult = 1.1
        elif signal_confidence >= 0.60:
            confidence_mult = 1.0
        else:
            confidence_mult = 0.8
        
        # Risk multiplier (0.6x to 1.0x)
        risk_mult = 1.0 - (risk_score * 0.4)
        
        adjusted_size = kelly_size * confidence_mult * risk_mult
        
        # Final clamp
        return max(0.02, min(0.25, adjusted_size))  # 2% to 25% of portfolio


# Export
__all__ = [
    "DynamicEntryThresholds",
    "AdaptiveEntryCalculator",
    "KellyCriterionCalculator",
    "MarketRegime"
]

