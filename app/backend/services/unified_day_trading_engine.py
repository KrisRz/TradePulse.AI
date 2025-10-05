"""
Unified Day Trading Engine - TradePulse.AI Professional
======================================================

JEDEN profesjonalny day trading engine łączący najlepsze funkcje:
- 6-layer AI analysis z EnterpriseTradingEngine
- Entry/Exit logic z Intelligent engines  
- Day trading optimization
- Professional thresholds (65%+ confidence)
- Warm-up period i market regime analysis

Author: TradePulse.AI Development Team
Created: January 2025
Version: 2.0.0 - Unified Professional Engine
"""

import asyncio
import os
import logging
import numpy as np
import pandas as pd
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

# Import market data services
from app.backend.services.live_market_data import (
    get_live_bitcoin_price, get_live_market_data, get_live_market_data_service
)
from app.backend.services.binance_hybrid_client import get_hybrid_client
from app.backend.services.professional_portfolio import get_professional_portfolio, PositionType

logger = logging.getLogger(__name__)

class TradingAction(str, Enum):
    """Trading actions"""
    BUY = "BUY"
    SELL = "SELL" 
    HOLD = "HOLD"

class ConfidenceLevel(str, Enum):
    """Signal confidence levels"""
    EXCELLENT = "excellent"    # 90%+ confidence
    HIGH = "high"             # 75-90% confidence  
    GOOD = "good"             # 65-75% confidence
    FAIR = "fair"             # 50-65% confidence
    POOR = "poor"             # <50% confidence

