"""
Day Trading Enhancement Engine - TradePulse.AI
==============================================

Dual-Mode Trading Architecture with High-Frequency Analysis
- Swing Trading Mode: 3-minute analysis cycles (default)
- Day Trading Mode: 30-second analysis cycles (aggressive)
- Session-aware optimization
- Ultra-low latency decision processing

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass

"""Day trading engine imports must succeed; no mocks allowed."""
from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine
from app.backend.services.intelligent_entry_engine import IntelligentEntryEngine
from app.backend.services.intelligent_exit_engine import IntelligentExitEngine
from app.backend.services.live_market_data import get_live_bitcoin_price, get_live_market_data, get_live_candlestick_data
from app.backend.services.professional_portfolio import get_professional_portfolio, PositionType
from app.backend.core.runtime_config import runtime_config_store
# Professional integrations - CRITICAL for Phase 1A
from app.backend.services.dynamic_risk_manager import DynamicRiskManager
from app.backend.services.emergency_controls import EmergencyControlSystem
from app.backend.services.market_data_persistence import load_recent, write_decisions

logger = logging.getLogger(__name__)

class TradingMode(str, Enum):
    """Trading mode types"""
    SWING = "swing"           # 3-minute cycles, longer positions
    DAY_TRADING = "day"       # 30-second cycles, intraday focus
    SCALPING = "scalping"     # 10-second cycles, ultra-short positions

class TradingSession(str, Enum):
    """Global trading sessions"""
    ASIAN = "asian"           # 21:00-06:00 UTC (Tokyo, Sydney)
    EUROPEAN = "european"     # 06:00-14:00 UTC (London, Frankfurt)
    AMERICAN = "american"     # 14:00-21:00 UTC (New York, Chicago)
    OVERLAP_EU_US = "overlap" # 12:00-16:00 UTC (High volume)

@dataclass
class TradingModeConfig:
    """Configuration for each trading mode"""
    mode: TradingMode
    analysis_interval: int     # Seconds between analyses
    position_duration: int     # Expected position duration (seconds)
    confidence_threshold: float # Minimum confidence to open position
    max_positions: int         # Maximum concurrent positions
    position_size_pct: float   # Position size as % of portfolio
    stop_loss_pct: float       # Stop loss percentage
    take_profit_pct: float     # Take profit percentage

class DayTradingEngine:
    """
    Advanced Day Trading Engine with Dual-Mode Architecture
    
    Features:
    - Swing vs Day trading modes
    - Session-aware optimization
    - High-frequency signal generation
    - Ultra-low latency processing
    """
    
    def __init__(self):
        self.is_initialized = False
        self.current_mode = TradingMode.SWING
        self.current_session = TradingSession.AMERICAN
        
        # Core engines
        self.enterprise_engine = None
        self.entry_engine = None
        self.exit_engine = None
        
        # PHASE 1A: Professional risk and safety systems
        self.risk_manager = None
        self.emergency_system = None
        
        # Trading state
        self.is_running = False
        self.analysis_task = None
        self.last_analysis_time = 0
        
        # Performance tracking (reset on each init)
        self.analyses_completed = 0
        self.positions_opened = 0
        self.avg_analysis_time_ms = 0
        
        # Mode configurations
        self.mode_configs = {
            TradingMode.SWING: TradingModeConfig(
                mode=TradingMode.SWING,
                analysis_interval=180,      # 3 minutes
                position_duration=7200,    # 2 hours average
                confidence_threshold=0.60,
                max_positions=3,
                position_size_pct=0.08,    # 8% per position
                stop_loss_pct=0.02,        # 2%
                take_profit_pct=0.04       # 4%
            ),
            TradingMode.DAY_TRADING: TradingModeConfig(
                mode=TradingMode.DAY_TRADING,
                analysis_interval=15,       # 15 seconds (day trading default)
                position_duration=1800,    # 30 minutes average
                confidence_threshold=0.65,
                max_positions=5,
                position_size_pct=0.05,    # 5% per position
                stop_loss_pct=0.015,       # 1.5%
                take_profit_pct=0.025      # 2.5%
            ),
            TradingMode.SCALPING: TradingModeConfig(
                mode=TradingMode.SCALPING,
                analysis_interval=10,       # 10 seconds
                position_duration=300,     # 5 minutes average
                confidence_threshold=0.70,
                max_positions=8,
                position_size_pct=0.03,    # 3% per position
                stop_loss_pct=0.01,        # 1%
                take_profit_pct=0.015      # 1.5%
            )
        }
        
        logger.info("🚀 Day Trading Engine initialized")
    
    async def initialize(self):
        """Initialize the day trading engine"""
        if self.is_initialized:
            return
            
        logger.info("🚀 Initializing Day Trading Engine...")
        
        try:
            # Initialize core engines
            self.enterprise_engine = EnterpriseTradingEngine()
            await self.enterprise_engine.initialize()
            
            self.entry_engine = IntelligentEntryEngine()
            await self.entry_engine.initialize()
            
            self.exit_engine = IntelligentExitEngine()
            await self.exit_engine.initialize()
            
            # PHASE 1A: Initialize professional risk and safety systems
            logger.info("🛡️ Initializing professional risk management...")
            self.risk_manager = DynamicRiskManager()
            await self.risk_manager.initialize()
            
            logger.info("🚨 Initializing emergency control system...")
            self.emergency_system = EmergencyControlSystem()
            await self.emergency_system.initialize()
            await self.emergency_system.start_monitoring()
            
            # Detect current trading session
            self.current_session = self._detect_current_session()
            
            self.is_initialized = True
            logger.info("✅ Day Trading Engine with professional risk management initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize day trading engine with professional systems: {e}")
            raise
    
    def set_trading_mode(self, mode: TradingMode) -> Dict[str, Any]:
        """Switch trading mode and update configurations"""
        old_mode = self.current_mode
        self.current_mode = mode
        
        config = self.mode_configs[mode]
        
        logger.info(f"🔄 Trading mode changed: {old_mode.value} → {mode.value}")
        logger.info(f"📊 New config: {config.analysis_interval}s intervals, "
                   f"{config.confidence_threshold:.1%} confidence threshold")
        
        return {
            "old_mode": old_mode.value,
            "new_mode": mode.value,
            "config": {
                "analysis_interval": config.analysis_interval,
                "confidence_threshold": config.confidence_threshold,
                "max_positions": config.max_positions,
                "position_size_pct": config.position_size_pct
            },
            "session": self.current_session.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _detect_current_session(self) -> TradingSession:
        """Detect current global trading session"""
        current_hour = datetime.now(timezone.utc).hour
        
        if 21 <= current_hour or current_hour < 6:
            return TradingSession.ASIAN
        elif 6 <= current_hour < 14:
            return TradingSession.EUROPEAN
        elif 14 <= current_hour < 21:
            return TradingSession.AMERICAN
        else:
            # Overlap period (12:00-16:00 UTC)
            if 12 <= current_hour < 16:
                return TradingSession.OVERLAP_EU_US
            return TradingSession.AMERICAN
    
    async def start_analysis_loop(self) -> Dict[str, Any]:
        """Start the continuous analysis loop based on current mode"""
        if self.is_running:
            return {"status": "already_running", "mode": self.current_mode.value}
        
        if not self.is_initialized:
            await self.initialize()
        
        self.is_running = True
        config = self.mode_configs[self.current_mode]
        
        logger.info(f"🚀 Starting {self.current_mode.value} trading analysis "
                   f"(every {config.analysis_interval} seconds)")
        
        # Start background analysis task
        self.analysis_task = asyncio.create_task(self._analysis_loop())
        
        return {
            "status": "started",
            "mode": self.current_mode.value,
            "analysis_interval": config.analysis_interval,
            "session": self.current_session.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def stop_analysis_loop(self) -> Dict[str, Any]:
        """Stop the continuous analysis loop"""
        if not self.is_running:
            return {"status": "not_running"}
        
        self.is_running = False
        
        if self.analysis_task and not self.analysis_task.done():
            self.analysis_task.cancel()
            try:
                await self.analysis_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"🛑 Stopped {self.current_mode.value} trading analysis")
        
        return {
            "status": "stopped",
            "analyses_completed": self.analyses_completed,
            "positions_opened": self.positions_opened,
            "avg_analysis_time_ms": self.avg_analysis_time_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _analysis_loop(self):
        """Main analysis loop - frequency depends on trading mode"""
        config = self.mode_configs[self.current_mode]
        
        try:
            while self.is_running:
                start_time = time.time()
                
                try:
                    # Honor runtime engine toggle
                    cfg = await runtime_config_store.get()
                    if not cfg.engine_enabled:
                        logger.debug("Engine disabled via runtime-config; skipping analysis cycle")
                        await asyncio.sleep(config.analysis_interval)
                        continue
                    
                    # Update current session
                    self.current_session = self._detect_current_session()
                    
                    # Run high-frequency market analysis
                    await self._run_market_analysis()
                    
                    # Track performance
                    analysis_time_ms = (time.time() - start_time) * 1000
                    self._update_performance_metrics(analysis_time_ms)
                    
                    if self.analyses_completed % 20 == 0:  # Log every 20 analyses
                        logger.info(f"📊 {self.current_mode.value} analysis #{self.analyses_completed} "
                                   f"completed in {analysis_time_ms:.1f}ms")
                    
                except Exception as e:
                    logger.error(f"❌ Analysis error in {self.current_mode.value} mode: {e}")
                
                # Wait for next analysis based on mode
                await asyncio.sleep(config.analysis_interval)
                
        except asyncio.CancelledError:
            logger.info(f"🛑 {self.current_mode.value} analysis loop cancelled")
        except Exception as e:
            logger.error(f"❌ Fatal error in {self.current_mode.value} analysis loop: {e}")
    
    async def _monitor_open_positions(self):
        """Monitor open positions using intelligent exit engine"""
        try:
            portfolio = await get_professional_portfolio("admin")
            active_positions = portfolio.get_active_positions()
            
            if not active_positions:
                return
            
            logger.info(f"🔍 Monitoring {len(active_positions)} open positions with intelligent exit engine")
            
            for position in active_positions:
                try:
                    # Convert position to dict for exit engine
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
                    
                    # Run intelligent exit analysis
                    exit_analysis = await self.exit_engine.analyze_exit_conditions(
                        symbol=position.symbol,
                        position_data=position_data
                    )
                    
                    # Log exit analysis result
                    logger.info(f"🚪 EXIT ANALYSIS {position.position_id}: "
                               f"{'EXIT' if exit_analysis['should_exit'] else 'HOLD'} "
                               f"conf={exit_analysis['confidence']:.2f} "
                               f"reason={exit_analysis.get('exit_reason', 'N/A')} "
                               f"pnl={exit_analysis.get('pnl_percent', 0):.2f}%")
                    
                    # Close position if exit engine recommends
                    if exit_analysis["should_exit"]:
                        logger.info(f"🚪 Closing position {position.position_id} - {exit_analysis['exit_reason']}")
                        realized_pnl = await portfolio.close_position(
                            position_id=position.position_id,
                            reason=exit_analysis["exit_reason"]
                        )
                        logger.info(f"✅ Position closed: {position.position_id} PnL=${float(realized_pnl):.2f}")
                        
                except Exception as e:
                    logger.error(f"❌ Exit analysis failed for {position.position_id}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Position monitoring failed: {e}")
    
    async def _run_market_analysis(self):
        """PHASE 1A: Professional tick-by-tick trading sequence with real data only"""
        config = self.mode_configs[self.current_mode]
        
        try:
            # (A) Get fresh data (WebSocket + REST fallback) - NO MOCKS
            logger.debug("📊 Getting fresh market data...")
            tick = await get_live_bitcoin_price()  # Latest tick price
            market_data = await get_live_market_data()  # Current market state
            candles = await get_live_candlestick_data("1m", 200)  # Recent history for LSTM
            
            logger.debug(f"🎯 Tick: BTCUSDT @${tick:.2f}, Candles: {len(candles)} loaded")
            
            # (B) Safety first - hard stop check (EMERGENCY CONTROLS)
            if self.emergency_system and await self.emergency_system.is_trading_halted():
                logger.warning("🚨 EMERGENCY: Trading halted by emergency controls")
                # Cancel all positions and return
                portfolio = await get_professional_portfolio("admin")
                active_positions = portfolio.get_active_positions()
                for position in active_positions:
                    await portfolio.close_position(position.position_id, "emergency_halt")
                return
            
            # (C) Enterprise signal (6-layer analysis) with REAL DATA
            signal = await self.enterprise_engine.generate_signal("BTCUSDT")
            
            # Enhanced layer analysis logging
            try:
                la = getattr(signal, 'layer_analysis', {}) or {}
                l1 = la.get("layer_1_regime", {})
                l3 = la.get("layer_3_reversal", {})
                l4 = la.get("layer_4_filters", {})
                l5 = la.get("layer_5_confidence", {})
                l6 = la.get("layer_6_timing", {})
                logger.info(
                    f"🧠 ENTERPRISE: L1={l1.get('regime','?')}/{l1.get('confidence',0):.2f} "
                    f"L3_rev={l3.get('reversal_probability',0):.2f} "
                    f"L4_filt={l4.get('filter_score',0):.2f} "
                    f"L5_conf={l5.get('confidence',0):.2f} "
                    f"L6_time={l6.get('timing_score',0):.2f} → {signal.action} ({signal.confidence:.2f})"
                )
            except Exception:
                pass
            
            if not signal:
                logger.warning("⚠️ No signal generated from enterprise engine")
                return
                
            # Get portfolio for risk and position management
            portfolio = await get_professional_portfolio("admin")
            
            # (D) Risk gate (pre-trade assessment) - DYNAMIC RISK MANAGER
            risk_assessment = None
            if self.risk_manager:
                try:
                    risk_assessment = await self.risk_manager.assess_pre_trade(
                        signal=signal, 
                        portfolio=portfolio, 
                        candles=candles, 
                        tick={"price": tick, "timestamp": datetime.now(timezone.utc)}
                    )
                    
                    if risk_assessment and hasattr(risk_assessment, 'block_reason') and risk_assessment.block_reason:
                        logger.info(f"🛡️ Risk blocked: {risk_assessment.block_reason}")
                        await self._audit_decision(signal, None, None, risk_assessment, "risk_blocked")
                        return
                        
                    logger.debug(f"🛡️ Risk assessment: score={getattr(risk_assessment, 'risk_score', 'N/A'):.2f}")
                except Exception as e:
                    logger.warning(f"⚠️ Risk manager failed, proceeding without: {e}")
            
            # (E) Entry/Exit decisions (parallel execution)
            # Monitor positions first with exit engine
            await self._monitor_open_positions()
            
            # Session-aware confidence adjustment
            session_multiplier = self._get_session_confidence_multiplier()
            adjusted_confidence = signal.confidence * session_multiplier
            
            logger.info(f"🎯 Signal: {signal.action} conf={signal.confidence:.2f} → {adjusted_confidence:.2f} (session={self.current_session.value})")
            
            # Check threshold and action type
            if adjusted_confidence > config.confidence_threshold and signal.action in ["BUY", "SELL"]:
                
                # Check position limits
                active_positions = len(portfolio.get_active_positions())
                if active_positions >= config.max_positions:
                    logger.debug(f"⚠️ Max positions reached: {active_positions}/{config.max_positions}")
                    await self._audit_decision(signal, None, None, risk_assessment, "max_positions")
                    return
                
                # ENTRY ANALYSIS using intelligent_entry_engine
                entry_decision = await self._run_professional_entry_analysis(
                    signal, portfolio, candles, tick, risk_assessment
                )
                
                logger.info(
                    f"🚦 ENTRY: {('ENTER' if entry_decision.get('should_enter') else 'WAIT')} "
                    f"conf={entry_decision.get('confidence',0):.2f} reason={entry_decision.get('reasoning','')}"
                )
                
                # (F) Position orchestration
                if entry_decision.get("should_enter", False):
                    # Calculate position size with risk manager
                    if self.risk_manager and risk_assessment:
                        try:
                            position_size = await self.risk_manager.calculate_position_size(
                                signal, risk_assessment, portfolio, tick
                            )
                        except Exception as e:
                            logger.warning(f"Risk manager size calculation failed: {e}, using fallback")
                            position_size = float(portfolio.cash_balance) * config.position_size_pct
                    else:
                        # Fallback to mode config
                        position_size = float(portfolio.cash_balance) * config.position_size_pct
                    
                    # Open position
                    from decimal import Decimal
                    logger.info(f"🚀 Opening position: {signal.symbol} {signal.action} size={position_size}")
                    
                    position_id = await portfolio.open_position(
                        symbol=signal.symbol,
                        position_type=PositionType.LONG if signal.action == "BUY" else PositionType.SHORT,
                        size=Decimal(str(position_size)),
                        ai_confidence=adjusted_confidence,
                        ai_reasoning=f"{self.current_mode.value}: {signal.reasoning}",
                        stop_loss_pct=Decimal(str(config.stop_loss_pct)),
                        take_profit_pct=Decimal(str(config.take_profit_pct))
                    )
                    
                    self.positions_opened += 1
                    logger.info(f"✅ POSITION OPENED: {position_id} ({signal.action}) conf={adjusted_confidence:.1%}")
                    
                    # (G) In-position risk management
                    if self.risk_manager:
                        try:
                            await self.risk_manager.assess_in_position(
                                portfolio, {"price": tick, "timestamp": datetime.now(timezone.utc)}
                            )
                        except Exception as e:
                            logger.warning(f"In-position risk assessment failed: {e}")
                    
                    await self._audit_decision(signal, entry_decision, None, risk_assessment, "position_opened")
                else:
                    await self._audit_decision(signal, entry_decision, None, risk_assessment, "entry_rejected")
            else:
                reason = "low_confidence" if adjusted_confidence <= config.confidence_threshold else "hold_signal"
                logger.debug(f"📊 Signal rejected: {reason}")
                await self._audit_decision(signal, None, None, risk_assessment, reason)
                
        except Exception as e:
            logger.error(f"❌ Professional trading analysis failed: {e}")
            # Emergency fallback - ensure no hanging positions
            if self.emergency_system:
                try:
                    await self.emergency_system.handle_analysis_failure(str(e))
                except Exception as e2:
                    logger.error(f"Emergency system also failed: {e2}")
    
    async def _run_professional_entry_analysis(self, signal: Any, portfolio: Any, candles: List, tick: float, risk_assessment: Any) -> Dict[str, Any]:
        """PHASE 1A: Professional entry analysis with risk integration"""
        try:
            # Get current market data
            market_data = await get_live_market_data()
            
            # Run intelligent entry analysis
            entry_result = await self.entry_engine.analyze_entry_opportunity(
                symbol=signal.symbol,
                signal_data={
                    "action": signal.action,
                    "confidence": signal.confidence,
                    "reasoning": signal.reasoning
                },
                user_portfolio={
                    "available_cash": float(portfolio.cash_balance),
                    "active_positions": portfolio.get_active_positions(),
                    "max_positions": self.mode_configs[self.current_mode].max_positions,
                    "daily_trades": portfolio.daily_trades,
                    "max_daily_trades": portfolio.max_daily_trades
                }
            )
            
            return {
                "should_enter": entry_result.should_enter,
                "confidence": entry_result.confidence,
                "entry_quality": entry_result.entry_quality.value,
                "optimal_price": entry_result.optimal_entry_price,
                "reasoning": f"Day trading analysis: {entry_result.entry_reason.value}"
            }
            
        except Exception as e:
            logger.error(f"Day trading entry analysis failed: {e}")
            return {"should_enter": False, "reasoning": f"Analysis failed: {e}"}
    
    def _get_session_confidence_multiplier(self) -> float:
        """Get confidence multiplier based on current trading session"""
        session_multipliers = {
            TradingSession.ASIAN: 0.85,      # Lower volatility
            TradingSession.EUROPEAN: 1.0,    # Standard
            TradingSession.AMERICAN: 1.1,    # Higher volume
            TradingSession.OVERLAP_EU_US: 1.2 # Highest liquidity
        }
        
        base_multiplier = session_multipliers.get(self.current_session, 1.0)
        
        # Additional boost for day trading during high-volume sessions
        if self.current_mode == TradingMode.DAY_TRADING:
            if self.current_session in [TradingSession.AMERICAN, TradingSession.OVERLAP_EU_US]:
                base_multiplier *= 1.05
        
        return base_multiplier
        
    async def _audit_decision(self, signal, entry_decision, exit_decision, risk_assessment, outcome: str):
        """PHASE 1A: Complete decision audit trail for professional operation"""
        try:
            audit_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": "BTCUSDT",
                "signal_action": signal.action if signal else "none",
                "signal_confidence": signal.confidence if signal else 0.0,
                "entry_decision": entry_decision.get('should_enter', False) if entry_decision else False,
                "entry_reason": entry_decision.get('reasoning', 'none') if entry_decision else "none",
                "exit_decision": exit_decision.get('should_exit', False) if exit_decision else False,
                "exit_reason": exit_decision.get('reasoning', 'none') if exit_decision else "none",
                "risk_score": getattr(risk_assessment, 'risk_score', 0.0) if risk_assessment else 0.0,
                "risk_block": getattr(risk_assessment, 'block_reason', None) if risk_assessment else None,
                "outcome": outcome,
                "trading_mode": self.current_mode.value,
                "session": self.current_session.value
            }
            
            # Use market data persistence for audit logging
            await write_decisions(entry_decision, exit_decision, risk_assessment, signal)
            logger.debug(f"📝 Decision audited: {outcome}")
            
        except Exception as e:
            logger.error(f"❌ Audit logging failed: {e}")
    
    def _update_performance_metrics(self, analysis_time_ms: float):
        """Update performance tracking metrics"""
        self.analyses_completed += 1
        
        # Update rolling average of analysis time
        if self.avg_analysis_time_ms == 0:
            self.avg_analysis_time_ms = analysis_time_ms
        else:
            # Exponential moving average
            alpha = 0.1
            self.avg_analysis_time_ms = (alpha * analysis_time_ms + 
                                       (1 - alpha) * self.avg_analysis_time_ms)
        
        # Update last analysis timestamp
        self.last_analysis_time = time.time()
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get comprehensive engine status"""
        config = self.mode_configs[self.current_mode]
        
        return {
            "is_initialized": self.is_initialized,
            "is_running": self.is_running,
            "current_mode": self.current_mode.value,
            "current_session": self.current_session.value,
            "mode_config": {
                "analysis_interval": config.analysis_interval,
                "confidence_threshold": config.confidence_threshold,
                "max_positions": config.max_positions,
                "position_size_pct": config.position_size_pct
            },
            "performance": {
                "analyses_completed": self.analyses_completed,
                "positions_opened": self.positions_opened,
                "avg_analysis_time_ms": round(self.avg_analysis_time_ms, 2),
                "last_analysis_ago_seconds": round(time.time() - self.last_analysis_time, 1) if self.last_analysis_time > 0 else None
            },
            "ultra_low_latency": self.avg_analysis_time_ms < 10,  # <10ms target
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_available_modes(self) -> Dict[str, Any]:
        """Get all available trading modes and their configurations"""
        return {
            mode.value: {
                "name": mode.value.title(),
                "analysis_interval": config.analysis_interval,
                "position_duration_min": config.position_duration // 60,
                "confidence_threshold": config.confidence_threshold,
                "max_positions": config.max_positions,
                "risk_profile": "Conservative" if mode == TradingMode.SWING 
                              else "Moderate" if mode == TradingMode.DAY_TRADING 
                              else "Aggressive"
            }
            for mode, config in self.mode_configs.items()
        }

# Global day trading engine instance
_day_trading_engine: Optional[DayTradingEngine] = None

async def get_day_trading_engine() -> DayTradingEngine:
    """Get or create global day trading engine"""
    global _day_trading_engine
    if _day_trading_engine is None:
        _day_trading_engine = DayTradingEngine()
        await _day_trading_engine.initialize()
    return _day_trading_engine

# Export classes and functions
__all__ = [
    "DayTradingEngine", 
    "TradingMode", 
    "TradingSession", 
    "TradingModeConfig",
    "get_day_trading_engine"
]