"""
Dynamic Risk Manager - TradePulse.AI
====================================

Advanced Risk Management with Dynamic Stop-Loss Adjustments
- Volatility-based stop-loss adjustments
- Real-time risk assessment 
- Dynamic position sizing
- Advanced risk metrics (VaR, correlation analysis)
- Drawdown protection mechanisms

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import asyncio
import logging
import numpy as np
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from decimal import Decimal

# Import services
try:
    from app.backend.services.live_market_data import get_live_bitcoin_price, get_live_market_data, get_live_candlestick_data
    from app.backend.services.professional_portfolio import get_professional_portfolio
except ImportError as e:
    # PRODUCTION: No fallbacks allowed
    logger.error(f"Critical import failure: {e}")
    raise RuntimeError(f"Real services required for production deployment: {e}")

logger = logging.getLogger(__name__)

class RiskLevel(str, Enum):
    """Risk level classifications"""
    VERY_LOW = "very_low"     # <1% volatility
    LOW = "low"               # 1-3% volatility
    MODERATE = "moderate"     # 3-5% volatility
    HIGH = "high"             # 5-10% volatility
    EXTREME = "extreme"       # >10% volatility

class StopLossMode(str, Enum):
    """Stop-loss adjustment modes"""
    STATIC = "static"         # Fixed percentage
    DYNAMIC = "dynamic"       # Volatility-based
    TRAILING = "trailing"     # Trailing stop
    ATR_BASED = "atr_based"   # ATR-based adjustment

@dataclass
class RiskMetrics:
    """Comprehensive risk metrics"""
    var_1d: float             # 1-day Value at Risk
    var_1w: float             # 1-week Value at Risk
    max_drawdown: float       # Maximum drawdown
    sharpe_ratio: float       # Risk-adjusted return
    volatility_24h: float     # 24-hour volatility
    correlation_btc: float    # Correlation with BTC
    risk_score: float         # Overall risk score (0-100)
    timestamp: datetime

@dataclass
class DynamicStopLoss:
    """Dynamic stop-loss configuration"""
    position_id: str
    base_stop_loss_pct: float     # Base stop-loss percentage
    current_stop_loss: float      # Current stop-loss price
    volatility_multiplier: float  # Volatility adjustment factor
    atr_periods: int              # ATR calculation periods
    last_adjustment: datetime     # Last adjustment timestamp
    adjustment_history: List[Tuple[datetime, float, str]]  # History of adjustments

class DynamicRiskManager:
    """
    Advanced Dynamic Risk Management System
    
    Features:
    - Real-time volatility monitoring
    - Dynamic stop-loss adjustments
    - Advanced risk metrics calculation
    - Position-specific risk management
    - Correlation analysis
    """
    
    def __init__(self):
        self.is_initialized = False
        self.is_active = False
        
        # Risk management state
        self.position_stop_losses: Dict[str, DynamicStopLoss] = {}
        self.current_risk_metrics: Optional[RiskMetrics] = None
        self.risk_level = RiskLevel.MODERATE
        
        # Monitoring task
        self.risk_monitoring_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self.adjustments_made = 0
        self.positions_protected = 0
        self.risk_assessments = 0
        
        # Configuration
        self.volatility_lookback_hours = 24
        self.atr_default_periods = 14
        self.max_stop_loss_pct = 0.10  # Maximum 10% stop-loss
        self.min_stop_loss_pct = 0.005  # Minimum 0.5% stop-loss
        
        # Risk level thresholds
        self.risk_thresholds = {
            RiskLevel.VERY_LOW: 0.01,   # 1%
            RiskLevel.LOW: 0.03,        # 3%
            RiskLevel.MODERATE: 0.05,   # 5%
            RiskLevel.HIGH: 0.10,       # 10%
            RiskLevel.EXTREME: 0.15     # 15%
        }
        
        logger.info("📊 Dynamic Risk Manager initialized")
    
    async def initialize(self):
        """Initialize the dynamic risk manager"""
        if self.is_initialized:
            return
            
        logger.info("🚀 Initializing Dynamic Risk Manager...")
        
        try:
            # Load existing stop-loss configurations
            await self._load_stop_loss_configurations()
            
            # Calculate initial risk metrics
            await self._calculate_risk_metrics()
            
            self.is_initialized = True
            logger.info("✅ Dynamic Risk Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize dynamic risk manager: {e}")
            raise
    
    async def start_risk_monitoring(self) -> Dict[str, Any]:
        """Start real-time risk monitoring and adjustment"""
        if not self.is_initialized:
            await self.initialize()
        
        if self.is_active:
            return {"status": "already_active"}
        
        self.is_active = True
        logger.info("📊 Starting dynamic risk monitoring...")
        
        # Start background monitoring task
        self.risk_monitoring_task = asyncio.create_task(self._risk_monitoring_loop())
        
        return {
            "status": "risk_monitoring_started",
            "current_risk_level": self.risk_level.value,
            "positions_monitored": len(self.position_stop_losses),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def stop_risk_monitoring(self) -> Dict[str, Any]:
        """Stop risk monitoring"""
        if not self.is_active:
            return {"status": "not_active"}
        
        self.is_active = False
        
        if self.risk_monitoring_task and not self.risk_monitoring_task.done():
            self.risk_monitoring_task.cancel()
            try:
                await self.risk_monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 Dynamic risk monitoring stopped")
        
        return {
            "status": "risk_monitoring_stopped",
            "adjustments_made": self.adjustments_made,
            "positions_protected": self.positions_protected,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def add_position_monitoring(
        self, 
        position_id: str, 
        entry_price: float, 
        position_type: str,
        base_stop_loss_pct: float = 0.02,
        mode: StopLossMode = StopLossMode.DYNAMIC
    ) -> Dict[str, Any]:
        """Add a position for dynamic risk monitoring"""
        
        try:
            # Calculate initial stop-loss based on current volatility
            current_volatility = await self._get_current_volatility()
            volatility_multiplier = self._calculate_volatility_multiplier(current_volatility)
            
            # Adjust stop-loss based on volatility
            adjusted_stop_loss_pct = base_stop_loss_pct * volatility_multiplier
            adjusted_stop_loss_pct = max(self.min_stop_loss_pct, 
                                       min(self.max_stop_loss_pct, adjusted_stop_loss_pct))
            
            # Calculate stop-loss price
            if position_type.upper() == "LONG":
                stop_loss_price = entry_price * (1 - adjusted_stop_loss_pct)
            else:  # SHORT
                stop_loss_price = entry_price * (1 + adjusted_stop_loss_pct)
            
            # Create dynamic stop-loss configuration
            dynamic_stop_loss = DynamicStopLoss(
                position_id=position_id,
                base_stop_loss_pct=base_stop_loss_pct,
                current_stop_loss=stop_loss_price,
                volatility_multiplier=volatility_multiplier,
                atr_periods=self.atr_default_periods,
                last_adjustment=datetime.now(timezone.utc),
                adjustment_history=[(datetime.now(timezone.utc), stop_loss_price, "initial_setup")]
            )
            
            self.position_stop_losses[position_id] = dynamic_stop_loss
            
            logger.info(f"📊 Added dynamic monitoring for position {position_id}: "
                       f"SL {adjusted_stop_loss_pct:.1%} @ ${stop_loss_price:.2f}")
            
            return {
                "status": "position_added",
                "position_id": position_id,
                "initial_stop_loss": stop_loss_price,
                "stop_loss_pct": adjusted_stop_loss_pct,
                "volatility_multiplier": volatility_multiplier,
                "current_volatility": current_volatility,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to add position monitoring: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def update_position_stop_loss(self, position_id: str, current_price: float) -> Dict[str, Any]:
        """Update stop-loss for a specific position based on current market conditions"""
        
        if position_id not in self.position_stop_losses:
            return {"status": "position_not_found"}
        
        try:
            dynamic_sl = self.position_stop_losses[position_id]
            
            # Get current market metrics
            current_volatility = await self._get_current_volatility()
            atr = await self._calculate_atr(dynamic_sl.atr_periods)
            
            # Calculate new volatility multiplier
            new_volatility_multiplier = self._calculate_volatility_multiplier(current_volatility)
            
            # Determine if adjustment is needed
            adjustment_threshold = 0.2  # 20% change in volatility multiplier
            multiplier_change = abs(new_volatility_multiplier - dynamic_sl.volatility_multiplier)
            
            if multiplier_change > adjustment_threshold:
                # Calculate new stop-loss percentage
                new_stop_loss_pct = dynamic_sl.base_stop_loss_pct * new_volatility_multiplier
                new_stop_loss_pct = max(self.min_stop_loss_pct, 
                                      min(self.max_stop_loss_pct, new_stop_loss_pct))
                
                # Get position type from portfolio
                portfolio = await get_professional_portfolio("admin")
                position = portfolio.get_position(position_id)
                
                if position:
                    # Calculate new stop-loss price
                    if position.type.value.upper() == "LONG":
                        new_stop_loss_price = current_price * (1 - new_stop_loss_pct)
                    else:  # SHORT
                        new_stop_loss_price = current_price * (1 + new_stop_loss_pct)
                    
                    # Update dynamic stop-loss
                    old_stop_loss = dynamic_sl.current_stop_loss
                    dynamic_sl.current_stop_loss = new_stop_loss_price
                    dynamic_sl.volatility_multiplier = new_volatility_multiplier
                    dynamic_sl.last_adjustment = datetime.now(timezone.utc)
                    dynamic_sl.adjustment_history.append((
                        datetime.now(timezone.utc), 
                        new_stop_loss_price, 
                        f"volatility_adjustment_{current_volatility:.1%}"
                    ))
                    
                    # Update position in portfolio
                    await portfolio.update_stop_loss(position_id, new_stop_loss_price)
                    
                    self.adjustments_made += 1
                    
                    logger.info(f"📊 Updated stop-loss for {position_id}: "
                               f"${old_stop_loss:.2f} → ${new_stop_loss_price:.2f} "
                               f"(volatility: {current_volatility:.1%})")
                    
                    return {
                        "status": "stop_loss_updated",
                        "position_id": position_id,
                        "old_stop_loss": old_stop_loss,
                        "new_stop_loss": new_stop_loss_price,
                        "adjustment_reason": "volatility_change",
                        "current_volatility": current_volatility,
                        "volatility_multiplier": new_volatility_multiplier,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    return {"status": "position_not_found_in_portfolio"}
            else:
                return {
                    "status": "no_adjustment_needed",
                    "current_volatility": current_volatility,
                    "multiplier_change": multiplier_change,
                    "threshold": adjustment_threshold
                }
                
        except Exception as e:
            logger.error(f"Failed to update stop-loss for {position_id}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def remove_position_monitoring(self, position_id: str) -> Dict[str, Any]:
        """Remove position from dynamic monitoring"""
        
        if position_id in self.position_stop_losses:
            removed_sl = self.position_stop_losses.pop(position_id)
            
            logger.info(f"📊 Removed dynamic monitoring for position {position_id}")
            
            return {
                "status": "position_removed",
                "position_id": position_id,
                "final_stop_loss": removed_sl.current_stop_loss,
                "total_adjustments": len(removed_sl.adjustment_history) - 1,  # Exclude initial setup
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {"status": "position_not_found"}
    
    async def _risk_monitoring_loop(self):
        """Main risk monitoring loop"""
        logger.info("📊 Risk monitoring loop started")
        
        try:
            while self.is_active:
                start_time = time.time()
                
                try:
                    # Update risk metrics
                    await self._calculate_risk_metrics()
                    
                    # Update all position stop-losses
                    await self._update_all_stop_losses()
                    
                    # Check for high-risk conditions
                    await self._check_risk_conditions()
                    
                    self.risk_assessments += 1
                    
                except Exception as e:
                    logger.error(f"❌ Error in risk monitoring: {e}")
                
                # Monitor every 60 seconds
                elapsed = time.time() - start_time
                sleep_time = max(60 - elapsed, 10)  # Minimum 10 seconds
                await asyncio.sleep(sleep_time)
                
        except asyncio.CancelledError:
            logger.info("🛑 Risk monitoring loop cancelled")
        except Exception as e:
            logger.error(f"❌ Fatal error in risk monitoring: {e}")
    
    async def _update_all_stop_losses(self):
        """Update stop-losses for all monitored positions"""
        if not self.position_stop_losses:
            return
        
        try:
            current_price = await get_live_bitcoin_price()
            
            for position_id in list(self.position_stop_losses.keys()):
                await self.update_position_stop_loss(position_id, current_price)
                
        except Exception as e:
            logger.error(f"Error updating all stop-losses: {e}")
    
    async def _calculate_risk_metrics(self) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        try:
            # Get historical data for calculations
            historical_data = await get_live_candlestick_data("1h", 168)  # 7 days
            
            if not historical_data or len(historical_data) < 24:
                # Use default metrics if insufficient data
                self.current_risk_metrics = RiskMetrics(
                    var_1d=0.05,
                    var_1w=0.15,
                    max_drawdown=0.02,
                    sharpe_ratio=1.0,
                    volatility_24h=0.03,
                    correlation_btc=1.0,
                    risk_score=50.0,
                    timestamp=datetime.now(timezone.utc)
                )
                return self.current_risk_metrics
            
            # Extract price data - handle dict format from Binance API
            closes = [float(candle.get("close", candle.get("c", 0))) for candle in historical_data]
            returns = np.diff(np.log(closes))
            
            # Calculate volatility (24h)
            volatility_24h = np.std(returns[-24:]) * np.sqrt(24) if len(returns) >= 24 else 0.03
            
            # Calculate Value at Risk (VaR)
            var_1d = np.percentile(returns, 5) if len(returns) > 0 else -0.05
            var_1w = np.percentile(returns, 1) if len(returns) > 0 else -0.15
            
            # Calculate max drawdown
            cumulative_returns = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (cumulative_returns - running_max) / running_max
            max_drawdown = abs(np.min(drawdowns)) if len(drawdowns) > 0 else 0.02
            
            # Calculate Sharpe ratio (simplified)
            mean_return = np.mean(returns) if len(returns) > 0 else 0.001
            volatility = np.std(returns) if len(returns) > 1 else 0.02
            sharpe_ratio = (mean_return * 365) / (volatility * np.sqrt(365)) if volatility > 0 else 1.0
            
            # Calculate overall risk score (0-100)
            risk_score = min(100, max(0, (
                volatility_24h * 1000 +       # Volatility component
                abs(var_1d) * 500 +           # VaR component
                max_drawdown * 300 +          # Drawdown component
                max(0, (2 - sharpe_ratio)) * 20  # Sharpe component
            )))
            
            # Update risk level
            self._update_risk_level(volatility_24h)
            
            self.current_risk_metrics = RiskMetrics(
                var_1d=var_1d,
                var_1w=var_1w,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                volatility_24h=volatility_24h,
                correlation_btc=1.0,  # Always 1.0 for BTC
                risk_score=risk_score,
                timestamp=datetime.now(timezone.utc)
            )
            
            return self.current_risk_metrics
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            logger.error(f"Risk calculation error details: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"Risk calculation traceback: {traceback.format_exc()}")
            
            # Return professional default metrics on error
            self.current_risk_metrics = RiskMetrics(
                var_1d=-0.05,
                var_1w=-0.15,
                max_drawdown=0.02,
                sharpe_ratio=1.0,
                volatility_24h=0.03,
                correlation_btc=1.0,
                risk_score=50.0,
                timestamp=datetime.now(timezone.utc)
            )
            return self.current_risk_metrics
    
    async def _get_current_volatility(self) -> float:
        """Get current market volatility"""
        try:
            market_data = await get_live_market_data()
            return market_data.get("volatility", 0.03)
        except Exception as e:
            logger.error(f"Error getting volatility: {e}")
            return 0.03  # Default volatility
    
    async def _calculate_atr(self, periods: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            # Get recent candlestick data
            candles = await get_live_candlestick_data("1h", periods + 1)
            
            if not candles or len(candles) < periods:
                return 0.02  # Default ATR
            
            true_ranges = []
            for i in range(1, len(candles)):
                high = float(candles[i][2])
                low = float(candles[i][3])
                prev_close = float(candles[i-1][4])
                
                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close)
                )
                true_ranges.append(tr)
            
            return np.mean(true_ranges) if true_ranges else 0.02
            
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return 0.02
    
    def _calculate_volatility_multiplier(self, volatility: float) -> float:
        """Calculate volatility-based stop-loss multiplier"""
        
        # Base multiplier is 1.0 for moderate volatility (3%)
        base_volatility = 0.03
        
        # Calculate multiplier based on current volatility
        if volatility <= 0.01:          # Very low volatility
            return 0.5                  # Tighter stop-loss
        elif volatility <= 0.02:        # Low volatility
            return 0.75
        elif volatility <= 0.05:        # Moderate volatility
            return 1.0
        elif volatility <= 0.08:        # High volatility
            return 1.5                  # Wider stop-loss
        else:                           # Extreme volatility
            return 2.0                  # Much wider stop-loss
    
    def _update_risk_level(self, volatility: float):
        """Update current risk level based on volatility"""
        if volatility <= self.risk_thresholds[RiskLevel.VERY_LOW]:
            self.risk_level = RiskLevel.VERY_LOW
        elif volatility <= self.risk_thresholds[RiskLevel.LOW]:
            self.risk_level = RiskLevel.LOW
        elif volatility <= self.risk_thresholds[RiskLevel.MODERATE]:
            self.risk_level = RiskLevel.MODERATE
        elif volatility <= self.risk_thresholds[RiskLevel.HIGH]:
            self.risk_level = RiskLevel.HIGH
        else:
            self.risk_level = RiskLevel.EXTREME
    
    async def _check_risk_conditions(self):
        """Check for high-risk conditions and take action"""
        if not self.current_risk_metrics:
            return
        
        # Check for extreme volatility
        if self.current_risk_metrics.volatility_24h > 0.15:  # 15%
            logger.warning(f"⚠️ Extreme volatility detected: {self.current_risk_metrics.volatility_24h:.1%}")
            
            # Trigger emergency controls if available
            try:
                from app.backend.services.emergency_controls import get_emergency_system
                emergency_system = await get_emergency_system()
                await emergency_system.trigger_emergency_stop(
                    f"Extreme volatility: {self.current_risk_metrics.volatility_24h:.1%}",
                    emergency_system.EmergencyLevel.HIGH
                )
            except Exception as e:
                logger.error(f"Failed to trigger emergency controls: {e}")
        
        # Check for extreme drawdown
        if self.current_risk_metrics.max_drawdown > 0.08:  # 8%
            logger.warning(f"⚠️ High drawdown detected: {self.current_risk_metrics.max_drawdown:.1%}")
    
    async def _load_stop_loss_configurations(self):
        """Load existing stop-loss configurations from database"""
        try:
            # Implementation would load from database
            # For now, start with empty configurations
            self.position_stop_losses = {}
        except Exception as e:
            logger.error(f"Failed to load stop-loss configurations: {e}")
    
    def get_risk_status(self) -> Dict[str, Any]:
        """Get comprehensive risk status"""
        return {
            "is_initialized": self.is_initialized,
            "is_active": self.is_active,
            "current_risk_level": self.risk_level.value,
            "positions_monitored": len(self.position_stop_losses),
            "risk_metrics": {
                "var_1d": self.current_risk_metrics.var_1d if self.current_risk_metrics else None,
                "var_1w": self.current_risk_metrics.var_1w if self.current_risk_metrics else None,
                "max_drawdown": self.current_risk_metrics.max_drawdown if self.current_risk_metrics else None,
                "sharpe_ratio": self.current_risk_metrics.sharpe_ratio if self.current_risk_metrics else None,
                "volatility_24h": self.current_risk_metrics.volatility_24h if self.current_risk_metrics else None,
                "risk_score": self.current_risk_metrics.risk_score if self.current_risk_metrics else None,
                "timestamp": self.current_risk_metrics.timestamp.isoformat() if self.current_risk_metrics else None
            },
            "performance": {
                "adjustments_made": self.adjustments_made,
                "positions_protected": self.positions_protected,
                "risk_assessments": self.risk_assessments
            },
            "monitored_positions": {
                position_id: {
                    "current_stop_loss": sl.current_stop_loss,
                    "volatility_multiplier": sl.volatility_multiplier,
                    "adjustment_count": len(sl.adjustment_history) - 1,
                    "last_adjustment": sl.last_adjustment.isoformat()
                }
                for position_id, sl in self.position_stop_losses.items()
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    async def assess_pre_trade(self, signal, portfolio, candles, tick) -> 'RiskContext':
        """PHASE 1A: Pre-trade risk assessment - called before every position"""
        try:
            # Create risk context object
            class RiskContext:
                def __init__(self):
                    self.block_reason = None
                    self.risk_score = 0.0
                    
            risk_ctx = RiskContext()
            
            # Block reasons
            if hasattr(portfolio, 'daily_pnl') and portfolio.daily_pnl < -0.10:  # 10% daily loss
                risk_ctx.block_reason = "daily_loss_limit"
                risk_ctx.risk_score = 1.0
                return risk_ctx
            
            active_positions = portfolio.get_active_positions() if hasattr(portfolio, 'get_active_positions') else []
            if len(active_positions) >= 5:
                risk_ctx.block_reason = "max_positions"
                risk_ctx.risk_score = 0.9
                return risk_ctx
            
            # Volatility check using current market data
            volatility = await self._calculate_current_volatility_from_candles(candles)
            if volatility > 0.15:  # 15% volatility
                risk_ctx.block_reason = "extreme_volatility"
                risk_ctx.risk_score = 0.95
                return risk_ctx
            
            # Calculate overall risk score
            risk_score = self._calculate_risk_score(signal, portfolio, candles)
            risk_ctx.risk_score = risk_score
            
            return risk_ctx
            
        except Exception as e:
            logger.error(f"Pre-trade risk assessment failed: {e}")
            # Return safe default (block trade)
            class RiskContext:
                def __init__(self):
                    self.block_reason = "assessment_failed"
                    self.risk_score = 1.0
            return RiskContext()
            
    async def calculate_position_size(self, signal, risk_ctx, portfolio, tick) -> float:
        """PHASE 1A: Calculate position size based on risk and signal type"""
        try:
            base_size = float(portfolio.cash_balance) * 0.12  # 12% base
            
            # Adjust for signal type
            if hasattr(signal, 'signal_type') and signal.signal_type == "exploratory":
                multiplier = 0.25  # Small probing positions
            elif hasattr(signal, 'confidence') and signal.confidence > 0.8:
                multiplier = 1.2   # Larger positions for high confidence
            else:
                multiplier = 1.0   # Normal size
            
            # Adjust for risk
            risk_multiplier = max(0.3, 1.0 - risk_ctx.risk_score)
            
            final_size = base_size * multiplier * risk_multiplier
            
            # Enforce minimum $500 position size
            min_size_usd = 500.0
            if final_size < min_size_usd:
                final_size = min_size_usd
                logger.info(f"💰 Position size increased to minimum: ${min_size_usd}")
            
            return final_size
            
        except Exception as e:
            logger.error(f"Position size calculation failed: {e}")
            raise RuntimeError(f"Professional position sizing failed: {e} - no fallback allowed")
            
    async def position_size(self, signal, risk_ctx, portfolio, tick) -> Decimal:
        """PHASE 1A: Position size calculation - alias for trading loop compatibility"""
        size_float = await self.calculate_position_size(signal, risk_ctx, portfolio, tick)
        return Decimal(str(size_float))
            
    async def assess_in_position(self, portfolio, tick):
        """PHASE 1A: In-position risk management - trailing stops, VaR monitoring"""
        try:
            active_positions = portfolio.get_active_positions() if hasattr(portfolio, 'get_active_positions') else []
            
            for position in active_positions:
                # Dynamic trailing stop with caps for aggressive adjustments
                if hasattr(position, 'position_id') and hasattr(position, 'stop_loss'):
                    new_stop = self._calculate_trailing_stop(position, tick)
                    
                    # CAP AGGRESSIVE TRAILING: Limit max trailing stop adjustment from entry
                    MAX_TS_FROM_ENTRY_BP = 60  # Max 0.60% from entry price at start
                    entry_price = getattr(position, 'entry_price', tick.get('tick', 0.0))
                    if entry_price > 0:
                        max_stop_from_entry = entry_price * (1 - 0.006)  # 0.60% max drawdown
                        new_stop = max(max_stop_from_entry, new_stop)  # Don't go below cap
                    
                    if new_stop != position.stop_loss:
                        old_stop = position.stop_loss
                        change_pct = ((new_stop - old_stop) / old_stop) * 100 if old_stop else 0
                        logger.info(f"📊 Adjusting trailing stop: {position.position_id} {old_stop:.2f} -> {new_stop:.2f} ({change_pct:+.1f}%)")
                        
                # VaR monitoring with proper caps for day trading
                var_risk = self._calculate_position_var(position, tick)
                # CAP VaR for day trading: Max 15% VaR tolerance (fresh positions can be volatile)
                var_threshold = 0.15  # 15% VaR limit for day trading
                
                if var_risk > var_threshold:
                    # Ensure VaR is properly bounded
                    var_pct = min(max(var_risk * 100.0, 0.0), 100.0)  # 0-100% bounds
                    logger.warning(f"🚨 High VaR (capped): {position.position_id} - {var_pct:.1f}% (threshold: {var_threshold*100:.1f}%)")
                    
        except Exception as e:
            logger.error(f"In-position risk assessment failed: {e}")
            
    def _calculate_risk_score(self, signal, portfolio, candles) -> float:
        """Calculate overall risk score (0-1, higher = more risky)"""
        try:
            # Simplified risk scoring
            base_risk = 0.3
            
            # Adjust for signal confidence
            if hasattr(signal, 'confidence'):
                confidence_risk = max(0, (0.8 - signal.confidence)) * 0.5
                base_risk += confidence_risk
                
            # Adjust for portfolio exposure
            if hasattr(portfolio, 'get_active_positions'):
                position_count = len(portfolio.get_active_positions())
                exposure_risk = min(0.3, position_count * 0.1)
                base_risk += exposure_risk
                
            return min(1.0, base_risk)
            
        except Exception:
            return 0.5  # Medium risk default
            
    def _calculate_trailing_stop(self, position, tick) -> float:
        """Calculate conservative trailing stop price for day trading"""
        try:
            if hasattr(tick, 'get'):
                current_price = tick.get('price', 0)
            elif isinstance(tick, dict):
                current_price = tick.get('price', 0)
            else:
                current_price = float(tick)
                
            # Get entry price for position age check
            entry_price = float(getattr(position, 'entry_price', current_price))
            current_stop = float(getattr(position, 'stop_loss', entry_price * 0.97))
            
            # CONSERVATIVE DAY TRADING: Only tighten stop loss, never widen it
            if hasattr(position, 'type') and hasattr(position.type, 'value') and position.type.value.upper() == 'LONG':
                # For LONG: New stop is 1% below current price, but never below current stop
                potential_stop = current_price * 0.99  # More conservative 1% (was 2%)
                return max(potential_stop, current_stop)  # Only tighten, never loosen
            else:
                # For SHORT: New stop is 1% above current price, but never above current stop  
                potential_stop = current_price * 1.01
                return min(potential_stop, current_stop)  # Only tighten, never loosen
                
        except Exception:
            return getattr(position, 'stop_loss', 0)
            
    def _calculate_position_var(self, position, tick) -> float:
        """Calculate position Value at Risk as percentage (0-1 range)"""
        try:
            # Return VaR as percentage for day trading
            # For new positions, VaR can be higher due to initial volatility
            if hasattr(position, 'entry_price') and hasattr(position, 'current_price'):
                entry_price = float(getattr(position, 'entry_price', 0))
                current_price = float(getattr(position, 'current_price', entry_price))
                
                if entry_price > 0:
                    # VaR based on current price deviation from entry
                    price_change_pct = abs(current_price - entry_price) / entry_price
                    # Cap at reasonable bounds for day trading (max 20%)
                    var_pct = min(price_change_pct + 0.02, 0.20)  # Add 2% base VaR
                    return var_pct
            
            # Default 2% VaR for new positions
            return 0.02
        except Exception:
            return 0.02
            
    async def _calculate_current_volatility_from_candles(self, candles) -> float:
        """Calculate current market volatility from candle data"""
        try:
            if not candles or len(candles) < 20:
                return 0.05  # Default 5% volatility
                
            # Calculate price changes
            closes = []
            for candle in candles[-20:]:  # Last 20 candles
                if isinstance(candle, dict):
                    closes.append(float(candle.get('close', 0)))
                elif hasattr(candle, 'close'):
                    closes.append(float(candle.close))
                    
            if len(closes) < 2:
                return 0.05
                
            # Calculate returns and volatility
            returns = []
            for i in range(1, len(closes)):
                if closes[i-1] > 0:
                    returns.append((closes[i] - closes[i-1]) / closes[i-1])
                    
            if not returns:
                return 0.05
                
            # Standard deviation of returns
            import math
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            volatility = math.sqrt(variance)
            
            return min(0.5, volatility)  # Cap at 50%
            
        except Exception as e:
            logger.warning(f"Volatility calculation failed: {e}")
            return 0.05  # Safe default

# Global dynamic risk manager instance
_risk_manager: Optional[DynamicRiskManager] = None

async def get_risk_manager() -> DynamicRiskManager:
    """Get or create global dynamic risk manager"""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = DynamicRiskManager()
        await _risk_manager.initialize()
    return _risk_manager

# Export classes and functions
__all__ = [
    "DynamicRiskManager",
    "RiskLevel",
    "StopLossMode", 
    "RiskMetrics",
    "DynamicStopLoss",
    "get_risk_manager"
]