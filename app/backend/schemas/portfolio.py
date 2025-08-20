#!/usr/bin/env python3
"""
Portfolio data models for TradePulse.AI
Virtual trading portfolio with positions and trade history
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid

from pydantic import BaseModel, Field, validator
import structlog

logger = structlog.get_logger()

class OrderType(str, Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class OrderSide(str, Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"

class PositionStatus(str, Enum):
    """Position status enumeration"""
    OPEN = "open"
    CLOSED = "closed"
    PARTIALLY_CLOSED = "partially_closed"

class TradeStatus(str, Enum):
    """Trade status enumeration"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class Portfolio(BaseModel):
    """Virtual portfolio model"""
    
    portfolio_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str = "Default Portfolio"
    
    # Balance information
    initial_balance: Decimal = Field(default=Decimal("10000.00"), description="Starting balance in USD")
    current_balance: Decimal = Field(default=Decimal("10000.00"), description="Current cash balance")
    total_equity: Decimal = Field(default=Decimal("10000.00"), description="Total portfolio value")
    
    # Performance metrics
    realized_pnl: Decimal = Field(default=Decimal("0.00"), description="Realized profit/loss")
    unrealized_pnl: Decimal = Field(default=Decimal("0.00"), description="Unrealized profit/loss")
    total_return: Decimal = Field(default=Decimal("0.00"), description="Total return %")
    
    # Trade statistics
    total_trades: int = Field(default=0, description="Total number of trades")
    winning_trades: int = Field(default=0, description="Number of winning trades")
    losing_trades: int = Field(default=0, description="Number of losing trades")
    win_rate: Decimal = Field(default=Decimal("0.00"), description="Win rate %")
    
    # Risk metrics
    max_drawdown: Decimal = Field(default=Decimal("0.00"), description="Maximum drawdown %")
    sharpe_ratio: Optional[Decimal] = Field(default=None, description="Sharpe ratio")
    
    # Status and timestamps
    is_active: bool = Field(default=True, description="Portfolio active status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Configuration
    max_position_size: Decimal = Field(default=Decimal("1000.00"), description="Max position size in USD")
    max_daily_loss: Decimal = Field(default=Decimal("500.00"), description="Max daily loss limit")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }
        
    @validator('current_balance', 'total_equity', 'initial_balance')
    def validate_positive_amounts(cls, v):
        """Ensure monetary amounts are positive"""
        if v < 0:
            raise ValueError("Balance amounts must be positive")
        return v
    
    def calculate_total_return(self) -> Decimal:
        """Calculate total return percentage"""
        if self.initial_balance <= 0:
            return Decimal("0.00")
        
        return ((self.total_equity - self.initial_balance) / self.initial_balance) * 100
    
    def calculate_win_rate(self) -> Decimal:
        """Calculate win rate percentage"""
        if self.total_trades == 0:
            return Decimal("0.00")
        
        return (Decimal(self.winning_trades) / Decimal(self.total_trades)) * 100
    
    def update_metrics(self):
        """Update calculated metrics"""
        self.total_return = self.calculate_total_return()
        self.win_rate = self.calculate_win_rate()
        self.updated_at = datetime.now(timezone.utc)

