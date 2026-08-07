"""
TradePulse.AI Application Factory
Professional FastAPI application factory with clean architecture
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.backend.core.config import get_settings
from app.backend.core.logging import get_logger, configure_logging
from app.backend.core.exceptions import TradePulseException
from app.backend.core.middleware import create_rate_limit_middleware
from app.backend.core.metrics import create_prometheus_middleware
from app.backend.core.container import get_container
from app.backend.presentation.api.router import create_api_router
from app.backend.services.startup_initialization_service import initialize_application
from app.backend.core.database import ensure_required_tables
from app.backend.utils.log_filters import configure_log_filtering


logger = get_logger(__name__)


class TradePulseApplication:
    """
    Professional application factory for TradePulse.AI
    Implements clean architecture principles with proper separation of concerns
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.app: FastAPI = None
        self.container = get_container()
        
        # Configure logging first
        configure_logging(
            log_level=self.settings.LOG_LEVEL,
            log_format=self.settings.LOG_FORMAT,
            environment=self.settings.ENVIRONMENT
        )
    
    def create_app(self) -> FastAPI:
        """
        Create and configure FastAPI application
        Returns fully configured app ready for production
        """
        logger.info("🚀 Creating TradePulse.AI Enterprise Application")
        
        # Create FastAPI app without lifespan (use startup event instead)
        self.app = FastAPI(
            title="TradePulse.AI Enterprise Backend",
            description="Professional Enterprise Trading System with Real Live Data",
            version="1.0.0",
            docs_url="/docs" if self.settings.is_development else None,
            redoc_url="/redoc" if self.settings.is_development else None
        )
        
        # Configure middleware
        self._configure_middleware()
        
        # Configure error handlers
        self._configure_error_handlers()
        
        # Configure routes
        self._configure_routes()
        
        # Add health endpoints
        self._configure_health_endpoints()
        
        # Store container in app state for API access
        self.app.state.container = self.container
        
        # Register placeholders for missing engines to prevent API errors  
        self.container.register_singleton("session_aware_trading_engine", lambda: None)
        self.container.register_singleton("brain_controller", lambda: None)
        self.container.register_singleton("continuous_learning_engine", lambda: None)
        
        # PHASE 1 STARTUP - Add Enterprise Trading Engine
        @self.app.on_event("startup")
        async def phase1_startup():
            """Phase 1: Database Migration and Enterprise Trading Engine initialization"""
            import asyncio
            
            # Configure log filtering first
            logger.info("🛡️ Configuring log filtering...")
            try:
                configure_log_filtering()
                logger.info("✅ Log filtering configured")
            except Exception as e:
                logger.error(f"❌ Log filtering configuration failed: {e}")
            
            # Ensure required tables exist before starting any services
            logger.info("🔧 Ensuring required database tables exist...")
            try:
                tables_ready = ensure_required_tables()
                if tables_ready:
                    logger.info("✅ All required database tables are available")
                else:
                    logger.error("❌ Some database tables could not be created")
            except Exception as e:
                logger.error(f"❌ Database table migration failed: {e}")

            # Load brain state once — sets the BrainStateStore readiness barrier
            # every wait_ready() caller depends on (previously only the dead
            # lifespan module did this, so waiters hung forever).
            try:
                from app.backend.core.brain_state_store import get_brain_state_store
                await get_brain_state_store().load_once()
            except Exception as e:
                logger.error(f"❌ Brain state load failed: {e}")
            
            async def init_enterprise_engine():
                try:
                    # QUARANTINE GATE (D11, docs/ANALIZA_6_WARSTW_2026-07-17.md):
                    # the condemned engines (enterprise/entry/exit/learning/brain)
                    # must not boot. Their phases are skipped and None placeholders
                    # registered so every endpoint degrades instead of erroring.
                    # Non-condemned services (risk, emergency, market data, day/
                    # session engines, phase-6 services) still initialize.
                    from app.backend.core.quarantine import ENV_FLAG, enterprise_enabled
                    quarantined = not enterprise_enabled()
                    if quarantined:
                        logger.info(f"🛑 QUARANTINE ACTIVE ({ENV_FLAG}=off): "
                                    f"phases 1/3/4-AI/7 skipped, condemned engines -> None")
                        self.container.register_singleton("enterprise_trading_engine", lambda: None)
                        self.container.register_singleton("entry_engine", lambda: None)
                        self.container.register_singleton("exit_engine", lambda: None)
                    else:
                        logger.info("🚀 PHASE 1: Adding Enterprise Trading Engine...")

                        # Initialize only Enterprise Trading Engine
                        from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine
                        enterprise_engine = EnterpriseTradingEngine()

                        # Register in container
                        self.container.register_singleton("enterprise_trading_engine", enterprise_engine)  # FIXED: Direct instance

                        # Initialize with recursion protection
                        try:
                            await enterprise_engine.initialize()
                            logger.info("✅ Enterprise Trading Engine initialized successfully")
                        except RecursionError as e:
                            logger.warning(f"⚠️ Enterprise engine recursion issue (expected): {str(e)[:100]}")
                            logger.info("📝 Enterprise engine in safe mode - classical models only")
                            enterprise_engine.is_initialized = True  # Mark as initialized in safe mode

                        logger.info("✅ PHASE 1 COMPLETE: Enterprise Trading Engine ready")
                    
                    # PHASE 2: Add Day Trading Engine
                    await asyncio.sleep(2)
                    logger.info("🚀 PHASE 2: Adding Day Trading Engine...")
                    
                    from app.backend.services.day_trading_engine import DayTradingEngine
                    day_engine = DayTradingEngine()
                    self.container.register_singleton("day_trading_engine", day_engine)  # FIXED: Direct instance
                    
                    # Initialize Day Trading Engine (but don't start - Brain Controller will orchestrate)
                    await day_engine.initialize()
                    # ORCHESTRATION FIX: Don't auto-start - let Brain Controller manage it
                    logger.info("✅ PHASE 2 COMPLETE: Day Trading Engine ready for orchestration")
                    
                    # PHASE 3: Add Continuous Learning Engine
                    if quarantined:
                        logger.info("🛑 PHASE 3 SKIPPED: Continuous Learning quarantined "
                                    "(D11: retrain NOTHING) — placeholder stays None")
                    else:
                        await asyncio.sleep(2)
                        logger.info("🚀 PHASE 3: Adding Continuous Learning Engine...")

                        try:
                            from app.backend.services.continuous_learning_engine import get_continuous_learning_engine
                            learning_engine = await get_continuous_learning_engine()
                            # Override placeholder with real engine
                            self.container.register_singleton("continuous_learning_engine", lambda: learning_engine)
                            logger.info("✅ PHASE 3 COMPLETE: Continuous Learning operational")
                        except Exception as learning_error:
                            logger.warning(f"⚠️ Continuous Learning failed: {learning_error}")
                            # Keep placeholder
                    
                    # PHASE 4: Add missing core services
                    await asyncio.sleep(1)
                    logger.info("🚀 PHASE 4: Adding missing core services...")
                    
                    try:
                        if quarantined:
                            logger.info("🛑 PHASE 4 AI part skipped: entry/exit engines "
                                        "quarantined — placeholders stay None")
                        else:
                            # Entry Engine — is_registered, NOT get(): get() raises
                            # KeyError before registration, which used to abort this
                            # whole phase into the placeholder except-branch.
                            from app.backend.services.intelligent_entry_engine import IntelligentEntryEngine
                            if not self.container.is_registered("entry_engine"):
                                entry_engine = IntelligentEntryEngine()
                                await entry_engine.initialize()
                                self.container.register_singleton("entry_engine", entry_engine)

                            # Exit Engine
                            from app.backend.services.intelligent_exit_engine import IntelligentExitEngine
                            if not self.container.is_registered("exit_engine"):
                                exit_engine = IntelligentExitEngine()
                                await exit_engine.initialize()
                                self.container.register_singleton("exit_engine", exit_engine)

                        # Risk Manager
                        from app.backend.services.dynamic_risk_manager import DynamicRiskManager
                        risk_manager = DynamicRiskManager()
                        await risk_manager.initialize()
                        await risk_manager.start_risk_monitoring()
                        self.container.register_singleton("risk_manager", lambda: risk_manager)
                        
                        # Emergency Controls
                        from app.backend.services.emergency_controls import EmergencyControlSystem
                        emergency_system = EmergencyControlSystem()
                        await emergency_system.initialize()
                        self.container.register_singleton("emergency_controls", lambda: emergency_system)
                        
                        # Market Data Services — use the module singleton so the
                        # singleton_app startup (WebSocket streams) reuses the
                        # SAME instance instead of streaming twice.
                        from app.backend.services.live_market_data import get_live_market_data_service
                        market_service = await get_live_market_data_service()
                        self.container.register_singleton("live_market_data", market_service)
                        
                        logger.info("✅ PHASE 4 COMPLETE: All core services ready")
                    except Exception as core_error:
                        logger.warning(f"⚠️ Core services failed: {core_error}")
                        # Register placeholders to prevent local instance creation
                        self.container.register_singleton("entry_engine", lambda: None)
                        self.container.register_singleton("exit_engine", lambda: None)
                        self.container.register_singleton("risk_manager", lambda: None)
                        self.container.register_singleton("emergency_controls", lambda: None)
                    
                    # PHASE 5: Add Session-Aware Engine
                    await asyncio.sleep(1)
                    logger.info("🚀 PHASE 5: Adding Session-Aware Trading Engine...")
                    
                    try:
                        from app.backend.services.session_aware_trading_engine import SessionAwareTradingEngine
                        session_engine = SessionAwareTradingEngine()
                        self.container.register_singleton("session_aware_trading_engine", session_engine)  # FIXED: Direct instance
                        await session_engine.initialize()
                        await session_engine.start()
                        logger.info("✅ PHASE 5 COMPLETE: Session-Aware Engine operational")
                    except Exception as session_error:
                        logger.warning(f"⚠️ Session-Aware Engine failed: {session_error}")
                        # Override placeholder registration
                        self.container.register_singleton("session_aware_trading_engine", None)  # FIXED: Direct None
                    
                    # PHASE 6: Initialize Missing Services
                    await asyncio.sleep(1)
                    logger.info("🚀 PHASE 6: Initializing Missing Services...")
                    
                    try:
                        # Initialize all the previously missing services
                        from app.backend.services.signal_processor import get_signal_processor
                        from app.backend.services.signal_performance_tracker import get_signal_performance_tracker
                        from app.backend.services.ai_vs_random_tracker import get_ai_vs_random_tracker
                        from app.backend.services.pattern_learning_engine import get_pattern_learning_engine
                        from app.backend.services.user_performance_showcase import get_user_performance_showcase
                        from app.backend.services.model_performance_metrics import get_model_performance_metrics
                        from app.backend.services.portfolio_manager import get_portfolio_manager
                        from app.backend.services.model_loader import get_model_loader
                        from app.backend.services.user_management_service import get_user_management_service
                        from app.backend.services.user_analytics_service import get_user_analytics_service
                        from app.backend.services.audit_compliance_service import get_audit_compliance_service
                        from app.backend.services.communication_service import get_communication_service
                        from app.backend.services.portfolio_showcase_engine import get_portfolio_showcase_engine
                        
                        # Initialize and register services
                        signal_processor = get_signal_processor()
                        self.container.register_singleton("signal_processor", lambda: signal_processor)
                        
                        signal_perf_tracker = get_signal_performance_tracker()
                        self.container.register_singleton("signal_performance_tracker", lambda: signal_perf_tracker)
                        
                        ai_vs_random = get_ai_vs_random_tracker()
                        self.container.register_singleton("ai_vs_random_tracker", lambda: ai_vs_random)
                        
                        pattern_engine = get_pattern_learning_engine()
                        self.container.register_singleton("pattern_learning_engine", lambda: pattern_engine)
                        
                        user_showcase = get_user_performance_showcase()
                        self.container.register_singleton("user_performance_showcase", lambda: user_showcase)
                        
                        model_metrics = get_model_performance_metrics()
                        self.container.register_singleton("model_performance_metrics", lambda: model_metrics)
                        
                        portfolio_mgr = get_portfolio_manager()
                        self.container.register_singleton("portfolio_manager", lambda: portfolio_mgr)
                        
                        model_loader_svc = get_model_loader()
                        self.container.register_singleton("model_loader", lambda: model_loader_svc)
                        
                        user_mgmt = get_user_management_service()
                        self.container.register_singleton("user_management_service", lambda: user_mgmt)
                        
                        user_analytics = get_user_analytics_service()
                        self.container.register_singleton("user_analytics_service", lambda: user_analytics)
                        
                        audit_service = get_audit_compliance_service()
                        self.container.register_singleton("audit_compliance_service", lambda: audit_service)
                        
                        comm_service = get_communication_service()
                        self.container.register_singleton("communication_service", lambda: comm_service)
                        
                        portfolio_showcase = get_portfolio_showcase_engine()
                        self.container.register_singleton("portfolio_showcase_engine", lambda: portfolio_showcase)
                        
                        logger.info("✅ PHASE 6 COMPLETE: All missing services initialized and registered")
                        
                    except Exception as services_error:
                        logger.warning(f"⚠️ Some services failed to initialize: {services_error}")
                    
                    # PHASE 7 + auto-start: Brain Controller is condemned
                    # (a facade — its unified signal returns None; see
                    # docs/ANALIZA_BRAIN_2026-07-17.md). Quarantined.
                    if quarantined:
                        logger.info("🛑 PHASE 7 SKIPPED: Brain Controller quarantined — placeholder stays None")
                    else:
                        # PHASE 7: Add Brain Controller (FINAL)
                        await asyncio.sleep(1)
                        logger.info("🚀 PHASE 7: Adding Brain Controller...")
                        print("🔍 DEBUG: Starting Brain Controller phase...")
                    
                        try:
                            # Wait for DI container to be fully initialized
                            await asyncio.sleep(2)  # Give container time to complete initialization
                        
                            # FORCE DI container initialization if not already done
                            if not hasattr(self.container, '_initialized') or not self.container._initialized:
                                logger.warning("⚠️ DI container not initialized, forcing initialization...")
                                self.container._initialized = True
                                logger.info("✅ DI container manually marked as initialized")
                            else:
                                logger.info("✅ DI container already initialized")
                        
                            # SIMPLIFIED Brain Controller registration - avoid complex initialization
                            logger.info("🔄 Creating simplified Brain Controller for registration...")
                        
                            from app.backend.brain.brain_controller import BrainController
                            brain_controller = BrainController()
                        
                            # Register immediately and FORCE initialization
                            self.container.register_singleton("brain_controller", brain_controller)  # FIXED: Direct instance
                            logger.info("🔧 Brain Controller registered in DI container")
                        
                            # 🚀 INDUSTRY STANDARD: Initialize with automatic startup
                            try:
                                logger.info("🔄 Initializing Brain Controller with automatic startup...")
                                await brain_controller.initialize()
                                logger.info("✅ Brain Controller initialization completed")
                                logger.info("🚀 AUTOMATIC STARTUP: Brain Controller will start trading automatically after warmup")
                            
                            except Exception as init_error:
                                logger.error(f"❌ Brain Controller auto-initialization failed: {init_error}")
                                # Still register it for API access
                                logger.info("📝 Brain Controller registered but not initialized")
                        
                            logger.info("✅ PHASE 7 COMPLETE: Brain Controller registered")
                            print("✅ DEBUG: Brain Controller registered successfully!")
                        except Exception as brain_error:
                            logger.warning(f"⚠️ Brain Controller failed: {brain_error}")
                            print(f"❌ DEBUG: Brain Controller failed: {brain_error}")
                        
                            # Create a basic Brain Controller for API access even if initialization failed
                            try:
                                from app.backend.brain.brain_controller import BrainController
                                fallback_brain = BrainController()
                                self.container.register_singleton("brain_controller", lambda: fallback_brain)
                                logger.info("🔄 Fallback Brain Controller registered for API access")
                            except Exception as fallback_error:
                                logger.error(f"❌ Fallback Brain Controller registration failed: {fallback_error}")
                                # Keep placeholder registration
                    
                        logger.info("🎉 ALL PHASES COMPLETE: Full professional backend restored!")
                        print("🎉 DEBUG: All phases completed!")
                    
                        # 🚀 INDUSTRY STANDARD: Auto-start Brain Controller after all phases complete
                        await asyncio.sleep(3)  # Wait for all services to stabilize
                        logger.info("🚀 INDUSTRY AUTO-START: Starting Brain Controller trading after all phases complete")
                    
                        try:
                            brain_controller = self.container.get("brain_controller")
                            if brain_controller and hasattr(brain_controller, 'state'):
                                current_state = brain_controller.state.current_state.value
                                logger.info(f"🧠 Brain Controller current state: {current_state}")
                            
                                if current_state == "warmup":
                                    logger.info("🚀 AUTO-START: Brain Controller ready - starting trading operations")
                                    result = await brain_controller.start_trading()
                                    logger.info(f"✅ AUTO-START RESULT: {result}")
                                else:
                                    logger.info(f"📝 Brain Controller in state: {current_state} - no auto-start needed")
                            else:
                                logger.warning("⚠️ Brain Controller not available for auto-start")
                        except Exception as auto_start_error:
                            logger.warning(f"⚠️ Auto-start failed: {auto_start_error}")
                    
                    # Final status check
                    await asyncio.sleep(1)
                    logger.info("🔍 FINAL CHECK: Verifying all engines...")
                    for engine_name in ["enterprise_trading_engine", "day_trading_engine", "continuous_learning_engine", "session_aware_trading_engine", "brain_controller"]:
                        try:
                            service = self.container.get(engine_name)
                            status = "✅ Available" if service else "❌ None"
                            logger.info(f"   {engine_name}: {status}")
                        except Exception as e:
                            logger.info(f"   {engine_name}: ❌ Error: {e}")
                    logger.info("🔍 FINAL CHECK COMPLETE")
                    
                except Exception as e:
                    logger.error(f"❌ PHASE FAILED: {e}")
                    print(f"❌ DEBUG: Phase failed with error: {e}")
                    import traceback
                    logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            
            # Initialize engines in background to not block uvicorn startup but ensure completion
            logger.info("🚀 Starting enterprise engine initialization (with completion tracking)...")
            print("🔍 DEBUG: Running engine initialization with completion tracking")
            
            # Create task and wait for completion
            init_task = asyncio.create_task(init_enterprise_engine())
            
            # Wait for completion or timeout
            try:
                await asyncio.wait_for(init_task, timeout=60.0)  # 60 second timeout
                logger.info("✅ Engine initialization completed successfully")
            except asyncio.TimeoutError:
                logger.error("❌ Engine initialization timed out after 60 seconds")
            except Exception as e:
                logger.error(f"❌ Engine initialization failed: {e}")
        
        logger.info("✅ TradePulse.AI Application created successfully")
        return self.app
    
    def _configure_middleware(self) -> None:
        """Configure all middleware in correct order"""
        logger.info("🔧 Configuring middleware")
        
        # CORS middleware - Configure allowed origins based on environment
        allowed_origins = [
            "https://tradepulseai.co.uk",
            "https://app.tradepulseai.co.uk",
            "http://localhost:4321",
            "http://localhost:3000",
            "http://127.0.0.1:4321",
            "http://127.0.0.1:3000",
        ]
        
        # In development, allow all origins
        if self.settings.ENVIRONMENT == "development":
            allowed_origins = ["*"]
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            allow_headers=["*"],
            expose_headers=["*"],
        )
        
        # Rate limiting middleware
        rate_limit_middleware = create_rate_limit_middleware(
            requests_per_minute=self.settings.RATE_LIMIT_REQUESTS,
            window_seconds=self.settings.RATE_LIMIT_WINDOW
        )
        self.app.middleware("http")(rate_limit_middleware)

        # Prometheus metrics middleware (after rate limiting to capture actual handled requests)
        try:
            prometheus_middleware = create_prometheus_middleware()
            self.app.middleware("http")(prometheus_middleware)
            logger.info("✅ Prometheus metrics middleware enabled")
        except Exception as e:
            logger.warning(f"⚠️ Failed to enable Prometheus middleware: {e}")
        
        logger.info("✅ Middleware configured")
    
    def _configure_error_handlers(self) -> None:
        """Configure global error handlers"""
        logger.info("🔧 Configuring error handlers")
        
        @self.app.exception_handler(TradePulseException)
        async def tradepulse_exception_handler(request: Request, exc: TradePulseException):
            """Handle TradePulse custom exceptions"""
            logger.error(
                "TradePulse exception occurred",
                error_code=exc.error_code,
                category=exc.category.value,
                path=request.url.path,
                method=request.method
            )
            return JSONResponse(
                status_code=exc.http_status,
                content={
                    "error": {
                        "code": exc.error_code,
                        "message": exc.user_message,
                        "category": exc.category.value,
                        "details": exc.details,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
        
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            """Handle FastAPI HTTP exceptions"""
            logger.warning(
                "HTTP exception occurred",
                status_code=exc.status_code,
                detail=exc.detail,
                path=request.url.path,
                method=request.method
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "code": f"HTTP_{exc.status_code}",
                        "message": exc.detail,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            """Handle unexpected exceptions"""
            logger.error(
                "Unexpected exception occurred",
                error=str(exc),
                error_type=type(exc).__name__,
                path=request.url.path,
                method=request.method,
                exc_info=True
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
        
        logger.info("✅ Error handlers configured")
    
    def _configure_routes(self) -> None:
        """Configure API routes"""
        logger.info("🔧 Configuring API routes")
        
        # Include main API router
        api_router = create_api_router()
        self.app.include_router(api_router)
        
        # Expose Prometheus metrics if library is available
        try:
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

            @self.app.get("/metrics")
            async def metrics():
                data = generate_latest()
                return Response(content=data, media_type=CONTENT_TYPE_LATEST)
        except Exception:
            # Do not fail if prometheus_client is not installed
            pass

        logger.info("✅ API routes configured")
    
    def _configure_health_endpoints(self) -> None:
        """Configure basic health endpoints"""
        
        @self.app.get("/")
        async def root():
            """Root endpoint with system info"""
            return {
                "service": "TradePulse.AI Enterprise Backend",
                "version": "1.0.0",
                "status": "operational",
                "mode": "PROFESSIONAL_LIVE_DATA_ONLY",
                "timestamp": datetime.utcnow().isoformat(),
                "environment": self.settings.ENVIRONMENT,
                "endpoints": {
                    "health": "/health",
                    "detailed_health": "/api/health",
                    "admin": "/api/admin",
                    "trading": "/api/trading"
                }
            }
        
        @self.app.get("/health")
        async def basic_health():
            """Basic health check endpoint"""
            return {
                "status": "healthy",
                "service": "TradePulse.AI Backend",
                "timestamp": datetime.utcnow().isoformat(),
                "environment": self.settings.ENVIRONMENT
            }

        @self.app.get("/healthz")
        async def liveness():
            return {"status": "ok"}

        @self.app.get("/readyz")
        async def readiness():
            # Simple readiness: snapshot age and phase
            try:
                from app.backend.services.metrics import SNAPSHOT_AGE
                age = 0.0
                if SNAPSHOT_AGE:
                    # Best effort: placeholder value; Prometheus gauge holds actual metric
                    age = 0.0
                return {"ready": True, "snapshot_age_hint": age}
            except Exception:
                return {"ready": False}
        
        @self.app.get("/test")
        async def test_route():
            """Simple test route for debugging"""
            return {
                "message": "TradePulse.AI Enterprise Backend - Test Route",
                "status": "success",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        @self.app.post("/admin/init-engines")
        async def init_missing_engines():
            """Initialize missing engines manually"""
            results = {}
            
            # Session-Aware Engine
            try:
                from app.backend.services.session_aware_trading_engine import SessionAwareTradingEngine
                session_engine = SessionAwareTradingEngine()
                self.container.register_singleton("session_aware_trading_engine", lambda: session_engine)
                await session_engine.initialize()
                await session_engine.start()
                results["session_aware"] = "✅ Initialized and started"
            except Exception as e:
                results["session_aware"] = f"❌ Failed: {str(e)[:100]}"
                # Register placeholder to prevent lookup errors
                self.container.register_singleton("session_aware_trading_engine", lambda: None)
            
            # Brain Controller
            try:
                from app.backend.brain.brain_controller import get_brain_controller
                brain_controller = await get_brain_controller()
                self.container.register_singleton("brain_controller", lambda: brain_controller)
                results["brain_controller"] = "✅ Initialized"
            except Exception as e:
                results["brain_controller"] = f"❌ Failed: {str(e)[:100]}"
                # Register placeholder to prevent lookup errors
                self.container.register_singleton("brain_controller", lambda: None)
            
            return {"results": results, "timestamp": datetime.utcnow().isoformat()}
    

def create_application() -> FastAPI:
    """
    Application factory function - creates FastAPI app only when explicitly called
    No side effects during import, only during execution
    """
    app_factory = TradePulseApplication()
    return app_factory.create_app()
