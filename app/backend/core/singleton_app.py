"""
TradePulse.AI - Singleton Trading App with Lease Guard
Ensures only one instance runs trading brain during rolling deploys
"""

import asyncio
import contextlib
import logging
import signal
from typing import Optional

from fastapi import FastAPI

from app.backend.core.lease_guard import get_lease_guard
from app.backend.core.config import get_settings
from app.backend.core.heartbeat import get_heartbeat_service

logger = logging.getLogger(__name__)

class SingletonTradingApp:
    """
    Singleton wrapper for TradePulse.AI trading application
    Handles lease-based trading brain management
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.lease_guard = get_lease_guard()
        self.heartbeat_service = get_heartbeat_service()
        self.is_ready = False
        self.models_loaded = False
        self.ddb_connected = False
        self._trading_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        
    async def startup(self):
        """Startup sequence with lease acquisition"""
        try:
            logger.info("🚀 TradePulse.AI Singleton App - Starting up...")
            # Sanitize any stray static AWS credentials that could override instance role
            try:
                import os
                removed_keys = []
                for key in (
                    "AWS_ACCESS_KEY_ID",
                    "AWS_SECRET_ACCESS_KEY",
                    "AWS_SESSION_TOKEN",
                    "AWS_PROFILE",
                    "AWS_SHARED_CREDENTIALS_FILE",
                    "AWS_CONFIG_FILE",
                ):
                    if os.environ.pop(key, None) is not None:
                        removed_keys.append(key)
                if removed_keys:
                    logger.warning(
                        "Removed conflicting AWS_* environment variables to prefer instance role",
                        extra={"removed": removed_keys},
                    )
            except Exception:
                pass
            # Diagnostics: log AWS identity and environment to verify credentials source
            try:
                import boto3  # local import to avoid global dependency at import-time
                import os
                sts = boto3.client("sts", region_name=self.settings.AWS_REGION)
                # Diagnostics: which provider is used and what AWS_* vars exist (names only)
                try:
                    session = boto3.Session()
                    creds = session.get_credentials()
                    provider = getattr(creds, "method", "unknown") if creds else "none"
                    aws_env_keys = [k for k in os.environ.keys() if k.startswith("AWS_")]
                    logger.info(
                        "🔎 AWS credentials chain",
                        extra={
                            "provider": provider,
                            "aws_env_keys": aws_env_keys,
                        },
                    )
                except Exception:
                    pass
                identity = sts.get_caller_identity()
                logger.info(
                    "🔐 AWS identity resolved",
                    extra={
                        "arn": identity.get("Arn"),
                        "account": identity.get("Account"),
                        "region": self.settings.AWS_REGION,
                        "environment": self.settings.ENVIRONMENT,
                        "is_development": self.settings.is_development,
                    },
                )
            except Exception as diag_err:
                logger.warning(f"AWS identity diagnostic failed: {diag_err}")
            
            # Step 1: Load ML models
            await self._load_models()
            
            # Step 2: Check DynamoDB connectivity
            await self._check_database_connectivity()
            
            # Step 3: Try to acquire trading brain lease
            lease_acquired = await self.lease_guard.try_acquire_lease()
            
            if lease_acquired:
                logger.info("✅ Acquired trading brain lease - Starting trading loop")
                await self._start_trading_brain()
                
                # Emit startup metric to CloudWatch
                await self.heartbeat_service.emit_startup_metric()
            else:
                logger.info("🔒 Another instance holds the lease - Running in API-only mode")
            
            # Don't mark ready until DB connectivity confirmed
            # API will serve /health immediately; /ready depends on flags
            logger.info("✅ TradePulse.AI startup sequence completed (awaiting readiness flags)")
            
        except Exception as e:
            logger.error(f"❌ Startup failed: {e}")
            raise
    
    async def shutdown(self):
        """Graceful shutdown with lease release"""
        try:
            logger.info("🛑 TradePulse.AI Singleton App - Shutting down...")
            
            # Emit shutdown metric
            await self.heartbeat_service.emit_shutdown_metric()
            
            # Stop heartbeat service
            if self._heartbeat_task and not self._heartbeat_task.done():
                self.heartbeat_service.stop()
                self._heartbeat_task.cancel()
                
                with contextlib.suppress(asyncio.CancelledError):
                    await self._heartbeat_task
            
            # Stop trading brain if running
            if self._trading_task and not self._trading_task.done():
                logger.info("⏹️ Stopping trading brain loop...")
                self._trading_task.cancel()
                
                with contextlib.suppress(asyncio.CancelledError):
                    await self._trading_task
                
                logger.info("✅ Trading brain loop stopped")
            
            # Release lease
            await self.lease_guard.release_lease()
            
            # Close WebSocket connections gracefully
            await self._close_websocket_connections()
            
            logger.info("✅ Graceful shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Shutdown error: {e}")
    
    async def _load_models(self):
        """Load ML models (lazy loading)"""
        try:
            logger.info("🤖 Loading ML models...")
            
            # Import here to avoid circular imports
            from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine
            
            # Initialize enterprise engine (loads models)
            engine = EnterpriseTradingEngine()
            await engine.initialize()
            
            self.models_loaded = True
            logger.info("✅ ML models loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load ML models: {e}")
            # Don't fail startup - models can be loaded later
            self.models_loaded = False
    
    async def _check_database_connectivity(self):
        """Check DynamoDB connectivity"""
        try:
            logger.info("🗄️ Checking DynamoDB connectivity...")
            
            # Simple connectivity test
            import boto3
            from botocore.exceptions import ClientError
            
            # Use explicit region and let boto3 use instance role credentials
            ddb = boto3.client(
                "dynamodb",
                region_name=self.settings.AWS_REGION,
                endpoint_url=self.settings.DYNAMODB_ENDPOINT if self.settings.is_development else None
            )
            
            # List tables to test connectivity
            response = ddb.list_tables()
            
            self.ddb_connected = True
            logger.info(f"✅ DynamoDB connected - Found {len(response.get('TableNames', []))} tables")
            
        except Exception as e:
            # Do NOT crash the process during startup; health must come up fast.
            # We'll report not-ready via /ready while continuing to serve /health.
            logger.error(f"❌ DynamoDB connectivity failed: {e}")
            self.ddb_connected = False
            # Intentionally not raising here to let the app start and pass health checks
    
    async def _start_trading_brain(self):
        """Start the trading brain loop"""
        try:
            # Import here to avoid circular imports during startup
            from app.backend.api.v1.routes.trading import trading_brain_loop
            
            # Start trading brain as background task
            self._trading_task = asyncio.create_task(trading_brain_loop())
            logger.info("🧠 Trading brain loop started as background task")
            
            # Start CloudWatch heartbeat loop
            self._heartbeat_task = asyncio.create_task(
                self.heartbeat_service.heartbeat_loop(self.lease_guard)
            )
            logger.info("💓 CloudWatch heartbeat loop started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start trading brain: {e}")
            raise
    
    # Removed _heartbeat_loop - now handled by CloudWatchHeartbeat service
    
    async def _close_websocket_connections(self):
        """Close WebSocket connections gracefully"""
        try:
            # Import and close live market data service
            from app.backend.services.live_market_data import get_live_market_data_service
            
            service = await get_live_market_data_service()
            if service.is_running:
                await service.stop()
                logger.info("✅ WebSocket connections closed")
                
        except Exception as e:
            logger.debug(f"WebSocket close error: {e}")
    
    def health_status(self) -> dict:
        """Get health status for /health endpoint"""
        return {
            "status": "healthy",
            "timestamp": self.settings.get_current_timestamp(),
            "instance_id": self.lease_guard.instance_id,
        }
    
    def readiness_status(self) -> tuple[dict, int]:
        """
        Get readiness status for /ready endpoint
        Returns 200 if ready to serve API traffic (models + DB OK)
        Lease status is informational only - API should work without lease
        """
        # Ready = models loaded + database connected
        # Lease is optional - instance can serve API without lease
        is_ready = (
            self.is_ready and 
            self.models_loaded and 
            self.ddb_connected
        )
        
        status = {
            "ready": is_ready,
            "models_loaded": self.models_loaded,
            "database_connected": self.ddb_connected,
            "is_trading_leader": self.lease_guard.is_leader,
            "lease_status": self.lease_guard.get_status(),
            "note": "API ready even without lease - only trading brain requires lease"
        }
        
        return status, 200 if is_ready else 503

# Global singleton instance
_singleton_app: Optional[SingletonTradingApp] = None

def get_singleton_app() -> SingletonTradingApp:
    """Get or create the singleton trading app"""
    global _singleton_app
    if _singleton_app is None:
        _singleton_app = SingletonTradingApp()
    return _singleton_app

def setup_lifespan_handlers(app: FastAPI):
    """Setup FastAPI lifespan event handlers"""
    singleton_app = get_singleton_app()
    
    @app.on_event("startup")
    async def startup_event():
        """FastAPI startup event"""
        await singleton_app.startup()
    
    @app.on_event("shutdown") 
    async def shutdown_event():
        """FastAPI shutdown event"""
        await singleton_app.shutdown()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        """Handle SIGTERM for graceful shutdown"""
        logger.info(f"Received signal {signum} - initiating graceful shutdown")
        # Let FastAPI handle the shutdown
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
