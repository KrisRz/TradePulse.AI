"""
Enterprise Dependencies for TradePulse.AI
Professional dependency injection for 6-layer enterprise system
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.backend.core.config import get_settings
from app.backend.core.database import get_database_session
from app.backend.services import (
    EnterpriseTradingEngine,
    RiskManager,
    PerformanceTracker,
    VirtualPortfolioManager,
    HistoricalDataProcessor,
    LiveDataProcessor
)

settings = get_settings()
security = HTTPBearer(auto_error=False)


# User Model
class User(BaseModel):
    """User model for authentication"""
    id: str
    email: str
    username: str
    role: str
    is_active: bool = True

# Database Dependencies
async def get_db() -> Generator:
    """Get database session"""
    db = get_database_session()
    try:
        yield db
    finally:
        await db.close()


# Authentication Dependencies  
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """Get current authenticated user"""
    if not credentials:
        if settings.ENVIRONMENT == "development":
            # Allow anonymous access in development (align with admin dashboard user id)
            return User(
                id="admin",
                email="admin@tradepulse.ai",
                username="admin",
                role="admin"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
    
    token = credentials.credentials
    
    # Enterprise admin token
    if token == "enterprise_admin_token":
        return User(
            id="enterprise_admin",
            email="admin@tradepulse.ai",
            username="enterprise_admin",
            role="admin"
        )
    
    # Regular user validation would go here
    # For now, return demo user
    return User(
        id="demo_user",
        email="demo@tradepulse.ai", 
        username="demo_user",
        role="user"
    )


def require_admin_role(current_user: User = Depends(get_current_user)) -> User:
    """Ensure user has admin role"""
    if current_user.role != "admin":
        # Allow in development
        if settings.ENVIRONMENT != "development":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required"
            )
    return current_user


# Service Dependencies
def get_enterprise_trading_engine() -> EnterpriseTradingEngine:
    """Get enterprise trading engine instance"""
    return EnterpriseTradingEngine()


def get_risk_manager() -> RiskManager:
    """Get risk manager instance"""
    return RiskManager()


def get_performance_tracker() -> PerformanceTracker:
    """Get performance tracker instance"""
    return PerformanceTracker()


def get_portfolio_manager() -> VirtualPortfolioManager:
    """Get portfolio manager instance"""
    return VirtualPortfolioManager()


def get_historical_data_processor() -> HistoricalDataProcessor:
    """Get historical data processor instance"""
    return HistoricalDataProcessor()

def get_live_data_processor() -> LiveDataProcessor:
    """Get live data processor instance"""
    # This needs a db_manager parameter
    from app.backend.core.database import db_manager
    return LiveDataProcessor(db_manager)


# Validation Dependencies
async def validate_symbol(symbol: str = "BTCUSDT") -> str:
    """Validate trading symbol"""
    allowed_symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
    if symbol not in allowed_symbols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Symbol {symbol} not supported. Allowed: {allowed_symbols}"
        )
    return symbol


async def validate_timeframe(timeframe: str = "1m") -> str:
    """Validate timeframe parameter"""
    allowed_timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
    if timeframe not in allowed_timeframes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Timeframe {timeframe} not supported. Allowed: {allowed_timeframes}"
        )
    return timeframe

def generate_user_id() -> str:
    """Generate a unique user ID"""
    import uuid
    return f"user_{uuid.uuid4().hex[:12]}" 