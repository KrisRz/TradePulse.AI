"""
TradePulse.AI Schemas
====================

Pydantic models for API request/response validation.
"""

from .portfolio import (
    VirtualPortfolio,
    VirtualPosition,
    VirtualTrade,
    PortfolioRequest,
    PositionRequest,
    TradeRequest,
    PortfolioResponse,
    PositionResponse,
    TradeResponse,
    Trade,
    PortfolioSummary,
    OrderType,
    OrderSide, 
    PositionStatus,
    TradeStatus
)

from .exit_analysis import *
