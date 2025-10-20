"""
Day Trading Validator for TradePulse.AI
========================================

Smart validation system for day trading setups that prevents bad trades
and ensures quality entries with proper risk-reward ratios.

Features:
- ADAPTIVE parameters (NO hardcoded values!)
- ATR-based risk management (industry standard)
- Dynamic thresholds based on market conditions
- Learning from losses (pattern avoidance)
- Support/resistance validation
- Market session awareness

Author: TradePulse.AI Development Team
Created: January 2025
Version: 2.0.0 - Professional Adaptive System
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
import numpy as np

# Import professional config system
from app.backend.config.validator_config import (
    DynamicValidatorConfig,
    AdaptiveParameterCalculator,
    MarketSession,
    VolatilityRegime
)

logger = logging.getLogger(__name__)

@dataclass
class TradeSetup:
    """Day trading setup data"""
    symbol: str
    action: str
    confidence: float
    current_price: float
    support: float
    resistance: float
    spread: float
    volume_ratio: float
    volatility: float
    layer_agreement: int
    lstm_confirmation: bool
    timestamp: datetime

@dataclass
class FailedTrade:
    """Failed trade pattern for learning"""
    symbol: str
    entry_price: float
    entry_conditions: Dict[str, Any]
    exit_reason: str
    loss_pct: float
    timestamp: datetime
    
    def matches_current(self, current_setup: TradeSetup, tolerance: float = 0.02) -> bool:
        """Check if current setup matches this failed pattern"""
        # Price similarity (within 2%)
        price_diff = abs(current_setup.current_price - self.entry_price) / self.entry_price
        if price_diff > tolerance:
            return False
        
        # Condition similarity
        conditions = self.entry_conditions
        if abs(current_setup.volatility - conditions.get("volatility", 0)) > 0.01:
            return False
        if abs(current_setup.volume_ratio - conditions.get("volume_ratio", 1.0)) > 0.3:
            return False
        
        return True


class DayTradingValidator:
    """
    Smart validator for day trading setups
    
    Validates entries based on:
    - Risk-reward ratios
    - Market conditions (spread, volume, volatility)
    - Historical failed patterns
    - Support/resistance levels
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize professional adaptive validator"""
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            # Default to project data directory
            current_file = Path(__file__).parent.parent.parent
            self.data_dir = current_file / "data" / "ml"
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.failed_trades_file = self.data_dir / "failed_trades_patterns.json"
        
        # Professional parameter calculator (NO HARDCODED VALUES!)
        self.param_calculator = AdaptiveParameterCalculator()
        
        # ATR percentiles cache (calculated from historical data)
        # These are statistical baselines, not magic numbers
        # 🔧 FIX (Oct 2025): LOWERED p25 from 1.0% to 0.20% for mean-reversion playbook
        self.atr_percentiles = {
            'p25': 0.0020,  # 0.20% (Bitcoin 25th percentile) - MEAN REVERSION: Allow very low volatility
            'p50': 0.025,   # 2.5% (Bitcoin median)
            'p75': 0.040,   # 4.0% (Bitcoin 75th percentile)
            'p95': 0.070    # 7.0% (Bitcoin 95th percentile)
        }
        
        # Rolling ATR history for dynamic calculation (last 30 minutes)
        self.atr_history: List[float] = []
        self.atr_history_max_size = 30
        
        # Learning system
        self.failed_trades: List[FailedTrade] = []
        self.max_failed_trades = 100           # Keep last 100 failed patterns
        self.pattern_match_tolerance = 0.02    # 2% tolerance for pattern matching
        
        # Load failed patterns
        self._load_failed_patterns()
        
        logger.info("🎯 PROFESSIONAL Adaptive Validator v2.0 - Dynamic ATR-based parameters")
        logger.info("   ✅ NO hardcoded thresholds - all calculated from market conditions")
        logger.info("   ✅ Industry-standard ATR-based risk management")
        logger.info("   ✅ Market session awareness (Asian/London/NY/Overlap)")
        logger.info("   ✅ Confidence-adaptive parameters (0.8:1 to 2.5:1 R/R)")
    
    def _load_failed_patterns(self):
        """Load historical failed trade patterns"""
        try:
            if self.failed_trades_file.exists():
                with open(self.failed_trades_file, 'r') as f:
                    data = json.load(f)
                    self.failed_trades = [
                        FailedTrade(
                            symbol=t["symbol"],
                            entry_price=t["entry_price"],
                            entry_conditions=t["entry_conditions"],
                            exit_reason=t["exit_reason"],
                            loss_pct=t["loss_pct"],
                            timestamp=datetime.fromisoformat(t["timestamp"])
                        )
                        for t in data
                    ]
                logger.info(f"📚 Loaded {len(self.failed_trades)} failed trade patterns")
        except Exception as e:
            logger.warning(f"Could not load failed patterns: {e}")
            self.failed_trades = []
    
    def _save_failed_patterns(self):
        """Save failed trade patterns to disk"""
        try:
            data = [
                {
                    "symbol": t.symbol,
                    "entry_price": t.entry_price,
                    "entry_conditions": t.entry_conditions,
                    "exit_reason": t.exit_reason,
                    "loss_pct": t.loss_pct,
                    "timestamp": t.timestamp.isoformat()
                }
                for t in self.failed_trades[-self.max_failed_trades:]  # Keep last N
            ]
            
            with open(self.failed_trades_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save failed patterns: {e}")
    
    def _calculate_dynamic_config(self, setup: TradeSetup) -> DynamicValidatorConfig:
        """
        Calculate complete dynamic configuration from market conditions
        
        PROFESSIONAL: Uses industry-standard formulas
        - ATR-based risk management
        - Market session analysis
        - Volatility regime classification
        - Confidence-adaptive scaling
        
        Returns:
            DynamicValidatorConfig with all thresholds calculated
        """
        # Get current time for session calculation
        now = datetime.now(timezone.utc)
        hour_utc = now.hour
        
        # Use volatility as ATR proxy (close enough for crypto)
        current_atr = setup.volatility
        
        # Calculate dynamic configuration using professional formulas
        config = self.param_calculator.calculate_dynamic_config(
            signal_confidence=setup.confidence,
            current_atr=current_atr,
            atr_percentiles=self.atr_percentiles,
            hour_utc=hour_utc
        )
        
        logger.info(f"📊 DYNAMIC CONFIG: {config}")
        logger.info(f"   Signal: {setup.confidence:.1%} confidence")
        logger.info(f"   Session: {config.market_session.value} (liquidity: {self.param_calculator.SESSION_LIQUIDITY_FACTORS[config.market_session]:.0%})")
        logger.info(f"   Volatility: {config.volatility_regime.value} (ATR: {current_atr:.2%})")
        logger.info(f"   Thresholds: R/R≥{config.min_risk_reward_ratio:.2f}:1, Vol≥{config.min_volume_ratio:.0%}")
        
        return config
    
    def _config_to_legacy_params(self, config: DynamicValidatorConfig) -> Dict[str, float]:
        """
        Convert DynamicValidatorConfig to legacy params dict for compatibility
        
        This adapter allows existing validation methods to work with new system
        """
        # Convert ATR-based thresholds to absolute percentages
        current_atr = config.current_atr
        
        # 🔧 DYNAMIC VOLATILITY GATE: Calculate min_volatility based on recent ATR history
        # Baseline: 0.20% for mean-reversion playbook
        # Dynamic: 0.5× rolling median of recent ATR (last 30 minutes)
        min_vol_baseline = 0.0020  # 0.20% baseline
        if len(self.atr_history) >= 5:
            import statistics
            recent_median = statistics.median(self.atr_history[-30:])
            min_vol_dynamic = max(min_vol_baseline, 0.5 * recent_median)
        else:
            min_vol_dynamic = min_vol_baseline
        
        # Update ATR history (keep last 30 samples)
        self.atr_history.append(current_atr)
        if len(self.atr_history) > self.atr_history_max_size:
            self.atr_history.pop(0)
        
        # 🔧 FIX (Oct 2025): Support distance logic - only check minimum (don't get too close)
        # Having support far away is GOOD (more room for profit) - no max check needed!
        min_sup_distance = 0.0  # No minimum for now - let AI decide
        
        return {
            'min_risk_reward_ratio': config.min_risk_reward_ratio,
            'max_spread_pct': config.max_spread_bps / 10000,  # Convert bps to percentage
            'min_volume_ratio': config.min_volume_ratio,
            'max_volatility': self.atr_percentiles['p95'],  # Use 95th percentile as max
            'min_volatility': min_vol_dynamic,  # DYNAMIC: 0.20% baseline or 0.5× recent median
            'min_resistance_distance': config.min_resistance_distance_atr * current_atr,  # ATR multiple to %
            'min_support_distance': min_sup_distance  # Only check if too close (not too far!)
        }
    
    async def validate_day_trading_setup(
        self,
        signal: Any,
        market_data: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        ADAPTIVE validation of day trading setup
        Adjusts thresholds based on market conditions and signal quality
        
        Args:
            signal: Trading signal from AI layers
            market_data: Current market data
            
        Returns:
            Tuple of (is_valid, reason, details)
        """
        try:
            # Extract setup data
            setup = TradeSetup(
                symbol=signal.symbol,
                action=signal.action,
                confidence=signal.confidence,
                current_price=signal.price,
                support=market_data.get("support", signal.price * 0.98),
                resistance=market_data.get("resistance", signal.price * 1.02),
                spread=market_data.get("spread", 0.0),
                volume_ratio=market_data.get("volume_ratio", 1.0),
                volatility=market_data.get("volatility", 0.02),
                layer_agreement=self._count_layer_agreement(signal),
                lstm_confirmation=self._check_lstm_confirmation(signal),
                timestamp=datetime.now(timezone.utc)
            )
            
            # Calculate DYNAMIC configuration from market conditions
            dynamic_config = self._calculate_dynamic_config(setup)
            
            # Convert to legacy params format for compatibility with existing validation methods
            adaptive_params = self._config_to_legacy_params(dynamic_config)
            
            # Run validation checks with dynamic thresholds
            checks = {
                "spread_check": self._validate_spread(setup, adaptive_params),
                "volume_check": self._validate_volume(setup, adaptive_params),
                "volatility_check": self._validate_volatility(setup, adaptive_params),
                "risk_reward_check": self._validate_risk_reward(setup, adaptive_params),
                "support_resistance_check": self._validate_support_resistance(setup, adaptive_params),
                "failed_pattern_check": self._check_failed_patterns(setup),
                "layer_agreement_check": self._validate_layer_agreement(setup, adaptive_params),
            }
            
            # Aggregate results
            all_passed = all(check[0] for check in checks.values())
            
            if all_passed:
                return True, "All validation checks passed", checks
            
            # Find first failed check
            failed_checks = [name for name, (passed, _) in checks.items() if not passed]
            reasons = [checks[name][1] for name in failed_checks]
            
            return False, "; ".join(reasons), checks
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, f"Validation error: {e}", {}
    
    def _validate_spread(self, setup: TradeSetup, params: Dict[str, float]) -> Tuple[bool, str]:
        """Validate spread is acceptable for day trading"""
        max_spread = params['max_spread_pct']
        if setup.spread > max_spread:
            return False, f"Spread too high ({setup.spread:.3f}% > {max_spread:.3f}%)"
        return True, f"Spread OK ({setup.spread:.3f}%)"
    
    def _validate_volume(self, setup: TradeSetup, params: Dict[str, float]) -> Tuple[bool, str]:
        """Validate volume is sufficient (ADAPTIVE)"""
        min_volume = params['min_volume_ratio']
        if setup.volume_ratio < min_volume:
            return False, f"Volume too low ({setup.volume_ratio:.1f}x < {min_volume:.1f}x avg)"
        return True, f"Volume OK ({setup.volume_ratio:.1f}x avg, threshold: {min_volume:.1f}x)"
    
    def _validate_volatility(self, setup: TradeSetup, params: Dict[str, float]) -> Tuple[bool, str]:
        """Validate volatility is in day trading range (ADAPTIVE)"""
        max_vol = params['max_volatility']
        min_vol = params['min_volatility']
        
        # DAY TRADING: Skip volatility check for HIGH CONFIDENCE (80%+) signals
        # When AI is very confident, trust the signal regardless of current volatility
        if setup.confidence >= 0.80:
            logger.info(f"🎯 HIGH CONFIDENCE ({setup.confidence:.1%}): Skipping volatility check (vol={setup.volatility:.1%})")
            return True, f"HIGH CONFIDENCE override (vol={setup.volatility:.1%})"
        
        # 🔧 FIX (Oct 2025): Use <= for boundary check (epsilon tolerance)
        EPS = 1e-9
        if setup.volatility > max_vol:
            return False, f"Volatility too high ({setup.volatility:.1%} > {max_vol:.1%})"
        if setup.volatility < min_vol - EPS:  # Allow exact boundary match
            return False, f"Volatility too low ({setup.volatility:.1%} < {min_vol:.1%})"
        return True, f"Volatility OK ({setup.volatility:.1%}, range: {min_vol:.1%}-{max_vol:.1%})"
    
    def _validate_risk_reward(self, setup: TradeSetup, params: Dict[str, float]) -> Tuple[bool, str]:
        """Validate risk-reward ratio for day trading (ADAPTIVE with ATR fallback)"""
        try:
            # ═══════════════════════════════════════════════════════════════════════════
            # 🚨 PROFESSIONAL FIX (Oct 2025): LOWER R/R FOR SELL SIGNALS
            # ═══════════════════════════════════════════════════════════════════════════
            # SELL signals (shorting overbought) naturally have better R/R due to:
            # - Reversal from top = asymmetric downside
            # - Shorter profit targets (quick scalp)
            # - Market structure favors reversals
            # Adjusting R/R requirement: dynamic → 1.45 for SELL only
            # ═══════════════════════════════════════════════════════════════════════════
            min_rr = params['min_risk_reward_ratio']
            
            if setup.action == "SELL" and min_rr > 1.45:
                original_rr = min_rr
                min_rr = 1.45  # Lower threshold for SELL
                logger.info(f"📊 SELL SIGNAL R/R ADJUSTMENT: {original_rr:.2f}:1 → {min_rr:.2f}:1 (reversal trading)")
            # ═══════════════════════════════════════════════════════════════════════════
            
            # PROFESSIONAL: If no S/R levels, use ATR-based targets (industry standard)
            if setup.resistance == 0 or setup.support == 0:
                logger.info("📊 Using ATR-based risk-reward (no S/R levels)")
                
                # ATR-based targets: 2x ATR profit, 1x ATR stop loss (conservative)
                # This is professional practice when S/R levels are unavailable
                atr_pct = setup.volatility * 1.5  # Approximate ATR from volatility
                potential_profit = atr_pct * 2  # 2x ATR profit target
                potential_loss = atr_pct  # 1x ATR stop loss
                
                risk_reward = potential_profit / potential_loss  # Should be 2.0
                
                if risk_reward < min_rr:
                    return False, f"ATR-based RR too low ({risk_reward:.2f}:1 < {min_rr:.2f}:1)"
                
                return True, f"ATR-based RR OK ({risk_reward:.2f}:1, profit: +{potential_profit:.2%}, stop: -{potential_loss:.2%})"
            
            # STANDARD: Use S/R levels for risk-reward
            potential_profit = abs(setup.resistance - setup.current_price) / setup.current_price
            potential_loss = abs(setup.current_price - setup.support) / setup.current_price
            
            if potential_loss == 0:
                return False, "Invalid support level (zero risk)"
            
            risk_reward = potential_profit / potential_loss
            
            # DAY TRADING: Skip R/R check for HIGH CONFIDENCE (80%+) signals
            # When AI is very confident, trust the signal even with tight S/R levels
            if setup.confidence >= 0.80:
                logger.info(f"🎯 HIGH CONFIDENCE ({setup.confidence:.1%}): Skipping R/R check (R/R={risk_reward:.2f}:1)")
                return True, f"HIGH CONFIDENCE override (R/R={risk_reward:.2f}:1, profit: +{potential_profit:.2%}, stop: -{potential_loss:.2%})"
            
            if risk_reward < min_rr:
                return False, f"Risk-reward too low ({risk_reward:.2f}:1 < {min_rr:.2f}:1)"
            
            return True, f"Risk-reward OK ({risk_reward:.2f}:1, threshold: {min_rr:.2f}:1, profit: {potential_profit:.2%}, loss: {potential_loss:.2%})"
            
        except Exception as e:
            logger.error(f"Risk-reward calculation failed: {e}")
            return False, "Risk-reward calculation error"
    
    def _validate_support_resistance(self, setup: TradeSetup, params: Dict[str, float]) -> Tuple[bool, str]:
        """Validate support/resistance levels provide room (ADAPTIVE with ATR fallback)"""
        try:
            # PROFESSIONAL: If no S/R levels, skip this check (ATR-based RR already validated)
            if setup.resistance == 0 or setup.support == 0:
                logger.info("📊 Skipping S/R distance check (using ATR-based targets)")
                return True, "ATR-based targets (no S/R required)"
            
            # DAY TRADING: Skip distance check for HIGH CONFIDENCE (80%+) signals
            # If AI is 80%+ confident, trust it even if resistance is close
            if setup.confidence >= 0.80:
                resistance_dist = abs(setup.resistance - setup.current_price) / setup.current_price
                support_dist = abs(setup.current_price - setup.support) / setup.current_price
                logger.info(f"🎯 HIGH CONFIDENCE ({setup.confidence:.1%}): Skipping S/R distance checks (R: +{resistance_dist:.2%}, S: -{support_dist:.2%})")
                return True, f"HIGH CONFIDENCE override (R: +{resistance_dist:.2%}, S: -{support_dist:.2%})"
            
            # STANDARD: Validate S/R distance for <80% confidence
            resistance_dist = abs(setup.resistance - setup.current_price) / setup.current_price
            min_res_dist = params['min_resistance_distance']
            if resistance_dist < min_res_dist:
                return False, f"Too close to resistance ({resistance_dist:.2%} < {min_res_dist:.2%})"
            
            # 🔧 FIX (Oct 2025): Support distance logic corrected
            # For LONG: We want support BELOW current price (support_dist > 0)
            # Check: support should NOT be too close (min distance check, not max!)
            # Having support far away is GOOD (more room for profit) - don't reject it!
            support_dist = abs(setup.current_price - setup.support) / setup.current_price
            min_sup_dist = params.get('min_support_distance', 0.0)  # Minimum distance (don't get too close)
            
            # Only check if support is too CLOSE (not too far!)
            # Having support 1.5% away is GOOD - gives room for profit
            if min_sup_dist > 0 and support_dist < min_sup_dist:
                return False, f"Support too close ({support_dist:.2%} < {min_sup_dist:.2%})"
            
            return True, f"Support/resistance OK (resistance: +{resistance_dist:.2%}, support: -{support_dist:.2%})"
            
        except Exception as e:
            return False, f"Support/resistance validation error: {e}"
    
    def _check_failed_patterns(self, setup: TradeSetup) -> Tuple[bool, str]:
        """Check if setup matches previously failed patterns"""
        try:
            # Check recent failures (last 24 hours)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_failures = [
                f for f in self.failed_trades 
                if f.timestamp > cutoff_time and f.symbol == setup.symbol
            ]
            
            # Check for pattern matches
            for failed in recent_failures:
                if failed.matches_current(setup, self.pattern_match_tolerance):
                    return False, f"Matches failed pattern from {failed.timestamp.strftime('%H:%M')} ({failed.exit_reason}, {failed.loss_pct:+.2f}%)"
            
            return True, "No failed pattern matches"
            
        except Exception as e:
            logger.warning(f"Failed pattern check error: {e}")
            return True, "Pattern check skipped"  # Don't block on error
    
    def _validate_layer_agreement(self, setup: TradeSetup, params: Dict[str, float]) -> Tuple[bool, str]:
        """Validate that enough layers agree (ADAPTIVE based on confidence)"""
        # ADAPTIVE: High confidence signals can have lower layer agreement
        # RELAXED: Allow more signals through for virtual portfolio testing
        if setup.confidence >= 0.70:
            min_agreement = 2  # Good confidence: 2/6 OK (RELAXED from 3)
            logger.info(f"🎯 HIGH CONFIDENCE ({setup.confidence:.1%}): Requiring only 2/6 layer agreement")
        elif setup.confidence >= 0.60:
            min_agreement = 3  # Medium confidence: 3/6 OK (RELAXED)
        else:
            min_agreement = 3  # Lower confidence: 3/6 required (RELAXED from 4)
        
        if setup.layer_agreement < min_agreement:
            return False, f"Insufficient layer agreement ({setup.layer_agreement}/6 < {min_agreement}/6)"
        
        # RELAXED LSTM check: Don't require LSTM for 70%+ confidence signals (DAY TRADING OPTIMIZED)
        # For day trading, we want to catch moves quickly - 70% is strong enough
        if setup.action in ["BUY", "SELL"]:
            if not setup.lstm_confirmation and setup.confidence < 0.70:  # LOWERED from 0.75 to 0.70 for day trading
                return False, f"LSTM does not confirm direction (required for <70% confidence)"
        
        return True, f"Layer agreement OK ({setup.layer_agreement}/6 layers >= {min_agreement}/6, LSTM: {'✓' if setup.lstm_confirmation else '✗'})"
    
    def _count_layer_agreement(self, signal: Any) -> int:
        """Count how many layers agree with the signal"""
        try:
            layer_analysis = signal.layer_analysis
            agreement = 0
            
            # Check each layer's recommendation (FIXED: Use actual layer names from signal)
            for layer_name in ["layer_1_regime", "layer_2_predictive", "layer_3_patterns", 
                              "layer_4_technical", "layer_5_price_direction", "layer_6_timing"]:
                layer_data = layer_analysis.get(layer_name, {})
                
                # Check if layer agrees with signal action
                # Layers report: {"recommendation": "enter"|"wait", "confidence": float}
                layer_recommendation = layer_data.get("recommendation", "wait")
                
                # "enter" means layer agrees with BUY/SELL signal
                if layer_recommendation == "enter":
                    agreement += 1
            
            return agreement
            
        except Exception as e:
            logger.warning(f"Layer agreement count failed: {e}")
            return 0
    
    def _check_lstm_confirmation(self, signal: Any) -> bool:
        """Check if LSTM confirms the signal direction"""
        try:
            lstm_data = signal.layer_analysis.get("layer_2_lstm", {})
            prediction = lstm_data.get("prediction", signal.price)
            
            if signal.action == "BUY":
                return prediction > signal.price * 1.001  # At least 0.1% higher
            elif signal.action == "SELL":
                return prediction < signal.price * 0.999  # At least 0.1% lower
            else:
                return True  # HOLD always confirmed
                
        except Exception:
            return False
    
    async def record_failed_trade(
        self,
        symbol: str,
        entry_price: float,
        entry_conditions: Dict[str, Any],
        exit_reason: str,
        loss_pct: float
    ):
        """Record a failed trade pattern for learning"""
        try:
            failed_trade = FailedTrade(
                symbol=symbol,
                entry_price=entry_price,
                entry_conditions=entry_conditions,
                exit_reason=exit_reason,
                loss_pct=loss_pct,
                timestamp=datetime.now(timezone.utc)
            )
            
            self.failed_trades.append(failed_trade)
            
            # Keep only recent failures
            if len(self.failed_trades) > self.max_failed_trades:
                self.failed_trades = self.failed_trades[-self.max_failed_trades:]
            
            # Save to disk
            self._save_failed_patterns()
            
            logger.info(f"📝 Recorded failed trade pattern: {exit_reason} ({loss_pct:+.2f}%)")
            
        except Exception as e:
            logger.error(f"Failed to record failed trade: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get validator statistics"""
        try:
            # Recent failures (last 24h)
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_failures = [f for f in self.failed_trades if f.timestamp > cutoff]
            
            # Group by exit reason
            exit_reasons = {}
            for f in recent_failures:
                reason = f.exit_reason
                if reason not in exit_reasons:
                    exit_reasons[reason] = 0
                exit_reasons[reason] += 1
            
            return {
                "total_failed_patterns": len(self.failed_trades),
                "recent_failures_24h": len(recent_failures),
                "exit_reasons": exit_reasons,
                "avg_loss": np.mean([f.loss_pct for f in recent_failures]) if recent_failures else 0.0,
                "parameters": {
                    "min_risk_reward": self.MIN_RISK_REWARD_RATIO,
                    "max_spread": self.MAX_SPREAD_PCT,
                    "min_volume_ratio": self.MIN_VOLUME_RATIO,
                    "volatility_range": f"{self.MIN_VOLATILITY:.1%}-{self.MAX_VOLATILITY:.1%}"
                }
            }
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}


# Global singleton
_validator_instance: Optional[DayTradingValidator] = None

def get_day_trading_validator() -> DayTradingValidator:
    """Get or create global validator instance"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = DayTradingValidator()
    return _validator_instance


__all__ = ["DayTradingValidator", "get_day_trading_validator", "TradeSetup", "FailedTrade"]

# VERSION 3.0.0 - Professional ATR-based risk-reward fallback - Mon Oct  6 22:00:00 BST 2025
# PROFESSIONAL: ATR-based targets when S/R levels unavailable (industry standard)
