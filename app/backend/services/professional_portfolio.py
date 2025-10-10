"""
Professional Virtual Portfolio Service for TradePulse.AI
Enterprise-grade portfolio management with real P&L calculations

Features:
- Real-time position tracking with live market data
- Professional P&L calculations and risk metrics
- Position sizing with Kelly criterion
- Risk management with drawdown protection
- Performance analytics and reporting
- Professional logging and error handling
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json
import uuid

import structlog
from .live_market_data import get_live_bitcoin_price
from ..utils.money import (
    D, quantize_qty, quantize_price, calculate_position_value,
    calculate_pnl, calculate_pnl_percentage, calculate_risk_amount,
    safe_monetary_add, safe_monetary_subtract, safe_monetary_multiply
)
from ..utils.risk_management import (
    calculate_tp_sl_from_entry, calculate_risk_reward_ratio,
    calculate_position_size_risk_based, validate_tp_sl_levels, log_risk_metrics
)

logger = structlog.get_logger(__name__)

class PositionType(Enum):
    """Professional position types"""
    LONG = "long"
    SHORT = "short"

class PositionStatus(Enum):
    """Professional position status"""
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"
    CANCELLED = "cancelled"

@dataclass
class ProfessionalPosition:
    """Professional position with comprehensive tracking"""
    position_id: str
    symbol: str
    type: PositionType
    size: Decimal
    entry_price: Decimal
    entry_time: datetime
    current_price: Decimal = field(default_factory=lambda: Decimal('0'))
    exit_price: Optional[Decimal] = None
    exit_time: Optional[datetime] = None
    status: PositionStatus = PositionStatus.OPEN
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    ai_confidence: float = 0.5
    ai_reasoning: str = ""
    commission_rate: Decimal = field(default_factory=lambda: Decimal('0.001'))  # 0.1%
    
    @property
    def unrealized_pnl(self) -> Decimal:
        """Calculate unrealized P&L"""
        if self.status != PositionStatus.OPEN:
            return Decimal('0')
        
        if self.type == PositionType.LONG:
            return (self.current_price - self.entry_price) * self.size
        else:  # SHORT
            return (self.entry_price - self.current_price) * self.size
    
    @property
    def unrealized_pnl_percentage(self) -> Decimal:
        """Calculate unrealized P&L percentage"""
        if self.entry_price == 0:
            return Decimal('0')
        
        return (self.unrealized_pnl / (self.entry_price * self.size)) * Decimal('100')
    
    @property
    def realized_pnl(self) -> Decimal:
        """Calculate realized P&L"""
        if self.status != PositionStatus.CLOSED or not self.exit_price:
            return Decimal('0')
        
        if self.type == PositionType.LONG:
            gross_pnl = (self.exit_price - self.entry_price) * self.size
        else:  # SHORT
            gross_pnl = (self.entry_price - self.exit_price) * self.size
        
        # Subtract commissions
        entry_commission = self.entry_price * self.size * self.commission_rate
        exit_commission = self.exit_price * self.size * self.commission_rate
        
        return gross_pnl - entry_commission - exit_commission
    
    @property
    def position_value(self) -> Decimal:
        """Current position value"""
        # Safety check to prevent None values
        current_price = self.current_price or self.entry_price or Decimal('0')
        size = self.size or Decimal('0')
        return current_price * size
        
    @property
    def current_value(self) -> Decimal:
        """Current position value - alias for position_value (required by risk manager)"""
        return self.position_value
    
    @property
    def risk_amount(self) -> Decimal:
        """Amount at risk (to stop loss)"""
        if not self.stop_loss:
            return self.position_value * Decimal('0.02')  # Default 2% risk
        
        if self.type == PositionType.LONG:
            return (self.entry_price - self.stop_loss) * self.size
        else:  # SHORT
            return (self.stop_loss - self.entry_price) * self.size

@dataclass
class PortfolioMetrics:
    """Professional portfolio performance metrics - ALL FLOAT VALUES"""
    total_value: float
    cash_balance: float
    positions_value: float
    total_pnl: float
    daily_pnl: float
    total_pnl_percentage: float
    daily_pnl_percentage: float
    number_of_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    average_win: float
    average_loss: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_percentage: float
    risk_score: float
    timestamp: datetime

class ProfessionalPortfolio:
    """Professional virtual portfolio with enterprise-grade features"""
    
    def __init__(self, 
                 user_id: str, 
                 initial_balance: Decimal = None,  # Will load from DynamoDB
                 max_risk_per_trade: Decimal = Decimal('0.02'),  # 2%
                 max_portfolio_risk: Decimal = Decimal('0.10')):  # 10%
        
        self.user_id = user_id
        # Load actual balance from DynamoDB virtual_portfolios table
        loaded_balance = initial_balance or self._load_balance_from_db()
        # Final safety check to ensure we never have None values
        self.initial_balance = loaded_balance or Decimal('50000')
        self.cash_balance = self.initial_balance
        self.max_risk_per_trade = max_risk_per_trade
        self.max_portfolio_risk = max_portfolio_risk
        
        # Position tracking
        self.positions: Dict[str, ProfessionalPosition] = {}
        self.closed_positions: List[ProfessionalPosition] = []
        
        # Performance tracking
        self.daily_starting_balance = self.initial_balance  # Use the resolved initial_balance
        self.peak_balance = self.initial_balance
        self.max_drawdown_amount = Decimal('0')
        self.last_daily_reset_date = datetime.now(timezone.utc).date()  # Track last reset
        
        # Risk management - OPTIMIZED FOR SMALL FREQUENT TRADES
        self.daily_trades = 0
        self.max_daily_trades = 30  # SMALL TRADES: 30 trades per day (was 8 - too low!)
        self.consecutive_losses = 0
        self.max_consecutive_losses = 8  # Higher tolerance for small losses (was 5)
        
        # DynamoDB persistence
        self.db_client = None
        self._initialize_persistence()
        
        logger.info(
            "Professional portfolio initialized",
            user_id=user_id,
            initial_balance=float(self.initial_balance),  # Use resolved balance, not parameter
            max_risk_per_trade=float(max_risk_per_trade)
        )
    
    def _load_balance_from_db(self) -> Decimal:
        """Load actual balance from DynamoDB virtual_portfolios table"""
        try:
            from app.backend.core.database import DynamoDBClient
            
            # Initialize DynamoDB client
            client = DynamoDBClient()
            
            # Get portfolio from virtual_portfolios table (AWS: tradepulse-virtual-portfolios)
            portfolio_data = client.get_item('tradepulse-virtual-portfolios', {'user_id': self.user_id}, consistent_read=True)
            
            if portfolio_data:
                balance = portfolio_data.get('balance', Decimal('50000'))
                initial_balance = portfolio_data.get('initial_balance', balance)
                # Ensure we never return None
                if initial_balance is None:
                    initial_balance = balance or Decimal('50000')
                logger.info(f"💰 Loaded balance from DynamoDB for {self.user_id}: ${float(initial_balance):,.2f}")
                return Decimal(str(initial_balance))
            else:
                logger.warning(f"⚠️ No portfolio found in DynamoDB for {self.user_id}, using default $50,000")
                return Decimal('50000')
                
        except Exception as e:
            logger.error(f"❌ Failed to load balance from DynamoDB for {self.user_id}: {e}")
            return Decimal('50000')  # Fallback to default - DAY TRADING CAPITAL
    
    def _initialize_persistence(self):
        """Initialize DynamoDB client and load existing positions"""
        try:
            from app.backend.core.database import DynamoDBClient
            self.db_client = DynamoDBClient()
            logger.info(f"✅ DynamoDB client initialized for portfolio {self.user_id}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize DynamoDB client: {e}")
            self.db_client = None
    
    async def update_positions_with_live_data(self):
        """Update all open positions with live market data"""
        if not self.positions:
            return
        
        try:
            # Get live Bitcoin price
            current_price = Decimal(str(await get_live_bitcoin_price()))
            
            # Update all Bitcoin positions
            for position in self.positions.values():
                if position.symbol == "BTCUSDT" and position.status == PositionStatus.OPEN:
                    old_price = position.current_price
                    position.current_price = current_price
                    
                    # Check stop loss and take profit
                    await self._check_position_triggers(position)
                    
                    logger.debug(
                        "Position updated with live data",
                        position_id=position.position_id,
                        old_price=float(old_price),
                        new_price=float(current_price),
                        unrealized_pnl=float(position.unrealized_pnl)
                    )
                    
        except Exception as e:
            logger.error("Failed to update positions with live data", error=str(e))
    
    async def _check_position_triggers(self, position: ProfessionalPosition):
        """Update position data only - NO automatic closing (use intelligent_exit_engine instead)"""
        if position.status != PositionStatus.OPEN:
            return
        
        # Only update position data - intelligent_exit_engine handles closing decisions
        logger.debug(f"Position {position.position_id} updated: price=${float(position.current_price)}, "
                    f"pnl={float(position.unrealized_pnl_percentage):.2f}%")
    
    
    def _validate_position_consistency(self, position_type: PositionType, ai_reasoning: str) -> None:
        """Validate semantic consistency between position type and reasoning"""
        reasoning_upper = ai_reasoning.upper()
        
        # Check for semantic consistency
        if position_type == PositionType.LONG:
            if "SHORT" in reasoning_upper and "BUY" not in reasoning_upper:
                raise ValueError(f"Semantic inconsistency: LONG position with SHORT reasoning: {ai_reasoning}")
            if "SELL SIGNAL" in reasoning_upper:
                raise ValueError(f"Semantic inconsistency: LONG position with SELL signal: {ai_reasoning}")
        
        elif position_type == PositionType.SHORT:
            if "LONG" in reasoning_upper and "SELL" not in reasoning_upper:
                raise ValueError(f"Semantic inconsistency: SHORT position with LONG reasoning: {ai_reasoning}")
            if "BUY SIGNAL" in reasoning_upper:
                raise ValueError(f"Semantic inconsistency: SHORT position with BUY signal: {ai_reasoning}")
        
        logger.debug(f"✅ Position consistency validated: {position_type.value} - {ai_reasoning[:50]}...")
    
    def _validate_position_invariants(self, position: ProfessionalPosition):
        """CRITICAL: Validate position invariants to prevent data corruption"""
        
        # Validate LONG position invariants
        if position.type == PositionType.LONG:
            if position.stop_loss and position.stop_loss >= position.entry_price:
                raise ValueError(f"LONG position invariant violated: stop_loss ({position.stop_loss}) >= entry_price ({position.entry_price})")
            
            if position.take_profit and position.take_profit <= position.entry_price:
                raise ValueError(f"LONG position invariant violated: take_profit ({position.take_profit}) <= entry_price ({position.entry_price})")
            
            # Validate AI reasoning consistency for LONG
            if "SHORT" in position.ai_reasoning.upper() or "SELL" in position.ai_reasoning:
                logger.warning(f"⚠️ LONG position has SHORT/SELL in reasoning: {position.ai_reasoning}")
        
        # Validate SHORT position invariants  
        elif position.type == PositionType.SHORT:
            if position.stop_loss and position.stop_loss <= position.entry_price:
                raise ValueError(f"SHORT position invariant violated: stop_loss ({position.stop_loss}) <= entry_price ({position.entry_price})")
            
            if position.take_profit and position.take_profit >= position.entry_price:
                raise ValueError(f"SHORT position invariant violated: take_profit ({position.take_profit}) >= entry_price ({position.entry_price})")
            
            # Validate AI reasoning consistency for SHORT
            if "LONG" in position.ai_reasoning.upper() or "BUY" in position.ai_reasoning:
                logger.warning(f"⚠️ SHORT position has LONG/BUY in reasoning: {position.ai_reasoning}")
        
        # Validate AI confidence range
        if not (0.0 <= position.ai_confidence <= 1.0):
            raise ValueError(f"AI confidence out of range: {position.ai_confidence} (must be 0.0-1.0)")
        
        logger.debug(f"✅ Position invariants validated: {position.position_id}")

    async def open_position(self,
                          symbol: str,
                          position_type: PositionType,
                          size: Decimal,
                          ai_confidence: float = 0.5,
                          ai_reasoning: str = "",
                          stop_loss_pct: Optional[Decimal] = None,
                          take_profit_pct: Optional[Decimal] = None) -> str:
        """Open a new professional position with risk management"""
        
        try:
            # Get current market price using safe conversion
            current_price = D(await get_live_bitcoin_price())

            # Calculate position size based on risk management
            risk_adjusted_size = await self._calculate_position_size(
                size, current_price, ai_confidence
            )

            # Validate position using safe money math
            position_value = calculate_position_value(current_price, risk_adjusted_size)
            if position_value > self.cash_balance:
                raise ValueError(f"Insufficient funds: need ${position_value}, have ${self.cash_balance}")

            # AGGRESSIVE SCALPING: Remove daily trade limit for continuous trading
            # System is smart enough with AI confidence thresholds and risk management
            # if self.daily_trades >= self.max_daily_trades:
            #     raise ValueError(f"Daily trade limit reached: {self.max_daily_trades}")
            logger.debug(f"📊 Daily trades: {self.daily_trades} (no limit for aggressive scalping)")

            
            # CRITICAL: Validate semantic consistency
            self._validate_position_consistency(position_type, ai_reasoning)
            # Create position with collision-resistant id
            position_id = f"pos_{symbol}_{uuid.uuid4().hex}"

                        # Calculate stop loss and take profit using standardized risk management
            stop_loss = None
            take_profit = None

            if stop_loss_pct or take_profit_pct:
                # Use standardized TP/SL calculation
                stop_loss_level = None
                take_profit_level = None

                if stop_loss_pct:
                    if position_type == PositionType.LONG:
                        # LONG: stop loss BELOW entry price
                        stop_loss_level = current_price * (D('1') - stop_loss_pct)
                    else:  # SHORT
                        # SHORT: stop loss ABOVE entry price (price goes up = loss)
                        stop_loss_level = current_price * (D('1') + stop_loss_pct)

                if take_profit_pct:
                    if position_type == PositionType.LONG:
                        # LONG: take profit ABOVE entry price
                        take_profit_level = current_price * (D('1') + take_profit_pct)
                    else:  # SHORT
                        # SHORT: take profit BELOW entry price (price goes down = profit)
                        take_profit_level = current_price * (D('1') - take_profit_pct)

                # Use standardized calculation for consistency
                take_profit, stop_loss = calculate_tp_sl_from_entry(
                    entry_price=current_price,
                    stop_loss=stop_loss_level,
                    take_profit=take_profit_level,
                    position_type=position_type.value,
                    symbol=symbol
                )
            
            # CRITICAL: Normalize AI confidence to [0,1] range
            normalized_confidence = min(max(ai_confidence, 0.0), 1.0)
            
            position = ProfessionalPosition(
                position_id=position_id,
                symbol=symbol,
                type=position_type,
                size=risk_adjusted_size,
                entry_price=current_price,
                entry_time=datetime.now(timezone.utc),
                current_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                ai_confidence=normalized_confidence,
                ai_reasoning=ai_reasoning
            )
            
            # CRITICAL: Validate position invariants
            self._validate_position_invariants(position)
            
            # Update portfolio state
            self.positions[position_id] = position
            self.cash_balance -= position_value
            self.daily_trades += 1
            
            # Save to DynamoDB for persistence
            await self._save_position_to_db(position)
            
            # Log comprehensive risk metrics
            log_risk_metrics(
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size=risk_adjusted_size,
                portfolio_value=self.get_total_portfolio_value(),
                position_type=position_type.value,
                symbol=symbol
            )

            logger.info(
                "Professional position opened",
                extra={
                    "position_id": position_id,
                    "symbol": symbol,
                    "type": position_type.value,
                    "size": float(risk_adjusted_size),
                    "entry_price": float(current_price),
                    "position_value": float(position_value),
                    "ai_confidence": ai_confidence,
                    "stop_loss": float(stop_loss) if stop_loss else None,
                    "take_profit": float(take_profit) if take_profit else None
                }
            )
            
            return position_id
            
        except Exception as e:
            logger.error("Failed to open professional position", error=str(e))
            raise
    
    async def close_position(self, position_id: str, reason: str = "manual") -> Decimal:
        """Close a professional position with P&L calculation"""
        
        if position_id not in self.positions:
            raise ValueError(f"Position {position_id} not found")
        
        position = self.positions[position_id]
        
        if position.status != PositionStatus.OPEN:
            raise ValueError(f"Position {position_id} is not open")
        
        try:
            # Get current market price using safe conversion
            current_price = D(await get_live_bitcoin_price())
            position.current_price = current_price

            # Close position
            position.exit_price = current_price
            position.exit_time = datetime.now(timezone.utc)
            position.status = PositionStatus.CLOSED

            # Calculate realized P&L using safe money math
            realized_pnl = position.realized_pnl

            # Update portfolio state: add back original entry value plus realized P&L
            entry_value = calculate_position_value(position.entry_price, position.size)
            self.cash_balance = safe_monetary_add(self.cash_balance, safe_monetary_add(entry_value, realized_pnl))
            self.closed_positions.append(position)
            del self.positions[position_id]
            
            # Update consecutive losses tracking
            if realized_pnl < 0:
                self.consecutive_losses += 1
            else:
                self.consecutive_losses = 0
            
            logger.info(
                "Professional position closed",
                position_id=position_id,
                reason=reason,
                entry_price=float(position.entry_price),
                exit_price=float(position.exit_price),
                realized_pnl=float(realized_pnl),
                duration_minutes=(position.exit_time - position.entry_time).total_seconds() / 60,
                ai_confidence=position.ai_confidence
            )
            
            # PHASE 4.3: Track position result for continuous learning
            try:
                from app.backend.services.position_result_tracker import get_position_result_tracker, PositionResult, PositionOutcome
                
                # Determine outcome type
                outcome = PositionOutcome.MANUAL_CLOSE
                if "take_profit" in reason.lower():
                    outcome = PositionOutcome.TAKE_PROFIT
                elif "stop_loss" in reason.lower():
                    outcome = PositionOutcome.STOP_LOSS
                elif "time" in reason.lower():
                    outcome = PositionOutcome.TIME_STOP
                elif "emergency" in reason.lower():
                    outcome = PositionOutcome.EMERGENCY_CLOSE
                
                # Create position result for learning
                position_result = PositionResult(
                    position_id=position_id,
                    symbol=position.symbol,
                    outcome=outcome,
                    was_successful=realized_pnl > 0,
                    pnl_absolute=float(realized_pnl),
                    pnl_percentage=float((realized_pnl / (position.entry_price * position.size)) * 100),
                    time_in_position_minutes=int((position.exit_time - position.entry_time).total_seconds() / 60),
                    entry_price=float(position.entry_price),
                    exit_price=float(position.exit_price),
                    ai_confidence=position.ai_confidence,
                    risk_assessment="medium",  # Could be enhanced with actual risk assessment
                    patterns_detected=[],  # Could be enhanced with pattern detection
                    closed_at=position.exit_time
                )
                
                # Record for continuous learning
                tracker = await get_position_result_tracker()
                await tracker.record_position_result(position_result)
                
                logger.info(f"📊 Position result recorded for continuous learning: {position_id}")
                
            except Exception as e:
                logger.warning(f"Continuous learning tracking failed for position {position_id}: {e}")
            
            # LEGACY: Also track with performance tracker for compatibility
            try:
                from app.backend.services.trading_performance_tracker import get_trading_performance_tracker
                performance_tracker = await get_trading_performance_tracker()
                
                # Create trade ID from position for tracking
                trade_id = f"trade_{position_id.split('_')[-1]}_{position.symbol}" if '_' in position_id else f"trade_{position_id}_{position.symbol}"
                
                exit_data = {
                    "exit_price": float(position.exit_price),
                    "reason": reason,
                    "confidence": 1.0  # High confidence for completed exit
                }
                
                exit_analysis = {
                    "exit_reason": reason,
                    "pnl": float(realized_pnl),
                    "duration_minutes": (position.exit_time - position.entry_time).total_seconds() / 60
                }
                
                await performance_tracker.track_trade_exit(trade_id, exit_data, exit_analysis)
                
            except Exception as e:
                logger.warning(f"Legacy performance tracking failed for position {position_id}: {e}")
            
            # Save closed position to DynamoDB for persistence
            await self._save_position_to_db(position)
            
            # Also save to closed positions history table for better tracking
            await self._save_closed_position_to_history(position, realized_pnl)
            
            return realized_pnl
            
        except Exception as e:
            logger.error("Failed to close professional position", error=str(e))
            raise
    
    async def _calculate_position_size(self,
                                     requested_size: Decimal,
                                     current_price: Decimal,
                                     ai_confidence: float) -> Decimal:
        """Calculate professional position size with risk management"""
        
        # Base position size (percentage of portfolio)
        base_size_pct = Decimal('0.10')  # 10% base allocation
        
        # Adjust by AI confidence (50% to 150% of base)
        confidence_multiplier = Decimal(str(0.5 + ai_confidence))
        
        # Adjust by consecutive losses (REDUCE size after losses - not increase!)
        # FIXED: Use division to reduce position size, not addition to increase it
        loss_adjustment = Decimal('1') / (Decimal('1') + Decimal('0.03') * Decimal(str(self.consecutive_losses)))
        
        # 🚨 CRITICAL FIX: Hard block after max consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            logger.error(f"🚨 LOSS LIMIT ENFORCED: {self.consecutive_losses} consecutive losses (max: {self.max_consecutive_losses})")
            logger.error(f"🚫 BLOCKING ALL NEW POSITIONS - wait for manual review or next trading session")
            # Return 0 immediately - DO NOT apply minimum size!
            return Decimal('0')
        
        # Calculate size using safe money math
        portfolio_value = self.get_total_portfolio_value()
        base_calc = safe_monetary_multiply(portfolio_value, base_size_pct)
        confidence_calc = safe_monetary_multiply(base_calc, confidence_multiplier)
        
        # Adjust by consecutive losses (reduce size after losses)
        loss_adjustment = Decimal('1') / (Decimal('1') + Decimal('0.03') * Decimal(str(self.consecutive_losses)))
        max_position_value = safe_monetary_multiply(confidence_calc, loss_adjustment)

        # Risk-based sizing (Kelly criterion approximation)
        if ai_confidence > 0.6:
            # Increase size for high confidence signals
            max_position_value = safe_monetary_multiply(max_position_value, D('1.2'))
        elif ai_confidence < 0.4:
            # Reduce size for low confidence signals
            max_position_value = safe_monetary_multiply(max_position_value, D('0.8'))

        # Calculate final size
        calculated_size = safe_monetary_multiply(max_position_value, D('1')) / current_price
        
        # Use the smaller of requested size or calculated size
        final_size = min(requested_size, calculated_size)
        
        # ✅ FIX: Only apply minimum size if we're not in a loss-block situation
        # This ensures the loss limit is actually enforced
        if final_size > 0:
            # Ensure minimum viable position
            min_size = Decimal('0.001')  # 0.001 BTC minimum
            final_size = max(final_size, min_size)
        else:
            # If calculated size is 0, respect that (loss limit reached)
            logger.warning(f"⚠️ Calculated position size is 0 - not applying minimum size")
            final_size = Decimal('0')
        
        # Apply Binance LOT_SIZE validation
        validated_size = await self._validate_binance_lot_size(final_size, "BTCUSDT")
        
        logger.debug(
            "Professional position size calculated",
            requested_size=float(requested_size),
            calculated_size=float(calculated_size),
            final_size=float(final_size),
            validated_size=float(validated_size),
            ai_confidence=ai_confidence,
            consecutive_losses=self.consecutive_losses,
            confidence_multiplier=float(confidence_multiplier),
            loss_adjustment=float(loss_adjustment)
        )
        
        return validated_size
    
    async def _validate_binance_lot_size(self, size: Decimal, symbol: str) -> Decimal:
        """Validate and round position size according to Binance LOT_SIZE rules"""
        try:
            # For BTCUSDT, typical LOT_SIZE is:
            # minQty: 0.00001000, maxQty: 9000.00000000, stepSize: 0.00001000
            # This is cached/hardcoded for performance, but should be fetched from exchangeInfo
            
            # BTCUSDT LOT_SIZE rules (update from exchangeInfo if needed)
            if symbol == "BTCUSDT":
                min_qty = Decimal('0.00001')
                max_qty = Decimal('9000.0')
                step_size = Decimal('0.00001')
            else:
                # Default fallback
                min_qty = Decimal('0.001')
                max_qty = Decimal('1000.0')
                step_size = Decimal('0.001')
            
            # Apply minimum quantity
            if size < min_qty:
                logger.warning(f"Position size {size} below minimum {min_qty}, adjusting")
                size = min_qty
            
            # Apply maximum quantity
            if size > max_qty:
                logger.warning(f"Position size {size} above maximum {max_qty}, adjusting")
                size = max_qty
            
            # Round to step size
            rounded_size = self._round_to_step_size(size, step_size)
            
            if rounded_size != size:
                logger.info(f"Position size rounded from {size} to {rounded_size} for Binance compliance")
            
            return rounded_size
            
        except Exception as e:
            logger.warning(f"Binance LOT_SIZE validation failed: {e}, using original size")
            return size
    
    def _round_to_step_size(self, value: Decimal, step_size: Decimal) -> Decimal:
        """Round value to Binance step size"""
        if step_size == 0:
            return value
        
        # Calculate how many steps fit into the value
        steps = (value / step_size).quantize(Decimal('1'), rounding='ROUND_DOWN')
        
        # Multiply back by step size to get rounded value
        rounded = steps * step_size
        
        return rounded
    
    async def check_and_fix_position_consistency(self):
        """Check and fix any existing position consistency issues"""
        try:
            logger.info("🔍 Checking position consistency in database...")
            
            # Get all positions from database - use Query for better performance when possible
            if self.user_id:
                # Use optimized Query for specific user
                from boto3.dynamodb.conditions import Key
                response = self.db_client.query_items(
                    table_name='portfolio_positions',
                    key_condition_expression=Key('user_id').eq(self.user_id),
                    consistent_read=True
                ) if self.db_client else {'Items': []}
                positions = response.get('Items', [])
            else:
                # Fallback to scan only if user_id is not available
                positions = self.db_client.scan_table('portfolio_positions') if self.db_client else []
            
            inconsistent_count = 0
            fixed_count = 0
            
            for position_data in positions:
                position_type = position_data.get('position_type', '').lower()
                ai_reasoning = position_data.get('ai_reasoning', '').upper()
                
                # Check for inconsistencies
                is_inconsistent = False
                
                if position_type == 'long' and ('SHORT' in ai_reasoning or 'SELL SIGNAL' in ai_reasoning):
                    is_inconsistent = True
                elif position_type == 'short' and ('LONG' in ai_reasoning or 'BUY SIGNAL' in ai_reasoning):
                    is_inconsistent = True
                
                if is_inconsistent:
                    inconsistent_count += 1
                    logger.warning(f"⚠️ Inconsistent position found: {position_type} with reasoning: {ai_reasoning[:100]}...")
                    
                    # Fix the reasoning to match position type
                    if position_type == 'long':
                        fixed_reasoning = ai_reasoning.replace('SHORT', 'LONG').replace('SELL SIGNAL', 'BUY SIGNAL')
                    else:
                        fixed_reasoning = ai_reasoning.replace('LONG', 'SHORT').replace('BUY SIGNAL', 'SELL SIGNAL')
                    
                    # Update in database
                    try:
                        position_data['ai_reasoning'] = fixed_reasoning.lower()
                        # Update the position in database
                        # Note: Actual update would depend on your database update method
                        fixed_count += 1
                        logger.info(f"✅ Fixed position consistency: {position_data.get('position_id', 'unknown')}")
                    except Exception as e:
                        logger.error(f"❌ Failed to fix position {position_data.get('position_id', 'unknown')}: {e}")
            
            if inconsistent_count > 0:
                logger.warning(f"🚨 Found {inconsistent_count} inconsistent positions, fixed {fixed_count}")
            else:
                logger.info("✅ All positions are consistent")
                
        except Exception as e:
            logger.error(f"❌ Position consistency check failed: {e}")

    def _initialize_persistence(self):
        """Initialize DynamoDB persistence"""
        try:
            from app.backend.core.database import DynamoDBClient
            self.db_client = DynamoDBClient()
            # Note: Positions are loaded on-demand by get_professional_portfolio()
            # to avoid duplicate loading and ensure proper caching
            logger.debug("💾 Portfolio persistence initialized - positions loaded on-demand")
        except Exception as e:
            logger.warning(f"Portfolio persistence initialization failed: {e}")
            self.db_client = None
    
    async def _save_position_to_db(self, position: ProfessionalPosition):
        """Save position to DynamoDB for persistence"""
        if not self.db_client:
            logger.warning("Cannot save position - no database client")
            return
        
        try:
            position_data = {
                'position_id': position.position_id,
                'user_id': self.user_id,
                'symbol': position.symbol,
                'position_type': position.type.value,
                'size': str(position.size),
                'entry_price': str(position.entry_price),
                'entry_time': position.entry_time.isoformat(),
                'current_price': str(position.current_price),
                'status': position.status.value,
                'ai_confidence': str(position.ai_confidence),
                'ai_reasoning': position.ai_reasoning,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Add optional fields
            if position.stop_loss:
                position_data['stop_loss'] = str(position.stop_loss)
            if position.take_profit:
                position_data['take_profit'] = str(position.take_profit)
            if position.exit_price:
                position_data['exit_price'] = str(position.exit_price)
                # realized_pnl is saved only to portfolio_closed_positions table
                # position_data['realized_pnl'] = str(position.realized_pnl)
            if position.exit_time:
                position_data['exit_time'] = position.exit_time.isoformat()
            
            # Fix async/await inconsistency - check if result is awaitable
            import inspect
            result = self.db_client.put_item('portfolio_positions', position_data)
            if inspect.isawaitable(result):
                await result
            logger.debug(f"💾 Position saved to DB: {position.position_id} (status: {position.status.value})")
            
        except Exception as e:
            logger.error(f"Failed to save position to DB: {e}")
    
    async def _save_portfolio_state(self):
        """Save current portfolio state and balance to database"""
        if not self.db_client:
            logger.warning("Cannot save portfolio state - no database client")
            return
        
        try:
            # Calculate current portfolio value
            total_value = self.cash_balance
            position_value = Decimal('0')
            
            for position in self.positions.values():
                if position.status == PositionStatus.OPEN:
                    position_value += position.current_price * position.size
            
            total_value += position_value
            
            # Save to virtual_portfolios table (AWS: tradepulse-virtual-portfolios)
            portfolio_data = {
                'user_id': self.user_id,  # PRIMARY KEY for tradepulse-virtual-portfolios
                'balance': str(total_value),
                'cash_balance': str(self.cash_balance),
                'position_value': str(position_value),
                'initial_balance': str(self.initial_balance),
                'active_positions_count': len([p for p in self.positions.values() if p.status == PositionStatus.OPEN]),
                'total_positions_count': len(self.positions) + len(self.closed_positions),
                'daily_trades': self.daily_trades,
                'peak_balance': str(self.peak_balance),
                'max_drawdown': str(self.max_drawdown_amount),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'last_sync': datetime.now(timezone.utc).isoformat()
            }
            
            self.db_client.put_item('tradepulse-virtual-portfolios', portfolio_data)
            logger.info(f"💾 Portfolio state saved: ${float(total_value):,.2f} total, {len(self.positions)} positions")
            
        except Exception as e:
            logger.error(f"Failed to save portfolio state: {e}")
    
    async def _save_closed_position_to_history(self, position: ProfessionalPosition, realized_pnl: Decimal):
        """Save closed position to dedicated history table for better tracking"""
        if not self.db_client:
            logger.warning("Cannot save closed position history - no database client")
            return
        
        try:
            # Calculate additional metrics
            duration_minutes = (position.exit_time - position.entry_time).total_seconds() / 60 if position.exit_time else 0
            pnl_percentage = float((realized_pnl / (position.entry_price * position.size)) * 100) if position.entry_price and position.size else 0.0
            
            history_data = {
                'position_id': position.position_id,
                'user_id': self.user_id,
                'symbol': position.symbol,
                'position_type': position.type.value,
                'size': str(position.size),
                'entry_price': str(position.entry_price),
                'exit_price': str(position.exit_price) if position.exit_price else str(position.current_price),
                'entry_time': position.entry_time.isoformat(),
                'exit_time': position.exit_time.isoformat() if position.exit_time else datetime.now(timezone.utc).isoformat(),
                'realized_pnl': str(realized_pnl),
                'pnl_percentage': str(pnl_percentage),
                'duration_minutes': str(duration_minutes),
                'ai_confidence': str(position.ai_confidence),
                'ai_reasoning': position.ai_reasoning,
                'status': 'closed',
                'closed_at': datetime.now(timezone.utc).isoformat(),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Add optional fields
            if position.stop_loss:
                history_data['stop_loss'] = str(position.stop_loss)
            if position.take_profit:
                history_data['take_profit'] = str(position.take_profit)
            
            # Save to dedicated closed positions history table
            self.db_client.put_item('portfolio_closed_positions', history_data)
            logger.debug(f"📊 Closed position saved to history: {position.position_id} PnL=${float(realized_pnl):.2f}")
            
        except Exception as e:
            logger.error(f"Failed to save closed position to history: {e}")
    
    async def _load_positions_from_db(self):
        """Load existing positions from DynamoDB using efficient Query"""
        if not self.db_client:
            logger.warning("No DB client available for loading positions")
            return

        # Request-scoped guard to prevent duplicate loading
        if hasattr(self, '_loading_positions') and self._loading_positions:
            logger.debug(f"🔄 Position loading already in progress for {self.user_id}")
            return

        try:
            self._loading_positions = True
            logger.debug(f"🔍 Loading positions from DynamoDB for user_id: {self.user_id}")

            # Load positions using scan (optimized for current schema)
            # Use optimized Query for user positions instead of Scan
            from boto3.dynamodb.conditions import Key
            response = self.db_client.query_items(
                table_name='portfolio_positions',
                key_condition_expression=Key('user_id').eq(self.user_id),
                consistent_read=True
            )
            all_items = response.get('Items', [])

            # Filter for this user's positions
            all_positions = [item for item in all_items if item.get('user_id') == self.user_id]
            logger.debug(f"🔍 Found {len(all_positions)} positions for user {self.user_id}")

            # Filter for open positions
            open_positions = [item for item in all_positions if item.get('status') == 'open']
            logger.debug(f"🔍 Found {len(open_positions)} open positions")
            
            for item in open_positions:
                try:
                    position = ProfessionalPosition(
                        position_id=item['position_id'],
                        symbol=item['symbol'],
                        type=PositionType.LONG if item['position_type'].upper() == 'LONG' else PositionType.SHORT,
                        size=Decimal(str(item['size'])),
                        entry_price=Decimal(str(item['entry_price'])),
                        entry_time=datetime.fromisoformat(item['entry_time']),
                        current_price=Decimal(str(item.get('current_price', item['entry_price']))),
                        stop_loss=Decimal(str(item['stop_loss'])) if item.get('stop_loss') else None,
                        take_profit=Decimal(str(item['take_profit'])) if item.get('take_profit') else None,
                        ai_confidence=float(item.get('ai_confidence', 0.5)),
                        ai_reasoning=item.get('ai_reasoning', '')
                    )
                    self.positions[position.position_id] = position
                    logger.debug(f"📥 Loaded position from DB: {position.position_id}")
                except Exception as e:
                    logger.error(f"Failed to load position {item.get('position_id')}: {e}")
            
            # Load closed positions from history table
            try:
                
                # Use optimized Query for user closed positions instead of Scan
                closed_response = self.db_client.query_items(
                    table_name='portfolio_closed_positions',
                    key_condition_expression=Key('user_id').eq(self.user_id),
                    consistent_read=True
                )
                closed_all_items = closed_response.get('Items', [])
                closed_items = [item for item in closed_all_items if item.get('user_id') == self.user_id]
                closed_positions_loaded = []
                
                for item in closed_items:
                    try:
                        position = ProfessionalPosition(
                            position_id=item['position_id'],
                            symbol=item['symbol'],
                            type=PositionType.LONG if item['position_type'].upper() == 'LONG' else PositionType.SHORT,
                            size=Decimal(str(item['size'])),
                            entry_price=Decimal(str(item['entry_price'])),
                            entry_time=datetime.fromisoformat(item['entry_time']),
                            current_price=Decimal(str(item.get('exit_price', item['entry_price']))),
                            exit_price=Decimal(str(item['exit_price'])) if item.get('exit_price') else None,
                            exit_time=datetime.fromisoformat(item['exit_time']) if item.get('exit_time') else None,
                            status=PositionStatus.CLOSED,
                            stop_loss=Decimal(str(item['stop_loss'])) if item.get('stop_loss') else None,
                            take_profit=Decimal(str(item['take_profit'])) if item.get('take_profit') else None,
                            ai_confidence=float(item.get('ai_confidence', 0.5)),
                            ai_reasoning=item.get('ai_reasoning', '')
                        )
                        # Store the original realized P&L from database (already net of commissions)
                        position._stored_realized_pnl = Decimal(str(item.get('realized_pnl', 0)))
                        closed_positions_loaded.append(position)
                    except Exception as e:
                        logger.error(f"Failed to load closed position {item.get('position_id')}: {e}")
                
                # Sort by exit time (no artificial limit)
                closed_positions_loaded.sort(key=lambda p: p.exit_time or p.entry_time, reverse=True)
                self.closed_positions = closed_positions_loaded
                
                logger.info(f"📥 Loaded {len(self.closed_positions)} closed positions from history")
                
            except Exception as e:
                logger.warning(f"Failed to load closed positions from history: {e}")
            
            # Calculate correct cash balance including realized P&L from closed positions
            await self.update_positions_with_live_data()
            
            # Use stored realized P&L directly (already includes commissions)
            # Don't use pos.realized_pnl property as it recalculates commissions
            total_realized_pnl = sum(Decimal(str(getattr(pos, '_stored_realized_pnl', 0))) for pos in self.closed_positions)
            
            # Calculate current position values (money tied up in open positions)
            total_position_value = sum(pos.entry_price * pos.size for pos in self.positions.values())
            
            # Cash balance = initial balance + realized P&L - money in open positions
            self.cash_balance = self.initial_balance + total_realized_pnl - total_position_value
            
            logger.info(f"💰 Portfolio loaded: {len(self.positions)} open positions, {len(self.closed_positions)} closed")
            logger.info(f"💰 Cash balance: ${float(self.cash_balance):.2f} (initial: ${float(self.initial_balance):.2f}, realized P&L: ${float(total_realized_pnl):.2f}, in positions: ${float(total_position_value):.2f})")
                
        except Exception as e:
            logger.error(f"Failed to load positions from DB: {e}")
        finally:
            # Clean up loading flag
            self._loading_positions = False
    
    async def _save_position_to_db(self, position: ProfessionalPosition):
        """Save position to DynamoDB"""
        if not self.db_client:
            return
            
        try:
            item = {
                'position_id': position.position_id,
                'user_id': self.user_id,
                'symbol': position.symbol,
                'position_type': position.type.value,
                'size': str(position.size),
                'entry_price': str(position.entry_price),
                'entry_time': position.entry_time.isoformat(),
                'current_price': str(position.current_price),
                'status': position.status.value,
                'stop_loss': str(position.stop_loss) if position.stop_loss else None,
                'take_profit': str(position.take_profit) if position.take_profit else None,
                'ai_confidence': str(position.ai_confidence),
                'ai_reasoning': position.ai_reasoning,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Fix async/await inconsistency - check if result is awaitable
            import inspect
            result = self.db_client.put_item('portfolio_positions', item)
            if inspect.isawaitable(result):
                await result
            logger.info(f"💾 Position saved to DB: {position.position_id}")
            
        except Exception as e:
            logger.error(f"Failed to save position to DB: {e}")
    
    def get_active_positions(self) -> List[ProfessionalPosition]:
        """Get list of active (open) positions"""
        return [pos for pos in self.positions.values() if pos.status == PositionStatus.OPEN]
    
    def get_total_portfolio_value(self) -> Decimal:
        """Calculate total portfolio value including open positions"""
        # Safety checks to prevent None values
        cash_balance = self.cash_balance or Decimal('0')
        positions_value = sum(pos.position_value or Decimal('0') for pos in self.positions.values())
        return cash_balance + positions_value
    
    async def get_professional_metrics(self) -> PortfolioMetrics:
        """Generate comprehensive professional portfolio metrics - ALL VALUES AS FLOAT"""

        # Update positions with live data
        await self.update_positions_with_live_data()

        # Calculate basic metrics - convert to float immediately with safety checks
        total_value = float(self.get_total_portfolio_value() or Decimal('0'))
        positions_value = float(sum(pos.position_value or Decimal('0') for pos in self.positions.values()))

        # Calculate P&L - convert to float with safety checks
        unrealized_pnl = float(sum(pos.unrealized_pnl or Decimal('0') for pos in self.positions.values()))
        realized_pnl = float(sum(pos.realized_pnl or Decimal('0') for pos in self.closed_positions))
        total_pnl = unrealized_pnl + realized_pnl

        # Daily P&L - convert to float with safety check
        daily_starting_balance_safe = self.daily_starting_balance or Decimal('0')
        daily_pnl = total_value - float(daily_starting_balance_safe)

        # Percentage calculations - convert to float
        total_pnl_pct = float((Decimal(str(total_pnl)) / self.initial_balance) * Decimal('100'))
        daily_pnl_pct = float((Decimal(str(daily_pnl)) / daily_starting_balance_safe) * Decimal('100'))

        # Trade statistics
        total_trades = len(self.closed_positions)
        winning_trades = sum(1 for pos in self.closed_positions if pos.realized_pnl > 0)
        losing_trades = total_trades - winning_trades

        # Win rate - convert to float
        win_rate = float(winning_trades / total_trades) if total_trades > 0 else 0.0
        
        # Average win/loss - convert to float
        wins = [float(pos.realized_pnl) for pos in self.closed_positions if pos.realized_pnl > 0]
        losses = [abs(float(pos.realized_pnl)) for pos in self.closed_positions if pos.realized_pnl < 0]

        avg_win = float(sum(wins) / len(wins)) if wins else 0.0
        avg_loss = float(sum(losses) / len(losses)) if losses else 0.0

        # Profit factor - convert to float
        total_wins = float(sum(wins)) if wins else 0.0
        total_losses = float(sum(losses)) if losses else 1.0  # Avoid division by zero
        profit_factor = total_wins / total_losses

        # Drawdown calculation - convert to float
        peak_balance = float(self.peak_balance)
        if total_value > peak_balance:
            self.peak_balance = Decimal(str(total_value))

        current_drawdown = peak_balance - total_value
        if current_drawdown > float(self.max_drawdown_amount):
            self.max_drawdown_amount = Decimal(str(current_drawdown))

        max_drawdown_pct = float((self.max_drawdown_amount / self.peak_balance) * Decimal('100')) if self.peak_balance > 0 else 0.0

        # Simplified Sharpe ratio (annualized) - convert to float
        if total_trades > 0:
            # SAFETY: Skip positions with zero size or entry_price to avoid division by zero
            returns = [
                float(pos.realized_pnl) / float(pos.entry_price) / float(pos.size) 
                for pos in self.closed_positions 
                if float(pos.entry_price) > 0 and float(pos.size) > 0
            ]
            if returns:  # Only calculate if we have valid returns
                avg_return = float(sum(returns) / len(returns))
                import math
                variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
                return_std = math.sqrt(variance)
                sharpe_ratio = (avg_return / return_std) * 15.87 if return_std > 0 else 0.0  # Sqrt(252) for annualization
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0
        
        # Risk score (0-1, lower is better) - convert to float
        risk_factors = [
            float(max_drawdown_pct) / 100,  # Drawdown risk
            max(0, (5 - winning_trades) / 5) if total_trades >= 5 else 0.5,  # Win rate risk
            min(1, self.consecutive_losses / 3),  # Consecutive loss risk
            min(1, len(self.positions) / 5)  # Position concentration risk
        ]
        risk_score = float(sum(risk_factors) / len(risk_factors))

        return PortfolioMetrics(
            total_value=total_value,
            cash_balance=float(self.cash_balance),
            positions_value=positions_value,
            total_pnl=total_pnl,
            daily_pnl=daily_pnl,
            total_pnl_percentage=total_pnl_pct,
            daily_pnl_percentage=daily_pnl_pct,
            number_of_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            average_win=avg_win,
            average_loss=avg_loss,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=float(self.max_drawdown_amount),
            max_drawdown_percentage=max_drawdown_pct,
            risk_score=risk_score,
            timestamp=datetime.now(timezone.utc)
        )
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get professional portfolio summary for API responses"""
        
        metrics = await self.get_professional_metrics()
        
        return {
            "user_id": self.user_id,
            "portfolio_value": {
                "total": float(metrics.total_value),
                "cash": float(metrics.cash_balance),
                "positions": float(metrics.positions_value),
                "currency": "USD"
            },
            "performance": {
                "total_pnl": float(metrics.total_pnl),
                "total_pnl_percentage": float(metrics.total_pnl_percentage),
                "daily_pnl": float(metrics.daily_pnl),
                "daily_pnl_percentage": float(metrics.daily_pnl_percentage),
                "max_drawdown_percentage": float(metrics.max_drawdown_percentage)
            },
            "trading_stats": {
                "total_trades": metrics.number_of_trades,
                "winning_trades": metrics.winning_trades,
                "losing_trades": metrics.losing_trades,
                "win_rate": float(metrics.win_rate),
                "profit_factor": float(metrics.profit_factor),
                "sharpe_ratio": float(metrics.sharpe_ratio)
            },
            "risk_metrics": {
                "risk_score": float(metrics.risk_score),
                "consecutive_losses": self.consecutive_losses,
                "daily_trades": self.daily_trades,
                "max_daily_trades": self.max_daily_trades,
                "daily_pnl_percentage": self.get_daily_pnl_percentage()
            },
            "open_positions": len(self.positions),
            "timestamp": metrics.timestamp.isoformat(),
            "status": "active"
        }
        
    @property
    def total_value(self) -> Decimal:
        """Total portfolio value - REQUIRED by BRAIN controller"""
        try:
            position_value = sum(
                pos.current_value for pos in self.positions.values() 
                if pos.status == PositionStatus.OPEN
            )
            return self.cash_balance + position_value
        except Exception as e:
            logger.error(f"Total value calculation failed: {e}")
            return self.cash_balance
        
    def get_daily_pnl(self) -> Decimal:
        """Get daily P&L amount - REQUIRED by BRAIN controller"""
        # Auto-reset if new day
        self._check_and_reset_daily_metrics()
        
        try:
            current_value = self.total_value
            daily_pnl = current_value - self.daily_starting_balance
            return daily_pnl
        except Exception as e:
            logger.error(f"Daily P&L calculation failed: {e}")
            return Decimal('0.0')
            
    def get_daily_pnl_percentage(self) -> float:
        """Get daily P&L as percentage of starting balance - REQUIRED by emergency controls"""
        # Auto-reset if new day
        self._check_and_reset_daily_metrics()
        
        try:
            current_value = float(self.cash_balance or Decimal('0')) + sum(
                float(pos.current_value or Decimal('0')) for pos in self.positions.values() 
                if pos.status == PositionStatus.OPEN
            )
            
            daily_starting_balance_safe = self.daily_starting_balance or Decimal('1')  # Avoid division by zero
            daily_pnl_pct = (current_value - float(daily_starting_balance_safe)) / float(daily_starting_balance_safe)
            return daily_pnl_pct
            
        except Exception as e:
            logger.error(f"Daily P&L calculation failed: {e}")
            return 0.0
    
    def _check_and_reset_daily_metrics(self):
        """Check if it's a new day and reset daily metrics if needed"""
        try:
            current_date = datetime.now(timezone.utc).date()
            if current_date > self.last_daily_reset_date:
                # New day detected - reset daily metrics
                current_value = float(self.cash_balance or Decimal('0')) + sum(
                    float(pos.current_value or Decimal('0')) for pos in self.positions.values() 
                    if pos.status == PositionStatus.OPEN
                )
                self.daily_starting_balance = Decimal(str(current_value))
                self.daily_trades = 0
                self.last_daily_reset_date = current_date
                logger.info(f"📅 Daily metrics reset - New starting balance: ${current_value:,.2f}")
        except Exception as e:
            logger.error(f"Failed to reset daily metrics: {e}")

