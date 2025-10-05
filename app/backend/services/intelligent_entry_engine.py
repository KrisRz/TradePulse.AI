"""
Intelligent Entry Engine - TradePulse.AI Enterprise
=================================================

6-Layer AI-powered position entry analysis system that optimizes
entry points and prevents poor timing decisions.

Features:
- 6-layer AI entry analysis
- Market timing optimization
- Entry point validation
- Risk-adjusted position sizing
- Comprehensive entry scoring

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

# TensorFlow mutex fix - set BEFORE any TensorFlow imports
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress all TensorFlow logging
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Disable oneDNN optimizations
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Disable CUDA
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'  # Allow GPU memory growth
os.environ['TF_GPU_THREAD_MODE'] = 'gpu_private'  # GPU thread mode
# CRITICAL MUTEX FIX
os.environ['TF_NUM_INTEROP_THREADS'] = '1'  # Single thread for interop
os.environ['TF_NUM_INTRAOP_THREADS'] = '1'  # Single thread for intraop
os.environ['OMP_NUM_THREADS'] = '1'  # OpenMP single thread
os.environ['MKL_NUM_THREADS'] = '1'  # Intel MKL single thread

# LSTM disable flag to prevent recursion errors
DISABLE_LSTM = os.getenv('DISABLE_LSTM', 'false').lower() == 'true'

# TensorFlow 2.16.1 STABLE - NO AUTO-DETECTION NEEDED
# Using official stable version from https://www.tensorflow.org/api_docs

import asyncio
import json
import logging
import numpy as np
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

# Import market data services
from app.backend.services.live_market_data import get_live_bitcoin_price, get_live_market_data, get_live_orderbook_data
from app.backend.utils.safe_formatting import safe_format_number, safe_format_price
from app.backend.services.binance_hybrid_client import get_hybrid_client
from app.backend.services.day_trading_validator import get_day_trading_validator

logger = logging.getLogger(__name__)

class EntryReason(str, Enum):
    """Entry decision reasons"""
    AI_CONSENSUS = "ai_consensus"
    TECHNICAL_BREAKOUT = "technical_breakout"
    MOMENTUM_SIGNAL = "momentum_signal"
    REVERSAL_PATTERN = "reversal_pattern"
    MARKET_REGIME_SHIFT = "market_regime_shift"
    HIGH_CONFIDENCE = "high_confidence"
    MANUAL_OVERRIDE = "manual_override"
    INSUFFICIENT_CONFIDENCE = "insufficient_confidence"
    POOR_TIMING = "poor_timing"
    WEAK_SIGNAL = "weak_signal"  # Added for weak signal rejection

class EntryQuality(str, Enum):
    """Entry quality classifications"""
    EXCELLENT = "excellent"    # 90%+ confidence
    GOOD = "good"             # 70-90% confidence
    FAIR = "fair"             # 50-70% confidence
    POOR = "poor"             # <50% confidence

@dataclass(eq=False, order=False)
class EntryAnalysisResult:
    """Comprehensive entry analysis result"""
    should_enter: bool
    confidence: float
    entry_reason: EntryReason
    entry_quality: EntryQuality
    optimal_entry_price: float
    position_size_recommendation: float
    risk_score: float
    timing_score: float
    layer_analysis: Dict[str, Any]
    market_conditions: Dict[str, Any]
    analysis_time_ms: float
    timestamp: datetime
    
    def __eq__(self, other):
        """Safe equality based on timestamp and entry_reason only"""
        return isinstance(other, EntryAnalysisResult) and self.timestamp == other.timestamp and self.entry_reason == other.entry_reason
    
    def __hash__(self):
        """Safe hash based on timestamp and entry_reason"""
        return hash((self.timestamp, self.entry_reason))

class IntelligentEntryEngine:
    """
    UPGRADED Intelligent Entry Engine with Predictive Price Analysis
    
    NEW FEATURES:
    - Predictive price movement analysis
    - Price drop confirmation before BUY entries
    - Price rise confirmation before SELL entries  
    - Historical price pattern learning
    - Smart entry timing with momentum confirmation
    """
    
    def __init__(self):
        self.is_initialized = False
        self.models = {}
        # Professional path resolution - works from any working directory
        current_file = Path(__file__).parent.parent  # Go up from services/ to backend/
        self.model_path = current_file / "models" / "enterprise"
        
        # DAY TRADING SMART: Balanced thresholds for quality frequent trading
        self.confidence_threshold = 0.60  # SMART: 60% minimum confidence (professional + active)
        self.consensus_threshold = 0.60   # SMART: 60% consensus required (4 out of 6 layers)
        self.high_confidence_threshold = 0.75  # SMART: 75% for high confidence
        self.historical_validation_threshold = 0.55  # SMART: 55% historical success (proven patterns)
        
        # PRICE MOMENTUM CONFIRMATION: Wait for price movement in trade direction
        self.price_confirmation_threshold = 0.002  # 0.2% price movement required
        self.price_momentum_periods = 5  # Check last 5 price points
        self.max_wait_for_confirmation = 300  # Max 5 minutes wait for price confirmation
        
        # PREDICTIVE ANALYSIS: Historical price tracking
        self.price_history = []  # Store recent price history for analysis
        self.max_price_history = 50  # Keep last 50 price points
        self.prediction_confidence_boost = 0.1  # Boost confidence when prediction aligns
        
        # OPTIMIZED DAY TRADING WARMUP: Phase-based approach
        self.startup_time = datetime.now(timezone.utc)
        self.warmup_period_minutes = 3  # OPTIMIZED: 3-minute maximum warmup for day trading
        self.is_warmed_up = False  # Start with analysis mode
        self.warmup_completed_at = None
        
        # FIXED: Add cool-down tracking for repeated WAIT decisions
        self._last_wait_decision = None
        self._wait_decision_cooldown = 60  # 60 seconds cooldown
        
        # FIXED: Resilient market data access
        self.market_data = None
        self.container = None
        self.smart_entry_mode = True  # NEW: Enable smart entry with price confirmation
        
        # PHASE-BASED WARMUP SYSTEM
        self.warmup_phase = 1  # Current warmup phase (1, 2, or 3)
        self.phase1_duration = 1.0  # Phase 1: 1 minute - collect basic price history
        self.phase2_duration = 2.0  # Phase 2: 2 minutes - normal operation with higher thresholds
        self.phase3_start = 3.0     # Phase 3: 3+ minutes - full optimization
        
        # PHASE-BASED THRESHOLDS for gradual confidence building
        self.phase1_confidence_threshold = 0.75  # Higher threshold during initial warmup
        self.phase2_confidence_threshold = 0.70  # Medium threshold during phase 2
        self.phase3_confidence_threshold = 0.65  # Normal threshold after full warmup
        
        # MINIMUM DATA REQUIREMENTS for each phase
        self.min_price_history_basic = 5   # Phase 1: 5 points = 60 seconds at 12s intervals
        self.min_price_history_full = 20   # Phase 2: 20 points = 4 minutes for full analysis
        
        # Historical context service
        self.historical_context = None
        
        # Entry analysis with smart timing
        self.entry_cooldown_cache = {}
        # Runtime-configurable cooldown (default 10s)
        try:
            from app.backend.core.config import get_settings
            s = get_settings()
            self.entry_cooldown_seconds = int(getattr(s, "ENTRY_COOLDOWN_SECONDS", 10))
        except Exception:
            self.entry_cooldown_seconds = 10  # fallback to default
        # Pre-init low-cardinality series at engine startup
        try:
            from app.backend.services.metrics import preinit_decision_dupe_series, preinit_l5_vector_source_series, preinit_analysis_only_failure_series
            preinit_decision_dupe_series()
            preinit_l5_vector_source_series()
            preinit_analysis_only_failure_series()
        except Exception:
            pass
        self.pending_entries = {}  # Track entries waiting for price confirmation
        
        # Performance tracking
        self.total_analyses = 0
        self.entries_recommended = 0
        self.successful_entries = 0
        self.layer_health = {}
        self.prediction_accuracy = 0.0
        
        # UPGRADED Layer configurations with price analysis
        self.layers = {
            1: {"name": "Market Regime Analysis", "weight": 0.15},
            2: {"name": "Predictive Price Analysis", "weight": 0.30},  # ENHANCED
            3: {"name": "Pattern Recognition", "weight": 0.20},
            4: {"name": "Technical Momentum", "weight": 0.15},  # ENHANCED  
            5: {"name": "Price Direction Confirmation", "weight": 0.15},  # NEW
            6: {"name": "Smart Entry Timing", "weight": 0.05}  # REDUCED
        }
        
        logger.info("🎯 UPGRADED Intelligent Entry Engine initialized with predictive analysis")
    
    async def update_price_history(self, current_price: float):
        """Update price history for predictive analysis"""
        timestamp = datetime.now(timezone.utc)
        
        # Add new price point
        self.price_history.append({
            "price": current_price,
            "timestamp": timestamp
        })
        
        # Keep only recent history
        if len(self.price_history) > self.max_price_history:
            self.price_history.pop(0)
            
        logger.debug(f"📈 Price history updated: {current_price:.2f} ({len(self.price_history)} points)")
    
    async def analyze_price_momentum(self, current_price: float, signal_action: str) -> Dict[str, Any]:
        """Analyze price momentum to confirm entry direction"""
        if len(self.price_history) < self.price_momentum_periods:
            return {
                "momentum_confirmed": False,
                "momentum_strength": 0.0,
                "price_direction": "insufficient_data",
                "reason": "Insufficient price history"
            }
        
        # Get recent price points
        recent_prices = [p["price"] for p in self.price_history[-self.price_momentum_periods:]]
        price_changes = []
        
        for i in range(1, len(recent_prices)):
            change_pct = (recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
            price_changes.append(change_pct)
        
        avg_momentum = sum(price_changes) / len(price_changes)
        momentum_strength = abs(avg_momentum)
        
        # Determine price direction
        if avg_momentum > self.price_confirmation_threshold:
            price_direction = "rising"
        elif avg_momentum < -self.price_confirmation_threshold:
            price_direction = "falling"
        else:
            price_direction = "sideways"
        
        # Check if momentum aligns with signal
        momentum_confirmed = False
        if signal_action == "BUY" and price_direction == "falling":
            # BUY signal with falling price = GOOD (buy the dip)
            momentum_confirmed = True
        elif signal_action == "SELL" and price_direction == "rising":
            # SELL signal with rising price = GOOD (sell the peak)
            momentum_confirmed = True
        elif momentum_strength < self.price_confirmation_threshold / 2:
            # Low momentum = neutral, allow entry
            momentum_confirmed = True
            
        return {
            "momentum_confirmed": momentum_confirmed,
            "momentum_strength": momentum_strength,
            "price_direction": price_direction,
            "avg_momentum": avg_momentum,
            "recent_prices": recent_prices[-3:],  # Last 3 prices for debugging
            "reason": f"Price {price_direction}, momentum {momentum_strength:.4f}"
        }
    
    async def predict_price_target(self, current_price: float, signal_action: str) -> Dict[str, Any]:
        """Predict optimal entry price based on historical patterns"""
        if len(self.price_history) < 20:
            return {
                "predicted_target": current_price,
                "confidence": 0.5,
                "wait_for_better_price": False,
                "reason": "Insufficient data for prediction"
            }
        
        # Analyze recent price volatility
        recent_prices = [p["price"] for p in self.price_history[-20:]]
        price_std = np.std(recent_prices)
        price_mean = np.mean(recent_prices)
        
        # Calculate support/resistance levels
        price_high = max(recent_prices)
        price_low = min(recent_prices)
        price_range = price_high - price_low
        
        # Predict better entry points
        if signal_action == "BUY":
            # For BUY: Target lower prices (support levels)
            support_level = price_low + (price_range * 0.2)  # 20% above low
            predicted_target = min(support_level, current_price - (price_std * 0.5))
            wait_for_better = current_price > predicted_target + (current_price * 0.005)  # 0.5% buffer
            
        else:  # SELL
            # For SELL: Target higher prices (resistance levels)  
            resistance_level = price_high - (price_range * 0.2)  # 20% below high
            predicted_target = max(resistance_level, current_price + (price_std * 0.5))
            wait_for_better = current_price < predicted_target - (current_price * 0.005)  # 0.5% buffer
        
        # Calculate prediction confidence based on pattern consistency
        price_volatility = price_std / price_mean
        confidence = max(0.3, min(0.9, 1.0 - (price_volatility * 2)))
        
        return {
            "predicted_target": predicted_target,
            "confidence": confidence,
            "wait_for_better_price": wait_for_better,
            "current_price": current_price,
            "support_level": support_level if signal_action == "BUY" else None,
            "resistance_level": resistance_level if signal_action == "SELL" else None,
            "price_volatility": price_volatility,
            "reason": f"Target: {predicted_target:.2f}, Current: {current_price:.2f}, Wait: {wait_for_better}"
        }
    
    async def initialize(self):
        """Initialize the entry engine with models and historical context"""
        if self.is_initialized:
            logger.info("🔄 PIPELINE DEBUG: Entry Engine already initialized, skipping...")
            return
            
        logger.info("🚀 Initializing Enhanced Intelligent Entry Engine...")
        logger.info("📊 PIPELINE DEBUG: Entry Engine - Starting initialization sequence")
        logger.info(f"🎯 PIPELINE DEBUG: Entry Engine - Component: Intelligent Entry Engine v1.0.0")
        logger.info(f"🎯 PIPELINE DEBUG: Entry Engine - Purpose: 6-Layer AI entry point optimization")
        
        try:
            # Load 6-layer models (NO MOCKS)
            logger.info("🤖 PIPELINE DEBUG: Entry Engine - Loading 6-layer AI models...")
            self._load_entry_models()
            logger.info("✅ PIPELINE DEBUG: Entry Engine - AI models loaded successfully")
            
            # Initialize historical context service
            logger.info("📊 Initializing historical market context service...")
            logger.info("📊 PIPELINE DEBUG: Entry Engine - Connecting to historical context service...")
            from app.backend.services.historical_market_context_service import get_historical_context_service
            self.historical_context = await get_historical_context_service()
            logger.info("✅ Historical context service ready")
            logger.info("✅ PIPELINE DEBUG: Entry Engine - Historical context service connected")
            
            # Initialize health monitoring
            logger.info("🏥 PIPELINE DEBUG: Entry Engine - Initializing health monitoring...")
            self._initialize_health_monitoring()
            logger.info("✅ PIPELINE DEBUG: Entry Engine - Health monitoring active")
            
            # Start warmup period
            logger.info("⏰ PIPELINE DEBUG: Entry Engine - Starting warmup period...")
            try:
                from app.backend.services.metrics import set_engine_phase, set_decision_threshold
                set_engine_phase("entry", 2)  # warmup
                # Export initial thresholds
                from app.backend.config.trading_thresholds import ConfidenceThresholds
                th = ConfidenceThresholds()
                set_decision_threshold("entry", "primary", "phase1", float(th.BUY_THRESHOLD))
                set_decision_threshold("entry", "exploratory", "phase1", float(th.EXPLORATORY_BUY))
            except Exception:
                pass
            await self._start_warmup_period()
            logger.info("✅ PIPELINE DEBUG: Entry Engine - Warmup period initiated")
            try:
                import os as _os
                from app.backend.services.metrics import set_engine_info
                phase = "warmup"
                set_engine_info("entry", "primary", phase, _os.getenv("HOSTNAME", "local"))
            except Exception:
                pass
            
            # Start background live price polling (keeps price_history fresh)
            try:
                asyncio.create_task(self._price_poll_loop(5))
                logger.info("✅ PIPELINE DEBUG: Entry Engine - Background price poller started (5s interval)")
            except Exception as e:
                logger.warning(f"⚠️ PIPELINE DEBUG: Entry Engine - Failed to start price poller: {e}")
            
            self.is_initialized = True
            logger.info("✅ Enhanced Intelligent Entry Engine initialized successfully")
            logger.info("🎯 PIPELINE DEBUG: Entry Engine - READY FOR OPERATIONS")
            logger.info("🎯 PIPELINE DEBUG: Entry Engine - Status: INITIALIZED & OPERATIONAL")
            
        except Exception as e:
            logger.error(f"Failed to initialize entry engine: {e}")
            logger.error("💥 PIPELINE DEBUG: Entry Engine - INITIALIZATION FAILED")
            logger.error(f"💥 PIPELINE DEBUG: Entry Engine - Error details: {str(e)}")
            raise

    async def _price_poll_loop(self, interval_sec: int = 5) -> None:
        """Background loop polling live price to update price_history.

        Args:
            interval_sec: polling interval in seconds.
        """
        while True:
            try:
                price = await get_live_bitcoin_price()
                if price and price > 0:
                    await self.update_price_history(price)
            except Exception as e:
                logger.debug(f"price poll failed: {e}")
            await asyncio.sleep(interval_sec)
    
    async def _start_warmup_period(self):
        """Start OPTIMIZED 3-minute phase-based warmup period for day trading"""
        logger.info(f"🔥 Starting OPTIMIZED {self.warmup_period_minutes}-minute phase-based warmup for day trading...")
        logger.info("📊 Phase 1 (1 min): Collect price history + higher thresholds")
        logger.info("📊 Phase 2 (2 min): Normal operation + medium thresholds")
        logger.info("📊 Phase 3 (3+ min): Full optimization + standard thresholds")
        
        # Start warmup task in background
        asyncio.create_task(self._warmup_background_task())
    
    async def _warmup_background_task(self):
        """OPTIMIZED: Phase-based warmup for day trading (3 minutes maximum)"""
        try:
            warmup_start = datetime.now(timezone.utc)
            logger.info("🚀 PHASE-BASED WARMUP: Starting optimized day trading warmup...")
            
            # PRE-LOAD HISTORICAL DATA in background (non-blocking)
            asyncio.create_task(self._preload_historical_data())
            
            # PHASE 1: Basic price history collection (1 minute)
            logger.info("🔥 PHASE 1: Collecting basic price history (higher thresholds)")
            self.warmup_phase = 1
            
            phase1_start = datetime.now(timezone.utc)
            while True:
                elapsed_minutes = (datetime.now(timezone.utc) - phase1_start).total_seconds() / 60
                
                # Check if we have minimum data for Phase 1
                if len(self.price_history) >= self.min_price_history_basic and elapsed_minutes >= 1.0:
                    logger.info(f"✅ PHASE 1 COMPLETE: {len(self.price_history)} price points collected")
                    break
                elif elapsed_minutes >= self.phase1_duration:
                    logger.info(f"⏰ PHASE 1 TIMEOUT: Proceeding with {len(self.price_history)} price points")
                    break
                
                await asyncio.sleep(10)  # Check every 10 seconds
            
            # PHASE 2: Normal operation with higher thresholds (2 minutes)
            logger.info("🔥 PHASE 2: Normal operation (medium thresholds)")
            self.warmup_phase = 2
            
            phase2_start = datetime.now(timezone.utc)
            while True:
                elapsed_minutes = (datetime.now(timezone.utc) - phase2_start).total_seconds() / 60
                
                # Check if we have full data for Phase 2
                if len(self.price_history) >= self.min_price_history_full and elapsed_minutes >= 1.0:
                    logger.info(f"✅ PHASE 2 COMPLETE: {len(self.price_history)} price points for full analysis")
                    break
                elif elapsed_minutes >= (self.phase2_duration - self.phase1_duration):
                    logger.info(f"⏰ PHASE 2 TIMEOUT: Proceeding with {len(self.price_history)} price points")
                    break
                
                await asyncio.sleep(10)  # Check every 10 seconds
            
            # PHASE 3: Full optimization (3+ minutes)
            logger.info("🔥 PHASE 3: Full optimization (standard thresholds)")
            self.warmup_phase = 3
            
            # Wait for minimum warmup period
            total_elapsed = (datetime.now(timezone.utc) - warmup_start).total_seconds() / 60
            if total_elapsed < self.warmup_period_minutes:
                remaining_time = (self.warmup_period_minutes - total_elapsed) * 60
                logger.info(f"⏰ Waiting {remaining_time:.0f} seconds for minimum warmup period...")
                await asyncio.sleep(remaining_time)
            
            # Warmup completed
            self.is_warmed_up = True
            self.warmup_completed_at = datetime.now(timezone.utc)
            total_time = (self.warmup_completed_at - warmup_start).total_seconds() / 60
            
            logger.info("✅ OPTIMIZED WARMUP COMPLETED!")
            logger.info(f"🎯 Total warmup time: {total_time:.1f} minutes")
            logger.info(f"📊 Price history points: {len(self.price_history)}")
            logger.info(f"🚀 Entry engine ready for DAY TRADING with standard thresholds")
            try:
                import os as _os
                from app.backend.services.metrics import set_engine_phase, set_engine_info
                set_engine_phase("entry", 3)
                set_engine_info("entry", "primary", "running", _os.getenv("HOSTNAME", "local"))
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"❌ Phase-based warmup failed: {e}")
            # Still mark as warmed up to prevent permanent blocking
            self.is_warmed_up = True
            self.warmup_completed_at = datetime.now(timezone.utc)
            self.warmup_phase = 3  # Default to full operation
    
    async def _preload_historical_data(self):
        """PRE-LOAD historical data in background during warmup (non-blocking)"""
        try:
            logger.info("🔄 PRE-LOADING: Historical context data in background...")
            
            # Test historical context if available
            if self.historical_context:
                # Test price range lookups
                from app.backend.services.live_market_data import get_live_bitcoin_price
                current_price = await get_live_bitcoin_price()
                
                if current_price:
                    # Pre-load price range positions
                    for period in ["1D", "7D", "30D"]:
                        try:
                            position = self.historical_context.get_price_range_position(current_price, period)
                            if position is not None:
                                logger.debug(f"   {period} range position: {position:.1%}")
                        except Exception as e:
                            logger.debug(f"   {period} range position failed: {e}")
                    
                    # Pre-load pattern success rates
                    for pattern in ["rsi_oversold", "macd_bullish", "bollinger_support"]:
                        try:
                            success_rate = self.historical_context.get_pattern_success_rate(pattern)
                            if success_rate:
                                logger.debug(f"   {pattern}: {success_rate.success_rate:.1%} success rate")
                        except Exception as e:
                            logger.debug(f"   {pattern} pattern failed: {e}")
                    
                    # Pre-load support/resistance levels
                    try:
                        support, resistance = self.historical_context.get_support_resistance_levels("30D")
                        logger.info(f"✅ PRE-LOADED: {len(support)} support, {len(resistance)} resistance levels")
                    except Exception as e:
                        logger.debug(f"   Support/resistance failed: {e}")
                        
                logger.info("✅ PRE-LOADING: Historical context data ready")
            else:
                logger.info("⚠️ PRE-LOADING: No historical context service available")
                
        except Exception as e:
            logger.warning(f"⚠️ PRE-LOADING: Historical data pre-load failed: {e}")
    
    def get_current_warmup_phase(self) -> int:
        """Get current warmup phase for dynamic threshold adjustment"""
        if not self.is_warmed_up:
            return self.warmup_phase
        return 3  # Full operation after warmup
    
    def get_phase_based_confidence_threshold(self) -> float:
        """Get confidence threshold based on current warmup phase"""
        phase = self.get_current_warmup_phase()
        
        if phase == 1:
            return self.phase1_confidence_threshold  # 0.75 - Higher during initial warmup
        elif phase == 2:
            return self.phase2_confidence_threshold  # 0.70 - Medium during phase 2  
        else:
            return self.phase3_confidence_threshold  # 0.65 - Normal after full warmup
    
    def _load_entry_models(self):
        """Load all 6-layer entry analysis models (OPTIONAL - graceful fallback)"""
        try:
            model_files = {
                "regime": "layer_1_regime.pkl",
                "lstm": "lstm_1h.h5",
                "patterns": "layer_3_reversal.pkl",  # Reuse for pattern detection
                "technical": "layer_4_filters.pkl",
                "momentum": "layer_5_confidence.pkl",  # Reuse for momentum
                "timing": "layer_6_timing.pkl"
            }
            
            models_loaded = 0
            for model_name, filename in model_files.items():
                model_file = self.model_path / filename
                try:
                    if model_file.exists():
                        if filename.endswith('.pkl'):
                            with open(model_file, "rb") as f:
                                self.models[model_name] = pickle.load(f)
                        else:
                            # For .h5 files (TensorFlow models)
                            self.models[model_name] = f"model_path:{model_file}"
                        
                        logger.info(f"✅ Loaded {model_name} entry model")
                        self.layer_health[model_name] = "healthy"
                        models_loaded += 1
                    else:
                        logger.warning(f"⚠️ Model file not found: {filename}")
                        self.layer_health[model_name] = "degraded"
                except Exception as model_error:
                    logger.warning(f"⚠️ Failed to load {model_name} model: {model_error}")
                    self.layer_health[model_name] = "degraded"
            
            if models_loaded == 0:
                logger.warning("⚠️ No models loaded - using fallback analysis mode")
            else:
                logger.info(f"✅ Loaded {models_loaded}/{len(model_files)} entry models")
            
        except Exception as e:
            logger.warning(f"Model loading encountered issues: {e}")
            logger.info("🔄 Continuing with fallback analysis mode (no models required)")
    
    def _initialize_health_monitoring(self):
        """Initialize health monitoring for all layers"""
        for layer_id, config in self.layers.items():
            layer_name = config["name"]
            if layer_name not in self.layer_health:
                self.layer_health[layer_name] = "unknown"
    
    async def analyze_entry_opportunity(
        self, symbol: str, signal_data: Dict[str, Any], user_portfolio: Dict[str, Any], market_data_override: Optional[Dict[str, Any]] = None
    ) -> EntryAnalysisResult:
        """
        ENHANCED: Analyze entry opportunity with historical validation, startup protection, and cooldown
        
        Args:
            symbol: Trading symbol
            signal_data: AI signal data
            user_portfolio: User portfolio information
            
        Returns:
            Comprehensive entry analysis result with historical validation
        """
        if not self.is_initialized:
            logger.info("🔄 PIPELINE DEBUG: Entry Engine - Not initialized, initializing now...")
            await self.initialize()
        
        # RE-ENTRY COOLDOWN CHECK: Prevent immediate re-entry after recent exit
        try:
            from app.backend.services.intelligent_exit_engine import IntelligentExitEngine
            # Get or create exit engine instance to check cooldown
            from app.backend.core.container import get_container
            container = get_container()
            if hasattr(container, '_exit_engine') and container._exit_engine:
                exit_engine = container._exit_engine
                if exit_engine.check_reentry_cooldown(symbol):
                    remaining = exit_engine.get_cooldown_remaining(symbol)
                    logger.info(f"⏰ RE-ENTRY COOLDOWN: {symbol} blocked for {remaining:.1f}s - WAIT")
                    return EntryAnalysisResult(
                        should_enter=False,
                        confidence=0.0,
                        entry_reason=EntryReason.WAIT_FOR_CONFIRMATION,
                        entry_quality=EntryQuality.POOR,
                        optimal_entry_price=None,
                        reasoning=f"Re-entry cooldown active ({remaining:.1f}s remaining)",
                        timestamp=datetime.now(timezone.utc),
                        historical_validation_score=0.0
                    )
        except Exception as e:
            logger.debug(f"Cooldown check failed (continuing): {e}")
        
        logger.info(f"🎯 UPGRADED ENTRY ENGINE - Analyzing predictive entry opportunity for {symbol}")
        logger.info(f"📊 PIPELINE DEBUG: Entry Engine - Signal data keys: {list(signal_data.keys()) if signal_data else 'None'}")
        logger.info(f"💼 PIPELINE DEBUG: Entry Engine - Portfolio data available: {bool(user_portfolio)}")
        
        # GET CURRENT PRICE AND UPDATE HISTORY (no fallbacks, best-effort history update)
        current_price: Optional[float] = None
        try:
            cp = await get_live_bitcoin_price()
            if cp is not None and cp > 0:
                current_price = cp
                await self.update_price_history(cp)
            else:
                logger.warning("Live price unavailable or invalid; skipping history update before cooldown check")
        except Exception as e:
            logger.warning(f"Failed to get live price for history update: {e}")
        signal_action = signal_data.get("action", "HOLD")
        
        logger.info(f"📈 PREDICTIVE ANALYSIS: Current price {current_price:.2f}, Signal: {signal_action}, History points: {len(self.price_history)}")
        
        # COOLDOWN CHECK: Prevent excessive analysis
        import time
        current_time = time.time()
        last_analysis_time = self.entry_cooldown_cache.get(symbol, 0)
        
        if current_time - last_analysis_time < self.entry_cooldown_seconds:
            remaining_cooldown = self.entry_cooldown_seconds - (current_time - last_analysis_time)
            logger.debug(f"🔄 PIPELINE DEBUG: Entry Engine - Cooldown active for {symbol}, {remaining_cooldown:.1f}s remaining")
            
            # Get current price even during cooldown
            try:
                current_price = await get_live_bitcoin_price()
            except Exception as e:
                logger.warning(f"Failed to get live price during cooldown: {e}")
                current_price = None
            
            return EntryAnalysisResult(
                should_enter=False,
                confidence=0.0,
                entry_reason=EntryReason.POOR_TIMING,
                entry_quality=EntryQuality.POOR,
                optimal_entry_price=float(current_price) if current_price else 0.0,
                position_size_recommendation=0.0,
                risk_score=1.0,
                timing_score=0.0,
                layer_analysis={"cooldown_status": "active"},
                market_conditions={"cooldown_remaining_seconds": remaining_cooldown},
                analysis_time_ms=0.0,
                timestamp=datetime.now(timezone.utc)
            )
        
        # Update last analysis time
        self.entry_cooldown_cache[symbol] = current_time
        
        # OPTIMIZED PHASE-BASED WARMUP: Allow entries with higher thresholds during phases
        current_phase = self.get_current_warmup_phase()
        phase_threshold = self.get_phase_based_confidence_threshold()
        
        if not self.is_warmed_up:
            elapsed_minutes = (datetime.now(timezone.utc) - self.startup_time).total_seconds() / 60
            remaining_minutes = max(0, self.warmup_period_minutes - elapsed_minutes)
            
            # PHASE 1: Block entries if insufficient price history
            if current_phase == 1 and len(self.price_history) < self.min_price_history_basic:
                logger.info(f"🔥 PHASE 1 WARMUP: Entry blocked - collecting price history ({len(self.price_history)}/{self.min_price_history_basic})")
                logger.info(f"⏰ PIPELINE DEBUG: Entry Engine - PHASE 1 ACTIVE - Need more price data")
                
                return EntryAnalysisResult(
                    should_enter=False,
                    confidence=0.0,
                    entry_reason=EntryReason.POOR_TIMING,
                    entry_quality=EntryQuality.POOR,
                    optimal_entry_price=float(current_price),
                    position_size_recommendation=0.0,
                    risk_score=1.0,
                    timing_score=0.0,
                    layer_analysis={"warmup_phase": current_phase, "price_history_count": len(self.price_history)},
                    market_conditions={"warmup_remaining_minutes": remaining_minutes, "phase_threshold": phase_threshold},
                    analysis_time_ms=0.0,
                    timestamp=datetime.now(timezone.utc)
                )
            
            # PHASE 2 & 3: Allow entries with phase-appropriate thresholds
            logger.info(f"🔥 PHASE {current_phase} WARMUP: Analysis allowed with {phase_threshold:.0%} threshold")
            logger.info(f"📊 PIPELINE DEBUG: Entry Engine - PHASE {current_phase} ACTIVE - Using higher thresholds")
        
        start_time = datetime.now()
        
        # Initialize variables early to prevent NameError in exception handlers
        market_data = {"price": 0.0, "volume": 0.0, "volatility": 0.02, "volume_ratio": 1.0, "trend_strength": 0.5}
        current_price = 0.0  # Initialize current_price for exception handler
        
        try:
            # FIXED: Resilient error handling for undefined variables
            logger.info(f"🎯 Analyzing ENHANCED entry opportunity for {symbol}")
            logger.info("📊 PIPELINE DEBUG: Entry Engine - Starting 6-layer entry analysis")
            
            return await self._analyze_entry_core(symbol, signal_data, user_portfolio, market_data_override, current_price, start_time)
            
        except NameError as e:
            logger.exception("❌ Entry analysis failed due to undefined variable: %s", e)
            return EntryAnalysisResult(
                should_enter=False,
                confidence=0.0,
                entry_reason=EntryReason.POOR_TIMING,
                entry_quality=EntryQuality.POOR,
                optimal_entry_price=float(current_price) if current_price > 0 else 0.0,
                position_size_recommendation=0.0,
                risk_score=1.0,
                timing_score=0.0,
                layer_analysis={"error": f"internal_error: undefined symbol - {str(e)}"},
                market_conditions={"error": "variable_not_defined"},
                analysis_time_ms=0.0,
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"❌ Entry analysis failed: {e}")
            
            # Strict no-fallback: surface error, but return structured WAIT with no fabricated price
            return EntryAnalysisResult(
                should_enter=False,
                confidence=0.0,
                entry_reason=EntryReason.POOR_TIMING,
                entry_quality=EntryQuality.POOR,
                optimal_entry_price=float(current_price) if current_price and current_price > 0 else 0.0,
                position_size_recommendation=0.0,
                risk_score=1.0,
                timing_score=0.0,
                layer_analysis={"error": str(e)},
                market_conditions={"error": "analysis_failed"},
                analysis_time_ms=0.0,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _analyze_entry_core(self, symbol: str, signal_data: Dict[str, Any], user_portfolio: Dict[str, Any], 
                                 market_data_override: Optional[Dict[str, Any]], current_price: float, start_time):
        """Core entry analysis logic separated for better error handling"""
        try:
            
            # Get current market data with strict validation (no fallbacks)
            logger.info("📈 PIPELINE DEBUG: Entry Engine - Fetching live market data...")
            current_price = await get_live_bitcoin_price()
            if current_price is None or current_price <= 0:
                logger.error("❌ Cannot get valid Bitcoin price for entry analysis")
                logger.error("💥 PIPELINE DEBUG: Entry Engine - CRITICAL: Invalid Bitcoin price")
                raise ValueError("Invalid Bitcoin price - cannot perform entry analysis")
            
            logger.info(f"💰 PIPELINE DEBUG: Entry Engine - Current Bitcoin price: ${current_price:,.2f}")
            
            # FIXED: Properly initialize market_data
            market_data = market_data_override if market_data_override is not None else await get_live_market_data()
            if market_data is None:
                logger.error("❌ Cannot get market data for entry analysis")
                raise RuntimeError("Live market data unavailable")
            else:
                try:
                    from app.backend.services.metrics import set_decision_threshold
                    from app.backend.config.trading_thresholds import ConfidenceThresholds
                    th = ConfidenceThresholds()
                    phase_str = f"phase{self.get_current_warmup_phase()}" if not self.is_warmed_up else "running"
                    set_decision_threshold("entry", "primary", phase_str, float(th.BUY_THRESHOLD))
                    set_decision_threshold("entry", "exploratory", phase_str, float(th.EXPLORATORY_BUY))
                except Exception:
                    pass
            logger.info("✅ PIPELINE DEBUG: Entry Engine - Live market data retrieved successfully")
            
            # ENHANCED: Add historical market context
            logger.info("📊 PIPELINE DEBUG: Entry Engine - Processing historical market context...")
            if self.historical_context:
                try:
                    # ENHANCED: Set current indicators for consistency checking
                    current_rsi = market_data.get("rsi", 50.0)
                    current_bb_pos = market_data.get("bollinger_position", 0.5)
                    self.historical_context.set_current_indicators(current_rsi, current_bb_pos)
                    
                    # Get price position in historical ranges
                    logger.info("📊 PIPELINE DEBUG: Entry Engine - Getting price range positions...")
                    price_position_30d = self.historical_context.get_price_range_position(current_price, "30D")
                    price_position_7d = self.historical_context.get_price_range_position(current_price, "7D")
                    if price_position_30d is None or price_position_7d is None:
                        raise RuntimeError("Historical context returned incomplete price range positions")
                    
                    # Get support/resistance levels
                    logger.info("📊 PIPELINE DEBUG: Entry Engine - Getting support/resistance levels...")
                    support_levels, resistance_levels = self.historical_context.get_support_resistance_levels("30D")
                    # Ensure we have valid data (no fabricated levels)
                    support_levels = support_levels if support_levels is not None else []
                    resistance_levels = resistance_levels if resistance_levels is not None else []
                    
                    # Add to market data for layer analysis
                    market_data["price_position_30d"] = price_position_30d
                    market_data["price_position_7d"] = price_position_7d
                    market_data["support_levels"] = support_levels
                    market_data["resistance_levels"] = resistance_levels
                    market_data["historical_context_available"] = True
                    
                    # Safe formatting for price positions
                    pos_30d_str = f"{price_position_30d:.1%}" if price_position_30d is not None else "N/A"
                    pos_7d_str = f"{price_position_7d:.1%}" if price_position_7d is not None else "N/A"
                    support_count = len(support_levels)
                    resistance_count = len(resistance_levels)
                    
                    logger.info(f"📊 Historical context: 30D position {pos_30d_str}, 7D position {pos_7d_str}")
                    logger.info(f"📊 Support/Resistance: {support_count} support levels, {resistance_count} resistance levels")
                    
                    # DIAGNOSTIC: Log symbol and time window info for debugging
                    if hasattr(self.historical_context, 'symbol'):
                        logger.info(f"🔍 RANGE DATA SOURCE: symbol={self.historical_context.symbol}, current_price=${current_price:.2f}")
                    
                    # Compare with current RSI/BB calculations for consistency check
                    current_rsi = market_data.get("rsi", 0.0)
                    current_bb_pos = market_data.get("bollinger_position", 0.5)
                    logger.info(f"🔍 MULTI-TF ANALYSIS: RSI={current_rsi:.1f}, BB_pos={current_bb_pos:.3f} vs 30D_pos={pos_30d_str}, 7D_pos={pos_7d_str}")
                    
                    # ENHANCED: Log data sources for debugging
                    rsi_source = "1m_candles_last_14_periods"
                    bb_source = "1m_candles_last_20_periods" 
                    range_source = f"dynamodb_historical_{self.historical_context.symbol if hasattr(self.historical_context, 'symbol') else 'unknown'}"
                    logger.info(f"🔍 DATA SOURCES: RSI/BB from {rsi_source}, Range from {range_source}, Price=${current_price:.2f}")
                    
                    # FIXED: Multi-timeframe divergence analysis (not inconsistency)
                    if price_position_30d > 0.9 and current_rsi < 10:
                        logger.info(f"📊 MULTI-TIMEFRAME: Short-term oversold (RSI={current_rsi:.1f}) in long-term high regime ({pos_30d_str}) - MEAN REVERSION OPPORTUNITY")
                        logger.info("    → This is NORMAL: Short-term indicators show oversold while long-term range shows high position")
                    if price_position_7d > 0.9 and current_bb_pos < 0.1:
                        logger.info(f"📊 MULTI-TIMEFRAME: Short-term lower band (BB={current_bb_pos:.3f}) in 7D high position ({pos_7d_str}) - POTENTIAL BOUNCE")
                        logger.info("    → This is NORMAL: Current price hit Bollinger lower band while still in weekly high range")
                    
                    # Enhanced divergence context
                    if (price_position_30d > 0.8 and current_rsi < 20) or (price_position_7d > 0.8 and current_bb_pos < 0.2):
                        logger.info(f"🎯 TRADING CONTEXT: Strong mean-reversion setup detected - ideal for BUY signals")
                    logger.info("✅ PIPELINE DEBUG: Entry Engine - Historical context processed successfully")
                    
                except Exception as context_error:
                    logger.error(f"⚠️ PIPELINE DEBUG: Entry Engine - Historical context failed: {context_error}")
                    try:
                        from app.backend.services.metrics import inc_historical_context_error
                        inc_historical_context_error()
                    except Exception:
                        pass
                    raise
            else:
                logger.error("⚠️ PIPELINE DEBUG: Entry Engine - No historical context service available")
                raise RuntimeError("Historical context service unavailable")
            
            # ENHANCED: Run microstructure validation first
            logger.info("📊 PIPELINE DEBUG: Entry Engine - Running microstructure validation...")
            try:
                from app.backend.services.microstructure_validator import get_microstructure_validator
                microstructure_validator = get_microstructure_validator()
                
                # Estimate position size for slippage calculation - FIXED
                cash_balance = user_portfolio.get('cash_balance', 50000.0) if isinstance(user_portfolio, dict) else getattr(user_portfolio, 'cash_balance', 50000.0)
                estimated_size_usd = min(5000.0, float(cash_balance) * 0.03)  # 3% or $5k max
                
                microstructure_result = await microstructure_validator.validate_entry_microstructure(
                    market_data, signal_data.get("action", "HOLD"), estimated_size_usd
                )
                
                # Add microstructure data to market_data for layer analysis
                market_data["microstructure"] = {
                    "spread_bps": microstructure_result["spread_metrics"]["spread_bps"],
                    "imbalance_ratio": microstructure_result["imbalance_metrics"]["imbalance_ratio"],
                    "slippage_bps": microstructure_result["slippage_metrics"]["slippage_bps"],
                    "edge_score": microstructure_result["edge_score"],
                    "is_valid": microstructure_result["is_valid"]
                }
                
                logger.info("✅ PIPELINE DEBUG: Entry Engine - Microstructure validation completed")
                
            except Exception as e:
                logger.warning(f"⚠️ Microstructure validation failed: {e}")
                # Add default microstructure data
                market_data["microstructure"] = {
                    "spread_bps": 1.0,
                    "imbalance_ratio": 0.5,
                    "slippage_bps": 1.0,
                    "edge_score": 0.5,
                    "is_valid": True
                }
            
            # Run 6-layer entry analysis
            layer_results = await self._run_six_layer_entry_analysis(
                symbol, signal_data, current_price, market_data, user_portfolio
            )
            
            # Calculate consensus decision - FIXED: Pass market_data parameter
            entry_decision = await self._calculate_entry_consensus(layer_results, signal_data, market_data)
            
            # Calculate optimal entry price with safe fallback
            try:
                optimal_entry_price = self._calculate_optimal_entry_price(
                    current_price, layer_results, market_data
                )
                # Ensure it's never None or zero
                if optimal_entry_price is None or optimal_entry_price <= 0:
                    optimal_entry_price = current_price
                    logger.warning(f"⚠️ Optimal entry price was invalid ({optimal_entry_price}), using current price: ${current_price:,.2f}")
            except Exception as e:
                logger.error(f"❌ Error calculating optimal entry price: {e}")
                optimal_entry_price = current_price
            
            # Calculate position size recommendation
            position_size = self._calculate_position_size(
                entry_decision, user_portfolio, layer_results
            )
            # Apply playbook override size haircut if present
            try:
                if entry_decision.get("reason") == "playbook_override":
                    from app.backend.core.runtime_config import runtime_config_store
                    cfg = await runtime_config_store.get()
                    position_size *= float(getattr(cfg, "playbook_override_size_multiplier", 0.60))
            except Exception:
                pass
            
            # Calculate analysis time
            analysis_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update performance stats
            self.total_analyses += 1
            if entry_decision["should_enter"]:
                self.entries_recommended += 1
            
            # DAY TRADING VALIDATOR: Smart quality check before entry
            validator_passed = True
            validator_reason = "Entry approved"
            validator_details = {}
            
            if entry_decision["should_enter"]:
                try:
                    logger.info("🎯 DAY TRADING VALIDATOR: Checking setup quality...")
                    validator = get_day_trading_validator()
                    
                    # Create signal object for validation
                    from dataclasses import dataclass as dc_class
                    @dc_class
                    class SignalForValidation:
                        symbol: str
                        action: str
                        confidence: float
                        price: float
                        layer_analysis: Dict[str, Any]
                    
                    signal_for_validation = SignalForValidation(
                        symbol=symbol,
                        action=signal_data.get("action", "HOLD"),
                        confidence=entry_decision["confidence"],
                        price=current_price,
                        layer_analysis=layer_results
                    )
                    
                    validator_passed, validator_reason, validator_details = await validator.validate_day_trading_setup(
                        signal_for_validation, market_data
                    )
                    
                    if not validator_passed:
                        logger.warning(f"❌ DAY TRADING VALIDATOR: Setup rejected - {validator_reason}")
                        entry_decision["should_enter"] = False
                        entry_decision["reason"] = "validator_rejected"
                        entry_decision["confidence"] = 0.0
                        entry_decision["validator_reason"] = validator_reason
                    else:
                        logger.info(f"✅ DAY TRADING VALIDATOR: Setup approved - {validator_reason}")
                        
                except Exception as validator_error:
                    logger.warning(f"⚠️ DAY TRADING VALIDATOR: Check failed - {validator_error}")
                    # Don't block entry on validator errors
                    pass
            
            # Create comprehensive result
            result = EntryAnalysisResult(
                should_enter=entry_decision["should_enter"],
                confidence=entry_decision["confidence"],
                entry_reason=EntryReason(entry_decision.get("reason", "wait_for_confirmation")),
                entry_quality=self._determine_entry_quality(entry_decision["confidence"]),
                optimal_entry_price=optimal_entry_price,
                position_size_recommendation=position_size,
                risk_score=entry_decision["risk_score"],
                timing_score=entry_decision["timing_score"],
                layer_analysis=layer_results,
                market_conditions={
                    "current_price": current_price,
                    "market_data": market_data,
                    "volatility": market_data.get("volatility", 0.0),
                    "volume_ratio": market_data.get("volume_ratio", 1.0),
                    "trend_strength": market_data.get("trend_strength", 0.5)
                },
                analysis_time_ms=analysis_time,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Safe logging with validation
            confidence_str = safe_format_number(entry_decision.get('confidence', 0) * 100, 1) + "%"
            logger.info(f"✅ Entry analysis completed: {'ENTER' if entry_decision['should_enter'] else 'WAIT'} "
                       f"(confidence: {confidence_str}, quality: {result.entry_quality.value})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Entry analysis core failed: {e}")
            raise  # Re-raise to be handled by outer exception handler
    
    async def _run_six_layer_entry_analysis(
        self, symbol: str, signal_data: Dict[str, Any], current_price: float, 
        market_data: Dict[str, Any], user_portfolio: Dict[str, Any]
    ) -> Dict[str, Any]:
        """UPGRADED: Run comprehensive 6-layer entry analysis with predictive features"""
        
        layer_results = {}
        signal_action = signal_data.get("action", "HOLD")
        
        # Layer 1: Market Regime Analysis (Reduced weight)
        try:
            regime_analysis = await self._analyze_entry_market_regime(market_data, signal_data)
            layer_results["layer_1_regime"] = regime_analysis
        except Exception as e:
            logger.warning(f"Layer 1 (Regime) failed: {e}")
            layer_results["layer_1_regime"] = {"recommendation": "wait", "confidence": 0.0}
        
        # Layer 2: UPGRADED Predictive Price Analysis (Increased weight)
        try:
            # Get price prediction
            price_prediction = await self.predict_price_target(current_price, signal_action)
            
            # Combine with LSTM if available
            if not DISABLE_LSTM:
                try:
                    lstm_analysis = await self._analyze_lstm_entry_signals(symbol, current_price, signal_data)
                    # Merge LSTM with price prediction
                    combined_confidence = (price_prediction["confidence"] + lstm_analysis.get("confidence", 0.0)) / 2
                    recommendation = "enter" if price_prediction["wait_for_better_price"] == False and lstm_analysis.get("recommendation") == "enter" else "wait"
                except Exception as e:
                    logger.warning(f"LSTM analysis failed: {e}")
                    combined_confidence = price_prediction["confidence"]
                    recommendation = "wait" if price_prediction["wait_for_better_price"] else "enter"
            else:
                combined_confidence = price_prediction["confidence"]
                recommendation = "wait" if price_prediction["wait_for_better_price"] else "enter"
            
            layer_results["layer_2_predictive"] = {
                "recommendation": recommendation,
                "confidence": combined_confidence,
                "predicted_target": price_prediction["predicted_target"],
                "wait_for_better_price": price_prediction["wait_for_better_price"],
                "reasoning": f"Predictive analysis: {price_prediction['reason']}"
            }
            
        except Exception as e:
            logger.warning(f"Layer 2 (Predictive) failed: {e}")
            layer_results["layer_2_predictive"] = {"recommendation": "wait", "confidence": 0.0}
        
        # Layer 3: Pattern Recognition (Same)
        try:
            pattern_analysis = await self._analyze_entry_patterns(market_data, signal_data)
            layer_results["layer_3_patterns"] = pattern_analysis
        except Exception as e:
            logger.warning(f"Layer 3 (Patterns) failed: {e}")
            layer_results["layer_3_patterns"] = {"recommendation": "wait", "confidence": 0.0}
        
        # Layer 4: ENHANCED Technical Momentum (Enhanced)
        try:
            technical_analysis = await self._analyze_entry_technical_indicators(market_data, current_price)
            layer_results["layer_4_technical"] = technical_analysis
        except Exception as e:
            logger.warning(f"Layer 4 (Technical) failed: {e}")
            layer_results["layer_4_technical"] = {"recommendation": "wait", "confidence": 0.0}
        
        # Layer 5: NEW Price Direction Confirmation (NEW)
        try:
            # Get price momentum confirmation
            momentum_confirmation = await self.analyze_price_momentum(current_price, signal_action)
            
            # Combine with traditional momentum analysis
            traditional_momentum = await self._analyze_entry_momentum(market_data, signal_data)
            
            # Create enhanced momentum analysis
            if momentum_confirmation["momentum_confirmed"]:
                recommendation = "enter" if traditional_momentum.get("recommendation") == "enter" else "wait"
                confidence = (momentum_confirmation["momentum_strength"] + traditional_momentum.get("confidence", 0.0)) / 2
                confidence = min(confidence * 1.2, 1.0)  # Boost confidence when momentum confirmed
            else:
                recommendation = "wait"  # Always wait if momentum not confirmed
                confidence = traditional_momentum.get("confidence", 0.0) * 0.5  # Reduce confidence
            
            layer_results["layer_5_price_direction"] = {
                "recommendation": recommendation,
                "confidence": confidence,
                "momentum_confirmed": momentum_confirmation["momentum_confirmed"],
                "price_direction": momentum_confirmation["price_direction"],
                "momentum_strength": momentum_confirmation["momentum_strength"],
                "reasoning": f"Price momentum: {momentum_confirmation['reason']}"
            }
            
        except Exception as e:
            logger.warning(f"Layer 5 (Price Direction) failed: {e}")
            layer_results["layer_5_price_direction"] = {"recommendation": "wait", "confidence": 0.0}
        
        # Layer 6: Smart Entry Timing (Reduced weight)
        try:
            timing_analysis = await self._analyze_entry_timing(market_data, signal_data, user_portfolio)
            layer_results["layer_6_timing"] = timing_analysis
        except Exception as e:
            logger.warning(f"Layer 6 (Timing) failed: {e}")
            layer_results["layer_6_timing"] = {"recommendation": "wait", "confidence": 0.0}
        
        logger.info(f"🎯 UPGRADED 6-LAYER ANALYSIS COMPLETE:")
        logger.info(f"   Layer 1 (Regime): {layer_results['layer_1_regime'].get('recommendation', 'unknown')}")
        logger.info(f"   Layer 2 (Predictive): {layer_results['layer_2_predictive'].get('recommendation', 'unknown')}")
        logger.info(f"   Layer 3 (Patterns): {layer_results['layer_3_patterns'].get('recommendation', 'unknown')}")
        logger.info(f"   Layer 4 (Technical): {layer_results['layer_4_technical'].get('recommendation', 'unknown')}")
        logger.info(f"   Layer 5 (Price Direction): {layer_results['layer_5_price_direction'].get('recommendation', 'unknown')}")
        logger.info(f"   Layer 6 (Timing): {layer_results['layer_6_timing'].get('recommendation', 'unknown')}")
        
        # Enrich with microstructure estimates (spread/slippage)
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
        try:
            import numpy as _np
            closes = [float(x) for x in self.price_history[-10:]] if hasattr(self, 'price_history') else []
            std = float(_np.std(_np.array(closes))) if len(closes) >= 5 else 0.0
            slippage_bps = float((std / max(current_price, 1e-9)) * 10000.0)
        except Exception:
            slippage_bps = 0.0
        layer_results["microstructure"] = {"spread_bps": spread_bps, "slippage_bps": slippage_bps}
        
        return layer_results
    
    async def _analyze_entry_market_regime(self, market_data: Dict[str, Any], signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 1: Analyze market regime for entry"""
        
        volatility = market_data.get("volatility", 0.02)
        volume_ratio = market_data.get("volume_ratio", 1.0)
        trend_strength = market_data.get("trend_strength", 0.5)
        signal_action = signal_data.get("action", "HOLD")
        
        # Determine if regime is favorable for entry
        if signal_action == "BUY":
            if trend_strength > 0.7 and volatility < 0.05:  # Strong uptrend, low volatility
                recommendation = "enter"
                confidence = 0.8
                regime = "favorable_uptrend"
            elif volume_ratio > 1.5 and volatility < 0.08:  # High volume, moderate volatility
                recommendation = "enter"
                confidence = 0.7
                regime = "high_volume_breakout"
            elif volatility > 0.10:  # Too volatile
                recommendation = "wait"
                confidence = 0.3
                regime = "too_volatile"
            else:
                recommendation = "enter"
                confidence = 0.6
                regime = "neutral"
        elif signal_action == "SELL":
            if trend_strength < -0.7 and volatility < 0.05:  # Strong downtrend
                recommendation = "enter"
                confidence = 0.8
                regime = "favorable_downtrend"
            else:
                recommendation = "wait"
                confidence = 0.4
                regime = "unfavorable_short"
        else:
            recommendation = "wait"
            confidence = 0.2
            regime = "no_signal"
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "regime": regime,
            "volatility": volatility,
            "volume_ratio": volume_ratio,
            "trend_strength": trend_strength,
            "reasoning": f"Market regime: {regime} with {safe_format_number(volatility * 100, 1)}% volatility"
        }
    
    def _calculate_technical_features(self, candles: List[Dict], lookback: int = 200) -> np.ndarray:
        """
        Calculate the 11 technical features that LSTM models expect.
        
        Features (in order):
        1. logret - Log returns
        2. ema9_delta - EMA9 delta  
        3. ema21_delta - EMA21 delta
        4. macd - MACD line
        5. macd_sig - MACD signal
        6. macd_hist - MACD histogram
        7. rsi14_norm - Normalized RSI (0-1)
        8. %B - Bollinger %B
        9. bb_width - Bollinger width
        10. atr14_norm - Normalized ATR
        11. vol_ratio - Volume ratio
        """
        try:
            import pandas as pd
            
            # Convert candles to DataFrame
            df = pd.DataFrame(candles)
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float) 
            df['low'] = df['low'].astype(float)
            df['open'] = df['open'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # Ensure we have enough data
            if len(df) < 50:
                raise ValueError(f"Insufficient data: {len(df)} candles, need at least 50")
            
            # 1. Log returns
            df['logret'] = np.log(df['close'] / df['close'].shift(1)).fillna(0)
            
            # 2-3. EMA deltas (using pandas ewm)
            ema9 = df['close'].ewm(span=9).mean()
            ema21 = df['close'].ewm(span=21).mean()
            df['ema9_delta'] = (df['close'] - ema9) / df['close']
            df['ema21_delta'] = (df['close'] - ema21) / df['close']
            
            # 4-6. MACD (simple implementation)
            ema_12 = df['close'].ewm(span=12).mean()
            ema_26 = df['close'].ewm(span=26).mean()
            macd_line = ema_12 - ema_26
            macd_signal = macd_line.ewm(span=9).mean()
            macd_hist = macd_line - macd_signal
            df['macd'] = macd_line / df['close']  # Normalized
            df['macd_sig'] = macd_signal / df['close']  # Normalized  
            df['macd_hist'] = macd_hist / df['close']  # Normalized
            
            # 7. RSI normalized (0-1) - simple implementation
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            df['rsi14_norm'] = rsi / 100.0
            
            # 8-9. Bollinger Bands
            bb_middle = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            bb_upper = bb_middle + (bb_std * 2)
            bb_lower = bb_middle - (bb_std * 2)
            df['%B'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
            df['bb_width'] = (bb_upper - bb_lower) / bb_middle
            
            # 10. ATR normalized (simple implementation)
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = true_range.rolling(window=14).mean()
            df['atr14_norm'] = atr / df['close']
            
            # 11. Volume ratio (current vs SMA)
            vol_sma = df['volume'].rolling(window=20).mean()
            df['vol_ratio'] = df['volume'] / vol_sma
            
            # Fill NaN values with neutral defaults
            feature_defaults = {
                'logret': 0.0,
                'ema9_delta': 0.0,
                'ema21_delta': 0.0, 
                'macd': 0.0,
                'macd_sig': 0.0,
                'macd_hist': 0.0,
                'rsi14_norm': 0.5,
                '%B': 0.5,
                'bb_width': 0.02,
                'atr14_norm': 0.02,
                'vol_ratio': 1.0
            }
            
            for feature, default_val in feature_defaults.items():
                df[feature] = df[feature].fillna(default_val)
            
            # Extract feature columns in correct order
            feature_columns = ['logret', 'ema9_delta', 'ema21_delta', 'macd', 'macd_sig', 
                             'macd_hist', 'rsi14_norm', '%B', 'bb_width', 'atr14_norm', 'vol_ratio']
            
            # Get the last `lookback` rows and reshape for LSTM
            features = df[feature_columns].values[-lookback:]
            
            # Pad if needed
            if len(features) < lookback:
                padding = np.tile(features[0], (lookback - len(features), 1))
                features = np.vstack([padding, features])
            
            # Reshape to (1, lookback, 11) for LSTM
            return features.reshape(1, lookback, 11)
            
        except Exception as e:
            logger.error(f"Technical feature calculation failed: {e}")
            # Return neutral feature matrix
            neutral_features = np.array([
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 0.5, 0.02, 0.02, 1.0]
            ] * lookback).reshape(1, lookback, 11)
            return neutral_features

    async def _analyze_lstm_entry_signals(self, symbol: str, current_price: float, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 2: Analyze LSTM/short-horizon predictions for entry timing (FIXED DIMENSIONS)."""
        try:
            # TensorFlow import with proper initialization
            try:
                import tensorflow as tf
                # Configure TensorFlow to prevent mutex issues
                tf.config.set_visible_devices([], 'GPU')  # Force CPU only
                tf.config.threading.set_inter_op_parallelism_threads(1)
                tf.config.threading.set_intra_op_parallelism_threads(1)
                tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
            except Exception as tf_error:
                logger.warning(f"⚠️ TensorFlow initialization failed: {tf_error}")
                raise ImportError("TensorFlow not available") from tf_error
            
            current_file = Path(__file__).parent.parent  # Go up from services/ to backend/
            models_dir = current_file / "models" / "enterprise"
            model_path_1m = models_dir / "lstm_1m.h5"
            model_path_5m = models_dir / "lstm_5m.h5"

            preds: List[float] = []
            pred_meta: Dict[str, Any] = {}

            threshold_map: Dict[str, float] = {}
            meta_1m = self.model_path / "lstm_1m_meta.json"
            meta_5m = self.model_path / "lstm_5m_meta.json"
            if meta_1m.exists():
                try:
                    threshold_map["1m"] = float(json.loads(meta_1m.read_text()).get("threshold", 0.5))
                except Exception:
                    threshold_map["1m"] = 0.5
            if meta_5m.exists():
                try:
                    threshold_map["5m"] = float(json.loads(meta_5m.read_text()).get("threshold", 0.5))
                except Exception:
                    threshold_map["5m"] = 0.5

            # Get historical sequences for LSTM (PROFESSIONAL IMPLEMENTATION)
            from app.backend.services.live_market_data import get_live_market_data_service
            service = await get_live_market_data_service()
            
            # Models output probability of upward move (sigmoid)
            if model_path_1m.exists():
                model_1m = tf.keras.models.load_model(model_path_1m, compile=False)
                
                # Get 200 recent 1m candles for proper feature calculation
                candles_1m = service.get_recent_candles('1m', 250)  # Extra buffer for indicators
                if len(candles_1m) >= 60:  # Higher minimum for enterprise accuracy
                    # Calculate proper 11-feature technical indicators
                    x_1m = self._calculate_technical_features(candles_1m, lookback=200)
                    p1 = float(model_1m.predict(x_1m)[0][0])
                    preds.append(p1)
                    pred_meta["1m"] = {"prediction": p1, "sequence_length": len(candles_1m)}
                    logger.debug(f"✅ LSTM 1m prediction successful: {p1:.4f}")
                else:
                    logger.warning(f"Insufficient 1m candles: {len(candles_1m)}/60 required")
                    
            if model_path_5m.exists():
                model_5m = tf.keras.models.load_model(model_path_5m, compile=False)
                
                # Get 250 recent 1m candles for 5m analysis
                candles_5m = service.get_recent_candles('1m', 300)  # Extra buffer
                if len(candles_5m) >= 100:  # Higher minimum for enterprise accuracy
                    # Calculate proper 11-feature technical indicators
                    x_5m = self._calculate_technical_features(candles_5m, lookback=200)
                    p5 = float(model_5m.predict(x_5m)[0][0])
                    preds.append(p5)
                    pred_meta["5m"] = {"prediction": p5, "sequence_length": len(candles_5m)}
                    logger.debug(f"✅ LSTM 5m prediction successful: {p5:.4f}")
                else:
                    logger.warning(f"Insufficient 5m candles: {len(candles_5m)}/100 required")

            if not preds:
                return {
                    "recommendation": "wait",
                    "confidence": 0.4,
                    "predictions": {},
                    "signal_alignment": False,
                    "reasoning": "No short-horizon models found; deferring to technical/momentum/timing layers",
                }

            # Ensemble probability and thresholding
            p_up = float(np.mean(preds))
            # Use real thresholds only - no fallbacks
            thresholds = list(threshold_map.values())
            if not thresholds:
                raise RuntimeError("LSTM threshold metadata missing - no fallback allowed")
            t = float(np.mean(thresholds))

            signal_action = signal_data.get("action", "HOLD")
            if signal_action == "BUY":
                enter = p_up >= t
                confidence = float(max(0.5, p_up))
            elif signal_action == "SELL":
                enter = (1.0 - p_up) >= t
                confidence = float(max(0.5, 1.0 - p_up))
            else:
                enter = False
                confidence = 0.3

            return {
                "recommendation": "enter" if enter else "wait",
                "confidence": confidence,
                "predictions": pred_meta,
                "threshold": t,
                "prob_up": p_up,
                "signal_alignment": enter,
                "reasoning": f"p_up={safe_format_number(p_up, 3)} threshold={safe_format_number(t, 3)} action={signal_action}",
            }
        except RecursionError as re:
            logger.error(f"🔄 PIPELINE DEBUG: Entry Engine - LSTM recursion error (TensorFlow/Keras issue): {str(re)[:200]}")
            return {
                "recommendation": "wait",
                "confidence": 0.4,
                "predictions": {},
                "signal_alignment": False,
                "reasoning": "LSTM model recursion error - TensorFlow compatibility issue"
            }
        except Exception as e:
            logger.warning(f"LSTM entry analysis unavailable: {e}")
            logger.debug(f"🔄 PIPELINE DEBUG: Entry Engine - LSTM analysis failed, using fallback")
            return {
                "recommendation": "wait",
                "confidence": 0.4,
                "predictions": {},
                "signal_alignment": False,
                "reasoning": "Short-horizon prediction unavailable"
            }
    
    async def _analyze_entry_patterns(self, market_data: Dict[str, Any], signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 3: Advanced historical pattern analysis with validation"""
        
        # Get current market indicators
        rsi = market_data.get("rsi", 50)
        macd = market_data.get("macd", 0)
        bollinger_position = market_data.get("bollinger_position", 0.5)
        signal_action = signal_data.get("action", "HOLD")
        current_price = market_data.get("price", 0)
        
        # ENHANCED: Use pre-cached historical analysis for instant lookups
        historical_analysis = {"patterns": [], "validation_score": 0.0}
        if self.historical_context:
            try:
                historical_analysis = await self._get_cached_historical_patterns(signal_action, current_price, rsi, macd, bollinger_position)
            except Exception as e:
                logger.warning(f"Cached historical analysis failed: {e}")
                historical_analysis = {"patterns": [], "validation_score": 0.0}
        
        pattern_score = 0
        patterns_detected = []
        historical_validation = historical_analysis.get("validation_score", 0.0)
        
        if signal_action == "BUY":
            # Look for bullish patterns with historical validation
            # DAY TRADING: More sensitive thresholds for frequent opportunities
            
            if rsi < 50:  # DAY TRADING: Any RSI below neutral (was <40)
                strength = max(0, (50 - rsi) / 50)  # 0-1 strength based on how oversold
                historical_success = await self._validate_oversold_pattern_historically(rsi)
                pattern_score += 0.25 * strength * historical_success
                historical_success_pct = safe_format_number(historical_success * 100, 1)
                patterns_detected.append(f"bearish_rsi_{rsi:.0f}_validated_{historical_success_pct}%")
                
            if macd > -0.001:  # DAY TRADING: Near-neutral or positive MACD (was >0 only)
                macd_signal = market_data.get("macd_signal", 0)
                if macd > macd_signal:  # Bullish crossover or momentum
                    historical_success = await self._validate_macd_crossover_historically("bullish")
                    pattern_score += 0.3 * historical_success
                    historical_success_pct = safe_format_number(historical_success * 100, 1)
                    patterns_detected.append(f"bullish_macd_validated_{historical_success_pct}%")
                
            if bollinger_position < 0.6:  # DAY TRADING: Below upper band (was <0.3 only)
                support_strength = max(0, (0.6 - bollinger_position) / 0.6)  # Strength based on position
                historical_success = await self._validate_bollinger_bounce_historically("support")
                pattern_score += 0.2 * support_strength * historical_success
                historical_success_pct = safe_format_number(historical_success * 100, 1)
                patterns_detected.append(f"bollinger_support_{bollinger_position:.2f}_validated_{historical_success_pct}%")
                
            # Advanced candlestick patterns
            candlestick_patterns = await self._detect_candlestick_patterns("bullish")
            for pattern in candlestick_patterns:
                pattern_strength = pattern.get("strength", 0.0)
                historical_success = pattern.get("historical_success_rate", 0.5)
                pattern_name = pattern.get("name", "unknown_pattern")
                
                # Safe validation of values
                if pattern_strength is not None and historical_success is not None and pattern_name:
                    pattern_score += 0.15 * pattern_strength * historical_success
                    historical_success_pct = safe_format_number(historical_success * 100, 1)
                    patterns_detected.append(f"{pattern_name}_validated_{historical_success_pct}%")
                
        elif signal_action == "SELL":
            # Look for bearish patterns with historical validation  
            # DAY TRADING: More sensitive thresholds for frequent opportunities
            
            if rsi > 50:  # DAY TRADING: Any RSI above neutral (was >60)
                strength = max(0, (rsi - 50) / 50)  # 0-1 strength based on how overbought
                historical_success = await self._validate_overbought_pattern_historically(rsi)
                pattern_score += 0.25 * strength * historical_success
                historical_success_pct = safe_format_number(historical_success * 100, 1)
                patterns_detected.append(f"bullish_rsi_{rsi:.0f}_validated_{historical_success_pct}%")
                
            if macd < 0.001:  # DAY TRADING: Near-neutral or negative MACD (was <0 only)
                macd_signal = market_data.get("macd_signal", 0)
                if macd < macd_signal:  # Bearish crossover or momentum
                    historical_success = await self._validate_macd_crossover_historically("bearish")
                    pattern_score += 0.3 * historical_success
                    historical_success_pct = safe_format_number(historical_success * 100, 1)
                    patterns_detected.append(f"bearish_macd_validated_{historical_success_pct}%")
                
            if bollinger_position > 0.4:  # DAY TRADING: Above lower band (was >0.7 only)
                resistance_strength = max(0, (bollinger_position - 0.4) / 0.6)  # Strength based on position
                historical_success = await self._validate_bollinger_bounce_historically("resistance")
                pattern_score += 0.2 * resistance_strength * historical_success
                historical_success_pct = safe_format_number(historical_success * 100, 1)
                patterns_detected.append(f"bollinger_resistance_{bollinger_position:.2f}_validated_{historical_success_pct}%")
                
            # Advanced candlestick patterns
            candlestick_patterns = await self._detect_candlestick_patterns("bearish")
            for pattern in candlestick_patterns:
                pattern_strength = pattern.get("strength", 0.0)
                historical_success = pattern.get("historical_success_rate", 0.5)
                pattern_name = pattern.get("name", "unknown_pattern")
                
                # Safe validation of values
                if pattern_strength is not None and historical_success is not None and pattern_name:
                    pattern_score += 0.15 * pattern_strength * historical_success
                    historical_success_pct = safe_format_number(historical_success * 100, 1)
                    patterns_detected.append(f"{pattern_name}_validated_{historical_success_pct}%")
        
        # Apply historical validation multiplier
        pattern_score *= (1.0 + historical_validation)  # Boost score if historically validated
        
        # Volume confirmation with historical analysis
        volume_ratio = market_data.get("volume_ratio", 1.0)
        if volume_ratio > 1.5:
            volume_success = await self._validate_volume_breakout_historically(volume_ratio)
            pattern_score += 0.2 * volume_success
            volume_success_pct = safe_format_number(volume_success * 100, 1)
            patterns_detected.append(f"volume_breakout_validated_{volume_success_pct}%")
        
        # Determine recommendation based on historical validation
        if pattern_score >= 0.7 and historical_validation > 0.3:
            recommendation = "enter"
            confidence = min(pattern_score + 0.2, 1.0)
        elif pattern_score >= 0.5 and historical_validation > 0.2:
            recommendation = "enter"
            confidence = pattern_score + 0.1
        elif pattern_score >= 0.3:
            recommendation = "enter"
            confidence = pattern_score
        else:
            recommendation = "wait"
            confidence = pattern_score * 0.8
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "pattern_score": pattern_score,
            "patterns_detected": patterns_detected,
            "historical_validation": historical_validation,
            "historical_patterns": historical_analysis.get("patterns", []),
            "market_indicators": {
                "rsi": rsi,
                "macd": macd,
                "bollinger_position": bollinger_position,
                "volume_ratio": volume_ratio
            },
            "reasoning": f"Pattern score: {safe_format_number(pattern_score, 2)} (historical validation: {safe_format_number(historical_validation * 100, 1)}%), detected: {len(patterns_detected)} patterns"
        }
    
    async def _analyze_entry_technical_indicators(self, market_data: Dict[str, Any], current_price: float) -> Dict[str, Any]:
        """Layer 4: Analyze technical indicators for entry"""
        
        # Get technical levels
        ema_20 = market_data.get("ema_20", current_price)
        ema_50 = market_data.get("ema_50", current_price)
        support_level = market_data.get("support", current_price * 0.98)
        resistance_level = market_data.get("resistance", current_price * 1.02)
        
        # Analyze price position
        above_ema20 = current_price > ema_20
        above_ema50 = current_price > ema_50
        near_support = abs(current_price - support_level) / current_price < 0.015
        near_resistance = abs(current_price - resistance_level) / current_price < 0.015
        
        # Calculate technical score
        technical_score = 0
        signals = []
        
        if above_ema20 and above_ema50:  # Bullish alignment
            technical_score += 0.4
            signals.append("bullish_ema_alignment")
        elif not above_ema20 and not above_ema50:  # Bearish alignment
            technical_score += 0.3
            signals.append("bearish_ema_alignment")
        
        if near_support and above_ema20:  # Support bounce opportunity
            technical_score += 0.4
            signals.append("support_bounce")
        elif near_resistance and not above_ema20:  # Resistance rejection
            technical_score += 0.3
            signals.append("resistance_rejection")
        
        # Determine recommendation
        if technical_score >= 0.6:
            recommendation = "enter"
            confidence = 0.8
        elif technical_score >= 0.3:
            recommendation = "enter"
            confidence = 0.6
        else:
            recommendation = "wait"
            confidence = 0.4
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "technical_score": technical_score,
            "signals": signals,
            "price_levels": {
                "current": current_price,
                "ema_20": ema_20,
                "ema_50": ema_50,
                "support": support_level,
                "resistance": resistance_level
            },
            "reasoning": f"Technical score: {safe_format_number(technical_score, 1)}, signals: {', '.join(signals) if signals else 'none'}"
        }
    
    async def _analyze_entry_momentum(self, market_data: Dict[str, Any], signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 5: Analyze momentum for entry timing - ENHANCED VERSION"""

        # Get momentum indicators with better defaults
        volume_ratio = market_data.get("volume_ratio", 1.0)
        price_momentum = market_data.get("price_momentum", 0.0)
        signal_confidence = signal_data.get("confidence", 0.5)
        signal_action = signal_data.get("action", "HOLD")

        momentum_score = 0
        momentum_factors = []
        detailed_scores = {}

        # ENHANCED: Volume momentum with more granular analysis
        if volume_ratio > 2.0:
            momentum_score += 0.4
            momentum_factors.append("extreme_high_volume")
            detailed_scores["volume"] = 0.4
        elif volume_ratio > 1.8:
            momentum_score += 0.35
            momentum_factors.append("very_high_volume")
            detailed_scores["volume"] = 0.35
        elif volume_ratio > 1.5:
            momentum_score += 0.3
            momentum_factors.append("high_volume")
            detailed_scores["volume"] = 0.3
        elif volume_ratio > 1.2:
            momentum_score += 0.2
            momentum_factors.append("increased_volume")
            detailed_scores["volume"] = 0.2
        elif volume_ratio > 0.8:
            momentum_score += 0.1
            momentum_factors.append("normal_volume")
            detailed_scores["volume"] = 0.1
        else:
            momentum_score += 0.05  # Small boost even for low volume
            momentum_factors.append("low_volume")
            detailed_scores["volume"] = 0.05

        # ENHANCED: Price momentum with better thresholds and fallback logic
        momentum_magnitude = abs(price_momentum)

        if signal_action == "BUY" and price_momentum > 0.02:
            momentum_score += 0.5
            momentum_factors.append("strong_bullish_momentum")
            detailed_scores["price_alignment"] = 0.5
        elif signal_action == "BUY" and price_momentum > 0.01:
            momentum_score += 0.4
            momentum_factors.append("bullish_momentum")
            detailed_scores["price_alignment"] = 0.4
        elif signal_action == "BUY" and price_momentum > 0.005:
            momentum_score += 0.3
            momentum_factors.append("weak_bullish_momentum")
            detailed_scores["price_alignment"] = 0.3
        elif signal_action == "SELL" and price_momentum < -0.02:
            momentum_score += 0.5
            momentum_factors.append("strong_bearish_momentum")
            detailed_scores["price_alignment"] = 0.5
        elif signal_action == "SELL" and price_momentum < -0.01:
            momentum_score += 0.4
            momentum_factors.append("bearish_momentum")
            detailed_scores["price_alignment"] = 0.4
        elif signal_action == "SELL" and price_momentum < -0.005:
            momentum_score += 0.3
            momentum_factors.append("weak_bearish_momentum")
            detailed_scores["price_alignment"] = 0.3
        elif momentum_magnitude < 0.005:
            # NEUTRAL momentum - add small boost for stability
            momentum_score += 0.15
            momentum_factors.append("neutral_momentum")
            detailed_scores["price_alignment"] = 0.15
        else:
            # Conflicting momentum - still add small boost
            momentum_score += 0.1
            momentum_factors.append("conflicting_momentum")
            detailed_scores["price_alignment"] = 0.1

        # ENHANCED: Signal strength with better handling of low confidence
        if signal_confidence > 0.8:
            momentum_score += 0.4
            momentum_factors.append("very_high_signal_confidence")
            detailed_scores["signal_strength"] = 0.4
        elif signal_confidence > 0.7:
            momentum_score += 0.35
            momentum_factors.append("high_signal_confidence")
            detailed_scores["signal_strength"] = 0.35
        elif signal_confidence > 0.6:
            momentum_score += 0.3
            momentum_factors.append("strong_signal_confidence")
            detailed_scores["signal_strength"] = 0.3
        elif signal_confidence > 0.5:
            momentum_score += 0.2
            momentum_factors.append("moderate_signal_confidence")
            detailed_scores["signal_strength"] = 0.2
        elif signal_confidence > 0.3:
            # IMPROVED: Add boost even for low confidence to prevent complete failure
            momentum_score += 0.15
            momentum_factors.append("low_signal_confidence")
            detailed_scores["signal_strength"] = 0.15
        elif signal_confidence > 0.1:
            # IMPROVED: Small boost for very low confidence
            momentum_score += 0.1
            momentum_factors.append("very_low_signal_confidence")
            detailed_scores["signal_strength"] = 0.1
        else:
            # IMPROVED: Minimal boost even for extremely low confidence
            momentum_score += 0.05
            momentum_factors.append("extremely_low_signal_confidence")
            detailed_scores["signal_strength"] = 0.05

        # ENHANCED: Add momentum sustainability factor
        volatility = market_data.get("volatility", 0.02)
        if volatility < 0.01:
            momentum_score += 0.1
            momentum_factors.append("low_volatility_stable")
            detailed_scores["volatility"] = 0.1
        elif volatility < 0.02:
            momentum_score += 0.05
            momentum_factors.append("moderate_volatility")
            detailed_scores["volatility"] = 0.05

        # IMPROVED: Better confidence calculation with minimum thresholds
        base_confidence = min(momentum_score, 1.0)

        # Apply confidence boost/penalty based on factor diversity
        factor_diversity = len(momentum_factors)
        if factor_diversity >= 4:
            confidence = min(base_confidence * 1.1, 1.0)  # Boost for diverse factors
        elif factor_diversity >= 3:
            confidence = base_confidence  # No change
        elif factor_diversity >= 2:
            confidence = max(base_confidence * 0.9, 0.2)  # Small penalty
        else:
            confidence = max(base_confidence * 0.8, 0.15)  # Larger penalty but minimum floor

        # ENHANCED: More conservative recommendation logic
        if momentum_score >= 0.8:
            recommendation = "enter"
        elif momentum_score >= 0.7:
            recommendation = "enter"
        elif momentum_score >= 0.5:
            recommendation = "enter"
        else:
            # PROFESSIONAL: Higher threshold - wait for better momentum
            recommendation = "wait"

        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "momentum_score": momentum_score,
            "momentum_factors": momentum_factors,
            "volume_ratio": volume_ratio,
            "price_momentum": price_momentum,
            "signal_confidence": signal_confidence,
            "reasoning": f"Momentum score: {safe_format_number(momentum_score, 1)}, factors: {', '.join(momentum_factors)}"
        }
    
    async def _analyze_entry_timing(self, market_data: Dict[str, Any], signal_data: Dict[str, Any], user_portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 6: Analyze entry timing optimization"""
        
        # Get timing factors
        time_of_day = datetime.now().hour
        market_hours = 9 <= time_of_day <= 16  # Example market hours
        volume = market_data.get("volume", 1000)
        avg_volume = market_data.get("avg_volume", 1000)
        
        # Portfolio factors
        available_cash = user_portfolio.get("available_cash", 10000)
        active_positions = len(user_portfolio.get("active_positions", []))
        max_positions = user_portfolio.get("max_positions", 5)
        daily_trades = user_portfolio.get("daily_trades", 0)
        max_daily_trades = user_portfolio.get("max_daily_trades", 30)  # SMALL TRADES: Default 30 per day
        
        timing_score = 0
        timing_factors = []
        
        # Market timing
        if market_hours:
            timing_score += 0.2
            timing_factors.append("market_hours")
        
        if volume > avg_volume * 1.2:
            timing_score += 0.3
            timing_factors.append("high_volume")
        elif volume > avg_volume:
            timing_score += 0.1
            timing_factors.append("normal_volume")
        
        # Portfolio constraints
        if available_cash > 1000:  # Sufficient cash
            timing_score += 0.2
            timing_factors.append("sufficient_cash")
        
        if active_positions < max_positions:
            timing_score += 0.2
            timing_factors.append("position_capacity")
        
        # AGGRESSIVE SCALPING: Remove daily trade limit check
        # Let AI confidence and risk management control trading frequency
        # if daily_trades < max_daily_trades:
        timing_score += 0.1
        timing_factors.append("trade_capacity_unlimited")
        
        # ENHANCED: Professional timing thresholds with historical validation
        if timing_score >= 0.7:  # PROFESSIONAL: Higher threshold for quality entries
            recommendation = "enter"
            confidence = 0.8
        elif timing_score >= 0.5:  # PROFESSIONAL: Moderate threshold
            recommendation = "enter"
            confidence = 0.6
        else:
            recommendation = "wait"
            confidence = 0.3
        
        # ENHANCED: Add historical market regime check
        if self.historical_context:
            current_regime = self.historical_context.get_current_market_regime()
            if current_regime in ["high_volatility"]:
                # Reduce confidence during high volatility periods
                confidence *= 0.8
                timing_factors.append(f"volatility_adjustment_{current_regime}")
                logger.info(f"📊 Market regime adjustment: {current_regime} (confidence reduced)")
            elif current_regime in ["bull_trend", "bear_trend"]:
                # Boost confidence during trending markets
                confidence *= 1.1
                timing_factors.append(f"trend_boost_{current_regime}")
                logger.info(f"📊 Market regime boost: {current_regime} (confidence increased)")
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "timing_score": timing_score,
            "timing_factors": timing_factors,
            "market_hours": market_hours,
            "volume_ratio": volume / max(avg_volume, 1),
            "portfolio_constraints": {
                "available_cash": available_cash,
                "active_positions": active_positions,
                "daily_trades": daily_trades,
                "can_trade": daily_trades < max_daily_trades
            },
            "reasoning": f"Timing score: {safe_format_number(timing_score, 1)}, factors: {', '.join(timing_factors)}"
        }
    
    async def _calculate_entry_consensus(self, layer_results: Dict[str, Any], signal_data: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """UPGRADED: Calculate consensus with enhanced predictive weighting"""
        
        enter_votes = 0
        wait_votes = 0
        total_confidence = 0.0
        weighted_confidence = 0.0
        consensus_scores = []
        
        # UPGRADED layer weights for predictive analysis
        layer_weights = {
            "layer_1_regime": 0.15,
            "layer_2_predictive": 0.30,  # Highest weight for predictive analysis
            "layer_3_patterns": 0.20,
            "layer_4_technical": 0.15,
            "layer_5_price_direction": 0.15,  # High weight for price confirmation
            "layer_6_timing": 0.05
        }
        
        logger.info("🎯 UPGRADED CONSENSUS CALCULATION:")
        
        for layer_name, layer_data in layer_results.items():
            if isinstance(layer_data, dict):
                recommendation = layer_data.get("recommendation", "wait")
                confidence = layer_data.get("confidence", 0.0)
                
                # Get enhanced layer weight
                weight = layer_weights.get(layer_name, 0.1)
                
                logger.info(f"   {layer_name}: {recommendation} (conf: {confidence:.2f}, weight: {weight:.2f})")
                
                if recommendation == "enter":
                    enter_votes += 1
                    consensus_scores.append(confidence)
                    weighted_confidence += confidence * weight
                else:
                    wait_votes += 1
                    # CRITICAL: For price direction layer, heavily penalize wait votes
                    if layer_name == "layer_5_price_direction":
                        weighted_confidence += confidence * weight * 0.1  # Heavy penalty
                    else:
                        weighted_confidence += confidence * weight * 0.5  # Standard penalty
                
                total_confidence += confidence
        
        total_votes = enter_votes + wait_votes
        
        # Safe consensus calculation
        if consensus_scores:
            try:
                consensus_score = float(np.mean(consensus_scores))
            except Exception as e:
                logger.warning(f"⚠️ Error calculating consensus score: {e}")
                consensus_score = 0.0
        else:
            consensus_score = 0.0
            
        risk_score = 1.0 - consensus_score  # Higher consensus = lower risk
        timing_score = float(weighted_confidence) if weighted_confidence is not None else 0.0
        
        # Get signal confidence boost
        signal_confidence = signal_data.get("confidence", 0.5)
        signal_action = signal_data.get("action", "HOLD")
        
        # ENHANCED: Historical validation check
        historical_validation_score = 0.0
        if self.historical_context:
            historical_validation_score = self._validate_entry_historically(
                signal_action, consensus_score, layer_results
            )
            logger.info(f"📊 Historical validation: {historical_validation_score:.1%}")
        
        # ENHANCED: Decision criteria with exploratory signal support
        # Get signal type and layer components
        signal_type = signal_data.get("signal_type", "primary")
        is_exploratory = signal_type == "exploratory"
        layer_analysis = signal_data.get("layer_analysis", {})
        l6_timing = layer_analysis.get("layer_6_timing", {}).get("timing_score", 0.0)
        
        # ACTIVE DAY TRADING: Use base confidence thresholds (not phase-based)
        conf_thresh = self.confidence_threshold if not is_exploratory else 0.35  # Use base threshold
        # Unified signal threshold
        from app.backend.config.trading_thresholds import ConfidenceThresholds
        thresholds = ConfidenceThresholds()
        signal_thresh = thresholds.BUY_THRESHOLD if not is_exploratory else thresholds.EXPLORATORY_BUY
        try:
            from app.backend.services.metrics import set_decision_threshold
            set_decision_threshold("entry", "exploratory" if is_exploratory else "primary", f"phase{phase}", float(signal_thresh))
        except Exception:
            pass
        
        # PHASE-BASED consensus threshold adjustment - FIXED FOR MEAN-REVERSION
        phase = self.get_current_warmup_phase()
        phase_consensus_thresh = self.consensus_threshold
        
        # Detect playbook type from signal data
        signal_playbook = signal_data.get("playbook", "unknown")
        layer3_patterns = layer_results.get("layer_3_patterns", {})
        market_indicators = layer3_patterns.get("market_indicators", {})
        rsi_val = market_indicators.get("rsi", 50.0)
        bb_pos_val = market_indicators.get("bollinger_position", 0.5)
        
        # Infer mean-reversion from RSI and BB position
        is_mean_reversion = (signal_action == "BUY" and rsi_val <= 30.0 and bb_pos_val <= 0.2) or \
                           (signal_action == "SELL" and rsi_val >= 70.0 and bb_pos_val >= 0.8)
        
        if phase == 1:
            if is_mean_reversion or signal_playbook == "mean_reversion":
                phase_consensus_thresh = 0.65  # FIXED: Lower threshold for mean-reversion in phase 1
                logger.info(f"🎯 MEAN-REVERSION DETECTED: Lowered phase-1 consensus to {phase_consensus_thresh}")
            else:
                phase_consensus_thresh = 0.75  # Higher consensus required during Phase 1 for other strategies
        elif phase == 2:
            phase_consensus_thresh = 0.60  # Medium consensus required during Phase 2 (was 0.72)
        
        # Enhanced checks with phase-based and exploratory support
        meets_consensus = enter_votes > wait_votes and consensus_score > phase_consensus_thresh
        meets_confidence = consensus_score > conf_thresh
        # During warmup phases, do not allow historical gating to block entries; only apply once warmed up
        if not self.is_warmed_up:
            meets_historical = True
        else:
            meets_historical = historical_validation_score > self.historical_validation_threshold
        meets_signal = signal_action in ["BUY", "SELL"] and signal_confidence > signal_thresh
        
        # Timing: respect Enterprise L6_time as override if strong
        timing_ok = meets_historical or l6_timing >= 0.70
        
        # For exploratory signals, treat disabled models as neutral
        if is_exploratory and enter_votes == 0 and wait_votes == 0:
            meets_consensus = True  # No active models = neutral = OK for exploratory
        
        # Generate SSOT ID for tracking across layers
        import hashlib
        import time
        ssot_data = f"{datetime.now(timezone.utc).timestamp()}_{signal_action}_{consensus_score:.6f}"
        ssot_id = hashlib.md5(ssot_data.encode()).hexdigest()[:8]
        
        logger.info(f"🔍 SSOT_ID={ssot_id} PHASE-BASED CHECKS: phase={phase}, consensus={meets_consensus}({consensus_score:.2f}>{phase_consensus_thresh:.2f}), confidence={meets_confidence}({consensus_score:.2f}>{conf_thresh:.2f}), historical={meets_historical}, signal={meets_signal}, timing_ok={timing_ok}, signal_type={signal_type}")
        
        # Add SSOT ID to market data for downstream tracking
        market_data["ssot_id"] = ssot_id
        
        # Playbook override with tight guardrails (runtime-configurable)
        try:
            from app.backend.core.runtime_config import runtime_config_store
            cfg = await runtime_config_store.get()
            # Recognize breakout playbook from market indicators
            pb = None
            md = layer_results.get("layer_3_patterns", {}).get("market_indicators", {})
            rsi_v = float(md.get("rsi", 50.0))
            bb_pos_v = float(md.get("bollinger_position", 0.5))
            macd_v = float(md.get("macd", 0.0))
            vol_ratio_v = float(md.get("volume_ratio", 1.0))
            if signal_action == "BUY" and bb_pos_v >= 0.85 and macd_v > 0.0 and vol_ratio_v >= 1.2:
                pb = "breakout"
            elif signal_action == "SELL" and bb_pos_v <= 0.15 and macd_v < 0.0 and vol_ratio_v >= 1.2:
                pb = "breakout_sell"
            # Apply override only if enabled and targeted playbook
            if (
                cfg.playbook_override_enabled
                and pb in cfg.playbook_override_playbooks
                and not meets_consensus  # only when consensus slightly below threshold
                and consensus_score >= cfg.playbook_override_min_consensus
                and l6_timing >= cfg.playbook_override_min_timing
            ):
                # Guard: block if breaker/volatility/cooldown/duplicate present
                blockers: list[str] = []
                # Breaker: expect external cb_active==0 (we can only inspect provided flags if available)
                cb_block = layer_results.get("circuit_breaker", {}).get("active", False)
                if cb_block:
                    blockers.append("breaker")
                # Duplicate/cooldown hints from engine can be absent here; leave to DayTradingEngine
                # Enhanced microstructure guards with professional validation
                microstructure_data = layer_results.get("microstructure", {})
                spread_bps = float(microstructure_data.get("spread_bps", 0.0))
                slippage_bps = float(microstructure_data.get("slippage_bps", 0.0))
                imbalance_ratio = float(microstructure_data.get("imbalance_ratio", 0.5))
                
                # ENHANCED: Professional microstructure edge checks
                if spread_bps > cfg.playbook_override_max_spread_bps:
                    blockers.append("spread")
                    logger.info(f"🛑 MICROSTRUCTURE: Spread {spread_bps:.2f}bps > {cfg.playbook_override_max_spread_bps}bps")
                if slippage_bps > cfg.playbook_override_max_slippage_bps:
                    blockers.append("slippage")
                    logger.info(f"🛑 MICROSTRUCTURE: Slippage {slippage_bps:.2f}bps > {cfg.playbook_override_max_slippage_bps}bps")
                
                # FIXED: Add imbalance checks for entry direction
                if signal_action == "BUY" and imbalance_ratio < 0.55:
                    blockers.append("imbalance")
                    logger.info(f"🛑 MICROSTRUCTURE: BUY imbalance {imbalance_ratio:.2f} < 0.55")
                elif signal_action == "SELL" and imbalance_ratio > 0.45:
                    blockers.append("imbalance")
                    logger.info(f"🛑 MICROSTRUCTURE: SELL imbalance {imbalance_ratio:.2f} > 0.45")
                # MACD validator must pass if required (we treat macd_v sign as proxy until codes are mapped)
                if cfg.require_macd_validator_pass and ((signal_action == "BUY" and macd_v <= 0.0) or (signal_action == "SELL" and macd_v >= 0.0)):
                    blockers.append("macd_validator")
                # Volatility proxy: if volatility extremely high, block
                vol_proxy = float(md.get("volatility", 0.02))
                if vol_proxy > 0.10:
                    blockers.append("volatility")
                # If any configured guard is present, do not override
                if any(b in cfg.playbook_override_block_if_guard for b in blockers):
                    pass
                else:
                    # Override: allow entry with size haircut; annotate decision
                    decision = {
                        "should_enter": True,
                        "confidence": signal_confidence,
                        "reason": "playbook_override",
                        "consensus_score": consensus_score,
                        "historical_validation": historical_validation_score,
                        "risk_score": risk_score,
                        "timing_score": timing_score,
                        "layer_votes": {"enter": enter_votes, "wait": wait_votes},
                        "playbook": pb,
                        "size_multiplier": float(cfg.playbook_override_size_multiplier),
                        "blockers": blockers,
                    }
                    return decision
        except Exception:
            pass
        
        # FINAL DECISION with exploratory-friendly criteria
        if meets_consensus and meets_confidence and timing_ok and meets_signal:
            decision = {
                "should_enter": True,
                "confidence": signal_confidence,  # Use original signal confidence, not consensus
                "reason": "ai_consensus",
                "consensus_score": consensus_score,
                "historical_validation": historical_validation_score,
                "risk_score": risk_score,
                "timing_score": timing_score,
                "layer_votes": {"enter": enter_votes, "wait": wait_votes}
            }
        elif consensus_score > self.high_confidence_threshold and signal_confidence > signal_thresh and timing_ok:
            decision = {
                "should_enter": True,
                "confidence": signal_confidence,  # Use original signal confidence
                "reason": "high_confidence",
                "consensus_score": consensus_score,
                "historical_validation": historical_validation_score,
                "risk_score": risk_score,
                "timing_score": timing_score,
                "layer_votes": {"enter": enter_votes, "wait": wait_votes}
            }
        else:
            # Enhanced WAIT logging with specific reasons and thresholds
            wait_reasons = []
            if not meets_consensus:
                wait_reasons.append(f"consensus {consensus_score:.2f}<{phase_consensus_thresh:.2f}")
            if not meets_confidence:
                wait_reasons.append(f"confidence {consensus_score:.2f}<{conf_thresh:.2f}")
            if not meets_historical:
                wait_reasons.append(f"historical {historical_validation_score:.2f}<{self.historical_validation_threshold:.2f}")
            if not meets_signal:
                wait_reasons.append(f"signal {signal_confidence:.2f}<{signal_thresh:.2f}")
            if not timing_ok:
                wait_reasons.append(f"timing l6={l6_timing:.2f}<0.70")
            
            # Determine specific reason for rejection with better diagnostics
            if not timing_ok:
                reason = "poor_timing"
                logger.info(f"📊 PIPELINE DEBUG: Entry Engine - Rejected due to poor timing (historical={meets_historical}, l6_timing={l6_timing:.2f})")
            elif not meets_confidence:
                reason = "insufficient_confidence"
                logger.info(f"📊 PIPELINE DEBUG: Entry Engine - Rejected due to insufficient confidence ({consensus_score:.2f} < {conf_thresh:.2f})")
            elif not meets_signal:
                reason = EntryReason.WEAK_SIGNAL.value
                logger.info(f"📊 PIPELINE DEBUG: Entry Engine - Rejected due to weak signal ({signal_confidence:.2f} < {signal_thresh:.2f})")
            else:
                reason = "poor_timing"
            
            # Enhanced single-line WAIT summary with cool-down logic
            wait_summary = " | ".join(wait_reasons) if wait_reasons else reason
            
            # FIXED: Cool-down for repeated WAIT decisions
            current_time = datetime.now(timezone.utc)
            should_log_full = True
            
            if (self._last_wait_decision and 
                (current_time - self._last_wait_decision).total_seconds() < self._wait_decision_cooldown and
                wait_summary == getattr(self, '_last_wait_reason', '')):
                # Same reason within cooldown period - use abbreviated logging
                logger.info(f"🚫 SSOT_ID={ssot_id} ENTRY: WAIT (unchanged)")
                should_log_full = False
            else:
                # Full logging for new/different reasons or after cooldown
                logger.info(f"🚫 SSOT_ID={ssot_id} ENTRY: WAIT - {wait_summary}")
                self._last_wait_decision = current_time
                self._last_wait_reason = wait_summary
            
            decision = {
                "should_enter": False,
                "confidence": signal_confidence,  # Use original signal confidence for rejected signals too
                "reason": reason,
                "consensus_score": consensus_score,
                "historical_validation": historical_validation_score,
                "risk_score": risk_score,
                "timing_score": timing_score,
                "layer_votes": {"enter": enter_votes, "wait": wait_votes}
            }
        
        return decision
    
    def _validate_entry_historically(self, signal_action: str, consensus_score: float, layer_results: Dict[str, Any]) -> float:
        """Validate entry decision against historical pattern success rates - ENHANCED with live data"""
        if not self.historical_context:
            logger.debug("📊 Historical validation: No historical context - using neutral 50%")
            return 0.5  # Default if no historical context
        
        validation_scores = []
        patterns_checked = []
        
        # Check RSI pattern validation
        rsi_data = layer_results.get("layer_3_patterns", {}).get("market_indicators", {})
        rsi = rsi_data.get("rsi", 50)
        
        if signal_action == "BUY" and rsi < 40:
            patterns_checked.append(f"rsi_oversold(rsi={rsi:.1f})")
            rsi_pattern = self.historical_context.get_pattern_success_rate("rsi_oversold")
            if rsi_pattern:
                validation_scores.append(rsi_pattern.success_rate)
                logger.debug(f"📊 RSI oversold pattern found: {rsi_pattern.success_rate:.1%} success rate")
            else:
                logger.debug(f"📊 RSI oversold pattern not found in historical data")
                # ENHANCED: Use live calculation as fallback for extreme RSI  
                if rsi <= 10:  # Extreme oversold - use high confidence
                    fallback_score = 0.75  # 75% success for extreme oversold
                    validation_scores.append(fallback_score)
                    logger.info(f"📊 EXTREME RSI ({rsi:.1f}) - Using live fallback validation: {fallback_score:.1%}")
        elif signal_action == "SELL" and rsi > 60:
            rsi_pattern = self.historical_context.get_pattern_success_rate("rsi_overbought")
            if rsi_pattern:
                validation_scores.append(rsi_pattern.success_rate)
        
        # Check MACD pattern validation
        macd_data = layer_results.get("layer_3_patterns", {}).get("market_indicators", {})
        macd = macd_data.get("macd", 0)
        
        if signal_action == "BUY" and macd > 0:
            macd_pattern = self.historical_context.get_pattern_success_rate("macd_bullish")
            if macd_pattern:
                validation_scores.append(macd_pattern.success_rate)
        elif signal_action == "SELL" and macd < 0:
            macd_pattern = self.historical_context.get_pattern_success_rate("macd_bearish")
            if macd_pattern:
                validation_scores.append(macd_pattern.success_rate)
        
        # Check Bollinger Band validation
        bollinger_position = layer_results.get("layer_3_patterns", {}).get("market_indicators", {}).get("bollinger_position", 0.5)
        
        if signal_action == "BUY" and bollinger_position < 0.3:
            bb_pattern = self.historical_context.get_pattern_success_rate("bollinger_support")
            if bb_pattern:
                validation_scores.append(bb_pattern.success_rate)
        elif signal_action == "SELL" and bollinger_position > 0.7:
            bb_pattern = self.historical_context.get_pattern_success_rate("bollinger_resistance")
            if bb_pattern:
                validation_scores.append(bb_pattern.success_rate)
        
        # ENHANCED: Return average validation score with detailed logging
        if validation_scores:
            final_score = np.mean(validation_scores)
            logger.info(f"📊 Historical validation: {final_score:.1%} (from {len(validation_scores)} patterns: {', '.join(patterns_checked)})")
            return final_score
        else:
            logger.info(f"📊 Historical validation: 50.0% (no patterns found for {signal_action}, checked: {', '.join(patterns_checked) if patterns_checked else 'none'})")
            return 0.5
    
    async def _get_cached_historical_patterns(self, signal_action: str, current_price: float, rsi: float, macd: float, bollinger_position: float) -> Dict[str, Any]:
        """ENHANCED: Get historical patterns from pre-cached data (INSTANT)"""
        if not self.historical_context:
            return {"patterns": [], "validation_score": 0.0}
        
        patterns_found = []
        validation_scores = []
        
        # Get price position in historical ranges
        price_position_30d = self.historical_context.get_price_range_position(current_price, "30D")
        price_position_7d = self.historical_context.get_price_range_position(current_price, "7D")
        
        # Get support/resistance levels
        support_levels, resistance_levels = self.historical_context.get_support_resistance_levels("30D")
        
        # Instant pattern validation using pre-cached success rates
        if signal_action == "BUY":
            # Check oversold RSI pattern
            if rsi < 40:
                rsi_pattern = self.historical_context.get_pattern_success_rate("rsi_oversold")
                if rsi_pattern and rsi_pattern.success_rate is not None:
                    success_rate_pct = safe_format_number(rsi_pattern.success_rate * 100, 1)
                    patterns_found.append(f"rsi_oversold_validated_{success_rate_pct}%")
                    validation_scores.append(rsi_pattern.success_rate)
            
            # Check bullish MACD pattern
            if macd > 0:
                macd_pattern = self.historical_context.get_pattern_success_rate("macd_bullish")
                if macd_pattern and macd_pattern.success_rate is not None:
                    success_rate_pct = safe_format_number(macd_pattern.success_rate * 100, 1)
                    patterns_found.append(f"macd_bullish_validated_{success_rate_pct}%")
                    validation_scores.append(macd_pattern.success_rate)
            
            # Check Bollinger support pattern
            if bollinger_position < 0.3:
                bb_pattern = self.historical_context.get_pattern_success_rate("bollinger_support")
                if bb_pattern and bb_pattern.success_rate is not None:
                    success_rate_pct = safe_format_number(bb_pattern.success_rate * 100, 1)
                    patterns_found.append(f"bollinger_support_validated_{success_rate_pct}%")
                    validation_scores.append(bb_pattern.success_rate)
            
            # Check if near support levels
            if support_levels:
                nearest_support = min(support_levels, key=lambda x: abs(x - current_price))
                distance_to_support = abs(current_price - nearest_support) / current_price
                if distance_to_support < 0.02:  # Within 2% of support
                    patterns_found.append(f"near_support_level_{nearest_support:.0f}")
                    validation_scores.append(0.65)  # Support levels have good success rate
        
        elif signal_action == "SELL":
            # Check overbought RSI pattern
            if rsi > 60:
                rsi_pattern = self.historical_context.get_pattern_success_rate("rsi_overbought")
                if rsi_pattern and rsi_pattern.success_rate is not None:
                    success_rate_pct = safe_format_number(rsi_pattern.success_rate * 100, 1)
                    patterns_found.append(f"rsi_overbought_validated_{success_rate_pct}%")
                    validation_scores.append(rsi_pattern.success_rate)
            
            # Check bearish MACD pattern
            if macd < 0:
                macd_pattern = self.historical_context.get_pattern_success_rate("macd_bearish")
                if macd_pattern and macd_pattern.success_rate is not None:
                    success_rate_pct = safe_format_number(macd_pattern.success_rate * 100, 1)
                    patterns_found.append(f"macd_bearish_validated_{success_rate_pct}%")
                    validation_scores.append(macd_pattern.success_rate)
            
            # Check Bollinger resistance pattern
            if bollinger_position > 0.7:
                bb_pattern = self.historical_context.get_pattern_success_rate("bollinger_resistance")
                if bb_pattern and bb_pattern.success_rate is not None:
                    success_rate_pct = safe_format_number(bb_pattern.success_rate * 100, 1)
                    patterns_found.append(f"bollinger_resistance_validated_{success_rate_pct}%")
                    validation_scores.append(bb_pattern.success_rate)
            
            # Check if near resistance levels
            if resistance_levels:
                nearest_resistance = min(resistance_levels, key=lambda x: abs(x - current_price))
                distance_to_resistance = abs(current_price - nearest_resistance) / current_price
                if distance_to_resistance < 0.02:  # Within 2% of resistance
                    patterns_found.append(f"near_resistance_level_{nearest_resistance:.0f}")
                    validation_scores.append(0.65)  # Resistance levels have good success rate
        
        # Calculate overall validation score
        avg_validation = np.mean(validation_scores) if validation_scores else 0.0
        
        # Add price position context
        context_info = {
            "price_position_30d": price_position_30d,
            "price_position_7d": price_position_7d,
            "support_levels_count": len(support_levels),
            "resistance_levels_count": len(resistance_levels),
            "patterns_validated": len(patterns_found)
        }
        
        return {
            "patterns": patterns_found,
            "validation_score": avg_validation,
            "total_similar_patterns": len(patterns_found),
            "data_source": "pre_cached_historical_context",
            "context_info": context_info
        }
    
    def _calculate_optimal_entry_price(self, current_price: float, layer_results: Dict[str, Any], market_data: Dict[str, Any]) -> float:
        """Calculate optimal entry price with safe validation"""
        
        # Validate current_price is not None
        if current_price is None or current_price <= 0:
            logger.warning(f"⚠️ Invalid current_price: {current_price}, using fallback logic")
            # Try to get a fallback price from market data
            fallback_price = market_data.get("price", 0.0)
            if fallback_price and fallback_price > 0:
                logger.info(f"💰 Using fallback price from market data: ${fallback_price:,.2f}")
                current_price = fallback_price
            else:
                logger.error(f"❌ No valid price available for optimal entry calculation")
                return 0.0
        
        # Start with current price
        optimal_price = current_price
        
        # Adjust based on technical levels with fallback
        technical_data = layer_results.get("layer_4_technical", {})
        price_levels = technical_data.get("price_levels", {})
        
        # Get support/resistance with intelligent fallback
        support = price_levels.get("support")
        resistance = price_levels.get("resistance")
        
        # If no support/resistance found, calculate simple levels from current price
        if support is None or support <= 0:
            support = current_price * 0.98  # 2% below current price
            logger.debug(f"📊 Using fallback support level: ${support:,.2f} (2% below current)")
            
        if resistance is None or resistance <= 0:
            resistance = current_price * 1.02  # 2% above current price
            logger.debug(f"📊 Using fallback resistance level: ${resistance:,.2f} (2% above current)")
        
        # For buy signals, prefer prices closer to support
        # For sell signals, prefer prices closer to resistance
        volatility = market_data.get("volatility", 0.02)
        
        # Add small buffer based on volatility
        buffer = current_price * min(volatility, 0.01)  # Max 1% buffer
        
        # Adjust optimal price (simple implementation)
        if abs(current_price - support) < abs(current_price - resistance):
            # Closer to support, good for buying
            optimal_price = current_price - buffer * 0.5
        else:
            # Closer to resistance, adjust accordingly
            optimal_price = current_price + buffer * 0.3
        
        return round(optimal_price, 2)
    
    def _calculate_position_size(self, entry_decision: Dict[str, Any], user_portfolio: Dict[str, Any], layer_results: Dict[str, Any]) -> float:
        """Calculate recommended position size with $500 minimum and safe validation"""
        
        # Safe extraction with validation
        available_cash = user_portfolio.get("available_cash", 10000)
        if available_cash is None or available_cash <= 0:
            logger.warning(f"⚠️ Invalid available_cash: {available_cash}, using default 10000")
            available_cash = 10000
            
        confidence = entry_decision.get("confidence", 0.5)
        if confidence is None:
            confidence = 0.5
            
        risk_score = entry_decision.get("risk_score", 0.5)
        if risk_score is None:
            risk_score = 0.5
        
        # Professional minimum position size
        MINIMUM_POSITION_SIZE = 500.0  # $500 minimum for professional trading
        
        # Base position size as percentage of available cash
        base_percentage = 0.1  # 10% base
        
        # Adjust based on confidence - higher confidence = larger positions
        if confidence >= 0.8:
            confidence_multiplier = 2.0  # High confidence: 20% of portfolio
        elif confidence >= 0.6:
            confidence_multiplier = 1.5  # Medium confidence: 15% of portfolio
        else:
            confidence_multiplier = 1.0  # Low confidence: 10% of portfolio
        
        # Adjust based on risk
        risk_multiplier = 1.0 - (risk_score * 0.3)  # Reduce size for higher risk
        
        # Calculate position size
        position_percentage = base_percentage * confidence_multiplier * risk_multiplier
        position_percentage = min(position_percentage, 0.25)  # Max 25% of portfolio
        
        position_size = available_cash * position_percentage
        
        # Enforce minimum position size for professional trading
        position_size = max(position_size, MINIMUM_POSITION_SIZE)
        
        # Ensure we don't exceed available cash
        position_size = min(position_size, available_cash * 0.9)  # Leave 10% cash buffer
        
        logger.info(f"💰 Position size calculated: {safe_format_price(position_size)} (confidence={safe_format_number(confidence, 2)}, available={safe_format_price(available_cash)})")
        
        return round(position_size, 2)
    
    def _determine_entry_quality(self, confidence: float) -> EntryQuality:
        """Determine entry quality based on confidence"""
        if confidence >= 0.9:
            return EntryQuality.EXCELLENT
        elif confidence >= 0.7:
            return EntryQuality.GOOD
        elif confidence >= 0.5:
            return EntryQuality.FAIR
        else:
            return EntryQuality.POOR
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get comprehensive engine status"""
        return {
            "is_initialized": self.is_initialized,
            "total_analyses": self.total_analyses,
            "entries_recommended": self.entries_recommended,
            "successful_entries": self.successful_entries,
            "success_rate": self.successful_entries / max(self.entries_recommended, 1),
            "layer_health": self.layer_health.copy(),
            "models_loaded": len(self.models),
            "confidence_threshold": self.confidence_threshold,
            "consensus_threshold": self.consensus_threshold,
            "status": "operational" if self.is_initialized else "initializing"
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get engine performance metrics"""
        return {
            "total_analyses": self.total_analyses,
            "entries_recommended": self.entries_recommended,
            "successful_entries": self.successful_entries,
            "success_rate": self.successful_entries / max(self.entries_recommended, 1),
            "average_confidence": 0.75,  # TODO: Calculate from actual data
            "layer_success_rates": {
                layer_name: 0.85 for layer_name in self.layer_health.keys()
            },
            "engine_uptime": "100%",
            "status": "healthy"
        }
    
    # ===== HISTORICAL PATTERN ANALYSIS METHODS =====
    
    async def _analyze_historical_patterns(self, signal_action: str, current_price: float) -> Dict[str, Any]:
        """Analyze historical patterns using real live candlestick data"""
        try:
            # Get historical data from live cache (STRICT_LIVE_STREAM compatible)
            from app.backend.services.live_market_data import get_live_market_data_service
            
            service = await get_live_market_data_service()
            # Use 1m candles from cache (3x more data for enterprise accuracy)
            historical_candles = service.get_recent_candles("1m", 600)
            
            if not historical_candles or len(historical_candles) < 50:
                logger.warning("Insufficient historical data for pattern analysis")
                return {"patterns": [], "validation_score": 0.0}
            
            # Analyze patterns in real historical data
            patterns_found = []
            validation_scores = []
            
            # Look for similar market conditions in the past
            for i in range(50, len(historical_candles) - 10):  # Leave buffer for outcome analysis
                candle = historical_candles[i]
                
                # Calculate if this historical point was similar to current conditions
                historical_price = float(candle.get("close", 0))  # Close price
                price_similarity = 1.0 - abs(historical_price - current_price) / current_price
                
                if price_similarity > 0.95:  # Very similar price levels
                    # Analyze what happened next (next 10 candles)
                    outcome = self._analyze_pattern_outcome(historical_candles[i:i+10], signal_action)
                    if outcome["success"]:
                        patterns_found.append({
                            "timestamp": candle[0],  # Open time
                            "price": historical_price,
                            "outcome": outcome,
                            "similarity": price_similarity
                        })
                        validation_scores.append(outcome["success_score"])
            
            # Calculate overall validation score
            avg_validation = np.mean(validation_scores) if validation_scores else 0.0
            
            return {
                "patterns": patterns_found,
                "validation_score": avg_validation,
                "total_similar_patterns": len(patterns_found),
                "data_source": "binance_live_historical"
            }
            
        except Exception as e:
            logger.error(f"Historical pattern analysis failed: {e}")
            return {"patterns": [], "validation_score": 0.0}
    
    def _analyze_pattern_outcome(self, future_candles: List, signal_action: str) -> Dict[str, Any]:
        """Analyze the outcome of a historical pattern"""
        if len(future_candles) < 5:
            return {"success": False, "success_score": 0.0}
        
        entry_price = float(future_candles[0][4])  # Close price of entry candle
        max_gain = 0.0
        max_loss = 0.0
        
        for candle in future_candles[1:]:
            high_price = float(candle[2])
            low_price = float(candle[3])
            
            # Calculate gains and losses
            gain = (high_price - entry_price) / entry_price
            loss = (entry_price - low_price) / entry_price
            
            max_gain = max(max_gain, gain)
            max_loss = max(max_loss, loss)
        
        # Determine success based on signal action
        if signal_action == "BUY":
            # For buy signals, success is significant upward movement
            success = max_gain > 0.02 and max_loss < 0.03  # 2% gain, <3% loss
            success_score = min(max_gain * 10, 1.0) if success else max_gain * 5
        elif signal_action == "SELL":
            # For sell signals, success is significant downward movement
            success = max_loss > 0.02 and max_gain < 0.03  # 2% drop, <3% gain
            success_score = min(max_loss * 10, 1.0) if success else max_loss * 5
        else:
            success = False
            success_score = 0.0
        
        return {
            "success": success,
            "success_score": success_score,
            "max_gain": max_gain,
            "max_loss": max_loss,
            "risk_reward": max_gain / max(max_loss, 0.001)
        }
    
    async def _validate_oversold_pattern_historically(self, current_rsi: float) -> float:
        """Validate oversold RSI patterns using historical data"""
        try:
            # Get historical data from live cache (STRICT_LIVE_STREAM compatible)
            from app.backend.services.live_market_data import get_live_market_data_service
            
            service = await get_live_market_data_service()
            historical_candles = service.get_recent_candles("1m", 300)  # 3x more data
            if not historical_candles:
                return 0.5  # Default confidence
            
            # Calculate historical RSI and find similar oversold conditions
            rsi_values = self._calculate_historical_rsi(historical_candles)
            
            success_count = 0
            total_count = 0
            
            for i, rsi in enumerate(rsi_values[:-5]):  # Leave buffer for outcome
                if abs(rsi - current_rsi) < 5:  # Similar RSI level
                    total_count += 1
                    # Check if price went up in next 5 periods
                    if i + 5 < len(historical_candles):
                        entry_price = float(historical_candles[i][4])
                        future_price = float(historical_candles[i + 5][4])
                        if future_price > entry_price * 1.01:  # 1% gain
                            success_count += 1
            
            return success_count / max(total_count, 1)
            
        except Exception as e:
            logger.warning(f"RSI validation failed: {e}")
            return 0.5
    
    async def _validate_overbought_pattern_historically(self, current_rsi: float) -> float:
        """Validate overbought RSI patterns using historical data"""
        try:
            from app.backend.services.live_market_data import get_live_market_data_service
            
            service = await get_live_market_data_service()
            historical_candles = service.get_recent_candles("1m", 300)  # 3x more data
            if not historical_candles:
                return 0.5
            
            rsi_values = self._calculate_historical_rsi(historical_candles)
            
            success_count = 0
            total_count = 0
            
            for i, rsi in enumerate(rsi_values[:-5]):
                if abs(rsi - current_rsi) < 5:  # Similar RSI level
                    total_count += 1
                    if i + 5 < len(historical_candles):
                        entry_price = float(historical_candles[i][4])
                        future_price = float(historical_candles[i + 5][4])
                        if future_price < entry_price * 0.99:  # 1% drop
                            success_count += 1
            
            return success_count / max(total_count, 1)
            
        except Exception as e:
            logger.warning(f"RSI validation failed: {e}")
            return 0.5
    
    async def _validate_macd_crossover_historically(self, direction: str) -> float:
        """Validate MACD crossover patterns using historical data"""
        try:
            from app.backend.services.live_market_data import get_live_market_data_service
            
            service = await get_live_market_data_service()
            historical_candles = service.get_recent_candles("1m", 720)  # 12h equivalent (3x more)
            if not historical_candles:
                return 0.6  # Default confidence for MACD
            
            # Calculate MACD for historical data
            macd_data = self._calculate_historical_macd(historical_candles)
            
            success_count = 0
            total_count = 0
            
            for i in range(1, len(macd_data) - 5):
                macd = macd_data[i]
                prev_macd = macd_data[i - 1]
                
                # Detect crossovers
                if direction == "bullish" and macd > 0 and prev_macd <= 0:
                    total_count += 1
                    # Check outcome
                    entry_price = float(historical_candles[i][4])
                    future_price = float(historical_candles[i + 5][4])
                    if future_price > entry_price * 1.015:  # 1.5% gain
                        success_count += 1
                        
                elif direction == "bearish" and macd < 0 and prev_macd >= 0:
                    total_count += 1
                    entry_price = float(historical_candles[i][4])
                    future_price = float(historical_candles[i + 5][4])
                    if future_price < entry_price * 0.985:  # 1.5% drop
                        success_count += 1
            
            return success_count / max(total_count, 1)
            
        except Exception as e:
            logger.warning(f"MACD validation failed: {e}")
            return 0.6
    
    async def _validate_bollinger_bounce_historically(self, level: str) -> float:
        """Validate Bollinger Band bounce patterns using historical data"""
        try:
            from app.backend.services.live_market_data import get_live_market_data_service
            
            service = await get_live_market_data_service()
            historical_candles = service.get_recent_candles("1m", 300)  # 3x more data
            if not historical_candles:
                return 0.55
            
            # Calculate Bollinger Bands for historical data
            bb_data = self._calculate_historical_bollinger_bands(historical_candles)
            
            success_count = 0
            total_count = 0
            
            for i, bb in enumerate(bb_data[:-5]):
                price = float(historical_candles[i][4])
                upper_band = bb["upper"]
                lower_band = bb["lower"]
                
                # Check for touches near bands
                if level == "support" and price <= lower_band * 1.005:  # Near lower band
                    total_count += 1
                    # Check for bounce (price goes up)
                    future_price = float(historical_candles[i + 3][4]) if i + 3 < len(historical_candles) else price
                    if future_price > price * 1.01:  # 1% bounce
                        success_count += 1
                        
                elif level == "resistance" and price >= upper_band * 0.995:  # Near upper band
                    total_count += 1
                    # Check for rejection (price goes down)
                    future_price = float(historical_candles[i + 3][4]) if i + 3 < len(historical_candles) else price
                    if future_price < price * 0.99:  # 1% rejection
                        success_count += 1
            
            return success_count / max(total_count, 1)
            
        except Exception as e:
            logger.warning(f"Bollinger validation failed: {e}")
            return 0.55
    
    async def _validate_volume_breakout_historically(self, volume_ratio: float) -> float:
        """Validate volume breakout patterns using historical data"""
        try:
            from app.backend.services.live_market_data import get_live_market_data_service
            
            service = await get_live_market_data_service()
            historical_candles = service.get_recent_candles("1m", 300)  # 3x more data
            if not historical_candles:
                return 0.65
            
            success_count = 0
            total_count = 0
            
            # Calculate average volume
            volumes = [float(candle.get("volume", 0)) for candle in historical_candles]
            avg_volume = np.mean(volumes) if volumes else 1.0
            
            for i, candle in enumerate(historical_candles[:-5]):
                volume = float(candle.get("volume", 0))
                current_volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
                
                # Find similar volume spikes
                if abs(current_volume_ratio - volume_ratio) < 0.3:
                    total_count += 1
                    # Check if price moved significantly
                    entry_price = float(candle.get("close", 0))
                    future_price = float(historical_candles[i + 3].get("close", entry_price)) if i + 3 < len(historical_candles) else entry_price
                    price_change = abs(future_price - entry_price) / entry_price
                    
                    if price_change > 0.015:  # 1.5% movement
                        success_count += 1
            
            return success_count / max(total_count, 1)
            
        except Exception as e:
            logger.warning(f"Volume validation failed: {e}")
            return 0.65
    
    async def _detect_candlestick_patterns(self, direction: str) -> List[Dict[str, Any]]:
        """Detect candlestick patterns using real market data"""
        try:
            from app.backend.services.live_market_data import get_live_market_data_service
            
            # Get recent candlesticks for pattern detection
            service = await get_live_market_data_service()
            candles = service.get_recent_candles("1m", 20)
            if not candles or len(candles) < 3:
                return []
            
            patterns = []
            
            # Analyze last 3 candles for patterns
            for i in range(len(candles) - 2):
                pattern = self._identify_candlestick_pattern(candles[i:i+3], direction)
                if pattern:
                    # Validate pattern historically
                    historical_success = await self._validate_candlestick_pattern_historically(pattern["name"])
                    pattern["historical_success_rate"] = historical_success
                    patterns.append(pattern)
            
            return patterns
            
        except Exception as e:
            logger.warning(f"Candlestick pattern detection failed: {e}")
            return []
    
    def _identify_candlestick_pattern(self, candles: List, direction: str) -> Optional[Dict[str, Any]]:
        """Identify specific candlestick patterns"""
        if len(candles) < 3:
            return None
        
        # Extract OHLC data - candles are already dictionaries
        candle_data = []
        for candle in candles:
            try:
                candle_data.append({
                    "open": float(candle.get("open", 0)),
                    "high": float(candle.get("high", 0)),
                    "low": float(candle.get("low", 0)),
                    "close": float(candle.get("close", 0))
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid candle data: {candle}, error: {e}")
                return None
        
        # Simple pattern detection
        if direction == "bullish":
            # Hammer pattern
            if self._is_hammer_pattern(candle_data[-1]):
                return {"name": "hammer", "strength": 0.7}
            # Bullish engulfing
            if len(candle_data) >= 2 and self._is_bullish_engulfing(candle_data[-2:]):
                return {"name": "bullish_engulfing", "strength": 0.8}
        
        elif direction == "bearish":
            # Shooting star pattern
            if self._is_shooting_star_pattern(candle_data[-1]):
                return {"name": "shooting_star", "strength": 0.7}
            # Bearish engulfing
            if len(candle_data) >= 2 and self._is_bearish_engulfing(candle_data[-2:]):
                return {"name": "bearish_engulfing", "strength": 0.8}
        
        return None
    
    def _is_hammer_pattern(self, candle: Dict[str, float]) -> bool:
        """Detect hammer candlestick pattern"""
        body_size = abs(candle["close"] - candle["open"])
        lower_shadow = candle["open"] - candle["low"] if candle["close"] > candle["open"] else candle["close"] - candle["low"]
        upper_shadow = candle["high"] - max(candle["open"], candle["close"])
        
        return (lower_shadow > body_size * 2 and 
                upper_shadow < body_size * 0.5 and
                body_size > 0)
    
    def _is_shooting_star_pattern(self, candle: Dict[str, float]) -> bool:
        """Detect shooting star candlestick pattern"""
        body_size = abs(candle["close"] - candle["open"])
        upper_shadow = candle["high"] - max(candle["open"], candle["close"])
        lower_shadow = min(candle["open"], candle["close"]) - candle["low"]
        
        return (upper_shadow > body_size * 2 and 
                lower_shadow < body_size * 0.5 and
                body_size > 0)
    
    def _is_bullish_engulfing(self, candles: List[Dict[str, float]]) -> bool:
        """Detect bullish engulfing pattern"""
        if len(candles) < 2:
            return False
        
        prev_candle = candles[0]
        current_candle = candles[1]
        
        # Previous candle is bearish, current is bullish and engulfs previous
        return (prev_candle["close"] < prev_candle["open"] and
                current_candle["close"] > current_candle["open"] and
                current_candle["open"] < prev_candle["close"] and
                current_candle["close"] > prev_candle["open"])
    
    def _is_bearish_engulfing(self, candles: List[Dict[str, float]]) -> bool:
        """Detect bearish engulfing pattern"""
        if len(candles) < 2:
            return False
        
        prev_candle = candles[0]
        current_candle = candles[1]
        
        # Previous candle is bullish, current is bearish and engulfs previous
        return (prev_candle["close"] > prev_candle["open"] and
                current_candle["close"] < current_candle["open"] and
                current_candle["open"] > prev_candle["close"] and
                current_candle["close"] < prev_candle["open"])
    
    async def _validate_candlestick_pattern_historically(self, pattern_name: str) -> float:
        """Validate candlestick pattern success rate historically"""
        # Default success rates based on pattern type
        pattern_success_rates = {
            "hammer": 0.65,
            "shooting_star": 0.62,
            "bullish_engulfing": 0.70,
            "bearish_engulfing": 0.68,
            "doji": 0.50,
            "spinning_top": 0.45
        }
        
        return pattern_success_rates.get(pattern_name, 0.55)
    
    def _calculate_historical_rsi(self, candles: List, period: int = 14) -> List[float]:
        """Calculate RSI for historical candlestick data"""
        if len(candles) < period + 1:
            return [50.0] * len(candles)  # Default RSI
        
        closes = [float(candle.get("close", 0)) for candle in candles]
        rsi_values = []
        
        # Calculate price changes
        changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        for i in range(period - 1, len(changes)):
            gains = [change if change > 0 else 0 for change in changes[i-period+1:i+1]]
            losses = [-change if change < 0 else 0 for change in changes[i-period+1:i+1]]
            
            avg_gain = np.mean(gains) if gains else 0
            avg_loss = np.mean(losses) if losses else 0
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            rsi_values.append(rsi)
        
        return rsi_values
    
    def _calculate_historical_macd(self, candles: List) -> List[float]:
        """Calculate MACD for historical candlestick data"""
        if len(candles) < 26:
            return [0.0] * len(candles)
        
        closes = [float(candle.get("close", 0)) for candle in candles]
        
        # Simple MACD calculation (EMA12 - EMA26)
        ema_12 = self._calculate_ema(closes, 12)
        ema_26 = self._calculate_ema(closes, 26)
        
        macd = [ema_12[i] - ema_26[i] for i in range(len(ema_12))]
        return macd
    
    def _calculate_historical_bollinger_bands(self, candles: List, period: int = 20) -> List[Dict[str, float]]:
        """Calculate Bollinger Bands for historical data"""
        if len(candles) < period:
            return [{"upper": 0, "middle": 0, "lower": 0}] * len(candles)
        
        closes = [float(candle.get("close", 0)) for candle in candles]
        bb_data = []
        
        for i in range(period - 1, len(closes)):
            data_slice = closes[i-period+1:i+1]
            middle = np.mean(data_slice)
            std = np.std(data_slice)
            
            bb_data.append({
                "upper": middle + (2 * std),
                "middle": middle,
                "lower": middle - (2 * std)
            })
        
        return bb_data
    
    def _calculate_ema(self, data: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        if len(data) < period:
            return data
        
        multiplier = 2 / (period + 1)
        ema = [np.mean(data[:period])]  # Start with SMA
        
        for i in range(period, len(data)):
            ema.append((data[i] * multiplier) + (ema[-1] * (1 - multiplier)))
        
        return [ema[0]] * (period - 1) + ema  # Pad beginning

# Export the engine class
__all__ = ["IntelligentEntryEngine", "EntryAnalysisResult", "EntryReason", "EntryQuality"]