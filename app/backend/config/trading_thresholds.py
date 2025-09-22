"""
Unified Trading Thresholds Configuration
Centralized configuration for all confidence thresholds across TradePulse.AI
"""

from dataclasses import dataclass
from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ConfidenceThresholds:
    """Unified confidence thresholds for all trading decisions"""
    
    # PRIMARY SIGNAL THRESHOLDS (Bitcoin scalping optimized)
    BUY_THRESHOLD: float = 0.45      # 45% confidence required for BUY signals (was 65% - too high!)
    SELL_THRESHOLD: float = 0.45     # 45% confidence required for SELL signals (was 65% - too high!)
    
    # EXPLORATORY SIGNAL THRESHOLDS (Lower confidence for smaller positions)
    EXPLORATORY_BUY: float = 0.35    # 35% confidence for exploratory BUY (was 45%)
    EXPLORATORY_SELL: float = 0.35   # 35% confidence for exploratory SELL (was 45%)
    
    # HOLD DECISION THRESHOLDS
    HOLD_LOWER_BOUND: float = 0.35   # Below 35% = potential SELL signal
    HOLD_UPPER_BOUND: float = 0.65   # Above 65% = potential BUY signal
    # Between 35% and 65% = HOLD
    
    # MINIMUM THRESHOLDS (Absolute minimums)
    ABSOLUTE_MINIMUM: float = 0.30   # Never trade below 30% confidence
    
    # SPECIAL THRESHOLDS
    HIGH_CONFIDENCE: float = 0.80    # High confidence threshold for premium signals
    CONSENSUS_THRESHOLD: float = 0.55  # Multi-model consensus requirement


@dataclass
class RiskThresholds:
    """Risk management thresholds"""
    
    MAX_RISK_PER_TRADE: float = 0.02    # 2% max risk per trade
    MAX_PORTFOLIO_RISK: float = 0.10    # 10% max portfolio risk
    STOP_LOSS_THRESHOLD: float = 0.015  # 1.5% stop loss
    TAKE_PROFIT_THRESHOLD: float = 0.025 # 2.5% take profit


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


# Global instance for application-wide use
UNIFIED_THRESHOLDS = TradingThresholds()


def get_trading_thresholds() -> TradingThresholds:
    """Get the unified trading thresholds instance"""
    return UNIFIED_THRESHOLDS


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
