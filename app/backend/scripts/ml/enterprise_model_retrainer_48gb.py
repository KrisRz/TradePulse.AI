#!/usr/bin/env python3
"""
Enterprise Model Retrainer - 48GB MacBook Pro Optimized
TradePulse.AI Professional Training System

Optimized for:
- 48GB RAM MacBook Pro
- Full 6-layer architecture 
- Memory-efficient training
- Professional production models
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import pickle
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import psutil
import gc
import logging

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Memory management for 48GB system
import numpy as np
np.random.seed(42)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enterprise_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ML imports
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler, RobustScaler, LabelEncoder
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, accuracy_score, classification_report
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
import xgboost as xgb
import lightgbm as lgb

# TensorFlow with memory optimization
try:
    import tensorflow as tf
    # Configure TensorFlow for 48GB system
    gpus = tf.config.experimental.list_physical_devices('GPU')
    if gpus:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    
    # TensorFlow memory optimization for CPU (no memory limit needed on CPU)
    tf.config.threading.set_inter_op_parallelism_threads(4)
    tf.config.threading.set_intra_op_parallelism_threads(4)
    
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    TENSORFLOW_AVAILABLE = True
    logger.info("✅ TensorFlow configured for 48GB system")
except ImportError:
    TENSORFLOW_AVAILABLE = False
    logger.warning("❌ TensorFlow not available")

# Technical analysis
try:
    import ta
    TA_AVAILABLE = True
    logger.info("✅ TA library available")
except ImportError:
    TA_AVAILABLE = False
    logger.warning("❌ TA library not available")


class Enterprise48GBTrainer:
    """
    Enterprise Model Trainer Optimized for 48GB MacBook Pro
    
    Features:
    - Memory-optimized training for 48GB RAM
    - Full 6-layer architecture training
    - Professional model validation
    - Production-ready model output
    """
    
    def __init__(self, data_path: str = None, models_dir: str = None, memory_limit_gb: int = 40):
        # Paths
        self.project_root = Path(__file__).parent.parent
        self.data_path = Path(data_path) if data_path else self.project_root / "data" / "historical" / "processed" / "BTCUSDT_1m_complete.parquet"
        self.models_dir = Path(models_dir) if models_dir else self.project_root / "apps" / "backend" / "app" / "models" / "enterprise"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Memory management (48GB system)
        self.memory_limit_gb = memory_limit_gb
        self.chunk_size = 100000 if memory_limit_gb < 40 else 500000  # Adaptive chunk size
        
        # Professional feature engineering (expanded to 15 features)
        self.enterprise_features = [
            # Price & Volume (core)
            'close', 'volume', 'high', 'low', 'open',
            
            # Technical Indicators (Layer 3 & 4)
            'rsi', 'macd', 'bb_position', 'volatility',
            
            # Advanced Features (Layer 1 & 6)
            'trend_strength', 'momentum', 'volume_ratio', 
            'price_change_1h', 'price_change_4h', 'market_pressure'
        ]
        
        # Model storage
        self.models = {}
        self.layer_performance = {}
        self.scalers = {}
        
        # Data storage
        self.data = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        
        logger.info(f"🏢 Enterprise48GBTrainer initialized")
        logger.info(f"📊 Memory limit: {memory_limit_gb}GB")
        logger.info(f"📁 Models dir: {self.models_dir}")
        
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resources before training"""
        memory = psutil.virtual_memory()
        cpu_count = psutil.cpu_count()
        
        resources = {
            'total_memory_gb': round(memory.total / (1024**3), 2),
            'available_memory_gb': round(memory.available / (1024**3), 2),
            'memory_percent': memory.percent,
            'cpu_count': cpu_count,
            'tensorflow_available': TENSORFLOW_AVAILABLE,
            'ta_available': TA_AVAILABLE
        }
        
        logger.info(f"🖥️  System Resources:")
        logger.info(f"   Total Memory: {resources['total_memory_gb']}GB")
        logger.info(f"   Available Memory: {resources['available_memory_gb']}GB")
        logger.info(f"   CPU Cores: {resources['cpu_count']}")
        logger.info(f"   TensorFlow: {'✅' if TENSORFLOW_AVAILABLE else '❌'}")
        
        return resources
    
    def load_and_prepare_data(self) -> bool:
        """Load and prepare data with memory optimization"""
        try:
            logger.info(f"📊 Loading data from: {self.data_path}")
            
            # Check file size
            file_size_mb = self.data_path.stat().st_size / (1024 * 1024)
            logger.info(f"📁 File size: {file_size_mb:.1f}MB")
            
            # Load data with memory optimization
            if file_size_mb > 1000:  # > 1GB
                logger.info("🔄 Large file detected - loading with memory optimization")
                # Read full data and sample if needed
                self.data = pd.read_parquet(self.data_path)
                if len(self.data) > 2000000:  # Limit to 2M records for 48GB
                    logger.info(f"📊 Sampling {2000000:,} records from {len(self.data):,} total")
                    # Take most recent 2M records (time-series aware)
                    self.data = self.data.tail(2000000).reset_index(drop=True)
                gc.collect()
            else:
                self.data = pd.read_parquet(self.data_path)
            
            logger.info(f"✅ Data loaded: {len(self.data):,} records")
            logger.info(f"📊 Columns: {list(self.data.columns)}")
            
            # Professional feature engineering
            self.data = self.create_enterprise_features(self.data)
            
            # Memory cleanup
            gc.collect()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Data loading failed: {e}")
            return False
    
    def create_enterprise_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create professional enterprise features"""
        logger.info("🔧 Creating enterprise features...")
        
        df = df.copy()
        
        # Ensure required columns exist
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return df
        
        try:
            # Technical indicators with TA library
            if TA_AVAILABLE:
                # RSI
                df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
                
                # MACD
                macd = ta.trend.MACD(df['close'])
                df['macd'] = macd.macd()
                
                # Bollinger Bands
                bb = ta.volatility.BollingerBands(df['close'], window=20)
                df['bb_position'] = (df['close'] - bb.bollinger_lband()) / (bb.bollinger_hband() - bb.bollinger_lband())
                
                # Volatility
                df['volatility'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
                
            else:
                # Fallback calculations
                df['rsi'] = self.calculate_rsi(df['close'])
                df['macd'] = self.calculate_macd(df['close'])
                df['bb_position'] = self.calculate_bb_position(df['close'])
                df['volatility'] = df['high'] - df['low']
            
            # Advanced features for 6-layer system
            df['trend_strength'] = abs(df['close'].rolling(20).mean() - df['close'].rolling(50).mean()) / df['close']
            df['momentum'] = df['close'].pct_change(5)
            df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
            df['price_change_1h'] = df['close'].pct_change(60)  # 1h change (60 minutes)
            df['price_change_4h'] = df['close'].pct_change(240)  # 4h change (240 minutes)
            df['market_pressure'] = (df['close'] - df['low']) / (df['high'] - df['low'])
            
            # Fill NaN values with proper methods
            df = df.fillna(method='ffill').fillna(method='bfill')
            
            # Verify no NaN values remain
            nan_count = df.isna().sum().sum()
            if nan_count > 0:
                logger.warning(f"⚠️ {nan_count} NaN values remain after fillna")
                # Final fallback: fill with 0
                df = df.fillna(0)
            
            # Keep only enterprise features
            available_features = [col for col in self.enterprise_features if col in df.columns]
            missing_features = [col for col in self.enterprise_features if col not in df.columns]
            
            if missing_features:
                logger.warning(f"⚠️ Missing features: {missing_features}")
            
            df = df[available_features]
            
            # Final data validation
            logger.info(f"✅ Created {len(available_features)} enterprise features")
            logger.info(f"📊 Data shape: {df.shape}")
            logger.info(f"🔍 NaN values: {df.isna().sum().sum()}")
            
            # Ensure we have the minimum required features
            if len(available_features) < 5:
                raise ValueError(f"Not enough features: {len(available_features)} < 5 minimum")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Feature engineering failed: {e}")
            return df
    
    def calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calculate RSI manually"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_macd(self, prices: pd.Series) -> pd.Series:
        """Calculate MACD manually"""
        ema12 = prices.ewm(span=12).mean()
        ema26 = prices.ewm(span=26).mean()
        return ema12 - ema26
    
    def calculate_bb_position(self, prices: pd.Series, window: int = 20) -> pd.Series:
        """Calculate Bollinger Band position manually"""
        ma = prices.rolling(window).mean()
        std = prices.rolling(window).std()
        upper = ma + (std * 2)
        lower = ma - (std * 2)
        return (prices - lower) / (upper - lower)
    
    def prepare_training_data(self) -> bool:
        """Prepare training data for all 6 layers"""
        try:
            logger.info("🔧 Preparing training data...")
            
            # Create targets for different layers
            features_df = self.data[self.enterprise_features].copy()
            
            # Layer 1: Market Regime (classification)
            # 0=bear, 1=sideways, 2=bull, 3=volatile
            self.y_regime = self.create_market_regime_labels(features_df)
            
            # Layer 3: Reversal Detection (classification)
            # 0=no_reversal, 1=reversal
            self.y_reversal = self.create_reversal_labels(features_df)
            
            # Layer 4: Technical Filters (classification)
            # 0=bad_conditions, 1=good_conditions
            self.y_filters = self.create_filter_labels(features_df)
            
            # Layer 5: Confidence Scoring (regression)
            # 0.0-1.0 confidence score
            self.y_confidence = self.create_confidence_labels(features_df)
            
            # Layer 6: Adaptive Timing (regression)
            # Expected price change in next 60 minutes
            self.y_timing = features_df['close'].pct_change(60).shift(-60)
            
            # Remove NaN values
            mask = ~(self.y_regime.isna() | self.y_reversal.isna() | 
                    self.y_filters.isna() | self.y_confidence.isna() | 
                    self.y_timing.isna())
            
            features_df = features_df[mask]
            self.y_regime = self.y_regime[mask]
            self.y_reversal = self.y_reversal[mask]
            self.y_filters = self.y_filters[mask]
            self.y_confidence = self.y_confidence[mask]
            self.y_timing = self.y_timing[mask]
            
            # Train/test split (time-series aware)
            split_idx = int(len(features_df) * 0.8)
            
            self.X_train = features_df.iloc[:split_idx]
            self.X_test = features_df.iloc[split_idx:]
            
            self.y_regime_train = self.y_regime.iloc[:split_idx]
            self.y_regime_test = self.y_regime.iloc[split_idx:]
            
            self.y_reversal_train = self.y_reversal.iloc[:split_idx]
            self.y_reversal_test = self.y_reversal.iloc[split_idx:]
            
            self.y_filters_train = self.y_filters.iloc[:split_idx]
            self.y_filters_test = self.y_filters.iloc[split_idx:]
            
            self.y_confidence_train = self.y_confidence.iloc[:split_idx]
            self.y_confidence_test = self.y_confidence.iloc[split_idx:]
            
            self.y_timing_train = self.y_timing.iloc[:split_idx]
            self.y_timing_test = self.y_timing.iloc[split_idx:]
            
            logger.info(f"✅ Training data prepared:")
            logger.info(f"   Train: {len(self.X_train):,} samples")
            logger.info(f"   Test: {len(self.X_test):,} samples")
            logger.info(f"   Features: {len(self.enterprise_features)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Training data preparation failed: {e}")
            return False
    
    def create_market_regime_labels(self, df: pd.DataFrame) -> pd.Series:
        """Create market regime labels for Layer 1"""
        # Simple regime classification based on volatility and trend
        volatility_pct = df['volatility'].rolling(20).mean().rank(pct=True)
        trend_strength_pct = df['trend_strength'].rolling(20).mean().rank(pct=True)
        price_change_pct = df['close'].pct_change(20).rank(pct=True)
        
        regime = pd.Series(1, index=df.index)  # Default: sideways
        
        # Bull market: strong uptrend, moderate volatility
        regime[(price_change_pct > 0.7) & (volatility_pct < 0.7)] = 2
        
        # Bear market: strong downtrend, moderate volatility  
        regime[(price_change_pct < 0.3) & (volatility_pct < 0.7)] = 0
        
        # Volatile market: high volatility regardless of trend
        regime[volatility_pct > 0.8] = 3
        
        return regime
    
    def create_reversal_labels(self, df: pd.DataFrame) -> pd.Series:
        """Create reversal labels for Layer 3"""
        # Reversal detection based on RSI extremes and momentum change
        rsi = df['rsi']
        momentum = df['momentum']
        
        reversal = pd.Series(0, index=df.index)
        
        # Reversal signals
        reversal[(rsi < 30) & (momentum > 0.01)] = 1  # Oversold + positive momentum
        reversal[(rsi > 70) & (momentum < -0.01)] = 1  # Overbought + negative momentum
        
        return reversal
    
    def create_filter_labels(self, df: pd.DataFrame) -> pd.Series:
        """Create filter labels for Layer 4"""
        # Good conditions: moderate volatility, good volume, clear trend
        volatility_pct = df['volatility'].rolling(20).mean().rank(pct=True)
        volume_pct = df['volume_ratio'].rank(pct=True)
        trend_pct = abs(df['trend_strength']).rank(pct=True)
        
        good_conditions = pd.Series(0, index=df.index)
        
        # Good trading conditions
        good_conditions[(volatility_pct > 0.3) & (volatility_pct < 0.8) & 
                       (volume_pct > 0.4) & (trend_pct > 0.3)] = 1
        
        return good_conditions
    
    def create_confidence_labels(self, df: pd.DataFrame) -> pd.Series:
        """Create confidence labels for Layer 5"""
        # Confidence based on multiple factor alignment
        factors = [
            abs(df['rsi'] - 50) / 50,  # RSI extreme
            abs(df['bb_position'] - 0.5) * 2,  # BB position
            abs(df['trend_strength']) * 10,  # Trend strength
            df['volume_ratio'].clip(0, 2) / 2  # Volume confirmation
        ]
        
        confidence = sum(factors) / len(factors)
        return confidence.clip(0, 1)
    
    def train_layer_1_market_regime(self) -> bool:
        """Train Layer 1: Market Regime Detection"""
        try:
            logger.info("🎯 Training Layer 1: Market Regime Detection")
            
            # Features for regime detection
            regime_features = ['close', 'volume', 'volatility', 'trend_strength', 'momentum']
            X_regime = self.X_train[regime_features]
            
            # XGBoost Classifier (optimized for 48GB)
            model = xgb.XGBClassifier(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,  # Use all CPU cores
                tree_method='hist',  # Memory efficient
                eval_metric='mlogloss'
            )
            
            model.fit(X_regime, self.y_regime_train)
            
            # Evaluate
            y_pred = model.predict(self.X_test[regime_features])
            accuracy = accuracy_score(self.y_regime_test, y_pred)
            
            # Save model
            self.models['layer_1_regime'] = model
            self.layer_performance['layer_1'] = {
                'accuracy': accuracy,
                'model_type': 'XGBoost Classifier',
                'features': regime_features,
                'classes': ['bear', 'sideways', 'bull', 'volatile']
            }
            
            logger.info(f"✅ Layer 1 trained - Accuracy: {accuracy:.4f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Layer 1 training failed: {e}")
            return False
    
    def train_layer_2_lstm_ensemble(self) -> bool:
        """Train Layer 2: LSTM Ensemble (1h, 4h, 24h models)"""
        if not TENSORFLOW_AVAILABLE:
            logger.warning("⚠️ TensorFlow not available - skipping LSTM training")
            return False
            
        try:
            logger.info("🤖 Training Layer 2: LSTM Ensemble")
            
            # LSTM features
            lstm_features = ['close', 'volume', 'rsi', 'macd', 'volatility']
            X_lstm = self.X_train[lstm_features].values
            y_lstm = self.y_timing_train.values
            
            # Scale features for LSTM
            scaler = StandardScaler()
            X_lstm_scaled = scaler.fit_transform(X_lstm)
            self.scalers['lstm'] = scaler
            
            # Create sequences for different timeframes
            lstm_models = {}
            
            # 1h model (60 time steps)
            X_seq_1h, y_seq_1h = self.create_sequences(X_lstm_scaled, y_lstm, 60)
            if len(X_seq_1h) > 1000:  # Ensure enough data
                lstm_1h = self.build_lstm_model(60, len(lstm_features))
                lstm_1h.fit(X_seq_1h, y_seq_1h, epochs=50, batch_size=64, 
                           validation_split=0.2, verbose=0)
                lstm_models['lstm_1h'] = lstm_1h
                logger.info("✅ LSTM 1h model trained")
            
            # 4h model (240 time steps) - reduced for memory
            X_seq_4h, y_seq_4h = self.create_sequences(X_lstm_scaled, y_lstm, 120)  # Reduced from 240
            if len(X_seq_4h) > 500:
                lstm_4h = self.build_lstm_model(120, len(lstm_features))
                lstm_4h.fit(X_seq_4h, y_seq_4h, epochs=30, batch_size=32,
                           validation_split=0.2, verbose=0)
                lstm_models['lstm_4h'] = lstm_4h
                logger.info("✅ LSTM 4h model trained")
            
            # 24h model (30 time steps)
            X_seq_24h, y_seq_24h = self.create_sequences(X_lstm_scaled, y_lstm, 30)
            if len(X_seq_24h) > 1000:
                lstm_24h = self.build_lstm_model(30, len(lstm_features))
                lstm_24h.fit(X_seq_24h, y_seq_24h, epochs=50, batch_size=64,
                           validation_split=0.2, verbose=0)
                lstm_models['lstm_24h'] = lstm_24h
                logger.info("✅ LSTM 24h model trained")
            
            self.models['layer_2_lstm'] = lstm_models
            self.layer_performance['layer_2'] = {
                'models': list(lstm_models.keys()),
                'features': lstm_features,
                'model_type': 'LSTM Ensemble'
            }
            
            logger.info(f"✅ Layer 2 trained - {len(lstm_models)} LSTM models")
            return len(lstm_models) > 0
            
        except Exception as e:
            logger.error(f"❌ Layer 2 training failed: {e}")
            return False
    
    def create_sequences(self, X: np.ndarray, y: np.ndarray, sequence_length: int) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training"""
        X_seq, y_seq = [], []
        for i in range(sequence_length, len(X)):
            X_seq.append(X[i-sequence_length:i])
            y_seq.append(y[i])
        return np.array(X_seq), np.array(y_seq)
    
    def build_lstm_model(self, sequence_length: int, n_features: int):
        """Build LSTM model architecture optimized for 48GB"""
        model = Sequential([
            LSTM(32, return_sequences=True, input_shape=(sequence_length, n_features)),  # Reduced from 64
            Dropout(0.2),
            LSTM(16, return_sequences=False),  # Reduced from 32
            Dropout(0.2),
            Dense(8, activation='relu'),  # Reduced from 16
            Dense(1, activation='linear')
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def train_remaining_layers(self) -> Dict[str, bool]:
        """Train layers 3, 4, 5, 6"""
        results = {}
        
        # Layer 3: Reversal Detection
        try:
            logger.info("🔄 Training Layer 3: Reversal Detection")
            reversal_features = ['rsi', 'macd', 'momentum']
            
            model = lgb.LGBMClassifier(
                n_estimators=200,
                max_depth=6,  # 2^6=64 > 63 leaves (removes warning)
                num_leaves=63,
                learning_rate=0.1,
                random_state=42,
                n_jobs=-1,
                verbose=-1
            )
            
            model.fit(self.X_train[reversal_features], self.y_reversal_train)
            y_pred = model.predict(self.X_test[reversal_features])
            accuracy = accuracy_score(self.y_reversal_test, y_pred)
            
            self.models['layer_3_reversal'] = model
            self.layer_performance['layer_3'] = {
                'accuracy': accuracy,
                'model_type': 'LightGBM Classifier',
                'features': reversal_features
            }
            
            results['layer_3'] = True
            logger.info(f"✅ Layer 3 trained - Accuracy: {accuracy:.4f}")
            
        except Exception as e:
            logger.error(f"❌ Layer 3 failed: {e}")
            results['layer_3'] = False
        
        # Layer 4: Technical Filters
        try:
            logger.info("🛡️ Training Layer 4: Technical Filters")
            filter_features = ['bb_position', 'volatility', 'volume_ratio', 'market_pressure']
            
            model = RandomForestClassifier(
                n_estimators=100,  # Reduced for memory
                max_depth=8,
                random_state=42,
                n_jobs=-1
            )
            
            model.fit(self.X_train[filter_features], self.y_filters_train)
            y_pred = model.predict(self.X_test[filter_features])
            accuracy = accuracy_score(self.y_filters_test, y_pred)
            
            self.models['layer_4_filters'] = model
            self.layer_performance['layer_4'] = {
                'accuracy': accuracy,
                'model_type': 'Random Forest Classifier',
                'features': filter_features
            }
            
            results['layer_4'] = True
            logger.info(f"✅ Layer 4 trained - Accuracy: {accuracy:.4f}")
            
        except Exception as e:
            logger.error(f"❌ Layer 4 failed: {e}")
            results['layer_4'] = False
        
        # Layer 5: Confidence Scoring
        try:
            logger.info("📊 Training Layer 5: Confidence Scoring")
            
            model = xgb.XGBRegressor(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                n_jobs=-1,
                tree_method='hist'
            )
            
            model.fit(self.X_train, self.y_confidence_train)
            y_pred = model.predict(self.X_test)
            r2 = r2_score(self.y_confidence_test, y_pred)
            
            self.models['layer_5_confidence'] = model
            self.layer_performance['layer_5'] = {
                'r2_score': r2,
                'model_type': 'XGBoost Regressor',
                'features': self.enterprise_features
            }
            
            results['layer_5'] = True
            logger.info(f"✅ Layer 5 trained - R²: {r2:.4f}")
            
        except Exception as e:
            logger.error(f"❌ Layer 5 failed: {e}")
            results['layer_5'] = False
        
        # Layer 6: Adaptive Timing
        try:
            logger.info("⏰ Training Layer 6: Adaptive Timing")
            
            model = lgb.LGBMRegressor(
                n_estimators=200,
                max_depth=6,  # 2^6=64 > 63 leaves (removes warning)
                num_leaves=63,
                learning_rate=0.1,
                random_state=42,
                n_jobs=-1,
                verbose=-1
            )
            
            model.fit(self.X_train, self.y_timing_train)
            y_pred = model.predict(self.X_test)
            r2 = r2_score(self.y_timing_test, y_pred)
            
            self.models['layer_6_timing'] = model
            self.layer_performance['layer_6'] = {
                'r2_score': r2,
                'model_type': 'LightGBM Regressor',
                'features': self.enterprise_features
            }
            
            results['layer_6'] = True
            logger.info(f"✅ Layer 6 trained - R²: {r2:.4f}")
            
        except Exception as e:
            logger.error(f"❌ Layer 6 failed: {e}")
            results['layer_6'] = False
        
        return results
    
    def save_models(self) -> None:
        """Save all trained models"""
        try:
            logger.info("💾 Saving enterprise models...")
            
            # Save each layer model
            for layer_name, model in self.models.items():
                if layer_name == 'layer_2_lstm':
                    # Save LSTM models
                    for lstm_name, lstm_model in model.items():
                        lstm_path = self.models_dir / f"{lstm_name}.h5"
                        lstm_model.save(lstm_path)
                        logger.info(f"✅ Saved {lstm_name}")
                else:
                    # Save other models
                    model_path = self.models_dir / f"{layer_name}.pkl"
                    with open(model_path, 'wb') as f:
                        pickle.dump(model, f)
                    logger.info(f"✅ Saved {layer_name}")
            
            # Save scalers
            if self.scalers:
                scalers_path = self.models_dir / "scalers.pkl"
                with open(scalers_path, 'wb') as f:
                    pickle.dump(self.scalers, f)
                logger.info("✅ Saved scalers")
            
            # Save metadata
            metadata = {
                'training_date': datetime.now().isoformat(),
                'feature_names': self.enterprise_features,
                'layer_performance': self.layer_performance,
                'model_versions': {
                    'layer_1': 'v3.0.0',
                    'layer_2': 'v3.0.0',
                    'layer_3': 'v3.0.0',
                    'layer_4': 'v3.0.0',
                    'layer_5': 'v3.0.0',
                    'layer_6': 'v3.0.0'
                },
                'system_info': {
                    'system_version': '6-Layer Enterprise v3.0.0',
                    'training_system': '48GB MacBook Pro Optimized',
                    'memory_limit_gb': self.memory_limit_gb,
                    'tensorflow_available': TENSORFLOW_AVAILABLE,
                    'total_features': len(self.enterprise_features)
                }
            }
            
            metadata_path = self.models_dir / "enterprise_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info("✅ Saved metadata")
            
        except Exception as e:
            logger.error(f"❌ Saving failed: {e}")
    
    def train_complete_enterprise_system(self) -> Dict[str, Any]:
        """Train the complete 6-layer enterprise system"""
        start_time = datetime.now()
        
        try:
            logger.info("🚀 Starting Enterprise 6-Layer Training (48GB Optimized)")
            logger.info("=" * 80)
            
            # System check
            resources = self.check_system_resources()
            if resources['available_memory_gb'] < 10:
                logger.warning("⚠️ Low memory detected - training may be slow")
            
            # Load and prepare data
            if not self.load_and_prepare_data():
                return {'success': False, 'error': 'Data loading failed'}
            
            if not self.prepare_training_data():
                return {'success': False, 'error': 'Training data preparation failed'}
            
            # Train all layers
            layer_results = {}
            
            # Layer 1: Market Regime Detection
            layer_results['layer_1'] = self.train_layer_1_market_regime()
            
            # Layer 2: LSTM Ensemble
            layer_results['layer_2'] = self.train_layer_2_lstm_ensemble()
            
            # Layers 3, 4, 5, 6
            remaining_results = self.train_remaining_layers()
            layer_results.update(remaining_results)
            
            # Save all models
            self.save_models()
            
            # Final summary
            successful_layers = sum(layer_results.values())
            total_layers = len(layer_results)
            training_time = datetime.now() - start_time
            
            logger.info("=" * 80)
            logger.info("🎯 Enterprise 6-Layer Training Complete!")
            logger.info(f"✅ Successful layers: {successful_layers}/{total_layers}")
            logger.info(f"⏱️ Training time: {training_time}")
            logger.info(f"💾 Models saved to: {self.models_dir}")
            
            # Detailed results
            for layer_name, success in layer_results.items():
                status = "✅" if success else "❌"
                if success and layer_name in self.layer_performance:
                    perf = self.layer_performance[layer_name]
                    if 'accuracy' in perf:
                        logger.info(f"{status} {layer_name}: {perf['accuracy']:.4f} accuracy")
                    elif 'r2_score' in perf:
                        logger.info(f"{status} {layer_name}: {perf['r2_score']:.4f} R²")
                else:
                    logger.info(f"{status} {layer_name}")
            
            return {
                'success': True,
                'successful_layers': successful_layers,
                'total_layers': total_layers,
                'layer_results': layer_results,
                'layer_performance': self.layer_performance,
                'training_time': str(training_time),
                'models_dir': str(self.models_dir)
            }
            
        except Exception as e:
            logger.error(f"❌ Enterprise training failed: {e}")
            return {'success': False, 'error': str(e)}


def main():
    """Main training function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enterprise 48GB Model Trainer')
    parser.add_argument('--memory-limit', type=int, default=40, help='Memory limit in GB')
    parser.add_argument('--data-path', type=str, help='Path to training data')
    parser.add_argument('--models-dir', type=str, help='Directory to save models')
    parser.add_argument('--quick', action='store_true', help='Quick training with reduced parameters')
    
    args = parser.parse_args()
    
    logger.info("🏢 TradePulse.AI Enterprise 48GB Trainer")
    logger.info("=" * 50)
    
    # Create trainer
    trainer = Enterprise48GBTrainer(
        data_path=args.data_path,
        models_dir=args.models_dir,
        memory_limit_gb=args.memory_limit
    )
    
    # Adjust for quick training
    if args.quick:
        logger.info("⚡ Quick training mode enabled")
        trainer.chunk_size = 100000  # Smaller chunks
    
    # Train complete system
    results = trainer.train_complete_enterprise_system()
    
    if results['success']:
        logger.info("🎉 Enterprise training completed successfully!")
        logger.info(f"📊 Results: {results['successful_layers']}/{results['total_layers']} layers trained")
    else:
        logger.error(f"❌ Enterprise training failed: {results['error']}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 