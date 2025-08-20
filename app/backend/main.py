"""
TradePulse.AI - Enterprise Backend
Professional Implementation with Trained Models
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to Python path for proper imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

# Only import uvicorn for local development
try:
    import uvicorn
except ImportError:
    uvicorn = None
from datetime import datetime

# Import API routes (module-relative)
from app.backend.api.v1.routes import trading, health, simple_portfolio  # Core trading functionality + simple portfolio
from app.backend.api.v1.routes import portfolio  # Admin dashboard virtual portfolio APIs
from app.backend.api.v1.routes import admin_runtime, auth
# Re-enable enterprise and signals routes (live data only, no mocks)
from app.backend.api.v1.routes import enterprise, signals
# Import admin routes for dashboard functionality
from app.backend.api.v1.routes import admin, user_management, user_analytics, communication, analytics, notifications
from app.backend.api.v1.routes import enterprise_admin
from app.backend.api.v1.routes import real_trading
from app.backend.services.live_market_data import get_live_market_data_service
from app.backend.services.market_data_persistence import start_candle_persistence
# Temporarily disabled for testing: showcase, enterprise, audit_compliance, signals

# Import configuration and logging
from app.backend.core.config import get_settings
from app.backend.core.logging import configure_logging, get_logger
from app.backend.core.exceptions import CommonExceptions

# Import background scheduler
import requests  # Use requests instead of aiohttp for stability

# Get settings first
settings = get_settings()

# Configure logging based on settings
configure_logging(
    log_level=settings.LOG_LEVEL,
    log_format=settings.LOG_FORMAT,
    environment=settings.ENVIRONMENT
)

# Get logger
logger = get_logger(__name__)

# 🚀 OPTIMIZED AUTO SIGNAL SCHEDULER FOR DAY TRADING
class AutoSignalScheduler:
    """Optimized automatic signal generation for aggressive day trading"""
    
    def __init__(self):
        self.is_running = False
        self.signal_interval = 30  # 30 seconds for aggressive day trading Bitcoin analysis
        self.last_signal_time = None
        self.signal_count = 0
        
    async def start_automatic_signals(self):
        """Start automatic signal generation every 3 minutes"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("🚀 AGGRESSIVE DAY TRADING SCHEDULER STARTED - 30 second intervals")
        
        while self.is_running:
            try:
                await self._generate_and_store_signal()
                await asyncio.sleep(self.signal_interval)
            except Exception as e:
                logger.error(f"❌ Error in signal generation loop: {e}")
                await asyncio.sleep(5)  # Wait 5 seconds before retrying
    
    async def _generate_and_store_signal(self):
        """Generate and store a single trading signal"""
        try:
            # This would integrate with your actual trading engine
            self.signal_count += 1
            self.last_signal_time = datetime.now()
            
            logger.info(f"📊 Generated signal #{self.signal_count} at {self.last_signal_time}")
            
        except Exception as e:
            logger.error(f"❌ Error generating signal: {e}")
    
    def stop(self):
        """Stop the automatic signal generation"""
        self.is_running = False
        logger.info(f"🛑 Aggressive scheduler stopped after {self.signal_count} signals")
    
    def get_stats(self):
        """Get scheduler statistics"""
        if not self.last_signal_time:
            return {
                "is_running": self.is_running,
                "signal_count": self.signal_count,
                "last_signal_time": None,
                "signals_per_hour": 0,
                "expected_signals_per_hour": 120,
                "uptime_minutes": 0
            }
        
        uptime_minutes = (datetime.now() - self.last_signal_time).total_seconds() / 60
        signals_per_hour = (self.signal_count / max(uptime_minutes, 1)) * 60
        
        return {
            "is_running": self.is_running,
            "signal_count": self.signal_count,
            "last_signal_time": self.last_signal_time.isoformat(),
            "signals_per_hour": round(signals_per_hour, 1),
            "expected_signals_per_hour": 120,  # 60min / 30sec = 120
            "uptime_minutes": round(uptime_minutes, 1)
        }

