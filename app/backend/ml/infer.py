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

# CRITICAL: RandomForest L5 model was trained on exactly these 6 features
# DO NOT CHANGE without retraining the model
L5_RF_MODEL_FEATURES: List[str] = [
    "close", 
    "volume", 
    "rsi", 
    "macd", 
    "volatility", 
    "trend_strength"
]

# Default values for missing features (based on typical market conditions)
FEATURE_DEFAULTS = {
    "close": 1.0,
    "volume": 0.0,
    "rsi": 50.0,
    "macd": 0.0,
    "bb_position": 0.5,
    "volatility": 0.02,
    "trend_strength": 0.0,
    "volume_ratio": 1.0,
    "price_change_24h": 0.0
}

def build_l5_rf_vector(features: Dict[str, float]) -> np.ndarray:
    """
    Build feature vector specifically for L5 RandomForest model.
    
    CRITICAL: This model was trained on exactly 6 features in this order.
    Feeding it more or fewer features will cause prediction errors.
    
    Args:
        features: Dictionary with all available features (can have 9+ features)
        
    Returns:
        numpy array with shape (1, 6) containing exactly the features
        the L5 RandomForest model expects
    """
    try:
        # Extract only the 6 features the model was trained on
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
            logger.warning(f"L5 RF missing features: {missing_features} -> using defaults")
        
        # Return as numpy array with correct shape
        arr = np.array([vector], dtype=np.float32)  # shape: (1, 6)
        
        logger.debug(f"L5 RF vector built: shape={arr.shape}, features={L5_RF_MODEL_FEATURES}")
        return arr
        
    except Exception as e:
        logger.error(f"Failed to build L5 RF vector: {e}")
        # Return safe fallback with neutral values
        fallback = np.array([[1.0, 0.0, 50.0, 0.0, 0.02, 0.0]], dtype=np.float32)
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
    Safe prediction for L5 RandomForest model with proper feature vector.
    
    Args:
        model: Trained L5 RandomForest model (expects 6 features)
        features: Feature dictionary (can contain 9+ features)
        
    Returns:
        Confidence prediction as float
    """
    try:
        # Build the exact 6-feature vector the model expects
        X = build_l5_rf_vector(features)
        
        # Predict using numpy array (no feature names to avoid warnings)
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(X)[0]
            return float(proba[1]) if len(proba) > 1 else float(proba[0])
        else:
            pred = model.predict(X)[0]
            return float(pred)
            
    except Exception as e:
        logger.warning(f"L5 RF prediction failed: {e}")
        return 0.5  # Neutral confidence


# SSOT: build vector from MarketSnapshot (v2.0 - Enhanced with 15 features)
def build_l5_vector_from_snapshot(snapshot: Any) -> np.ndarray:
    """
    Build L5 vector (1x15) from MarketSnapshot - Enhanced v2.0
    
    Features (15 total):
    - 9 Core: close, volume, rsi, macd, bb_position, volatility, trend_strength, volume_ratio, price_change_24h
    - 6 Session: session_asian, session_european, session_us, session_overlap, hour_of_day, volatility_regime
    
    Args:
        snapshot: MarketSnapshot object with price, volume, indicators
        
    Returns:
        numpy array (1, 15) with normalized features for prediction
    """
    try:
        # Normalize snapshot to object with attributes
        obj = snapshot
        
        # Extract core fields
        price = getattr(obj, "price", None)
        volume = getattr(obj, "volume", None)
        inds = getattr(obj, "indicators", None)
        
        # Core features - FIXED: read from Indicators dataclass (v2.0 with 7 fields)
        rsi = getattr(inds, "rsi", None) if inds is not None else None
        macd = getattr(inds, "macd", None) if inds is not None else None
        bb_position = getattr(inds, "bb_pos", None) if inds is not None else None  # FIXED: bb_pos is the field name
        volatility = getattr(inds, "volatility", None) if inds is not None else None
        trend_strength = getattr(inds, "trend_strength", None) if inds is not None else None
        volume_ratio = getattr(inds, "volume_ratio", None) if inds is not None else None  # NEW in v2.0
        price_change_24h = getattr(inds, "price_change_24h", None) if inds is not None else None  # NEW in v2.0
        
        # DEBUG: Log indicators object to diagnose missing fields
        if inds is not None:
            ind_fields = [f for f in dir(inds) if not f.startswith('_')]
            logger.debug(f"🔍 DEBUG Indicators fields: {ind_fields}")
            logger.debug(f"🔍 DEBUG volume_ratio={volume_ratio}, price_change_24h={price_change_24h}")
        
        # Session context (new in v2.0)
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        hour_utc = now.hour
        
        # Session definitions (UTC hours)
        session_asian = 1 if 0 <= hour_utc < 8 else 0
        session_european = 1 if 7 <= hour_utc < 15 else 0
        session_us = 1 if 13 <= hour_utc < 21 else 0
        session_overlap = 1 if (session_asian + session_european + session_us) > 1 else 0
        hour_of_day = hour_utc
        
        # Volatility regime (0=low, 1=normal, 2=high)
        vol_val = volatility if volatility is not None else 0.02
        volatility_regime = 1  # Default: normal
        if vol_val < 0.001:
            volatility_regime = 0  # Low
        elif vol_val > 0.005:
            volatility_regime = 2  # High

        # Prevalidation for clearer errors
        missing = []
        if price is None: missing.append("price")
        if volume is None: missing.append("volume")
        if rsi is None: missing.append("rsi")
        if macd is None: missing.append("macd")
        if bb_position is None: missing.append("bb_position")
        if volatility is None: missing.append("volatility")
        if trend_strength is None: missing.append("trend_strength")
        if volume_ratio is None: missing.append("volume_ratio")
        if price_change_24h is None: missing.append("price_change_24h")
        if missing:
            logger.warning(f"MissingFeatures: {','.join(missing)} - using defaults")
            # Use defaults instead of failing
            price = price or 100000.0
            volume = volume or 1000000.0
            rsi = rsi or 50.0
            macd = macd or 0.0
            bb_position = bb_position or 0.5
            volatility = volatility or 0.02
            trend_strength = trend_strength or 0.0
            volume_ratio = volume_ratio or 1.0
            price_change_24h = price_change_24h or 0.0

        # Build 15-feature vector (order matters!)
        vec = np.array([[
            float(price),
            float(volume),
            float(rsi),
            float(macd),
            float(bb_position),
            float(volatility),
            float(trend_strength),
            float(volume_ratio),
            float(price_change_24h),
            float(session_asian),
            float(session_european),
            float(session_us),
            float(session_overlap),
            float(hour_of_day),
            float(volatility_regime)
        ]], dtype=np.float32)
        
        return vec
        
    except Exception as e:
        logger.warning(f"Failed to build L5 vector from snapshot: {e}")
        # Return defaults for all 15 features
        return np.array([[100000.0, 1000000.0, 50.0, 0.0, 0.5, 0.02, 0.0, 1.0, 0.0, 0, 0, 0, 0, 12, 1]], dtype=np.float32)

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
