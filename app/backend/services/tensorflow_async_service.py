"""
Professional TensorFlow Async Service for TradePulse.AI
Enterprise-grade async TensorFlow integration with mutex protection
"""

import asyncio
import logging
import threading
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import queue
import time

# TensorFlow async configuration - MUST be set before any TF imports
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress all TensorFlow logging
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Disable oneDNN optimizations
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Disable CUDA
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
os.environ['TF_GPU_THREAD_MODE'] = 'gpu_private'
os.environ['TF_USE_LEGACY_KERAS'] = '1'
os.environ['TF_DISABLE_MKL'] = '1'  # Disable Intel MKL
os.environ['TF_NUM_INTEROP_THREADS'] = '1'  # Single thread for inter-op
os.environ['TF_NUM_INTRAOP_THREADS'] = '1'  # Single thread for intra-op

try:
    import tensorflow as tf
    
    # Use only tf.keras to avoid Keras 3 namespace issues on Py3.11
    from tensorflow.keras.models import load_model as tf_load_model
    
    # Professional TensorFlow configuration for async usage
    tf.config.set_visible_devices([], 'GPU')  # Force CPU only
    tf.config.threading.set_inter_op_parallelism_threads(1)
    tf.config.threading.set_intra_op_parallelism_threads(1)
    tf.config.experimental.enable_op_determinism()  # Deterministic ops
    tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
    
    # Keep eager execution enabled for better compatibility
    # tf.compat.v1.disable_eager_execution()  # Commented out - causes issues
    
    TENSORFLOW_AVAILABLE = True
    
except ImportError:
    TENSORFLOW_AVAILABLE = False
    tf = None
    tf_load_model = None

from app.backend.core.logging import get_logger

logger = get_logger(__name__)