# Global scheduler instance
auto_scheduler = AutoSignalScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Modern FastAPI lifespan context manager"""
    # Startup
    logger.info("🚀 TradePulse.AI Backend starting...")
    # Ensure live market data WebSocket service is running early and sync STRICT flag from env at boot
    try:
        service = await get_live_market_data_service()
        if service and service.is_running:
            logger.info("✅ Live market data service initialized at startup")
        else:
            logger.warning("⚠️ Live market data service not running at startup")
        # Sync STRICT_LIVE_STREAM from env once on startup
        from app.backend.core.config import get_settings as _gs
        from app.backend.core.runtime_config import runtime_config_store as _rcs
        s = _gs()
        cfg = await _rcs.get()
        if bool(s.STRICT_LIVE_STREAM) != bool(cfg.strict_live_stream):
            new_cfg = type(cfg)(strict_live_stream=bool(s.STRICT_LIVE_STREAM), engine_enabled=bool(cfg.engine_enabled))
            await _rcs.set(new_cfg)
            logger.info(f"🔒 STRICT_LIVE_STREAM synced from env: {new_cfg.strict_live_stream}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize live market data service at startup: {e}")
    
    # Start candle persistence in background (non-blocking)
    try:
        asyncio.create_task(start_candle_persistence())
        logger.info("📝 Candle persistence task started")
    except Exception as e:
        logger.error(f"❌ Failed to start candle persistence: {e}")

    # Disable main scheduler - Trading Brain has its own optimized loop
    if not os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        # asyncio.create_task(auto_scheduler.start_automatic_signals())  # Disabled - Trading Brain handles this
        logger.info("✅ Trading Brain internal loop handling signals (main scheduler disabled)")
    else:
        logger.info("⏸ Background scheduler disabled in Lambda runtime")
    
    logger.info("✅ TradePulse.AI Backend initialized")
    
    yield
    
    # Shutdown
    logger.info("🛑 TradePulse.AI Backend shutting down...")
    auto_scheduler.stop()
    logger.info("🛑 Aggressive scheduler stopped after 0 signals")

# Create FastAPI app with modern lifespan
app = FastAPI(
    title="TradePulse.AI Enterprise Backend",
    description="Professional Enterprise Trading System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes - Core trading functionality + simple portfolio
app.include_router(trading.router, prefix="/api/trading", tags=["trading"])
app.include_router(simple_portfolio.router, prefix="/api/portfolio/virtual", tags=["portfolio"])
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(admin_runtime.router, prefix="/api", tags=["admin-runtime"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])  # exposes /api/portfolio/virtual/*
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])  # login/register/me
# Real trading + live data control
app.include_router(real_trading.router, prefix="/api/real_trading", tags=["real-trading"]) 
# Enterprise admin endpoints (model hot-reload only, lightweight)
app.include_router(enterprise_admin.router, prefix="/api/enterprise-admin", tags=["enterprise-admin"]) 
# Include admin routes for dashboard functionality
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(user_management.router, prefix="/api/admin", tags=["user-management"])
app.include_router(user_analytics.router, prefix="/api/analytics/admin", tags=["user-analytics"])
app.include_router(communication.router, prefix="/api/admin/communications", tags=["communication"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
# Enterprise signal + analysis APIs (LIVE ONLY)
app.include_router(enterprise.router, prefix="/api/enterprise", tags=["enterprise"])
# Signals aggregation APIs
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])



# Add root health endpoint
@app.get("/health")
async def root_health():
    """Root level health check endpoint"""
    return {"status": "healthy", "service": "TradePulse.AI Backend", "timestamp": datetime.now().isoformat()}

@app.get("/")
async def root():
    """Root endpoint with system info"""
    return {
        "service": "TradePulse.AI Enterprise Backend",
        "version": "1.0.0",
        "status": "operational",
        "mode": "AGGRESSIVE_DAY_TRADING",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health",
            "detailed_health": "/api/health",
            "admin": "/api/admin",
            "trading": "/api/trading"
        }
    }

if __name__ == "__main__":
    if uvicorn:
        logger.info("🚀 Starting TradePulse.AI Enterprise Backend - AGGRESSIVE DAY TRADING MODE")
        logger.info("🎯 Target: Real-time Bitcoin analysis with 30-second signal generation")
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            access_log=True
        )
    else:
        logger.info("🔧 TradePulse.AI Backend - Lambda Mode (uvicorn not available)") # deploy trigger 20250813T141540Z
# Deployment trigger Wed Aug 13 15:44:54 UTC 2025

# Test route for API Gateway debugging
@app.get("/test")
async def test_route():
    """Simple test route for debugging API Gateway"""
    return {"message": "Test route works!", "service": "Main Backend Lambda"}

@app.get("/api/test")
async def api_test_route():
    """API test route for debugging"""
    return {"message": "API test route works!", "path": "/api/test", "service": "Main Backend Lambda"}


# Simple debug routes for testing
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "TradePulse.AI Enterprise Backend", "status": "running", "timestamp": datetime.now().isoformat()}

@app.get("/test")
async def test():
    """Test endpoint"""
    return {"message": "Test endpoint working!", "status": "success"}

@app.get("/api/test")
async def api_test():
    """API test endpoint"""
    return {"message": "API test working!", "path": "/api/test", "status": "success"}
