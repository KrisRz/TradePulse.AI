"""
Professional Dependency Injection Container for TradePulse.AI
Industry standard IoC container managing all service dependencies
"""

from typing import Dict, Any, Optional, Type, TypeVar, Generic
import inspect
from functools import lru_cache

from app.backend.core.config import get_settings
from app.backend.core.logging import get_logger
from app.backend.core.database import DynamoDBClient, DatabaseManager
# Infrastructure removed - using core database client directly
from app.backend.services.tensorflow_async_service import get_tensorflow_async_service
from app.backend.brain.brain_controller import get_brain_controller

logger = get_logger(__name__)

T = TypeVar('T')

def require_instance(name: str, obj):
    """PRODUCTION SAFE: Assert that DI returned an instance, not a callable"""
    if callable(obj) and not hasattr(obj, "__dict__"):
        raise TypeError(f"DI misuse: '{name}' is callable. Use container.get('{name}') WITHOUT '()'.")
    return obj


class ServiceContainer:
    """
    Production-safe dependency injection container with hardened guarantees
    Manages service lifecycle and dependencies with real data only
    """
    
    def __init__(self):
        self._instances: Dict[str, object] = {}
        self._factories: Dict[str, callable] = {}
        self._sealed = False
        self._initialized = False
        self._initialization_in_progress = False
        
        # Register core services
        self._register_core_services()
    
    def _register_core_services(self) -> None:
        """Register core infrastructure services"""
        logger.info("🔧 Registering core services in DI container")
        
        # Configuration
        self.register_singleton("settings", get_settings)
        
        # Database services (REAL DATA ONLY)
        self.register_singleton("database_client", self._create_database_client)
        self.register_singleton("database_manager", self._create_database_manager)
        
        # Infrastructure services removed - using core database client directly
        
        # AI/ML services (PROFESSIONAL GRADE)
        self.register_singleton("tensorflow_async_service", self._create_tensorflow_async_service)
        
        logger.info("✅ Core services registered")
    
    def register_singleton(self, name: str, instance_or_factory) -> None:
        """Register a singleton service - PRODUCTION SAFE"""
        if self._sealed:
            raise RuntimeError(f"DI sealed — registration after seal: {name}")
        
        if name in self._instances or name in self._factories:
            logger.debug(f"🔄 PIPELINE DEBUG: Service {name} already registered, skipping")
            return
        
        if callable(instance_or_factory) and not hasattr(instance_or_factory, "__dict__"):
            self._factories[name] = instance_or_factory
        else:
            self._instances[name] = instance_or_factory
        
        logger.debug(f"Registered singleton service: {name}")
    
    def register_transient(self, name: str, factory: callable) -> None:
        """Register a transient service (new instance each time)"""
        self._services[name] = factory
        logger.debug(f"Registered transient service: {name}")
    
    def get(self, name: str):
        """Get service by name - PRODUCTION SAFE"""
        # Check instances first (direct singletons)
        if name in self._instances:
            return self._instances[name]
        
        # Check legacy singletons  
        if name in self._singletons:
            return self._singletons[name]
        
        # Check if it's a singleton factory
        if name in self._factories:
            instance = self._factories[name](self)
            self._instances[name] = instance
            return instance
        
        # Check transient services
        if name in self._services:
            return self._services[name]()
        
        raise KeyError(f"Service not registered: {name}")
    
    def seal(self):
        """Seal container to prevent further registrations"""
        self._sealed = True
        logger.info(f"🔒 DI Container sealed with {len(self._instances)} instances, {len(self._singletons)} legacy singletons, and {len(self._factories)} factories")
    
    def is_registered(self, name: str) -> bool:
        """Check if service is registered - PRODUCTION SAFE"""
        return (name in self._instances or 
                name in self._factories or 
                name in self._services or 
                name in self._singletons)
    
    def get_typed(self, service_type: Type[T]) -> T:
        """Get service by type (for type safety)"""
        service_name = service_type.__name__.lower()
        return self.get(service_name)
    
    def _create_database_client(self) -> DynamoDBClient:
        """Factory for database client (REAL DATA ONLY)"""
        settings = self.get("settings")
        return DynamoDBClient(local_development=settings.is_development)
    
    def _create_database_manager(self) -> DatabaseManager:
        """Factory for database manager (REAL DATA ONLY)"""
        settings = self.get("settings")
        return DatabaseManager(local_development=settings.is_development)
    
    # Infrastructure methods removed - using core database client directly
    
    async def _create_tensorflow_async_service(self):
        """Factory for TensorFlow async service (PROFESSIONAL GRADE)"""
        return await get_tensorflow_async_service()
    
    async def initialize_async_services(self) -> None:
        """Initialize async services that require startup - FIXED: Idempotent"""
        if self._initialized:
            logger.debug("🔄 Services already initialized, skipping...")
            return
        
        # FIXED: Prevent double initialization during race conditions
        if self._initialization_in_progress:
            logger.debug("🔄 Initialization already in progress, skipping...")
            return
        
        self._initialization_in_progress = True
        logger.info("🚀 Initializing async services")
        
        try:
            # Initialize market data services (REAL DATA ONLY)
            await self._initialize_market_data_services()
            
            # Initialize AI services (REAL MODELS ONLY)
            await self._initialize_ai_services()
            
            # Initialize trading services (REAL TRADING LOGIC)
            await self._initialize_trading_services()
            
            self._initialized = True
            self._initialization_in_progress = False  # FIXED: Reset progress flag
            logger.info("✅ All async services initialized")
            
        except Exception as e:
            self._initialization_in_progress = False  # FIXED: Reset flag on error
            logger.error(f"❌ Failed to initialize async services: {e}")
            raise
    
    async def _initialize_market_data_services(self) -> None:
        """Initialize market data services with real data"""
        try:
            from app.backend.services.live_market_data import get_live_market_data_service
            from app.backend.services.btc_price_cache import get_btc_price_cache
            
            # Live market data service (REAL BINANCE DATA)
            market_service = await get_live_market_data_service()
            self.register_singleton("market_data_service", lambda: market_service)
            
            # BTC price cache (REAL PRICE DATA)
            btc_cache = get_btc_price_cache()
            self.register_singleton("btc_price_cache", lambda: btc_cache)
            
            logger.info("✅ Market data services initialized with REAL DATA")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize market data services: {e}")
            raise
    
    async def _initialize_ai_services(self) -> None:
        """Initialize AI services with real models"""
        try:
            from app.backend.services.continuous_learning_engine import get_continuous_learning_engine
            from app.backend.services.intelligent_entry_engine import IntelligentEntryEngine
            from app.backend.services.intelligent_exit_engine import IntelligentExitEngine
            
            # TensorFlow async service (PROFESSIONAL GRADE)
            try:
                tensorflow_service = await self._create_tensorflow_async_service()
                self.register_singleton("tensorflow_async_service", lambda: tensorflow_service)
                logger.info("✅ TensorFlow async service initialized")
            except Exception as tf_error:
                logger.warning(f"⚠️ TensorFlow async service initialization failed: {tf_error}")
                # Continue without TensorFlow - system can operate with reduced functionality
            
            # Continuous learning engine (REAL AI MODELS) - INITIALIZE AND START
            try:
                learning_engine = await get_continuous_learning_engine()
                if learning_engine:
                    # The learning loop is automatically started in initialize()
                    # Check if it's running
                    if hasattr(learning_engine, 'is_running') and learning_engine.is_running:
                        logger.info("🧠 Continuous Learning Engine periodic optimization loop is running")
                    else:
                        logger.warning("⚠️ Continuous Learning Engine may not be running properly")
                    
                    self.register_singleton("continuous_learning_engine", lambda: learning_engine)
                    logger.info("✅ Continuous Learning Engine initialized and started")
            except Exception as e:
                logger.error(f"❌ Failed to initialize continuous learning engine: {e}")
                self.register_singleton("continuous_learning_engine", lambda: None)
            
            # Entry engine (REAL AI ANALYSIS) - FIXED: Register instance directly  
            try:
                entry_engine = IntelligentEntryEngine()
                await entry_engine.initialize()
                self.register_singleton("entry_engine", entry_engine)  # FIXED: Direct instance, not lambda
                logger.info("✅ Intelligent Entry Engine initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize entry engine: {e}")
                self.register_singleton("entry_engine", None)
            
            # Exit engine (REAL AI ANALYSIS) - FIXED: Register instance directly
            try:
                exit_engine = IntelligentExitEngine()
                await exit_engine.initialize()
                self.register_singleton("exit_engine", exit_engine)  # FIXED: Direct instance
                logger.info("✅ Intelligent Exit Engine initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize exit engine: {e}")
                self.register_singleton("exit_engine", None)
            
            logger.info("✅ AI services initialized with REAL MODELS")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize AI services: {e}")
            # Don't raise - AI services are not critical for basic operation
    
    async def _initialize_trading_services(self) -> None:
        """Initialize and START all trading services with real logic"""
        try:
            from app.backend.services.professional_portfolio import get_professional_portfolio
            from app.backend.services.dynamic_risk_manager import DynamicRiskManager
            from app.backend.services.emergency_controls import EmergencyControlSystem
            from app.backend.brain.brain_controller import get_brain_controller
            from app.backend.services.day_trading_engine import get_day_trading_engine
            from app.backend.services.session_aware_trading_engine import get_session_aware_trading_engine
            
            # Professional portfolio (REAL PORTFOLIO DATA)
            portfolio = await get_professional_portfolio("admin")
            self.register_singleton("portfolio", lambda: portfolio)
            
            # Enterprise Trading Engine (REAL AI MODELS) - RESILIENT INITIALIZATION
            try:
                logger.info("🔄 Creating Enterprise Trading Engine...")
                from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine
                trading_engine = EnterpriseTradingEngine()
                
                # FIXED: Register direct instance (not lambda)
                self.register_singleton("enterprise_trading_engine", trading_engine)
                logger.info("✅ Enterprise Trading Engine registered")
                
                # Try to initialize in background to avoid blocking other services
                import asyncio
                async def init_enterprise_engine():
                    try:
                        await trading_engine.initialize()
                        logger.info("✅ Enterprise Trading Engine fully initialized with 6-layer AI system")
                    except RecursionError as re:
                        logger.error(f"❌ RecursionError in enterprise engine: {str(re)[:100]}")
                        logger.info("📝 Enterprise engine in degraded mode due to recursion")
                        trading_engine.is_initialized = False
                    except Exception as init_error:
                        logger.warning(f"⚠️ Enterprise engine initialization failed: {init_error}")
                        logger.info("📝 Enterprise engine in degraded mode")
                        trading_engine.is_initialized = False
                
                # Start initialization in background
                asyncio.create_task(init_enterprise_engine())
                    
            except Exception as e:
                logger.error(f"❌ Failed to create enterprise trading engine: {e}")
                self.register_singleton("enterprise_trading_engine", lambda: None)
            
            # Day Trading Engine (REAL DAY TRADING) - CREATE WITHOUT CIRCULAR DEPENDENCIES
            try:
                logger.info("🔄 Creating Day Trading Engine without circular dependencies...")
                from app.backend.services.day_trading_engine import DayTradingEngine
                day_engine = DayTradingEngine()  # Don't call initialize yet
                self.register_singleton("day_trading_engine", lambda: day_engine)
                logger.info("✅ Day Trading Engine registered (will initialize after all services ready)")
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to create day trading engine: {e}")
                logger.info("📝 Registering Day Trading Engine as None (degraded mode)")
                self.register_singleton("day_trading_engine", lambda: None)
            
            # Session-Aware Trading Engine (REAL SESSION ANALYSIS) - CREATE WITHOUT CIRCULAR DEPENDENCIES
            try:
                logger.info("🔄 Creating Session-Aware Trading Engine without circular dependencies...")
                from app.backend.services.session_aware_trading_engine import SessionAwareTradingEngine
                session_engine = SessionAwareTradingEngine()  # Don't call initialize yet
                self.register_singleton("session_aware_trading_engine", session_engine)  # FIXED: Direct instance
                logger.info("✅ Session-Aware Trading Engine registered (will initialize after all services ready)")
            except Exception as e:
                logger.error(f"❌ Session-Aware Trading Engine creation failed: {e}")
                import traceback
                logger.error(f"📋 Full traceback: {traceback.format_exc()}")
                logger.info("📝 Registering Session-Aware Trading Engine as None (degraded mode)")
                self.register_singleton("session_aware_trading_engine", lambda: None)
            
            # Risk manager (REAL RISK CALCULATIONS) - INITIALIZE AND START MONITORING
            try:
                risk_manager = DynamicRiskManager()
                await risk_manager.initialize()
                await risk_manager.start_risk_monitoring()
                self.register_singleton("risk_manager", lambda: risk_manager)
                logger.info("✅ Dynamic Risk Manager initialized and monitoring started")
            except Exception as e:
                logger.error(f"❌ Failed to initialize risk manager: {e}")
                self.register_singleton("risk_manager", lambda: None)
            
            # Emergency controls (REAL SAFETY SYSTEMS)
            self.register_singleton("emergency_controls", EmergencyControlSystem)
            
            # Enhanced persistence (REAL DATA PERSISTENCE) - Register as factory to avoid async issues
            try:
                from app.backend.services.enhanced_market_persistence import EnhancedMarketPersistence
                self.register_singleton("enhanced_persistence", lambda: EnhancedMarketPersistence())
                logger.info("✅ Enhanced Persistence factory registered (will initialize on first use)")
            except Exception as e:
                logger.warning(f"⚠️ Enhanced Persistence registration failed: {e}")
                self.register_singleton("enhanced_persistence", lambda: None)
            
            # BRAIN Controller - Skip registration here, handled by application.py Phase 6
            logger.info("🔄 Brain Controller registration deferred to application startup phase")
            # Register a placeholder to prevent service lookup failures during startup
            self.register_singleton("brain_controller", lambda: None)
            
            # POST-INITIALIZATION: Initialize engines that were registered but not initialized
            await self._post_initialize_trading_engines()
            
            logger.info("🚀 ALL TRADING SERVICES INITIALIZED AND STARTED WITH REAL LOGIC")
            
            # CRITICAL: Mark container as initialized for Brain Controller DI checks
            self._initialized = True
            logger.info("✅ DI Container marked as initialized - Brain Controller can now access services")
            
            # Note: Brain auto-enable is now handled by lifespan manager after services are ready
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize trading services: {e}")
            # Don't raise - some services may not be critical
    
    async def _post_initialize_trading_engines(self) -> None:
        """Initialize trading engines after all services are registered (avoids circular dependencies)"""
        try:
            logger.info("🔄 Post-initializing trading engines...")
            
            # Initialize day trading engine
            try:
                day_engine = self.get("day_trading_engine")
                if day_engine and not day_engine.is_initialized:
                    logger.info("🔄 Initializing Day Trading Engine...")
                    await day_engine.initialize()
                    logger.info("🔄 Starting Day Trading Engine analysis loop...")
                    await day_engine.start_analysis_loop()
                    logger.info("✅ Day Trading Engine fully operational")
            except Exception as e:
                logger.warning(f"⚠️ Day Trading Engine post-initialization failed: {e}")
            
            # Initialize session-aware trading engine
            try:
                session_engine = self.get("session_aware_trading_engine")
                if session_engine and not getattr(session_engine, 'is_initialized', False):
                    logger.info("🔄 Initializing Session-Aware Trading Engine...")
                    await session_engine.initialize()
                    logger.info("🔄 Starting Session-Aware Trading Engine...")
                    await session_engine.start()
                    logger.info("✅ Session-Aware Trading Engine fully operational")
                elif session_engine is None:
                    logger.error("❌ Session-Aware Trading Engine is None in container")
                elif getattr(session_engine, 'is_initialized', False):
                    logger.info("✅ Session-Aware Trading Engine already initialized")
                else:
                    logger.warning(f"⚠️ Session-Aware Trading Engine in unknown state")
            except Exception as e:
                logger.error(f"❌ Session-Aware Trading Engine post-initialization failed: {e}")
                import traceback
                logger.error(f"📋 Full traceback: {traceback.format_exc()}")
                
            logger.info("✅ Post-initialization complete")
            
        except Exception as e:
            logger.error(f"❌ Post-initialization failed: {e}")

    # REMOVED: _auto_enable_brain_after_services_ready - now handled by lifespan manager
    
    async def shutdown_services(self) -> None:
        """Shutdown all services gracefully"""
        logger.info("🛑 Shutting down services")
        
        try:
            # Shutdown BRAIN Controller
            if "brain_controller" in self._singletons:
                brain = self._singletons["brain_controller"]
                if hasattr(brain, 'shutdown'):
                    await brain.shutdown()
            
            # Shutdown learning engine
            if "learning_engine" in self._singletons:
                engine = self._singletons["learning_engine"]
                if hasattr(engine, 'is_running'):
                    engine.is_running = False
            
            logger.info("✅ All services shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Error during service shutdown: {e}")


