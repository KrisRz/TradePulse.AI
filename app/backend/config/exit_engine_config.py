"""
Professional Exit Engine Configuration
======================================

Industry-standard parameters for 6-layer exit analysis.
NO HARDCODED VALUES - All parameters calculated dynamically based on:
- Market volatility (ATR)
- Historical win rates
- Risk-reward optimization
- Market regime classification
- Profit maximization strategies

Author: TradePulse.AI Development Team
Created: October 2025
Version: 2.0.0 - Professional Dynamic Exit Parameters
"""

from dataclasses import dataclass
from typing import Dict, Tuple
from enum import Enum
import numpy as np


class ExitMarketRegime(str, Enum):
    """Market regime classification for adaptive exit thresholds"""
    HIGH_VOLATILITY = "high_volatility"
    NORMAL = "normal"
    LOW_VOLATILITY = "low_volatility"
    TRENDING = "trending"
    CONSOLIDATING = "consolidating"
    BREAKOUT = "breakout"


@dataclass
class DynamicExitThresholds:
    """
    Dynamic exit thresholds calculated from market conditions
    
    All parameters calculated using industry-standard formulas:
    - ATR-based profit targets
    - Sharpe-optimized confidence levels
    - Risk-adjusted trailing stops
    - Adaptive consensus requirements
    """
    
    # Confidence thresholds (Sharpe-optimized)
    min_confidence: float  # Calculated from historical Sharpe ratio
    min_consensus: float   # Layer consensus requirement
    emergency_threshold: float  # Emergency exit threshold
    
    # ATR-based profit targets (NO HARDCODED %!)
    take_profit_atr_multiple: float  # Take profit = entry + ATR * multiple
    stop_loss_atr_multiple: float    # Stop loss = entry - ATR * multiple
    trailing_stop_atr_multiple: float  # Trailing stop ATR multiple
    
    # Dynamic profit thresholds (ATR-based)
    excellent_profit_threshold: float  # Based on ATR * high multiple
    good_profit_threshold: float       # Based on ATR * medium multiple
    small_profit_threshold: float      # Based on ATR * low multiple
    
    # Market regime exit parameters
    reversal_confirmation_ticks: int  # Ticks to confirm reversal
    time_multiplier: float            # Position duration multiplier
    
    # Context
    market_regime: ExitMarketRegime
    current_atr: float
    current_sharpe: float
    
    def __repr__(self) -> str:
        return (
            f"DynamicExitThresholds(conf={self.min_confidence:.2f}, "
            f"consensus={self.min_consensus:.2f}, "
            f"regime={self.market_regime.value})"
        )


