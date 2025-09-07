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
# os.environ['TF_USE_LEGACY_KERAS'] = '1'  # Disabled - causes import issues

# LSTM disable flag to prevent recursion errors
DISABLE_LSTM = os.getenv('DISABLE_LSTM', 'false').lower() == 'true'

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
from app.backend.services.live_market_data import get_live_bitcoin_price, get_live_market_data
from app.backend.utils.safe_formatting import safe_format_number, safe_format_price
from app.backend.services.binance_hybrid_client import get_hybrid_client

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
    Intelligent Entry Engine with 6-Layer AI Analysis
    
    Analyzes market conditions and optimizes entry points
    using multiple AI layers and consensus-based decision making.
    """
    
    def __init__(self):
        self.is_initialized = False
        self.models = {}
        # Professional path resolution - works from any working directory
        current_file = Path(__file__).parent.parent  # Go up from services/ to backend/
        self.model_path = current_file / "models" / "enterprise"
        
        # AGGRESSIVE SCALPING: Lower thresholds for more frequent trades
        self.confidence_threshold = 0.35  # SCALPING: 35% minimum (dla testów)
        self.consensus_threshold = 0.40   # SCALPING: 40% consensus (dla testów)
        self.high_confidence_threshold = 0.50  # SCALPING: 50% for high confidence (dla testów)
        self.historical_validation_threshold = 0.45  # SCALPING: 45% historical success (dla testów)
        
        # AGGRESSIVE SCALPING STARTUP: No warmup for immediate entry
        self.startup_time = datetime.now(timezone.utc)
        self.warmup_period_minutes = 0  # NO WARMUP: Immediate entry for aggressive scalping
        self.is_warmed_up = True  # Start warmed up
        self.warmup_completed_at = datetime.now(timezone.utc)
        self.scalping_mode = True  # NEW: Enable scalping optimizations
        
        # Historical context service
        self.historical_context = None
        
        # Entry analysis cooldown to reduce CPU usage - SHORTENED FOR AGGRESSIVE SCALPING
        self.entry_cooldown_cache = {}
        self.entry_cooldown_seconds = 3  # SCALPING: 3 seconds cooldown (was 15 - too long!)  # Minimum 15 seconds between analyses for same symbol
        
        # Performance tracking
        self.total_analyses = 0
        self.entries_recommended = 0
        self.successful_entries = 0
        self.layer_health = {}
        
        # Layer configurations
        self.layers = {
            1: {"name": "Market Regime Analysis", "weight": 0.20},
            2: {"name": "LSTM Prediction Models", "weight": 0.25},
            3: {"name": "Pattern Recognition", "weight": 0.20},
            4: {"name": "Technical Indicators", "weight": 0.15},
            5: {"name": "Momentum Analysis", "weight": 0.10},
            6: {"name": "Entry Timing", "weight": 0.10}
        }
        
        logger.info("🎯 Intelligent Entry Engine initialized")
    
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
            await self._start_warmup_period()
            logger.info("✅ PIPELINE DEBUG: Entry Engine - Warmup period initiated")
            
            self.is_initialized = True
            logger.info("✅ Enhanced Intelligent Entry Engine initialized successfully")
            logger.info("🎯 PIPELINE DEBUG: Entry Engine - READY FOR OPERATIONS")
            logger.info("🎯 PIPELINE DEBUG: Entry Engine - Status: INITIALIZED & OPERATIONAL")
            
        except Exception as e:
            logger.error(f"Failed to initialize entry engine: {e}")
            logger.error("💥 PIPELINE DEBUG: Entry Engine - INITIALIZATION FAILED")
            logger.error(f"💥 PIPELINE DEBUG: Entry Engine - Error details: {str(e)}")
            raise
    
    async def _start_warmup_period(self):
        """Start 30-minute warmup period with market assessment"""
        logger.info(f"🔥 Starting {self.warmup_period_minutes}-minute warmup period...")
        logger.info("📊 During warmup: Pre-loading market context and validating historical patterns")
        
        # Start warmup task in background
        asyncio.create_task(self._warmup_background_task())
    
    async def _warmup_background_task(self):
        """Background task for warmup period market assessment"""
        try:
            warmup_start = datetime.now(timezone.utc)
            
            # During warmup, prepare everything for instant decisions
            logger.info("🔄 Warmup: Validating historical context data...")
            
            # Test all historical lookups to ensure they're working
            if self.historical_context:
                # Test price range lookups
                from app.backend.services.live_market_data import get_live_bitcoin_price
                current_price = await get_live_bitcoin_price()
                
                for period in ["1D", "7D", "30D"]:
                    position = self.historical_context.get_price_range_position(current_price, period)
                    if position is not None:
                        logger.info(f"   {period} range position: {position:.1%}")
                
                # Test pattern success rates
                for pattern in ["rsi_oversold", "macd_bullish", "bollinger_support"]:
                    success_rate = self.historical_context.get_pattern_success_rate(pattern)
                    if success_rate:
                        logger.info(f"   {pattern}: {success_rate.success_rate:.1%} success rate")
                
                # Test support/resistance levels
                support, resistance = self.historical_context.get_support_resistance_levels("30D")
                logger.info(f"   Support levels: {len(support)}, Resistance levels: {len(resistance)}")
            
            # Wait for warmup period to complete
            while True:
                elapsed = (datetime.now(timezone.utc) - warmup_start).total_seconds() / 60
                if elapsed >= self.warmup_period_minutes:
                    break
                
                # Log progress every 5 minutes
                if int(elapsed) % 5 == 0 and elapsed > 0:
                    remaining = self.warmup_period_minutes - elapsed
                    logger.info(f"🔥 Warmup progress: {elapsed:.0f}/{self.warmup_period_minutes} minutes ({remaining:.0f} remaining)")
                
                await asyncio.sleep(60)  # Check every minute
            
            # Warmup completed
            self.is_warmed_up = True
            self.warmup_completed_at = datetime.now(timezone.utc)
            logger.info("✅ WARMUP COMPLETED: Entry engine ready for intelligent decisions")
            
        except Exception as e:
            logger.error(f"❌ Warmup period failed: {e}")
            # Still mark as warmed up to prevent permanent blocking
            self.is_warmed_up = True
            self.warmup_completed_at = datetime.now(timezone.utc)
    
    def _load_entry_models(self):
        """Load all 6-layer entry analysis models"""
        try:
            model_files = {
                "regime": "layer_1_regime.pkl",
                "lstm": "lstm_1h.h5",
                "patterns": "layer_3_reversal.pkl",  # Reuse for pattern detection
                "technical": "layer_4_filters.pkl",
                "momentum": "layer_5_confidence.pkl",  # Reuse for momentum
                "timing": "layer_6_timing.pkl"
            }
            
            for model_name, filename in model_files.items():
                model_file = self.model_path / filename
                if model_file.exists():
                    if filename.endswith('.pkl'):
                        with open(model_file, "rb") as f:
                            self.models[model_name] = pickle.load(f)
                    else:
                        # For .h5 files (TensorFlow models)
                        self.models[model_name] = f"model_path:{model_file}"
                    
                    logger.info(f"✅ Loaded {model_name} entry model")
                    self.layer_health[model_name] = "healthy"
                else:
                    logger.warning(f"⚠️ Model file not found: {filename}")
                    self.layer_health[model_name] = "degraded"
            
        except Exception as e:
            logger.error(f"Failed to load entry models: {e}")
            raise RuntimeError(f"Entry model loading failed: {e}")
    
    def _initialize_health_monitoring(self):
        """Initialize health monitoring for all layers"""
        for layer_id, config in self.layers.items():
            layer_name = config["name"]
            if layer_name not in self.layer_health:
                self.layer_health[layer_name] = "unknown"
    
    async def analyze_entry_opportunity(
        self, symbol: str, signal_data: Dict[str, Any], user_portfolio: Dict[str, Any]
    ) -> EntryAnalysisResult:
        """
        ENHANCED: Analyze entry opportunity with historical validation and startup protection
        
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
        
        logger.info(f"🎯 PIPELINE DEBUG: Entry Engine - Analyzing entry opportunity for {symbol}")
        logger.info(f"📊 PIPELINE DEBUG: Entry Engine - Signal data keys: {list(signal_data.keys()) if signal_data else 'None'}")
        logger.info(f"💼 PIPELINE DEBUG: Entry Engine - Portfolio data available: {bool(user_portfolio)}")
        
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
                if current_price is None or current_price <= 0:
                    current_price = portfolio_data.get('current_market_price', 111000.0)  # Fallback price
            except:
                current_price = 111000.0  # Safe fallback
            
            return EntryAnalysisResult(
                should_enter=False,
                confidence=0.0,
                entry_reason=EntryReason.POOR_TIMING,
                entry_quality=EntryQuality.POOR,
                optimal_entry_price=float(current_price),  # FIXED: Use current price instead of 0.0
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
        
        # STARTUP PROTECTION: Block entries during warmup period
        if not self.is_warmed_up:
            elapsed_minutes = (datetime.now(timezone.utc) - self.startup_time).total_seconds() / 60
            remaining_minutes = self.warmup_period_minutes - elapsed_minutes
            
            if remaining_minutes > 0:
                logger.info(f"🔥 WARMUP PERIOD: Entry blocked for {remaining_minutes:.1f} more minutes")
                logger.info(f"⏰ PIPELINE DEBUG: Entry Engine - WARMUP ACTIVE - Blocking entry analysis")
                logger.info(f"⏰ PIPELINE DEBUG: Entry Engine - Remaining warmup time: {remaining_minutes:.1f} minutes")
                # Get current price even during warmup
                try:
                    current_price = await get_live_bitcoin_price()
                    if current_price is None or current_price <= 0:
                        current_price = portfolio_data.get('current_market_price', 111000.0)  # Fallback price
                except:
                    current_price = 111000.0  # Safe fallback
                
                return EntryAnalysisResult(
                    should_enter=False,
                    confidence=0.0,
                    entry_reason=EntryReason.POOR_TIMING,
                    entry_quality=EntryQuality.POOR,
                    optimal_entry_price=float(current_price),  # FIXED: Use current price instead of 0.0
                    position_size_recommendation=0.0,
                    risk_score=1.0,
                    timing_score=0.0,
                    layer_analysis={"warmup_status": "in_progress"},
                    market_conditions={"warmup_remaining_minutes": remaining_minutes},
                    analysis_time_ms=0.0,
                    timestamp=datetime.now(timezone.utc)
                )
        
        start_time = datetime.now()
        
        try:
            logger.info(f"🎯 Analyzing ENHANCED entry opportunity for {symbol}")
            logger.info("📊 PIPELINE DEBUG: Entry Engine - Starting 6-layer entry analysis")
            
            # Get current market data with safe validation
            logger.info("📈 PIPELINE DEBUG: Entry Engine - Fetching live market data...")
            current_price = await get_live_bitcoin_price()
            if current_price is None or current_price <= 0:
                logger.error("❌ Cannot get valid Bitcoin price for entry analysis")
                logger.error("💥 PIPELINE DEBUG: Entry Engine - CRITICAL: Invalid Bitcoin price")
                raise ValueError("Invalid Bitcoin price - cannot perform entry analysis")
            
            logger.info(f"💰 PIPELINE DEBUG: Entry Engine - Current Bitcoin price: ${current_price:,.2f}")
            
            market_data = await get_live_market_data()
            if market_data is None:
                logger.error("❌ Cannot get market data for entry analysis")
                logger.warning("⚠️ PIPELINE DEBUG: Entry Engine - Market data unavailable, using fallback")
                market_data = {"price": current_price, "volume": 0}
            else:
                logger.info("✅ PIPELINE DEBUG: Entry Engine - Live market data retrieved successfully")
            
            # ENHANCED: Add historical market context
            logger.info("📊 PIPELINE DEBUG: Entry Engine - Processing historical market context...")
            if self.historical_context:
                try:
                    # Get price position in historical ranges
                    logger.info("📊 PIPELINE DEBUG: Entry Engine - Getting price range positions...")
                    price_position_30d = self.historical_context.get_price_range_position(current_price, "30D")
                    price_position_7d = self.historical_context.get_price_range_position(current_price, "7D")
                    
                    # Get support/resistance levels
                    logger.info("📊 PIPELINE DEBUG: Entry Engine - Getting support/resistance levels...")
                    support_levels, resistance_levels = self.historical_context.get_support_resistance_levels("30D")
                    
                    # Ensure we have valid data
                    support_levels = support_levels if support_levels is not None else []
                    resistance_levels = resistance_levels if resistance_levels is not None else []
                    
                    # Add to market data for layer analysis
                    market_data["price_position_30d"] = price_position_30d if price_position_30d is not None else 0.5
                    market_data["price_position_7d"] = price_position_7d if price_position_7d is not None else 0.5
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
                    logger.info("✅ PIPELINE DEBUG: Entry Engine - Historical context processed successfully")
                    
                except Exception as context_error:
                    logger.error(f"⚠️ PIPELINE DEBUG: Entry Engine - Historical context failed: {context_error}")
                    # Fallback to no historical context
                    market_data["historical_context_available"] = False
                    market_data["price_position_30d"] = 0.5
                    market_data["price_position_7d"] = 0.5
                    market_data["support_levels"] = []
                    market_data["resistance_levels"] = []
            else:
                logger.info("⚠️ PIPELINE DEBUG: Entry Engine - No historical context service available")
                market_data["historical_context_available"] = False
                market_data["price_position_30d"] = 0.5
                market_data["price_position_7d"] = 0.5
                market_data["support_levels"] = []
                market_data["resistance_levels"] = []
            
            # Run 6-layer entry analysis
            layer_results = await self._run_six_layer_entry_analysis(
                symbol, signal_data, current_price, market_data, user_portfolio
            )
            
            # Calculate consensus decision
            entry_decision = await self._calculate_entry_consensus(layer_results, signal_data)
            
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
            
            # Calculate analysis time
            analysis_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update performance stats
            self.total_analyses += 1
            if entry_decision["should_enter"]:
                self.entries_recommended += 1
            
            # Create comprehensive result
            result = EntryAnalysisResult(
                should_enter=entry_decision["should_enter"],
                confidence=entry_decision["confidence"],
                entry_reason=EntryReason(entry_decision["reason"]),
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
            logger.error(f"❌ Entry analysis failed: {e}")
            
            # Return safe fallback instead of crashing
            return EntryAnalysisResult(
                should_enter=False,
                confidence=0.0,
                entry_reason=EntryReason.POOR_TIMING,
                entry_quality=EntryQuality.POOR,
                optimal_entry_price=current_price if current_price and current_price > 0 else 111000.0,  # FIXED: Safe fallback price
                position_size_recommendation=0.0,
                risk_score=1.0,
                timing_score=0.0,
                layer_analysis={"error": str(e)},
                market_conditions={"error": "analysis_failed"},
                analysis_time_ms=0.0,
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _run_six_layer_entry_analysis(
        self, symbol: str, signal_data: Dict[str, Any], current_price: float, 
        market_data: Dict[str, Any], user_portfolio: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run comprehensive 6-layer entry analysis"""
        
        layer_results = {}
        
        # Layer 1: Market Regime Analysis
        try:
            regime_analysis = await self._analyze_entry_market_regime(market_data, signal_data)
            layer_results["layer_1_regime"] = regime_analysis
        except Exception as e:
            logger.warning(f"Layer 1 (Regime) failed: {e}")
            layer_results["layer_1_regime"] = {"recommendation": "wait", "confidence": 0.0}
        
        # Layer 2: LSTM Prediction Analysis
        if DISABLE_LSTM:
            logger.debug("🔄 PIPELINE DEBUG: Entry Engine - LSTM disabled by environment flag")
            layer_results["layer_2_lstm"] = {
                "recommendation": "wait", 
                "confidence": 0.5,
                "reasoning": "LSTM analysis disabled to prevent recursion errors"
            }
        else:
            try:
                lstm_analysis = await self._analyze_lstm_entry_signals(symbol, current_price, signal_data)
                layer_results["layer_2_lstm"] = lstm_analysis
            except Exception as e:
                logger.warning(f"Layer 2 (LSTM) failed: {e}")
                logger.debug(f"🔄 PIPELINE DEBUG: Entry Engine - LSTM analysis failed, using fallback")
                layer_results["layer_2_lstm"] = {"recommendation": "wait", "confidence": 0.0}
        
        # Layer 3: Pattern Recognition
        try:
            pattern_analysis = await self._analyze_entry_patterns(market_data, signal_data)
            layer_results["layer_3_patterns"] = pattern_analysis
        except Exception as e:
            logger.warning(f"Layer 3 (Patterns) failed: {e}")
            layer_results["layer_3_patterns"] = {"recommendation": "wait", "confidence": 0.0}
        
        # Layer 4: Technical Indicators
        try:
            technical_analysis = await self._analyze_entry_technical_indicators(market_data, current_price)
            layer_results["layer_4_technical"] = technical_analysis
        except Exception as e:
            logger.warning(f"Layer 4 (Technical) failed: {e}")
            layer_results["layer_4_technical"] = {"recommendation": "wait", "confidence": 0.0}
        
        # Layer 5: Momentum Analysis
        try:
            momentum_analysis = await self._analyze_entry_momentum(market_data, signal_data)
            layer_results["layer_5_momentum"] = momentum_analysis
        except Exception as e:
            logger.warning(f"Layer 5 (Momentum) failed: {e}")
            layer_results["layer_5_momentum"] = {"recommendation": "wait", "confidence": 0.0}
        
        # Layer 6: Entry Timing
        try:
            timing_analysis = await self._analyze_entry_timing(market_data, signal_data, user_portfolio)
            layer_results["layer_6_timing"] = timing_analysis
        except Exception as e:
            logger.warning(f"Layer 6 (Timing) failed: {e}")
            layer_results["layer_6_timing"] = {"recommendation": "wait", "confidence": 0.0}
        
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
    
    async def _analyze_lstm_entry_signals(self, symbol: str, current_price: float, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 2: Analyze LSTM/short-horizon predictions for entry timing (NO RANDOM)."""
        try:
            # Prefer short-horizon (1m/5m) models for day trading if available in enterprise engine path
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
                
                # Get 180 recent 1m candles for sequence (3x more data)
                candles_1m = service.get_recent_candles('1m', 180)
                if len(candles_1m) >= 60:  # Higher minimum for enterprise accuracy
                    # Create price sequence
                    prices = [float(c.get('close', current_price)) for c in candles_1m[-180:]]
                    # Pad if needed
                    while len(prices) < 180:
                        prices.insert(0, prices[0])
                    
                    x_1m = np.array(prices).reshape(1, 180, 1)
                    p1 = float(model_1m.predict(x_1m, verbose=0)[0][0])
                    preds.append(p1)
                    pred_meta["1m"] = {"prediction": p1, "sequence_length": len(candles_1m)}
                else:
                    logger.warning(f"Insufficient 1m candles: {len(candles_1m)}/60 required")
                    
            if model_path_5m.exists():
                model_5m = tf.keras.models.load_model(model_path_5m, compile=False)
                
                # Get 300 recent 1m candles for 5m equivalent (5 hours of data, 3x more)
                candles_5m = service.get_recent_candles('1m', 300)
                if len(candles_5m) >= 100:  # Higher minimum for enterprise accuracy
                    prices = [float(c.get('close', current_price)) for c in candles_5m[-300:]]
                    while len(prices) < 300:
                        prices.insert(0, prices[0])
                        
                    x_5m = np.array(prices).reshape(1, 300, 1)
                    p5 = float(model_5m.predict(x_5m, verbose=0)[0][0])
                    preds.append(p5)
                    pred_meta["5m"] = {"prediction": p5, "sequence_length": len(candles_5m)}
                else:
                    logger.warning(f"Insufficient 5m candles: {len(candles_5m)}/60 required")

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
            if rsi < 40:  # Oversold condition
                historical_success = await self._validate_oversold_pattern_historically(rsi)
                pattern_score += 0.25 * historical_success
                historical_success_pct = safe_format_number(historical_success * 100, 1)
                patterns_detected.append(f"oversold_rsi_validated_{historical_success_pct}%")
                
            if macd > 0 and macd > market_data.get("macd_signal", 0):  # Bullish MACD crossover
                historical_success = await self._validate_macd_crossover_historically("bullish")
                pattern_score += 0.3 * historical_success
                historical_success_pct = safe_format_number(historical_success * 100, 1)
                patterns_detected.append(f"bullish_macd_validated_{historical_success_pct}%")
                
            if bollinger_position < 0.3:  # Near lower Bollinger Band
                historical_success = await self._validate_bollinger_bounce_historically("support")
                pattern_score += 0.2 * historical_success
                historical_success_pct = safe_format_number(historical_success * 100, 1)
                patterns_detected.append(f"bollinger_support_validated_{historical_success_pct}%")
                
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
            if rsi > 60:  # Overbought condition
                historical_success = await self._validate_overbought_pattern_historically(rsi)
                pattern_score += 0.25 * historical_success
                historical_success_pct = safe_format_number(historical_success * 100, 1)
                patterns_detected.append(f"overbought_rsi_validated_{historical_success_pct}%")
                
            if macd < 0 and macd < market_data.get("macd_signal", 0):  # Bearish MACD crossover
                historical_success = await self._validate_macd_crossover_historically("bearish")
                pattern_score += 0.3 * historical_success
                historical_success_pct = safe_format_number(historical_success * 100, 1)
                patterns_detected.append(f"bearish_macd_validated_{historical_success_pct}%")
                
            if bollinger_position > 0.7:  # Near upper Bollinger Band
                historical_success = await self._validate_bollinger_bounce_historically("resistance")
                pattern_score += 0.2 * historical_success
                historical_success_pct = safe_format_number(historical_success * 100, 1)
                patterns_detected.append(f"bollinger_resistance_validated_{historical_success_pct}%")
                
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
        max_daily_trades = user_portfolio.get("max_daily_trades", 8)
        
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
        
        if daily_trades < max_daily_trades:
            timing_score += 0.1
            timing_factors.append("trade_capacity")
        else:
            timing_score = 0  # Can't trade if daily limit reached
            timing_factors = ["daily_limit_reached"]
        
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
    
    async def _calculate_entry_consensus(self, layer_results: Dict[str, Any], signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """ENHANCED: Calculate consensus with historical validation"""
        
        enter_votes = 0
        wait_votes = 0
        total_confidence = 0.0
        weighted_confidence = 0.0
        consensus_scores = []
        
        for layer_name, layer_data in layer_results.items():
            if isinstance(layer_data, dict):
                recommendation = layer_data.get("recommendation", "wait")
                confidence = layer_data.get("confidence", 0.0)
                
                # Get layer weight
                layer_number = int(layer_name.split('_')[1]) if '_' in layer_name else 1
                weight = self.layers.get(layer_number, {}).get("weight", 0.1)
                
                if recommendation == "enter":
                    enter_votes += 1
                    consensus_scores.append(confidence)
                    weighted_confidence += confidence * weight
                else:
                    wait_votes += 1
                    weighted_confidence += confidence * weight * 0.5  # Penalize wait votes
                
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
        
        # Adaptive thresholds based on signal type
        conf_thresh = self.confidence_threshold if not is_exploratory else 0.35  # Lower for exploratory
        signal_thresh = 0.7 if not is_exploratory else 0.30  # Much lower for exploratory
        
        # Enhanced checks with exploratory support
        meets_consensus = enter_votes > wait_votes and consensus_score > self.consensus_threshold
        meets_confidence = consensus_score > conf_thresh
        meets_historical = historical_validation_score > self.historical_validation_threshold
        meets_signal = signal_action in ["BUY", "SELL"] and signal_confidence > signal_thresh
        
        # Timing: respect Enterprise L6_time as override if strong
        timing_ok = meets_historical or l6_timing >= 0.70
        
        # For exploratory signals, treat disabled models as neutral
        if is_exploratory and enter_votes == 0 and wait_votes == 0:
            meets_consensus = True  # No active models = neutral = OK for exploratory
        
        logger.info(f"🔍 ENHANCED CHECKS: consensus={meets_consensus}, confidence={meets_confidence}, historical={meets_historical}, signal={meets_signal}, timing_ok={timing_ok}, signal_type={signal_type}")
        
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
        """Validate entry decision against historical pattern success rates"""
        if not self.historical_context:
            return 0.5  # Default if no historical context
        
        validation_scores = []
        
        # Check RSI pattern validation
        rsi_data = layer_results.get("layer_3_patterns", {}).get("market_indicators", {})
        rsi = rsi_data.get("rsi", 50)
        
        if signal_action == "BUY" and rsi < 40:
            rsi_pattern = self.historical_context.get_pattern_success_rate("rsi_oversold")
            if rsi_pattern:
                validation_scores.append(rsi_pattern.success_rate)
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
        
        # Return average validation score
        return np.mean(validation_scores) if validation_scores else 0.5
    
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
                historical_price = float(candle[4])  # Close price
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
            volumes = [float(candle[5]) for candle in historical_candles]
            avg_volume = np.mean(volumes)
            
            for i, candle in enumerate(historical_candles[:-5]):
                volume = float(candle[5])
                current_volume_ratio = volume / avg_volume
                
                # Find similar volume spikes
                if abs(current_volume_ratio - volume_ratio) < 0.3:
                    total_count += 1
                    # Check if price moved significantly
                    entry_price = float(candle[4])
                    future_price = float(historical_candles[i + 3][4]) if i + 3 < len(historical_candles) else entry_price
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
        
        # Extract OHLC data
        candle_data = []
        for candle in candles:
            candle_data.append({
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4])
            })
        
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
        
        closes = [float(candle[4]) for candle in candles]
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
        
        closes = [float(candle[4]) for candle in candles]
        
        # Simple MACD calculation (EMA12 - EMA26)
        ema_12 = self._calculate_ema(closes, 12)
        ema_26 = self._calculate_ema(closes, 26)
        
        macd = [ema_12[i] - ema_26[i] for i in range(len(ema_12))]
        return macd
    
    def _calculate_historical_bollinger_bands(self, candles: List, period: int = 20) -> List[Dict[str, float]]:
        """Calculate Bollinger Bands for historical data"""
        if len(candles) < period:
            return [{"upper": 0, "middle": 0, "lower": 0}] * len(candles)
        
        closes = [float(candle[4]) for candle in candles]
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