class Position(BaseModel):
    """Trading position model"""
    
    position_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id: str
    symbol: str = Field(default="BTCUSDT", description="Trading symbol")
    
    # Position details
    side: OrderSide = Field(description="Position side (buy/sell)")
    size: Decimal = Field(description="Position size")
    entry_price: Decimal = Field(description="Average entry price")
    current_price: Decimal = Field(description="Current market price")
    
    # P&L calculations
    unrealized_pnl: Decimal = Field(default=Decimal("0.00"), description="Unrealized P&L")
    realized_pnl: Decimal = Field(default=Decimal("0.00"), description="Realized P&L")
    
    # Risk management
    stop_loss: Optional[Decimal] = Field(default=None, description="Stop loss price")
    take_profit: Optional[Decimal] = Field(default=None, description="Take profit price")
    
    # Status and timestamps
    status: PositionStatus = Field(default=PositionStatus.OPEN)
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = Field(default=None)
    
    # Trade references
    entry_trade_ids: List[str] = Field(default_factory=list, description="Entry trade IDs")
    exit_trade_ids: List[str] = Field(default_factory=list, description="Exit trade IDs")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }
    
    @validator('size', 'entry_price', 'current_price')
    def validate_positive_values(cls, v):
        """Ensure values are positive"""
        if v <= 0:
            raise ValueError("Position values must be positive")
        return v
    
    def calculate_unrealized_pnl(self) -> Decimal:
        """Calculate unrealized P&L"""
        if self.side == OrderSide.BUY:
            return (self.current_price - self.entry_price) * self.size
        else:  # SELL
            return (self.entry_price - self.current_price) * self.size
    
    def calculate_return_percentage(self) -> Decimal:
        """Calculate return percentage"""
        if self.entry_price <= 0:
            return Decimal("0.00")
        
        pnl = self.calculate_unrealized_pnl()
        position_value = self.entry_price * self.size
        
        return (pnl / position_value) * 100
    
    def update_current_price(self, price: Decimal):
        """Update current price and recalculate P&L"""
        self.current_price = price
        self.unrealized_pnl = self.calculate_unrealized_pnl()
    
    def close_position(self, close_price: Decimal):
        """Close the position"""
        self.current_price = close_price
        self.status = PositionStatus.CLOSED
        self.closed_at = datetime.now(timezone.utc)
        self.realized_pnl = self.calculate_unrealized_pnl()
        self.unrealized_pnl = Decimal("0.00")

class Trade(BaseModel):
    """Individual trade model"""
    
    trade_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id: str
    position_id: Optional[str] = Field(default=None, description="Associated position ID")
    
    # Trade details
    symbol: str = Field(default="BTCUSDT", description="Trading symbol")
    side: OrderSide = Field(description="Trade side (buy/sell)")
    order_type: OrderType = Field(default=OrderType.MARKET, description="Order type")
    
    # Quantities and prices
    quantity: Decimal = Field(description="Trade quantity")
    price: Decimal = Field(description="Execution price")
    total_value: Decimal = Field(description="Total trade value")
    
    # Fees and costs
    commission: Decimal = Field(default=Decimal("0.00"), description="Trading commission")
    slippage: Decimal = Field(default=Decimal("0.00"), description="Price slippage")
    
    # P&L (for closing trades)
    pnl: Optional[Decimal] = Field(default=None, description="Profit/loss for closing trades")
    pnl_percentage: Optional[Decimal] = Field(default=None, description="P&L percentage")
    
    # Status and timestamps
    status: TradeStatus = Field(default=TradeStatus.PENDING)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    executed_at: Optional[datetime] = Field(default=None)
    
    # Strategy context
    strategy_name: Optional[str] = Field(default=None, description="Trading strategy used")
    confidence_score: Optional[Decimal] = Field(default=None, description="AI confidence score")
    
    # Risk management
    stop_loss: Optional[Decimal] = Field(default=None, description="Stop loss price")
    take_profit: Optional[Decimal] = Field(default=None, description="Take profit price")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: str(v)
        }
    
    @validator('quantity', 'price', 'total_value')
    def validate_positive_values(cls, v):
        """Ensure values are positive"""
        if v <= 0:
            raise ValueError("Trade values must be positive")
        return v
    
    @validator('total_value')
    def validate_total_value(cls, v, values):
        """Validate total value matches quantity * price"""
        if 'quantity' in values and 'price' in values:
            expected_value = values['quantity'] * values['price']
            if abs(v - expected_value) > Decimal("0.01"):  # Allow small rounding differences
                raise ValueError("Total value must equal quantity * price")
        return v
    
    def execute_trade(self, execution_price: Optional[Decimal] = None):
        """Execute the trade"""
        if execution_price:
            self.price = execution_price
            self.total_value = self.quantity * self.price
        
        self.status = TradeStatus.FILLED
        self.executed_at = datetime.now(timezone.utc)
        
        logger.info(
            "trade_executed",
            trade_id=self.trade_id,
            symbol=self.symbol,
            side=self.side,
            quantity=str(self.quantity),
            price=str(self.price),
            total_value=str(self.total_value)
        )
    
    def cancel_trade(self):
        """Cancel the trade"""
        self.status = TradeStatus.CANCELLED
        
        logger.info(
            "trade_cancelled",
            trade_id=self.trade_id,
            symbol=self.symbol,
            side=self.side
        )

