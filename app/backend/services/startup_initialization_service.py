"""
Startup Initialization Service - TradePulse.AI Enterprise
========================================================

Handles application startup initialization including:
- Historical market context pre-calculation
- Entry engine warmup period
- Background data preparation
- Service readiness coordination

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class StartupInitializationService:
    """
    Coordinates application startup and background data preparation
    
    Ensures all services are ready before allowing trading operations
    """
    
    def __init__(self):
        self.is_initialized = False
        self.initialization_start_time = None
        self.services_status = {}
        
        logger.info("🚀 Startup Initialization Service created")
    
    async def initialize_all_services(self):
        """Initialize all services in the correct order"""
        if self.is_initialized:
            return self.services_status
        
        self.initialization_start_time = datetime.now(timezone.utc)
        logger.info("🚀 Starting comprehensive service initialization...")
        
        try:
            # Phase 1: Initialize historical context service (background)
            logger.info("📊 Phase 1: Starting historical context service initialization...")
            historical_task = asyncio.create_task(self._initialize_historical_context())
            
            # Phase 2: Initialize other core services
            logger.info("🔧 Phase 2: Initializing core services...")
            await self._initialize_core_services()
            
            # Phase 3: Wait for historical context to complete
            logger.info("⏳ Phase 3: Waiting for historical context service...")
            historical_status = await historical_task
            
            # Phase 4: Initialize trading engines with historical context ready
            logger.info("🎯 Phase 4: Initializing enhanced trading engines...")
            await self._initialize_trading_engines()
            
            self.is_initialized = True
            total_time = (datetime.now(timezone.utc) - self.initialization_start_time).total_seconds()
            
            logger.info(f"✅ ALL SERVICES INITIALIZED in {total_time:.1f} seconds")
            
            return self.services_status
            
        except Exception as e:
            logger.error(f"❌ Service initialization failed: {e}")
            raise
    
    async def _initialize_historical_context(self) -> Dict[str, Any]:
        """Initialize historical market context service"""
        try:
            logger.info("📊 Initializing historical market context...")
            
            from app.backend.services.historical_market_context_service import get_historical_context_service
            
            start_time = datetime.now(timezone.utc)
            context_service = await get_historical_context_service()
            init_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            status = context_service.get_service_status()
            self.services_status["historical_context"] = {
                "status": "operational",
                "initialization_time_seconds": init_time,
                "details": status
            }
            
            logger.info(f"✅ Historical context service ready in {init_time:.1f}s")
            return self.services_status["historical_context"]
            
        except Exception as e:
            logger.error(f"❌ Historical context initialization failed: {e}")
            self.services_status["historical_context"] = {
                "status": "failed",
                "error": str(e)
            }
            # Don't raise - allow other services to continue
            return self.services_status["historical_context"]
    
    async def _initialize_core_services(self):
        """Initialize core services (database, market data, etc.)"""
        try:
            # Initialize live market data service
            from app.backend.services.live_market_data import get_live_market_data_service
            
            start_time = datetime.now(timezone.utc)
            market_service = await get_live_market_data_service()
            init_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            self.services_status["live_market_data"] = {
                "status": "operational",
                "initialization_time_seconds": init_time,
                "is_running": market_service.is_running
            }
            
            logger.info(f"✅ Live market data service ready in {init_time:.1f}s")
            
        except Exception as e:
            logger.error(f"❌ Core services initialization failed: {e}")
            self.services_status["core_services"] = {
                "status": "failed", 
                "error": str(e)
            }
    
    async def _initialize_trading_engines(self):
        """Initialize trading engines after historical context is ready"""
        try:
            # Initialize enterprise trading engine
            from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine
            
            start_time = datetime.now(timezone.utc)
            enterprise_engine = EnterpriseTradingEngine()
            await enterprise_engine.initialize()
            init_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            self.services_status["enterprise_trading_engine"] = {
                "status": "operational",
                "initialization_time_seconds": init_time,
                "is_initialized": enterprise_engine.is_initialized
            }
            
            logger.info(f"✅ Enterprise trading engine ready in {init_time:.1f}s")
            
            # Note: Intelligent entry engine will initialize with warmup period when first called
            self.services_status["intelligent_entry_engine"] = {
                "status": "ready_for_warmup",
                "warmup_period_minutes": 30
            }
            
        except Exception as e:
            logger.error(f"❌ Trading engines initialization failed: {e}")
            self.services_status["trading_engines"] = {
                "status": "failed",
                "error": str(e)
            }
    
    def get_initialization_status(self) -> Dict[str, Any]:
        """Get current initialization status"""
        if self.initialization_start_time:
            elapsed = (datetime.now(timezone.utc) - self.initialization_start_time).total_seconds()
        else:
            elapsed = 0
        
        return {
            "is_initialized": self.is_initialized,
            "initialization_time_seconds": elapsed,
            "services_status": self.services_status,
            "services_ready": len([s for s in self.services_status.values() if s.get("status") == "operational"]),
            "total_services": len(self.services_status),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Global service instance
_startup_service: Optional[StartupInitializationService] = None

async def get_startup_service() -> StartupInitializationService:
    """Get or create startup initialization service"""
    global _startup_service
    if _startup_service is None:
        _startup_service = StartupInitializationService()
    return _startup_service

async def initialize_application():
    """Initialize the entire application with proper service coordination"""
    service = await get_startup_service()
    return await service.initialize_all_services()

# Export the service
__all__ = ["StartupInitializationService", "get_startup_service", "initialize_application"]