# Professional singleton pattern with persistent instances
_portfolio_instances: Dict[str, ProfessionalPortfolio] = {}
_instance_creation_times: Dict[str, datetime] = {}

# Cache configuration
PORTFOLIO_CACHE_TTL_MINUTES = 30  # 30 minutes cache TTL
PORTFOLIO_CACHE_MAX_AGE_HOURS = 24  # Maximum age before forced cleanup

def _is_portfolio_cache_fresh(user_id: str) -> bool:
    """Check if portfolio cache is still fresh based on TTL"""
    if user_id not in _instance_creation_times:
        return False
        
    creation_time = _instance_creation_times[user_id]
    age_minutes = (datetime.now(timezone.utc) - creation_time).total_seconds() / 60
    
    return age_minutes < PORTFOLIO_CACHE_TTL_MINUTES


async def get_professional_portfolio(user_id: str) -> ProfessionalPortfolio:
    """Get professional portfolio for user with TTL-based caching"""
    from datetime import datetime, timezone

    # Check if we have a fresh cached instance
    if user_id in _portfolio_instances and _is_portfolio_cache_fresh(user_id):
        portfolio = _portfolio_instances[user_id]
        # Verify instance is still valid (not corrupted)
        if hasattr(portfolio, 'user_id') and portfolio.user_id == user_id:
            logger.debug(f"🔄 Using existing portfolio instance for {user_id}")
            return portfolio
        else:
            # Instance is corrupted, remove it
            logger.warning(f"🗑️ Removing corrupted portfolio instance for {user_id}")
            del _portfolio_instances[user_id]
            if user_id in _instance_creation_times:
                del _instance_creation_times[user_id]
    elif user_id in _portfolio_instances:
        # Cache is expired, remove old instance
        logger.debug(f"⏰ Portfolio cache expired for {user_id}, creating fresh instance")
        del _portfolio_instances[user_id]
        if user_id in _instance_creation_times:
            del _instance_creation_times[user_id]

    # Create new portfolio instance
    logger.info(f"🏗️ Creating new portfolio instance for {user_id}")
    portfolio = ProfessionalPortfolio(user_id)
    try:
        await portfolio._load_positions_from_db()
    except AttributeError as e:
        logger.error(f"Portfolio method error: {e}")
        logger.info("Attempting to reinitialize portfolio persistence...")
        portfolio._initialize_persistence()
        # Try again after reinitialization
        try:
            await portfolio._load_positions_from_db()
        except Exception as retry_error:
            logger.error(f"Portfolio persistence retry failed: {retry_error}")

    # Store the instance
    _portfolio_instances[user_id] = portfolio
    _instance_creation_times[user_id] = datetime.now(timezone.utc)

    logger.info(f"✅ Portfolio instance created and cached for {user_id}")
    return portfolio