class TensorFlowAsyncService:
    """
    Professional async TensorFlow service with mutex protection
    
    Features:
    - Thread-safe model loading and inference
    - Async prediction queue with batching
    - Memory management and cleanup
    - Performance monitoring
    - Graceful degradation if TensorFlow unavailable
    """
    
    def __init__(self):
        self.is_initialized = False
        self.models: Dict[str, Any] = {}
        self.model_path = Path(__file__).parent.parent / "models" / "enterprise"
        
        # Thread safety
        self._model_lock = threading.RLock()
        self._prediction_queue = queue.Queue(maxsize=100)
        self._executor = None
        self._worker_thread = None
        self._shutdown_event = threading.Event()
        
        # Performance tracking
        self._prediction_count = 0
        self._total_prediction_time = 0.0
        self._last_cleanup = time.time()
        
        # Async prediction results
        self._pending_predictions: Dict[str, asyncio.Future] = {}
        
    async def initialize(self) -> bool:
        """Initialize the TensorFlow async service"""
        if not TENSORFLOW_AVAILABLE:
            logger.warning("⚠️ TensorFlow not available - LSTM predictions will be disabled")
            return False
            
        if self.is_initialized:
            return True
            
        try:
            logger.info("🔧 Initializing TensorFlow Async Service...")
            
            # Create thread pool for TensorFlow operations
            self._executor = ThreadPoolExecutor(
                max_workers=1,  # Single worker to prevent mutex issues
                thread_name_prefix="tf_async"
            )
            
            # Start prediction worker thread
            self._worker_thread = threading.Thread(
                target=self._prediction_worker,
                name="tf_prediction_worker",
                daemon=True
            )
            self._worker_thread.start()
            
            # Load LSTM models in thread-safe manner
            await self._load_models_async()
            
            self.is_initialized = True
            logger.info("✅ TensorFlow Async Service initialized successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ TensorFlow Async Service initialization failed: {e}")
            return False
    
    async def _load_models_async(self):
        """Load TensorFlow models asynchronously"""
        try:
            logger.info("📚 Loading LSTM models asynchronously...")
            
            # Load models in executor to prevent blocking
            loop = asyncio.get_event_loop()
            
            model_files = [
                ("lstm_1h", "lstm_1h.h5"),
                ("lstm_4h", "lstm_4h.h5"), 
                ("lstm_24h", "lstm_24h.h5"),
                ("lstm_1m", "lstm_1m.h5"),
                ("lstm_5m", "lstm_5m.h5")
            ]
            
            loaded_count = 0
            
            for model_name, filename in model_files:
                model_path = self.model_path / filename
                
                if model_path.exists():
                    try:
                        # Load model in thread pool
                        model = await loop.run_in_executor(
                            self._executor,
                            self._load_single_model,
                            model_path
                        )
                        
                        with self._model_lock:
                            self.models[model_name] = model
                        
                        loaded_count += 1
                        logger.info(f"✅ Loaded {model_name} model asynchronously")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to load {model_name}: {e}")
                        
            logger.info(f"📊 Loaded {loaded_count} LSTM models successfully")
            
        except Exception as e:
            logger.error(f"❌ Async model loading failed: {e}")
    
    def keras_predict(self, model, x):
        """FIXED: Explicitly set verbose=0 to avoid TF 2.16+ conflicts"""
        # Explicitly pass verbose=0 to prevent Keras 3.x from adding duplicate verbose argument
        try:
            return model.predict(x, verbose=0)
        except TypeError:
            # Fallback for older TensorFlow versions that don't accept verbose
            return model.predict(x)
    
    def _load_single_model(self, model_path: Path):
        """Load a single TensorFlow model (thread-safe) - FIXED for proper warm-up"""
        try:
            # Load with compile=False to prevent issues
            model = tf.keras.models.load_model(str(model_path), compile=False)
            
            # FIXED: Introspect required shape and warm up with correct dimensions
            if len(model.input_shape) != 3:
                raise ValueError(f"Unexpected input_shape {model.input_shape} for {model_path}")
            
            _, timesteps, features = model.input_shape
            logger.info(f"📊 LSTM loaded: {model_path.name} | timesteps={timesteps} features={features}")
            
            # Warm-up with the right shape (zeros are fine)
            dummy_input = np.zeros((1, timesteps, features), dtype=np.float32)
            _ = self.keras_predict(model, dummy_input)
            
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model {model_path}: {e}")
            raise
    
    async def predict_async(self, model_name: str, input_data: np.ndarray, timeout: float = 5.0) -> Optional[np.ndarray]:
        """
        Async prediction with timeout protection
        
        Args:
            model_name: Name of the model to use
            input_data: Input data for prediction
            timeout: Maximum time to wait for prediction
            
        Returns:
            Prediction result or None if failed/timeout
        """
        if not self.is_initialized or model_name not in self.models:
            logger.debug(f"Model {model_name} not available for async prediction")
            return None
            
        try:
            # Create unique prediction ID
            prediction_id = f"{model_name}_{time.time()}_{id(input_data)}"
            
            # Create future for result
            result_future = asyncio.Future()
            self._pending_predictions[prediction_id] = result_future
            
            # Queue prediction request
            prediction_request = {
                'id': prediction_id,
                'model_name': model_name,
                'input_data': input_data.copy(),  # Copy to prevent race conditions
                'timestamp': time.time()
            }
            
            try:
                self._prediction_queue.put_nowait(prediction_request)
            except queue.Full:
                logger.warning("Prediction queue full - dropping request")
                del self._pending_predictions[prediction_id]
                return None
            
            # Wait for result with timeout
            try:
                result = await asyncio.wait_for(result_future, timeout=timeout)
                return result
                
            except asyncio.TimeoutError:
                logger.warning(f"Prediction timeout for {model_name}")
                # Clean up
                if prediction_id in self._pending_predictions:
                    del self._pending_predictions[prediction_id]
                return None
                
        except Exception as e:
            logger.error(f"Async prediction failed for {model_name}: {e}")
            return None
    
    def _prediction_worker(self):
        """Worker thread for processing predictions"""
        logger.info("🔄 TensorFlow prediction worker started")
        
        while not self._shutdown_event.is_set():
            try:
                # Get prediction request with timeout
                try:
                    request = self._prediction_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process prediction
                self._process_prediction_request(request)
                
                # Periodic cleanup
                if time.time() - self._last_cleanup > 60:  # Every minute
                    self._cleanup_expired_predictions()
                    self._last_cleanup = time.time()
                
            except Exception as e:
                logger.error(f"Prediction worker error: {e}")
                time.sleep(0.1)  # Brief pause on error
        
        logger.info("🛑 TensorFlow prediction worker stopped")
    
    def _process_prediction_request(self, request: Dict[str, Any]):
        """Process a single prediction request"""
        try:
            prediction_id = request['id']
            model_name = request['model_name']
            input_data = request['input_data']
            
            # Check if request is still pending
            if prediction_id not in self._pending_predictions:
                return
            
            future = self._pending_predictions[prediction_id]
            
            # Perform prediction with thread safety
            start_time = time.time()
            
            with self._model_lock:
                if model_name not in self.models:
                    future.set_result(None)
                    del self._pending_predictions[prediction_id]
                    return
                
                model = self.models[model_name]
                
                try:
                    # FIXED: Use centralized predict method to avoid verbose conflicts
                    prediction = self.keras_predict(model, input_data)
                    
                    # Update performance metrics
                    self._prediction_count += 1
                    self._total_prediction_time += time.time() - start_time
                    
                    # Set result
                    future.set_result(prediction)
                    
                except Exception as pred_error:
                    logger.error(f"Model prediction error: {pred_error}")
                    future.set_result(None)
            
            # Clean up
            del self._pending_predictions[prediction_id]
            
        except Exception as e:
            logger.error(f"Prediction processing error: {e}")
            # Ensure future is resolved
            if prediction_id in self._pending_predictions:
                self._pending_predictions[prediction_id].set_result(None)
                del self._pending_predictions[prediction_id]
    
    def _cleanup_expired_predictions(self):
        """Clean up expired prediction requests"""
        try:
            current_time = time.time()
            expired_ids = []
            
            for prediction_id, future in self._pending_predictions.items():
                # Extract timestamp from ID
                try:
                    timestamp = float(prediction_id.split('_')[1])
                    if current_time - timestamp > 30:  # 30 second expiry
                        expired_ids.append(prediction_id)
                except (IndexError, ValueError):
                    expired_ids.append(prediction_id)  # Invalid ID format
            
            # Clean up expired requests
            for prediction_id in expired_ids:
                future = self._pending_predictions.get(prediction_id)
                if future and not future.done():
                    future.set_result(None)
                del self._pending_predictions[prediction_id]
            
            if expired_ids:
                logger.debug(f"Cleaned up {len(expired_ids)} expired predictions")
                
        except Exception as e:
            logger.error(f"Prediction cleanup error: {e}")
    
    async def get_ensemble_prediction(self, input_data: np.ndarray, timeframes: List[str] = None) -> Dict[str, Any]:
        """
        Get ensemble prediction from multiple LSTM models
        
        Args:
            input_data: Input sequence data
            timeframes: List of timeframes to use (default: all available)
            
        Returns:
            Ensemble prediction results
        """
        if timeframes is None:
            timeframes = ["1h", "4h", "24h"]
        
        try:
            # Prepare input for each model
            predictions = {}
            tasks = []
            
            for timeframe in timeframes:
                model_name = f"lstm_{timeframe}"
                if model_name in self.models:
                    # Create prediction task
                    task = self.predict_async(model_name, input_data)
                    tasks.append((timeframe, task))
            
            if not tasks:
                return {
                    'ensemble_prediction': 0.5,
                    'individual_predictions': {},
                    'models_used': 0,
                    'confidence': 0.0
                }
            
            # Wait for all predictions
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            # Process results
            valid_predictions = []
            
            for i, (timeframe, _) in enumerate(tasks):
                result = results[i]
                
                if isinstance(result, Exception):
                    logger.warning(f"Prediction failed for {timeframe}: {result}")
                    predictions[timeframe] = None
                elif result is not None:
                    pred_value = float(result[0][0]) if result.size > 0 else 0.5
                    predictions[timeframe] = pred_value
                    valid_predictions.append(pred_value)
                else:
                    predictions[timeframe] = None
            
            # Calculate ensemble
            if valid_predictions:
                ensemble_pred = np.mean(valid_predictions)
                confidence = 1.0 - (np.std(valid_predictions) if len(valid_predictions) > 1 else 0.0)
            else:
                ensemble_pred = 0.5
                confidence = 0.0
            
            return {
                'ensemble_prediction': float(ensemble_pred),
                'individual_predictions': predictions,
                'models_used': len(valid_predictions),
                'confidence': float(confidence)
            }
            
        except Exception as e:
            logger.error(f"Ensemble prediction failed: {e}")
            return {
                'ensemble_prediction': 0.5,
                'individual_predictions': {},
                'models_used': 0,
                'confidence': 0.0
            }
    
    async def shutdown(self):
        """Gracefully shutdown the service"""
        logger.info("🛑 Shutting down TensorFlow Async Service...")
        
        try:
            # Signal shutdown
            self._shutdown_event.set()
            
            # Cancel pending predictions
            for future in self._pending_predictions.values():
                if not future.done():
                    future.cancel()
            
            self._pending_predictions.clear()
            
            # Wait for worker thread
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=5.0)
            
            # Shutdown executor
            if self._executor:
                self._executor.shutdown(wait=True)
            
            # Clear models
            with self._model_lock:
                self.models.clear()
            
            logger.info("✅ TensorFlow Async Service shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Shutdown error: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        avg_time = (
            self._total_prediction_time / self._prediction_count 
            if self._prediction_count > 0 else 0.0
        )
        
        return {
            'is_initialized': self.is_initialized,
            'models_loaded': len(self.models),
            'total_predictions': self._prediction_count,
            'average_prediction_time': avg_time,
            'pending_predictions': len(self._pending_predictions),
            'queue_size': self._prediction_queue.qsize(),
            'tensorflow_available': TENSORFLOW_AVAILABLE
        }


# Global service instance
_tensorflow_async_service: Optional[TensorFlowAsyncService] = None

async def get_tensorflow_async_service() -> TensorFlowAsyncService:
    """Get global TensorFlow async service instance"""
    global _tensorflow_async_service
    
    if _tensorflow_async_service is None:
        _tensorflow_async_service = TensorFlowAsyncService()
        await _tensorflow_async_service.initialize()
    
    return _tensorflow_async_service


async def shutdown_tensorflow_service():
    """Shutdown the global TensorFlow service"""
    global _tensorflow_async_service
    
    if _tensorflow_async_service:
        await _tensorflow_async_service.shutdown()
        _tensorflow_async_service = None
