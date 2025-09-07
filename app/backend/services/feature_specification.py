"""
Professional Feature Specification System for TradePulse.AI
Ensures model input consistency and prevents feature mismatches
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

# Import scaler persistence for deterministic preprocessing
from app.backend.services.scaler_persistence import apply_deterministic_scaling, get_scaler_manager

logger = logging.getLogger(__name__)


class FeatureType(Enum):
    """Feature data types"""
    PRICE = "price"
    VOLUME = "volume"
    INDICATOR = "indicator"
    RATIO = "ratio"
    PERCENTAGE = "percentage"


@dataclass(eq=False)
class FeatureSpec:
    """Feature specification with validation rules"""
    name: str
    feature_type: FeatureType
    min_value: float
    max_value: float
    default_value: float
    description: str
    
    def validate(self, value: float) -> float:
        """Validate and clip feature value to acceptable range"""
        if not isinstance(value, (int, float)):
            logger.warning(f"Feature {self.name}: Converting {type(value)} to float")
            try:
                value = float(value)
            except (ValueError, TypeError):
                logger.error(f"Feature {self.name}: Cannot convert {value} to float, using default")
                return self.default_value
        
        # Handle NaN/inf values
        if not np.isfinite(value):
            logger.warning(f"Feature {self.name}: Invalid value {value}, using default")
            return self.default_value
        
        # Clip to valid range
        if value < self.min_value or value > self.max_value:
            clipped = np.clip(value, self.min_value, self.max_value)
            logger.debug(f"Feature {self.name}: Clipped {value} to {clipped}")
            return clipped
        
        return value
    
    def apply_deterministic_scaling(self, value: float) -> float:
        """Apply deterministic scaling using persisted training parameters"""
        try:
            scaled_value = apply_deterministic_scaling(self.name, value)
            return float(scaled_value)
        except Exception as e:
            logger.warning(f"Deterministic scaling failed for {self.name}: {e}, using raw value")
            return value
    
    def __eq__(self, other) -> bool:
        """Shallow equality check to avoid recursion"""
        if not isinstance(other, FeatureSpec):
            return False
        return self.name == other.name and self.feature_type == other.feature_type


class FeatureRegistry:
    """Central registry for all feature specifications"""
    
    def __init__(self):
        self.specs: Dict[str, FeatureSpec] = {}
        self._initialize_standard_features()
    
    def _initialize_standard_features(self):
        """Initialize standard TradePulse.AI features"""
        
        # Price features
        self.register(FeatureSpec(
            name="close",
            feature_type=FeatureType.PRICE,
            min_value=1000.0,    # Minimum reasonable BTC price
            max_value=1000000.0, # Maximum reasonable BTC price
            default_value=50000.0,
            description="Current close price"
        ))
        
        # Volume features
        self.register(FeatureSpec(
            name="volume",
            feature_type=FeatureType.VOLUME,
            min_value=0.0,
            max_value=1000000.0,
            default_value=1000.0,
            description="Trading volume"
        ))
        
        self.register(FeatureSpec(
            name="volume_ratio",
            feature_type=FeatureType.RATIO,
            min_value=0.1,
            max_value=10.0,
            default_value=1.0,
            description="Volume ratio vs average"
        ))
        
        # Technical indicators
        self.register(FeatureSpec(
            name="rsi",
            feature_type=FeatureType.INDICATOR,
            min_value=0.0,
            max_value=100.0,
            default_value=50.0,
            description="Relative Strength Index"
        ))
        
        self.register(FeatureSpec(
            name="macd",
            feature_type=FeatureType.INDICATOR,
            min_value=-10000.0,
            max_value=10000.0,
            default_value=0.0,
            description="MACD indicator"
        ))
        
        self.register(FeatureSpec(
            name="bb_position",
            feature_type=FeatureType.RATIO,
            min_value=0.0,
            max_value=1.0,
            default_value=0.5,
            description="Bollinger Band position"
        ))
        
        # Risk/volatility features
        self.register(FeatureSpec(
            name="volatility",
            feature_type=FeatureType.PERCENTAGE,
            min_value=0.001,
            max_value=0.5,
            default_value=0.02,
            description="Price volatility"
        ))
        
        self.register(FeatureSpec(
            name="trend_strength",
            feature_type=FeatureType.RATIO,
            min_value=0.0,
            max_value=1.0,
            default_value=0.5,
            description="Trend strength indicator"
        ))
        
        # CRITICAL FIX: Price change percentage (was causing 1238.75 error)
        self.register(FeatureSpec(
            name="price_change_24h",
            feature_type=FeatureType.PERCENTAGE,
            min_value=-50.0,     # Maximum 50% daily drop
            max_value=50.0,      # Maximum 50% daily gain
            default_value=0.0,
            description="24-hour price change percentage"
        ))
        
        logger.info(f"✅ Initialized {len(self.specs)} feature specifications")
    
    def register(self, spec: FeatureSpec):
        """Register a feature specification"""
        self.specs[spec.name] = spec
        logger.debug(f"Registered feature: {spec.name}")
    
    def get_spec(self, name: str) -> Optional[FeatureSpec]:
        """Get feature specification by name"""
        return self.specs.get(name)
    
    def validate_features(self, features: Dict[str, Any]) -> Dict[str, float]:
        """Validate and normalize all features with deterministic scaling"""
        validated = {}
        
        for name, value in features.items():
            spec = self.get_spec(name)
            if spec:
                # First validate the raw value
                validated_value = spec.validate(value)
                # Then apply deterministic scaling using persisted parameters
                scaled_value = spec.apply_deterministic_scaling(validated_value)
                validated[name] = scaled_value
            else:
                # Unknown feature - use as-is but log warning
                logger.warning(f"Unknown feature: {name} = {value}")
                try:
                    validated[name] = float(value)
                except (ValueError, TypeError):
                    logger.error(f"Cannot convert unknown feature {name} = {value} to float")
                    validated[name] = 0.0
        
        return validated
    
    def get_feature_order(self, model_name: str = "default") -> List[str]:
        """Get standard feature order for models"""
        # Standard order for TradePulse.AI models
        return [
            "close", "volume", "rsi", "macd", 
            "bb_position", "volatility", "trend_strength", "volume_ratio"
        ]
    
    def prepare_model_input(self, features: Dict[str, Any], 
                          required_features: List[str] = None,
                          model_name: str = "default") -> np.ndarray:
        """Prepare validated model input array"""
        
        # Validate all features first
        validated_features = self.validate_features(features)
        
        # Use provided feature order or default
        if required_features is None:
            required_features = self.get_feature_order(model_name)
        
        # Build feature array in correct order
        feature_values = []
        for feature_name in required_features:
            if feature_name in validated_features:
                feature_values.append(validated_features[feature_name])
            else:
                # Missing feature - use default from spec
                spec = self.get_spec(feature_name)
                default_value = spec.default_value if spec else 0.0
                feature_values.append(default_value)
                logger.warning(f"Missing feature {feature_name}, using default: {default_value}")
        
        # Convert to numpy array
        feature_array = np.array(feature_values, dtype=np.float32).reshape(1, -1)
        
        logger.debug(f"Prepared model input: {len(feature_values)} features, shape: {feature_array.shape}")
        
        return feature_array


# Global feature registry instance
_feature_registry: Optional[FeatureRegistry] = None

def get_feature_registry() -> FeatureRegistry:
    """Get global feature registry instance"""
    global _feature_registry
    if _feature_registry is None:
        _feature_registry = FeatureRegistry()
    return _feature_registry


def validate_and_prepare_features(features: Dict[str, Any], 
                                model_name: str = "default",
                                required_features: List[str] = None) -> np.ndarray:
    """Convenience function for feature validation and preparation"""
    registry = get_feature_registry()
    return registry.prepare_model_input(features, required_features, model_name)


def fix_price_change_calculation(features: Dict[str, Any]) -> Dict[str, Any]:
    """Fix price_change_24h calculation to be percentage-based"""
    
    if "price_change_24h" in features:
        price_change = features["price_change_24h"]
        current_price = features.get("close", 50000.0)
        
        # If price_change looks like absolute value (> 100), convert to percentage
        if abs(price_change) > 100:
            # Assume it's absolute change, convert to percentage
            percentage_change = (price_change / current_price) * 100
            features["price_change_24h"] = percentage_change
            logger.info(f"Fixed price_change_24h: {price_change} → {percentage_change:.2f}%")
    
    return features