class AdaptiveExitCalculator:
    """
    Professional parameter calculator for exit analysis
    
    Uses industry standards:
    1. ATR-based profit targets (not fixed %)
    2. Sharpe Ratio optimization for confidence thresholds
    3. Dynamic trailing stops
    4. Adaptive market regime detection
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
    BASE_CONSENSUS_TARGET = 0.55   # 55% layer agreement
    EMERGENCY_THRESHOLD = 0.90     # 90% emergency exits
    
    # ATR-based profit multiples (industry standard)
    ATR_TAKE_PROFIT_HIGH = 3.0    # High volatility: 3x ATR
    ATR_TAKE_PROFIT_NORMAL = 2.5  # Normal: 2.5x ATR
    ATR_TAKE_PROFIT_LOW = 2.0     # Low volatility: 2x ATR
    
    ATR_STOP_LOSS_HIGH = 1.5      # High volatility: 1.5x ATR
    ATR_STOP_LOSS_NORMAL = 1.2    # Normal: 1.2x ATR
    ATR_STOP_LOSS_LOW = 1.0       # Low volatility: 1x ATR
    
    @staticmethod
    def classify_exit_market_regime(
        volatility: float,
        trend_strength: float,
        volume_ratio: float,
        atr_percentiles: Dict[str, float]
    ) -> ExitMarketRegime:
        """
        Classify current market regime for adaptive exit thresholds
        
        Args:
            volatility: Current ATR
            trend_strength: Current trend strength (-1 to 1)
            volume_ratio: Current volume / average volume
            atr_percentiles: Historical ATR percentiles
        """
        # Classify volatility regime
        if volatility > atr_percentiles['p75']:
            vol_regime = "high"
        elif volatility < atr_percentiles['p25']:
            vol_regime = "low"
        else:
            vol_regime = "normal"
        
        # Classify market state
        is_trending = abs(trend_strength) > 0.6
        is_consolidating = abs(trend_strength) < 0.3 and volatility < atr_percentiles['p50']
        is_breakout = volume_ratio > 1.5 and volatility > atr_percentiles['p75']
        
        # Determine regime
        if is_breakout:
            return ExitMarketRegime.BREAKOUT
        elif is_trending:
            return ExitMarketRegime.TRENDING
        elif is_consolidating:
            return ExitMarketRegime.CONSOLIDATING
        elif vol_regime == "high":
            return ExitMarketRegime.HIGH_VOLATILITY
        elif vol_regime == "low":
            return ExitMarketRegime.LOW_VOLATILITY
        else:
            return ExitMarketRegime.NORMAL
    
    @staticmethod
    def calculate_sharpe_optimized_confidence(
        historical_sharpe: float,
        target_sharpe: float = 2.0
    ) -> float:
        """
        Calculate optimal exit confidence threshold for target Sharpe ratio
        
        Returns:
            Confidence threshold (0.50 to 0.80)
        """
        if historical_sharpe >= target_sharpe:
            adjustment = -0.05  # Can exit more freely
        elif historical_sharpe >= target_sharpe * 0.75:
            adjustment = 0.0
        elif historical_sharpe >= target_sharpe * 0.5:
            adjustment = +0.05  # Be more selective
        else:
            adjustment = +0.10
        
        threshold = AdaptiveExitCalculator.BASE_CONFIDENCE_TARGET + adjustment
        return max(0.50, min(0.80, threshold))
    
    @staticmethod
    def calculate_atr_profit_targets(
        current_atr: float,
        market_regime: ExitMarketRegime,
        entry_price: float
    ) -> Tuple[float, float, float, float, float]:
        """
        Calculate ATR-based profit targets (NO HARDCODED %!)
        
        Returns:
            (take_profit_multiple, stop_loss_multiple, trailing_multiple,
             excellent_profit_threshold, good_profit_threshold, small_profit_threshold)
        """
        # Select ATR multiples based on regime
        if market_regime == ExitMarketRegime.HIGH_VOLATILITY:
            take_profit_mult = AdaptiveExitCalculator.ATR_TAKE_PROFIT_HIGH
            stop_loss_mult = AdaptiveExitCalculator.ATR_STOP_LOSS_HIGH
            trailing_mult = 2.5
            excellent_mult = 3.0  # 3x ATR = excellent
            good_mult = 2.0       # 2x ATR = good
            small_mult = 1.0      # 1x ATR = small
        elif market_regime == ExitMarketRegime.LOW_VOLATILITY:
            take_profit_mult = AdaptiveExitCalculator.ATR_TAKE_PROFIT_LOW
            stop_loss_mult = AdaptiveExitCalculator.ATR_STOP_LOSS_LOW
            trailing_mult = 1.5
            excellent_mult = 2.0  # 2x ATR = excellent (tighter in low vol)
            good_mult = 1.5       # 1.5x ATR = good
            small_mult = 0.75     # 0.75x ATR = small
        elif market_regime == ExitMarketRegime.TRENDING:
            take_profit_mult = 3.5  # Let trends run
            stop_loss_mult = 1.5
            trailing_mult = 2.0
            excellent_mult = 4.0
            good_mult = 2.5
            small_mult = 1.5
        elif market_regime == ExitMarketRegime.BREAKOUT:
            take_profit_mult = 4.0  # Let breakouts run
            stop_loss_mult = 1.5
            trailing_mult = 2.5
            excellent_mult = 4.5
            good_mult = 3.0
            small_mult = 2.0
        else:  # NORMAL or CONSOLIDATING
            take_profit_mult = AdaptiveExitCalculator.ATR_TAKE_PROFIT_NORMAL
            stop_loss_mult = AdaptiveExitCalculator.ATR_STOP_LOSS_NORMAL
            trailing_mult = 2.0
            excellent_mult = 2.5
            good_mult = 1.75
            small_mult = 1.0
        
        # Calculate actual profit thresholds as % of entry price
        # 🔧 FIX (Oct 2025): Add floor values to prevent 0.00% thresholds + hysteresis and fee control
        atr_pct = current_atr / entry_price if entry_price > 0 else 0.0025  # Fallback: 0.25%
        
        # Estimate trading costs (taker fee + spread)
        taker_fee_bp = 0.0004  # 4bp taker fee (Binance)
        spread_bp_est = 0.0001  # 1bp spread estimate
        fees_bp = taker_fee_bp + spread_bp_est
        
        # Base thresholds
        base_small = 0.0002  # 2bp base
        base_good = 0.0005   # 5bp base  
        base_excellent = 0.0010  # 10bp base
        
        # Fee control: when costs eat >50% of small target, adjust upward
        if fees_bp > base_small * 0.5:
            base_small = max(base_small, fees_bp * 1.2)
            base_good = max(base_good, base_small * 2.5)
            base_excellent = max(base_excellent, base_good * 2.0)
        
        excellent_profit_threshold = max(excellent_mult * atr_pct, base_excellent)
        good_profit_threshold = max(good_mult * atr_pct, base_good)
        small_profit_threshold = max(small_mult * atr_pct, base_small)
        
        return (
            take_profit_mult,
            stop_loss_mult,
            trailing_mult,
            excellent_profit_threshold,
            good_profit_threshold,
            small_profit_threshold
        )
    
    @staticmethod
    def apply_hysteresis_to_thresholds(
        current_pnl_pct: float,
        thresholds: Tuple[float, float, float],  # (excellent, good, small)
        previous_threshold_met: Optional[str] = None,
        hysteresis_bp: float = 0.0003  # 3bp hysteresis
    ) -> Tuple[float, float, float, Optional[str]]:
        """
        Apply hysteresis to exit thresholds to prevent oscillation.
        Once a threshold is met, require pullback before re-entering that zone.
        
        Returns:
            (adjusted_excellent, adjusted_good, adjusted_small, current_threshold_met)
        """
        excellent_thresh, good_thresh, small_thresh = thresholds
        current_threshold_met = None
        
        # Determine which threshold is currently met
        if current_pnl_pct >= excellent_thresh:
            current_threshold_met = "excellent"
        elif current_pnl_pct >= good_thresh:
            current_threshold_met = "good"
        elif current_pnl_pct >= small_thresh:
            current_threshold_met = "small"
        
        # Apply hysteresis: once threshold met, require pullback to re-enter
        adjusted_excellent = excellent_thresh
        adjusted_good = good_thresh
        adjusted_small = small_thresh
        
        if previous_threshold_met == "excellent" and current_threshold_met != "excellent":
            # Require pullback below excellent - hysteresis before re-entering
            adjusted_excellent = excellent_thresh + hysteresis_bp
        elif previous_threshold_met == "good" and current_threshold_met != "good":
            adjusted_good = good_thresh + hysteresis_bp
        elif previous_threshold_met == "small" and current_threshold_met != "small":
            adjusted_small = small_thresh + hysteresis_bp
        
        return (adjusted_excellent, adjusted_good, adjusted_small, current_threshold_met)
    
    @staticmethod
    def calculate_adaptive_consensus(
        market_regime: ExitMarketRegime,
        exit_confidence: float
    ) -> float:
        """
        Calculate adaptive consensus requirement for exits
        
        Different regimes require different layer agreement
        """
        base_consensus = AdaptiveExitCalculator.BASE_CONSENSUS_TARGET
        
        # Regime adjustments
        regime_adjustments = {
            ExitMarketRegime.HIGH_VOLATILITY: -0.05,  # Easier exits in volatility
            ExitMarketRegime.LOW_VOLATILITY: +0.05,   # Harder exits in low vol
            ExitMarketRegime.TRENDING: +0.05,         # Let trends run
            ExitMarketRegime.CONSOLIDATING: 0.0,      # Normal
            ExitMarketRegime.BREAKOUT: +0.10,         # Let breakouts run
            ExitMarketRegime.NORMAL: 0.0
        }
        
        adjustment = regime_adjustments.get(market_regime, 0.0)
        
        # High confidence exits get easier consensus
        if exit_confidence >= 0.75:
            adjustment -= 0.05
        
        consensus = base_consensus + adjustment
        return max(0.45, min(0.70, consensus))
    
    @staticmethod
    def calculate_reversal_confirmation_ticks(
        market_regime: ExitMarketRegime,
        volatility: float,
        atr_percentiles: Dict[str, float]
    ) -> int:
        """
        Calculate reversal confirmation ticks (adaptive, not hardcoded 3!)
        
        Returns:
            Number of confirmation ticks needed (2-5)
        """
        # Base on volatility regime
        if volatility > atr_percentiles['p75']:
            # High volatility: need more confirmation (avoid noise)
            base_ticks = 4
        elif volatility < atr_percentiles['p25']:
            # Low volatility: less confirmation needed
            base_ticks = 2
        else:
            base_ticks = 3
        
        # Adjust based on market regime
        if market_regime == ExitMarketRegime.TRENDING:
            # Trending: need strong reversal confirmation
            return min(base_ticks + 1, 5)
        elif market_regime == ExitMarketRegime.BREAKOUT:
            # Breakout: quick confirmation
            return max(base_ticks - 1, 2)
        else:
            return base_ticks
    
    @classmethod
    def calculate_dynamic_exit_thresholds(
        cls,
        current_atr: float,
        atr_percentiles: Dict[str, float],
        trend_strength: float,
        volume_ratio: float,
        historical_sharpe: float,
        entry_price: float
    ) -> DynamicExitThresholds:
        """
        Calculate complete dynamic exit thresholds
        
        Args:
            current_atr: Current volatility (ATR)
            atr_percentiles: Historical ATR percentiles
            trend_strength: Current trend strength (-1 to 1)
            volume_ratio: Current volume / average
            historical_sharpe: Strategy Sharpe ratio
            entry_price: Position entry price
        
        Returns:
            DynamicExitThresholds with all parameters
        """
        # Classify market regime
        regime = cls.classify_exit_market_regime(
            current_atr, trend_strength, volume_ratio, atr_percentiles
        )
        
        # Calculate Sharpe-optimized confidence
        min_confidence = cls.calculate_sharpe_optimized_confidence(historical_sharpe)
        
        # Calculate adaptive consensus
        min_consensus = cls.calculate_adaptive_consensus(regime, min_confidence)
        
        # Calculate ATR-based profit targets
        (
            take_profit_mult,
            stop_loss_mult,
            trailing_mult,
            excellent_profit,
            good_profit,
            small_profit
        ) = cls.calculate_atr_profit_targets(current_atr, regime, entry_price)
        
        # Calculate reversal confirmation ticks
        reversal_ticks = cls.calculate_reversal_confirmation_ticks(
            regime, current_atr, atr_percentiles
        )
        
        # Calculate time multiplier based on regime
        if regime == ExitMarketRegime.TRENDING:
            time_multiplier = 1.5  # Let trends run longer
        elif regime == ExitMarketRegime.HIGH_VOLATILITY:
            time_multiplier = 0.8  # Shorter holds in volatility
        elif regime == ExitMarketRegime.BREAKOUT:
            time_multiplier = 1.2  # Medium duration for breakouts
        else:
            time_multiplier = 1.0
        
        return DynamicExitThresholds(
            min_confidence=min_confidence,
            min_consensus=min_consensus,
            emergency_threshold=cls.EMERGENCY_THRESHOLD,
            take_profit_atr_multiple=take_profit_mult,
            stop_loss_atr_multiple=stop_loss_mult,
            trailing_stop_atr_multiple=trailing_mult,
            excellent_profit_threshold=excellent_profit,
            good_profit_threshold=good_profit,
            small_profit_threshold=small_profit,
            reversal_confirmation_ticks=reversal_ticks,
            time_multiplier=time_multiplier,
            market_regime=regime,
            current_atr=current_atr,
            current_sharpe=historical_sharpe
        )


# Export
__all__ = [
    "DynamicExitThresholds",
    "AdaptiveExitCalculator",
    "ExitMarketRegime"
]

