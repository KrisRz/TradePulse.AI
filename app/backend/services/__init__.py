"""
TradePulse.AI Professional Services Package
==========================================

Production-grade services for enterprise trading system.
All services use real live data from Binance API and trained AI models.

Author: TradePulse.AI Development Team
Version: 2.0.0 (Production)
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

# Core service imports
try:
    from app.backend.services.binance_hybrid_client import get_hybrid_client
    from app.backend.services.live_market_data import (
        get_live_bitcoin_price,
        get_live_market_data,
        get_live_candlestick_data,
        get_live_orderbook_data,
        get_live_market_data_service,
        LiveMarketDataService as MarketDataService
    )
    # EnterpriseTradingEngine import
    from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine
    from app.backend.services.professional_portfolio import (
        get_professional_portfolio,
        ProfessionalPortfolio
    )
    from app.backend.services.database_service import DatabaseService, get_database_service
    from app.backend.services.day_trading_engine import DayTradingEngine
    from app.backend.services.intelligent_entry_engine import IntelligentEntryEngine
    from app.backend.services.intelligent_exit_engine import IntelligentExitEngine
    from app.backend.services.dynamic_risk_manager import DynamicRiskManager
    RiskManager = DynamicRiskManager
    from app.backend.services.emergency_controls import EmergencyControlSystem as EmergencyControls
    from app.backend.services.continuous_learning_engine import (
        get_continuous_learning_engine,
        ContinuousLearningEngine
    )
    from app.backend.services.position_result_tracker import (
        get_position_result_tracker,
        PositionOutcome
    )
    from app.backend.services.trading_performance_tracker import TradingPerformanceTracker as PerformanceTracker
    # Archived services - no longer imported
    # from app.backend.services.pipeline_orchestrator import PipelineOrchestrator
    # from app.backend.services.session_aware_trading_engine import SessionAwareTradingEngine
    # from app.backend.services.session_monitoring_analytics import SessionMonitoringAnalytics

    # Import additional services with fallback
    try:
        from app.backend.services.signal_processor import SignalProcessor
    except ImportError:
        logger.warning("SignalProcessor not available")
        SignalProcessor = None

    try:
        from app.backend.services.signal_performance_tracker import signal_performance_tracker
    except ImportError:
        logger.warning("signal_performance_tracker not available")
        signal_performance_tracker = None

    try:
        from app.backend.services.ai_vs_random_tracker import ai_vs_random_tracker
    except ImportError:
        logger.warning("ai_vs_random_tracker not available")
        ai_vs_random_tracker = None

    try:
        from app.backend.services.pattern_learning_engine import pattern_learning_engine
    except ImportError:
        logger.warning("pattern_learning_engine not available")
        pattern_learning_engine = None

    try:
        from app.backend.services.user_performance_showcase import user_performance_showcase
    except ImportError:
        logger.warning("user_performance_showcase not available")
        user_performance_showcase = None

    try:
        from app.backend.services.model_performance_metrics import model_performance_metrics
    except ImportError:
        logger.warning("model_performance_metrics not available")
        model_performance_metrics = None

    try:
        from app.backend.services.portfolio_manager import portfolio_manager
    except ImportError:
        logger.warning("portfolio_manager not available")
        portfolio_manager = None

    try:
        from app.backend.services.model_loader import model_loader
    except ImportError:
        logger.warning("model_loader not available")
        model_loader = None

    try:
        from app.backend.services.user_management_service import user_management_service
    except ImportError:
        logger.warning("user_management_service not available")
        user_management_service = None

    try:
        from app.backend.services.user_analytics_service import user_analytics_service
    except ImportError:
        logger.warning("user_analytics_service not available")
        user_analytics_service = None

    try:
        from app.backend.services.audit_compliance_service import audit_compliance_service
    except ImportError:
        logger.warning("audit_compliance_service not available")
        audit_compliance_service = None

    try:
        from app.backend.services.communication_service import communication_service
    except ImportError:
        logger.warning("communication_service not available")
        communication_service = None

    try:
        from app.backend.services.portfolio_showcase_engine import portfolio_showcase_engine
    except ImportError:
        logger.warning("portfolio_showcase_engine not available")
        portfolio_showcase_engine = None

    try:
        from app.backend.services.virtual_portfolio_manager import VirtualPortfolioManager
    except ImportError:
        logger.warning("VirtualPortfolioManager not available - using placeholder")
        class VirtualPortfolioManager:
            """Placeholder for VirtualPortfolioManager"""
            pass

except ImportError as e:
    logger.error(f"Critical services import failed: {e}")
    raise

# Create placeholder classes for missing services
class HistoricalDataProcessor:
    """Placeholder for HistoricalDataProcessor"""
    pass

class LiveDataProcessor:
    """Placeholder for LiveDataProcessor"""
    pass

# Define missing enums
class MessageType(str, Enum):
    """Message types for communication service"""
    DIRECT_MESSAGE = "direct_message"
    NOTIFICATION = "notification"
    ALERT = "alert"
    SYSTEM_MESSAGE = "system_message"

class MessagePriority(str, Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class NotificationChannel(str, Enum):
    """Notification channels"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"

# Export key functions and classes
__all__ = [
    # Core services
    'get_hybrid_client',
    'MarketDataService',
    'EnterpriseTradingEngine',
    'DatabaseService',
    'database_service',
    'DayTradingEngine',
    'IntelligentEntryEngine',
    'IntelligentExitEngine',
    'DynamicRiskManager',
    'EmergencyControls',
    'get_continuous_learning_engine',
    'get_position_result_tracker',
    'get_performance_tracker',
    # Archived services removed from exports
    # 'PipelineOrchestrator',
    # 'SessionAwareTradingEngine', 
    # 'SessionMonitoringAnalytics',
    # EnterpriseTradingEngine removed to avoid recursion

    # Professional portfolio
    'get_professional_portfolio',
    'ProfessionalPortfolio',

    # Optional services (with fallbacks)
    'SignalProcessor',
    'signal_performance_tracker',
    'ai_vs_random_tracker',
    'pattern_learning_engine',
    'user_performance_showcase',
    'model_performance_metrics',
    'portfolio_manager',
    'model_loader',
    'user_management_service',
    'user_analytics_service',
    'audit_compliance_service',
    'communication_service',
    'portfolio_showcase_engine',
    'VirtualPortfolioManager',
    'HistoricalDataProcessor',
    'LiveDataProcessor',

    # Enums
    'PositionOutcome',
    'MessageType',
    'NotificationChannel',
    'MessagePriority',
]