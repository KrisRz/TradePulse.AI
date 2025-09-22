"""
TradePulse.AI - Enterprise Backend Entry Point
Professional Clean Architecture Implementation with Real Data Only
"""

import sys
import os
from pathlib import Path

# Add project root to Python path for proper imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Only import uvicorn for local development
try:
    import uvicorn
except ImportError:
    uvicorn = None

from app.backend.core.application import create_application
from app.backend.core.config import get_settings
from app.backend.core.logging import get_logger
from app.backend.utils.pipeline_debug_logger import (
    get_pipeline_debug_logger, log_pipeline_startup_banner,
    register_pipeline_component, ComponentStatus
)

# Initialize settings and logger
settings = get_settings()
logger = get_logger(__name__)

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
