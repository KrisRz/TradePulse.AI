"""
BRAIN State Management - TradePulse.AI
=====================================

Complete Pydantic-based state management for the BRAIN controller.
Provides type-safe state models for all trading operations and components.

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from dataclasses import dataclass

class BrainState(str, Enum):
    """BRAIN controller FSM states"""
    INIT = "init"                    # Initial startup
    WARMUP = "warmup"               # Loading models and data
    RUNNING = "running"             # Active trading operations
    HALT = "halt"                   # Temporary suspension
    COOLDOWN = "cooldown"           # Graceful shutdown
    ERROR = "error"                 # Error recovery

class TradingSession(str, Enum):
    """Global trading sessions"""
    ASIAN = "asian"                 # 21:00-06:00 UTC
    EUROPEAN = "european"           # 06:00-14:00 UTC  
    AMERICAN = "american"           # 14:00-21:00 UTC
    OVERLAP = "overlap"             # 12:00-16:00 UTC (EU-US overlap)

class SignalType(str, Enum):
    """Types of trading signals"""
    PRIMARY = "primary"             # Main AI signal
    EXPLORATORY = "exploratory"     # Small probing position
    REVERSAL = "reversal"           # Counter-trend signal
    MOMENTUM = "momentum"           # Trend following signal

class RiskLevel(str, Enum):
    """Risk assessment levels"""
    VERY_LOW = "very_low"           # <1% volatility
    LOW = "low"                     # 1-3% volatility
    MODERATE = "moderate"           # 3-5% volatility
    HIGH = "high"                   # 5-10% volatility
    EXTREME = "extreme"             # >10% volatility

class PositionStatus(str, Enum):
    """Position lifecycle states"""
    PENDING = "pending"             # Order submitted
    OPEN = "open"                   # Position active
    CLOSING = "closing"             # Exit signal triggered
    CLOSED = "closed"               # Position completed
    CANCELLED = "cancelled"         # Order cancelled

class OrderType(str, Enum):
    """Order execution types"""
    MARKET = "market"               # Immediate execution
    LIMIT = "limit"                 # Price-specific order
    STOP_LOSS = "stop_loss"         # Risk management order
    TAKE_PROFIT = "take_profit"     # Profit taking order

# Core State Models

class MarketTick(BaseModel):
    """Real-time market price data"""
    symbol: str
    price: Decimal
    timestamp: datetime
    volume_24h: Optional[Decimal] = None
    change_24h: Optional[Decimal] = None
    source: str = "websocket"  # websocket, rest, cache

class MarketData(BaseModel):
    """Comprehensive market information"""
    symbol: str
    current_price: Decimal
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    spread_pct: Optional[Decimal] = None
    volatility_24h: Decimal
    volume_24h: Decimal
    volume_ratio: Decimal = Decimal('1.0')
    timestamp: datetime

class Candle(BaseModel):
    """OHLCV candlestick data"""
    symbol: str
    timestamp: datetime
    interval: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    trades: int = 0
    is_closed: bool = True
    source: str = "rest"

class LayerAnalysis(BaseModel):
    """Enterprise 6-layer AI analysis results"""
    layer_1_regime: Dict[str, Any] = Field(default_factory=dict)
    layer_3_reversal: Dict[str, Any] = Field(default_factory=dict) 
    layer_4_filters: Dict[str, Any] = Field(default_factory=dict)
    layer_5_confidence: Dict[str, Any] = Field(default_factory=dict)
    layer_6_timing: Dict[str, Any] = Field(default_factory=dict)

class TradingSignal(BaseModel):
    """AI-generated trading signal"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: Decimal
    reasoning: str
    signal_type: SignalType = SignalType.PRIMARY
    layer_analysis: Optional[LayerAnalysis] = None
    timestamp: datetime
    expiry: Optional[datetime] = None

class RiskContext(BaseModel):
    """Risk assessment context"""
    risk_score: Decimal = Field(ge=0, le=1)  # 0-1 scale
    risk_level: RiskLevel
    block_reason: Optional[str] = None
    volatility_current: Decimal
    volatility_median: Decimal  
    position_exposure: Decimal
    daily_pnl_pct: Decimal
    max_positions_reached: bool
    emergency_conditions: List[str] = Field(default_factory=list)

class EntryAnalysis(BaseModel):
    """Entry opportunity analysis"""
    should_enter: bool
    confidence: Decimal
    entry_quality: str  # "excellent", "good", "fair", "poor"
    optimal_price: Optional[Decimal] = None
    reasoning: str
    size_recommendation: Decimal
    stop_loss_price: Optional[Decimal] = None
    take_profit_price: Optional[Decimal] = None

