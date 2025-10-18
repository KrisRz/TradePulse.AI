"""
TradePulse.AI - Enterprise Backend Entry Point
Professional Clean Architecture Implementation with Real Data Only
"""

import sys
import os
from pathlib import Path

# TensorFlow mutex deadlock prevention - MUST BE BEFORE ANY TF IMPORTS
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_USE_LEGACY_KERAS'] = '1'
os.environ['TF_NUM_INTEROP_THREADS'] = '1'
os.environ['TF_NUM_INTRAOP_THREADS'] = '1'
os.environ['TF_DISABLE_MKL'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'

# Import TensorFlow first to configure it before other imports
try:
    import tensorflow as tf  # pyright: ignore[reportMissingImports]
    # Configure TensorFlow to prevent mutex deadlocks
    tf.config.threading.set_inter_op_parallelism_threads(1)
    tf.config.threading.set_intra_op_parallelism_threads(1)
    physical_devices = tf.config.list_physical_devices('GPU')
    if len(physical_devices) > 0:
        tf.config.experimental.set_memory_growth(physical_devices[0], True)
    print("✅ TensorFlow configured successfully")
except Exception as tf_error:
    print(f"⚠️ TensorFlow configuration warning: {tf_error}")

# Add paths for local development
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent if current_dir.name == "backend" else current_dir

# Add paths to Python path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(current_dir))

# Suppress ML library warnings before model imports
import warnings
warnings.filterwarnings('ignore')
os.environ['PYTHONWARNINGS'] = 'ignore'

# Suppress specific LightGBM warnings that appear during model loading
try:
    import lightgbm as lgb
    # Use correct LightGBM logging suppression
    import logging
    lgb_logger = logging.getLogger('lightgbm')
    lgb_logger.setLevel(logging.CRITICAL)
except ImportError:
    pass  # LightGBM not installed

# Only import uvicorn for local development
try:
    import uvicorn
except ImportError:
    uvicorn = None

# Standard imports
from app.backend.core.application import create_application
from app.backend.core.config import get_settings
from app.backend.core.logging import get_logger
from app.backend.core.singleton_app import get_singleton_app, setup_lifespan_handlers
from app.backend.utils.pipeline_debug_logger import (
    get_pipeline_debug_logger, log_pipeline_startup_banner,
    register_pipeline_component, ComponentStatus
)

# Initialize settings and logger
settings = get_settings()
logger = get_logger(__name__)

# STARTUP DEBUG - Print to console immediately
print("=" * 80)
print("🚀 TradePulse.AI Backend Starting...")
print(f"📍 Version: main.py loaded")
print(f"🌍 Environment: {settings.ENVIRONMENT}")
print(f"🐍 Python: {sys.version}")
print("=" * 80)

# Initialize pipeline debug logger and register core components
pipeline_logger = get_pipeline_debug_logger()

# Register all expected pipeline components
register_pipeline_component("brain_controller", "BRAIN Controller", "1.0.0", "FSM Orchestrator", [])
register_pipeline_component("enterprise_engine", "Enterprise Trading Engine", "1.0.0", "6-Layer AI Signal Generation", ["market_data"])
register_pipeline_component("entry_engine", "Intelligent Entry Engine", "1.0.0", "Entry Point Optimization", ["enterprise_engine", "market_data"])
register_pipeline_component("exit_engine", "Intelligent Exit Engine", "1.0.0", "Position Exit Management", ["enterprise_engine", "market_data"])
register_pipeline_component("day_trading_engine", "Day Trading Engine", "1.0.0", "High-Frequency Coordination", ["enterprise_engine", "entry_engine", "exit_engine"])
register_pipeline_component("market_data", "Live Market Data Service", "1.0.0", "Real-time WebSocket Streaming", [])
register_pipeline_component("risk_manager", "Dynamic Risk Manager", "1.0.0", "Risk Assessment & Controls", [])
register_pipeline_component("emergency_controls", "Emergency Control System", "1.0.0", "Safety & Circuit Breakers", [])

# Create FastAPI application using factory pattern
app = create_application()

# Setup singleton lease-based trading brain
setup_lifespan_handlers(app)

# Add singleton-aware health endpoints
singleton_app = get_singleton_app()

@app.get("/health")
def health_check():
    """Health check endpoint - always returns 200 if app is running (fast response for App Runner)"""
    return {
        "status": "healthy",
        "service": "TradePulse.AI Backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": "production"
    }

@app.get("/ready")
def readiness_check():
    """Readiness check - returns 503 if not ready for traffic"""
    status, code = singleton_app.readiness_status()
    return status, code

# Entry point for development server
if __name__ == "__main__":
    if uvicorn:
        logger.info("🚀 Starting TradePulse.AI Enterprise Backend - PROFESSIONAL LIVE DATA MODE")
        logger.info("🎯 Target: Real-time Bitcoin analysis with professional AI models")
        logger.info("🤖 AUTO-START: All trading engines will start automatically")
        
        # Log comprehensive pipeline startup banner
        log_pipeline_startup_banner()
        
        print(f"🚀 Starting uvicorn on {settings.HOST}:{settings.PORT}")
        print(f"🔧 App module: main:app")
        print(f"🔧 Working directory: {os.getcwd()}")
        print(f"🤖 AUTO-START: Day Trading + Brain Controller will start automatically")
        
        # Optional: start Prometheus metrics endpoint
        try:
            from prometheus_client import start_http_server
            start_http_server(9108)
            logger.info("📈 Prometheus metrics server started at :9108")
        except Exception:
            pass

        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=False,  # Disable reload for production stability
            access_log=True,
            log_level="info"
        )
    else:
        logger.info("🔧 TradePulse.AI Backend - Lambda Mode (uvicorn not available)")

# Note: All routing, middleware, and lifespan management is now handled
# by the application factory in core/application.py
# This maintains clean separation of concerns and follows industry standards
# Deployment trigger to sync AWS with latest local code
# This ensures all 3 CI/CD workflows have the most recent fixes
