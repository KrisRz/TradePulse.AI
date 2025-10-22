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
from app.backend.services.live_market_data import get_live_bitcoin_price, get_live_market_data, get_live_candlestick_data, get_live_market_data_service
from app.backend.services.professional_portfolio import get_professional_portfolio, PositionType, PositionStatus
from app.backend.core.runtime_config import runtime_config_store
from app.backend.config.day_trading_config import get_day_trading_config
# Professional integrations - CRITICAL for Phase 1A
from app.backend.services.dynamic_risk_manager import DynamicRiskManager
from app.backend.services.emergency_controls import EmergencyControlSystem
from app.backend.services.market_data_persistence import load_recent, write_decisions
from app.backend.services.trading_performance_tracker import get_trading_performance_tracker
from app.backend.utils.safe_formatting import (
    safe_format_price, safe_format_percentage, safe_format_number,
    ensure_price_not_none, ensure_confidence_not_none
)

logger = logging.getLogger(__name__)


def validate_signal_position_mapping(signal_action: str, position_type: "PositionType") -> None:
    """Validate that signal action maps correctly to position type"""
    from app.backend.services.professional_portfolio import PositionType
    
    valid_mappings = {
        "BUY": PositionType.LONG,
        "SELL": PositionType.SHORT,
        "LONG": PositionType.LONG,
        "SHORT": PositionType.SHORT
    }
    
    expected_type = valid_mappings.get(signal_action.upper())
    if expected_type and expected_type != position_type:
        raise ValueError(
            f"Signal-Position mismatch: {signal_action} signal should create {expected_type.value} position, "
            f"not {position_type.value} position"
        )
    
    logger.debug(f"✅ Signal-position mapping validated: {signal_action} → {position_type.value}")


class TradingMode(str, Enum):
    """Trading mode types - DAY TRADING FOCUSED"""
    DAY_TRADING = "day"       # 15-second cycles, intraday focus - MAIN MODE
    SCALPING = "scalping"     # 10-second cycles, ultra-short positions - OPTIONAL

