"""
Professional Confidence Model Wrapper for TradePulse.AI
Ensures confidence predictions are bounded between 0.0 and 1.0
"""

import numpy as np
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class ProfessionalConfidenceModel:
    """
    Professional wrapper for confidence scoring models
    
    Ensures all predictions are properly bounded between 0.0 and 1.0
    and handles edge cases for production deployment
    """
    
    def __init__(self, model: Any, scaler: Optional[Any] = None):
        """
        Initialize professional confidence model
        
        Args:
            model: The underlying ML model (XGBoost, etc.)
            scaler: Optional feature scaler
        """
        self.model = model
        self.scaler = scaler
        self.prediction_count = 0
        self.out_of_bounds_count = 0
        
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make bounded confidence predictions
        
        Args:
            X: Input features
            
        Returns:
            Bounded confidence scores [0.0, 1.0]
        """
        try:
            # Apply scaling if available
            if self.scaler is not None:
                X_scaled = self.scaler.transform(X)
            else:
                X_scaled = X
            
            # Get raw prediction
            raw_prediction = self.model.predict(X_scaled)
            
            # Handle different prediction formats
            if hasattr(raw_prediction, 'shape') and len(raw_prediction.shape) > 1:
                raw_prediction = raw_prediction.flatten()
            
            # Convert to numpy array if needed
            if not isinstance(raw_prediction, np.ndarray):
                raw_prediction = np.array([raw_prediction])
            
            # Apply professional bounds
            bounded_prediction = self._apply_professional_bounds(raw_prediction)
            
            self.prediction_count += len(bounded_prediction)
            
            return bounded_prediction
            
        except Exception as e:
            logger.error(f"Professional confidence prediction failed: {e}")
            # Return safe default confidence
            return np.array([0.5] * len(X))
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities (for compatibility)
        
        Args:
            X: Input features
            
        Returns:
            Probability array with shape (n_samples, 2)
        """
        confidence = self.predict(X)
        
        # Return as [1-confidence, confidence] for binary classification compatibility
        proba = np.column_stack([1 - confidence, confidence])
        
        return proba
    
    def _apply_professional_bounds(self, predictions: np.ndarray) -> np.ndarray:
        """
        Apply professional bounds to ensure predictions are in [0.0, 1.0]
        
        Args:
            predictions: Raw model predictions
            
        Returns:
            Bounded predictions
        """
        bounded = np.copy(predictions)
        
        # Count out-of-bounds predictions
        out_of_bounds = np.sum((predictions < 0.0) | (predictions > 1.0))
        self.out_of_bounds_count += out_of_bounds
        
        if out_of_bounds > 0:
            logger.debug(f"Bounded {out_of_bounds} out-of-range predictions")
        
        # Apply sigmoid transformation for extreme values
        extreme_mask = (predictions < -2.0) | (predictions > 3.0)
        if np.any(extreme_mask):
            bounded[extreme_mask] = 1.0 / (1.0 + np.exp(-predictions[extreme_mask]))
        
        # Hard bounds for safety
        bounded = np.clip(bounded, 0.0, 1.0)
        
        # Ensure reasonable confidence distribution
        # Avoid extreme confidence (too high or too low)
        bounded = np.clip(bounded, 0.05, 0.95)
        
        return bounded
    
    def get_performance_stats(self) -> dict:
        """Get performance statistics"""
        return {
            'total_predictions': self.prediction_count,
            'out_of_bounds_predictions': self.out_of_bounds_count,
            'out_of_bounds_rate': self.out_of_bounds_count / max(self.prediction_count, 1),
            'model_type': type(self.model).__name__,
            'has_scaler': self.scaler is not None
        }
    
    @property
    def feature_names_in_(self):
        """Expose feature names if available"""
        return getattr(self.model, 'feature_names_in_', None)
    
    @property 
    def n_features_in_(self):
        """Expose number of features if available"""
        return getattr(self.model, 'n_features_in_', None)
