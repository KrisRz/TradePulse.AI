"""
Phase 2.2: Model Performance Optimizer for TradePulse.AI
Optimizes AI model inference speed to achieve <5-second cycles
"""

import asyncio
import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import logging
from pathlib import Path
import pickle
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ModelPerformanceMetrics:
    """Performance metrics for model inference"""
    model_name: str
    inference_time_ms: float
    feature_prep_time_ms: float
    total_time_ms: float
    memory_usage_mb: float
    cache_hit_rate: float
    throughput_per_second: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'model_name': self.model_name,
            'inference_time_ms': self.inference_time_ms,
            'feature_prep_time_ms': self.feature_prep_time_ms,
            'total_time_ms': self.total_time_ms,
            'memory_usage_mb': self.memory_usage_mb,
            'cache_hit_rate': self.cache_hit_rate,
            'throughput_per_second': self.throughput_per_second
        }


@dataclass
class OptimizationConfig:
    """Configuration for model optimization"""
    enable_parallel_inference: bool = True
    enable_result_caching: bool = True
    enable_feature_caching: bool = True
    enable_model_quantization: bool = False  # Advanced optimization
    max_cache_size: int = 1000
    cache_ttl_seconds: int = 30
    parallel_workers: int = 4
    target_latency_ms: float = 1000.0  # Target <1s per layer
    
    # Performance thresholds
    slow_inference_threshold_ms: float = 500.0
    memory_warning_threshold_mb: float = 500.0


