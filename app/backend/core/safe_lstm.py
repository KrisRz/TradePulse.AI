"""
Safe LSTM Wrapper
Prevents recursion crashes with re-entrancy guards
"""

import threading
import numpy as np
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class SafeLSTM:
    """Thread-safe LSTM wrapper with re-entrancy protection"""
    
    def __init__(self, keras_model: Any):
        self.model = keras_model
        self._lock = threading.Lock()
        self._in_call = False  # Re-entrancy flag
        self.model_name = getattr(keras_model, 'name', 'unknown_lstm')
    
    def predict(self, X: np.ndarray, **kwargs) -> np.ndarray:
        """
        Safe prediction with re-entrancy guard
        
        Args:
            X: Input features array
            **kwargs: Additional arguments for model.predict()
            
        Returns:
            Model predictions
            
        Raises:
            RuntimeError: If called re-entrantly to prevent recursion
        """
        # Non-blocking guard prevents nested predict() loops
        if self._in_call or not self._lock.acquire(blocking=False):
            error_msg = f"LSTM {self.model_name} predict re-entrant; skipping to avoid recursion"
            logger.warning(f"⚠️ {error_msg}")
            raise RuntimeError(error_msg)
        
        try:
            self._in_call = True
            logger.debug(f"🔍 LSTM {self.model_name} predicting on shape {X.shape}")
            
            # Call actual model with verbose=0 to reduce noise
            result = self.model.predict(X, verbose=0, **kwargs)
            
            logger.debug(f"✅ LSTM {self.model_name} prediction completed")
            return result
            
        except Exception as e:
            logger.error(f"❌ LSTM {self.model_name} prediction failed: {e}")
            raise
        finally:
            self._in_call = False
            self._lock.release()
    
    def predict_safe(self, X: np.ndarray, fallback_value: float = 0.5) -> float:
        """
        Safe prediction with fallback for critical paths
        
        Args:
            X: Input features
            fallback_value: Value to return if prediction fails
            
        Returns:
            Prediction result or fallback value
        """
        try:
            result = self.predict(X)
            if isinstance(result, np.ndarray) and len(result) > 0:
                return float(result[0])
            return float(result)
        except (RuntimeError, Exception) as e:
            logger.warning(f"⚠️ LSTM {self.model_name} failed, using fallback {fallback_value}: {e}")
            return fallback_value
    
    def __getattr__(self, name: str):
        """Delegate other attributes to the wrapped model"""
        return getattr(self.model, name)