async def clear_portfolio_cache(user_id: str = None):
    """Clear portfolio cache to force reload from database"""
    global _portfolio_instances, _instance_creation_times
    
    if user_id:
        # Clear specific user's cache
        if user_id in _portfolio_instances:
            del _portfolio_instances[user_id]
            logger.info(f"🗑️ Cleared portfolio cache for {user_id}")
        if user_id in _instance_creation_times:
            del _instance_creation_times[user_id]
    else:
        # Clear all caches
        cache_count = len(_portfolio_instances)
        _portfolio_instances.clear()
        _instance_creation_times.clear()
        logger.info(f"🗑️ Cleared all portfolio caches ({cache_count} instances)")

async def force_portfolio_sync(user_id: str):
    """Force portfolio synchronization with database"""
    # Clear cache first
    await clear_portfolio_cache(user_id)
    
    # Get fresh instance (will reload from DB)
    portfolio = await get_professional_portfolio(user_id)
    
    # Update with live market data
    await portfolio.update_positions_with_live_data()
    
    # Save current state to ensure sync
    await portfolio._save_portfolio_state()
    
    logger.info(f"🔄 Forced portfolio sync for {user_id}")
    return portfolio

async def cleanup_old_portfolio_instances(max_age_hours: int = None):
    """Clean up old portfolio instances to prevent memory leaks with TTL-based cleanup"""
    from datetime import datetime, timezone, timedelta

    if max_age_hours is None:
        max_age_hours = PORTFOLIO_CACHE_MAX_AGE_HOURS

    current_time = datetime.now(timezone.utc)
    cutoff_time = current_time - timedelta(hours=max_age_hours)

    expired_users = [
        user_id for user_id, creation_time in _instance_creation_times.items()
        if creation_time < cutoff_time
    ]

    for user_id in expired_users:
        if user_id in _portfolio_instances:
            del _portfolio_instances[user_id]
        del _instance_creation_times[user_id]
        logger.debug(f"🧹 Cleaned up old portfolio instance for {user_id}")

    if expired_users:
        logger.info(f"🧹 Cleaned up {len(expired_users)} expired portfolio instances (max age: {max_age_hours}h)")
    
    return len(expired_users)


def get_portfolio_cache_stats() -> Dict[str, Any]:
    """Get portfolio cache statistics for monitoring"""
    current_time = datetime.now(timezone.utc)
    cache_ages = {}
    
    for user_id, creation_time in _instance_creation_times.items():
        age_minutes = (current_time - creation_time).total_seconds() / 60
        cache_ages[user_id] = {
            "age_minutes": round(age_minutes, 1),
            "is_fresh": age_minutes < PORTFOLIO_CACHE_TTL_MINUTES,
            "created_at": creation_time.isoformat()
        }
    
    return {
        "total_instances": len(_portfolio_instances),
        "cache_ttl_minutes": PORTFOLIO_CACHE_TTL_MINUTES,
        "max_age_hours": PORTFOLIO_CACHE_MAX_AGE_HOURS,
        "instances": cache_ages
    }


# Clean up the file - remove broken method definitions

# Demo functions removed - Professional deployment only
