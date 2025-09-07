"""
Signal Quality Validator for TradePulse.AI
Professional signal validation with industry standards
"""

from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class SignalQualityValidator:
    """
    Professional signal quality validator
    
    Validates signals against industry-standard criteria:
    - Confidence thresholds (60%+ for primary, 45%+ for exploratory)
    - Risk management requirements
    - Technical filter validation
    - Market timing requirements
    - R/R ratio validation
    """
    
    def __init__(self):
        # CONSERVATIVE SCALPING: Lower thresholds for frequent trades
        self.primary_confidence_threshold = 0.45      # SCALPING: 45% (was 60%)
        self.exploratory_confidence_threshold = 0.35  # SCALPING: 35% (was 45%)
        self.absolute_minimum_confidence = 0.40       # SCALPING: 40% (was 50%)
        
        self.max_risk_threshold = 0.80  # SCALPING: Higher tolerance for reversal opportunities
        self.min_risk_reward_ratio = 1.6  # SCALPING: Lower R/R for frequent trades (was 2.0)
        self.max_position_size = 0.20     # SCALPING: 20% max (8 positions × 2.5%)
        
        self.primary_filter_threshold = 0.15    # SCALPING: Lower filter (was 0.40)
        self.exploratory_filter_threshold = 0.08  # SCALPING: Lower filter (was 0.25)
        
        self.primary_timing_threshold = 0.015     # SCALPING: More sensitive (was 0.05)
        self.exploratory_timing_threshold = 0.008  # SCALPING: More sensitive (was 0.02)
        
        # Quality tracking
        self.signals_validated = 0
        self.signals_passed = 0
        self.rejection_reasons = {}
    
    def validate_signal(self, signal: Dict[str, Any], signal_type: str = "primary") -> Dict[str, Any]:
        """
        Validate signal quality against professional standards
        
        Args:
            signal: Trading signal to validate
            signal_type: "primary" or "exploratory"
            
        Returns:
            Validation result with pass/fail and detailed reasons
        """
        self.signals_validated += 1
        
        validation_result = {
            "is_valid": True,
            "signal_type": signal_type,
            "validation_timestamp": datetime.now(timezone.utc).isoformat(),
            "checks_passed": [],
            "checks_failed": [],
            "quality_score": 0.0,
            "rejection_reason": None
        }
        
        try:
            # Extract signal components
            confidence = signal.get("confidence", 0.0)
            action = signal.get("action", "HOLD")
            layer_analysis = signal.get("layer_analysis", {})
            
            # Skip validation for HOLD signals
            if action == "HOLD":
                validation_result["is_valid"] = True
                validation_result["quality_score"] = 0.5
                validation_result["checks_passed"].append("HOLD signal - no validation required")
                return validation_result
            
            # Check 1: Confidence threshold
            confidence_threshold = (
                self.primary_confidence_threshold if signal_type == "primary" 
                else self.exploratory_confidence_threshold
            )
            
            if confidence >= confidence_threshold:
                validation_result["checks_passed"].append(f"Confidence {confidence:.1%} >= {confidence_threshold:.1%}")
                validation_result["quality_score"] += 0.3
            else:
                validation_result["checks_failed"].append(f"Confidence {confidence:.1%} < {confidence_threshold:.1%}")
                validation_result["is_valid"] = False
                validation_result["rejection_reason"] = "insufficient_confidence"
            
            # Check 2: Absolute minimum confidence
            if confidence >= self.absolute_minimum_confidence:
                validation_result["checks_passed"].append(f"Above absolute minimum {self.absolute_minimum_confidence:.1%}")
                validation_result["quality_score"] += 0.1
            else:
                validation_result["checks_failed"].append(f"Below absolute minimum {self.absolute_minimum_confidence:.1%}")
                validation_result["is_valid"] = False
                validation_result["rejection_reason"] = "below_absolute_minimum"
            
            # Check 3: Risk assessment
            risk_data = layer_analysis.get("layer_3_reversal", {})
            reversal_prob = risk_data.get("reversal_probability", 0.5)
            
            if reversal_prob <= self.max_risk_threshold:
                validation_result["checks_passed"].append(f"Risk {reversal_prob:.1%} <= {self.max_risk_threshold:.1%}")
                validation_result["quality_score"] += 0.2
            else:
                validation_result["checks_failed"].append(f"Risk {reversal_prob:.1%} > {self.max_risk_threshold:.1%}")
                validation_result["is_valid"] = False
                validation_result["rejection_reason"] = "excessive_risk"
            
            # Check 4: Technical filters
            filter_data = layer_analysis.get("layer_4_filters", {})
            filter_score = filter_data.get("filter_score", 0.0)
            
            filter_threshold = (
                self.primary_filter_threshold if signal_type == "primary"
                else self.exploratory_filter_threshold
            )
            
            if filter_score >= filter_threshold:
                validation_result["checks_passed"].append(f"Filter {filter_score:.1%} >= {filter_threshold:.1%}")
                validation_result["quality_score"] += 0.2
            else:
                validation_result["checks_failed"].append(f"Filter {filter_score:.1%} < {filter_threshold:.1%}")
                validation_result["is_valid"] = False
                validation_result["rejection_reason"] = "insufficient_filter_score"
            
            # Check 5: Market timing
            timing_data = layer_analysis.get("layer_6_timing", {})
            timing_score = timing_data.get("timing_score", 0.0)
            
            timing_threshold = (
                self.primary_timing_threshold if signal_type == "primary"
                else self.exploratory_timing_threshold
            )
            
            # Check timing based on action
            timing_valid = False
            if action == "BUY" and timing_score >= timing_threshold:
                timing_valid = True
            elif action == "SELL" and timing_score <= -timing_threshold:
                timing_valid = True
            
            if timing_valid:
                validation_result["checks_passed"].append(f"Timing {timing_score:.3f} meets {action} threshold")
                validation_result["quality_score"] += 0.2
            else:
                validation_result["checks_failed"].append(f"Timing {timing_score:.3f} insufficient for {action}")
                validation_result["is_valid"] = False
                validation_result["rejection_reason"] = "insufficient_timing"
            
            # Update statistics
            if validation_result["is_valid"]:
                self.signals_passed += 1
            else:
                reason = validation_result["rejection_reason"]
                self.rejection_reasons[reason] = self.rejection_reasons.get(reason, 0) + 1
            
            # Log validation result
            status = "PASSED" if validation_result["is_valid"] else "REJECTED"
            logger.info(f"Signal validation {status}: {signal_type} {action} "
                       f"conf={confidence:.1%} quality={validation_result['quality_score']:.2f}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Signal validation error: {e}")
            validation_result["is_valid"] = False
            validation_result["rejection_reason"] = "validation_error"
            validation_result["checks_failed"].append(f"Validation error: {e}")
            return validation_result
    
    def get_quality_statistics(self) -> Dict[str, Any]:
        """Get signal quality statistics"""
        pass_rate = (
            self.signals_passed / self.signals_validated 
            if self.signals_validated > 0 else 0.0
        )
        
        return {
            "signals_validated": self.signals_validated,
            "signals_passed": self.signals_passed,
            "pass_rate": pass_rate,
            "rejection_reasons": self.rejection_reasons.copy(),
            "quality_thresholds": {
                "primary_confidence": self.primary_confidence_threshold,
                "exploratory_confidence": self.exploratory_confidence_threshold,
                "absolute_minimum": self.absolute_minimum_confidence,
                "max_risk": self.max_risk_threshold,
                "min_rr_ratio": self.min_risk_reward_ratio
            }
        }


# Global validator instance
_signal_quality_validator = None

def get_signal_quality_validator() -> SignalQualityValidator:
    """Get global signal quality validator instance"""
    global _signal_quality_validator
    
    if _signal_quality_validator is None:
        _signal_quality_validator = SignalQualityValidator()
    
    return _signal_quality_validator
