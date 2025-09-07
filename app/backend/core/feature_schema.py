"""
Unified Feature Schema for TradePulse.AI
=======================================

Single source of truth for all AI model features.
Ensures consistency across Enterprise, Entry, and Exit engines.
"""

import hashlib
import pandas as pd
import numpy as np
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

# SINGLE SOURCE OF TRUTH - All models use these exact features in this order
FEATURE_COLUMNS = [
    "close",
    "volume", 
    "rsi",
    "macd",
    "bb_position",
    "volatility",
    "trend_strength",
    "volume_ratio",
    "price_change_24h"
]

# Schema validation hash for drift detection
SCHEMA_HASH = hashlib.md5(",".join(FEATURE_COLUMNS).encode()).hexdigest()[:8]

def make_X_live(features_dict: Dict[str, Any]) -> pd.DataFrame:
    """
    Create standardized feature DataFrame for all models
    
    Args:
        features_dict: Raw feature dictionary
        
    Returns:
        Standardized DataFrame with proper column names and order
    """
    try:
        # Build row with exact feature order
        row = {col: float(features_dict.get(col, 0.0)) for col in FEATURE_COLUMNS}
        
        # Create DataFrame with proper column names
        df = pd.DataFrame([row], columns=FEATURE_COLUMNS)
        
        return df
        
    except Exception as e:
        logger.error(f"Feature standardization failed: {e}")
        # Return safe fallback
        fallback_row = {col: 0.5 for col in FEATURE_COLUMNS}
        return pd.DataFrame([fallback_row], columns=FEATURE_COLUMNS)

def predict_lgbm_safe(model, features_dict: Dict[str, Any]) -> float:
    """
    Safe LightGBM prediction with proper feature names
    
    Args:
        model: LightGBM model (trained with named features)
        features_dict: Feature dictionary
        
    Returns:
        Prediction value
    """
    try:
        X = make_X_live(features_dict)
        
        # Validate schema if possible
        if hasattr(model, 'feature_name_'):
            model_features = list(model.feature_name_)
            if model_features != FEATURE_COLUMNS:
                logger.warning(f"LightGBM schema mismatch: {model_features[:3]}... vs {FEATURE_COLUMNS[:3]}...")
        
        # LightGBM expects DataFrame with named columns
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(X)[0]
            return float(proba[1]) if len(proba) > 1 else float(proba[0])
        else:
            pred = model.predict(X)[0]
            return float(pred)
            
    except Exception as e:
        logger.warning(f"LightGBM prediction failed: {e}")
        return 0.5

def predict_rf_safe(model, features_dict: Dict[str, Any]) -> float:
    """
    Safe RandomForest prediction (trained without named features)
    
    Args:
        model: RandomForest model (trained without names)
        features_dict: Feature dictionary
        
    Returns:
        Prediction value
    """
    try:
        X = make_X_live(features_dict)
        
        # RandomForest expects numpy array (trained without names)
        X_array = X.values.astype(np.float32)
        
        if hasattr(model, 'predict_proba'):
            proba = model.predict_proba(X_array)[0]
            return float(proba[1]) if len(proba) > 1 else float(proba[0])
        else:
            pred = model.predict(X_array)[0]
            return float(pred)
            
    except Exception as e:
        logger.warning(f"RandomForest prediction failed: {e}")
        return 0.5

def validate_feature_schema(features_dict: Dict[str, Any]) -> bool:
    """
    Validate that all required features are present
    
    Args:
        features_dict: Feature dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        missing_features = [col for col in FEATURE_COLUMNS if col not in features_dict]
        
        if missing_features:
            logger.warning(f"Missing features: {missing_features}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Feature validation failed: {e}")
        return False

def log_schema_info():
    """Log schema information for debugging"""
    logger.info(f"🔍 FEATURE_SCHEMA={SCHEMA_HASH} columns={len(FEATURE_COLUMNS)}")
    logger.debug(f"🔍 Schema columns: {FEATURE_COLUMNS}")