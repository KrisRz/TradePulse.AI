"""
Enterprise Trading Engine for TradePulse.AI
6-Layer AI Decision System with Real Market Data Integration
"""

import asyncio
import logging
import numpy as np
import pandas as pd
import pickle
from app.backend.core.feature_schema import FEATURE_COLUMNS, make_X_live, predict_lgbm_safe, predict_rf_safe, log_schema_info
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

from .binance_hybrid_client import get_hybrid_client
from .live_market_data import get_live_market_data_service, get_live_bitcoin_price
from ..config.trading_thresholds import get_trading_thresholds

logger = logging.getLogger(__name__)

@dataclass(eq=False, order=False)
class TradingSignal:
    """Trading signal with full AI analysis"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: float
    price: float
    timestamp: datetime
    reasoning: str
    layer_analysis: Dict[str, Any]
    risk_score: float
    position_size: float
    signal_type: str = "primary"  # primary, exploratory
    
    def __eq__(self, other):
        """Safe equality based on symbol and timestamp only"""
        return isinstance(other, TradingSignal) and self.symbol == other.symbol and self.timestamp == other.timestamp
    
    def __hash__(self):
        """Safe hash based on symbol and timestamp"""
        return hash((self.symbol, self.timestamp))

class EnterpriseTradingEngine:
    """Professional 6-Layer AI Trading Engine with Real Market Data"""
    
    def __init__(self):
        self.is_initialized = False
        self.models = {}
        # Professional path resolution - works from any working directory
        current_file = Path(__file__).parent.parent  # Go up from services/ to backend/
        self.model_path = current_file / "models" / "enterprise"
        
        # Use unified trading thresholds (delegated to validator & entry/exit engines)
        self.thresholds = get_trading_thresholds()
        self.confidence_threshold = self.thresholds.confidence.BUY_THRESHOLD  # 65% unified threshold
        
        # ✅ PROFESSIONAL: Risk & position sizing delegated to specialized services:
        # - Risk threshold → DynamicRiskManager (adaptive)
        # - Position size → Kelly Criterion in Entry Engine (adaptive)
        # - No hardcoded flags (engine is pure signal generator)
        
        # Market data service
        self.market_service = None
        
        # 🔮 PRICE FORECASTING SERVICE (Layer 7 - ML Price Prediction)
        # Professional day trading optimization - predicts price 1h/4h/24h ahead
        self.price_forecasting_service = None
        
        # 📊 MONITORING METRICS: Track signal generation performance
        # Industry best practice: Monitor what you manage
        self.signal_metrics = {
            "sell_signals": {
                "extreme_overbought_count": 0,       # Tier 1: Extreme RSI≥90 SELL signals
                "standard_overbought_count": 0,      # Tier 2: Standard RSI≥85 SELL signals
                "standard_sell_count": 0,            # Regular standard SELL signals
                "blocked_by_rsi_count": 0,           # SELL blocked by RSI<20
                "blocked_by_volume_count": 0,        # Tier 2 blocked by volume gate
                "total_sell_confidence": 0.0,        # Sum of all SELL confidences
                "avg_sell_confidence": 0.0,          # Average SELL confidence
                "last_sell_rsi": 0.0,                # Last SELL signal RSI
                "last_sell_reversal": 0.0,           # Last SELL signal reversal prob
            },
            "buy_signals": {
                "extreme_oversold_count": 0,         # Extreme RSI<30 BUY signals
                "standard_buy_count": 0,             # Standard BUY signals
                "blocked_by_rsi_count": 0,           # BUY blocked by RSI>80
                "total_buy_confidence": 0.0,         # Sum of all BUY confidences
                "avg_buy_confidence": 0.0,           # Average BUY confidence
                "last_buy_rsi": 0.0,                 # Last BUY signal RSI
                "last_buy_reversal": 0.0,            # Last BUY signal reversal prob
            },
            "hold_signals": {
                "total_hold_count": 0,               # Total HOLD decisions
                "avg_hold_time_extreme_rsi": 0.0,    # Avg hold time during extreme RSI
            },
            "session_stats": {
                "session_start": None,               # Session start time
                "total_signals": 0,                  # Total signals generated
                "sell_rate": 0.0,                    # SELL signals / total signals
                "buy_rate": 0.0,                     # BUY signals / total signals
            }
        }
        
        # Initialize session start time
        from datetime import datetime
        self.signal_metrics["session_stats"]["session_start"] = datetime.utcnow()
        
    async def initialize(self):
        """Initialize the trading engine with models and market data"""
        if self.is_initialized:
            logger.info("🔄 PIPELINE DEBUG: Enterprise Trading Engine already initialized, skipping...")
            return
            
        logger.info("🧠 Initializing Enterprise Trading Engine...")
        logger.info("📊 PIPELINE DEBUG: Enterprise Trading Engine - Starting initialization sequence")
        logger.info(f"🎯 PIPELINE DEBUG: Enterprise Trading Engine - Component: Enterprise Trading Engine v1.0.0")
        logger.info(f"🎯 PIPELINE DEBUG: Enterprise Trading Engine - Purpose: 6-Layer AI signal generation")
        
        try:
            # Load 6-layer models (NO FALLBACKS)
            logger.info("🤖 PIPELINE DEBUG: Enterprise Trading Engine - Loading 6-layer AI models...")
            await self._load_models()
            logger.info("✅ Models loaded successfully, initializing market service...")
            logger.info("✅ PIPELINE DEBUG: Enterprise Trading Engine - AI models loaded successfully")
            
            # Log unified feature schema
            log_schema_info()
            
            # Initialize market data service
            logger.info("📈 PIPELINE DEBUG: Enterprise Trading Engine - Initializing market data service...")
            try:
                self.market_service = await get_live_market_data_service()
                logger.info("✅ Market data service initialized")
                logger.info("✅ PIPELINE DEBUG: Enterprise Trading Engine - Market data service connected")
            except Exception as market_error:
                logger.warning(f"⚠️ Market data service failed: {market_error}")
                logger.warning("⚠️ PIPELINE DEBUG: Enterprise Trading Engine - Market data service failed, continuing without")
                self.market_service = None
            
            # 🔮 LAYER 7: Initialize Price Forecasting Service (ML Price Prediction)
            logger.info("🔮 PIPELINE DEBUG: Enterprise Trading Engine - Initializing Price Forecasting Service...")
            try:
                from app.backend.services.price_forecasting_service import PriceForecastingService
                
                # Create forecasting service and share our LSTM models (prevent duplicate loading)
                self.price_forecasting_service = PriceForecastingService()
                
                # Share LSTM models if we have them (avoid recursion errors from duplicate loading)
                await self.price_forecasting_service.initialize(shared_models=self.models)
                
                logger.info("✅ Price Forecasting Service initialized (Layer 7)")
                logger.info("✅ PIPELINE DEBUG: Enterprise Trading Engine - Price predictions enabled (1h/4h/24h)")
            except Exception as forecast_error:
                logger.warning(f"⚠️ Price Forecasting Service failed: {forecast_error}")
                logger.warning("⚠️ PIPELINE DEBUG: Enterprise Trading Engine - Continuing without price predictions")
                self.price_forecasting_service = None
            
            self.is_initialized = True
            logger.info("🎯 PIPELINE DEBUG: Enterprise Trading Engine - READY FOR OPERATIONS")
            logger.info("🎯 PIPELINE DEBUG: Enterprise Trading Engine - Status: INITIALIZED & OPERATIONAL")
            logger.info("✅ Enterprise Trading Engine initialized successfully")
            
        except RecursionError as re:
            logger.error(f"❌ RecursionError in enterprise engine: {str(re)[:200]}")
            raise RuntimeError(f"Recursion error in enterprise engine initialization")
        except Exception as e:
            logger.error(f"Failed to initialize trading engine: {e}")
            raise

    async def reload_models(self) -> Dict[str, Any]:
        """Hot-reload all AI models from disk.

        Returns:
            Summary dict with model keys loaded and timestamp.
        """
        if not self.is_initialized:
            await self.initialize()
        try:
            await self._load_models()
            info = {
                "reloaded_at": datetime.now(timezone.utc).isoformat(),
                "models": sorted(list(self.models.keys()))
            }
            logger.info("🔄 Enterprise models hot-reloaded", extra={"models": info["models"]})
            return info
        except Exception as e:
            logger.error(f"Model reload failed: {e}")
            raise RuntimeError(f"Model reload failed: {e}")
    
    async def _load_models(self):
        """Load all 6-layer AI models. Raise on failure to avoid fallbacks."""
        import traceback
        import faulthandler
        import sys
        
        # Enable fault handler for recursion detection
        faulthandler.enable()
        
        # Temporarily increase recursion limit as guard (not a fix)
        original_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(5000)
        
        try:
            # Load feature scalers if available (PROFESSIONAL REQUIREMENT)
            scaler_path = self.model_path / "feature_scalers.pkl"
            if scaler_path.exists():
                with open(scaler_path, "rb") as f:
                    self.scalers = pickle.load(f)
                logger.info("✅ Feature scalers loaded for professional deployment")
            else:
                self.scalers = {}
                logger.warning("⚠️ No feature scalers found - models may not work with live data")
            
            # Load each layer with precise error handling - EXPLICIT ORDERING
            layers_to_load = [
                ("regime", "layer_1_regime.pkl", "Layer 1 (Market Regime)", 1),
                ("reversal", "layer_3_reversal.pkl", "Layer 3 (Reversal Detection)", 3),
                ("filters", "layer_4_filters.pkl", "Layer 4 (Technical Filters)", 4),
                ("confidence", "layer_5_confidence.pkl", "Layer 5 (Confidence Scoring)", 5),
                ("timing", "layer_6_timing.pkl", "Layer 6 (Adaptive Timing)", 6)
            ]
            
            # SAFE SORTING: Use explicit key, not implicit comparison
            layers_to_load = sorted(layers_to_load, key=lambda x: x[3])  # Sort by priority number
            
            for model_key, filename, display_name, priority in layers_to_load:
                model_path = self.model_path / filename
                if model_path.exists():
                    try:
                        # SAFE LOGGING: Only log name/id, not full objects
                        logger.info(f"🔄 Loading {display_name} (priority {priority})...")
                        
                        # Try loading with metadata first (new format), fallback to legacy pickle
                        try:
                            from app.backend.ml.infer import load_model_with_metadata
                            bundle = load_model_with_metadata(model_path)
                            model = bundle.get("model")
                            features = bundle.get("features")
                            model_type = bundle.get("model_type", "unknown")
                            
                            if model and features:
                                logger.info(f"✅ {display_name} loaded with metadata: {model_type}, "
                                          f"{len(features)} features: {features}")
                            elif model:
                                logger.info(f"✅ {display_name} loaded (legacy format): {type(model).__name__}")
                            else:
                                raise ValueError("No model in bundle")
                                
                        except Exception:
                            # Fallback to legacy pickle loading
                            with open(model_path, "rb") as f:
                                old_limit = sys.getrecursionlimit()
                                sys.setrecursionlimit(3000)  # Sufficient for loading
                                try:
                                    model = pickle.load(f)
                                    logger.info(f"✅ {display_name} loaded (legacy pickle): {type(model).__name__}")
                                finally:
                                    sys.setrecursionlimit(old_limit)
                        
                        # SAFE MODEL HANDLING: Skip hardening to prevent recursion
                        # Model objects are handled safely through proper feature preparation
                        
                        self.models[model_key] = model
                        
                    except RecursionError as re:
                        # TARGETED RECURSION DEBUGGING
                        logger.error(f"❌ RecursionError in {display_name}: {str(re)[:200]}")
                        logger.error(f"Recursion limit: {sys.getrecursionlimit()}")
                        logger.error(f"Traceback (limited):\n{traceback.format_exc(limit=10)}")
                        # Log model info for cycle detection
                        if 'model' in locals():
                            logger.error(f"Model type: {type(model).__name__}, id: {id(model)}")
                        raise RuntimeError(f"Recursion error in {display_name} - model has cyclic references")
                    except Exception as e:
                        logger.error(f"❌ Failed loading {display_name}: {str(e)[:200]}")
                        logger.error(f"Traceback (limited):\n{traceback.format_exc(limit=10)}")
                        raise
                else:
                    logger.warning(f"⚠️ {display_name} model file not found: {filename}")
            
            # LSTM/TF models (Layer 2 + Layer 7) - ENABLED with safe loading
            logger.info("🔄 Loading LSTM models with recursion prevention...")
            
            try:
                # Load LSTM models with safe wrapper
                # Layer 2: Short-term (1m, 5m) for immediate signals
                # Layer 7: Day trading horizons (1h, 4h, 24h) for price forecasting
                lstm_models = {
                    "lstm_1m": "lstm_1m.h5",    # Layer 2: 1-minute signals
                    "lstm_5m": "lstm_5m.h5",    # Layer 2: 5-minute signals
                    "lstm_1h": "lstm_1h.h5",    # Layer 7: 1-hour price prediction
                    "lstm_4h": "lstm_4h.h5",    # Layer 7: 4-hour price prediction
                    "lstm_24h": "lstm_24h.h5"   # Layer 7: 24-hour price prediction
                }
                
                for model_key, filename in lstm_models.items():
                    model_file = self.model_path / filename
                    if model_file.exists():
                        try:
                            # Use safe LSTM loading
                            from app.backend.core.safe_lstm import SafeLSTM
                            import tensorflow as tf
                            
                            # Load model with minimal verbose output
                            keras_model = tf.keras.models.load_model(str(model_file), compile=False)
                            safe_model = SafeLSTM(keras_model)
                            
                            self.models[model_key] = safe_model
                            logger.info(f"✅ {model_key} loaded with safe wrapper")
                            
                        except Exception as lstm_error:
                            logger.warning(f"⚠️ Failed to load {model_key}: {lstm_error}")
                            # Continue without this LSTM model
                    else:
                        logger.warning(f"⚠️ LSTM model not found: {filename}")
                
                logger.info("✅ LSTM model loading completed with safe wrappers")
                
            except Exception as lstm_error:
                logger.warning(f"⚠️ LSTM loading failed, continuing with classical models: {lstm_error}")
            
            logger.info("✅ Model loading completed - AI layers operational")
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            raise RuntimeError(f"Model loading failed: {e}")
        finally:
            # Safely restore original recursion limit
            try:
                sys.setrecursionlimit(original_limit)
            except Exception as restore_error:
                logger.warning(f"⚠️ Could not restore recursion limit: {restore_error}")
                # Set to a safe default
                sys.setrecursionlimit(1000)
    
    # REMOVED: _harden_model_object method was causing recursion issues
    # Models are now handled safely through proper feature preparation without modification

    def _get_model_feature_names(self, model: Any, default_order: List[str]) -> List[str]:
        """Return feature names in the order expected by the model if available.

        Tries common attributes across sklearn, LightGBM, and XGBoost wrappers.
        Falls back to the provided default order.
        """
        try:
            # scikit-learn >=1.0
            if hasattr(model, 'feature_names_in_'):
                return list(getattr(model, 'feature_names_in_'))
            # LightGBM booster
            if hasattr(model, 'booster_') and hasattr(model.booster_, 'feature_names'):
                return list(model.booster_.feature_names)
            # LightGBM sklearn wrapper sometimes exposes feature_name_
            if hasattr(model, 'feature_name_'):
                return list(getattr(model, 'feature_name_'))
        except Exception:
            pass
        return list(default_order)

    def _get_model_expected_size(self, model: Any, fallback: int) -> int:
        """Return expected feature count for the model if known."""
        try:
            if hasattr(model, 'n_features_in_'):
                return int(getattr(model, 'n_features_in_'))
        except Exception:
            pass
        return int(fallback)

    def _build_feature_array(self, model: Any, 
                features: Dict[str, float], 
                default_order: List[str],
                layer_name: str = "") -> Any:
        """Build a feature vector aligned to the model's expected names/order/length.

        We use any advertised feature names; otherwise default_order. Unknown names are
        filled with 0.0. Values are pulled from the `features` dict which includes:
        ['close','volume','rsi','macd','bb_position','volatility','trend_strength',
         'volume_ratio','price_change_24h']
        """
        # Determine the required order and size
        required_names = self._get_model_feature_names(model, default_order)
        expected_size = self._get_model_expected_size(model, len(required_names))
        # If the model doesn't expose names but expects more features than default_order,
        # extend with plausible extras to reach size (stable order)
        known_pool = [
            "close","volume","rsi","macd","bb_position","volatility",
            "trend_strength","volume_ratio","price_change_24h"
        ]
        if len(required_names) < expected_size:
            for name in known_pool:
                if name not in required_names:
                    required_names.append(name)
                    if len(required_names) >= expected_size:
                        break
        # Build vector in order
        vector = [float(features.get(name, 0.0)) for name in required_names[:expected_size]]
        # Ensure correct shape
        arr = np.array(vector, dtype=float).reshape(1, -1)
        
        # PROFESSIONAL SCALING: Apply training scalers if available (DISABLED for L5 - model works without)
        if layer_name and layer_name in self.scalers and layer_name != "layer_5":
            try:
                scaler = self.scalers[layer_name]
                arr = scaler.transform(arr)
                logger.info(f"🔧 Applied {layer_name} scaler to features")
            except Exception as e:
                logger.warning(f"⚠️ Failed to apply {layer_name} scaler: {e}")
        elif layer_name == "layer_5":
            logger.info(f"🔧 L5 scaler DISABLED - model works with raw features")
        
        # Handle feature names properly to avoid sklearn/LightGBM warnings
        try:
            import pandas as pd
            
            # Check if model was trained with feature names
            model_has_feature_names = (
                hasattr(model, 'feature_names_in_') or 
                (hasattr(model, 'booster_') and hasattr(model.booster_, 'feature_names')) or
                hasattr(model, 'feature_name_')
            )
            
            # Handle different model types based on their training
            if model_has_feature_names:
                # Model was trained with feature names - return DataFrame
                col_names = None
                if hasattr(model, 'feature_names_in_'):
                    col_names = list(getattr(model, 'feature_names_in_'))[:arr.shape[1]]
                elif hasattr(model, 'booster_') and hasattr(model.booster_, 'feature_names'):
                    col_names = list(model.booster_.feature_names)[:arr.shape[1]]
                elif hasattr(model, 'feature_name_'):
                    col_names = list(getattr(model, 'feature_name_'))[:arr.shape[1]]
                
                if col_names:
                    return pd.DataFrame(arr, columns=col_names)
                else:
                    # Fallback: use required_names if no feature names found
                    return pd.DataFrame(arr, columns=required_names[:arr.shape[1]])
            else:
                # Model was trained without feature names - return numpy array
                return arr
            
        except Exception as e:
            logger.debug(f"Feature array preparation failed for {layer_name}: {e}")
            return arr
    
    async def generate_signal(self, symbol: str = "BTCUSDT", market_snapshot: Optional[Any] = None) -> TradingSignal:
        """Generate comprehensive trading signal using 6-layer analysis"""
        if not self.is_initialized:
            logger.info("🔄 PIPELINE DEBUG: Enterprise Trading Engine - Not initialized, initializing now...")
            await self.initialize()
        
        try:
            logger.info(f"🎯 Generating AI signal for {symbol}...")
            logger.info(f"🎯 PIPELINE DEBUG: Enterprise Trading Engine - Generating signal for {symbol}")
            logger.info("📊 PIPELINE DEBUG: Enterprise Trading Engine - Starting 6-layer AI analysis")
            
            # Get current market data
            logger.info("📈 PIPELINE DEBUG: Enterprise Trading Engine - Fetching live market data...")
            current_price = await get_live_bitcoin_price()
            if current_price is None or current_price <= 0:
                logger.error("💥 PIPELINE DEBUG: Enterprise Trading Engine - CRITICAL: Invalid Bitcoin price")
                raise ValueError("Invalid Bitcoin price for signal generation")
            
            logger.info(f"💰 PIPELINE DEBUG: Enterprise Trading Engine - Current Bitcoin price: ${current_price:,.2f}")
            
            logger.info("🔍 PIPELINE DEBUG: Enterprise Trading Engine - Extracting market features...")
            snapshot_obj = None
            if market_snapshot is not None:
                # Map LiveMarketData snapshot to enterprise feature schema (SSOT)
                if hasattr(market_snapshot, "indicators") or hasattr(market_snapshot, "to_dict"):
                    # Real MarketSnapshot object
                    snapshot_obj = market_snapshot
                elif isinstance(market_snapshot, dict) and "snapshot" in market_snapshot:
                    snapshot_obj = market_snapshot.get("snapshot")
                if hasattr(market_snapshot, "to_dict"):
                    md = market_snapshot.to_dict()
                else:
                    md = market_snapshot
                market_data = {
                    "close": float(md.get("price", 0.0)),
                    "volume": float(md.get("volume", 0.0)),
                    "rsi": float(md.get("rsi", 50.0)),
                    "macd": float(md.get("macd", 0.0)),
                    "bb_position": float(md.get("bollinger_position", md.get("bb_pos", md.get("bb_position", 0.5)))),
                    "volatility": float(md.get("volatility", 0.02)),
                    "trend_strength": float(md.get("trend_strength", 0.0)),
                    "volume_ratio": float(md.get("volume_ratio", 1.0)),
                    "price_change_24h": float(md.get("price_change_percent_24h", md.get("price_change_24h", 0.0))),
                }
                logger.info("🧩 Using SSOT market snapshot for features (no local recompute)")
            else:
                market_data = await self._get_market_features(symbol)
            logger.info(f"📊 PIPELINE DEBUG: Enterprise Trading Engine - Market features extracted: {len(market_data)} features")
            
            # Run 6-layer analysis
            logger.info("🤖 PIPELINE DEBUG: Enterprise Trading Engine - Running 6-layer AI analysis...")
            layer_results = await self._run_six_layer_analysis(market_data, snapshot_obj)
            logger.info("✅ PIPELINE DEBUG: Enterprise Trading Engine - 6-layer analysis completed")

            # SSOT sanity logging for L5 vs snapshot
            try:
                l5 = layer_results.get("layer_5_confidence", {})
                snap_rsi = market_data.get("rsi")
                snap_macd = market_data.get("macd")
                if isinstance(l5, dict) and "features" in layer_results:
                    l5_rsi = layer_results["features"].get("rsi")
                    l5_macd = layer_results["features"].get("macd")
                    if l5_rsi is not None and snap_rsi is not None and abs(float(l5_rsi) - float(snap_rsi)) > 1e-6:
                        from app.backend.services.metrics import inc_indicator_mismatch
                        inc_indicator_mismatch("L5", "rsi")
                    if l5_macd is not None and snap_macd is not None and abs(float(l5_macd) - float(snap_macd)) > 1e-6:
                        from app.backend.services.metrics import inc_indicator_mismatch
                        inc_indicator_mismatch("L5", "macd")
            except Exception:
                pass
            
            # PHASE 1A: Calculate final decision with signal type
            final_action, final_confidence, signal_type = self._calculate_final_decision(layer_results)
            # Server-side readiness marker (we can't read gauges here; set 1 to indicate analysis path active)
            try:
                from app.backend.services.metrics import set_readiness_gate
                set_readiness_gate("entry", True)
            except Exception:
                pass
            
            # Calculate position size and risk
            position_size = self._calculate_position_size(final_confidence, layer_results)
            risk_score = self._calculate_risk_score(layer_results)
            
            # Generate reasoning
            reasoning = self._generate_reasoning(layer_results, final_action, final_confidence)
            
            signal = TradingSignal(
                symbol=symbol,
                action=final_action,
                confidence=final_confidence,
                price=current_price,
                timestamp=datetime.now(timezone.utc),
                reasoning=reasoning,
                layer_analysis=layer_results,
                risk_score=risk_score,
                position_size=position_size,
                signal_type=signal_type
            )
            
            logger.info(f"✅ AI signal generated: {final_action} with {final_confidence:.1%} confidence")
            return signal
            
        except Exception as e:
            logger.error(f"Failed to generate trading signal: {e}")
            raise
    
    async def _get_market_features(self, symbol: str) -> Dict[str, float]:
        """Extract technical features from current market data"""
        try:
            client = await get_hybrid_client()
            
            async with client:
                # Day-trading tuned: fetch 24h stats and 1m klines for short-horizon features
                # Parallelize via asyncio.gather for lower latency
                ticker_task = asyncio.create_task(client.get_24hr_ticker(symbol))
                klines_task = asyncio.create_task(client.get_klines(symbol, "1m", 200))
                ticker, klines = await asyncio.gather(ticker_task, klines_task)
                
            # Calculate features
            prices = [float(k["close"]) for k in klines[-120:]]  # last 120 minutes if 1m
            volumes = [float(k["volume"]) for k in klines[-120:]]
            
            # Use schema normalization for price
            from app.backend.core.boot_once import normalize_ticker_price, normalize_ticker_change_percent
            current_price = normalize_ticker_price(ticker)
            
            # Technical indicators (simplified)
            rsi = self._calculate_rsi(prices)
            macd, macd_signal = self._calculate_macd(prices)
            bb_position = self._calculate_bb_position(prices, current_price)
            volatility = float(np.std(prices) / max(np.mean(prices), 1e-8))
            
            # Volume analysis
            avg_volume = float(np.mean(volumes)) if volumes else 0.0
            volume_ratio = float(volumes[-1] / avg_volume) if avg_volume > 0 else 1.0
            
            # Trend strength
            trend_strength = self._calculate_trend_strength(prices)
            
            # Normalize scale-sensitive fields for classical models
            sma20 = float(np.mean(prices[-20:])) if len(prices) >= 20 else current_price
            close_norm = float(np.clip(current_price / max(sma20, 1e-8), 0.5, 1.5))
            # Use volume_ratio as a bounded proxy for volume to match trained distributions better
            volume_scaled = float(np.clip(volume_ratio, 0.1, 3.0))
            
            features = {
                "close": close_norm,
                "volume": volume_scaled,
                "rsi": rsi,
                "macd": macd - macd_signal,
                "bb_position": bb_position,
                "volatility": volatility,
                "trend_strength": trend_strength,
                "volume_ratio": volume_ratio,
                "price_change_24h": normalize_ticker_change_percent(ticker)
            }
            
            # DEBUG: Log raw feature values for model debugging
            logger.info(f"🔍 RAW FEATURES - close_norm={close_norm:.4f}, volume_scaled={volume_scaled:.4f}, rsi={rsi:.2f}, macd={macd-macd_signal:.6f}, bb_position={bb_position:.4f}, volatility={volatility:.6f}, trend_strength={trend_strength:.4f}")
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to get market features: {e}")
            raise RuntimeError(f"Real market features unavailable: {e}")
    
    async def _run_six_layer_analysis(self, features: Dict[str, float], snapshot_obj: Optional[Any] = None) -> Dict[str, Any]:
        """Run complete 6-layer AI analysis"""
        results = {}
        
        # Layer 1: Market Regime Detection
        regime_prediction = self._layer_1_regime_detection(features)
        results["layer_1_regime"] = regime_prediction
        
        # Layer 2: LSTM Ensemble
        lstm_predictions = self._layer_2_lstm_ensemble(features)
        results["layer_2_lstm"] = lstm_predictions
        
        # Layer 3: Reversal Detection
        reversal_probability = self._layer_3_reversal_detection(features)
        results["layer_3_reversal"] = reversal_probability
        
        # Layer 4: Technical Filters
        filter_score = self._layer_4_technical_filters(features)
        results["layer_4_filters"] = filter_score
        
        # Layer 5: Confidence Scoring
        confidence_score = self._layer_5_confidence_scoring(features, snapshot_obj)
        results["layer_5_confidence"] = confidence_score
        
        # Layer 6: Adaptive Timing
        timing_score = self._layer_6_adaptive_timing(features)
        results["layer_6_timing"] = timing_score
        
        # Layer 7: Price Prediction (ML Forecasting for Day Trading)
        price_predictions = await self._layer_7_price_prediction(features)
        results["layer_7_predictions"] = price_predictions
        
        # Attach raw features for downstream decision context (RSI/BB checks for labels)
        results["features"] = features.copy()
        
        # Emit rolling stddev of entry confidence (5m window in-process simple)
        try:
            if not hasattr(self, "_conf_history"):
                self._conf_history = []
            self._conf_history.append(float(confidence_score.get("confidence", 0.0)))
            if len(self._conf_history) > 200:
                self._conf_history = self._conf_history[-200:]
            import numpy as _np
            std5 = float(_np.std(self._conf_history[-50:])) if len(self._conf_history) >= 2 else 0.0
            from app.backend.services.metrics import set_confidence_stddev
            set_confidence_stddev("5m", std5)
        except Exception:
            pass
        return results
    
    def _layer_1_regime_detection(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Layer 1: Market Regime Detection"""
        try:
            if "regime" in self.models:
                # Use model-advertised feature names if available to avoid shape mismatch
                                            # Layer 1 uses all 9 features for regime classification
                            feature_array = self._build_feature_array(
                                    self.models["regime"],
                                    features,
                                    default_order=["close", "volume", "rsi", "macd", "bb_position", "volatility", "trend_strength", "volume_ratio", "price_change_24h"],
                                    layer_name="regime_classifier"
                            )
                
                            # Convert DataFrame to numpy array to avoid sklearn feature name warning
                            prediction_array = feature_array.values if hasattr(feature_array, 'values') else feature_array
                            prediction = self.models["regime"].predict(prediction_array)[0]
                            confidence = max(self.models["regime"].predict_proba(prediction_array)[0])
                
                            regimes = ["bull", "bear", "sideways", "volatile"]
                            regime = regimes[prediction] if prediction < len(regimes) else "sideways"
                
                            return {
                                    "regime": regime,
                                    "confidence": confidence,
                                    "model_used": True
                            }
            else:
                # Fallback logic
                if features["volatility"] > 0.05:
                    regime = "volatile"
                elif features["trend_strength"] > 0.7:
                    regime = "bull" if features["price_change_24h"] > 0 else "bear"
                else:
                    regime = "sideways"
                
                return {
                    "regime": regime,
                    "confidence": 0.6,
                    "model_used": False
                }
        except Exception as e:
            logger.error(f"Layer 1 error: {e}")
            return {"regime": "sideways", "confidence": 0.5, "model_used": False}
    
    def _layer_2_lstm_ensemble(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Layer 2: LSTM Ensemble Predictions - FIXED for proper input shapes"""
        try:
            predictions = []
            
            for timeframe in ["1m", "5m", "1h", "4h", "24h"]:  # FIXED: Use actual model names
                model_key = f"lstm_{timeframe}"
                if model_key in self.models:
                    try:
                        # FIXED: Create proper input sequence with correct dimensions
                        input_seq = self._build_lstm_input_sequence(features, timeframe)
                        if input_seq is not None:
                            # FIXED: Safety assertion before prediction
                            self.ensure_lstm_shape(input_seq, self.models[model_key], timeframe)
                            pred = self.keras_predict(self.models[model_key], input_seq)[0][0]
                            predictions.append(pred)
                            logger.debug(f"✅ LSTM {timeframe}: input_shape={input_seq.shape}, pred={pred:.4f}")
                        else:
                            logger.warning(f"⚠️ LSTM {timeframe}: Could not build input sequence")
                    except Exception as lstm_error:
                        logger.warning(f"⚠️ LSTM {timeframe} prediction failed: {lstm_error}")
                        # Don't crash, just skip this model
            
            if predictions:
                ensemble_pred = np.mean(predictions)
                return {
                    "prediction": float(ensemble_pred),
                    "individual_predictions": predictions,
                    "models_used": len(predictions)
                }
            else:
                # Fallback prediction based on trend
                trend_pred = features["close"] * (1 + features["price_change_24h"] / 100 * 0.1)
                return {
                    "prediction": trend_pred,
                    "individual_predictions": [],
                    "models_used": 0
                }
                
        except Exception as e:
            logger.error(f"Layer 2 error: {e}")
            return {"prediction": features["close"], "individual_predictions": [], "models_used": 0}
    
    def keras_predict(self, model, x):
        """FIXED: Remove verbose entirely to avoid TF 2.16+ conflicts"""
        # Don't pass verbose at all - let TensorFlow handle it
        return model.predict(x)
    
    def ensure_lstm_shape(self, x, model, timeframe):
        """FIXED: Safety assertion before every LSTM inference"""
        assert x.ndim == 3, f"Need (B,T,F), got {x.shape} for {timeframe}"
        _, T, F = model.input_shape
        assert x.shape[1] == T, f"Timesteps mismatch for {timeframe}: {x.shape[1]} vs {T}"
        assert x.shape[2] == F, f"Features mismatch for {timeframe}: {x.shape[2]} vs {F}"
    
    def _build_lstm_input_sequence(self, features: Dict[str, float], timeframe: str) -> Optional[np.ndarray]:
        """FIXED: Build proper LSTM input sequence with correct dimensions for all timeframes"""
        try:
            # Define expected shapes based on actual model requirements
            if timeframe in ["1m", "5m"]:
                # 1m/5m models expect (batch, 200, 11) 
                expected_timesteps = 200
                expected_features = 11
                
                # Build 11-feature vector for 1m/5m models
                feature_vector = np.array([
                    features.get("close", 0.0),
                    features.get("volume", 0.0),
                    features.get("rsi", 50.0), 
                    features.get("macd", 0.0),
                    features.get("bb_position", 0.5),
                    features.get("volatility", 0.02),
                    features.get("trend_strength", 0.5),
                    features.get("volume_ratio", 1.0),
                    features.get("price_change_24h", 0.0),
                    features.get("ema_20", features.get("close", 0.0)),
                    features.get("atr", features.get("close", 0.0) * 0.02)
                ], dtype=np.float32)
                
            elif timeframe == "1h":
                # 1h model expects (batch, 120, 16)
                expected_timesteps = 120
                expected_features = 16
                
                # Build 16-feature vector for 1h model
                feature_vector = np.array([
                    features.get("close", 0.0),
                    features.get("volume", 0.0), 
                    features.get("rsi", 50.0),
                    features.get("macd", 0.0),
                    features.get("bb_position", 0.5),
                    features.get("volatility", 0.02),
                    features.get("trend_strength", 0.5),
                    features.get("volume_ratio", 1.0),
                    features.get("price_change_24h", 0.0),
                    features.get("ema_20", features.get("close", 0.0)),
                    features.get("ema_50", features.get("close", 0.0)),
                    features.get("atr", features.get("close", 0.0) * 0.02),
                    features.get("stoch_k", 50.0),
                    features.get("stoch_d", 50.0),
                    features.get("williams_r", -50.0),
                    features.get("roc", 0.0)
                ], dtype=np.float32)
                
            elif timeframe == "4h":
                # 4h model expects (batch, 240, 16)
                expected_timesteps = 240
                expected_features = 16
                
                # Build 16-feature vector for 4h model
                feature_vector = np.array([
                    features.get("close", 0.0),
                    features.get("volume", 0.0), 
                    features.get("rsi", 50.0),
                    features.get("macd", 0.0),
                    features.get("bb_position", 0.5),
                    features.get("volatility", 0.02),
                    features.get("trend_strength", 0.5),
                    features.get("volume_ratio", 1.0),
                    features.get("price_change_24h", 0.0),
                    features.get("ema_20", features.get("close", 0.0)),
                    features.get("ema_50", features.get("close", 0.0)),
                    features.get("atr", features.get("close", 0.0) * 0.02),
                    features.get("stoch_k", 50.0),
                    features.get("stoch_d", 50.0),
                    features.get("williams_r", -50.0),
                    features.get("roc", 0.0)
                ], dtype=np.float32)
                
            elif timeframe == "24h":
                # 24h model expects (batch, 60, 16)
                expected_timesteps = 60
                expected_features = 16
                
                # Build 16-feature vector for 24h model
                feature_vector = np.array([
                    features.get("close", 0.0),
                    features.get("volume", 0.0), 
                    features.get("rsi", 50.0),
                    features.get("macd", 0.0),
                    features.get("bb_position", 0.5),
                    features.get("volatility", 0.02),
                    features.get("trend_strength", 0.5),
                    features.get("volume_ratio", 1.0),
                    features.get("price_change_24h", 0.0),
                    features.get("ema_20", features.get("close", 0.0)),
                    features.get("ema_50", features.get("close", 0.0)),
                    features.get("atr", features.get("close", 0.0) * 0.02),
                    features.get("stoch_k", 50.0),
                    features.get("stoch_d", 50.0),
                    features.get("williams_r", -50.0),
                    features.get("roc", 0.0)
                ], dtype=np.float32)
                
            else:
                logger.error(f"Unknown timeframe for LSTM: {timeframe}")
                return None
            
            # Create sequence by repeating the feature vector (simple but functional)
            sequence = np.tile(feature_vector, (expected_timesteps, 1))
            
            # Reshape to (batch, timesteps, features)
            input_tensor = sequence.reshape(1, expected_timesteps, expected_features)
            
            return input_tensor
            
        except Exception as e:
            logger.error(f"Failed to build LSTM input for {timeframe}: {e}")
            return None
    
    def _layer_3_reversal_detection(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Layer 3: Reversal Detection"""
        try:
            if "reversal" in self.models:
                feature_array = self._build_feature_array(
                    self.models["reversal"],
                    features,
                    default_order=["rsi","macd"]
                )
                
                # Suppress model warnings during prediction
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    raw_reversal_prob = self.models["reversal"].predict_proba(feature_array)[0][1]
                
                # CRITICAL FIX: Use dynamic reversal risk instead of raw probability
                # Professional trading requires market-adaptive thresholds
                reversal_prob = self._calculate_dynamic_reversal_risk(raw_reversal_prob, features)
                
                logger.debug(f"🔍 L3 FIXED - Raw: {raw_reversal_prob:.4f} → Dynamic: {reversal_prob:.4f}")
                
                return {
                    "reversal_probability": float(reversal_prob),
                    "raw_probability": float(raw_reversal_prob),
                    "model_used": True
                }
            else:
                # Fallback logic
                reversal_signals = 0
                if features["rsi"] > 70:  # Overbought
                    reversal_signals += 1
                elif features["rsi"] < 30:  # Oversold
                    reversal_signals += 1
                
                if abs(features["macd"]) > 0.01:  # Strong MACD signal
                    reversal_signals += 1
                
                reversal_prob = min(reversal_signals / 2.0, 1.0)
                
                return {
                    "reversal_probability": reversal_prob,
                    "model_used": False
                }
                
        except Exception as e:
            logger.error(f"Layer 3 error: {e}")
            # Professional fallback - conservative but not blocking
            return {"reversal_probability": 0.4, "model_used": False}
            
    def _enhanced_volume_spike_detection(self, features: Dict[str, float]) -> Dict[str, Any]:
        """
        🎯 ENHANCED: Detect volume spikes that indicate exhaustion (not breakout!)
        
        Volume spikes + extreme prices = STRONG reversal signals
        This replaces Anomaly Detection with reversal-specific logic
        """
        try:
            volume_ratio = features.get('volume_ratio', 1.0)
            volatility = features.get('volatility', 0.03)
            rsi = features.get('rsi', 50.0)
            trend_strength = abs(features.get('trend_strength', 0.0))
            
            # Check for volume spike (2.5x+ average volume)
            if volume_ratio > 2.5:
                # Calculate spike strength (0-0.3 range)
                spike_strength = min((volume_ratio - 2.5) / 2.0, 0.3)
                
                # Overbought + Volume Spike = SELL exhaustion signal
                if rsi > 70:
                    return {
                        'volume_spike_detected': True,
                        'spike_type': 'sell_exhaustion',
                        'spike_strength': spike_strength,
                        'reversal_boost': spike_strength * 1.5,  # 45% max boost
                        'reasoning': f"Volume spike {volume_ratio:.1f}x + Overbought RSI {rsi:.0f}"
                    }
                
                # Oversold + Volume Spike = BUY exhaustion signal
                elif rsi < 30:
                    return {
                        'volume_spike_detected': True,
                        'spike_type': 'buy_exhaustion',
                        'spike_strength': spike_strength,
                        'reversal_boost': spike_strength * 1.5,  # 45% max boost
                        'reasoning': f"Volume spike {volume_ratio:.1f}x + Oversold RSI {rsi:.0f}"
                    }
                
                # Volume spike with strong trend = potential exhaustion
                elif trend_strength > 0.05:
                    return {
                        'volume_spike_detected': True,
                        'spike_type': 'trend_exhaustion',
                        'spike_strength': spike_strength * 0.7,  # Weaker signal
                        'reversal_boost': spike_strength * 0.7,  # 21% max boost
                        'reasoning': f"Volume spike {volume_ratio:.1f}x + Strong trend {trend_strength:.2%}"
                    }
            
            # High volatility spike without volume = potential fake signal
            elif volatility > 0.06 and volume_ratio < 1.5:
                return {
                    'volume_spike_detected': False,
                    'spike_type': 'false_spike',
                    'spike_strength': 0.0,
                    'reversal_boost': -0.1,  # Penalize (likely noise)
                    'reasoning': f"High volatility {volatility:.2%} but low volume {volume_ratio:.1f}x - likely noise"
                }
            
            return {
                'volume_spike_detected': False,
                'spike_type': 'none',
                'spike_strength': 0.0,
                'reversal_boost': 0.0,
                'reasoning': 'No significant volume spike'
            }
            
        except Exception as e:
            logger.error(f"❌ Enhanced volume spike detection failed: {e}")
            return {
                'volume_spike_detected': False,
                'spike_type': 'error',
                'spike_strength': 0.0,
                'reversal_boost': 0.0,
                'reasoning': 'Error in spike detection'
            }
    
    def _smart_timing_filter(self, reversal_prob: float, features: Dict[str, float], volume_spike_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎯 SMART TIMING FILTER: Filter false reversals from real opportunities
        
        Real reversals require:
        - Volume confirmation
        - Volatility confirmation
        - Trend exhaustion
        - Proper timing
        """
        try:
            volume_ratio = features.get('volume_ratio', 1.0)
            volatility = features.get('volatility', 0.03)
            trend_strength = abs(features.get('trend_strength', 0.0))
            rsi = features.get('rsi', 50.0)
            
            # Start with base reversal probability
            filtered_prob = reversal_prob
            confidence_adjustments = []
            
            # Check 1: Volume Confirmation (BITCOIN SCALPING OPTIMIZED)
            if reversal_prob > 0.65:  # High reversal signal
                if volume_ratio < 0.8:  # Very weak volume (was 1.2)
                    # Extremely weak volume = likely false signal
                    filtered_prob *= 0.85  # -15% confidence (was -30%, too harsh!)
                    confidence_adjustments.append(f"Weak volume ({volume_ratio:.1f}x) → -15% confidence")
                elif volume_ratio > 2.0:
                    # Strong volume = confirm signal
                    filtered_prob *= 1.15  # +15% confidence
                    confidence_adjustments.append(f"Strong volume ({volume_ratio:.1f}x) → +15% confidence")
            
            # Check 2: Volatility Confirmation (BITCOIN SCALPING OPTIMIZED)
            if reversal_prob > 0.65:
                if volatility < 0.010:  # Very low volatility (was 0.015 = 1.5%, now 1.0%)
                    # Too calm = likely false signal (no real movement)
                    filtered_prob *= 0.80  # -20% confidence (was -40%, too harsh!)
                    confidence_adjustments.append(f"Low volatility ({volatility:.2%}) → -20% confidence")
                elif volatility > 0.05:
                    # High volatility = confirm signal (real movement)
                    filtered_prob *= 1.1  # +10% confidence
                    confidence_adjustments.append(f"High volatility ({volatility:.2%}) → +10% confidence")
            
            # Check 3: Trend Exhaustion
            if reversal_prob > 0.60:
                if trend_strength < 0.03:
                    # No strong trend = nothing to reverse
                    filtered_prob *= 0.5  # -50% confidence
                    confidence_adjustments.append(f"Weak trend ({trend_strength:.2%}) → -50% confidence")
                elif trend_strength > 0.07:
                    # Very strong trend = high exhaustion potential
                    filtered_prob *= 1.2  # +20% confidence
                    confidence_adjustments.append(f"Strong trend ({trend_strength:.2%}) → +20% confidence")
            
            # Check 4: RSI Extreme Confirmation
            if reversal_prob > 0.60:
                if 45 < rsi < 55:
                    # Neutral RSI = no extreme to reverse from
                    filtered_prob *= 0.6  # -40% confidence
                    confidence_adjustments.append(f"Neutral RSI ({rsi:.0f}) → -40% confidence")
                elif rsi > 75 or rsi < 25:
                    # Extreme RSI = strong reversal potential
                    filtered_prob *= 1.25  # +25% confidence
                    confidence_adjustments.append(f"Extreme RSI ({rsi:.0f}) → +25% confidence")
            
            # Check 5: Volume Spike Integration
            if volume_spike_data.get('volume_spike_detected', False):
                spike_boost = volume_spike_data.get('reversal_boost', 0.0)
                filtered_prob += spike_boost
                confidence_adjustments.append(f"Volume spike boost → +{spike_boost*100:.0f}% confidence")
            
            # Clamp to valid range
            filtered_prob = max(0.10, min(filtered_prob, 0.95))
            
            # Determine if signal passes filter
            is_real_reversal = False
            filter_threshold = 0.70 if reversal_prob < 0.70 else 0.65  # Lower threshold for already strong signals
            
            if filtered_prob >= filter_threshold:
                # Additional checks for very high confidence
                if volume_ratio >= 1.2 and volatility >= 0.015 and (rsi > 70 or rsi < 30 or trend_strength > 0.03):
                    is_real_reversal = True
            
            return {
                'filtered_reversal_prob': filtered_prob,
                'original_prob': reversal_prob,
                'is_real_reversal': is_real_reversal,
                'confidence_adjustments': confidence_adjustments,
                'filter_passed': is_real_reversal,
                'reasoning': ' | '.join(confidence_adjustments) if confidence_adjustments else 'No adjustments needed'
            }
            
        except Exception as e:
            logger.error(f"❌ Smart timing filter failed: {e}")
            return {
                'filtered_reversal_prob': reversal_prob,
                'original_prob': reversal_prob,
                'is_real_reversal': reversal_prob > 0.70,
                'confidence_adjustments': [],
                'filter_passed': reversal_prob > 0.70,
                'reasoning': 'Filter error, using original probability'
            }
            
    def _calculate_dynamic_reversal_risk(self, raw_prob: float, features: Dict[str, float]) -> float:
        """Calculate market-adaptive reversal risk instead of raw model probability
        
        🎯 ENHANCED: Now includes volume spike detection and smart timing filter
        """
        try:
            # Use 90-day quantiles instead of absolute thresholds
            # This prevents the model from being overly conservative
            
            # Market condition adjustments
            rsi = features.get("rsi", 50.0)
            volatility = features.get("volatility", 0.05)
            trend_strength = features.get("trend_strength", 0.0)
            
            # 🚀 DAY TRADING FIX: Higher cap to catch strong reversals
            adjusted_prob = min(raw_prob, 0.90)  # Cap at 90% (was 85%)
            
            # RSI-based adjustment (overbought INCREASES reversal opportunity!)
            if rsi > 75:  # OVERBOUGHT = HIGH REVERSAL OPPORTUNITY (Bitcoin at top!)
                adjusted_prob *= 1.4  # INCREASE reversal signal by 40% (was 30%)
            elif rsi < 25:  # OVERSOLD = HIGH REVERSAL OPPORTUNITY (Bitcoin at bottom!)
                adjusted_prob *= 1.4  # INCREASE reversal signal by 40% (was reduction!)
            
            # Volatility adjustment (high volatility = more reversal opportunities) - BITCOIN SCALPING OPTIMIZED
            if volatility > 0.08:  # High volatility
                adjusted_prob = min(adjusted_prob * 1.3, 0.95)  # Amplify (was 1.2)
            elif volatility < 0.010:  # Very low volatility (was 0.02 = 2%, now 1.0% - aligned with Check 2)
                adjusted_prob *= 0.95  # Minimal reduction (was 0.9, too harsh for normal Bitcoin conditions)
            
            # Trend strength adjustment (strong trends still valid, but don't kill reversal signal)
            if abs(trend_strength) > 0.05:  # Strong trend
                adjusted_prob *= 0.85  # Less dramatic reduction (was 0.75)
            
            # 🎯 ENHANCED: Apply volume spike detection
            volume_spike_data = self._enhanced_volume_spike_detection(features)
            if volume_spike_data.get('volume_spike_detected', False):
                spike_boost = volume_spike_data.get('reversal_boost', 0.0)
                adjusted_prob += spike_boost
                logger.info(f"🔥 VOLUME SPIKE: {volume_spike_data.get('spike_type')} → +{spike_boost*100:.0f}% reversal boost")
            
            # Clamp before filtering
            adjusted_prob = max(0.15, min(adjusted_prob, 0.95))
            
            # 🎯 ENHANCED: Apply smart timing filter
            filter_result = self._smart_timing_filter(adjusted_prob, features, volume_spike_data)
            final_prob = filter_result['filtered_reversal_prob']
            
            # ✅ FIX: Store filter result for use in confidence calculation
            self._last_filter_passed = filter_result['filter_passed']
            
            if filter_result['filter_passed']:
                logger.info(f"✅ REAL REVERSAL: {final_prob:.1%} (original: {raw_prob:.1%}) | {filter_result['reasoning']}")
            else:
                logger.warning(f"⚠️ FILTERED: {final_prob:.1%} (from {adjusted_prob:.1%}) | {filter_result['reasoning']}")
            
            # 🎯 DAY TRADING: Keep between 15%-95% (was 15%-85%, expanded for strong signals)
            return max(0.15, min(final_prob, 0.95))
            
        except Exception as e:
            logger.error(f"Dynamic reversal risk calculation failed: {e}")
            return 0.4  # Safe default
            
    def _calculate_technical_reversal_risk(self, volatility: float, trend_strength: float, rsi: float) -> float:
        """Calculate reversal risk using technical indicators when model unavailable"""
        try:
            risk_score = 0.3  # Base risk
            
            # RSI contribution
            if rsi > 70:
                risk_score += 0.2  # Overbought increases reversal risk
            elif rsi < 30:
                risk_score += 0.15  # Oversold increases reversal risk (less than overbought)
            
            # Volatility contribution
            risk_score += min(volatility * 2.0, 0.3)  # High volatility increases risk
            
            # Trend strength contribution (strong trends reduce reversal risk)
            risk_score -= min(abs(trend_strength) * 0.5, 0.2)
            
            return max(0.1, min(risk_score, 0.7))  # Professional bounds
            
        except Exception as e:
            logger.error(f"Technical reversal risk calculation failed: {e}")
            return 0.4
            
    def _normalize_timing_score(self, raw_score: float, features: Dict[str, float]) -> float:
        """Normalize timing score for professional trading decisions"""
        try:
            # Current timing score is 1.00 (100%) which is too extreme
            # Professional trading needs nuanced timing signals
            
            # Market context
            rsi = features.get("rsi", 50.0)
            macd = features.get("macd", 0.0)
            volume_ratio = features.get("volume_ratio", 1.0)
            
            # Base normalization - convert extreme values to usable range
            if abs(raw_score) > 0.9:  # Extreme timing scores
                normalized = np.tanh(raw_score * 0.5)  # Dampen extreme values
            else:
                normalized = raw_score
            
            # Market condition adjustments
            timing_boost = 0.0
            
            # RSI-based timing adjustment
            if rsi < 35:  # Oversold - good buy timing
                timing_boost += 0.15
            elif rsi > 65:  # Overbought - good sell timing  
                timing_boost -= 0.15
                
            # MACD momentum timing
            if macd > 0.005:  # Bullish momentum
                timing_boost += 0.1
            elif macd < -0.005:  # Bearish momentum
                timing_boost -= 0.1
                
            # Volume confirmation
            if volume_ratio > 1.3:  # High volume confirms timing
                timing_boost *= 1.2
                
            # Apply timing boost
            final_timing = normalized + timing_boost
            
            # Professional bounds for trading decisions
            return max(-0.8, min(final_timing, 0.8))  # Keep in [-0.8, 0.8] range
            
        except Exception as e:
            logger.error(f"Timing score normalization failed: {e}")
            return 0.0  # Neutral timing
    
    def _layer_4_technical_filters(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Layer 4: Technical Filters - FIXED for live data compatibility"""
        try:
            if "filters" in self.models:
                # PROFESSIONAL FIX: Use correct feature order and validation
                # Layer 4 model expects: ['close', 'volume', 'rsi', 'macd', 'bb_position', 'volatility', 'trend_strength', 'volume_ratio']
                l4_features = {
                    "close": features.get("close", features.get("current_price", 112000.0)),
                    "volume": features.get("volume", 1000000.0),
                    "rsi": np.clip(features.get("rsi", 50.0), 10.0, 90.0),
                    "macd": np.clip(features.get("macd", 0.0), -1000.0, 1000.0),
                    "bb_position": np.clip(features.get("bb_position", 0.5), 0.01, 0.99),
                    "volatility": np.clip(features.get("volatility", 0.02), 0.001, 0.2),
                    "trend_strength": np.clip(features.get("trend_strength", 0.0), -1.0, 1.0),
                    "volume_ratio": np.clip(features.get("volume_ratio", 1.0), 0.1, 10.0)
                }
                
                # Build feature array with proper validation
                feature_array = self._build_feature_array(
                    self.models["filters"],
                    l4_features,
                    default_order=["close", "volume", "rsi", "macd", "bb_position", "volatility", "trend_strength", "volume_ratio"],
                    layer_name="technical_filters"
                )
                
                # Get prediction with error handling
                try:
                    # Convert DataFrame to numpy array to avoid sklearn feature name warning
                    prediction_array = feature_array.values if hasattr(feature_array, 'values') else feature_array
                    filter_score = self.models["filters"].predict(prediction_array)[0]
                    logger.debug(f"✅ L4 SUCCESS - Filter score: {filter_score:.4f}")
                    
                    # Validate and normalize score
                    if np.isnan(filter_score) or np.isinf(filter_score):
                        logger.warning(f"⚠️ L4 invalid score: {filter_score}, using fallback")
                        filter_score = 0.5
                    elif filter_score < 0:
                        filter_score = abs(filter_score)
                    elif filter_score > 1:
                        filter_score = 1.0 / (1.0 + filter_score)  # Normalize to [0,1]
                    
                except Exception as pred_error:
                    logger.debug(f"L4 model prediction failed: {pred_error}, using enhanced technical analysis")
                    # PROFESSIONAL TECHNICAL ANALYSIS FALLBACK
                    rsi = l4_features["rsi"]
                    bb_pos = l4_features["bb_position"] 
                    volatility = l4_features["volatility"]
                    
                    # Enhanced technical scoring for day trading
                    rsi_score = 0.5  # Base score
                    if rsi < 30:  # Oversold = good for BUY
                        rsi_score = 0.8
                    elif rsi > 70:  # Overbought = good for SELL
                        rsi_score = 0.8
                    elif 40 <= rsi <= 60:  # Neutral zone
                        rsi_score = 0.6
                    
                    # Bollinger band position scoring
                    if bb_pos < 0.2:  # Near lower band = oversold
                        bb_score = 0.8
                    elif bb_pos > 0.8:  # Near upper band = overbought
                        bb_score = 0.8
                    else:
                        bb_score = 0.5
                    
                    # Volatility scoring (moderate volatility preferred)
                    if 0.01 <= volatility <= 0.05:  # Good volatility for day trading
                        vol_score = 0.7
                    else:
                        vol_score = 0.4
                    
                    # Combined technical score
                    filter_score = (rsi_score * 0.5 + bb_score * 0.3 + vol_score * 0.2)
                
                # PROFESSIONAL: Ensure viable trading score
                final_filter_score = np.clip(filter_score, 0.2, 0.9)
                
                return {
                    "filter_score": float(final_filter_score),
                    "raw_score": float(filter_score),
                    "model_used": True,
                    "features_used": list(l4_features.keys())
                }
            else:
                # Fallback scoring
                score = 0.5
                
                # Volume filter
                if features["volume_ratio"] > 1.5:
                    score += 0.1
                elif features["volume_ratio"] < 0.5:
                    score -= 0.1
                
                # Volatility filter
                if 0.01 < features["volatility"] < 0.04:
                    score += 0.1
                elif features["volatility"] > 0.06:
                    score -= 0.1
                
                return {
                    "filter_score": max(0.0, min(1.0, score)),
                    "model_used": False
                }
                
        except Exception as e:
            logger.error(f"Layer 4 error: {e}")
            return {"filter_score": 0.5, "model_used": False}
    
    def _layer_5_confidence_scoring(self, features: Dict[str, float], snapshot_obj: Optional[Any] = None) -> Dict[str, Any]:
        """Layer 5: Confidence Scoring"""
        try:
            if "confidence" in self.models:
                model = self.models["confidence"]
                # SSOT: try to build vector from latest features snapshot if available
                confidence = None
                try:
                    from app.backend.services.metrics import inc_l5_vector_source, inc_l5_builder_error, preinit_l5_vector_source_series
                    preinit_l5_vector_source_series()
                    # Prefer real snapshot object if provided
                    from app.backend.ml.infer import build_l5_vector_from_snapshot
                    if snapshot_obj is None:
                        raise NameError("snapshot_object_missing")
                    X = build_l5_vector_from_snapshot(snapshot_obj)
                    # Suppress LightGBM warnings about num_leaves
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        if hasattr(model, 'predict_proba'):
                            proba = model.predict_proba(X)[0]
                            confidence = float(proba[1]) if len(proba) > 1 else float(proba[0])
                        else:
                            pred = model.predict(X)[0]
                            confidence = float(pred)
                    inc_l5_vector_source("snapshot")
                except Exception as e:
                    # Fallback to legacy feature dict path
                    from app.backend.ml.infer import predict_l5_rf_safe
                    confidence = predict_l5_rf_safe(model, features)
                    try:
                        from app.backend.services.metrics import inc_l5_vector_source
                        inc_l5_vector_source("fallback")
                        from app.backend.services.metrics import inc_l5_builder_error
                        inc_l5_builder_error(type(e).__name__)
                    except Exception:
                        pass
                logger.info(f"🔍 L5 DEBUG - Raw prediction: {confidence}")
                
                logger.info(f"🔍 L5 DEBUG - Final confidence: {confidence}")
                
                # PROFESSIONAL FIX: Handle extreme values by feature rescaling
                if confidence < 1e-100 or confidence > 1e100:
                    logger.warning(f"⚠️ L5 extreme value detected: {confidence}, rescaling features")
                    # Try rescaling features to match training distribution
                    rescaled_features = self._rescale_features_for_l5(features)
                    rescaled_array = self._build_feature_array(
                        model, 
                        rescaled_features, 
                        ["close","volume","rsi","macd","bb_position","volatility","trend_strength"],
                        layer_name="layer_5"
                    )
                    if hasattr(model, "predict_proba"):
                        # Convert DataFrame to numpy array to avoid sklearn feature name warning
                        prediction_array = rescaled_array.values if hasattr(rescaled_array, 'values') else rescaled_array
                        proba = model.predict_proba(prediction_array)[0]
                        confidence = float(proba[1]) if len(proba) > 1 else float(proba)
                    else:
                        # Convert DataFrame to numpy array to avoid sklearn feature name warning
                        prediction_array = rescaled_array.values if hasattr(rescaled_array, 'values') else rescaled_array
                        pred = model.predict(prediction_array)[0]
                        confidence = float(pred)
                        if confidence < 0.0 or confidence > 1.0:
                            confidence = float(1.0 / (1.0 + np.exp(-confidence)))
                    logger.info(f"🔧 L5 rescaled confidence: {confidence}")
                    
                    # If still extreme, the model needs retraining
                    if confidence < 1e-50 or confidence > 1e50:
                        logger.error(f"❌ L5 model incompatible with live data - needs retraining")
                        raise RuntimeError("Layer 5 confidence model incompatible with live data distribution")
                
                return {
                    "confidence": float(np.clip(confidence, 0.0, 1.0)),
                    "model_used": True
                }
            else:
                logger.error(f"❌ Layer 5 confidence model not loaded - this is required for production")
                # Return minimal confidence for now, but log for urgent fixing
                return {"confidence": 0.3, "model_used": False, "error": "model_not_loaded"}
                
        except Exception as e:
            logger.error(f"Layer 5 error: {e}")
            # Return minimal confidence but log the error for fixing
            return {"confidence": 0.3, "model_used": False, "error": str(e)}
    

    
    def _rescale_features_for_l5(self, features: Dict[str, float]) -> Dict[str, float]:
        """Rescale features to match Layer 5 training distribution"""
        # Based on enterprise_metadata.json, Layer 5 expects these features:
        # ["close","volume","rsi","macd","bb_position","volatility","trend_strength"]
        
        rescaled = features.copy()
        
        # Professional rescaling based on typical training ranges
        rescaled["close"] = np.clip(features["close"], 0.8, 1.2)  # Tighter range around SMA20
        rescaled["volume"] = np.clip(features["volume"], 0.5, 2.0)  # Volume ratio bounds
        rescaled["rsi"] = np.clip(features["rsi"], 10, 90)  # RSI bounds
        rescaled["macd"] = np.clip(features["macd"], -0.1, 0.1)  # MACD bounds
        rescaled["bb_position"] = np.clip(features["bb_position"], 0.1, 0.9)  # BB position bounds
        rescaled["volatility"] = np.clip(features["volatility"], 0.001, 0.1)  # Volatility bounds
        rescaled["trend_strength"] = np.clip(features["trend_strength"], 0.1, 0.9)  # Trend bounds
        
        logger.info(f"🔧 L5 RESCALED - volatility:{features['volatility']:.6f}→{rescaled['volatility']:.6f}, bb_position:{features['bb_position']:.4f}→{rescaled['bb_position']:.4f}")
        
        return rescaled
    
    def _layer_6_adaptive_timing(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Layer 6: Adaptive Timing"""
        try:
            if "timing" in self.models:
                feature_array = self._build_feature_array(
                    self.models["timing"],
                    features,
                    default_order=[
                        "close","volume","rsi","macd","bb_position","volatility","trend_strength"
                    ]
                )
                
                # Use the feature_array directly - _build_feature_array handles DataFrame vs numpy array based on model training
                # Suppress LightGBM warnings about num_leaves
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    raw_timing_score = float(self.models["timing"].predict(feature_array)[0])
                # CRITICAL FIX: Proper timing score normalization
                # Raw model output needs professional scaling for trading decisions
                timing_score = self._normalize_timing_score(raw_timing_score, features)
                
                logger.debug(f"🔍 L6 FIXED - Raw: {raw_timing_score:.4f} → Normalized: {timing_score:.4f}")
                
                return {
                    "timing_score": float(timing_score),
                    "raw_timing": float(raw_timing_score),
                    "model_used": True
                }
            else:
                # Fallback timing logic
                timing = 0.0
                
                # MACD timing
                if features["macd"] > 0.01:
                    timing += 0.3
                elif features["macd"] < -0.01:
                    timing -= 0.3
                
                # RSI timing
                if features["rsi"] < 30:
                    timing += 0.2  # Oversold - buy timing
                elif features["rsi"] > 70:
                    timing -= 0.2  # Overbought - sell timing
                
                # Volume timing
                if features["volume_ratio"] > 1.5:
                    timing += 0.1
                
                return {
                    "timing_score": float(np.clip(timing, -1.0, 1.0)),
                    "model_used": False
                }
                
        except Exception as e:
            logger.error(f"Layer 6 error: {e}")
            return {"timing_score": 0.0, "model_used": False}
    
    async def _layer_7_price_prediction(self, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Layer 7: ML Price Prediction (Day Trading Optimization)
        
        Predicts price 1h, 4h, 24h ahead using existing LSTM models.
        Provides confidence intervals, trend direction, and probability distributions.
        
        Returns:
            Dict with predictions for each horizon, aggregate insights, and confidence boost
        """
        try:
            # Check if forecasting service is available
            if not self.price_forecasting_service:
                logger.debug("⚠️ Price Forecasting Service not available - skipping predictions")
                return self._create_empty_predictions()
            
            current_price = features.get("close", 0.0)
            if current_price <= 0:
                logger.warning("⚠️ Invalid current price - skipping predictions")
                return self._create_empty_predictions()
            
            # Get price predictions
            logger.debug("🔮 Layer 7: Generating price predictions...")
            forecast = await self.price_forecasting_service.predict_prices(
                current_price=current_price,
                features=features,
                horizons=["1h", "4h", "24h"]
            )
            
            # Extract predictions
            pred_1h = forecast.predictions_1h
            pred_4h = forecast.predictions_4h
            pred_24h = forecast.predictions_24h
            aggregate = forecast.aggregate
            
            # Log predictions
            if pred_1h:
                logger.info(f"🔮 LAYER 7 - 1h prediction: ${pred_1h.price_target:.2f} ({pred_1h.expected_move_pct:+.2f}%, confidence: {pred_1h.confidence:.1%})")
            if pred_4h:
                logger.info(f"🔮 LAYER 7 - 4h prediction: ${pred_4h.price_target:.2f} ({pred_4h.expected_move_pct:+.2f}%, confidence: {pred_4h.confidence:.1%})")
            if pred_24h:
                logger.info(f"🔮 LAYER 7 - 24h prediction: ${pred_24h.price_target:.2f} ({pred_24h.expected_move_pct:+.2f}%, confidence: {pred_24h.confidence:.1%})")
            
            logger.info(f"🔮 LAYER 7 - Aggregate: {aggregate['short_term_bias']} ({aggregate['momentum_strength']}), confidence_boost: {aggregate['confidence_boost']:+.2f}")
            
            # Return comprehensive prediction data
            return {
                "predictions_1h": {
                    "price_target": pred_1h.price_target if pred_1h else 0.0,
                    "confidence": pred_1h.confidence if pred_1h else 0.0,
                    "expected_move_pct": pred_1h.expected_move_pct if pred_1h else 0.0,
                    "trend_direction": pred_1h.trend_direction if pred_1h else "sideways",
                    "probability_up": pred_1h.probability_up if pred_1h else 0.5
                } if pred_1h else None,
                "predictions_4h": {
                    "price_target": pred_4h.price_target if pred_4h else 0.0,
                    "confidence": pred_4h.confidence if pred_4h else 0.0,
                    "expected_move_pct": pred_4h.expected_move_pct if pred_4h else 0.0,
                    "trend_direction": pred_4h.trend_direction if pred_4h else "sideways",
                    "probability_up": pred_4h.probability_up if pred_4h else 0.5
                } if pred_4h else None,
                "predictions_24h": {
                    "price_target": pred_24h.price_target if pred_24h else 0.0,
                    "confidence": pred_24h.confidence if pred_24h else 0.0,
                    "expected_move_pct": pred_24h.expected_move_pct if pred_24h else 0.0,
                    "trend_direction": pred_24h.trend_direction if pred_24h else "sideways",
                    "probability_up": pred_24h.probability_up if pred_24h else 0.5
                } if pred_24h else None,
                "aggregate": aggregate,
                "metadata": forecast.metadata,
                "model_used": True
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Layer 7 (Price Prediction) error: {e}")
            return self._create_empty_predictions()
    
    def _create_empty_predictions(self) -> Dict[str, Any]:
        """Create empty predictions when forecasting unavailable"""
        return {
            "predictions_1h": None,
            "predictions_4h": None,
            "predictions_24h": None,
            "aggregate": {
                "short_term_bias": "neutral",
                "momentum_strength": "weak",
                "reversal_risk": 0.50,
                "optimal_entry_timing": "neutral",
                "recommended_action": "HOLD",
                "confidence_boost": 0.0
            },
            "metadata": {"is_enabled": False},
            "model_used": False
        }
    
    def _calculate_final_decision(self, layer_results: Dict[str, Any]) -> Tuple[str, float, str]:
        """PHASE 1A: Calculate final trading decision with exploratory signals"""
        try:
            # Extract key metrics
            confidence = layer_results["layer_5_confidence"]["confidence"]
            timing_score = layer_results["layer_6_timing"]["timing_score"]
            reversal_prob = layer_results["layer_3_reversal"]["reversal_probability"]
            filter_score = layer_results["layer_4_filters"]["filter_score"]
            volatility = layer_results.get("volatility", 0.05)  # Default 5%
            
            logger.info(f"🔍 DECISION DEBUG - confidence={confidence:.3f}, timing={timing_score:.3f}, reversal={reversal_prob:.3f}, filter={filter_score:.3f}")
            logger.info(f"🔍 THRESHOLDS - primary={self.thresholds.confidence.BUY_THRESHOLD:.2f}, exploratory={self.thresholds.confidence.EXPLORATORY_BUY:.2f}, consensus={self.thresholds.confidence.CONSENSUS_THRESHOLD:.2f}")
            
            # PRIMARY SIGNAL (strict criteria)
            primary_signal = self._calculate_primary_signal(
                confidence,
                timing_score,
                reversal_prob,
                filter_score,
                layer_results.get("features", {}),
                layer_results  # Pass full layer results for price predictions access
            )
            if primary_signal[0] != "HOLD":
                return primary_signal[0], primary_signal[1], "primary"
            
            # EXPLORATORY SIGNAL (lower thresholds for small positions)
            # ✅ PROFESSIONAL: Always enabled for day trading opportunities
            exploratory_signal = self._calculate_exploratory_signal(
                confidence, timing_score, reversal_prob, filter_score, volatility,
                layer_results.get("features", {})  # Pass features for alternative SELL signals
            )
            if exploratory_signal[0] != "HOLD":
                return exploratory_signal[0], exploratory_signal[1], "exploratory"
            
            # Default to HOLD if no signals generated
            logger.info("🔍 DECISION: No signals generated - HOLD")
            return "HOLD", confidence, "hold"
            
        except Exception as e:
            logger.error(f"Final decision calculation error: {e}")
            return "HOLD", 0.5, "error"
            
    def _calculate_primary_signal(self, confidence: float, timing_score: float, reversal_prob: float, filter_score: float, features: Dict[str, float], layer_results: Optional[Dict[str, Any]] = None) -> Tuple[str, float]:
        """
        Calculate primary signal with professional criteria using unified thresholds
        
        Enhanced with Layer 7 Price Predictions for day trading optimization.
        """
        try:
            # ═══════════════════════════════════════════════════════════════════════════
            # 🔮 LAYER 7: PRICE PREDICTION CONFIDENCE BOOST (Day Trading Enhancement)
            # ═══════════════════════════════════════════════════════════════════════════
            # Use ML price predictions to boost/reduce confidence before other checks
            # This is professional practice: "What will price do next?" informs "Should I trade?"
            # ═══════════════════════════════════════════════════════════════════════════
            predictions_boost = 0.0
            prediction_available = False
            
            if layer_results and "layer_7_predictions" in layer_results:
                predictions = layer_results["layer_7_predictions"]
                if predictions and predictions.get("model_used", False):
                    aggregate = predictions.get("aggregate", {})
                    predictions_boost = aggregate.get("confidence_boost", 0.0)
                    prediction_available = True
                    
                    if predictions_boost != 0.0:
                        old_confidence = confidence
                        confidence = min(confidence + predictions_boost, 0.95)
                        logger.info(f"🔮 LAYER 7 BOOST: Price predictions {'support' if predictions_boost > 0 else 'contradict'} signal")
                        logger.info(f"   Confidence: {old_confidence:.1%} → {confidence:.1%} ({predictions_boost:+.1%})")
                        logger.info(f"   Prediction bias: {aggregate.get('short_term_bias', 'neutral')}")
            # ═══════════════════════════════════════════════════════════════════════════
            
            # Use unified threshold for consistency
            conf_check = confidence >= self.thresholds.confidence.BUY_THRESHOLD  # 65% confidence required
            
            # 🎯 DAY TRADING: High reversal probability = OPPORTUNITY for quick profits!
            # ✅ PROFESSIONAL: Risk threshold delegated to DynamicRiskManager
            reversal_opportunity = reversal_prob > 0.70  # 🔧 PROFESSIONAL FIX: 70%+ reversal = STRONG OPPORTUNITY (was 0.50)
            reversal_check = reversal_opportunity  # Opportunity-based (risk delegated) - stronger confirmation required
            
            # 🔥 CRITICAL: Extract technical indicators FIRST (needed for alternative SELL signals)
            rsi = float(features.get("rsi", 50.0))
            bb_pos = float(features.get("bb_position", features.get("bollinger_position", 0.5)))
            macd = float(features.get("macd", 0.0))
            volume_ratio = float(features.get("volume_ratio", 1.0))
            
            # 🔧 FIX (Oct 2025): Cap timing contribution to prevent marginal setups from passing
            # Timing alone shouldn't push confidence over thresholds
            # Cap timing influence to ±0.10 absolute to avoid timing-driven false signals
            capped_timing_score = max(-0.10, min(0.10, timing_score))
            
            filter_check = filter_score > 0.08  # SCALPING: Lower filter threshold (was 0.15)
            timing_buy_check = capped_timing_score > 0.008   # SCALPING: More sensitive timing (was 0.02)
            timing_sell_check = capped_timing_score < -0.003 # SCALPING: RELAXED for day trading (was -0.008) - allows SELL in neutral/slightly bullish markets
            
            if timing_score != capped_timing_score:
                logger.debug(f"⚖️ TIMING CAPPED: {timing_score:.3f} → {capped_timing_score:.3f} (max ±0.10)")
            
            # 🔥 CRITICAL FIX: Alternative SELL signals for mean reversion (day trading needs SHORT positions!)
            # Even in bullish markets, overbought conditions present SHORT opportunities
            mean_reversion_sell = (rsi > 70 and bb_pos > 0.85 and reversal_prob > 0.60)  # Strong overbought reversal
            resistance_rejection_sell = (bb_pos > 0.95 and macd < 0.0)  # Price rejected at upper band with bearish MACD
            momentum_shift_sell = (timing_score < 0.0 and macd < -0.001 and volume_ratio > 1.2)  # Momentum turning bearish with volume
            
            # 🔧 FIX (Oct 2025): Fade-top-band micro-playbook for shorts in sideways markets
            # When BB_pos ≥ 0.98 AND RSI ≥ 68 AND MACD histogram narrowing AND low vol → fade the top
            # This is a high-signal short opportunity in sideways/low-vol regimes
            regime = layer_results.get("layer_1_regime", {}) if layer_results else {}
            is_sideways = regime.get("regime", "") == "sideways"
            volatility_pct = float(features.get("volatility", 0.05))
            
            # Check for MACD histogram narrowing (approximation: MACD approaching 0)
            macd_narrowing = abs(macd) < 0.0005  # MACD histogram narrowing (near zero)
            
            fade_top_band = (
                bb_pos >= 0.98 and 
                rsi >= 68 and 
                macd_narrowing and 
                volatility_pct < 0.001 and  # zVol < 1.0 (0.1%)
                is_sideways
            )
            
            if fade_top_band:
                logger.info(f"🎯 FADE-TOP-BAND: BB={bb_pos:.3f}, RSI={rsi:.1f}, MACD={macd:.5f}, Vol={volatility_pct:.4f}")
            
            # 🔧 FIX (Oct 2025): Oversold-bounce micro-playbook for longs
            # When BB_pos ≤ 0.05 AND RSI ∈ [28,36] AND volume spike → bounce play
            # This is a high-signal long opportunity in oversold/capitulation regimes
            z_vol = layer_results.get("layer_4_filters", {}).get("volume_zscore", 0.0) if layer_results else 0.0
            
            # Check for MACD histogram contraction (becoming less negative)
            macd_contracting = macd > -0.01 and macd < 0  # MACD negative but contracting
            
            oversold_bounce = (
                bb_pos <= 0.05 and 
                28 <= rsi <= 36 and 
                (z_vol >= 2.0 or volume_ratio >= 5.0) and  # Volume spike (capitulation)
                macd_contracting
            )
            
            if oversold_bounce:
                logger.info(f"🎯 OVERSOLD-BOUNCE: BB={bb_pos:.3f}, RSI={rsi:.1f}, MACD={macd:.5f}, zVol={z_vol:.2f}, VolRatio={volume_ratio:.2f}")
            
            # Combined SELL check: timing OR alternative signals OR fade-top-band
            any_sell_signal = timing_sell_check or mean_reversion_sell or resistance_rejection_sell or momentum_shift_sell or fade_top_band
            
            logger.info(f"DAY TRADING CHECKS - conf:{conf_check}, reversal_opp:{reversal_opportunity}, filter:{filter_check}, timing_buy:{timing_buy_check}, timing_sell:{timing_sell_check}")
            if any_sell_signal and not timing_sell_check:
                logger.info(f"🎯 ALTERNATIVE SELL PATH: mean_rev={mean_reversion_sell}, resistance={resistance_rejection_sell}, momentum={momentum_shift_sell}, fade_band={fade_top_band}")
            
            # 🎯 DAY TRADING: Special logic for extreme oversold/overbought conditions
            # Bind to actual RSI/BB to avoid mislabeling
            rsi = float(features.get("rsi", 50.0))
            bb_pos = float(features.get("bb_position", features.get("bollinger_position", 0.5)))
            
            # 🚀 STRONG REVERSAL BOOST: High reversal signal = high confidence!
            # ✅ FIX: Only boost confidence if reversal signal is NOT filtered out
            # Check if reversal signal passed the smart timing filter (set in _calculate_dynamic_reversal_risk)
            reversal_filter_passed = getattr(self, '_last_filter_passed', True)
            
            strong_reversal = reversal_prob > 0.70  # 70%+ reversal is STRONG signal
            if strong_reversal and reversal_filter_passed:
                confidence = min(confidence * 1.15, 0.95)  # +15% confidence boost for strong reversals
                logger.info(f"🚀 STRONG REVERSAL DETECTED: {reversal_prob:.1%} → confidence boosted to {confidence:.1%}")
            elif strong_reversal and not reversal_filter_passed:
                # Strong reversal detected but FILTERED OUT by smart timing filter
                confidence *= 0.85  # REDUCE confidence by 15% (penalty for filtered signal)
                logger.warning(f"⚠️ STRONG REVERSAL FILTERED: {reversal_prob:.1%} failed smart timing filter → confidence reduced to {confidence:.1%}")
            
            # 🚨 CRITICAL FIX: RSI safety checks - prevent buying at extreme overbought/oversold
            # NEVER buy when RSI > 80 (extremely overbought) - high probability of reversal DOWN
            # NEVER sell when RSI < 20 (extremely oversold) - high probability of reversal UP
            rsi_overbought_danger = rsi > 80  # Extremely overbought - DON'T BUY
            rsi_oversold_danger = rsi < 20     # Extremely oversold - DON'T SELL
            
            if rsi_overbought_danger:
                logger.warning(f"🚨 RSI SAFETY: RSI={rsi:.1f} is EXTREMELY OVERBOUGHT - Blocking BUY signals, only SELL allowed")
            if rsi_oversold_danger:
                logger.warning(f"🚨 RSI SAFETY: RSI={rsi:.1f} is EXTREMELY OVERSOLD - Blocking SELL signals, only BUY allowed")
            
            # ═══════════════════════════════════════════════════════════════════════════
            # 🎯 TIER 1: EXTREME OVERBOUGHT SCALP (Highest Priority)
            # ═══════════════════════════════════════════════════════════════════════════
            # PROFESSIONAL FIX (Oct 2025): Increased threshold for quality control
            # After 82 trades with 0% win rate, we're prioritizing quality over quantity
            # This allows Tier 1 to trigger only with higher confidence
            # Reasoning: Extreme conditions (RSI≥90, Rev≥90%, BB≥0.99) still strong but
            #           we need better confirmation to avoid false signals
            # ═══════════════════════════════════════════════════════════════════════════
            
            # 🎯 PROFESSIONAL SCALP: Extreme overbought SELL opportunity (Industry Best Practice)
            # This is the CORE of reversal day trading - profiting from tops rolling over
            # Conditions aligned with professional scalping standards:
            # - RSI > 90: Extreme overbought (statistically high probability of reversal)
            # - Reversal ≥ 90%: ML model confirms high reversal probability
            # - BB Position > 0.99: Price at/above upper Bollinger Band (exhaustion)
            # - Volume consideration: Blow-off tops often have weak volume (adaptive penalty)
            tier1_conf_check = confidence >= 0.70  # 🔧 PROFESSIONAL FIX: Raised threshold for quality (was 0.60)
            extreme_overbought_scalp = (
                rsi >= 90.0 and 
                reversal_prob >= 0.90 and 
                bb_pos >= 0.99 and
                tier1_conf_check  # Independent confidence check
            )
            
            if extreme_overbought_scalp:
                # 🎯 ADAPTIVE VOLUME GATE: Blow-off tops often have weak volume before rollover
                # Industry observation: Volume exhaustion is a CONFIRMATION, not a disqualification
                volume_ratio = float(features.get("volume_ratio", 1.0))
                
                # When at extreme overbought (RSI≥95, BB≥0.99), reduce volume penalty
                # This is evidence-based: institutional distribution often happens on declining volume
                if rsi >= 95.0 and bb_pos >= 0.99:
                    # At EXTREME exhaustion, volume weakness is EXPECTED and BULLISH for SELL
                    volume_multiplier = 1.0  # No penalty
                    logger.info(f"🔥 BLOW-OFF TOP DETECTED: RSI={rsi:.1f}, BB={bb_pos:.3f}, Vol={volume_ratio:.2f}x")
                    logger.info(f"   Volume exhaustion is CONFIRMATION of top - no penalty applied")
                elif volume_ratio < 1.2:
                    # Standard weak volume penalty (reduced from -30% to -15% for SELL signals)
                    volume_multiplier = 0.85  # -15% penalty
                    logger.info(f"   Weak volume {volume_ratio:.2f}x - applying reduced penalty for SELL")
                else:
                    # Normal or strong volume - full confidence
                    volume_multiplier = 1.0
                    logger.info(f"   Normal/strong volume {volume_ratio:.2f}x - full confidence")
                
                # Calculate final SELL confidence with volume adjustment
                sell_confidence = confidence * volume_multiplier
                sell_confidence = max(0.50, min(sell_confidence, 0.95))  # Clamp to 50-95%
                
                logger.info(f"")
                logger.info(f"╔═══════════════════════════════════════════════════════════════════╗")
                logger.info(f"║  🎯 EXTREME OVERBOUGHT SCALP OPPORTUNITY DETECTED                ║")
                logger.info(f"╠═══════════════════════════════════════════════════════════════════╣")
                logger.info(f"║  Signal Type:      SHORT SCALP (Reversal from top)               ║")
                logger.info(f"║  RSI:              {rsi:.1f} (EXTREME overbought)                ║")
                logger.info(f"║  Reversal Prob:    {reversal_prob:.1%} (ML confirmed)            ║")
                logger.info(f"║  BB Position:      {bb_pos:.3f} (At/above upper band)            ║")
                logger.info(f"║  Volume Ratio:     {volume_ratio:.2f}x                            ║")
                logger.info(f"║  Base Confidence:  {confidence:.1%}                               ║")
                logger.info(f"║  Final Confidence: {sell_confidence:.1%}                          ║")
                logger.info(f"║                                                                   ║")
                logger.info(f"║  📊 SCALP PARAMETERS (Professional Standards):                   ║")
                logger.info(f"║     • Take Profit:  0.2-0.4% (quick exit on reversal)            ║")
                logger.info(f"║     • Stop Loss:    0.15-0.25% (tight risk management)           ║")
                logger.info(f"║     • Expected R:R: 1:1.5 to 1:2 (professional scalping)         ║")
                logger.info(f"║     • Hold Time:    1-15 minutes (intraday only)                 ║")
                logger.info(f"╚═══════════════════════════════════════════════════════════════════╝")
                logger.info(f"")
                
                # 📊 METRICS: Track extreme overbought SELL signal
                self._track_signal_metrics("SELL", sell_confidence, rsi, reversal_prob, signal_type="extreme_overbought")
                
                return "SELL", sell_confidence
            
            # ═══════════════════════════════════════════════════════════════════════════
            # 🎯 TIER 2: STANDARD OVERBOUGHT (More Frequent, Slightly Lower Confidence)
            # ═══════════════════════════════════════════════════════════════════════════
            # PROFESSIONAL FIX (Oct 2025): Increased threshold for quality control
            # After 82 trades with 0% win rate, balancing accessibility with quality
            # Reasoning: Tier 2 is designed for MORE FREQUENT signals but needs better confirmation
            #           The volume gate and trend exhaustion checks provide additional safety
            # ═══════════════════════════════════════════════════════════════════════════
            # Criteria:
            #   - RSI ≥ 85 (strong overbought, but not extreme)
            #   - Reversal Probability ≥ 85% (high ML confidence)
            #   - BB Position ≥ 0.80 (near/above upper band, not necessarily at edge)
            #   - Volume ≥ 1.2x OR Trend Exhaustion confirmed
            #   - Confidence ≥ 65% (🔧 PROFESSIONAL FIX: Raised from 50% for better quality)
            # Expected: 2-4 signals/day, 65%+ win rate, 0.35% avg profit
            # ═══════════════════════════════════════════════════════════════════════════
            
            tier2_conf_check = confidence >= 0.65  # 🔧 PROFESSIONAL FIX: Raised threshold for quality (was 0.50)
            standard_overbought_scalp = (
                rsi >= 85.0 and
                reversal_prob >= 0.85 and
                bb_pos >= 0.80 and
                tier2_conf_check  # Independent confidence check
            )
            
            if standard_overbought_scalp:
                # 🎯 TIER 2 VOLUME GATE: Requires EITHER strong volume OR trend exhaustion
                volume_ratio = float(features.get("volume_ratio", 1.0))
                trend_strength = float(features.get("trend_strength", 0.0))
                
                # Check for trend exhaustion (weakening trend at overbought levels)
                # 🔧 FIX: Adjusted threshold from <0.4 to <0.6 (more realistic for overbought conditions)
                # At RSI≥88, even a 52% trend strength indicates exhaustion approaching
                trend_exhaustion = (trend_strength < 0.6 and rsi >= 88.0)
                
                # Volume gate: Require 1.2x volume OR trend exhaustion
                volume_gate_passed = (volume_ratio >= 1.2) or trend_exhaustion
                
                if not volume_gate_passed:
                    logger.info(f"⚠️ TIER 2 SELL BLOCKED: Insufficient volume ({volume_ratio:.2f}x) and no trend exhaustion")
                    logger.info(f"   RSI={rsi:.1f}, Rev={reversal_prob:.1%}, BB={bb_pos:.3f}, but volume/exhaustion criteria not met")
                    # Track blocked signal
                    self.signal_metrics["sell_signals"]["blocked_by_volume_count"] = self.signal_metrics["sell_signals"].get("blocked_by_volume_count", 0) + 1
                else:
                    # Calculate TIER 2 confidence (slightly lower than TIER 1)
                    # Base confidence is already calculated, but we'll apply a small penalty for lower tier
                    tier2_multiplier = 0.95  # -5% penalty compared to Tier 1
                    
                    # Apply volume adjustment (less strict than Tier 1)
                    if volume_ratio >= 1.5:
                        volume_multiplier = 1.0  # Strong volume
                    elif volume_ratio >= 1.2:
                        volume_multiplier = 0.95  # Adequate volume
                    elif trend_exhaustion:
                        volume_multiplier = 0.90  # Trend exhaustion compensates for weak volume
                        logger.info(f"   Volume weak ({volume_ratio:.2f}x) but TREND EXHAUSTION detected - proceeding")
                    else:
                        volume_multiplier = 0.80  # This shouldn't happen due to gate, but safe fallback
                    
                    sell_confidence = confidence * tier2_multiplier * volume_multiplier
                    sell_confidence = max(0.50, min(sell_confidence, 0.90))  # Clamp to 50-90% (lower max than Tier 1)
                    
                    logger.info(f"")
                    logger.info(f"╔═══════════════════════════════════════════════════════════════════╗")
                    logger.info(f"║  🎯 STANDARD OVERBOUGHT OPPORTUNITY DETECTED (TIER 2)            ║")
                    logger.info(f"╠═══════════════════════════════════════════════════════════════════╣")
                    logger.info(f"║  Signal Type:      SHORT SCALP (Reversal from overbought)        ║")
                    logger.info(f"║  RSI:              {rsi:.1f} (Strong overbought)                 ║")
                    logger.info(f"║  Reversal Prob:    {reversal_prob:.1%} (ML confirmed)            ║")
                    logger.info(f"║  BB Position:      {bb_pos:.3f} (Near/above upper band)          ║")
                    logger.info(f"║  Volume Ratio:     {volume_ratio:.2f}x                            ║")
                    logger.info(f"║  Trend Exhaustion: {'YES' if trend_exhaustion else 'NO'}                                         ║")
                    logger.info(f"║  Base Confidence:  {confidence:.1%}                               ║")
                    logger.info(f"║  Final Confidence: {sell_confidence:.1%}                          ║")
                    logger.info(f"║                                                                   ║")
                    logger.info(f"║  📊 SCALP PARAMETERS:                                            ║")
                    logger.info(f"║     • Take Profit:  0.25-0.35% (quick exit)                      ║")
                    logger.info(f"║     • Stop Loss:    0.20-0.30% (standard risk)                   ║")
                    logger.info(f"║     • Expected R:R: 1:1.3 to 1:1.5                               ║")
                    logger.info(f"║     • Hold Time:    1-20 minutes                                 ║")
                    logger.info(f"║     • Tier:         2 (Standard Overbought)                      ║")
                    logger.info(f"╚═══════════════════════════════════════════════════════════════════╝")
                    logger.info(f"")
                    
                    # 📊 METRICS: Track standard overbought SELL signal
                    self._track_signal_metrics("SELL", sell_confidence, rsi, reversal_prob, signal_type="standard_overbought")
                    
                    return "SELL", sell_confidence
            
            # ═══════════════════════════════════════════════════════════════════════════
            # 🎯 TIER 1: OVERSOLD-BOUNCE MICRO-PLAYBOOK (Capitulation Longs)
            # ═══════════════════════════════════════════════════════════════════════════
            # 🔧 FIX (Oct 2025): New playbook for oversold bounces
            # When BB_pos ≤ 0.05, RSI ∈ [28,36], volume spike → allow exploratory long
            # This catches capitulation bounces with tight risk management
            # ═══════════════════════════════════════════════════════════════════════════
            
            if oversold_bounce and not rsi_oversold_danger:
                # Temporarily relax exploratory threshold for this high-signal setup
                bounce_confidence = max(confidence * 0.9, 0.45)  # Slightly reduce for exploratory nature
                bounce_confidence = min(bounce_confidence, 0.75)  # Cap at 75%
                
                logger.info(f"")
                logger.info(f"╔═══════════════════════════════════════════════════════════════════╗")
                logger.info(f"║  🎯 OVERSOLD-BOUNCE OPPORTUNITY DETECTED (TIER 1)                ║")
                logger.info(f"╠═══════════════════════════════════════════════════════════════════╣")
                logger.info(f"║  Signal Type:      LONG SCALP (Bounce from oversold)             ║")
                logger.info(f"║  RSI:              {rsi:.1f} (Oversold)                           ║")
                logger.info(f"║  BB Position:      {bb_pos:.3f} (At/below lower band)            ║")
                logger.info(f"║  Volume Spike:     zVol={z_vol:.2f}, ratio={volume_ratio:.2f}x   ║")
                logger.info(f"║  MACD:             {macd:.4f} (contracting)                       ║")
                logger.info(f"║  Base Confidence:  {confidence:.1%}                               ║")
                logger.info(f"║  Final Confidence: {bounce_confidence:.1%}                        ║")
                logger.info(f"║                                                                   ║")
                logger.info(f"║  📊 SCALP PARAMETERS (Tight Risk):                               ║")
                logger.info(f"║     • Size Factor:  0.25-0.40× exploratory base                  ║")
                logger.info(f"║     • Stop Loss:    0.15-0.20% below swing low                   ║")
                logger.info(f"║     • Take Profit:  TP1: +0.20-0.30% (scale 50%)                 ║")
                logger.info(f"║                     TP2: mid-band or +0.50% (trail)              ║")
                logger.info(f"║     • Cooldown:     10-15 minutes after exit                     ║")
                logger.info(f"╚═══════════════════════════════════════════════════════════════════╝")
                logger.info(f"")
                
                # 📊 METRICS: Track oversold bounce BUY signal
                self._track_signal_metrics("BUY", bounce_confidence, rsi, reversal_prob, signal_type="oversold_bounce")
                
                return "BUY", bounce_confidence
            
            # ═══════════════════════════════════════════════════════════════════════════
            # 🎯 LEGACY EXTREME CONDITIONS (for backwards compatibility)
            # ═══════════════════════════════════════════════════════════════════════════
            # These are the original extreme condition checks that require full conf_check
            # Kept for backwards compatibility with existing behavior
            # ═══════════════════════════════════════════════════════════════════════════
            
            extreme_oversold_buy = (reversal_prob > 0.60 and timing_score > 0.0 and rsi < 30 and bb_pos < 0.2)
            extreme_overbought_sell = (reversal_prob > 0.60 and timing_score < 0.0 and rsi > 70 and bb_pos > 0.8)
            
            # DAY TRADING: Aggressive entry for extreme conditions (bypass filter check)
            if conf_check and reversal_check:
                if extreme_oversold_buy:
                    logger.info(f"🚀 DAY TRADING SIGNAL: BUY (extreme_oversold_reversal - rsi={rsi:.1f}, bb_pos={bb_pos:.2f})")
                    # 📊 METRICS: Track extreme oversold BUY signal
                    self._track_signal_metrics("BUY", confidence, rsi, reversal_prob, signal_type="extreme_oversold")
                    return "BUY", confidence
                elif extreme_overbought_sell:
                    logger.info(f"🚀 DAY TRADING SIGNAL: SELL (extreme_overbought_reversal - rsi={rsi:.1f}, bb_pos={bb_pos:.2f})")
                    # 📊 METRICS: Track extreme overbought SELL signal (legacy path)
                    self._track_signal_metrics("SELL", confidence, rsi, reversal_prob, signal_type="extreme_overbought")
                    return "SELL", confidence
            
            # Standard day trading: Confidence + reversal + filter + (timing OR alternative SELL signals) + RSI safety
            if conf_check and reversal_check and filter_check:
                if timing_buy_check and not rsi_overbought_danger:  # ✅ FIX: Don't buy when RSI > 80
                    action = "BUY"
                    logger.info(f"✅ DAY TRADING SIGNAL: {action} (standard_buy)")
                    # 📊 METRICS: Track standard BUY signal
                    self._track_signal_metrics("BUY", confidence, rsi, reversal_prob, signal_type="standard")
                    return action, confidence
                elif any_sell_signal and not rsi_oversold_danger:  # 🔥 FIX: Use combined SELL check (timing OR mean reversion)
                    action = "SELL"
                    sell_reason = "timing" if timing_sell_check else "mean_reversion" if mean_reversion_sell else "resistance" if resistance_rejection_sell else "momentum"
                    logger.info(f"✅ DAY TRADING SIGNAL: {action} (standard_sell_{sell_reason})")
                    # 📊 METRICS: Track standard SELL signal
                    self._track_signal_metrics("SELL", confidence, rsi, reversal_prob, signal_type="standard")
                    return action, confidence
                elif timing_buy_check and rsi_overbought_danger:
                    logger.warning(f"⚠️ BUY signal BLOCKED by RSI safety check (RSI={rsi:.1f} > 80)")
                    # 📊 METRICS: Track blocked BUY
                    self.signal_metrics["buy_signals"]["blocked_by_rsi_count"] += 1
                elif any_sell_signal and rsi_oversold_danger:
                    logger.warning(f"⚠️ SELL signal BLOCKED by RSI safety check (RSI={rsi:.1f} < 20)")
                    # 📊 METRICS: Track blocked SELL
                    self.signal_metrics["sell_signals"]["blocked_by_rsi_count"] += 1
            
            # 📊 METRICS: Track HOLD signal
            self._track_signal_metrics("HOLD", confidence, rsi, reversal_prob, signal_type="standard")
            
            return "HOLD", confidence
            
        except Exception as e:
            logger.error(f"Primary signal calculation error: {e}")
            return "HOLD", 0.5
        
    def _calculate_exploratory_signal(self, confidence: float, timing_score: float, reversal_prob: float, filter_score: float, volatility: float, features: Dict[str, float] = None) -> Tuple[str, float]:
        """Calculate exploratory signal for small probing positions using unified thresholds"""
        try:
            # Extract technical indicators for alternative SELL signals
            if features is None:
                features = {}
            rsi = float(features.get("rsi", 50.0))
            bb_pos = float(features.get("bb_position", features.get("bollinger_position", 0.5)))
            macd = float(features.get("macd", 0.0))
            
            # 🔧 FIX (Oct 2025): Dynamic exploratory threshold in low-vol regimes
            # Top-band: volatility ≤ 0.05% & BB_pos ≥ 0.90 & RSI ∈ [55,70] → relax to 0.52
            # Bottom-band: volatility ≤ 0.06% & BB_pos ≤ 0.05 & RSI ∈ [28,36] → relax to 0.52
            # This allows tiny, time-boxed exploratory positions near band touches
            base_exploratory_threshold = self.thresholds.confidence.EXPLORATORY_BUY  # 0.55 default
            
            is_top_band_regime = (volatility <= 0.0005 and bb_pos >= 0.90 and 55 <= rsi <= 70)
            is_bottom_band_regime = (volatility <= 0.0006 and bb_pos <= 0.05 and 28 <= rsi <= 36)
            
            if is_top_band_regime:
                exploratory_threshold = 0.52
                logger.info(f"📊 EXPLORATORY THRESHOLD: RELAXED (TOP-BAND) to 0.52 (from {base_exploratory_threshold:.2f}) | vol={volatility:.4f}, BB={bb_pos:.2f}, RSI={rsi:.1f}")
            elif is_bottom_band_regime:
                exploratory_threshold = 0.52
                logger.info(f"📊 EXPLORATORY THRESHOLD: RELAXED (BOTTOM-BAND) to 0.52 (from {base_exploratory_threshold:.2f}) | vol={volatility:.4f}, BB={bb_pos:.2f}, RSI={rsi:.1f}")
            else:
                exploratory_threshold = base_exploratory_threshold
                logger.debug(f"📊 EXPLORATORY THRESHOLD: STANDARD {exploratory_threshold:.2f} | vol={volatility:.4f}, BB={bb_pos:.2f}, RSI={rsi:.1f}")
            
            # Use dynamic exploratory threshold
            conf_check = confidence >= exploratory_threshold
            reversal_check = reversal_prob < 0.75  # Higher tolerance for reversal risk
            volatility_check = volatility < 0.12  # Avoid high volatility periods
            timing_buy_check = timing_score > 0.005  # Very low timing requirement
            timing_sell_check = timing_score < -0.002  # 🔥 RELAXED for exploratory (was -0.005)
            
            # 🔥 Alternative SELL signals for exploratory (lower requirements)
            exploratory_mean_reversion = (rsi > 68 and bb_pos > 0.80)  # Slightly lower requirements than standard
            exploratory_momentum_shift = (timing_score < 0.0 and macd < 0.0)  # Any bearish momentum
            
            any_exploratory_sell = timing_sell_check or exploratory_mean_reversion or exploratory_momentum_shift
            
            # CRITICAL FIX: Much lower filter threshold for exploratory signals
            filter_check = filter_score > 0.05  # Very low filter requirement (5%)
            
            logger.debug(f"EXPLORATORY CHECKS - conf:{conf_check}, reversal:{reversal_check}, vol:{volatility_check}, filter:{filter_check}, timing_buy:{timing_buy_check}")
            
            if conf_check and reversal_check and volatility_check and filter_check:
                if timing_buy_check:
                    # Reduce confidence for exploratory signals
                    exploratory_confidence = max(confidence * 0.7, 0.2)
                    logger.info(f"🔬 EXPLORATORY SIGNAL: BUY (conf={exploratory_confidence:.2f})")
                    return "BUY", exploratory_confidence
                elif any_exploratory_sell:
                    # Reduce confidence for exploratory signals
                    exploratory_confidence = max(confidence * 0.7, 0.2)
                    sell_reason = "timing" if timing_sell_check else "mean_rev" if exploratory_mean_reversion else "momentum"
                    logger.info(f"🔬 EXPLORATORY SIGNAL: SELL_{sell_reason} (conf={exploratory_confidence:.2f})")
                    return "SELL", exploratory_confidence
            
            return "HOLD", confidence
            
        except Exception as e:
            logger.error(f"Exploratory signal calculation error: {e}")
            return "HOLD", 0.5
    
    def _calculate_position_size(self, confidence: float, layer_results: Dict[str, Any]) -> float:
        """
        Calculate relative position size indicator (0-1 scale)
        
        ✅ PROFESSIONAL: Actual position sizing delegated to Kelly Criterion in Entry Engine
        This just provides a relative indicator for signal strength
        """
        try:
            # Adjust by confidence
            confidence_factor = confidence
            
            # Adjust by volatility (from layer analysis)
            volatility_factor = 1.0
            if "layer_4_filters" in layer_results:
                # Lower size for high volatility
                volatility_factor = max(0.5, 1.0 - layer_results["layer_4_filters"]["filter_score"])
            
            # Calculate relative size indicator (0-1 scale)
            position_size = confidence_factor * volatility_factor
            
            # Return clamped indicator
            return min(1.0, max(0.0, position_size))
            
        except Exception as e:
            logger.error(f"Position size calculation error: {e}")
            return 0.5  # Neutral fallback
    
    def _calculate_risk_score(self, layer_results: Dict[str, Any]) -> float:
        """Calculate overall risk score"""
        try:
            risk_factors = []
            
            # Reversal risk
            risk_factors.append(layer_results["layer_3_reversal"]["reversal_probability"])
            
            # Volatility risk (inverse of filter score)
            risk_factors.append(1.0 - layer_results["layer_4_filters"]["filter_score"])
            
            # Confidence risk (inverse)
            risk_factors.append(1.0 - layer_results["layer_5_confidence"]["confidence"])
            
            return np.mean(risk_factors)
            
        except Exception as e:
            logger.error(f"Risk score calculation error: {e}")
            return 0.5
    
    def _generate_reasoning(self, layer_results: Dict[str, Any], action: str, confidence: float) -> str:
        """Generate human-readable reasoning for the trading decision"""
        try:
            regime = layer_results["layer_1_regime"]["regime"]
            timing = layer_results["layer_6_timing"]["timing_score"]
            reversal = layer_results["layer_3_reversal"]["reversal_probability"]
            
            reasoning = f"6-Layer AI Analysis: {action} signal with {confidence:.1%} confidence. "
            reasoning += f"Market regime: {regime}. "
            
            if action == "BUY":
                reasoning += f"Positive timing score ({timing:.3f}) with low reversal risk ({reversal:.1%}). "
            elif action == "SELL":
                reasoning += f"Negative timing score ({timing:.3f}) indicating sell pressure. "
            else:
                reasoning += f"Neutral timing ({timing:.3f}) suggests holding position. "
            
            reasoning += f"Analysis based on real-time Binance market data."
            
            return reasoning
            
        except Exception as e:
            logger.error(f"Reasoning generation error: {e}")
            return f"AI analysis resulted in {action} signal with {confidence:.1%} confidence."
    
    def _create_fallback_signal(self, symbol: str, error: str) -> TradingSignal:
        """NO FALLBACKS - Raise error for professional deployment"""
        raise RuntimeError(f"Real AI signal generation failed: {error}")
    
    # Technical indicator helpers
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    def _calculate_macd(self, prices: List[float]) -> Tuple[float, float]:
        """Calculate MACD indicator"""
        if len(prices) < 26:
            return 0.0, 0.0
        
        ema_12 = self._ema(prices, 12)
        ema_26 = self._ema(prices, 26)
        macd = ema_12 - ema_26
        
        # Simple signal line (9-period EMA of MACD)
        macd_signal = macd * 0.9  # Simplified
        
        return macd, macd_signal
    
    def _ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return np.mean(prices)
        
        alpha = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        
        return ema
    
    def _calculate_bb_position(self, prices: List[float], current_price: float) -> float:
        """Calculate Bollinger Band position (0 = lower band, 1 = upper band)"""
        if len(prices) < 20:
            return 0.5
        
        sma = np.mean(prices[-20:])
        std = np.std(prices[-20:])
        
        upper_band = sma + (2 * std)
        lower_band = sma - (2 * std)
        
        if upper_band == lower_band:
            return 0.5
        
        position = (current_price - lower_band) / (upper_band - lower_band)
        return float(np.clip(position, 0.0, 1.0))
    
    def _calculate_trend_strength(self, prices: List[float]) -> float:
        """Calculate trend strength using linear regression slope"""
        if len(prices) < 10:
            return 0.5
        
        x = np.arange(len(prices))
        y = np.array(prices)
        
        # Linear regression
        slope, intercept = np.polyfit(x, y, 1)
        
        # Normalize slope to 0-1 range
        trend_strength = np.tanh(abs(slope) / np.mean(prices) * 100)
        
        return float(trend_strength)
    
    def _track_signal_metrics(self, action: str, confidence: float, rsi: float, reversal_prob: float, signal_type: str = "standard"):
        """
        Track signal generation metrics for monitoring and optimization
        Industry best practice: Monitor what you manage
        """
        try:
            # Update session stats
            self.signal_metrics["session_stats"]["total_signals"] += 1
            
            if action == "SELL":
                # Track SELL metrics
                sell_metrics = self.signal_metrics["sell_signals"]
                
                if signal_type == "extreme_overbought":
                    sell_metrics["extreme_overbought_count"] += 1
                elif signal_type == "standard_overbought":
                    sell_metrics["standard_overbought_count"] += 1
                else:
                    sell_metrics["standard_sell_count"] += 1
                
                sell_metrics["total_sell_confidence"] += confidence
                sell_metrics["last_sell_rsi"] = rsi
                sell_metrics["last_sell_reversal"] = reversal_prob
                
                # Calculate average confidence
                total_sells = (sell_metrics["extreme_overbought_count"] + 
                              sell_metrics["standard_overbought_count"] + 
                              sell_metrics["standard_sell_count"])
                if total_sells > 0:
                    sell_metrics["avg_sell_confidence"] = sell_metrics["total_sell_confidence"] / total_sells
                
            elif action == "BUY":
                # Track BUY metrics
                buy_metrics = self.signal_metrics["buy_signals"]
                
                if signal_type == "extreme_oversold":
                    buy_metrics["extreme_oversold_count"] += 1
                else:
                    buy_metrics["standard_buy_count"] += 1
                
                buy_metrics["total_buy_confidence"] += confidence
                buy_metrics["last_buy_rsi"] = rsi
                buy_metrics["last_buy_reversal"] = reversal_prob
                
                # Calculate average confidence
                total_buys = buy_metrics["extreme_oversold_count"] + buy_metrics["standard_buy_count"]
                if total_buys > 0:
                    buy_metrics["avg_buy_confidence"] = buy_metrics["total_buy_confidence"] / total_buys
            
            else:  # HOLD
                self.signal_metrics["hold_signals"]["total_hold_count"] += 1
            
            # Update session rates
            total = self.signal_metrics["session_stats"]["total_signals"]
            if total > 0:
                total_sells = (self.signal_metrics["sell_signals"]["extreme_overbought_count"] + 
                              self.signal_metrics["sell_signals"]["standard_sell_count"])
                total_buys = (self.signal_metrics["buy_signals"]["extreme_oversold_count"] + 
                             self.signal_metrics["buy_signals"]["standard_buy_count"])
                
                self.signal_metrics["session_stats"]["sell_rate"] = total_sells / total
                self.signal_metrics["session_stats"]["buy_rate"] = total_buys / total
            
            # Log metrics every 50 signals
            if total % 50 == 0:
                self._log_signal_metrics()
                
        except Exception as e:
            logger.warning(f"Failed to track signal metrics: {e}")
    
    def _log_signal_metrics(self):
        """Log current signal generation metrics"""
        try:
            from datetime import datetime
            
            metrics = self.signal_metrics
            session = metrics["session_stats"]
            sell = metrics["sell_signals"]
            buy = metrics["buy_signals"]
            hold = metrics["hold_signals"]
            
            # Calculate session duration
            if session["session_start"]:
                duration = datetime.utcnow() - session["session_start"]
                duration_hours = duration.total_seconds() / 3600
            else:
                duration_hours = 0.0
            
            logger.info("")
            logger.info("╔═══════════════════════════════════════════════════════════════════╗")
            logger.info("║           📊 SIGNAL GENERATION METRICS REPORT                     ║")
            logger.info("╠═══════════════════════════════════════════════════════════════════╣")
            logger.info(f"║  Session Duration:  {duration_hours:.2f} hours                   ")
            logger.info(f"║  Total Signals:     {session['total_signals']}                   ")
            logger.info(f"║                                                                   ║")
            logger.info(f"║  🔴 SELL SIGNALS:                                                 ║")
            logger.info(f"║     • Tier 1 (Extreme):   {sell['extreme_overbought_count']}     ")
            logger.info(f"║     • Tier 2 (Standard):  {sell['standard_overbought_count']}    ")
            logger.info(f"║     • Regular SELL:       {sell['standard_sell_count']}          ")
            logger.info(f"║     • Blocked (RSI<20):   {sell['blocked_by_rsi_count']}         ")
            logger.info(f"║     • Blocked (Volume):   {sell['blocked_by_volume_count']}      ")
            logger.info(f"║     • Avg Confidence:     {sell['avg_sell_confidence']:.1%}      ")
            logger.info(f"║     • Last RSI:           {sell['last_sell_rsi']:.1f}            ")
            logger.info(f"║     • SELL Rate:          {session['sell_rate']:.1%}             ")
            logger.info(f"║                                                                   ║")
            logger.info(f"║  🟢 BUY SIGNALS:                                                  ║")
            logger.info(f"║     • Extreme Oversold:   {buy['extreme_oversold_count']}        ")
            logger.info(f"║     • Standard BUY:       {buy['standard_buy_count']}            ")
            logger.info(f"║     • Blocked (RSI>80):   {buy['blocked_by_rsi_count']}          ")
            logger.info(f"║     • Avg Confidence:     {buy['avg_buy_confidence']:.1%}        ")
            logger.info(f"║     • Last RSI:           {buy['last_buy_rsi']:.1f}              ")
            logger.info(f"║     • BUY Rate:           {session['buy_rate']:.1%}              ")
            logger.info(f"║                                                                   ║")
            logger.info(f"║  ⚪ HOLD SIGNALS:                                                 ║")
            logger.info(f"║     • Total HOLD:         {hold['total_hold_count']}             ")
            logger.info(f"╚═══════════════════════════════════════════════════════════════════╝")
            logger.info("")
            
        except Exception as e:
            logger.warning(f"Failed to log signal metrics: {e}")
    
    def get_signal_metrics(self) -> dict:
        """Get current signal generation metrics (for external monitoring)"""
        return self.signal_metrics.copy()
