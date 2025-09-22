"""
TradePulse.AI Model Performance Metrics Service
==============================================

Professional model performance tracking service for enterprise trading system.
Tracks AI model performance and accuracy using real live data.

Author: TradePulse.AI Development Team
Version: 1.0.0 (Production)
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import statistics

from app.backend.core.database import get_database_client
from app.backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

@dataclass
class ModelMetrics:
    """Model performance metrics"""
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    total_predictions: int
    correct_predictions: int
    avg_confidence: float
    last_updated: int

class ModelPerformanceMetrics:
    """
    Professional model performance metrics tracker for TradePulse.AI
    Tracks AI model performance with real data only
    """
    
    def __init__(self):
        self.db_client = get_database_client()
        self.model_metrics: Dict[str, ModelMetrics] = {}
        logger.info("🔧 ModelPerformanceMetrics initialized")
    
    async def track_model_performance(self, model_name: str, prediction: float, actual_outcome: float, confidence: float) -> None:
        """Track model performance with real prediction and outcome"""
        try:
            if model_name not in self.model_metrics:
                self.model_metrics[model_name] = ModelMetrics(
                    model_name=model_name,
                    accuracy=0.0,
                    precision=0.0,
                    recall=0.0,
                    f1_score=0.0,
                    total_predictions=0,
                    correct_predictions=0,
                    avg_confidence=0.0,
                    last_updated=int(datetime.now(timezone.utc).timestamp())
                )
            
            metrics = self.model_metrics[model_name]
            metrics.total_predictions += 1
            
            # Check if prediction was correct (within threshold)
            if abs(prediction - actual_outcome) < 0.1:  # 10% threshold
                metrics.correct_predictions += 1
            
            # Update accuracy
            metrics.accuracy = (metrics.correct_predictions / metrics.total_predictions) * 100
            
            # Update average confidence
            metrics.avg_confidence = (metrics.avg_confidence * (metrics.total_predictions - 1) + confidence) / metrics.total_predictions
            
            metrics.last_updated = int(datetime.now(timezone.utc).timestamp())
            
            # Store in database
            await self._store_metrics(metrics)
            
        except Exception as e:
            logger.error(f"❌ Error tracking model performance: {e}")
    
    async def _store_metrics(self, metrics: ModelMetrics) -> None:
        """Store model metrics in database"""
        try:
            item = {
                'PK': f'MODEL_METRICS#{metrics.model_name}',
                'SK': f'{metrics.last_updated}',
                'model_name': metrics.model_name,
                'accuracy': metrics.accuracy,
                'precision': metrics.precision,
                'recall': metrics.recall,
                'f1_score': metrics.f1_score,
                'total_predictions': metrics.total_predictions,
                'correct_predictions': metrics.correct_predictions,
                'avg_confidence': metrics.avg_confidence,
                'last_updated': metrics.last_updated,
                'date': datetime.fromtimestamp(metrics.last_updated, tz=timezone.utc).strftime('%Y-%m-%d'),
                'TTL': metrics.last_updated + (90 * 24 * 60 * 60)  # 90 days retention
            }
            
            table = self.db_client.get_table('model_performance_metrics')
            table.put_item(Item=item)
            
        except Exception as e:
            logger.error(f"❌ Error storing model metrics: {e}")
    
    def get_model_metrics(self, model_name: str) -> Optional[ModelMetrics]:
        """Get metrics for specific model"""
        return self.model_metrics.get(model_name)
    
    def get_all_metrics(self) -> Dict[str, ModelMetrics]:
        """Get all model metrics"""
        return self.model_metrics.copy()

# Global instance
_model_performance_metrics = None

def get_model_performance_metrics():
    """Get global model performance metrics instance"""
    global _model_performance_metrics
    if _model_performance_metrics is None:
        _model_performance_metrics = ModelPerformanceMetrics()
    return _model_performance_metrics

# Export for backward compatibility
model_performance_metrics = get_model_performance_metrics()
