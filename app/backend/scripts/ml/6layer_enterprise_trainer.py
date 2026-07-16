#!/usr/bin/env python3
"""
6-Layer Enterprise Trainer for TradePulse.AI
Trains the new 6-layer enterprise system with 7 core features

Layer 1: Market Regime Detection
Layer 2: LSTM Ensemble (1h, 4h, 24h models)  
Layer 3: Reversal Detection
Layer 4: Technical Filters
Layer 5: Confidence Scoring
Layer 6: Adaptive Timing
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
warnings.filterwarnings('ignore')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# ML imports
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
import lightgbm as lgb

# LSTM imports
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("TensorFlow not available - LSTM models will be skipped")

# Technical analysis
try:
    import ta
    TA_AVAILABLE = True
except ImportError:
    TA_AVAILABLE = False
    print("TA library not available")

# Logging setup
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SixLayerEnterpriseTrainer:
    """
    6-Layer Enterprise Trainer
    Trains the complete enterprise system with 7 core features
    """
    
    def __init__(self, data_path: str = None, models_dir: str = None):
        self.data_path = Path(data_path) if data_path else project_root / "data" / "historical" / "processed" / "BTCUSDT_1m_complete.parquet"
        self.models_dir = Path(models_dir) if models_dir else project_root / "data" / "models" / "6layer_enterprise"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # 7 Core features for 6-layer system
        self.core_features = [
            'close',           # Price data
            'volume',          # Volume data  
            'rsi',            # Layer 3: Reversal detection
            'macd',           # Layer 3: Reversal detection
            'bb_position',    # Layer 4: Technical filters
            'volatility',     # Layer 4: Technical filters
            'trend_strength'  # Layer 1: Market regime
        ]
        
        # Model storage
        self.models = {}
        self.model_scores = {}
        self.layer_performance = {}
        
        # Data storage
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.feature_names = []
        
    def load_and_prepare_data(self, max_samples: int = 100000) -> bool:
        """Load and prepare data with 7 core features"""
        try:
            if not self.data_path.exists():
                logger.error(f"Data file not found: {self.data_path}")
                return False
            
            logger.info(f"Loading data from: {self.data_path}")
            df = pd.read_parquet(self.data_path)
            
            # Sample data if too large
            if len(df) > max_samples:
                logger.info(f"Sampling {max_samples} from {len(df)} records")
                df = df.tail(max_samples).copy()
            
            # Add 7 core features
            df_with_features = self.add_core_features(df)
            
            # Select only 7 core features
            feature_cols = []
            for feature in self.core_features:
                if feature in df_with_features.columns:
                    feature_cols.append(feature)
                else:
                    logger.warning(f"Feature {feature} not found, using default value")
                    df_with_features[feature] = 0.0
                    feature_cols.append(feature)
            
            logger.info(f"Selected {len(feature_cols)} core features: {feature_cols}")
            
            # Remove any remaining NaN values
            df_clean = df_with_features[feature_cols + ['close']].dropna()
            logger.info(f"Clean data shape: {df_clean.shape}")
            
            # Extract features and target
            X = df_clean[feature_cols].values.astype(np.float32)
            y = df_clean['close'].values.astype(np.float32)
            
            # Store feature names
            self.feature_names = feature_cols
            
            # Split data (time series split - use last 20% for testing)
            split_idx = int(len(X) * 0.8)
            self.X_train = X[:split_idx]
            self.X_test = X[split_idx:]
            self.y_train = y[:split_idx]
            self.y_test = y[split_idx:]
            
            logger.info(f"Training set: {self.X_train.shape}")
            logger.info(f"Test set: {self.X_test.shape}")
            logger.info(f"Features: {len(self.feature_names)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False
    
    def add_core_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add 7 core features for 6-layer enterprise system"""
        try:
            df = df.copy()
            
            # 1. close - already exists
            # 2. volume - already exists
            
            # 3. RSI for Layer 3: Reversal Detection
            if TA_AVAILABLE:
                df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            else:
                df['rsi'] = self.calculate_rsi_simple(df['close'])
            
            # 4. MACD for Layer 3: Reversal Detection
            if TA_AVAILABLE:
                macd = ta.trend.MACD(df['close'])
                df['macd'] = macd.macd()
            else:
                df['macd'] = df['close'].ewm(span=12).mean() - df['close'].ewm(span=26).mean()
            
            # 5. Bollinger Bands Position for Layer 4: Technical Filters
            if TA_AVAILABLE:
                bb = ta.volatility.BollingerBands(df['close'])
                df['bb_upper'] = bb.bollinger_hband()
                df['bb_lower'] = bb.bollinger_lband()
                df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            else:
                sma_20 = df['close'].rolling(20).mean()
                std_20 = df['close'].rolling(20).std()
                df['bb_upper'] = sma_20 + (std_20 * 2)
                df['bb_lower'] = sma_20 - (std_20 * 2)
                df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # 6. Volatility for Layer 4: Technical Filters
            df['volatility'] = df['close'].rolling(20).std() / df['close']
            
            # 7. Trend Strength for Layer 1: Market Regime
            df['trend_strength'] = abs(df['close'].pct_change(periods=60))
            
            logger.info(f"Core features added. Shape: {df.shape}")
            return df
            
        except Exception as e:
            logger.error(f"Error adding features: {e}")
            return df
    
    def calculate_rsi_simple(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Simple RSI calculation"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def train_layer_1_market_regime(self) -> bool:
        """Train Layer 1: Market Regime Detection"""
        try:
            logger.info("Training Layer 1: Market Regime Detection")
            
            # Create regime labels based on trend strength and volatility
            regime_labels = []
            for i in range(len(self.X_train)):
                trend = self.X_train[i][6]  # trend_strength
                vol = self.X_train[i][5]    # volatility
                
                if trend > 0.02 and vol < 0.01:
                    regime_labels.append('bull')
                elif trend > 0.02 and vol > 0.01:
                    regime_labels.append('volatile')
                elif trend < 0.01 and vol < 0.01:
                    regime_labels.append('sideways')
                else:
                    regime_labels.append('bear')
            
            # Train XGBoost classifier for regime detection
            regime_model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )
            
            regime_model.fit(self.X_train, regime_labels)
            
            # Test performance
            test_regime_labels = []
            for i in range(len(self.X_test)):
                trend = self.X_test[i][6]
                vol = self.X_test[i][5]
                
                if trend > 0.02 and vol < 0.01:
                    test_regime_labels.append('bull')
                elif trend > 0.02 and vol > 0.01:
                    test_regime_labels.append('volatile')
                elif trend < 0.01 and vol < 0.01:
                    test_regime_labels.append('sideways')
                else:
                    test_regime_labels.append('bear')
            
            accuracy = regime_model.score(self.X_test, test_regime_labels)
            
            self.models['layer_1_regime'] = regime_model
            self.layer_performance['layer_1'] = {
                'accuracy': accuracy,
                'model_type': 'XGBoost Classifier',
                'features': self.feature_names
            }
            
            logger.info(f"Layer 1 trained - Accuracy: {accuracy:.4f}")
            return True
            
        except Exception as e:
            logger.error(f"Error training Layer 1: {e}")
            return False
    
    def train_layer_2_lstm_ensemble(self) -> bool:
        """Train Layer 2: LSTM Ensemble (1h, 4h, 24h models)"""
        if not TENSORFLOW_AVAILABLE:
            logger.warning("TensorFlow not available - skipping LSTM training")
            return False
            
        try:
            logger.info("Training Layer 2: LSTM Ensemble")
            
            # Create sequences for LSTM
            sequence_length = 60
            X_seq, y_seq = self.create_sequences(self.X_train, self.y_train, sequence_length)
            
            # Train 3 LSTM models for different timeframes
            lstm_models = {}
            
            # 1h model
            lstm_1h = self.build_lstm_model(sequence_length, len(self.feature_names))
            lstm_1h.fit(X_seq, y_seq, epochs=50, batch_size=32, validation_split=0.2, verbose=0)
            lstm_models['lstm_1h'] = lstm_1h
            
            # 4h model (longer sequence)
            sequence_length_4h = 240
            X_seq_4h, y_seq_4h = self.create_sequences(self.X_train, self.y_train, sequence_length_4h)
            lstm_4h = self.build_lstm_model(sequence_length_4h, len(self.feature_names))
            lstm_4h.fit(X_seq_4h, y_seq_4h, epochs=50, batch_size=32, validation_split=0.2, verbose=0)
            lstm_models['lstm_4h'] = lstm_4h
            
            # 24h model (shorter sequence)
            sequence_length_24h = 30
            X_seq_24h, y_seq_24h = self.create_sequences(self.X_train, self.y_train, sequence_length_24h)
            lstm_24h = self.build_lstm_model(sequence_length_24h, len(self.feature_names))
            lstm_24h.fit(X_seq_24h, y_seq_24h, epochs=50, batch_size=32, validation_split=0.2, verbose=0)
            lstm_models['lstm_24h'] = lstm_24h
            
            self.models['layer_2_lstm'] = lstm_models
            self.layer_performance['layer_2'] = {
                'models': ['lstm_1h', 'lstm_4h', 'lstm_24h'],
                'sequence_lengths': [60, 240, 30],
                'model_type': 'LSTM Ensemble'
            }
            
            logger.info("Layer 2 trained - LSTM Ensemble")
            return True
            
        except Exception as e:
            logger.error(f"Error training Layer 2: {e}")
            return False
    
    def create_sequences(self, X: np.ndarray, y: np.ndarray, sequence_length: int) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training"""
        X_seq, y_seq = [], []
        for i in range(sequence_length, len(X)):
            X_seq.append(X[i-sequence_length:i])
            y_seq.append(y[i])
        return np.array(X_seq), np.array(y_seq)
    
    def build_lstm_model(self, sequence_length: int, n_features: int):
        """Build LSTM model architecture"""
        model = Sequential([
            LSTM(64, return_sequences=True, input_shape=(sequence_length, n_features)),
            Dropout(0.2),
            LSTM(32, return_sequences=False),
            Dropout(0.2),
            Dense(16, activation='relu'),
            Dense(1, activation='linear')
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def train_layer_3_reversal_detection(self) -> bool:
        """Train Layer 3: Reversal Detection"""
        try:
            logger.info("Training Layer 3: Reversal Detection")
            
            # Create reversal labels based on RSI and MACD
            reversal_labels = []
            for i in range(len(self.X_train)):
                rsi = self.X_train[i][2]  # rsi
                macd = self.X_train[i][3]  # macd
                
                # RSI oversold/overbought
                rsi_reversal = (rsi < 30 or rsi > 70)
                # MACD zero crossing
                macd_reversal = abs(macd) < 0.001
                
                if rsi_reversal or macd_reversal:
                    reversal_labels.append(1)  # Reversal detected
                else:
                    reversal_labels.append(0)  # No reversal
            
            # Train LightGBM for reversal detection
            reversal_model = lgb.LGBMClassifier(
                n_estimators=100,
                max_depth=6,  # 2^6=64 > 63 leaves (removes warning)
                num_leaves=63,
                learning_rate=0.1,
                random_state=42
            )
            
            reversal_model.fit(self.X_train, reversal_labels)
            
            # Test performance
            test_reversal_labels = []
            for i in range(len(self.X_test)):
                rsi = self.X_test[i][2]
                macd = self.X_test[i][3]
                
                rsi_reversal = (rsi < 30 or rsi > 70)
                macd_reversal = abs(macd) < 0.001
                
                if rsi_reversal or macd_reversal:
                    test_reversal_labels.append(1)
                else:
                    test_reversal_labels.append(0)
            
            accuracy = reversal_model.score(self.X_test, test_reversal_labels)
            
            self.models['layer_3_reversal'] = reversal_model
            self.layer_performance['layer_3'] = {
                'accuracy': accuracy,
                'model_type': 'LightGBM Classifier',
                'features': ['rsi', 'macd']
            }
            
            logger.info(f"Layer 3 trained - Accuracy: {accuracy:.4f}")
            return True
            
        except Exception as e:
            logger.error(f"Error training Layer 3: {e}")
            return False
    
    def train_layer_4_technical_filters(self) -> bool:
        """Train Layer 4: Technical Filters"""
        try:
            logger.info("Training Layer 4: Technical Filters")
            
            # Create filter labels based on BB position and volatility
            filter_labels = []
            for i in range(len(self.X_train)):
                bb_pos = self.X_train[i][4]  # bb_position
                vol = self.X_train[i][5]     # volatility
                
                # Filter conditions
                bb_extreme = (bb_pos < 0.1 or bb_pos > 0.9)
                vol_high = vol > 0.02
                
                if bb_extreme or vol_high:
                    filter_labels.append(0)  # Filter out
                else:
                    filter_labels.append(1)  # Pass filter
            
            # Train Random Forest for technical filters
            from sklearn.ensemble import RandomForestClassifier
            filter_model = RandomForestClassifier(
                n_estimators=100,
                max_depth=6,
                random_state=42
            )
            
            filter_model.fit(self.X_train, filter_labels)
            
            # Test performance
            test_filter_labels = []
            for i in range(len(self.X_test)):
                bb_pos = self.X_test[i][4]
                vol = self.X_test[i][5]
                
                bb_extreme = (bb_pos < 0.1 or bb_pos > 0.9)
                vol_high = vol > 0.02
                
                if bb_extreme or vol_high:
                    test_filter_labels.append(0)
                else:
                    test_filter_labels.append(1)
            
            accuracy = filter_model.score(self.X_test, test_filter_labels)
            
            self.models['layer_4_filters'] = filter_model
            self.layer_performance['layer_4'] = {
                'accuracy': accuracy,
                'model_type': 'Random Forest Classifier',
                'features': ['bb_position', 'volatility']
            }
            
            logger.info(f"Layer 4 trained - Accuracy: {accuracy:.4f}")
            return True
            
        except Exception as e:
            logger.error(f"Error training Layer 4: {e}")
            return False
    
    def train_layer_5_confidence_scoring(self) -> bool:
        """Train Layer 5: Confidence Scoring"""
        try:
            logger.info("Training Layer 5: Confidence Scoring")
            
            # Create confidence scores based on feature agreement
            confidence_scores = []
            for i in range(len(self.X_train)):
                # Calculate confidence based on feature stability
                rsi = self.X_train[i][2]
                macd = self.X_train[i][3]
                bb_pos = self.X_train[i][4]
                vol = self.X_train[i][5]
                
                # Confidence factors
                rsi_confidence = 1.0 - abs(rsi - 50) / 50  # Higher confidence when RSI near 50
                macd_confidence = 1.0 - abs(macd) / 0.01   # Higher confidence when MACD near 0
                bb_confidence = 1.0 - abs(bb_pos - 0.5)    # Higher confidence when price near BB middle
                vol_confidence = 1.0 - min(vol / 0.02, 1.0)  # Higher confidence with lower volatility
                
                # Average confidence
                avg_confidence = (rsi_confidence + macd_confidence + bb_confidence + vol_confidence) / 4
                confidence_scores.append(avg_confidence)
            
            # Train XGBoost regressor for confidence scoring
            confidence_model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )
            
            confidence_model.fit(self.X_train, confidence_scores)
            
            # Test performance
            test_confidence_scores = []
            for i in range(len(self.X_test)):
                rsi = self.X_test[i][2]
                macd = self.X_test[i][3]
                bb_pos = self.X_test[i][4]
                vol = self.X_test[i][5]
                
                rsi_confidence = 1.0 - abs(rsi - 50) / 50
                macd_confidence = 1.0 - abs(macd) / 0.01
                bb_confidence = 1.0 - abs(bb_pos - 0.5)
                vol_confidence = 1.0 - min(vol / 0.02, 1.0)
                
                avg_confidence = (rsi_confidence + macd_confidence + bb_confidence + vol_confidence) / 4
                test_confidence_scores.append(avg_confidence)
            
            r2 = confidence_model.score(self.X_test, test_confidence_scores)
            
            self.models['layer_5_confidence'] = confidence_model
            self.layer_performance['layer_5'] = {
                'r2_score': r2,
                'model_type': 'XGBoost Regressor',
                'features': self.feature_names
            }
            
            logger.info(f"Layer 5 trained - R²: {r2:.4f}")
            return True
            
        except Exception as e:
            logger.error(f"Error training Layer 5: {e}")
            return False
    
    def train_layer_6_adaptive_timing(self) -> bool:
        """Train Layer 6: Adaptive Timing"""
        try:
            logger.info("Training Layer 6: Adaptive Timing")
            
            # Create timing labels (hold duration in minutes)
            timing_labels = []
            for i in range(len(self.X_train)):
                trend = self.X_train[i][6]  # trend_strength
                vol = self.X_train[i][5]    # volatility
                rsi = self.X_train[i][2]    # rsi
                
                # Adaptive timing logic
                if trend > 0.03:  # Strong trend
                    base_time = 120  # 2 hours
                elif trend > 0.01:  # Medium trend
                    base_time = 60   # 1 hour
                else:  # Weak trend
                    base_time = 30   # 30 minutes
                
                # Adjust for volatility
                if vol > 0.02:  # High volatility
                    base_time = int(base_time * 0.5)  # Shorter hold time
                
                # Adjust for RSI extremes
                if rsi < 30 or rsi > 70:
                    base_time = int(base_time * 0.7)  # Shorter hold time
                
                timing_labels.append(max(15, min(240, base_time)))  # 15min to 4h range
            
            # Train LightGBM for adaptive timing
            timing_model = lgb.LGBMRegressor(
                n_estimators=100,
                max_depth=6,  # 2^6=64 > 63 leaves (removes warning)
                num_leaves=63,
                learning_rate=0.1,
                random_state=42
            )
            
            timing_model.fit(self.X_train, timing_labels)
            
            # Test performance
            test_timing_labels = []
            for i in range(len(self.X_test)):
                trend = self.X_test[i][6]
                vol = self.X_test[i][5]
                rsi = self.X_test[i][2]
                
                if trend > 0.03:
                    base_time = 120
                elif trend > 0.01:
                    base_time = 60
                else:
                    base_time = 30
                
                if vol > 0.02:
                    base_time = int(base_time * 0.5)
                
                if rsi < 30 or rsi > 70:
                    base_time = int(base_time * 0.7)
                
                test_timing_labels.append(max(15, min(240, base_time)))
            
            r2 = timing_model.score(self.X_test, test_timing_labels)
            
            self.models['layer_6_timing'] = timing_model
            self.layer_performance['layer_6'] = {
                'r2_score': r2,
                'model_type': 'LightGBM Regressor',
                'features': self.feature_names
            }
            
            logger.info(f"Layer 6 trained - R²: {r2:.4f}")
            return True
            
        except Exception as e:
            logger.error(f"Error training Layer 6: {e}")
            return False
    
    def save_models(self) -> None:
        """Save all trained models"""
        try:
            logger.info("Saving 6-layer enterprise models...")
            
            # Save each layer model
            for layer_name, model in self.models.items():
                model_path = self.models_dir / f"{layer_name}.pkl"
                
                if layer_name == 'layer_2_lstm':
                    # Save LSTM models separately
                    for lstm_name, lstm_model in model.items():
                        lstm_path = self.models_dir / f"{lstm_name}.h5"
                        lstm_model.save(lstm_path)
                        logger.info(f"Saved {lstm_name} to {lstm_path}")
                else:
                    # Save other models with pickle
                    with open(model_path, 'wb') as f:
                        pickle.dump(model, f)
                    logger.info(f"Saved {layer_name} to {model_path}")
            
            # Save metadata
            metadata = {
                'training_date': datetime.now().isoformat(),
                'feature_names': self.feature_names,
                'layer_performance': self.layer_performance,
                'model_versions': {
                    'layer_1': 'v2.1.0',
                    'layer_2': 'v2.1.0', 
                    'layer_3': 'v2.1.0',
                    'layer_4': 'v2.1.0',
                    'layer_5': 'v2.1.0',
                    'layer_6': 'v2.1.0'
                },
                'system_version': '6-Layer Enterprise v3.0.0'
            }
            
            metadata_path = self.models_dir / "enterprise_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved metadata to {metadata_path}")
            
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    def train_complete_system(self) -> Dict[str, Any]:
        """Train the complete 6-layer enterprise system"""
        try:
            logger.info("🚀 Starting 6-Layer Enterprise Training")
            logger.info("=" * 60)
            
            # Load and prepare data
            if not self.load_and_prepare_data():
                return {'success': False, 'error': 'Data loading failed'}
            
            # Train all 6 layers
            layer_results = {}
            
            # Layer 1: Market Regime Detection
            layer_results['layer_1'] = self.train_layer_1_market_regime()
            
            # Layer 2: LSTM Ensemble
            layer_results['layer_2'] = self.train_layer_2_lstm_ensemble()
            
            # Layer 3: Reversal Detection
            layer_results['layer_3'] = self.train_layer_3_reversal_detection()
            
            # Layer 4: Technical Filters
            layer_results['layer_4'] = self.train_layer_4_technical_filters()
            
            # Layer 5: Confidence Scoring
            layer_results['layer_5'] = self.train_layer_5_confidence_scoring()
            
            # Layer 6: Adaptive Timing
            layer_results['layer_6'] = self.train_layer_6_adaptive_timing()
            
            # Save all models
            self.save_models()
            
            # Summary
            successful_layers = sum(layer_results.values())
            total_layers = len(layer_results)
            
            logger.info("=" * 60)
            logger.info(f"🎯 6-Layer Enterprise Training Complete!")
            logger.info(f"✅ Successful layers: {successful_layers}/{total_layers}")
            
            for layer_name, success in layer_results.items():
                status = "✅" if success else "❌"
                logger.info(f"{status} {layer_name}")
            
            return {
                'success': True,
                'layers_trained': successful_layers,
                'total_layers': total_layers,
                'layer_results': layer_results,
                'performance': self.layer_performance,
                'models_dir': str(self.models_dir)
            }
            
        except Exception as e:
            logger.error(f"Error in complete training: {e}")
            return {'success': False, 'error': str(e)}


def main():
    """Main training function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='6-Layer Enterprise Trainer')
    parser.add_argument('--quick', action='store_true', help='Quick training with smaller dataset')
    parser.add_argument('--data-path', type=str, help='Path to training data')
    parser.add_argument('--models-dir', type=str, help='Path to save models')
    
    args = parser.parse_args()
    
    # Initialize trainer
    trainer = SixLayerEnterpriseTrainer(
        data_path=args.data_path,
        models_dir=args.models_dir
    )
    
    # Train complete system
    result = trainer.train_complete_system()
    
    if result['success']:
        print(f"\n🎉 6-Layer Enterprise Training Successful!")
        print(f"📁 Models saved to: {result['models_dir']}")
        print(f"📊 Layers trained: {result['layers_trained']}/{result['total_layers']}")
    else:
        print(f"\n❌ Training failed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main() 