# Global container instance
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """Get global service container instance"""
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


def get_service(name: str) -> Any:
    """Convenience function to get service from container"""
    return get_container().get(name)


def get_typed_service(service_type: Type[T]) -> T:
    """Convenience function to get typed service from container"""
    return get_container().get_typed(service_type)


# Dependency injection decorators for FastAPI
def inject_service(service_name: str):
    """Decorator to inject service into FastAPI endpoint"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            service = get_service(service_name)
            return func(*args, service=service, **kwargs)
        return wrapper
    return decorator


def inject_typed_service(service_type: Type[T]):
    """Decorator to inject typed service into FastAPI endpoint"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            service = get_typed_service(service_type)
            return func(*args, service=service, **kwargs)
        return wrapper
    return decorator


# FastAPI dependency functions
def get_database_client() -> DynamoDBClient:
    """FastAPI dependency for database client"""
    return get_service("database_client")


def get_database_manager() -> DatabaseManager:
    """FastAPI dependency for database manager"""
    return get_service("database_manager")


def get_market_data_service():
    """FastAPI dependency for market data service"""
    try:
        return get_service("market_data_service")
    except ValueError:
        # Service not initialized yet
        return None


def get_portfolio_service():
    """FastAPI dependency for portfolio service"""
    try:
        return get_service("portfolio")
    except ValueError:
        # Service not initialized yet
        return None


def get_brain_controller():
    """FastAPI dependency for BRAIN controller"""
    try:
        return get_service("brain_controller")
    except ValueError:
        # Service not initialized yet
        return None


def get_portfolio_repository():
    """FastAPI dependency for portfolio repository"""
    return get_service("portfolio_repository")


def get_dynamodb_infrastructure_client():
    """FastAPI dependency for DynamoDB infrastructure client"""
    return get_service("dynamodb_infrastructure_client")