class TradingSession(str, Enum):
    """Global trading sessions"""
    ASIAN = "asian"                    # 21:00-06:00 UTC (Tokyo, Sydney)
    EUROPEAN = "european"              # 06:00-14:00 UTC (London, Frankfurt)
    AMERICAN = "american"              # 14:00-21:00 UTC (New York, Chicago)
    OVERLAP_ASIAN_EU = "overlap_asian_eu"      # 06:00-09:00 UTC (Tokyo/London)
    OVERLAP_EU_US = "overlap_eu_us"            # 12:00-16:00 UTC (London/NY - Highest liquidity)
    OVERLAP_US_ASIAN = "overlap_us_asian"      # 21:00-00:00 UTC (NY/Sydney)

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
        self.current_mode = TradingMode.DAY_TRADING  # DAY TRADING ONLY!
        self.current_session = TradingSession.AMERICAN
        
        # Core engines
        self.enterprise_engine = None
        self.entry_engine = None
        self.exit_engine = None
        
        # PHASE 1A: Professional risk and safety systems
        self.risk_manager = None
        self.emergency_system = None
        
        # PHASE 4.3: Performance tracking and learning
        self.performance_tracker = None
        
        # Trading state
        self.is_running = False
        self.analysis_task = None
        self.last_analysis_time = 0
        
        # Performance tracking (reset on each init)
        self.analyses_completed = 0
        self.positions_opened = 0
        self.avg_analysis_time_ms = 0
        # Circuit breaker (volume z-score) hysteresis
        # 🔧 FIX (Oct 2025): Relaxed thresholds to allow trading in volatile spikes
        # Previous: on=3.5, off=2.0, safe_ticks=3 (too restrictive - blocked valid entries)
        # New: on=4.5, off=2.5, safe_ticks=2 (allows more entries, still protects from extremes)
        self.cb_active = False
        self.cb_threshold_on = 4.5  # Raised from 3.5 (only extreme spikes trigger halt)
        self.cb_threshold_off = 2.5  # Raised from 2.0 (easier to recover)
        self.cb_safe_ticks = 0
        self.cb_safe_required = 2  # Reduced from 3 (faster recovery)
        self.cb_safe_window_sec = 90  # Allow accumulation across 90s in micro-vol
        # EMA z-score for smoothing (prevents single spike halts)
        self.z_ema = None
        self.z_ema_alpha = 0.3  # 30% weight to new value, 70% to EMA
        # Duplicate suppression burst tracker (timestamps of suppressions)
        self._dupe_suppress_ts: List[float] = []
        
        # 🔮 LAYER 7: Price Prediction Tracking (Day Trading ML Enhancement)
        self.prediction_cache = {}  # Cache predictions (5-minute TTL)
        self.prediction_accuracy_tracker = []  # Track prediction vs actual prices
        self.last_prediction_time = 0
        self.prediction_update_interval = 300  # 5 minutes
        
        # ✅ PROFESSIONAL: Use adaptive config from day_trading_config.py
        from app.backend.core.config import get_settings
        s = get_settings()
        
        # Static config for compatibility (used for max_positions only)
        # Other params delegated to adaptive systems:
        # - analysis_interval → adaptive (volatility-based)
        # - confidence_threshold → ConfidenceThresholds (unified)
        # - position_size_pct → Kelly Criterion (Entry Engine)
        # - stop_loss_pct → ATR-based (Exit Engine)
        # - take_profit_pct → ATR-based (Exit Engine)
        self.mode_configs = {
            TradingMode.DAY_TRADING: TradingModeConfig(
                mode=TradingMode.DAY_TRADING,
                analysis_interval=8,        # Base interval (adaptive in _analysis_loop)
                position_duration=900,      # Informational only (time stop disabled, AI decides)
                confidence_threshold=0.30,  # Delegated to ConfidenceThresholds
                max_positions=15,           # 🎯 INCREASED: 15 positions (was 12) for more opportunities
                position_size_pct=0.015,   # Delegated to Kelly Criterion
                stop_loss_pct=0.004,       # Delegated to Exit Engine
                take_profit_pct=0.003      # Delegated to Exit Engine
            )
        }
        
        logger.info("🚀 Day Trading Engine initialized")
    
    async def initialize(self):
        """Initialize the day trading engine"""
        if self.is_initialized:
            logger.info("🔄 PIPELINE DEBUG: Day Trading Engine already initialized, skipping...")
            return
            
        logger.info("🚀 Initializing Day Trading Engine...")
        logger.info("📊 PIPELINE DEBUG: Day Trading Engine - Starting initialization sequence")
        logger.info(f"🎯 PIPELINE DEBUG: Day Trading Engine - Component: Day Trading Engine v1.0.0")
        logger.info(f"🎯 PIPELINE DEBUG: Day Trading Engine - Purpose: High-frequency trading coordination")
        
        try:
            # Use DI container for core engines to avoid circular dependencies
            logger.info("🔗 PIPELINE DEBUG: Day Trading Engine - Connecting to DI container...")
            from app.backend.core.container import get_container
            container = get_container()
            logger.info("✅ PIPELINE DEBUG: Day Trading Engine - DI container connected")
            
            # Get engines from DI container (they're already initialized)
            logger.info("🤖 PIPELINE DEBUG: Day Trading Engine - Retrieving Enterprise Engine...")
            try:
                enterprise_engine_obj = container.get("enterprise_trading_engine")
                from app.backend.core.container import require_instance
                self.enterprise_engine = require_instance("enterprise_trading_engine", enterprise_engine_obj)
                logger.info("✅ Enterprise engine retrieved from DI container")
                logger.info("✅ PIPELINE DEBUG: Day Trading Engine - Enterprise Engine connected")
            except Exception:
                # Fallback: create our own instance
                logger.warning("⚠️ Enterprise engine not in DI, creating local instance")
                logger.warning("⚠️ PIPELINE DEBUG: Day Trading Engine - Creating local Enterprise Engine instance")
                self.enterprise_engine = EnterpriseTradingEngine()
                await self.enterprise_engine.initialize()
            
            try:
                # Ensure AI services are initialized first
                logger.info("🤖 PIPELINE DEBUG: Day Trading Engine - Ensuring AI services are initialized...")
                await container._initialize_ai_services()
                
                logger.info("🤖 PIPELINE DEBUG: Day Trading Engine - Retrieving Entry Engine from DI...")
                self.entry_engine = container.get("entry_engine")
                if self.entry_engine is None:
                    raise ValueError("Entry engine not found in DI container")
                
                # FIXED: Direct instance access (no function call needed)
                logger.info(f"✅ Retrieved Entry Engine instance: {type(self.entry_engine).__name__}")
                if self.entry_engine is None:
                    raise ValueError("Entry engine is None from DI container")
                
                logger.info("✅ PIPELINE DEBUG: Day Trading Engine - Using shared Entry Engine from DI")
                
                logger.info("✅ Enhanced Entry Engine retrieved from DI container")
                logger.info("✅ PIPELINE DEBUG: Day Trading Engine - Entry Engine connected")
            except Exception as e:
                logger.error(f"❌ Entry engine DI retrieval failed: {e}")
                logger.warning("⚠️ PIPELINE DEBUG: Day Trading Engine - Creating and registering Entry Engine")
                
                # FIXED: Create and register instance directly to avoid callable errors
                from app.backend.services.intelligent_entry_engine import IntelligentEntryEngine
                self.entry_engine = IntelligentEntryEngine()
                await self.entry_engine.initialize()
                
                # FIXED: Register direct instance (not lambda) to prevent callable errors
                try:
                    container.register_singleton("entry_engine", self.entry_engine)  # Direct instance
                    logger.info("✅ Entry Engine registered in DI container")
                except:
                    pass  # Continue if registration fails
            
            try:
                self.exit_engine = container.get("exit_engine")
                logger.info("✅ Exit engine retrieved from DI container")
            except Exception:
                logger.warning("⚠️ Exit engine not in DI, creating local instance")
                from app.backend.services.intelligent_exit_engine import IntelligentExitEngine
                self.exit_engine = IntelligentExitEngine()
                await self.exit_engine.initialize()
                # FIXED: Register immediately to prevent orphans
                try:
                    container.register_singleton("exit_engine", self.exit_engine)
                    logger.info("✅ Exit Engine registered in DI container")
                except:
                    pass
            
            # PHASE 1A: Use DI container for risk and safety systems
            logger.info("🛡️ Getting professional risk management from DI...")
            try:
                self.risk_manager = container.get("risk_manager")
                logger.info("✅ Risk manager retrieved from DI container")
            except Exception:
                logger.warning("⚠️ Risk manager not in DI, creating local instance")
                from app.backend.services.dynamic_risk_manager import DynamicRiskManager
                self.risk_manager = DynamicRiskManager()
                await self.risk_manager.initialize()
                # FIXED: Register immediately to prevent orphans
                try:
                    container.register_singleton("risk_manager", self.risk_manager)
                    logger.info("✅ Risk Manager registered in DI container")
                except:
                    pass
            
            logger.info("🚨 Initializing emergency control system...")
            self.emergency_system = EmergencyControlSystem()
            await self.emergency_system.initialize()
            await self.emergency_system.start_monitoring()
            
            # PHASE 4.3: Initialize performance tracking and learning
            logger.info("📊 Initializing performance tracking system...")
            self.performance_tracker = await get_trading_performance_tracker()
            await self.performance_tracker.start_tracking()
            
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
        """Detect current global trading session with overlaps"""
        current_hour = datetime.now(timezone.utc).hour
        
        if 21 <= current_hour or current_hour < 6:
            # Asian session with US overlap check
            if 21 <= current_hour <= 23:
                return TradingSession.OVERLAP_US_ASIAN
            return TradingSession.ASIAN
        elif 6 <= current_hour < 14:
            # European session with overlap checks
            if 6 <= current_hour < 9:
                return TradingSession.OVERLAP_ASIAN_EU
            elif 12 <= current_hour < 14:
                return TradingSession.OVERLAP_EU_US
            return TradingSession.EUROPEAN
        elif 14 <= current_hour < 21:
            # American session with EU overlap check
            if 14 <= current_hour < 16:
                return TradingSession.OVERLAP_EU_US
            return TradingSession.AMERICAN
        else:
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
        """Main analysis loop - frequency adapts to market volatility"""
        config = self.mode_configs[self.current_mode]
        day_config = get_day_trading_config()
        
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
                    
                    # Monitor open positions with exit engine (EVERY CYCLE for day trading)
                    await self._monitor_open_positions()
                    
                    # Track performance
                    analysis_time_ms = (time.time() - start_time) * 1000
                    self._update_performance_metrics(analysis_time_ms)
                    try:
                        from app.backend.services.metrics import inc_analysis_cycle
                        inc_analysis_cycle()
                    except Exception:
                        pass
                    
                    if self.analyses_completed % 20 == 0:  # Log every 20 analyses
                        logger.info(f"📊 {self.current_mode.value} analysis #{self.analyses_completed} "
                                   f"completed in {analysis_time_ms:.1f}ms")
                    
                except Exception as e:
                    logger.error(f"❌ Analysis error in {self.current_mode.value} mode: {e}")
                
                # ✅ ADAPTIVE INTERVAL: Calculate based on current volatility
                try:
                    service = await get_live_market_data_service()
                    recent_candles = service.get_recent_candles("1m", 20)
                    
                    # Calculate realized volatility from recent closes
                    current_vol = 0.015  # default
                    if recent_candles and len(recent_candles) >= 10:
                        closes = []
                        for c in recent_candles[-10:]:
                            if isinstance(c, dict):
                                closes.append(float(c.get("close", 0.0)))
                            elif isinstance(c, list) and len(c) >= 5:
                                closes.append(float(c[4]))
                        
                        if len(closes) >= 10 and min(closes) > 0:
                            import numpy as np
                            current_vol = float(np.std(closes) / np.mean(closes))
                    
                    adaptive_interval = day_config.get_analysis_interval(current_vol)
                    await asyncio.sleep(adaptive_interval)
                    
                except Exception as e:
                    logger.debug(f"Adaptive interval calculation failed: {e}, using base interval")
                    await asyncio.sleep(config.analysis_interval)
                
        except asyncio.CancelledError:
            logger.info(f"🛑 {self.current_mode.value} analysis loop cancelled")
        except Exception as e:
            logger.error(f"❌ Fatal error in {self.current_mode.value} analysis loop: {e}")
    
    async def _monitor_open_positions(self):
        """Monitor open positions using intelligent exit engine"""
        try:
            # Get portfolio (will use TTL-based caching)
            portfolio = await get_professional_portfolio("admin")
            try:
                from app.backend.services.metrics import set_concurrent_positions
                set_concurrent_positions(len(portfolio.get_active_positions()))
            except Exception:
                pass
            await portfolio.update_positions_with_live_data()  # Update with live prices
            active_positions = portfolio.get_active_positions()
            
            if not active_positions:
                return
            
            logger.info(f"🔍 Monitoring {len(active_positions)} open positions with intelligent exit engine (LIVE DATA SYNC)")
            
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
                    # 🔧 FIX (Oct 2025): Show PnL with sign (+/-)
                    pnl_pct = exit_analysis.get('pnl_percent', 0)
                    logger.info(f"🚪 EXIT ANALYSIS {position.position_id}: "
                               f"{'EXIT' if exit_analysis['should_exit'] else 'HOLD'} "
                               f"conf={exit_analysis['confidence']:.2f} "
                               f"reason={exit_analysis.get('exit_reason', 'N/A')} "
                               f"pnl={pnl_pct:+.2f}%")
                    
                    # Close position if exit engine recommends
                    if exit_analysis["should_exit"]:
                        # 🔧 FIX (Oct 2025): Idempotency check - prevent double-close attempts
                        if position.position_id not in portfolio.positions:
                            logger.info(f"⏭️ Position {position.position_id} already closed, skipping")
                            continue
                        
                        if portfolio.positions[position.position_id].status != PositionStatus.OPEN:
                            logger.info(f"⏭️ Position {position.position_id} status={portfolio.positions[position.position_id].status}, skipping close")
                            continue
                        
                        logger.info(f"🚪 Closing position {position.position_id} - {exit_analysis['exit_reason']}")
                        realized_pnl = await portfolio.close_position(
                            position_id=position.position_id,
                            reason=exit_analysis["exit_reason"]
                        )
                        # CRITICAL FIX: Save portfolio state after closing position
                        await portfolio._save_portfolio_state()
                        logger.info(f"✅ Position closed: {position.position_id} PnL=${float(realized_pnl):.2f}")
                        
                except Exception as e:
                    logger.error(f"❌ Exit analysis failed for {position.position_id}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Position monitoring failed: {e}")
    
    async def _is_duplicate_entry(self, signal, portfolio) -> bool:
        """Check if this entry would be a duplicate of recent positions - SCALPING OPTIMIZED"""
        
        # AGGRESSIVE SCALPING: Bypass duplicate prevention for high confidence signals
        # This enables rapid re-entry for profitable setups
        if hasattr(signal, 'confidence') and signal.confidence > 0.75:  # Lower threshold to 75%
            logger.info(f"🚀 HIGH CONFIDENCE BYPASS ({signal.confidence:.1%}) - allowing rapid re-entry")
            return False
            
        # SCALPING MODE: Much more permissive duplicate checking
        # For small trades, we want more opportunities, not strict prevention
        try:
            current_time = datetime.now(timezone.utc)
            current_price = await get_live_bitcoin_price()
            
            # Load runtime-config and settings for duplicate thresholds
            from app.backend.core.runtime_config import runtime_config_store
            from app.backend.core.config import get_settings
            cfg = await runtime_config_store.get()
            s = get_settings()
            active_window = int(getattr(cfg, "dup_active_window_sec", s.DUP_ACTIVE_WINDOW_SEC))
            active_delta = float(getattr(cfg, "dup_active_price_delta_pct", s.DUP_ACTIVE_PRICE_DELTA_PCT))
            closed_window = int(getattr(cfg, "dup_closed_window_sec", s.DUP_CLOSED_WINDOW_SEC))
            closed_delta = float(getattr(cfg, "dup_closed_price_delta_pct", s.DUP_CLOSED_PRICE_DELTA_PCT))

            # Volatility-adaptive thresholds (realized 5m)
            realized_vol_5m = 0.0
            try:
                service = await get_live_market_data_service()
                candles = service.get_recent_candles("1m", 5)
                if candles and len(candles) >= 5:
                    closes = []
                    for c in candles[-5:]:
                        if isinstance(c, dict):
                            closes.append(float(c.get("close", 0.0)))
                        elif isinstance(c, list) and len(c) >= 5:
                            closes.append(float(c[4]))
                    if len(closes) >= 5 and min(closes) > 0:
                        import numpy as _np
                        rets = _np.diff(_np.log(_np.array(closes)))
                        realized_vol_5m = float(_np.sqrt(_np.mean(rets**2)))
            except Exception:
                pass

            # 🎯 DAY TRADING OPTIMIZED: Much shorter windows for catching multiple reversals
            adapt_active_delta = max(active_delta, 1.0 * realized_vol_5m)  # Very tolerant
            adapt_closed_delta = max(closed_delta * 3.0, 1.2 * realized_vol_5m)  # Extremely tolerant for re-entry  
            
            # 🔧 FIX (Oct 2025): CRYPTO DAY TRADING cooldown with meaningful-change bypass
            # Crypto requires faster re-entry than stocks (24/7, high liquidity, fast moves)
            adapt_active_window = max(10, 60)  # 1 minute active window (crypto scalping)
            
            # Base cooldown: 90s for crypto day trading (was 5min - too slow!)
            REENTRY_COOLDOWN_BASE = 90  # 90 seconds base (crypto day trading)
            MEANINGFUL_PRICE_ATR = 0.35  # 35% ATR move = meaningful
            MEANINGFUL_CONF_DELTA = 0.12  # 12pp confidence change = meaningful
            
            adapt_closed_window = REENTRY_COOLDOWN_BASE  # Will be adjusted per-position below

            # Check recent positions (active) within adaptive window
            for position in portfolio.get_active_positions():
                time_diff = (current_time - position.entry_time).total_seconds()
                price_diff = abs(current_price - float(position.entry_price)) / float(position.entry_price)
                
                # Consider duplicate if:
                # 1. Same direction (LONG/SHORT)
                # 2. Within window
                # 3. Price difference < delta
                same_direction = (
                    (signal.action == "BUY" and position.type == PositionType.LONG) or
                    (signal.action == "SELL" and position.type == PositionType.SHORT)
                )
                
                if same_direction and time_diff < adapt_active_window and price_diff < adapt_active_delta:
                    # 🔧 FIX (Oct 2025): Consolidated duplicate log with details
                    cooldown_left = adapt_active_window - time_diff
                    logger.warning(f"🚫 Duplicate entry blocked: {signal.action} within {adapt_active_window:.0f}s window "
                                 f"(reason=active_duplicate, cooldown={adapt_active_window:.0f}s, remaining={cooldown_left:.0f}s, "
                                 f"price_delta={price_diff:.2%})")
                    try:
                        from app.backend.services.metrics import inc_decision_dupe
                        inc_decision_dupe("similar_signal")
                    except Exception:
                        pass
                    # Audit with meta
                    try:
                        await self._audit_decision(
                            signal, None, None, None, "duplicate_entry_prevented",
                            meta={
                                "reason": "active_duplicate",
                                "remaining_sec": float(cooldown_left),
                                "cooldown_sec": float(adapt_active_window),
                                "base": 90, "tp": 60, "sl": 180, "unknown": 90, "active_dup": 60
                            }
                        )
                    except Exception:
                        pass
                    return True
            
            # 🔧 FIX (Oct 2025): Smart cooldown with meaningful-change bypass
            # Check closed positions with adaptive cooldown based on exit reason
            for position in portfolio.closed_positions[-10:]:  # Check last 10 closed
                if position.exit_time:
                    time_diff = (current_time - position.exit_time).total_seconds()
                    
                    # Exit-aware cooldown: longer for stop-loss, shorter for take-profit (CRYPTO DAY TRADING)
                    exit_reason = getattr(position, 'exit_reason', 'unknown')
                    if 'stop' in exit_reason.lower() or 'emergency' in exit_reason.lower():
                        effective_cooldown = 180  # 3 min for stop-loss (crypto day trading)
                    elif 'profit' in exit_reason.lower() or 'target' in exit_reason.lower():
                        effective_cooldown = 60  # 1 min for TP (quick re-entry in crypto)
                    else:
                        effective_cooldown = REENTRY_COOLDOWN_BASE  # 90s default
                    
                    if time_diff < effective_cooldown:
                        price_diff = abs(current_price - float(position.exit_price or position.entry_price)) / float(position.entry_price)
                        same_direction = (
                            (signal.action == "BUY" and position.type == PositionType.LONG) or
                            (signal.action == "SELL" and position.type == PositionType.SHORT)
                        )
                        
                        playbook_match = getattr(signal, 'playbook', 'default') == getattr(position, 'playbook', 'default')
                        
                        if same_direction and playbook_match:
                            # Check for meaningful change that can bypass cooldown
                            meaningful_change = False
                            
                            # 1) Significant price move (35% of ATR)
                            exit_atr = getattr(position, 'exit_atr', 0.02)  # Fallback 2%
                            if exit_atr > 0 and price_diff >= (MEANINGFUL_PRICE_ATR * exit_atr):
                                meaningful_change = True
                                logger.info(f"✅ Meaningful price move: {price_diff:.2%} >= {MEANINGFUL_PRICE_ATR * exit_atr:.2%} (0.35×ATR)")
                            
                            # 2) Confidence delta (L5/L6 changed significantly)
                            exit_conf = getattr(position, 'ai_confidence', 0.5)
                            signal_conf = getattr(signal, 'confidence', 0.5)
                            if abs(signal_conf - exit_conf) >= MEANINGFUL_CONF_DELTA:
                                meaningful_change = True
                                logger.info(f"✅ Meaningful confidence shift: Δ={abs(signal_conf - exit_conf):.2f} >= {MEANINGFUL_CONF_DELTA:.2f}")
                            
                            # 3) Momentum breakout (vol spike + timing surge)
                            try:
                                from app.backend.services.live_market_data import get_live_market_data
                                import asyncio
                                market_data = asyncio.run(get_live_market_data()) if asyncio.get_event_loop().is_running() == False else None
                                if market_data:
                                    vol_ratio = market_data.get('volume_ratio', 1.0)
                                    timing_score = getattr(signal, 'timing_score', 0.0)
                                    if vol_ratio > 3.0 and abs(timing_score) > 0.15:
                                        meaningful_change = True
                                        logger.info(f"✅ Momentum breakout: vol_ratio={vol_ratio:.1f}, timing={timing_score:+.2f}")
                            except Exception:
                                pass
                            
                            if not meaningful_change:
                                cooldown_left = effective_cooldown - time_diff
                                # Map exit_reason to cooldown type
                                cooldown_type = "unknown"
                                if 'stop' in exit_reason.lower() or 'emergency' in exit_reason.lower():
                                    cooldown_type = "stop_loss"
                                elif 'profit' in exit_reason.lower() or 'target' in exit_reason.lower():
                                    cooldown_type = "take_profit"
                                
                                logger.warning(f"🚫 Re-entry blocked: {cooldown_left:.0f}s remaining "
                                             f"(reason={cooldown_type}, cooldown={effective_cooldown:.0f}s, "
                                             f"base=90s, tp=60s, sl=180s)")
                                try:
                                    from app.backend.services.metrics import inc_decision_dupe
                                    inc_decision_dupe("reentry_cooldown")
                                except Exception:
                                    pass
                                # Audit with meta
                                try:
                                    await self._audit_decision(
                                        signal, None, None, None, "duplicate_entry_prevented",
                                        meta={
                                            "reason": cooldown_type,
                                            "remaining_sec": float(cooldown_left),
                                            "cooldown_sec": float(effective_cooldown),
                                            "base": 90, "tp": 60, "sl": 180, "unknown": 90, "active_dup": 60
                                        }
                                    )
                                except Exception:
                                    pass
                                return True
                            else:
                                logger.info(f"🎯 Cooldown bypassed: meaningful_change detected ({time_diff:.0f}s < {effective_cooldown:.0f}s)")
                                # Allow re-entry despite cooldown
            
            return False
            
        except Exception as e:
            logger.error(f"Duplicate entry check failed: {e}")
            return False  # Allow entry if check fails
    
    async def _run_market_analysis(self):
        """PHASE 1A: Professional tick-by-tick trading sequence with real data only"""
        config = self.mode_configs[self.current_mode]
        
        try:
            # (A) Get fresh data (WebSocket + REST fallback) - NO MOCKS
            logger.debug("📊 Getting fresh market data...")
            tick = await get_live_bitcoin_price()  # Latest tick price
            market_data = await get_live_market_data()  # Current market state (SSOT snapshot)
            try:
                # Export snapshot age if embedded
                snap = market_data.get("snapshot")
                if snap and hasattr(snap, "asof"):
                    from time import time as _now
                    from app.backend.services.metrics import set_snapshot_age_seconds
                    set_snapshot_age_seconds(max(0.0, _now() - float(getattr(snap, "asof", 0.0))))
            except Exception:
                pass
            service = await get_live_market_data_service()
            candles = service.get_recent_candles("1m", 800)  # Stream-first, backed by DynamoDB Local
            
            logger.debug(f"🎯 Tick: BTCUSDT @${tick:.2f}, Candles: {len(candles)} loaded")

            # Readiness gate (server-side): based on snapshot and history ages
            try:
                from time import time as _now
                from app.backend.services.metrics import set_readiness_gate
                snapshot_asof = float(getattr(market_data.get("snapshot", None), "asof", 0.0)) if isinstance(market_data, dict) else 0.0
                snap_age_ok = (_now() - snapshot_asof) < 5.0 if snapshot_asof > 0 else False
                history_close_ts = 0.0
                if candles:
                    last = candles[-1]
                    if isinstance(last, dict):
                        history_close_ts = float(last.get("close_time", last.get("timestamp", 0)))
                        if history_close_ts > 1e12:
                            history_close_ts /= 1000.0
                    elif isinstance(last, list) and len(last) >= 7:
                        # Binance format index 6 is close time (ms)
                        history_close_ts = float(last[6]) / 1000.0
                hist_age_ok = (_now() - history_close_ts) < 60.0 if history_close_ts > 0 else False
                set_readiness_gate("entry", bool(snap_age_ok and hist_age_ok))
                if not (snap_age_ok and hist_age_ok):
                    try:
                        from time import time as _t
                        from app.backend.services.metrics import inc_analysis_only_failure, set_last_decision_epoch
                        inc_analysis_only_failure("not_ready")
                        set_last_decision_epoch(_t())
                    except Exception:
                        pass
            except Exception:
                pass

            # Circuit breaker (volume z-score with hysteresis)
            try:
                import numpy as _np
                vols = []
                # extract volumes from last 60 closed candles (dict or list)
                for c in candles[-60:]:
                    if isinstance(c, dict):
                        vols.append(float(c.get("volume", 0.0)))
                    elif isinstance(c, list) and len(c) >= 6:
                        vols.append(float(c[5]))
                if len(vols) >= 10:
                    v_last = float(vols[-1])
                    mu = float(_np.mean(vols))
                    sigma = float(_np.std(vols))
                    z = 0.0 if sigma == 0.0 else (v_last - mu) / sigma
                    try:
                        from app.backend.services.metrics import set_volume_zscore
                        set_volume_zscore("BTCUSDT", float(z))
                    except Exception:
                        pass
                    
                    # 🔧 FIX (Oct 2025): Adaptive volume gate scaling
                    # When zVol < 1.0 and ATR/close < 0.10%, scale thresholds to 2.2/1.2
                    vol_ratio = market_data.get("volume_ratio", 1.0)
                    volatility = market_data.get("volatility", 0.05)
                    atr_pct = volatility  # ATR/close approximation
                    
                    # 🔧 FIX (Oct 2025): Adaptive volume gate with capitulation detection
                    # In oversold context (BB_pos ≤ 0.05 & RSI ≤ 36), use composite volume metric
                    # This catches capitulation spikes that would otherwise be blocked
                    rsi = market_data.get("rsi", 50.0)
                    bb_pos = market_data.get("bb_position", 0.5)
                    
                    is_oversold = (bb_pos <= 0.05 and rsi <= 36)
                    is_low_vol_regime = (vol_ratio < 1.0 and atr_pct < 0.001)
                    
                    if is_oversold:
                        # 🔧 FIX (Oct 2025): Easier capitulation volume gate
                        # Lower bars: zVol/2.0 and vol_ratio/5.0 (was /3.5 and /7.0)
                        # This catches more oversold bounces in micro-tape conditions
                        vol_composite = max(z / 2.0, vol_ratio / 5.0)
                        threshold_on = 3.5  # Keep standard for z-score
                        threshold_off = 2.0
                        
                        if vol_composite >= 1.0:
                            logger.info(f"📊 VOLUME GATE: CAPITULATION (composite={vol_composite:.2f}) | zVol={z:.2f}, vol_ratio={vol_ratio:.2f}, RSI={rsi:.1f}, BB={bb_pos:.3f}")
                        else:
                            logger.debug(f"📊 VOLUME GATE: OVERSOLD (composite={vol_composite:.2f} < 1.0) | zVol={z:.2f}, vol_ratio={vol_ratio:.2f}")
                    elif is_low_vol_regime:
                        threshold_on = 2.2
                        threshold_off = 1.2
                        logger.info(f"📊 VOLUME GATE: LOW-VOL REGIME (on={threshold_on}, off={threshold_off}) | vol_ratio={vol_ratio:.2f}, atr={atr_pct:.4f}")
                    else:
                        threshold_on = self.cb_threshold_on
                        threshold_off = self.cb_threshold_off
                        logger.debug(f"📊 VOLUME GATE: NORMAL (on={threshold_on}, off={threshold_off}) | vol_ratio={vol_ratio:.2f}, atr={atr_pct:.4f}")
                    
                    # 🔧 FIX (Oct 2025): EMA smoothing to prevent single-spike halts
                    # Update EMA z-score (exponential moving average)
                    if self.z_ema is None:
                        self.z_ema = z  # Initialize with first value
                    else:
                        self.z_ema = self.z_ema_alpha * z + (1 - self.z_ema_alpha) * self.z_ema
                    
                    # Use EMA z-score for breaker decisions (smoother)
                    z_smoothed = self.z_ema
                    
                    # 🔧 FIX (Oct 2025): FSM-based breaker with both raw + EMA checks
                    # ON: raw_z >= on AND ema_z >= on*0.7 (prevents false activation from single spike)
                    # OFF: raw_z <= off AND ema_z <= off for N consecutive ticks
                    ema_on_threshold = threshold_on * 0.7  # 70% of ON threshold for EMA
                    
                    prev = self.cb_active
                    
                    # Calculate ticks needed for recovery (fix off-by-one)
                    ticks_needed = max(0, self.cb_safe_required - self.cb_safe_ticks)
                    
                    # FSM State Machine
                    if not prev:
                        # State: OFF → check for activation
                        # Require BOTH raw and EMA to exceed thresholds
                        if z >= threshold_on and z_smoothed >= ema_on_threshold:
                            self.cb_active = True
                            self.cb_safe_ticks = 0
                            try:
                                logger.warning(f"🚨 CB state=ON raw_z={z:.2f} ema_z={z_smoothed:.2f} on={threshold_on:.2f} reason=raw>={threshold_on:.2f}&ema>={ema_on_threshold:.2f}")
                            except Exception:
                                pass
                        else:
                            # Still OFF, log info (every tick for visibility)
                            try:
                                logger.info(f"📉 CB state=OFF raw_z={z:.2f} ema_z={z_smoothed:.2f} on={threshold_on:.2f} off={threshold_off:.2f}")
                            except Exception:
                                pass
                    else:
                        # State: ON → check for recovery
                        # Require BOTH raw and EMA below OFF threshold
                        if z <= threshold_off and z_smoothed <= threshold_off:
                            self.cb_safe_ticks += 1
                            if self.cb_safe_ticks >= self.cb_safe_required:
                                # Recovery complete
                                self.cb_active = False
                                self.cb_safe_ticks = 0
                                try:
                                    logger.info(f"✅ CB recover raw_z={z:.2f} ema_z={z_smoothed:.2f} safe={self.cb_safe_required}/{self.cb_safe_required}")
                                except Exception:
                                    pass
                            else:
                                # Still accumulating safe ticks
                                try:
                                    logger.info(f"📉 CB state=ON raw_z={z:.2f} ema_z={z_smoothed:.2f} safe={self.cb_safe_ticks}/{self.cb_safe_required} need={ticks_needed}")
                                except Exception:
                                    pass
                        else:
                            # Condition broken, reset safe counter
                            if self.cb_safe_ticks > 0:
                                try:
                                    logger.debug(f"⚠️ CB safe reset: raw_z={z:.2f} ema_z={z_smoothed:.2f} (was {self.cb_safe_ticks}/{self.cb_safe_required})")
                                except Exception:
                                    pass
                            self.cb_safe_ticks = 0
                    # export status
                    try:
                        from app.backend.services.metrics import set_cb_active, inc_cb_halt
                        set_cb_active("BTCUSDT", self.cb_active)
                        if self.cb_active and not prev:
                            inc_cb_halt("volume_zscore")
                    except Exception:
                        pass
                # Short-circuit if CB active
                if self.cb_active:
                    try:
                        logger.warning("🚨 Trading halted: Circuit breaker volume active (z-score)")
                    except Exception:
                        pass
                    await self._audit_decision(None, None, None, None, "circuit_breaker_halt")
                    try:
                        from time import time as _t
                        from app.backend.services.metrics import inc_analysis_only_failure, set_last_decision_epoch
                        inc_analysis_only_failure("cb_active")
                        set_last_decision_epoch(_t())
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            
            # (B) SMART EMERGENCY: Separate data-plane vs control-plane
            try:
                from app.backend.services.smart_emergency_controller import get_smart_emergency_controller
                smart_emergency = get_smart_emergency_controller()
                emergency_state = smart_emergency.evaluate()
                
                if emergency_state == "halt":
                    logger.critical("🚨 EMERGENCY HALT: Both data and control planes failed")
                    # Full stop - close all positions
                    portfolio = await get_professional_portfolio("admin")
                    active_positions = portfolio.get_active_positions()
                    for position in active_positions:
                        await portfolio.close_position(position.position_id, "emergency_halt")
                    return
                elif emergency_state == "pause":
                    logger.warning(f"⏸️ EMERGENCY PAUSE: New entries blocked (API fail rate: {smart_emergency.api.fail_rate:.2f})")
                    # Only manage existing positions - no new entries
                    await self._monitor_open_positions()
                    return
                else:
                    # NORMAL - proceed with full trading
                    logger.debug(f"✅ Emergency status: {emergency_state}")
                    
            except Exception as e:
                logger.error(f"Smart emergency check failed: {e}")
                # Fallback to legacy emergency system
                if self.emergency_system and await self.emergency_system.is_trading_halted():
                    logger.warning("🚨 EMERGENCY: Trading halted by legacy emergency controls")
                    return
            
            # (C) Enterprise signal (6-layer analysis) with REAL DATA
            signal = await self.enterprise_engine.generate_signal("BTCUSDT", market_snapshot=market_data.get("snapshot", market_data))
            
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
            
            # 🔧 FIX (Oct 2025): Check knife-catch cooldown before entry
            # Prevents "fade the knife" loops after rapid stop-outs
            if self.risk_manager and self.risk_manager.is_knife_catch_cooldown_active("BTCUSDT"):
                logger.warning(f"🚫 Entry blocked: BTCUSDT in knife-catch cooldown (rapid stop-out protection)")
                await self._audit_decision(signal, None, None, None, "knife_catch_cooldown")
                return
            
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
                        # Enhanced risk blocking log with position details
                        active_positions = portfolio.get_active_positions() if hasattr(portfolio, 'get_active_positions') else []
                        signal_type = getattr(signal, 'action', 'UNKNOWN')
                        confidence = getattr(signal, 'confidence', 0.0)
                        mode = getattr(signal, 'mode', 'unknown')
                        
                        logger.info(f"🛡️ Risk blocked: {risk_assessment.block_reason} | "
                                  f"open={len(active_positions)}/{config.max_positions} | "
                                  f"signal={signal_type} | conf={confidence:.1%} | mode={mode}")
                        await self._audit_decision(signal, None, None, risk_assessment, "risk_blocked")
                        return
                        
                    risk_score = getattr(risk_assessment, 'risk_score', None)
                    risk_score_str = safe_format_number(risk_score) if risk_score is not None else "N/A"
                    logger.debug(f"🛡️ Risk assessment: score={risk_score_str}")
                except Exception as e:
                    logger.warning(f"⚠️ Risk manager failed, proceeding without: {e}")
            
            # (E) Entry/Exit decisions (parallel execution)
            # Monitor positions first with exit engine
            await self._monitor_open_positions()
            
            # Session-aware confidence adjustment
            session_multiplier = self._get_session_confidence_multiplier()
            adjusted_confidence = signal.confidence * session_multiplier
            
            logger.info(f"🎯 Signal: {signal.action} conf={signal.confidence:.2f} → {adjusted_confidence:.2f} (session={self.current_session.value})")
            try:
                from app.backend.services.metrics import observe_entry_confidence
                observe_entry_confidence(float(adjusted_confidence))
            except Exception:
                pass
            
            # Unified thresholds
            from app.backend.config.trading_thresholds import ConfidenceThresholds
            thresholds = ConfidenceThresholds()
            effective_threshold = thresholds.BUY_THRESHOLD if getattr(signal, 'signal_type', 'primary') == 'primary' else thresholds.EXPLORATORY_BUY
            # Entry playbooks: mean‑reversion and breakout
            playbook = None
            try:
                md = market_data if isinstance(market_data, dict) else {}
                rsi = float(md.get("rsi", 50.0))
                bb_pos = float(md.get("bollinger_position", 0.5))
                macd = float(md.get("macd", 0.0))
                vol_ratio = float(md.get("volume_ratio", 1.0))
                # Mean‑reversion buy: deep oversold and bottom band proximity
                if signal.action == "BUY" and rsi <= 30.0 and bb_pos <= 0.15:
                    playbook = "mean_reversion"
                # Breakout continuation: strong momentum and band top proximity with volume
                elif signal.action == "BUY" and bb_pos >= 0.85 and macd > 0.0 and vol_ratio >= 1.2:
                    playbook = "breakout"
                # Mirror for SELL (optional): oversold/overbought logic inverted
                elif signal.action == "SELL" and rsi >= 70.0 and bb_pos >= 0.85:
                    playbook = "mean_reversion_sell"
                elif signal.action == "SELL" and bb_pos <= 0.15 and macd < 0.0 and vol_ratio >= 1.2:
                    playbook = "breakout_sell"
                # Apply small threshold boost when playbook recognized
                if playbook is not None:
                    effective_threshold = max(0.30, float(effective_threshold) - 0.02)
            except Exception:
                pass
            
            logger.info(f"🔍 THRESHOLD CHECK: {adjusted_confidence:.2f} > {effective_threshold:.2f} ? signal_type={getattr(signal, 'signal_type', 'primary')} playbook={playbook or 'none'}")
            try:
                from app.backend.services.metrics import set_decision_threshold
                set_decision_threshold("day_trading", getattr(signal, 'signal_type', 'primary'), self.current_session.value, float(effective_threshold))
            except Exception:
                pass
            try:
                from app.backend.services.metrics import set_effective_threshold
                set_effective_threshold(float(effective_threshold), getattr(signal, 'signal_type', 'primary'))
            except Exception:
                pass
            
            # Early cooldown gate: if entry engine cooldown active, avoid deep analysis
            try:
                last_t = self.entry_engine.entry_cooldown_cache.get(signal.symbol, 0)
                import time as _t
                if _t.time() - last_t < self.entry_engine.entry_cooldown_seconds:
                    remaining = self.entry_engine.entry_cooldown_seconds - (_t.time() - last_t)
                    logger.info(f"⌛ WAIT (cooldown {remaining:.1f}s) - skipping entry analysis")
                    try:
                        from app.backend.services.metrics import inc_cooldown_skip
                        inc_cooldown_skip()
                    except Exception:
                        pass
                    await self._audit_decision(signal, {"should_enter": False, "reasoning": "cooldown_active"}, None, risk_assessment, "cooldown_skip")
                    return
            except Exception:
                pass
            
            # Check threshold and action type
            if adjusted_confidence > effective_threshold and signal.action in ["BUY", "SELL"]:
                
                # Check position limits
                active_positions = len(portfolio.get_active_positions())
                if active_positions >= config.max_positions:
                    logger.debug(f"⚠️ Max positions reached: {active_positions}/{config.max_positions}")
                    await self._audit_decision(signal, None, None, risk_assessment, "max_positions")
                    return
                
                # CRITICAL: Check for duplicate positions (prevent same-minute entries)
                if await self._is_duplicate_entry(signal, portfolio):
                    # 🔧 FIX (Oct 2025): Log already emitted in _is_duplicate_entry, skip duplicate
                    try:
                        from app.backend.services.metrics import inc_decision_dupe
                        inc_decision_dupe("similar_signal")
                    except Exception:
                        pass
                    # Track suppression for burst escape logic
                    try:
                        import time as _t
                        self._dupe_suppress_ts.append(_t.time())
                        # Keep last 20 timestamps
                        if len(self._dupe_suppress_ts) > 20:
                            self._dupe_suppress_ts = self._dupe_suppress_ts[-20:]
                    except Exception:
                        pass
                    await self._audit_decision(signal, None, None, risk_assessment, "duplicate_entry_prevented")
                    return
                
                # ENTRY ANALYSIS using intelligent_entry_engine (SSOT snapshot)
                entry_decision = await self._run_professional_entry_analysis(
                    signal, portfolio, candles, tick, risk_assessment, market_data
                )
                # Attach playbook context for audit/metrics
                try:
                    if isinstance(entry_decision, dict):
                        entry_decision = dict(entry_decision)
                        entry_decision["playbook"] = playbook or "none"
                except Exception:
                    pass
                
                logger.info(
                    f"🚦 ENTRY: {('ENTER' if entry_decision.get('should_enter') else 'WAIT')} "
                    f"conf={entry_decision.get('confidence',0):.2f} reason={entry_decision.get('reasoning','')}"
                )
                
                # (F) Position orchestration
                if entry_decision.get("should_enter", False):
                    # Execution guards (volatility/slippage proxy)
                    try:
                        import numpy as _np
                        closes_guard = []
                        for c in candles[-10:]:
                            if isinstance(c, dict):
                                closes_guard.append(float(c.get("close", 0.0)))
                            elif isinstance(c, list) and len(c) >= 5:
                                closes_guard.append(float(c[4]))
                        vol_proxy = float(_np.std(_np.array(closes_guard))) if len(closes_guard) >= 5 else 0.0
                        vol_ratio = vol_proxy / max(1e-9, float(tick if isinstance(tick, (int, float)) else tick.get("price", 0.0)))
                        if vol_ratio > 0.004 and adjusted_confidence < (effective_threshold + 0.05):
                            logger.info(f"🛑 Execution guard: high short-term volatility ({vol_ratio:.4f}) - skipping entry")
                            await self._audit_decision(signal, {"should_enter": False, "reasoning": "execution_guard_volatility"}, None, risk_assessment, "execution_guard")
                            try:
                                from app.backend.services.metrics import inc_entry_guard_block
                                inc_entry_guard_block("volatility")
                            except Exception:
                                pass
                            return
                        # Spread/slippage guards using live orderbook/ticker when available
                        try:
                            from app.backend.services.live_market_data import get_live_orderbook_data
                            ob = await get_live_orderbook_data()
                            bids = ob.get("bids") or []
                            asks = ob.get("asks") or []
                            best_bid = float(bids[0][0]) if bids else 0.0
                            best_ask = float(asks[0][0]) if asks else 0.0
                            mid = (best_bid + best_ask) / 2.0 if best_bid and best_ask else 0.0
                            spread_bps = ((best_ask - best_bid) / mid * 10000.0) if mid else 0.0
                        except Exception:
                            spread_bps = 0.0
                        # Slippage proxy: use vol_ratio in bps terms as a conservative proxy
                        slippage_bps = float(vol_ratio * 10000.0)
                        try:
                            from app.backend.core.runtime_config import runtime_config_store
                            cfg = await runtime_config_store.get()
                            if spread_bps > float(cfg.playbook_override_max_spread_bps):
                                logger.info(f"🛑 Execution guard: spread {spread_bps:.2f}bps > {cfg.playbook_override_max_spread_bps}bps")
                                await self._audit_decision(signal, {"should_enter": False, "reasoning": "execution_guard_spread"}, None, risk_assessment, "execution_guard")
                                try:
                                    from app.backend.services.metrics import inc_entry_guard_block
                                    inc_entry_guard_block("spread")
                                except Exception:
                                    pass
                                return
                            if slippage_bps > float(cfg.playbook_override_max_slippage_bps):
                                logger.info(f"🛑 Execution guard: slippage {slippage_bps:.2f}bps > {cfg.playbook_override_max_slippage_bps}bps (proxy)")
                                await self._audit_decision(signal, {"should_enter": False, "reasoning": "execution_guard_slippage"}, None, risk_assessment, "execution_guard")
                                try:
                                    from app.backend.services.metrics import inc_entry_guard_block
                                    inc_entry_guard_block("slippage")
                                except Exception:
                                    pass
                                return
                        except Exception:
                            pass
                    except Exception:
                        pass
                    # Burst escape hatch: if >=3 suppressions within 120s, allow micro-size bypass
                    micro_bypass = False
                    try:
                        import time as _t
                        now = _t.time()
                        recent = [t for t in self._dupe_suppress_ts if now - t <= 120]
                        if len(recent) >= 3:
                            micro_bypass = True
                    except Exception:
                        pass
                    # Calculate position size with risk manager
                    if self.risk_manager and risk_assessment:
                        try:
                            position_size = await self.risk_manager.calculate_position_size(
                                signal, risk_assessment, portfolio, tick
                            )
                        except Exception as e:
                            logger.error(f"Risk manager size calculation failed: {e}")
                            raise RuntimeError(f"Position sizing failed: {e}")
                    else:
                        # Use mode config for position sizing
                        position_size = float(portfolio.cash_balance) * config.position_size_pct
                    if micro_bypass:
                        # Use 25% of normal size for micro-bypass
                        position_size *= 0.25
                        try:
                            from app.backend.services.metrics import inc_dupe_micro_bypass
                            inc_dupe_micro_bypass()
                        except Exception:
                            pass
                    # Apply playbook override size hair-cut if provided by entry engine
                    try:
                        size_mult = float(entry_decision.get("size_multiplier", 1.0))
                        if size_mult > 0 and size_mult < 1.0:
                            position_size *= size_mult
                    except Exception:
                        pass

                    # ATR-proxy stops and TP ladder
                    sl_pct = 0.003  # 0.30% floor
                    try:
                        import numpy as _np
                        closes_atr = []
                        for c in candles[-14:]:
                            if isinstance(c, dict):
                                closes_atr.append(float(c.get("close", 0.0)))
                            elif isinstance(c, list) and len(c) >= 5:
                                closes_atr.append(float(c[4]))
                        if len(closes_atr) >= 10:
                            atr_proxy = float(_np.std(_np.array(closes_atr)))
                            price_now = float(tick if isinstance(tick, (int, float)) else tick.get("price", 0.0))
                            sl_pct = max(sl_pct, 0.35 * (atr_proxy / max(price_now, 1e-9)))
                    except Exception:
                        pass
                    tp_ladder = [round(sl_pct * 1.4, 6), round(sl_pct * 2.0, 6), round(sl_pct * 2.8, 6)]
                    
                    # Open position with semantic consistency
                    from decimal import Decimal
                    
                    position_type = PositionType.LONG if signal.action == "BUY" else PositionType.SHORT
                    position_direction = "LONG" if position_type == PositionType.LONG else "SHORT"
                    
                    # Create semantically consistent AI reasoning
                    consistent_reasoning = f"{self.current_mode.value}: {position_direction} position based on {signal.action} signal - {signal.reasoning}"
                    
                    
                    # CRITICAL: Validate signal-position mapping
                    validate_signal_position_mapping(signal.action, position_type)
                    # Validate semantic consistency
                    assert (signal.action == "BUY" and position_type == PositionType.LONG) or \
                           (signal.action == "SELL" and position_type == PositionType.SHORT), \
                           f"Semantic inconsistency: {signal.action} signal with {position_type} position"
                    
                    logger.info(f"🚀 Opening position: {signal.symbol} {position_direction} size={position_size}")
                    
                    # CRITICAL: Normalize AI confidence to [0,1] range
                    normalized_confidence = min(max(adjusted_confidence, 0.0), 1.0)
                    
                    # Real trading path (optional, runtime-config)
                    try:
                        from app.backend.core.runtime_config import runtime_config_store
                        cfg = await runtime_config_store.get()
                        if getattr(cfg, "real_trading_enabled", False):
                            from app.backend.services.binance_hybrid_client import get_hybrid_client
                            hc = await get_hybrid_client()
                            # Build idempotent client order id
                            import uuid
                            coid = f"tp-{uuid.uuid4().hex[:16]}"
                            side = "BUY" if position_type == PositionType.LONG else "SELL"
                            # Use quoteOrderQty to spend position_size dollars
                            quote_qty_str = f"{position_size:.2f}"
                            order = await hc.place_order(
                                symbol=signal.symbol,
                                side=side,
                                order_type="MARKET",
                                quote_order_qty=quote_qty_str,
                                new_client_order_id=coid,
                            )
                            try:
                                await write_orders({
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "symbol": signal.symbol,
                                    "action": side,
                                    "size": position_size,
                                    "price": float(order.get("fills", [{}])[0].get("price", tick if isinstance(tick, (int,float)) else tick.get("price", 0))),
                                    "order_id": order.get("orderId", coid),
                                    "slippage": 0.0,
                                })
                            except Exception:
                                pass
                    except Exception as e:
                        logger.warning(f"Real trading path failed or disabled: {e}")
                    
                    position_id = await portfolio.open_position(
                        symbol=signal.symbol,
                        position_type=position_type,
                        size=Decimal(str(position_size)),
                        ai_confidence=normalized_confidence,
                        ai_reasoning=consistent_reasoning,
                        stop_loss_pct=Decimal(str(sl_pct)),
                        take_profit_pct=Decimal(str(tp_ladder[1]))
                    )
                    
                    self.positions_opened += 1
                    
                    # CRITICAL FIX: Save portfolio state after opening position
                    await portfolio._save_portfolio_state()
                    logger.info(f"✅ POSITION OPENED: {position_id} ({signal.action}) conf={adjusted_confidence:.1%}")
                    try:
                        from time import time as _t
                        from app.backend.services.metrics import inc_decision, set_last_decision_epoch, inc_positions_opened, set_concurrent_positions, inc_decision_by_playbook
                        inc_decision("opened", signal.action, getattr(signal, 'signal_type', 'primary'))
                        inc_decision_by_playbook("opened", signal.action, getattr(signal, 'signal_type', 'primary'), playbook or "none")
                        set_last_decision_epoch(_t())
                        inc_positions_opened()
                        set_concurrent_positions(len(portfolio.get_active_positions()))
                    except Exception:
                        pass
                    
                    # PHASE 4.3: Track trade execution for performance learning
                    if self.performance_tracker:
                        position_data = {
                            "symbol": signal.symbol,
                            "entry_price": tick if isinstance(tick, (int, float)) else tick.get("price", 0),
                            "position_size": position_size,
                            "position_id": position_id
                        }
                        trade_id = await self.performance_tracker.track_trade_execution(
                            position_data, entry_decision, signal
                        )
                    
                    # (G) In-position risk management
                    if self.risk_manager:
                        try:
                            tick_data = {"price": tick if isinstance(tick, (int, float)) else tick.get("price", 0), "timestamp": datetime.now(timezone.utc)}
                            await self.risk_manager.assess_in_position(portfolio, tick_data)
                        except Exception as e:
                            logger.warning(f"In-position risk assessment failed: {e}")
                    
                    # Attach ladder info to audit
                    ed_with_ladder = dict(entry_decision)
                    try:
                        ed_with_ladder["tp_ladder"] = tp_ladder
                        ed_with_ladder["stop_loss_pct"] = sl_pct
                    except Exception:
                        ed_with_ladder = entry_decision
                    await self._audit_decision(signal, ed_with_ladder, None, risk_assessment, "position_opened")
                else:
                    await self._audit_decision(signal, entry_decision, None, risk_assessment, "entry_rejected")
                    try:
                        from time import time as _t
                        from app.backend.services.metrics import inc_decision, set_last_decision_epoch, inc_decision_by_playbook
                        inc_decision("rejected", signal.action, getattr(signal, 'signal_type', 'primary'))
                        inc_decision_by_playbook("rejected", signal.action, getattr(signal, 'signal_type', 'primary'), playbook or "none")
                        set_last_decision_epoch(_t())
                    except Exception:
                        pass
            else:
                reason = "low_confidence" if adjusted_confidence <= config.confidence_threshold else "hold_signal"
                # Ensure HOLD decisions use no_action audit reason instead of risk_blocked
                audit_reason = "no_action" if reason == "hold_signal" else reason
                logger.debug(f"📊 Signal rejected: {reason}")
                await self._audit_decision(signal, None, None, risk_assessment, audit_reason)
                try:
                    from time import time as _t
                    from app.backend.services.metrics import inc_decision, set_last_decision_epoch, inc_decision_by_playbook
                    inc_decision("rejected", signal.action, getattr(signal, 'signal_type', 'primary'))
                    inc_decision_by_playbook("rejected", signal.action, getattr(signal, 'signal_type', 'primary'), playbook or "none")
                    set_last_decision_epoch(_t())
                except Exception:
                    pass
                
        except Exception as e:
            logger.error(f"❌ Professional trading analysis failed: {e}")
            # Emergency handling - ensure system stability
            if self.emergency_system:
                try:
                    await self.emergency_system.handle_analysis_failure(str(e))
                except Exception as e2:
                    logger.error(f"Emergency system also failed: {e2}")
    
    async def _run_professional_entry_analysis(self, signal: Any, portfolio: Any, candles: List, tick: float, risk_assessment: Any, market_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """PHASE 1A: Professional entry analysis with risk integration"""
        try:
            # Use provided SSOT market snapshot
            market_data = market_snapshot
            
            # Run intelligent entry analysis
            entry_result = await self.entry_engine.analyze_entry_opportunity(
                symbol=signal.symbol,
                signal_data={
                    "action": signal.action,
                    "confidence": signal.confidence,
                    "reasoning": signal.reasoning,
                    "signal_type": getattr(signal, 'signal_type', 'primary'),  # Pass signal type
                    "layer_analysis": getattr(signal, 'layer_analysis', {})  # Pass layer analysis for L6_timing
                },
                user_portfolio={
                    "available_cash": float(portfolio.cash_balance),
                    "active_positions": portfolio.get_active_positions(),
                    "max_positions": self.mode_configs[self.current_mode].max_positions,
                    "daily_trades": portfolio.daily_trades,
                    "max_daily_trades": portfolio.max_daily_trades
                },
                market_data_override=market_data
            )
            
            # Safe formatting for optimal price
            try:
                optimal_price = entry_result.optimal_entry_price
                if optimal_price is None or optimal_price <= 0:
                    logger.debug(f"🔄 PIPELINE DEBUG: Day Trading Engine - Invalid entry price during warmup: {optimal_price}")
                    optimal_price = 0.0
                    optimal_price_str = "N/A (warmup)"
                else:
                    optimal_price = float(optimal_price)
                    optimal_price_str = safe_format_price(optimal_price)
            except (ValueError, TypeError) as price_error:
                logger.debug(f"🔄 PIPELINE DEBUG: Day Trading Engine - Entry price validation failed: {price_error}")
                optimal_price = 0.0
                optimal_price_str = "N/A (invalid)"
            
            return {
                "should_enter": entry_result.should_enter,
                "confidence": entry_result.confidence,
                "entry_quality": entry_result.entry_quality.value,
                "optimal_price": optimal_price,
                "optimal_price_formatted": optimal_price_str,
                "reasoning": f"Day trading analysis: {entry_result.entry_reason.value}"
            }
            
        except Exception as e:
            logger.error(f"Day trading entry analysis failed: {e}")
            return {
                "should_enter": False, 
                "confidence": 0.0,
                "reasoning": f"Analysis failed: {str(e)}"
            }
    
    def _get_session_confidence_multiplier(self) -> float:
        """
        Get confidence multiplier based on current trading session
        
        ✅ ADAPTIVE: Uses DayTradingConfig for Bitcoin-optimized session detection
        Bitcoin trades 24/7, so effects are subtle (0.95-1.12x)
        """
        day_config = get_day_trading_config()
        current_hour = datetime.now(timezone.utc).hour
        
        # Get adaptive multiplier from config
        return day_config.get_session_multiplier(current_hour)
        
    async def _audit_decision(self, signal, entry_decision, exit_decision, risk_assessment, outcome: str):
        """PHASE 1A: Complete decision audit trail for professional operation"""
        try:
            # Ensure HOLD decisions don't show risk_blocked when they're just no-action
            final_outcome = outcome
            if outcome == "no_action" and signal and signal.action == "HOLD":
                final_outcome = "no_action"
            elif outcome == "hold_signal":
                final_outcome = "no_action"
            
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
                "outcome": final_outcome,
                "trading_mode": self.current_mode.value,
                "session": self.current_session.value
            }
            
            # Enhance entry_decision with audit reason for better tracking
            if entry_decision is None and final_outcome == "no_action":
                entry_decision = {"should_enter": False, "reasoning": "no_action"}
            
            # Use market data persistence for audit logging
            audit_success = await write_decisions(entry_decision, exit_decision, risk_assessment, signal)
            if audit_success:
                logger.debug(f"📝 Decision audited: {final_outcome}")
            else:
                logger.warning(f"⚠️ Decision audit failed, but continuing: {final_outcome}")
            
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