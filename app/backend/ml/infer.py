"""
Model Inference Utilities for TradePulse.AI
==========================================

Handles proper feature vector construction for different model types,
ensuring compatibility between training and inference time.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# CRITICAL: XGBRegressor L5 model was trained on exactly these 19 features
# RETRAINED: 2025-10-22 with micro-PnL calibration
L5_RF_MODEL_FEATURES: List[str] = [
    # Base features (9)
    "close", 
    "volume", 
    "rsi", 
    "macd", 
    "bb_position",
    "volatility", 
    "trend_strength",
    "volume_ratio",
    "price_change_24h",
    # NEW features (10) - added to fix inverse correlation
    "hour_of_day",
    "day_of_week",
    "volume_spike",
    "price_momentum_5m",
    "price_momentum_15m",
    "distance_from_support",
    "distance_from_resistance",
    "atr_normalized",
    "stoch_oversold",
    "stoch_overbought"
]

# Default values for missing features (based on typical market conditions)
FEATURE_DEFAULTS = {
    # Base features
    "close": 1.0,
    "volume": 0.0,
    "rsi": 50.0,
    "macd": 0.0,
    "bb_position": 0.5,
    "volatility": 0.02,
    "trend_strength": 0.0,
    "volume_ratio": 1.0,
    "price_change_24h": 0.0,
    # NEW features
    "hour_of_day": 0.5,  # Noon UTC default
    "day_of_week": 0.5,  # Mid-week default
    "volume_spike": 1.0,  # Normal volume
    "price_momentum_5m": 0.0,  # No momentum
    "price_momentum_15m": 0.0,
    "distance_from_support": 0.02,  # 2% from support
    "distance_from_resistance": 0.02,  # 2% from resistance
    "atr_normalized": 0.01,  # 1% ATR
    "stoch_oversold": 0.0,  # Not oversold
    "stoch_overbought": 0.0  # Not overbought
}

def build_l5_rf_vector(features: Dict[str, float]) -> np.ndarray:
    """
    Build feature vector specifically for L5 XGBRegressor model.
    
    CRITICAL: This model was RETRAINED 2025-10-22 on exactly 19 features.
    Feeding it more or fewer features will cause prediction errors.
    
    Args:
        features: Dictionary with all available features
        
    Returns:
        numpy array with shape (1, 19) containing exactly the features
        the L5 XGBRegressor model expects
    """
    try:
        # Extract all 19 features the model was trained on
        vector = []
        missing_features = []
        
        for feature_name in L5_RF_MODEL_FEATURES:
            if feature_name in features:
                vector.append(float(features[feature_name]))
            else:
                default_val = FEATURE_DEFAULTS.get(feature_name, 0.0)
                vector.append(default_val)
                missing_features.append(feature_name)
        
        # Log missing features for debugging
        if missing_features:
            logger.warning(f"L5 XGB missing features: {missing_features} -> using defaults")
        
        # Return as numpy array with correct shape
        arr = np.array([vector], dtype=np.float32)  # shape: (1, 19)
        
        logger.debug(f"L5 XGB vector built: shape={arr.shape}, 19 features")
        return arr
        
    except Exception as e:
        logger.error(f"Failed to build L5 XGB vector: {e}")
        # Return safe 19-feature fallback with neutral values
        fallback = np.array([[
            1.0, 0.0, 50.0, 0.0, 0.5, 0.02, 0.0, 1.0, 0.0,  # 9 base features
            0.5, 0.5, 1.0, 0.0, 0.0, 0.02, 0.02, 0.01, 0.0, 0.0  # 10 new features
        ]], dtype=np.float32)
        return fallback

def build_model_vector(features: Dict[str, float], model_features: List[str]) -> np.ndarray:
    """
    Generic function to build feature vector for any model.
    
    Args:
        features: Dictionary with all available features
        model_features: List of features expected by the model in correct order
        
    Returns:
        numpy array with shape (1, len(model_features))
    """
    try:
        vector = []
        missing_features = []
        
        for feature_name in model_features:
            if feature_name in features:
                vector.append(float(features[feature_name]))
            else:
                default_val = FEATURE_DEFAULTS.get(feature_name, 0.0)
                vector.append(default_val)
                missing_features.append(feature_name)
        
        if missing_features:
            logger.warning(f"Model missing features: {missing_features} -> using defaults")
        
        arr = np.array([vector], dtype=np.float32)
        return arr
        
    except Exception as e:
        logger.error(f"Failed to build model vector: {e}")
        # Return safe fallback
        fallback = [FEATURE_DEFAULTS.get(name, 0.0) for name in model_features]
        return np.array([fallback], dtype=np.float32)

def predict_l5_rf_safe(model: Any, features: Dict[str, float]) -> float:
    """
    Safe prediction for L5 XGBRegressor model with proper feature vector.
    
    Args:
        model: Trained L5 XGBRegressor model (expects 19 features)
        features: Feature dictionary (can contain many features)
        
    Returns:
        Confidence prediction as float
    """
    try:
        # Build the exact 19-feature vector the model expects
        X = build_l5_rf_vector(features)
        
        # Predict using numpy array (XGBoost regressor returns single value)
        pred = model.predict(X)[0]
        return float(np.clip(pred, 0.0, 1.0))
            
    except Exception as e:
        logger.warning(f"L5 XGB prediction failed: {e}")
        return 0.5  # Neutral confidence


# SSOT: build vector from MarketSnapshot
def build_l5_vector_from_snapshot(snapshot: Any) -> np.ndarray:
    """Build L5 XGBRegressor vector (1x19) from MarketSnapshot with all 19 features.
    
    RETRAINED 2025-10-22: Now expects 19 features to fix inverse correlation.
    """
    try:
        from datetime import datetime
        
        # Extract base features
        obj = snapshot
        price = getattr(obj, "price", None) or 1.0
        volume = getattr(obj, "volume", None) or 0.0
        inds = getattr(obj, "indicators", None)
        
        # Base indicators (9)
        rsi = getattr(inds, "rsi", None) if inds else None
        macd = getattr(inds, "macd", None) if inds else None
        bb_upper = getattr(inds, "bb_upper", None) if inds else None
        bb_lower = getattr(inds, "bb_lower", None) if inds else None
        volatility = getattr(inds, "volatility", None) if inds else None
        trend_strength = getattr(inds, "trend_strength", None) if inds else None
        volume_ratio = getattr(inds, "volume_ratio", None) if inds else None
        price_change_24h = getattr(inds, "price_change_24h", None) if inds else None
        
        # Calculate bb_position
        if bb_upper and bb_lower and bb_upper != bb_lower:
            bb_position = (price - bb_lower) / (bb_upper - bb_lower)
        else:
            bb_position = 0.5
        
        # NEW features (10) - calculate from available data
        now = datetime.now()
        hour_of_day = now.hour / 24.0
        day_of_week = now.weekday() / 7.0
        
        # Volume spike (defaults to 1.0 = normal)
        volume_spike = volume_ratio if volume_ratio else 1.0
        
        # Price momentum (would need historical data - use fallback)
        price_momentum_5m = 0.0
        price_momentum_15m = 0.0
        
        # Support/Resistance distances (would need S/R calc - use fallback)
        distance_from_support = 0.02
        distance_from_resistance = 0.02
        
        # ATR normalized (from volatility)
        atr_normalized = volatility if volatility else 0.01
        
        # Stochastic (from RSI as proxy)
        stoch_oversold = 1.0 if (rsi and rsi < 20) else 0.0
        stoch_overbought = 1.0 if (rsi and rsi > 80) else 0.0
        
        # Build 19-feature vector
        vec = np.array([[
            float(price),
            float(volume),
            float(rsi if rsi else 50.0),
            float(macd if macd else 0.0),
            float(bb_position),
            float(volatility if volatility else 0.02),
            float(trend_strength if trend_strength else 0.0),
            float(volume_ratio if volume_ratio else 1.0),
            float(price_change_24h if price_change_24h else 0.0),
            float(hour_of_day),
            float(day_of_week),
            float(volume_spike),
            float(price_momentum_5m),
            float(price_momentum_15m),
            float(distance_from_support),
            float(distance_from_resistance),
            float(atr_normalized),
            float(stoch_oversold),
            float(stoch_overbought)
        ]], dtype=np.float32)
        
        logger.debug(f"✅ L5 vector built: shape={vec.shape} (19 features)")
        return vec
        
    except Exception as e:
        logger.warning(f"Failed to build L5 vector from snapshot: {e}")
        # Return 19-feature fallback with defaults
        fallback = np.array([[
            1.0, 0.0, 50.0, 0.0, 0.5,  # close, volume, rsi, macd, bb_position
            0.02, 0.0, 1.0, 0.0,  # volatility, trend, volume_ratio, price_change
            0.5, 0.5, 1.0, 0.0, 0.0,  # hour, day, spike, momentum_5m, momentum_15m
            0.02, 0.02, 0.01, 0.0, 0.0  # support, resistance, atr, oversold, overbought
        ]], dtype=np.float32)
        return fallback

def save_model_with_metadata(model: Any, features: List[str], model_path: str, 
                           model_type: str = "unknown", version: str = "v1") -> None:
    """
    Save model with metadata including feature list for runtime compatibility.
    
    Args:
        model: Trained model
        features: List of features the model was trained on
        model_path: Path to save the model bundle
        model_type: Type of model (e.g., "RandomForest", "LightGBM")
        version: Model version
    """
    try:
        import joblib
        
        bundle = {
            "model": model,
            "features": features,
            "model_type": model_type,
            "version": version,
            "feature_count": len(features)
        }
        
        joblib.dump(bundle, model_path)
        logger.info(f"Saved {model_type} model with {len(features)} features to {model_path}")
        
    except Exception as e:
        logger.error(f"Failed to save model bundle: {e}")

def load_model_with_metadata(model_path: str) -> Dict[str, Any]:
    """
    Load model bundle with metadata.
    
    Args:
        model_path: Path to model bundle
        
    Returns:
        Dictionary with model, features, and metadata
    """
    try:
        import joblib
        
        bundle = joblib.load(model_path)
        
        # Validate bundle structure
        if not isinstance(bundle, dict) or "model" not in bundle:
            logger.warning(f"Legacy model format detected: {model_path}")
            return {"model": bundle, "features": None, "model_type": "unknown"}
        
        logger.info(f"Loaded {bundle.get('model_type', 'unknown')} model with "
                   f"{len(bundle.get('features', []))} features")
        
        return bundle
        
    except Exception as e:
        logger.error(f"Failed to load model bundle: {e}")
        return {"model": None, "features": None, "model_type": "unknown"}
