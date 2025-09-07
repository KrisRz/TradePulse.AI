"""
Professional API Router for TradePulse.AI
Centralized routing configuration preserving ALL existing functionality
"""

from fastapi import APIRouter

from app.backend.core.logging import get_logger

# Import ALL existing routes to preserve functionality
from app.backend.api.v1.routes import (
    trading, health, portfolio, admin_runtime, auth, metrics,
    enterprise, signals, admin, user_management, user_analytics,
    communication, analytics, notifications, learning, system_control,
    enterprise_admin, real_trading, simple_signals, market, user_portfolio, engines_status, user_invitations, admin_users, admin_system
)
from app.backend.api import trading_signals

logger = get_logger(__name__)


def create_api_router() -> APIRouter:
    """
    Create main API router with ALL existing routes
    Preserves complete functionality while organizing routes professionally
    """
    logger.info("🔧 Creating API router with all existing routes")
    
    # Create main API router
    main_router = APIRouter()
    
    # Core trading functionality (REAL DATA ONLY)
    main_router.include_router(
        trading.router,
        prefix="/api/trading",
        tags=["trading"]
    )
    
    # Health and monitoring endpoints
    main_router.include_router(
        health.router,
        prefix="/api",
        tags=["health"]
    )
    
    # Market data endpoints (REAL DATA ONLY)
    main_router.include_router(
        market.router,
        prefix="/api/v1/market",
        tags=["market"]
    )
    
    main_router.include_router(
        metrics.router,
        prefix="/api",
        tags=["metrics"]
    )
    
    # Portfolio management (REAL DATA ONLY)
    main_router.include_router(
        portfolio.router,
        prefix="/api/portfolio",
        tags=["portfolio"]
    )
    
    # User portfolio endpoints (REAL DATA ONLY)
    main_router.include_router(
        user_portfolio.router,
        prefix="/api/user/portfolio",
        tags=["user-portfolio"]
    )
    
    # User dashboard endpoints (REAL DATA ONLY)
    main_router.include_router(
        user_portfolio.router,
        prefix="/api/user",
        tags=["user-dashboard"]
    )
    
    # Authentication and authorization
    main_router.include_router(
        auth.router,
        prefix="/api/auth",
        tags=["auth"]
    )
    
    # Authentication with v1 prefix (for compatibility)
    main_router.include_router(
        auth.router,
        prefix="/api/v1/auth",
        tags=["auth-v1"]
    )
    
    # Engine Status Monitoring (REAL ENGINE STATUS)
    main_router.include_router(
        engines_status.router,
        prefix="/api/v1",
        tags=["engines-status"]
    )
    
    # Admin and runtime configuration
    main_router.include_router(
        admin_runtime.router,
        prefix="/api",
        tags=["admin-runtime"]
    )
    
    main_router.include_router(
        admin.router,
        prefix="/api/admin",
        tags=["admin"]
    )
    
    # User management (admin_users.py has user status/role endpoints)
    main_router.include_router(
        admin_users.router,
        prefix="/api/admin",
        tags=["admin-users"]
    )
    
    # User management (user_management.py - legacy)
    main_router.include_router(
        user_management.router,
        prefix="/api/user-management-legacy",
        tags=["user-management-legacy"]
    )
    
    # User invitation system
    main_router.include_router(
        user_invitations.router,
        prefix="/api/user-management",
        tags=["user-invitations"]
    )
    
    # Admin system management
    main_router.include_router(
        admin_system.router,
        prefix="/api/admin/system",
        tags=["admin-system"]
    )
    
    main_router.include_router(
        user_analytics.router,
        prefix="/api/analytics/admin",
        tags=["user-analytics"]
    )
    
    # Communication system
    main_router.include_router(
        communication.router,
        prefix="/api/admin/communications",
        tags=["communication"]
    )
    
    # Analytics and reporting (REAL DATA ONLY)
    main_router.include_router(
        analytics.router,
        prefix="/api/analytics",
        tags=["analytics"]
    )
    
    # Notifications
    main_router.include_router(
        notifications.router,
        prefix="/api/notifications",
        tags=["notifications"]
    )
    
    # Learning and AI systems (REAL MODELS ONLY)
    main_router.include_router(
        learning.router,
        prefix="/api",
        tags=["learning"]
    )
    
    # System control
    main_router.include_router(
        system_control.router,
        prefix="/api",
        tags=["system"]
    )
    
    # Enterprise features (REAL DATA ONLY)
    main_router.include_router(
        enterprise.router,
        prefix="/api/enterprise",
        tags=["enterprise"]
    )
    
    main_router.include_router(
        enterprise_admin.router,
        prefix="/api/enterprise-admin",
        tags=["enterprise-admin"]
    )
    
    # Real trading endpoints (LIVE DATA ONLY)
    main_router.include_router(
        real_trading.router,
        prefix="/api/real_trading",
        tags=["real-trading"]
    )
    
    # Trading signals (REAL ANALYSIS ONLY)
    main_router.include_router(
        simple_signals.router,
        prefix="/api/trading/signals",
        tags=["signals"]
    )
    
    # Professional trading signals with TP/SL levels
    main_router.include_router(trading_signals.router)
    
    # Signals aggregation APIs - ENABLED for market intelligence
    main_router.include_router(signals.router, prefix="/api/signals", tags=["signals"])
    
    logger.info("✅ API router created with all existing routes preserved")
    return main_router


def get_route_summary() -> dict:
    """
    Get summary of all configured routes
    Useful for debugging and documentation
    """
    router = create_api_router()
    
    routes_summary = {
        "total_routes": len(router.routes),
        "route_paths": [],
        "tags": set()
    }
    
    for route in router.routes:
        if hasattr(route, 'path'):
            routes_summary["route_paths"].append({
                "path": route.path,
                "methods": getattr(route, 'methods', []),
                "name": getattr(route, 'name', 'unknown')
            })
        
        if hasattr(route, 'tags'):
            routes_summary["tags"].update(route.tags or [])
    
    routes_summary["tags"] = list(routes_summary["tags"])
    
    return routes_summary