class PortfolioSummary(BaseModel):
    """Portfolio summary for API responses"""
    
    portfolio_id: str
    name: str
    current_balance: Decimal
    total_equity: Decimal
    total_return: Decimal
    win_rate: Decimal
    total_trades: int
    open_positions: int
    daily_pnl: Decimal
    max_drawdown: Decimal
    is_active: bool
    
    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        } 

class VirtualPosition(BaseModel):
    """Virtual Position model for tracking individual positions"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    symbol: str = Field(default="BTCUSDT")
    position_type: str = Field(default="LONG")  # LONG or SHORT
    size: Decimal = Field(default=Decimal('0.00547'))
    entry_price: Decimal = Field(default=Decimal('0.00'))
    current_price: Decimal = Field(default=Decimal('0.00'))
    unrealized_pnl: Decimal = Field(default=Decimal('0.00'))
    unrealized_pnl_percentage: float = Field(default=0.0)
    confidence: float = Field(default=71.0)
    entry_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(default="ACTIVE")  # ACTIVE, CLOSED
    strategy: str = Field(default="intelligent_entry")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }

class VirtualPortfolio(BaseModel):
    """Virtual Portfolio model for tracking portfolio state"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    total_value: Decimal = Field(default=Decimal('10000.00'))
    available_cash: Decimal = Field(default=Decimal('10000.00'))
    invested_amount: Decimal = Field(default=Decimal('0.00'))
    unrealized_pnl: Decimal = Field(default=Decimal('0.00'))
    realized_pnl: Decimal = Field(default=Decimal('0.00'))
    active_positions_count: int = Field(default=0)
    total_trades: int = Field(default=0)
    win_rate: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        } 

# Add missing classes at the end
class VirtualTrade(BaseModel):
    """Virtual Trade model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = "BTCUSDT"
    side: str = "BUY"
    quantity: Decimal = Decimal('0.00547')
    price: Decimal = Decimal('0.00')
    status: str = "COMPLETED"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PortfolioRequest(BaseModel):
    """Portfolio request model"""
    user_id: str

class PositionRequest(BaseModel):
    """Position request model"""
    user_id: str
    symbol: str = "BTCUSDT"
    size: Decimal
    position_type: str = "LONG"

class TradeRequest(BaseModel):
    """Trade request model"""
    user_id: str
    symbol: str = "BTCUSDT"
    side: str = "BUY"
    quantity: Decimal
    price: Decimal

class PortfolioResponse(BaseModel):
    """Portfolio response model"""
    success: bool = True
    data: dict = {}

class PositionResponse(BaseModel):
    """Position response model"""
    success: bool = True
    data: dict = {}

class TradeResponse(BaseModel):
    """Trade response model"""
    success: bool = True
    data: dict = {}

class Trade(BaseModel):
    """Trade model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = "BTCUSDT"
    side: str = "BUY"
    quantity: Decimal = Decimal('0.00547')
    price: Decimal = Decimal('0.00')
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PortfolioSummary(BaseModel):
    """Portfolio summary model"""
    total_value: Decimal = Decimal('10000.00')
    available_cash: Decimal = Decimal('10000.00')
    active_positions: int = 0
    total_pnl: Decimal = Decimal('0.00') 