class ModelPerformanceOptimizer:
    """
    Professional Model Performance Optimizer
    Implements aggressive optimizations to achieve <5-second AI cycles
    """
    
    def __init__(self, config: OptimizationConfig = None):
        self.config = config or OptimizationConfig()
        self.metrics_history: List[ModelPerformanceMetrics] = []
        self.performance_cache: Dict[str, Any] = {}
        self.feature_cache: Dict[str, Any] = {}
        self.model_cache: Dict[str, Any] = {}
        
        # Thread pool for parallel inference
        self.executor = ThreadPoolExecutor(max_workers=self.config.parallel_workers)
        
        # Performance tracking
        self.total_inferences = 0
        self.cache_hits = 0
        self.optimization_start_time = time.time()
        
        logger.info(f"🚀 Model Performance Optimizer initialized")
        logger.info(f"   Target latency: {self.config.target_latency_ms}ms per layer")
        logger.info(f"   Parallel workers: {self.config.parallel_workers}")
        logger.info(f"   Cache size: {self.config.max_cache_size}")
    
    def create_feature_cache_key(self, features: Dict[str, Any], model_name: str) -> str:
        """Create a cache key for feature arrays"""
        # Create a stable hash of the features
        feature_str = str(sorted(features.items()))
        cache_key = f"{model_name}:{hashlib.md5(feature_str.encode()).hexdigest()[:8]}"
        return cache_key
    
    def create_result_cache_key(self, features: Dict[str, Any], model_name: str, layer_name: str) -> str:
        """Create a cache key for inference results"""
        feature_str = str(sorted(features.items()))
        cache_key = f"{layer_name}:{model_name}:{hashlib.md5(feature_str.encode()).hexdigest()[:8]}"
        return cache_key
    
    @lru_cache(maxsize=1000)
    def _cached_feature_preparation(self, feature_tuple: tuple, model_name: str) -> np.ndarray:
        """Cached feature preparation to avoid repeated computation"""
        features = dict(feature_tuple)
        
        # Import here to avoid circular imports
        from app.backend.services.feature_schema_validator import validate_features_for_model
        
        try:
            is_valid, feature_array = validate_features_for_model(features, model_name, "cached")
            if is_valid and feature_array is not None:
                return feature_array
        except Exception as e:
            logger.warning(f"Cached feature preparation failed: {e}")
        
        # Fallback to basic array creation
        feature_order = ["close", "volume", "rsi", "macd", "bb_position", "volatility", "trend_strength", "volume_ratio"]
        feature_values = [features.get(f, 0.0) for f in feature_order]
        return np.array(feature_values, dtype=np.float32).reshape(1, -1)
    
    async def optimize_model_inference(self, 
                                     model: Any, 
                                     features: Dict[str, Any],
                                     model_name: str,
                                     layer_name: str) -> Tuple[Any, ModelPerformanceMetrics]:
        """
        Optimized model inference with caching and performance monitoring
        """
        start_time = time.time()
        
        # Create cache keys
        result_cache_key = self.create_result_cache_key(features, model_name, layer_name)
        
        # Check result cache first
        if self.config.enable_result_caching and result_cache_key in self.performance_cache:
            cache_entry = self.performance_cache[result_cache_key]
            if time.time() - cache_entry['timestamp'] < self.config.cache_ttl_seconds:
                self.cache_hits += 1
                logger.debug(f"🎯 Cache hit for {layer_name}: {result_cache_key[:8]}...")
                
                # Return cached result with updated metrics
                metrics = ModelPerformanceMetrics(
                    model_name=model_name,
                    inference_time_ms=0.1,  # Cache hit is very fast
                    feature_prep_time_ms=0.0,
                    total_time_ms=0.1,
                    memory_usage_mb=0.0,
                    cache_hit_rate=100.0,
                    throughput_per_second=10000.0
                )
                return cache_entry['result'], metrics
        
        # Feature preparation with caching
        feature_prep_start = time.time()
        
        if self.config.enable_feature_caching:
            # Convert features to tuple for caching
            feature_tuple = tuple(sorted(features.items()))
            feature_array = self._cached_feature_preparation(feature_tuple, model_name)
        else:
            # Direct feature preparation
            from app.backend.services.feature_schema_validator import validate_features_for_model
            is_valid, feature_array = validate_features_for_model(features, model_name, layer_name)
            if not is_valid or feature_array is None:
                raise ValueError(f"Feature validation failed for {layer_name}")
        
        feature_prep_time = (time.time() - feature_prep_start) * 1000
        
        # Model inference
        inference_start = time.time()
        
        if self.config.enable_parallel_inference:
            # Run inference in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor, 
                self._run_model_inference, 
                model, 
                feature_array, 
                model_name
            )
        else:
            # Direct inference
            result = self._run_model_inference(model, feature_array, model_name)
        
        inference_time = (time.time() - inference_start) * 1000
        total_time = (time.time() - start_time) * 1000
        
        # Cache the result
        if self.config.enable_result_caching:
            self.performance_cache[result_cache_key] = {
                'result': result,
                'timestamp': time.time()
            }
            
            # Clean old cache entries
            if len(self.performance_cache) > self.config.max_cache_size:
                self._cleanup_cache()
        
        # Calculate metrics
        self.total_inferences += 1
        cache_hit_rate = (self.cache_hits / self.total_inferences) * 100
        
        metrics = ModelPerformanceMetrics(
            model_name=model_name,
            inference_time_ms=inference_time,
            feature_prep_time_ms=feature_prep_time,
            total_time_ms=total_time,
            memory_usage_mb=self._estimate_memory_usage(),
            cache_hit_rate=cache_hit_rate,
            throughput_per_second=1000.0 / max(total_time, 1.0)
        )
        
        # Log performance warnings
        if total_time > self.config.slow_inference_threshold_ms:
            logger.warning(f"⚠️ Slow inference in {layer_name}: {total_time:.1f}ms (target: {self.config.target_latency_ms}ms)")
        
        # Store metrics
        self.metrics_history.append(metrics)
        
        return result, metrics
    
    def _run_model_inference(self, model: Any, feature_array: np.ndarray, model_name: str) -> Any:
        """Run actual model inference"""
        try:
            # Handle different model types
            if hasattr(model, 'predict_proba'):
                # Classification model
                probabilities = model.predict_proba(feature_array)
                return probabilities[0] if len(probabilities) > 0 else [0.5, 0.5]
            elif hasattr(model, 'predict'):
                # Regression model or other
                prediction = model.predict(feature_array)
                return prediction[0] if len(prediction) > 0 else 0.0
            else:
                logger.error(f"Unknown model type for {model_name}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Model inference failed for {model_name}: {e}")
            return 0.0
    
    def _cleanup_cache(self):
        """Clean up old cache entries"""
        current_time = time.time()
        
        # Remove expired entries
        expired_keys = [
            key for key, entry in self.performance_cache.items()
            if current_time - entry['timestamp'] > self.config.cache_ttl_seconds
        ]
        
        for key in expired_keys:
            del self.performance_cache[key]
        
        # If still too large, remove oldest entries
        if len(self.performance_cache) > self.config.max_cache_size:
            sorted_entries = sorted(
                self.performance_cache.items(),
                key=lambda x: x[1]['timestamp']
            )
            
            # Keep only the most recent entries
            entries_to_keep = sorted_entries[-self.config.max_cache_size:]
            self.performance_cache = dict(entries_to_keep)
        
        logger.debug(f"Cache cleanup: {len(self.performance_cache)} entries remaining")
    
    def _estimate_memory_usage(self) -> float:
        """Estimate current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            return memory_mb
        except ImportError:
            return 0.0
    
    async def optimize_parallel_layers(self, 
                                     layer_configs: List[Dict[str, Any]], 
                                     features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run multiple AI layers in parallel for maximum speed
        """
        start_time = time.time()
        
        # Create tasks for parallel execution
        tasks = []
        for layer_config in layer_configs:
            task = asyncio.create_task(
                self.optimize_model_inference(
                    model=layer_config['model'],
                    features=features,
                    model_name=layer_config['model_name'],
                    layer_name=layer_config['layer_name']
                )
            )
            tasks.append((layer_config['layer_name'], task))
        
        # Wait for all tasks to complete
        results = {}
        metrics = {}
        
        for layer_name, task in tasks:
            try:
                result, layer_metrics = await task
                results[layer_name] = result
                metrics[layer_name] = layer_metrics
            except Exception as e:
                logger.error(f"Parallel layer {layer_name} failed: {e}")
                results[layer_name] = 0.0
                metrics[layer_name] = None
        
        total_time = (time.time() - start_time) * 1000
        
        logger.info(f"🚀 Parallel inference completed in {total_time:.1f}ms for {len(layer_configs)} layers")
        
        return {
            'results': results,
            'metrics': metrics,
            'total_time_ms': total_time
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        if not self.metrics_history:
            return {"status": "no_data"}
        
        recent_metrics = self.metrics_history[-100:]  # Last 100 inferences
        
        avg_inference_time = np.mean([m.inference_time_ms for m in recent_metrics])
        avg_feature_prep_time = np.mean([m.feature_prep_time_ms for m in recent_metrics])
        avg_total_time = np.mean([m.total_time_ms for m in recent_metrics])
        avg_throughput = np.mean([m.throughput_per_second for m in recent_metrics])
        
        cache_hit_rate = (self.cache_hits / max(self.total_inferences, 1)) * 100
        
        return {
            "total_inferences": self.total_inferences,
            "cache_hit_rate": cache_hit_rate,
            "avg_inference_time_ms": avg_inference_time,
            "avg_feature_prep_time_ms": avg_feature_prep_time,
            "avg_total_time_ms": avg_total_time,
            "avg_throughput_per_second": avg_throughput,
            "cache_size": len(self.performance_cache),
            "target_latency_ms": self.config.target_latency_ms,
            "performance_target_met": avg_total_time < self.config.target_latency_ms,
            "optimization_uptime_hours": (time.time() - self.optimization_start_time) / 3600
        }
    
    def clear_caches(self):
        """Clear all caches"""
        self.performance_cache.clear()
        self.feature_cache.clear()
        self._cached_feature_preparation.cache_clear()
        logger.info("🧹 All caches cleared")
    
    async def shutdown(self):
        """Shutdown the optimizer"""
        self.executor.shutdown(wait=True)
        logger.info("🛑 Model Performance Optimizer shutdown complete")


# Global optimizer instance
_optimizer: Optional[ModelPerformanceOptimizer] = None

def get_model_optimizer() -> ModelPerformanceOptimizer:
    """Get global model optimizer instance"""
    global _optimizer
    if _optimizer is None:
        _optimizer = ModelPerformanceOptimizer()
    return _optimizer


async def optimize_ai_inference(model: Any, 
                              features: Dict[str, Any],
                              model_name: str,
                              layer_name: str) -> Tuple[Any, ModelPerformanceMetrics]:
    """
    Convenience function for optimized AI inference
    """
    optimizer = get_model_optimizer()
    return await optimizer.optimize_model_inference(model, features, model_name, layer_name)
