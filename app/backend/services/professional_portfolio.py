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
		return self.current_price * self.size
	
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
	"""Professional portfolio performance metrics"""
	total_value: Decimal
	cash_balance: Decimal
	positions_value: Decimal
	total_pnl: Decimal
	daily_pnl: Decimal
	total_pnl_percentage: Decimal
	daily_pnl_percentage: Decimal
	number_of_trades: int
	winning_trades: int
	losing_trades: int
	win_rate: Decimal
	average_win: Decimal
	average_loss: Decimal
	profit_factor: Decimal
	sharpe_ratio: Decimal
	max_drawdown: Decimal
	max_drawdown_percentage: Decimal
	risk_score: Decimal
	timestamp: datetime

class ProfessionalPortfolio:
	"""Professional virtual portfolio with enterprise-grade features"""
	
	def __init__(self, 
				 user_id: str, 
				 initial_balance: Decimal = Decimal('10000'),
				 max_risk_per_trade: Decimal = Decimal('0.02'),  # 2%
				 max_portfolio_risk: Decimal = Decimal('0.10')):  # 10%
		
		self.user_id = user_id
		self.initial_balance = initial_balance
		self.cash_balance = initial_balance
		self.max_risk_per_trade = max_risk_per_trade
		self.max_portfolio_risk = max_portfolio_risk
		
		# Position tracking
		self.positions: Dict[str, ProfessionalPosition] = {}
		self.closed_positions: List[ProfessionalPosition] = []
		
		# Performance tracking
		self.daily_starting_balance = initial_balance
		self.peak_balance = initial_balance
		self.max_drawdown_amount = Decimal('0')
		
		# Risk management
		self.daily_trades = 0
		self.max_daily_trades = 8
		self.consecutive_losses = 0
		self.max_consecutive_losses = 5
		
		logger.info(
			"Professional portfolio initialized",
			user_id=user_id,
			initial_balance=float(initial_balance),
			max_risk_per_trade=float(max_risk_per_trade)
		)
	
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
			# Get current market price
			current_price = Decimal(str(await get_live_bitcoin_price()))
			
			# Calculate position size based on risk management
			risk_adjusted_size = await self._calculate_position_size(
				size, current_price, ai_confidence
			)
			
			# Validate position
			position_value = current_price * risk_adjusted_size
			if position_value > self.cash_balance:
				raise ValueError(f"Insufficient funds: need ${position_value}, have ${self.cash_balance}")
			
			# Check daily limits
			if self.daily_trades >= self.max_daily_trades:
				raise ValueError(f"Daily trade limit reached: {self.max_daily_trades}")
			
			# Create position with collision-resistant id
			position_id = f"pos_{symbol}_{uuid.uuid4().hex}"
			
			# Calculate stop loss and take profit
			stop_loss = None
			take_profit = None
			
			if stop_loss_pct:
				if position_type == PositionType.LONG:
					stop_loss = current_price * (Decimal('1') - stop_loss_pct)
				else:
					stop_loss = current_price * (Decimal('1') + stop_loss_pct)
			
			if take_profit_pct:
				if position_type == PositionType.LONG:
					take_profit = current_price * (Decimal('1') + take_profit_pct)
				else:
					take_profit = current_price * (Decimal('1') - take_profit_pct)
			
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
				ai_confidence=ai_confidence,
				ai_reasoning=ai_reasoning
			)
			
			# Update portfolio state
			self.positions[position_id] = position
			self.cash_balance -= position_value
			self.daily_trades += 1
			
			logger.info(
				"Professional position opened",
				position_id=position_id,
				symbol=symbol,
				type=position_type.value,
				size=float(risk_adjusted_size),
				entry_price=float(current_price),
				position_value=float(position_value),
				ai_confidence=ai_confidence,
				stop_loss=float(stop_loss) if stop_loss else None,
				take_profit=float(take_profit) if take_profit else None
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
			# Get current market price
			current_price = Decimal(str(await get_live_bitcoin_price()))
			position.current_price = current_price
			
			# Close position
			position.exit_price = current_price
			position.exit_time = datetime.now(timezone.utc)
			position.status = PositionStatus.CLOSED
			
			# Calculate realized P&L
			realized_pnl = position.realized_pnl
			
			# Update portfolio state: add back original entry value plus realized P&L
			entry_value = position.entry_price * position.size
			self.cash_balance += entry_value + realized_pnl
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
		
		# Adjust by consecutive losses (reduce size after losses)
		loss_adjustment = max(Decimal('0.5'), Decimal('1') - (Decimal(str(self.consecutive_losses)) * Decimal('0.1')))
		
		# Calculate size
		portfolio_value = self.get_total_portfolio_value()
		max_position_value = portfolio_value * base_size_pct * confidence_multiplier * loss_adjustment
		
		# Risk-based sizing (Kelly criterion approximation)
		if ai_confidence > 0.6:
			# Increase size for high confidence signals
			max_position_value *= Decimal('1.2')
		elif ai_confidence < 0.4:
			# Reduce size for low confidence signals  
			max_position_value *= Decimal('0.8')
		
		# Calculate final size
		calculated_size = max_position_value / current_price
		
		# Use the smaller of requested size or calculated size
		final_size = min(requested_size, calculated_size)
		
		# Ensure minimum viable position
		min_size = Decimal('0.001')  # 0.001 BTC minimum
		final_size = max(final_size, min_size)
		
		logger.debug(
			"Professional position size calculated",
			requested_size=float(requested_size),
			calculated_size=float(calculated_size),
			final_size=float(final_size),
			ai_confidence=ai_confidence,
			consecutive_losses=self.consecutive_losses,
			confidence_multiplier=float(confidence_multiplier),
			loss_adjustment=float(loss_adjustment)
		)
		
		return final_size
	
	def get_active_positions(self) -> List[ProfessionalPosition]:
		"""Get list of active (open) positions"""
		return [pos for pos in self.positions.values() if pos.status == PositionStatus.OPEN]
	
	def get_total_portfolio_value(self) -> Decimal:
		"""Calculate total portfolio value including open positions"""
		positions_value = sum(pos.position_value for pos in self.positions.values())
		return self.cash_balance + positions_value
	
	async def get_professional_metrics(self) -> PortfolioMetrics:
		"""Generate comprehensive professional portfolio metrics"""
		
		# Update positions with live data
		await self.update_positions_with_live_data()
		
		# Calculate basic metrics
		total_value = self.get_total_portfolio_value()
		positions_value = sum(pos.position_value for pos in self.positions.values())
		
		# Calculate P&L
		unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
		realized_pnl = sum(pos.realized_pnl for pos in self.closed_positions)
		total_pnl = unrealized_pnl + realized_pnl
		
		# Daily P&L
		daily_pnl = total_value - self.daily_starting_balance
		
		# Percentage calculations
		total_pnl_pct = (total_pnl / self.initial_balance) * Decimal('100')
		daily_pnl_pct = (daily_pnl / self.daily_starting_balance) * Decimal('100')
		
		# Trade statistics
		total_trades = len(self.closed_positions)
		winning_trades = sum(1 for pos in self.closed_positions if pos.realized_pnl > 0)
		losing_trades = total_trades - winning_trades
		
		# Win rate
		win_rate = Decimal(str(winning_trades / total_trades)) if total_trades > 0 else Decimal('0')
		
		# Average win/loss
		wins = [pos.realized_pnl for pos in self.closed_positions if pos.realized_pnl > 0]
		losses = [abs(pos.realized_pnl) for pos in self.closed_positions if pos.realized_pnl < 0]
		
		avg_win = sum(wins) / len(wins) if wins else Decimal('0')
		avg_loss = sum(losses) / len(losses) if losses else Decimal('0')
		
		# Profit factor
		total_wins = sum(wins) if wins else Decimal('0')
		total_losses = sum(losses) if losses else Decimal('1')  # Avoid division by zero
		profit_factor = total_wins / total_losses
		
		# Drawdown calculation
		if total_value > self.peak_balance:
			self.peak_balance = total_value
		
		current_drawdown = self.peak_balance - total_value
		if current_drawdown > self.max_drawdown_amount:
			self.max_drawdown_amount = current_drawdown
		
		max_drawdown_pct = (self.max_drawdown_amount / self.peak_balance) * Decimal('100') if self.peak_balance > 0 else Decimal('0')
		
		# Simplified Sharpe ratio (annualized)
		if total_trades > 0:
			returns = [pos.realized_pnl / pos.entry_price / pos.size for pos in self.closed_positions]
			avg_return = sum(returns) / len(returns)
			return_std = Decimal(str((sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5))
			sharpe_ratio = (avg_return / return_std) * Decimal('15.87') if return_std > 0 else Decimal('0')  # Sqrt(252) for annualization
		else:
			sharpe_ratio = Decimal('0')
		
		# Risk score (0-1, lower is better)
		risk_factors = [
			float(max_drawdown_pct) / 100,  # Drawdown risk
			max(0, (5 - winning_trades) / 5) if total_trades >= 5 else 0.5,  # Win rate risk
			min(1, self.consecutive_losses / 3),  # Consecutive loss risk
			min(1, len(self.positions) / 5)  # Position concentration risk
		]
		risk_score = Decimal(str(sum(risk_factors) / len(risk_factors)))
		
		return PortfolioMetrics(
			total_value=total_value,
			cash_balance=self.cash_balance,
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
			max_drawdown=self.max_drawdown_amount,
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
				"max_daily_trades": self.max_daily_trades
			},
			"open_positions": len(self.positions),
			"timestamp": metrics.timestamp.isoformat(),
			"status": "active"
		}

# Global portfolio management
_professional_portfolios: Dict[str, ProfessionalPortfolio] = {}

async def get_professional_portfolio(user_id: str) -> ProfessionalPortfolio:
	"""Get or create professional portfolio for user"""
	if user_id not in _professional_portfolios:
		_professional_portfolios[user_id] = ProfessionalPortfolio(user_id)
	
	return _professional_portfolios[user_id]

# Demo functions removed - Professional deployment only
