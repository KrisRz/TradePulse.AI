"""
Dependency Injection Keys - TradePulse.AI
========================================

Standardized DI container keys to prevent inconsistencies and
ensure all modules use the same service identifiers.

Author: TradePulse.AI Development Team
Version: 1.0.0
"""

from types import SimpleNamespace

# FIXED: Standardized DI keys for consistent service registration and retrieval
DI_KEYS = SimpleNamespace(
    # Core Trading Engines
    ENTRY_ENGINE="entry_engine",
    EXIT_ENGINE="exit_engine", 
    DAY_TRADING_ENGINE="day_trading_engine",
    ENTERPRISE_TRADING_ENGINE="enterprise_trading_engine",
    SESSION_AWARE_TRADING_ENGINE="session_aware_trading_engine",
    UNIFIED_TRADING_ENGINE="unified_trading_engine",
    
    # AI Services
    CONTINUOUS_LEARNING_ENGINE="continuous_learning_engine",
    TENSORFLOW_SERVICE="tensorflow_async_service",
    MODEL_PERFORMANCE_OPTIMIZER="model_performance_optimizer",
    
    # Risk and Safety
    RISK_MANAGER="risk_manager",
    EMERGENCY_CONTROLS="emergency_controls",
    BRAIN_CONTROLLER="brain_controller",
    
    # Market Data
    LIVE_MARKET_DATA="live_market_data",
    MARKET_DATA_SERVICE="market_data_service",
    BINANCE_CLIENT="binance_hybrid_client",
    
    # Portfolio and Trading
    PORTFOLIO_MANAGER="portfolio_manager",
    PROFESSIONAL_PORTFOLIO="professional_portfolio",
    SIGNAL_PROCESSOR="signal_processor",
    
    # Analytics and Performance
    TRADING_PERFORMANCE_TRACKER="trading_performance_tracker",
    SIGNAL_PERFORMANCE_TRACKER="signal_performance_tracker",
    USER_ANALYTICS="user_analytics_service",
    
    # Utilities
    AUDIT_SERVICE="audit_compliance_service",
    COMMUNICATION_SERVICE="communication_service",
    USER_MANAGEMENT="user_management_service"
)

# Export for easy access
__all__ = ["DI_KEYS"]
