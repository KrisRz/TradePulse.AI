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


# SSOT: build vector from MarketSnapshot
def build_l5_vector_from_snapshot(snapshot: Any) -> np.ndarray:
    """Build L5 RF vector (1x6) from MarketSnapshot with prevalidation and stable names.

    Expected mapping (SSOT):
    - price → close
    - volume → volume
    - indicators.rsi → rsi
    - indicators.macd → macd
    - indicators.volatility → volatility
    - indicators.trend_strength → trend_strength
    """
    try:
        # Normalize snapshot to object with attributes
        obj = snapshot
        # Extract fields deterministically (no eval)
        price = getattr(obj, "price", None)
        volume = getattr(obj, "volume", None)
        inds = getattr(obj, "indicators", None)
        rsi = getattr(inds, "rsi", None) if inds is not None else None
        macd = getattr(inds, "macd", None) if inds is not None else None
        volatility = getattr(inds, "volatility", None) if inds is not None else None
        trend_strength = getattr(inds, "trend_strength", None) if inds is not None else None

        # Prevalidation for clearer errors than NameError
        missing = []
        if price is None: missing.append("price")
        if volume is None: missing.append("volume")
        if rsi is None: missing.append("rsi")
        if macd is None: missing.append("macd")
        if volatility is None: missing.append("volatility")
        if trend_strength is None: missing.append("trend_strength")
        if missing:
            raise ValueError(f"MissingFeatures:{','.join(missing)}")

        vec = np.array([[float(price), float(volume), float(rsi), float(macd), float(volatility), float(trend_strength)]], dtype=np.float32)
        return vec
    except Exception as e:
        logger.warning(f"Failed to build L5 vector from snapshot: {e}")
        return np.array([[1.0, 0.0, 50.0, 0.0, 0.02, 0.0]], dtype=np.float32)

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
