"""
TradePulse.AI Model Loader Service
=================================

Professional model loading service for enterprise trading system.
Loads and manages AI models using real data only.

Author: TradePulse.AI Development Team
Version: 1.0.0 (Production)
"""

import asyncio
import logging
import pickle
import joblib
from pathlib import Path
from typing import Dict, Any, Optional
import tensorflow as tf

from app.backend.core.config import get_settings
from app.backend.core.lazy import LazyProxy

logger = logging.getLogger(__name__)
settings = get_settings()

class ModelLoader:
    """
    Professional model loader for TradePulse.AI
    Loads AI/ML models for trading system
    """
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.model_path = Path(__file__).parent.parent / "models"
        logger.info("🔧 ModelLoader initialized")
    
    async def load_model(self, model_name: str, model_type: str = "pickle") -> Optional[Any]:
        """Load a specific model"""
        try:
            if model_name in self.models:
                return self.models[model_name]
            
            model_file = self.model_path / f"{model_name}.pkl"
            
            if not model_file.exists():
                logger.warning(f"Model file not found: {model_file}")
                return None
            
            if model_type == "pickle":
                with open(model_file, 'rb') as f:
                    model = pickle.load(f)
            elif model_type == "joblib":
                model = joblib.load(model_file)
            elif model_type == "tensorflow":
                model = tf.keras.models.load_model(str(model_file))
            else:
                logger.error(f"Unsupported model type: {model_type}")
                return None
            
            self.models[model_name] = model
            logger.info(f"✅ Loaded model: {model_name}")
            return model
            
        except Exception as e:
            logger.error(f"❌ Error loading model {model_name}: {e}")
            return None
    
    def get_model(self, model_name: str) -> Optional[Any]:
        """Get a loaded model"""
        return self.models.get(model_name)
    
    def list_models(self) -> list:
        """List all loaded models"""
        return list(self.models.keys())

# Global instance
_model_loader = None

def get_model_loader():
    """Get global model loader instance"""
    global _model_loader
    if _model_loader is None:
        _model_loader = ModelLoader()
    return _model_loader

# Export for backward compatibility
model_loader = LazyProxy(get_model_loader)