class ExitAnalysis(BaseModel):
    """Exit opportunity analysis"""  
    should_exit: bool
    confidence: Decimal
    exit_reason: str  # "take_profit", "stop_loss", "ai_signal", "time_limit"
    optimal_price: Optional[Decimal] = None
    pnl_percent: Decimal
    pnl_absolute: Decimal
    hold_duration_minutes: int

class Position(BaseModel):
    """Active trading position"""
    position_id: str
    symbol: str
    side: str  # LONG, SHORT
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    status: PositionStatus
    entry_time: datetime
    exit_time: Optional[datetime] = None
    pnl_absolute: Decimal = Decimal('0')
    pnl_percent: Decimal = Decimal('0')
    ai_confidence: Decimal
    ai_reasoning: str

class OrderResult(BaseModel):
    """Order execution result"""
    order_id: str
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    order_type: OrderType
    status: str
    execution_time: datetime
    slippage_pct: Optional[Decimal] = None
    fees: Optional[Decimal] = None
    latency_ms: Optional[int] = None

class PortfolioState(BaseModel):
    """Current portfolio state"""
    cash_balance: Decimal
    total_value: Decimal
    active_positions: List[Position] = Field(default_factory=list)
    daily_pnl: Decimal = Decimal('0')
    daily_pnl_pct: Decimal = Decimal('0')
    total_trades_today: int = 0
    consecutive_losses: int = 0
    max_drawdown: Decimal = Decimal('0')
    last_updated: datetime

class PerformanceMetrics(BaseModel):
    """Real-time performance tracking"""
    total_trades: int = 0
    winning_trades: int = 0  
    losing_trades: int = 0
    win_rate: Decimal = Decimal('0')
    avg_win_pct: Decimal = Decimal('0')
    avg_loss_pct: Decimal = Decimal('0')
    sharpe_ratio: Decimal = Decimal('0')
    max_drawdown: Decimal = Decimal('0')
    profit_factor: Decimal = Decimal('0')
    avg_trade_duration_minutes: int = 0
    last_updated: datetime

class TradingContext(BaseModel):
    """Complete trading context for decision making"""
    session: TradingSession
    current_tick: Optional[MarketTick] = None
    market_data: Optional[MarketData] = None
    recent_candles: List[Candle] = Field(default_factory=list)
    current_signal: Optional[TradingSignal] = None
    risk_context: Optional[RiskContext] = None
    entry_analysis: Optional[EntryAnalysis] = None
    exit_analysis: Optional[ExitAnalysis] = None
    portfolio_state: Optional[PortfolioState] = None
    performance_metrics: Optional[PerformanceMetrics] = None
    timestamp: datetime

class BrainControllerState(BaseModel):
    """BRAIN controller internal state"""
    current_state: BrainState
    state_entered_at: datetime
    trading_context: TradingContext
    cycle_count: int = 0
    last_decision_at: Optional[datetime] = None
    last_error: Optional[str] = None
    error_count: int = 0
    uptime_seconds: int = 0
    
    # Performance tracking
    avg_cycle_time_ms: Decimal = Decimal('0')
    cycles_per_hour: int = 0
    positions_opened_today: int = 0
    decisions_made_today: int = 0
    
    # Configuration
    cycle_interval_seconds: int = 15
    max_positions: int = 5
    position_size_pct: Decimal = Decimal('0.05')
    confidence_threshold: Decimal = Decimal('0.55')  # Exploratory threshold for sideways markets (lowered from 0.45)
    
    class Config:
        arbitrary_types_allowed = True

# Helper Functions

def create_initial_trading_context(session: TradingSession) -> TradingContext:
    """Create initial trading context for new session"""
    return TradingContext(
        session=session,
        timestamp=datetime.now(timezone.utc)
    )

def create_initial_brain_state() -> BrainControllerState:
    """Create initial BRAIN controller state"""
    current_hour = datetime.now(timezone.utc).hour
    
    # Detect current session
    if 21 <= current_hour or current_hour < 6:
        session = TradingSession.ASIAN
    elif 6 <= current_hour < 14:
        session = TradingSession.EUROPEAN  
    elif 12 <= current_hour < 16:
        session = TradingSession.OVERLAP
    else:
        session = TradingSession.AMERICAN
    
    return BrainControllerState(
        current_state=BrainState.INIT,
        state_entered_at=datetime.now(timezone.utc),
        trading_context=create_initial_trading_context(session)
    )

# Export all models
__all__ = [
    # Enums
    "BrainState", "TradingSession", "SignalType", "RiskLevel", 
    "PositionStatus", "OrderType",
    # Core Models
    "MarketTick", "MarketData", "Candle", "LayerAnalysis",
    "TradingSignal", "RiskContext", "EntryAnalysis", "ExitAnalysis",
    "Position", "OrderResult", "PortfolioState", "PerformanceMetrics",
    "TradingContext", "BrainControllerState",
    # Helper Functions
    "create_initial_trading_context", "create_initial_brain_state"
]