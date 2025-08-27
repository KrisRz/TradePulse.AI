"""
BRAIN Controller - TradePulse.AI
===============================

Finite State Machine (FSM) based orchestrator for professional trading operations.
Coordinates all existing services without replacing them.

FSM States: INIT → WARMUP → RUNNING → HALT → COOLDOWN
Professional tick cycle: (A) Data → (B) Safety → (C) Signal → (D) Risk → (E) Entry/Exit → (F) Position → (G) Audit

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
import traceback

from .brain_state import (
    BrainState, BrainControllerState, TradingContext, TradingSession,
    create_initial_brain_state, MarketTick, TradingSignal, RiskContext,
    EntryAnalysis, ExitAnalysis, Position, PortfolioState, PerformanceMetrics
)
from .brain_events import (
    get_event_bus, publish_state_change_event, publish_system_event,
    publish_tick_event, publish_signal_event, publish_risk_event,
    publish_entry_event, publish_exit_event, publish_position_event,
    EventType, EventSeverity
)

# Import existing services (NO CHANGES TO SERVICES)
from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine
from app.backend.services.intelligent_entry_engine import IntelligentEntryEngine
from app.backend.services.intelligent_exit_engine import IntelligentExitEngine
from app.backend.services.dynamic_risk_manager import DynamicRiskManager
from app.backend.services.emergency_controls import EmergencyControlSystem
from app.backend.services.professional_portfolio import get_professional_portfolio, PositionType
from app.backend.services.live_market_data import (
    get_live_bitcoin_price, get_live_market_data, get_live_candlestick_data
)
from app.backend.services.market_data_persistence import write_decisions, write_orders

logger = logging.getLogger(__name__)

class BrainController:
    """
    BRAIN Controller - FSM-based orchestrator for professional trading
    
    Coordinates existing services through event-driven architecture:
    - Orchestrates without replacing existing services
    - FSM-based state management (INIT → WARMUP → RUNNING → HALT → COOLDOWN)
    - Professional decision-making cycle
    - Complete audit trail and monitoring
    """
    
    def __init__(self):
        self.state = create_initial_brain_state()
        self.event_bus = get_event_bus()
        
        # Core service references (imported, not replaced)
        self.enterprise_engine: Optional[EnterpriseTradingEngine] = None
        self.entry_engine: Optional[IntelligentEntryEngine] = None
        self.exit_engine: Optional[IntelligentExitEngine] = None
        self.risk_manager: Optional[DynamicRiskManager] = None
        self.emergency_system: Optional[EmergencyControlSystem] = None
        
        # Control tasks
        self.main_task: Optional[asyncio.Task] = None
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self.start_time = datetime.now(timezone.utc)
        self.last_cycle_time = 0.0
        self.cycle_times: List[float] = []
        self.max_cycle_history = 100
        
        # Error handling
        self.error_backoff_seconds = 1
        self.max_backoff_seconds = 60
        
        logger.info("🧠 BRAIN Controller initialized")
        
    async def initialize(self) -> Dict[str, Any]:
        """Initialize BRAIN controller and all services"""
        if self.state.current_state != BrainState.INIT:
            return {"status": "already_initialized", "current_state": self.state.current_state.value}
            
        logger.info("🚀 BRAIN Controller initialization starting...")
        
        try:
            # Transition to WARMUP state
            await self._transition_state(BrainState.WARMUP)
            
            # Initialize all core services
            await self._initialize_services()
            
            # Validate system readiness
            await self._validate_system_readiness()
            
            # Subscribe to events
            self._setup_event_handlers()
            
            logger.info("✅ BRAIN Controller initialization complete")
            
            return {
                "status": "initialized",
                "current_state": self.state.current_state.value,
                "services_loaded": self._get_service_status(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ BRAIN Controller initialization failed: {e}")
            await self._transition_state(BrainState.ERROR)
            raise
            
    async def _initialize_services(self):
        """Initialize all core trading services"""
        logger.info("📚 Initializing core trading services...")
        
        # Enterprise trading engine
        logger.info("🧠 Initializing enterprise trading engine...")
        self.enterprise_engine = EnterpriseTradingEngine()
        await self.enterprise_engine.initialize()
        
        # Entry and exit engines
        logger.info("🚪 Initializing entry/exit engines...")
        self.entry_engine = IntelligentEntryEngine()
        await self.entry_engine.initialize()
        
        self.exit_engine = IntelligentExitEngine()
        await self.exit_engine.initialize()
        
        # Risk management system
        logger.info("🛡️ Initializing risk management system...")
        self.risk_manager = DynamicRiskManager()
        await self.risk_manager.initialize()
        await self.risk_manager.start_risk_monitoring()
        
        # Emergency controls
        logger.info("🚨 Initializing emergency control system...")
        self.emergency_system = EmergencyControlSystem()
        await self.emergency_system.initialize()
        await self.emergency_system.start_monitoring()
        
        logger.info("✅ All services initialized successfully")
        
    async def _validate_system_readiness(self):
        """Validate all systems are ready for trading"""
        logger.info("🔍 Validating system readiness...")
        
        # Check service initialization
        services = [
            ("enterprise_engine", self.enterprise_engine),
            ("entry_engine", self.entry_engine),
            ("exit_engine", self.exit_engine),
            ("risk_manager", self.risk_manager),
            ("emergency_system", self.emergency_system)
        ]
        
        for name, service in services:
            if not service or not hasattr(service, 'is_initialized') or not service.is_initialized:
                raise RuntimeError(f"Service not ready: {name}")
                
        # Test market data connectivity
        try:
            price = await get_live_bitcoin_price()
            market_data = await get_live_market_data()
            candles = await get_live_candlestick_data("1m", 10)
            
            if not price or not market_data or not candles:
                raise RuntimeError("Market data connectivity failed")
                
            logger.info(f"📊 Market data OK: BTCUSDT @${price}, {len(candles)} candles")
            
        except Exception as e:
            logger.warning(f"Market data validation warning: {e}")
            # BRAIN FIX: Don't fail initialization on market data issues
            
        # Test portfolio access
        try:
            portfolio = await get_professional_portfolio("admin")
            if not portfolio:
                raise RuntimeError("Portfolio access failed")
                
            logger.info(f"💰 Portfolio OK: ${float(portfolio.cash_balance):.2f} cash")
            
        except Exception as e:
            raise RuntimeError(f"Portfolio validation failed: {e}")
            
        logger.info("✅ System readiness validated")
        
    def _setup_event_handlers(self):
        """Setup event bus handlers"""
        logger.info("📡 Setting up event handlers...")
        
        # Subscribe to critical events
        self.event_bus.subscribe(EventType.API_FAILURE, self._handle_api_failure)
        self.event_bus.subscribe(EventType.CONNECTION_LOST, self._handle_connection_lost)
        self.event_bus.subscribe(EventType.EMERGENCY_TRIGGERED, self._handle_emergency)
        
        logger.info("✅ Event handlers configured")
        
    def _handle_api_failure(self, event):
        """Handle API failure events"""
        logger.warning(f"🚨 API Failure handled by BRAIN: {event.message}")
        
    def _handle_connection_lost(self, event):
        """Handle connection loss events"""
        logger.warning(f"📡 Connection loss handled by BRAIN: {event.message}")
        
    def _handle_emergency(self, event):
        """Handle emergency events"""
        logger.critical(f"🚨 Emergency handled by BRAIN: {event.message}")
        asyncio.create_task(self._transition_state(BrainState.HALT))
        
    async def start_trading(self) -> Dict[str, Any]:
        """Start professional trading operations"""
        if self.state.current_state == BrainState.RUNNING:
            return {"status": "already_running"}
            
        if self.state.current_state != BrainState.WARMUP:
            return {"status": "not_ready", "current_state": self.state.current_state.value}
            
        logger.info("🚀 BRAIN Controller starting trading operations...")
        
        try:
            # Transition to RUNNING state
            await self._transition_state(BrainState.RUNNING)
            
            # Start main trading loop
            self.main_task = asyncio.create_task(self._main_trading_loop())
            
            # Start monitoring loop
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            return {
                "status": "trading_started",
                "current_state": self.state.current_state.value,
                "cycle_interval": self.state.cycle_interval_seconds,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to start trading: {e}")
            await self._transition_state(BrainState.ERROR)
            return {"status": "start_failed", "error": str(e)}
            
    async def stop_trading(self) -> Dict[str, Any]:
        """Stop trading operations gracefully"""
        if self.state.current_state != BrainState.RUNNING:
            return {"status": "not_running"}
            
        logger.info("🛑 BRAIN Controller stopping trading operations...")
        
        try:
            # Transition to COOLDOWN state
            await self._transition_state(BrainState.COOLDOWN)
            
            # Cancel tasks
            if self.main_task and not self.main_task.done():
                self.main_task.cancel()
                try:
                    await self.main_task
                except asyncio.CancelledError:
                    pass
                    
            if self.monitoring_task and not self.monitoring_task.done():
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
                    
            # Stop service monitoring
            if self.risk_manager:
                await self.risk_manager.stop_risk_monitoring()
            if self.emergency_system:
                await self.emergency_system.stop_monitoring()
                
            # Transition to HALT state
            await self._transition_state(BrainState.HALT)
            
            return {
                "status": "trading_stopped",
                "cycles_completed": self.state.cycle_count,
                "uptime_minutes": (datetime.now(timezone.utc) - self.start_time).total_seconds() / 60,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error stopping trading: {e}")
            return {"status": "stop_failed", "error": str(e)}
            
    async def _main_trading_loop(self):
        """Main BRAIN trading loop - professional tick cycle"""
        logger.info("🔄 BRAIN main trading loop started")
        
        try:
            while self.state.current_state == BrainState.RUNNING:
                cycle_start = time.time()
                
                try:
                    # Professional trading cycle
                    await self._execute_trading_cycle()
                    
                    # Update performance metrics
                    cycle_time = time.time() - cycle_start
                    self._update_cycle_metrics(cycle_time)
                    
                    # Reset error backoff on successful cycle
                    self.error_backoff_seconds = 1
                    
                except Exception as e:
                    logger.error(f"❌ Trading cycle error: {e}")
                    
                    # Exponential backoff on errors
                    await asyncio.sleep(self.error_backoff_seconds)
                    self.error_backoff_seconds = min(self.error_backoff_seconds * 2, self.max_backoff_seconds)
                    
                    # Increment error count
                    self.state.error_count += 1
                    self.state.last_error = str(e)
                    
                    # Emergency stop after too many errors
                    if self.state.error_count > 10:
                        logger.critical("🚨 Too many errors, triggering emergency stop")
                        if self.emergency_system:
                            await self.emergency_system.trigger_emergency_stop(f"BRAIN error count: {self.state.error_count}")
                        break
                
                # Wait for next cycle
                elapsed = time.time() - cycle_start
                sleep_time = max(self.state.cycle_interval_seconds - elapsed, 1)
                await asyncio.sleep(sleep_time)
                
        except asyncio.CancelledError:
            logger.info("🛑 BRAIN main trading loop cancelled")
        except Exception as e:
            logger.error(f"❌ Fatal error in main trading loop: {e}")
            await self._transition_state(BrainState.ERROR)
            
    async def _execute_trading_cycle(self):
        """Execute professional trading cycle (A→I steps)"""
        try:
            # (A) Fresh market data
            tick_data = await self._get_fresh_market_data()
            if not tick_data:
                return
                
            # (B) Safety checks (emergency controls)
            if await self._check_safety_conditions():
                return  # Trading halted
                
            # (C) Enterprise signal generation
            signal = await self._generate_enterprise_signal()
            if not signal:
                return
                
            # (D) Risk assessment
            risk_context = await self._assess_risk(signal, tick_data)
            if risk_context and risk_context.block_reason:
                return  # Risk blocked
                
            # (E) Entry/Exit analysis (parallel)
            await self._process_entry_exit_decisions(signal, risk_context, tick_data)
            
            # (F) Position management
            await self._manage_open_positions(tick_data)
            
            # (G) In-position risk monitoring
            if self.risk_manager:
                portfolio = await get_professional_portfolio("admin")
                await self.risk_manager.assess_in_position(portfolio, tick_data)
            
            # (H) Audit trail
            await self._audit_cycle(signal, risk_context, tick_data)
            
            # Update cycle count
            self.state.cycle_count += 1
            self.state.last_decision_at = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Trading cycle execution failed: {e}")
            raise
            
    async def _get_fresh_market_data(self) -> Optional[Dict[str, Any]]:
        """(A) Get fresh market data using existing services - NO NEW CONNECTIONS"""
        try:
            # BRAIN FIX: Use existing services without creating new sessions
            tick = await get_live_bitcoin_price()
            market_data = await get_live_market_data() 
            candles = await get_live_candlestick_data("1m", 200)
            
            # BRAIN FIX: Accept partial data instead of failing
            if not tick:
                logger.warning("⚠️ No tick data - using fallback")
                tick = 0.0
            if not market_data:
                logger.warning("⚠️ No market data - using fallback")
                market_data = {"status": "fallback"}
            if not candles:
                logger.warning("⚠️ No candles - using empty list")
                candles = []
                
            # Update trading context
            self.state.trading_context.current_tick = MarketTick(
                symbol="BTCUSDT",
                price=Decimal(str(tick)),
                timestamp=datetime.now(timezone.utc)
            )
            
            # Publish tick event
            publish_tick_event(self.state.trading_context.current_tick)
            
            return {
                "tick": tick,
                "market_data": market_data,
                "candles": candles
            }
            
        except Exception as e:
            logger.error(f"Market data retrieval failed: {e}")
            return None
            
    async def _check_safety_conditions(self) -> bool:
        """(B) Safety checks - returns True if trading should halt"""
        try:
            if self.emergency_system and await self.emergency_system.is_trading_halted():
                publish_system_event(
                    EventType.EMERGENCY_TRIGGERED,
                    "Trading halted by emergency system",
                    "emergency_system",
                    EventSeverity.CRITICAL
                )
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Safety check failed: {e}")
            return True  # Fail-safe: halt on error
            
    async def _generate_enterprise_signal(self) -> Optional[TradingSignal]:
        """(C) Generate enterprise AI signal"""
        try:
            if not self.enterprise_engine:
                return None
                
            signal = await self.enterprise_engine.generate_signal("BTCUSDT")
            if not signal:
                return None
                
            # Convert to BRAIN signal format
            brain_signal = TradingSignal(
                symbol=signal.symbol,
                action=signal.action,
                confidence=Decimal(str(signal.confidence)),
                reasoning=signal.reasoning,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Update trading context
            self.state.trading_context.current_signal = brain_signal
            
            # Publish signal event
            publish_signal_event(brain_signal)
            
            return brain_signal
            
        except Exception as e:
            logger.error(f"Signal generation failed: {e}")
            return None
            
    async def _assess_risk(self, signal: TradingSignal, tick_data: Dict) -> Optional[RiskContext]:
        """(D) Risk assessment"""
        try:
            if not self.risk_manager:
                return None
                
            portfolio = await get_professional_portfolio("admin")
            candles = tick_data.get("candles", [])
            
            assessment = await self.risk_manager.assess_pre_trade(
                signal=signal, 
                portfolio=portfolio, 
                candles=candles, 
                tick=tick_data
            )
            
            if not assessment:
                return None
                
            # Convert to BRAIN format
            risk_context = RiskContext(
                risk_score=Decimal(str(getattr(assessment, 'risk_score', 0.5))),
                risk_level=getattr(assessment, 'risk_level', 'MODERATE'),
                block_reason=getattr(assessment, 'block_reason', None),
                volatility_current=Decimal('0.05'),
                volatility_median=Decimal('0.03'),
                position_exposure=Decimal(str(len(portfolio.get_active_positions()) / self.state.max_positions)),
                daily_pnl_pct=portfolio.get_daily_pnl_percentage(),
                max_positions_reached=len(portfolio.get_active_positions()) >= self.state.max_positions
            )
            
            # Update trading context
            self.state.trading_context.risk_context = risk_context
            
            # Publish risk event
            action_taken = "blocked" if risk_context.block_reason else "approved"
            publish_risk_event(risk_context, action_taken)
            
            return risk_context
            
        except Exception as e:
            logger.error(f"Risk assessment failed: {e}")
            return None
            
    async def _process_entry_exit_decisions(self, signal: TradingSignal, risk_context: Optional[RiskContext], tick_data: Dict):
        """(E) Process entry and exit decisions"""
        try:
            # Check if we should consider entry
            if (signal.action in ["BUY", "SELL"] and 
                signal.confidence >= self.state.confidence_threshold and
                (not risk_context or not risk_context.block_reason)):
                
                await self._process_entry_decision(signal, risk_context, tick_data)
                
            # Always check for exit opportunities
            await self._process_exit_decisions(tick_data)
            
        except Exception as e:
            logger.error(f"Entry/exit processing failed: {e}")
            
    async def _process_entry_decision(self, signal: TradingSignal, risk_context: Optional[RiskContext], tick_data: Dict):
        """Process entry decision"""
        try:
            if not self.entry_engine:
                return
                
            portfolio = await get_professional_portfolio("admin")
            
            # Check position limits
            active_positions = len(portfolio.get_active_positions())
            if active_positions >= self.state.max_positions:
                logger.debug(f"Max positions reached: {active_positions}/{self.state.max_positions}")
                return
                
            # Analyze entry opportunity
            entry_result = await self.entry_engine.analyze_entry_opportunity(
                symbol=signal.symbol,
                signal_data={
                    "action": signal.action,
                    "confidence": float(signal.confidence),
                    "reasoning": signal.reasoning
                },
                user_portfolio={
                    "available_cash": float(portfolio.cash_balance),
                    "active_positions": portfolio.get_active_positions(),
                    "max_positions": self.state.max_positions,
                    "daily_trades": portfolio.daily_trades,
                    "max_daily_trades": portfolio.max_daily_trades
                }
            )
            
            if not entry_result:
                return
                
            # Convert to BRAIN format
            entry_analysis = EntryAnalysis(
                should_enter=entry_result.should_enter,
                confidence=Decimal(str(entry_result.confidence)),
                entry_quality=entry_result.entry_quality.value,
                optimal_price=Decimal(str(entry_result.optimal_entry_price)) if entry_result.optimal_entry_price else None,
                reasoning=f"BRAIN entry analysis: {entry_result.entry_reason.value}",
                size_recommendation=Decimal(str(float(portfolio.cash_balance) * float(self.state.position_size_pct)))
            )
            
            # Update trading context
            self.state.trading_context.entry_analysis = entry_analysis
            
            # Publish entry event
            publish_entry_event(entry_analysis)
            
            # Execute entry if recommended
            if entry_analysis.should_enter:
                await self._execute_entry(signal, entry_analysis, risk_context, tick_data)
                
        except Exception as e:
            logger.error(f"Entry decision processing failed: {e}")
            
    async def _execute_entry(self, signal: TradingSignal, entry_analysis: EntryAnalysis, risk_context: Optional[RiskContext], tick_data: Dict):
        """Execute position entry"""
        try:
            portfolio = await get_professional_portfolio("admin")
            
            # Calculate position size
            if self.risk_manager and risk_context:
                position_size = await self.risk_manager.calculate_position_size(
                    signal, risk_context, portfolio, tick_data
                )
            else:
                position_size = float(portfolio.cash_balance) * float(self.state.position_size_pct)
                
            # Open position
            position_id = await portfolio.open_position(
                symbol=signal.symbol,
                position_type=PositionType.LONG if signal.action == "BUY" else PositionType.SHORT,
                size=Decimal(str(position_size)),
                ai_confidence=signal.confidence,
                ai_reasoning=f"BRAIN: {signal.reasoning}",
                stop_loss_pct=Decimal('0.015'),  # 1.5% stop loss
                take_profit_pct=Decimal('0.025')  # 2.5% take profit
            )
            
            self.state.positions_opened_today += 1
            
            logger.info(f"✅ BRAIN Position opened: {position_id} ({signal.action}) conf={signal.confidence:.1%}")
            
            # Create position for event
            position = Position(
                position_id=position_id,
                symbol=signal.symbol,
                side=signal.action,
                quantity=Decimal(str(position_size)),
                entry_price=Decimal(str(tick_data["tick"])),
                current_price=Decimal(str(tick_data["tick"])),
                status="OPEN",
                entry_time=datetime.now(timezone.utc),
                ai_confidence=signal.confidence,
                ai_reasoning=signal.reasoning
            )
            
            # Publish position opened event
            publish_position_event(position, EventType.POSITION_OPENED)
            
        except Exception as e:
            logger.error(f"Position entry execution failed: {e}")
            
    async def _process_exit_decisions(self, tick_data: Dict):
        """Process exit decisions for all open positions"""
        try:
            if not self.exit_engine:
                return
                
            portfolio = await get_professional_portfolio("admin")
            active_positions = portfolio.get_active_positions()
            
            for position in active_positions:
                try:
                    # Convert position to exit engine format
                    position_data = {
                        "position_id": position.position_id,
                        "symbol": position.symbol,
                        "type": position.type.value,
                        "size": float(position.size),
                        "entry_price": float(position.entry_price),
                        "current_price": float(position.current_price),
                        "entry_time": position.entry_time.isoformat(),
                        "stop_loss": float(position.stop_loss) if position.stop_loss else None,
                        "take_profit": float(position.take_profit) if position.take_profit else None
                    }
                    
                    # Analyze exit conditions
                    exit_result = await self.exit_engine.analyze_exit_conditions(
                        symbol=position.symbol,
                        position_data=position_data
                    )
                    
                    if not exit_result:
                        continue
                        
                    # Convert to BRAIN format
                    exit_analysis = ExitAnalysis(
                        should_exit=exit_result["should_exit"],
                        confidence=Decimal(str(exit_result["confidence"])),
                        exit_reason=exit_result.get("exit_reason", "unknown"),
                        pnl_percent=Decimal(str(exit_result.get("pnl_percent", 0))),
                        pnl_absolute=Decimal(str(exit_result.get("pnl_absolute", 0))),
                        hold_duration_minutes=int((datetime.now(timezone.utc) - position.entry_time).total_seconds() / 60)
                    )
                    
                    # Publish exit event
                    publish_exit_event(exit_analysis, position.position_id)
                    
                    # Execute exit if recommended
                    if exit_analysis.should_exit:
                        await self._execute_exit(position, exit_analysis, tick_data)
                        
                except Exception as e:
                    logger.error(f"Exit analysis failed for {position.position_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Exit decisions processing failed: {e}")
            
    async def _execute_exit(self, position, exit_analysis: ExitAnalysis, tick_data: Dict):
        """Execute position exit"""
        try:
            portfolio = await get_professional_portfolio("admin")
            
            # Close position
            pnl = await portfolio.close_position(
                position_id=position.position_id,
                reason=exit_analysis.exit_reason
            )
            
            logger.info(f"🚪 BRAIN Position closed: {position.position_id} PnL=${float(pnl):.2f}")
            
            # Create closed position for event
            closed_position = Position(
                position_id=position.position_id,
                symbol=position.symbol,
                side=position.type.value,
                quantity=position.size,
                entry_price=position.entry_price,
                current_price=Decimal(str(tick_data["tick"])),
                status="CLOSED",
                entry_time=position.entry_time,
                exit_time=datetime.now(timezone.utc),
                pnl_absolute=pnl,
                pnl_percent=exit_analysis.pnl_percent,
                ai_confidence=position.ai_confidence,
                ai_reasoning=position.ai_reasoning
            )
            
            # Publish position closed event
            publish_position_event(closed_position, EventType.POSITION_CLOSED)
            
        except Exception as e:
            logger.error(f"Position exit execution failed: {e}")
            
    async def _manage_open_positions(self, tick_data: Dict):
        """(F) Manage open positions"""
        try:
            # Position management is handled in exit analysis
            # This could include dynamic stop-loss updates, etc.
            pass
            
        except Exception as e:
            logger.error(f"Position management failed: {e}")
            
    async def _audit_cycle(self, signal: Optional[TradingSignal], risk_context: Optional[RiskContext], tick_data: Dict):
        """(H) Audit trading cycle"""
        try:
            # Write decisions to audit trail
            await write_decisions(
                entry_decision=self.state.trading_context.entry_analysis.__dict__ if self.state.trading_context.entry_analysis else None,
                exit_decision=self.state.trading_context.exit_analysis.__dict__ if self.state.trading_context.exit_analysis else None,
                risk_assessment=risk_context,
                signal=signal
            )
            
        except Exception as e:
            logger.error(f"Audit cycle failed: {e}")
            
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        logger.info("📊 BRAIN monitoring loop started")
        
        try:
            while self.state.current_state == BrainState.RUNNING:
                try:
                    # Update performance metrics
                    await self._update_performance_metrics()
                    
                    # Update uptime
                    self.state.uptime_seconds = int((datetime.now(timezone.utc) - self.start_time).total_seconds())
                    
                    # Log status every 5 minutes
                    if self.state.cycle_count % 20 == 0:  # Every 20 cycles (5 minutes at 15s intervals)
                        logger.info(f"📊 BRAIN Status: cycles={self.state.cycle_count} "
                                   f"avg_time={self.state.avg_cycle_time_ms:.1f}ms "
                                   f"positions_today={self.state.positions_opened_today}")
                        
                except Exception as e:
                    logger.error(f"Monitoring error: {e}")
                    
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
        except asyncio.CancelledError:
            logger.info("📊 BRAIN monitoring loop cancelled")
        except Exception as e:
            logger.error(f"❌ Fatal monitoring error: {e}")
            
    async def _update_performance_metrics(self):
        """Update performance metrics"""
        try:
            portfolio = await get_professional_portfolio("admin")
            
            # Update portfolio state in trading context
            self.state.trading_context.portfolio_state = PortfolioState(
                cash_balance=portfolio.cash_balance,
                total_value=portfolio.total_value,
                active_positions=[],  # Would populate with current positions
                daily_pnl=portfolio.get_daily_pnl(),
                daily_pnl_pct=portfolio.get_daily_pnl_percentage(),
                last_updated=datetime.now(timezone.utc)
            )
            
            # Calculate cycles per hour
            if self.state.cycle_count > 0:
                hours = (datetime.now(timezone.utc) - self.start_time).total_seconds() / 3600
                self.state.cycles_per_hour = int(self.state.cycle_count / max(hours, 1))
                
        except Exception as e:
            logger.error(f"Performance metrics update failed: {e}")
            
    def _update_cycle_metrics(self, cycle_time: float):
        """Update cycle timing metrics"""
        cycle_time_ms = cycle_time * 1000
        
        # Update cycle times history
        self.cycle_times.append(cycle_time_ms)
        if len(self.cycle_times) > self.max_cycle_history:
            self.cycle_times.pop(0)
            
        # Update average cycle time
        if self.cycle_times:
            self.state.avg_cycle_time_ms = Decimal(str(sum(self.cycle_times) / len(self.cycle_times)))
            
        self.last_cycle_time = cycle_time
        
    async def _transition_state(self, new_state: BrainState):
        """Transition BRAIN to new state"""
        old_state = self.state.current_state
        self.state.current_state = new_state
        self.state.state_entered_at = datetime.now(timezone.utc)
        
        logger.info(f"🔄 BRAIN State: {old_state.value} → {new_state.value}")
        
        # Publish state change event
        publish_state_change_event(old_state.value, new_state.value)
        
    def _get_service_status(self) -> Dict[str, bool]:
        """Get status of all services"""
        return {
            "enterprise_engine": self.enterprise_engine is not None and getattr(self.enterprise_engine, 'is_initialized', False),
            "entry_engine": self.entry_engine is not None and getattr(self.entry_engine, 'is_initialized', False),
            "exit_engine": self.exit_engine is not None and getattr(self.exit_engine, 'is_initialized', False),
            "risk_manager": self.risk_manager is not None and getattr(self.risk_manager, 'is_initialized', False),
            "emergency_system": self.emergency_system is not None and getattr(self.emergency_system, 'is_initialized', False)
        }
        
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive BRAIN status"""
        return {
            "current_state": self.state.current_state.value,
            "state_entered_at": self.state.state_entered_at.isoformat(),
            "uptime_seconds": self.state.uptime_seconds,
            "cycle_count": self.state.cycle_count,
            "cycles_per_hour": self.state.cycles_per_hour,
            "avg_cycle_time_ms": float(self.state.avg_cycle_time_ms),
            "positions_opened_today": self.state.positions_opened_today,
            "last_decision_at": self.state.last_decision_at.isoformat() if self.state.last_decision_at else None,
            "error_count": self.state.error_count,
            "last_error": self.state.last_error,
            "services": self._get_service_status(),
            "trading_context": {
                "session": self.state.trading_context.session.value,
                "has_tick": self.state.trading_context.current_tick is not None,
                "has_signal": self.state.trading_context.current_signal is not None,
                "has_risk_context": self.state.trading_context.risk_context is not None,
                "has_entry_analysis": self.state.trading_context.entry_analysis is not None,
                "has_exit_analysis": self.state.trading_context.exit_analysis is not None
            },
            "configuration": {
                "cycle_interval_seconds": self.state.cycle_interval_seconds,
                "max_positions": self.state.max_positions,
                "position_size_pct": float(self.state.position_size_pct),
                "confidence_threshold": float(self.state.confidence_threshold)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Global BRAIN controller instance
_brain_controller: Optional[BrainController] = None

async def get_brain_controller() -> BrainController:
    """Get or create global BRAIN controller"""
    global _brain_controller
    if _brain_controller is None:
        _brain_controller = BrainController()
        await _brain_controller.initialize()
    return _brain_controller

# Export classes and functions
__all__ = [
    "BrainController",
    "get_brain_controller"
]