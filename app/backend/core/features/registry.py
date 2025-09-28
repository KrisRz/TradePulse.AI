"""
Feature Registry for LightGBM Models
Fixed feature order for production models
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Global feature spec - initialized once
_FEATURES: List[str] = None

def get_feature_spec() -> List[str]:
    """Get exact feature order used to train the LightGBM reversal model"""
    global _FEATURES
    if _FEATURES is None:
        # EXACT order used to train the LightGBM reversal model (8 features)
        _FEATURES = [
            "volume",
            "volume_ratio", 
            "rsi",
            "macd",
            "bb_position",
            "volatility",
            "trend_strength",
            "price_change_24h",
        ]
        logger.info("✅ Initialized %d feature specifications", len(_FEATURES))
    return _FEATURES

def make_feature_vector(features: Dict[str, float]) -> List[float]:
    """Make feature vector in exact model order"""
    spec = get_feature_spec()
    return [float(features.get(k, 0.0)) for k in spec]

def validate_feature_count(features: Dict[str, Any], expected_count: int = 8) -> bool:
    """Validate that we have the expected number of features"""
    spec = get_feature_spec()
    available_count = len([k for k in spec if k in features])
    if available_count != expected_count:
        logger.warning(f"Feature count mismatch: {available_count}/{expected_count} available")
        return False
    return True