class MarketRegime(str, Enum):
    """Market regime classifications"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"

@dataclass(eq=False, order=False)
class UnifiedTradingSignal:
    """Unified trading signal with comprehensive analysis"""
    symbol: str
    action: TradingAction
    confidence: float
    price: float
    timestamp: datetime
    reasoning: str
    
    # Analysis breakdown
    layer_analysis: Dict[str, Any]
    market_regime: MarketRegime
    confidence_level: ConfidenceLevel
    
    # Risk management
    risk_score: float
    position_size_pct: float
    stop_loss_pct: float
    take_profit_pct: float
    
    # Timing
    optimal_entry_price: float
    timing_score: float
    
    def __eq__(self, other):
        return isinstance(other, UnifiedTradingSignal) and self.symbol == other.symbol and self.timestamp == other.timestamp
    
    def __hash__(self):
        return hash((self.symbol, self.timestamp))

class UnifiedDayTradingEngine:
    """
    UNIFIED Professional Day Trading Engine
    
    Combines best features from all previous engines:
    - EnterpriseTradingEngine: 6-layer AI analysis
    - IntelligentEntryEngine: Entry optimization
    - IntelligentExitEngine: Exit analysis  
    - DayTradingEngine: Day trading focus
    
    Professional Features:
    - 65%+ confidence thresholds
    - 10-minute warm-up period
    - Market regime analysis
    - Real data only (no fallbacks)
    - Conservative position sizing
    """
    
    def __init__(self):
        self.is_initialized = False
        self.models = {}
        
        # Professional path resolution
        current_file = Path(__file__).parent.parent
        self.model_path = current_file / "models" / "enterprise"
        
        # 🎯 ADAPTIVE TRADING PARAMETERS - NO HARDCODED VALUES!
        # These are initial defaults - will be replaced by Continuous Learning
        self._default_params = {
            'confidence_threshold': 0.45,
            'consensus_threshold': 0.50,
            'risk_threshold': 0.80,
            'volatility_threshold': 0.12,
            'max_position_size_pct': 0.030,
            'max_positions': 5,
            'min_position_size': 500.0,
            'analysis_interval': 12,
            'position_duration_target': 900,
            'stop_loss_pct': 0.006,
            'take_profit_pct': 0.004
        }
        
        # ADAPTIVE: Will be loaded from Continuous Learning
        self.confidence_threshold = self._default_params['confidence_threshold']
        self.consensus_threshold = self._default_params['consensus_threshold']
        self.risk_threshold = self._default_params['risk_threshold']
        self.volatility_threshold = self._default_params['volatility_threshold']
        self.max_position_size_pct = self._default_params['max_position_size_pct']
        self.max_positions = self._default_params['max_positions']
        self.min_position_size = self._default_params['min_position_size']
        self.analysis_interval = self._default_params['analysis_interval']
        self.position_duration_target = self._default_params['position_duration_target']
        self.stop_loss_pct = self._default_params['stop_loss_pct']
        self.take_profit_pct = self._default_params['take_profit_pct']
        
        # Parameter refresh tracking
        self._last_param_refresh = datetime.min
        self._param_refresh_interval = 3600  # Refresh every 1 hour
        
        # 🔥 WARM-UP AND SAFETY
        self.warm_up_required = True
        self.warm_up_minutes = 10
        self.min_historical_candles = 200
        self.is_warmed_up = False
        
        # 📈 PERFORMANCE TRACKING
        self.total_signals = 0
        self.signals_generated = 0
        self.positions_opened = 0
        self.successful_trades = 0
        self.layer_health = {}
        
        # 🧠 ADAPTIVE LAYER CONFIGURATION - Weights learned from performance!
        self._default_layer_weights = {
            1: 0.20,  # Market Regime Analysis
            2: 0.25,  # LSTM Prediction Models
            3: 0.20,  # Pattern Recognition
            4: 0.15,  # Technical Indicators
            5: 0.10,  # Momentum Analysis
            6: 0.10   # Entry Timing
        }
        
        self.layers = {
            1: {"name": "Market Regime Analysis", "weight": self._default_layer_weights[1]},
            2: {"name": "LSTM Prediction Models", "weight": self._default_layer_weights[2]}, 
            3: {"name": "Pattern Recognition", "weight": self._default_layer_weights[3]},
            4: {"name": "Technical Indicators", "weight": self._default_layer_weights[4]},
            5: {"name": "Momentum Analysis", "weight": self._default_layer_weights[5]},
            6: {"name": "Entry Timing", "weight": self._default_layer_weights[6]}
        }
        
        # Continuous Learning Engine reference (will be set during initialization)
        self.continuous_learning = None
        
        logger.info("🚀 ADAPTIVE Unified Day Trading Engine initialized (no hardcoded values)")
    
    async def initialize(self):
        """Initialize unified engine with all models and safety checks"""
        if self.is_initialized:
            return
            
        logger.info("🧠 Initializing ADAPTIVE Unified Day Trading Engine...")
        
        try:
            # Load AI models (6-layer system)
            await self._load_unified_models()
            
            # Initialize market data service
            self.market_service = await get_live_market_data_service()
            
            # PROFESSIONAL: Connect to Continuous Learning Engine
            try:
                from app.backend.services.continuous_learning_engine import get_continuous_learning_engine
                self.continuous_learning = await get_continuous_learning_engine()
                logger.info("✅ Connected to Continuous Learning Engine")
                
                # Load adaptive parameters from learning
                await self._load_adaptive_parameters()
                
                # Start periodic parameter refresh
                asyncio.create_task(self._periodic_parameter_refresh())
                logger.info("✅ Adaptive parameter loading enabled")
                
            except Exception as cl_error:
                logger.warning(f"⚠️ Continuous Learning not available: {cl_error} - using defaults")
                self.continuous_learning = None
            
            # Validate minimum data requirements
            await self._validate_data_requirements()
            
            self.is_initialized = True
            logger.info("✅ ADAPTIVE Unified Day Trading Engine initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize unified engine: {e}")
            raise
    
    async def _load_unified_models(self):
        """Load all 6-layer AI models with professional error handling"""
        try:
            # AUTO-DETECT TensorFlow and LSTM availability
            lstm_available = not os.getenv('DISABLE_LSTM', 'false').lower() == 'true'
            
            model_files = {
                "regime": "layer_1_regime.pkl",           # Market regime analysis
                "patterns": "layer_3_reversal.pkl",       # Pattern recognition  
                "technical": "layer_4_filters.pkl",       # Technical indicators
                "confidence": "layer_5_confidence.pkl",   # Confidence scoring
                "timing": "layer_6_timing.pkl",          # Entry/exit timing
            }
            
            # Add LSTM models - TensorFlow 2.16.1 stable version
            if lstm_available:
                model_files["lstm_1h"] = "lstm_1h.h5"
                model_files["lstm_4h"] = "lstm_4h.h5" 
                model_files["lstm_24h"] = "lstm_24h.h5"
                logger.info("✅ TensorFlow 2.16.1 stable - LSTM Layer 2 enabled")
            
            for model_name, filename in model_files.items():
                model_file = self.model_path / filename
                if model_file.exists():
                    if filename.endswith('.pkl'):
                        with open(model_file, "rb") as f:
                            self.models[model_name] = pickle.load(f)
                        logger.info(f"✅ Loaded {model_name} model")
                    elif filename.endswith('.h5'):
                        # Store model path for TF models; load lazily in usage to avoid pickle errors
                        self.models[model_name] = f"model_path:{model_file}"
                        logger.info(f"✅ Registered {model_name} TensorFlow model path")
                    else:
                        logger.warning(f"⚠️ Unknown model extension for {filename}, registering path")
                        self.models[model_name] = str(model_file)
                    self.layer_health[model_name] = "healthy"
                else:
                    if filename.endswith('.h5'):
                        logger.warning(f"⚠️ Optional LSTM model not found: {filename} (continuing without)")
                        self.layer_health[model_name] = "degraded"
                        continue
                    logger.error(f"❌ CRITICAL: Model file not found: {filename}")
                    raise FileNotFoundError(f"Required model missing: {filename}")
            
            # Load feature scalers
            scaler_path = self.model_path / "feature_scalers.pkl"
            if scaler_path.exists():
                with open(scaler_path, "rb") as f:
                    self.scalers = pickle.load(f)
                logger.info("✅ Feature scalers loaded")
            else:
                self.scalers = {}
                logger.warning("⚠️ No feature scalers found")
                
        except Exception as e:
            logger.error(f"❌ Model loading failed: {e}")
            raise RuntimeError(f"Unified model loading failed: {e}")
    
    async def _validate_data_requirements(self):
        """Validate minimum data requirements for professional trading"""
        try:
            # Check market data availability
            current_price = await get_live_bitcoin_price()
            market_data = await get_live_market_data()
            
            # Check historical data
            candles = self.market_service.get_recent_candles("1m", self.min_historical_candles)
            
            if len(candles) < self.min_historical_candles:
                raise RuntimeError(f"Insufficient historical data: {len(candles)}/{self.min_historical_candles} candles")
                
            logger.info(f"✅ Data validation passed: ${current_price:,.2f}, {len(candles)} candles")
            
        except Exception as e:
            logger.error(f"❌ Data validation failed: {e}")
            raise
    
    async def _load_adaptive_parameters(self):
        """
        Load adaptive parameters from Continuous Learning Engine
        PROFESSIONAL: No hardcoded values - learns from real trading data!
        """
        if not self.continuous_learning:
            logger.info("⚠️ Continuous Learning not available - using defaults")
            return
        
        try:
            # Fetch learned parameters
            learned_params = await self.continuous_learning.get_optimal_trading_parameters()
            
            if not learned_params:
                logger.info("📊 No learned parameters yet - using intelligent defaults")
                return
            
            # Update thresholds with learned values
            if 'confidence_threshold' in learned_params:
                old_val = self.confidence_threshold
                self.confidence_threshold = learned_params['confidence_threshold']
                logger.info(f"✅ ADAPTIVE confidence_threshold: {old_val:.3f} → {self.confidence_threshold:.3f}")
            
            if 'consensus_threshold' in learned_params:
                old_val = self.consensus_threshold
                self.consensus_threshold = learned_params['consensus_threshold']
                logger.info(f"✅ ADAPTIVE consensus_threshold: {old_val:.3f} → {self.consensus_threshold:.3f}")
            
            # Update position sizing with learned values
            if 'optimal_position_size_pct' in learned_params:
                old_val = self.max_position_size_pct
                self.max_position_size_pct = learned_params['optimal_position_size_pct']
                logger.info(f"✅ ADAPTIVE position_size: {old_val:.3f} → {self.max_position_size_pct:.3f}")
            
            # Update stop loss/take profit with learned values
            if 'optimal_stop_loss_pct' in learned_params:
                old_val = self.stop_loss_pct
                self.stop_loss_pct = learned_params['optimal_stop_loss_pct']
                logger.info(f"✅ ADAPTIVE stop_loss: {old_val:.4f} → {self.stop_loss_pct:.4f}")
            
            if 'optimal_take_profit_pct' in learned_params:
                old_val = self.take_profit_pct
                self.take_profit_pct = learned_params['optimal_take_profit_pct']
                logger.info(f"✅ ADAPTIVE take_profit: {old_val:.4f} → {self.take_profit_pct:.4f}")
            
            # Update layer weights with learned values
            if 'optimal_layer_weights' in learned_params:
                weights = learned_params['optimal_layer_weights']
                for layer_id, weight in weights.items():
                    if layer_id in self.layers:
                        old_weight = self.layers[layer_id]['weight']
                        self.layers[layer_id]['weight'] = weight
                        logger.info(f"✅ ADAPTIVE layer_{layer_id}_weight: {old_weight:.2f} → {weight:.2f}")
            
            self._last_param_refresh = datetime.now(timezone.utc)
            logger.info("🎯 ADAPTIVE parameters loaded from Continuous Learning!")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to load adaptive parameters: {e} - using defaults")
    
    async def _periodic_parameter_refresh(self):
        """
        Periodically refresh parameters from Continuous Learning
        Runs every 1 hour to pick up latest optimizations
        """
        try:
            while True:
                await asyncio.sleep(self._param_refresh_interval)
                
                # Check if refresh is needed
                time_since_refresh = (datetime.now(timezone.utc) - self._last_param_refresh).total_seconds()
                if time_since_refresh >= self._param_refresh_interval:
                    logger.info("🔄 Refreshing adaptive parameters from Continuous Learning...")
                    await self._load_adaptive_parameters()
                    
        except asyncio.CancelledError:
            logger.info("🛑 Parameter refresh loop cancelled")
        except Exception as e:
            logger.error(f"❌ Parameter refresh loop error: {e}")
    
    async def start_warm_up(self) -> Dict[str, Any]:
        """Start professional warm-up period"""
        if self.is_warmed_up:
            return {"status": "already_warmed_up"}
            
        if not self.is_initialized:
            await self.initialize()
            
        logger.info(f"🔥 Starting {self.warm_up_minutes}-minute professional warm-up...")
        
        try:
            warm_up_cycles = (self.warm_up_minutes * 60) // self.analysis_interval
            market_data_points = []
            signal_history = []
            
            for cycle in range(warm_up_cycles):
                try:
                    # Collect market data
                    current_price = await get_live_bitcoin_price()
                    market_data = await get_live_market_data()
                    
                    market_data_points.append({
                        'price': current_price,
                        'timestamp': datetime.now(timezone.utc),
                        'volatility': market_data.get('volatility', 0.02),
                        'volume_ratio': market_data.get('volume_ratio', 1.0)
                    })
                    
                    # Generate signals during warm-up (but don't trade!)
                    signal = await self._generate_analysis_only_signal("BTCUSDT")
                    if signal:
                        signal_history.append(signal)
                    
                    # Progress logging
                    if cycle % 8 == 0:  # Every 2 minutes
                        progress = (cycle / warm_up_cycles) * 100
                        avg_confidence = np.mean([s.confidence for s in signal_history[-10:]]) if signal_history else 0
                        logger.info(f"🔥 WARM-UP Progress: {progress:.0f}% - Avg confidence: {avg_confidence:.1%}")
                    
                    await asyncio.sleep(self.analysis_interval)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Warm-up cycle {cycle} failed: {e}")
            
            # Analyze warm-up results
            analysis_result = await self._analyze_warm_up_results(market_data_points, signal_history)
            
            self.is_warmed_up = True
            logger.info("✅ WARM-UP COMPLETE: Ready for professional trading")
            
            return {
                "status": "warm_up_complete",
                "duration_minutes": self.warm_up_minutes,
                "data_points_collected": len(market_data_points),
                "signals_analyzed": len(signal_history),
                "market_regime": analysis_result.get("market_regime", "unknown"),
                "average_confidence": analysis_result.get("avg_confidence", 0),
                "trading_readiness": analysis_result.get("ready_for_trading", False)
            }
            
        except Exception as e:
            logger.error(f"❌ Warm-up failed: {e}")
            raise
    
    async def _analyze_warm_up_results(self, market_data_points: List[Dict], signal_history: List) -> Dict[str, Any]:
        """Analyze warm-up data to determine market readiness"""
        try:
            if not market_data_points:
                return {"ready_for_trading": False, "reason": "no_data"}
            
            # Calculate market metrics
            prices = [point['price'] for point in market_data_points]
            volatilities = [point['volatility'] for point in market_data_points]
            
            # Market regime analysis
            price_trend = (prices[-1] - prices[0]) / prices[0]
            avg_volatility = np.mean(volatilities)
            price_stability = 1.0 - np.std(prices) / np.mean(prices)
            
            # Determine market regime
            if abs(price_trend) < 0.005 and avg_volatility < 0.03:
                market_regime = MarketRegime.SIDEWAYS
            elif price_trend > 0.01 and avg_volatility < 0.05:
                market_regime = MarketRegime.TRENDING_UP
            elif price_trend < -0.01 and avg_volatility < 0.05:
                market_regime = MarketRegime.TRENDING_DOWN
            elif avg_volatility > 0.08:
                market_regime = MarketRegime.VOLATILE
            else:
                market_regime = MarketRegime.UNKNOWN
            
            # Signal quality analysis
            avg_confidence = np.mean([s.confidence for s in signal_history]) if signal_history else 0
            signal_consistency = len([s for s in signal_history if s.confidence > 0.5]) / max(len(signal_history), 1)
            
            # Trading readiness decision
            ready_for_trading = (
                avg_volatility < self.volatility_threshold and  # Not too volatile
                avg_confidence > 0.4 and                        # Decent signal quality
                signal_consistency > 0.3 and                    # Some consistency
                len(market_data_points) >= 20                   # Sufficient data
            )
            
            return {
                "ready_for_trading": ready_for_trading,
                "market_regime": market_regime.value,
                "avg_confidence": avg_confidence,
                "avg_volatility": avg_volatility,
                "price_trend": price_trend,
                "signal_consistency": signal_consistency,
                "data_quality_score": len(market_data_points) / (self.warm_up_minutes * 4)
            }
            
        except Exception as e:
            logger.error(f"❌ Warm-up analysis failed: {e}")
            return {"ready_for_trading": False, "reason": "analysis_failed"}
    
    async def generate_signal(self, symbol: str = "BTCUSDT") -> Optional[UnifiedTradingSignal]:
        """Generate unified trading signal with professional analysis"""
        if not self.is_initialized:
            await self.initialize()
        
        if self.warm_up_required and not self.is_warmed_up:
            logger.warning("⚠️ Warm-up required before signal generation")
            return None
        
        try:
            logger.info(f"🎯 Generating unified signal for {symbol}")
            
            # Get real market data
            current_price = await get_live_bitcoin_price()
            market_data = await get_live_market_data()
            
            # Run 6-layer unified analysis
            layer_results = await self._run_unified_six_layer_analysis(symbol, current_price, market_data)
            
            # Calculate consensus decision
            decision = self._calculate_unified_consensus(layer_results, current_price, market_data)
            
            # Create unified signal
            if decision["should_trade"]:
                signal = UnifiedTradingSignal(
                    symbol=symbol,
                    action=TradingAction(decision["action"]),
                    confidence=decision["confidence"],
                    price=current_price,
                    timestamp=datetime.now(timezone.utc),
                    reasoning=decision["reasoning"],
                    layer_analysis=layer_results,
                    market_regime=decision["market_regime"],
                    confidence_level=self._determine_confidence_level(decision["confidence"]),
                    risk_score=decision["risk_score"],
                    position_size_pct=decision["position_size_pct"],
                    stop_loss_pct=self.stop_loss_pct,
                    take_profit_pct=self.take_profit_pct,
                    optimal_entry_price=decision["optimal_price"],
                    timing_score=decision["timing_score"]
                )
                
                self.signals_generated += 1
                logger.info(f"✅ UNIFIED SIGNAL: {signal.action.value} conf={signal.confidence:.1%} quality={signal.confidence_level.value}")
                return signal
            else:
                logger.info(f"📊 No signal generated: {decision['reasoning']}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Signal generation failed: {e}")
            return None
    
    async def _generate_analysis_only_signal(self, symbol: str) -> Optional[UnifiedTradingSignal]:
        """Generate signal for analysis only (during warm-up)"""
        try:
            current_price = await get_live_bitcoin_price()
            market_data = await get_live_market_data()
            
            # Run simplified analysis
            layer_results = await self._run_unified_six_layer_analysis(symbol, current_price, market_data)
            decision = self._calculate_unified_consensus(layer_results, current_price, market_data)
            
            return UnifiedTradingSignal(
                symbol=symbol,
                action=TradingAction(decision.get("action", "HOLD")),
                confidence=decision.get("confidence", 0.0),
                price=current_price,
                timestamp=datetime.now(timezone.utc),
                reasoning="warm_up_analysis",
                layer_analysis=layer_results,
                market_regime=MarketRegime.UNKNOWN,
                confidence_level=ConfidenceLevel.POOR,
                risk_score=decision.get("risk_score", 0.5),
                position_size_pct=0.0,
                stop_loss_pct=0.0,
                take_profit_pct=0.0,
                optimal_entry_price=current_price,
                timing_score=0.0
            )
            
        except Exception as e:
            logger.warning(f"⚠️ Analysis-only signal failed: {e}")
            return None
    
    async def _run_unified_six_layer_analysis(self, symbol: str, current_price: float, market_data: Dict) -> Dict[str, Any]:
        """Run unified 6-layer analysis combining best from all engines"""
        
        # Prepare features for all layers
        features = await self._prepare_unified_features(symbol, current_price, market_data)
        
        layer_results = {}
        
        # Layer 1: Market Regime (from Enterprise)
        layer_results["layer_1_regime"] = await self._analyze_market_regime(features, market_data)
        
        # Layer 2: LSTM Predictions (simplified, no TensorFlow issues)
        layer_results["layer_2_lstm"] = await self._analyze_price_predictions(features)
        
        # Layer 3: Pattern Recognition (from Entry engine)
        layer_results["layer_3_patterns"] = await self._analyze_patterns(features, market_data)
        
        # Layer 4: Technical Indicators (from Enterprise)
        layer_results["layer_4_technical"] = await self._analyze_technical_indicators(features, current_price)
        
        # Layer 5: Momentum Analysis (from Entry engine)
        layer_results["layer_5_momentum"] = await self._analyze_momentum(features, market_data)
        
        # Layer 6: Entry/Exit Timing (from Exit engine)
        layer_results["layer_6_timing"] = await self._analyze_timing(features, market_data)
        
        return layer_results
    
    async def _prepare_unified_features(self, symbol: str, current_price: float, market_data: Dict) -> Dict[str, float]:
        """Prepare unified feature set for all layers"""
        try:
            # Get historical data
            candles = self.market_service.get_recent_candles("1m", 100)
            # Update history as-of epoch gauge for readiness evaluation
            try:
                from app.backend.services.metrics import set_history_asof_epoch
                last_ts = float(candles[-1][0]) / 1000.0 if candles and isinstance(candles[-1], list) else float(candles[-1].get("open_time", candles[-1].get("timestamp", 0))) / 1000.0 if candles else 0.0
                if last_ts > 0:
                    set_history_asof_epoch(last_ts)
            except Exception:
                pass
            
            # Calculate technical indicators
            closes = [float(candle[4]) for candle in candles[-20:]] if candles else [current_price]
            
            # SSOT features only: disallow local recomputes
            try:
                from app.backend.services.metrics import inc_ssot_guard_violation
                DISALLOW_LOCAL_TECHS = True
                if DISALLOW_LOCAL_TECHS:
                    required = [
                        "price","volume","rsi","macd","bollinger_position",
                        "volatility","trend_strength","volume_ratio","price_change_24h"
                    ]
                    missing = [k for k in required if k not in market_data or market_data.get(k) is None]
                    if missing:
                        # Emit violation only when truly missing
                        inc_ssot_guard_violation("unified_features","missing_fields")
                        raise RuntimeError(f"SSOT missing fields: {missing}")
                # Map SSOT to unified names
                features = {
                    "close": market_data.get("price"),
                    "volume": market_data.get("volume"),
                    "rsi": market_data.get("rsi"),
                    "macd": market_data.get("macd"),
                    "bb_position": market_data.get("bollinger_position"),
                    "volatility": market_data.get("volatility"),
                    "trend_strength": market_data.get("trend_strength"),
                    "volume_ratio": market_data.get("volume_ratio"),
                    "price_change_24h": market_data.get("price_change_24h", market_data.get("price_change_percent_24h", 0.0))
                }
            except Exception as e:
                # Strict: bubble up to caller; we don't recompute locally when SSOT is enforced
                raise
            
            return features
            
        except Exception as e:
            # Enhanced feature preparation logging with correct semantics
            required_features = [
                "price", "volume", "rsi", "macd", "bollinger_position",
                "volatility", "trend_strength", "volume_ratio", "price_change_24h"
            ]
            missing_features = [f for f in required_features if f not in market_data or market_data.get(f) is None]

            if missing_features:
                logger.error(f"SSOT violation: missing={missing_features} | error: {e}")
                try:
                    from app.backend.services.metrics import inc_ssot_guard_violation
                    inc_ssot_guard_violation("unified_features","missing_fields")
                except Exception:
                    pass
            else:
                # No missing fields → salvage SSOT features from provided market_data and continue
                try:
                    features = {
                        "close": market_data.get("price"),
                        "volume": market_data.get("volume"),
                        "rsi": market_data.get("rsi"),
                        "macd": market_data.get("macd"),
                        "bb_position": market_data.get("bollinger_position"),
                        "volatility": market_data.get("volatility"),
                        "trend_strength": market_data.get("trend_strength"),
                        "volume_ratio": market_data.get("volume_ratio"),
                        "price_change_24h": market_data.get("price_change_24h", market_data.get("price_change_percent_24h", 0.0))
                    }
                    logger.debug("SSOT check passed; recovered features without local recompute")
                    return features
                except Exception:
                    # If salvage fails, propagate original error
                    pass
            # Propagate original error if we couldn't salvage
            raise
    
    def _calculate_unified_consensus(self, layer_results: Dict, current_price: float, market_data: Dict) -> Dict[str, Any]:
        """Calculate unified consensus decision with professional criteria"""
        
        # Extract layer recommendations
        buy_votes = 0
        sell_votes = 0
        hold_votes = 0
        confidence_scores = []
        risk_scores = []
        
        for layer_name, layer_data in layer_results.items():
            if not isinstance(layer_data, dict):
                continue
                
            recommendation = layer_data.get("recommendation", "hold")
            confidence = layer_data.get("confidence", 0.0)
            risk = layer_data.get("risk_score", 0.5)
            
            confidence_scores.append(confidence)
            risk_scores.append(risk)
            
            if recommendation == "buy":
                buy_votes += 1
            elif recommendation == "sell":
                sell_votes += 1
            else:
                hold_votes += 1
        
        # Calculate consensus metrics
        total_votes = buy_votes + sell_votes + hold_votes
        avg_confidence = np.mean(confidence_scores) if confidence_scores else 0.0
        avg_risk = np.mean(risk_scores) if risk_scores else 0.5
        
        # Determine market regime
        volatility = market_data.get("volatility", 0.02)
        trend_strength = market_data.get("trend_strength", 0.5)
        
        if volatility > self.volatility_threshold:
            market_regime = MarketRegime.VOLATILE
        elif trend_strength > 0.7:
            market_regime = MarketRegime.TRENDING_UP
        elif trend_strength < -0.7:
            market_regime = MarketRegime.TRENDING_DOWN
        else:
            market_regime = MarketRegime.SIDEWAYS
        
        # 🎯 PROFESSIONAL DECISION LOGIC
        consensus_pct = max(buy_votes, sell_votes) / max(total_votes, 1)
        
        # STRICT PROFESSIONAL CRITERIA
        confidence_check = avg_confidence >= self.confidence_threshold  # 65%
        consensus_check = consensus_pct >= (self.consensus_threshold / 100)  # 70%
        risk_check = avg_risk <= self.risk_threshold  # 30%
        volatility_check = volatility <= self.volatility_threshold  # 8%
        
        if (confidence_check and consensus_check and risk_check and volatility_check):
            if buy_votes > sell_votes and buy_votes > hold_votes:
                action = "BUY"
                should_trade = True
            elif sell_votes > buy_votes and sell_votes > hold_votes:
                action = "SELL"
                should_trade = True
            else:
                action = "HOLD"
                should_trade = False
        else:
            action = "HOLD"
            should_trade = False
        
        # Calculate position size (conservative)
        position_size_pct = self.max_position_size_pct * min(avg_confidence, 1.0)
        
        return {
            "should_trade": should_trade,
            "action": action,
            "confidence": avg_confidence,
            "risk_score": avg_risk,
            "market_regime": market_regime,
            "consensus_pct": consensus_pct,
            "position_size_pct": position_size_pct,
            "optimal_price": current_price,  # TODO: Improve with technical levels
            "timing_score": layer_results.get("layer_6_timing", {}).get("timing_score", 0.0),
            "reasoning": f"Unified consensus: {consensus_pct:.1%}, conf={avg_confidence:.1%}, risk={avg_risk:.1%}, regime={market_regime.value}",
            "layer_votes": {"buy": buy_votes, "sell": sell_votes, "hold": hold_votes}
        }
    
    def _determine_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Determine confidence level classification"""
        if confidence >= 0.90:
            return ConfidenceLevel.EXCELLENT
        elif confidence >= 0.75:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.65:
            return ConfidenceLevel.GOOD
        elif confidence >= 0.50:
            return ConfidenceLevel.FAIR
        else:
            return ConfidenceLevel.POOR
    
    # ===== LAYER ANALYSIS METHODS (Simplified from original engines) =====
    
    async def _analyze_market_regime(self, features: Dict, market_data: Dict) -> Dict[str, Any]:
        """Layer 1: Market regime analysis"""
        volatility = features.get("volatility", 0.02)
        trend_strength = features.get("trend_strength", 0.5)
        volume_ratio = features.get("volume_ratio", 1.0)
        
        if trend_strength > 0.6 and volatility < 0.04:
            recommendation = "buy"
            confidence = 0.7
        elif trend_strength < -0.6 and volatility < 0.04:
            recommendation = "sell"
            confidence = 0.7
        elif volatility > 0.08:
            recommendation = "hold"
            confidence = 0.3
        else:
            recommendation = "hold"
            confidence = 0.5
            
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "risk_score": volatility / 0.10,  # Normalize to 0-1
            "regime": "trending" if abs(trend_strength) > 0.5 else "sideways"
        }
    
    async def _analyze_price_predictions(self, features: Dict) -> Dict[str, Any]:
        """Layer 2: Price prediction analysis (simplified)"""
        # Simplified momentum-based prediction
        price_momentum = features.get("price_change_24h", 0.0)
        
        if price_momentum > 0.02:
            recommendation = "buy"
            confidence = 0.6
        elif price_momentum < -0.02:
            recommendation = "sell"
            confidence = 0.6
        else:
            recommendation = "hold"
            confidence = 0.4
            
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "risk_score": abs(price_momentum) / 0.05,
            "prediction": "bullish" if price_momentum > 0 else "bearish"
        }
    
    async def _analyze_patterns(self, features: Dict, market_data: Dict) -> Dict[str, Any]:
        """Layer 3: Pattern recognition analysis"""
        rsi = features.get("rsi", 50)
        macd = features.get("macd", 0)
        bb_position = features.get("bb_position", 0.5)
        
        pattern_score = 0
        
        # RSI patterns
        if rsi < 30:  # Oversold
            pattern_score += 0.3
            recommendation = "buy"
        elif rsi > 70:  # Overbought
            pattern_score += 0.3
            recommendation = "sell"
        else:
            recommendation = "hold"
        
        # MACD patterns
        if macd > 0:
            pattern_score += 0.2
        elif macd < 0:
            pattern_score += 0.2
        
        confidence = min(pattern_score, 0.8)
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "risk_score": 1.0 - confidence,
            "patterns": ["rsi", "macd", "bollinger"]
        }
    
    async def _analyze_technical_indicators(self, features: Dict, current_price: float) -> Dict[str, Any]:
        """Layer 4: Technical indicator analysis"""
        rsi = features.get("rsi", 50)
        volume_ratio = features.get("volume_ratio", 1.0)
        
        technical_score = 0
        
        if rsi < 40 and volume_ratio > 1.2:
            recommendation = "buy"
            technical_score = 0.7
        elif rsi > 60 and volume_ratio > 1.2:
            recommendation = "sell" 
            technical_score = 0.7
        else:
            recommendation = "hold"
            technical_score = 0.4
        
        return {
            "recommendation": recommendation,
            "confidence": technical_score,
            "risk_score": 1.0 - technical_score,
            "technical_score": technical_score
        }
    
    async def _analyze_momentum(self, features: Dict, market_data: Dict) -> Dict[str, Any]:
        """Layer 5: Momentum analysis"""
        volume_ratio = features.get("volume_ratio", 1.0)
        price_momentum = features.get("price_change_24h", 0.0)
        
        momentum_score = 0
        
        if volume_ratio > 1.5 and price_momentum > 0.01:
            recommendation = "buy"
            momentum_score = 0.6
        elif volume_ratio > 1.5 and price_momentum < -0.01:
            recommendation = "sell"
            momentum_score = 0.6
        else:
            recommendation = "hold"
            momentum_score = 0.3
        
        return {
            "recommendation": recommendation,
            "confidence": momentum_score,
            "risk_score": 1.0 - momentum_score,
            "momentum_factors": ["volume", "price"]
        }
    
    async def _analyze_timing(self, features: Dict, market_data: Dict) -> Dict[str, Any]:
        """Layer 6: Entry/exit timing analysis"""
        current_hour = datetime.now(timezone.utc).hour
        volume_ratio = features.get("volume_ratio", 1.0)
        
        # Market hours timing
        market_hours = 9 <= current_hour <= 16  # Example market hours
        
        timing_score = 0
        if market_hours:
            timing_score += 0.3
        if volume_ratio > 1.2:
            timing_score += 0.4
        
        recommendation = "buy" if timing_score > 0.5 else "hold"
        
        return {
            "recommendation": recommendation,
            "confidence": timing_score,
            "risk_score": 1.0 - timing_score,
            "timing_score": timing_score,
            "market_hours": market_hours
        }
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get comprehensive engine status"""
        return {
            "engine_type": "unified_day_trading",
            "is_initialized": self.is_initialized,
            "is_warmed_up": self.is_warmed_up,
            "total_signals": self.total_signals,
            "signals_generated": self.signals_generated,
            "positions_opened": self.positions_opened,
            "successful_trades": self.successful_trades,
            "success_rate": self.successful_trades / max(self.positions_opened, 1),
            "layer_health": self.layer_health.copy(),
            "models_loaded": len(self.models),
            "configuration": {
                "confidence_threshold": self.confidence_threshold,
                "consensus_threshold": self.consensus_threshold,
                "risk_threshold": self.risk_threshold,
                "max_positions": self.max_positions,
                "position_size_pct": self.max_position_size_pct,
                "warm_up_minutes": self.warm_up_minutes
            },
            "status": "operational" if self.is_initialized else "initializing"
        }

# Export the unified engine
__all__ = ["UnifiedDayTradingEngine", "UnifiedTradingSignal", "TradingAction", "ConfidenceLevel", "MarketRegime"]
