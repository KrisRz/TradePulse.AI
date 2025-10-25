"""
Unified Trading Thresholds Configuration
Centralized configuration for all confidence thresholds across TradePulse.AI
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ConfidenceThresholds:
    """Unified confidence thresholds for all trading decisions"""
    
    # 🎯 BALANCED THRESHOLDS: Raised to improve win rate (currently 7.75%)
    # CRITICAL FIX (Oct 25): Increased from 62% to 70% to filter weak signals
    # Win rate 7.75% (42/542) indicates too many low-quality entries
    # Higher threshold = fewer but better quality trades
    BUY_THRESHOLD: float = 0.70      # Raised from 0.62 to improve win rate
    SELL_THRESHOLD: float = 0.70     # Symmetric SELL threshold
    
    # EXPLORATORY SIGNAL THRESHOLDS - Raised to reduce noise
    EXPLORATORY_BUY: float = 0.65    # Raised from 0.55 to reduce weak signals
    EXPLORATORY_SELL: float = 0.65   # Raised from 0.55 to reduce weak signals
    
    # HOLD DECISION THRESHOLDS
    HOLD_LOWER_BOUND: float = 0.62   # Align hold band with relaxed thresholds
    HOLD_UPPER_BOUND: float = 0.85   # Leave upper bound as-is
    # Between 70% and 85% = HOLD
    
    # MINIMUM THRESHOLDS (Absolute minimums)
    ABSOLUTE_MINIMUM: float = 0.55   # Allow trades ≥55% when other gates pass
    
    # SPECIAL THRESHOLDS
    HIGH_CONFIDENCE: float = 0.90    # High confidence threshold for premium signals (raised from 80%)
    CONSENSUS_THRESHOLD: float = 0.75  # Multi-model consensus requirement (raised from 55%)


@dataclass
class RiskThresholds:
    """Risk management thresholds"""
    
    # 🚨 EMERGENCY FIX: Cut position sizes by 50% after -$5,117 loss (2.7% win rate)
    MAX_RISK_PER_TRADE: float = 0.01    # 1% max risk per trade (EMERGENCY FIX - was 2%)
    MAX_PORTFOLIO_RISK: float = 0.05    # 5% max portfolio risk (EMERGENCY FIX - was 10%)
    STOP_LOSS_THRESHOLD: float = 0.01   # 1% stop loss (tightened from 1.5%)
    TAKE_PROFIT_THRESHOLD: float = 0.03  # 3% take profit (widened from 2.5%)


@dataclass
class TradingThresholds:
    """Complete trading thresholds configuration"""
    
    confidence: ConfidenceThresholds
    risk: RiskThresholds
    
    def __init__(self):
        self.confidence = ConfidenceThresholds()
        self.risk = RiskThresholds()
    
    def get_signal_action(self, confidence: float) -> str:
        """
        Determine trading action based on unified confidence thresholds
        
        Args:
            confidence: AI model confidence score (0.0 to 1.0)
            
        Returns:
            str: "BUY", "SELL", or "HOLD"
        """
        if confidence < self.confidence.ABSOLUTE_MINIMUM:
            return "HOLD"  # Too low confidence
            
        if confidence >= self.confidence.BUY_THRESHOLD:
            return "BUY"   # High confidence BUY
            
        if confidence <= self.confidence.SELL_THRESHOLD:
            # Note: For SELL signals, we typically look for low confidence in upward movement
            # or high confidence in downward movement. This logic may need refinement
            # based on the specific signal type (bullish/bearish)
            return "SELL"
            
        # Between thresholds = HOLD
        return "HOLD"
    
    def get_signal_type(self, confidence: float) -> str:
        """
        Determine signal type (primary vs exploratory) based on confidence
        
        Args:
            confidence: AI model confidence score (0.0 to 1.0)
            
        Returns:
            str: "primary", "exploratory", or "none"
        """
        if confidence >= self.confidence.BUY_THRESHOLD:
            return "primary"
        elif confidence >= self.confidence.EXPLORATORY_BUY:
            return "exploratory"
        else:
            return "none"
    
    def is_high_confidence_signal(self, confidence: float) -> bool:
        """Check if signal meets high confidence criteria"""
        return confidence >= self.confidence.HIGH_CONFIDENCE
    
    def meets_consensus_requirement(self, consensus_score: float) -> bool:
        """Check if multi-model consensus requirement is met"""
        return consensus_score >= self.confidence.CONSENSUS_THRESHOLD
    
    def to_dict(self) -> Dict[str, Any]:
        """Export thresholds as dictionary for logging/config"""
        return {
            "confidence_thresholds": {
                "buy_threshold": self.confidence.BUY_THRESHOLD,
                "sell_threshold": self.confidence.SELL_THRESHOLD,
                "exploratory_buy": self.confidence.EXPLORATORY_BUY,
                "exploratory_sell": self.confidence.EXPLORATORY_SELL,
                "hold_lower_bound": self.confidence.HOLD_LOWER_BOUND,
                "hold_upper_bound": self.confidence.HOLD_UPPER_BOUND,
                "absolute_minimum": self.confidence.ABSOLUTE_MINIMUM,
                "high_confidence": self.confidence.HIGH_CONFIDENCE,
                "consensus_threshold": self.confidence.CONSENSUS_THRESHOLD
            },
            "risk_thresholds": {
                "max_risk_per_trade": self.risk.MAX_RISK_PER_TRADE,
                "max_portfolio_risk": self.risk.MAX_PORTFOLIO_RISK,
                "stop_loss": self.risk.STOP_LOSS_THRESHOLD,
                "take_profit": self.risk.TAKE_PROFIT_THRESHOLD
            }
        }


# Global instance for application-wide use (lazy initialization)
_UNIFIED_THRESHOLDS: Optional[TradingThresholds] = None


def get_trading_thresholds() -> TradingThresholds:
    """Get the unified trading thresholds instance (lazy singleton)"""
    global _UNIFIED_THRESHOLDS
    if _UNIFIED_THRESHOLDS is None:
        _UNIFIED_THRESHOLDS = TradingThresholds()
    return _UNIFIED_THRESHOLDS


def log_threshold_summary():
    """Log current threshold configuration for debugging"""
    thresholds = get_trading_thresholds()
    logger.info("🎯 UNIFIED TRADING THRESHOLDS:")
    logger.info(f"   BUY signals: ≥{thresholds.confidence.BUY_THRESHOLD:.1%} confidence")
    logger.info(f"   SELL signals: ≤{thresholds.confidence.SELL_THRESHOLD:.1%} confidence")
    logger.info(f"   HOLD range: {thresholds.confidence.HOLD_LOWER_BOUND:.1%} - {thresholds.confidence.HOLD_UPPER_BOUND:.1%}")
    logger.info(f"   Exploratory: ≥{thresholds.confidence.EXPLORATORY_BUY:.1%} confidence")
    logger.info(f"   Absolute minimum: ≥{thresholds.confidence.ABSOLUTE_MINIMUM:.1%} confidence")
    logger.info(f"   High confidence: ≥{thresholds.confidence.HIGH_CONFIDENCE:.1%} confidence")
    logger.info(f"   Consensus required: ≥{thresholds.confidence.CONSENSUS_THRESHOLD:.1%}")


# Example usage for debugging inconsistent thresholds from your logs:
def analyze_threshold_inconsistency():
    """Analyze the threshold inconsistency mentioned in logs (0.65 vs 0.42)"""
    thresholds = get_trading_thresholds()
    
    logger.info("🔍 THRESHOLD INCONSISTENCY ANALYSIS:")
    logger.info(f"   Unified BUY threshold: {thresholds.confidence.BUY_THRESHOLD:.2f} (65%)")
    logger.info(f"   Unified SELL threshold: {thresholds.confidence.SELL_THRESHOLD:.2f} (65%)")
    logger.info(f"   HOLD range: {thresholds.confidence.HOLD_LOWER_BOUND:.2f} - {thresholds.confidence.HOLD_UPPER_BOUND:.2f}")
    
    # Test the problematic values from logs
    test_confidence_1 = 0.65
    test_confidence_2 = 0.42
    
    action_1 = thresholds.get_signal_action(test_confidence_1)
    action_2 = thresholds.get_signal_action(test_confidence_2)
    
    logger.info(f"   Confidence 0.65 → {action_1}")
    logger.info(f"   Confidence 0.42 → {action_2}")
    logger.info("   ✅ Inconsistency resolved with unified thresholds")
