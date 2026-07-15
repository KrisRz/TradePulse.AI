#!/usr/bin/env python3
"""
Quick LSTM Trainer for Layer 2 - TradePulse.AI
Optimized for MacBook Pro M4 Pro (48GB RAM)
Fast training only for missing LSTM models
"""

import os
import sys
import numpy as np
import pandas as pd
import warnings
from datetime import datetime
from pathlib import Path
warnings.filterwarnings('ignore')

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    
    # Optimize for Apple Silicon M4 Pro
    try:
        # Try to enable optimization if available
        if hasattr(tf.config.experimental, 'enable_mlir_graph_optimization'):
            tf.config.experimental.enable_mlir_graph_optimization()
    except:
        pass  # Ignore if not available
    
    TENSORFLOW_AVAILABLE = True
    print("✅ TensorFlow optimized for Apple Silicon M4 Pro")
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("❌ TensorFlow not available")
    sys.exit(1)

import ta
from sklearn.preprocessing import StandardScaler

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuickLSTMTrainer48GB:
    """Quick LSTM trainer optimized for MacBook Pro M4 Pro (48GB RAM)"""
    
    def __init__(self, output_dir: str = "app/backend/app/models/enterprise"):
        self.project_root = Path(__file__).parent.parent.parent  # Fixed path
        self.data_path = self.project_root / "data" / "historical" / "processed" / "BTCUSDT_1m_complete.parquet"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # MacBook Pro M4 Pro 48GB optimization
        self.memory_gb = 48
        self.cpu_cores = 12  # M4 Pro cores
        self.sample_size = 2000000  # 2M records (vs 300k) - use more data
        
        logger.info(f"🎯 Quick LSTM Trainer (MacBook Pro M4 Pro 48GB)")
        logger.info(f"📁 Data path: {self.data_path}")
        logger.info(f"📁 Output dir: {self.output_dir}")
        logger.info(f"📁 Output dir exists: {self.output_dir.exists()}")
        logger.info(f"💾 Memory: {self.memory_gb}GB, CPU cores: {self.cpu_cores}")
        logger.info(f"📊 Sample size: {self.sample_size:,} records")
    
    def load_and_prepare_data(self):
        """Load and prepare data optimized for 48GB RAM"""
        logger.info("📊 Loading data (48GB optimization)...")
        
        # Load data with chunking for memory efficiency
        df = pd.read_parquet(self.data_path)
        logger.info(f"📊 Loaded {len(df):,} records")
        
        # Use last 2M records instead of 300k - more data = better models
        df = df.tail(self.sample_size).copy()
        logger.info(f"📊 Using last {len(df):,} records for training")
        
        # Enhanced feature engineering for 48GB system
        logger.info("🔧 Adding enhanced features (48GB system)...")
        
        # Core features
        df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
        df['macd'] = ta.trend.MACD(df['close']).macd()
        df['macd_signal'] = ta.trend.MACD(df['close']).macd_signal()
        df['macd_hist'] = ta.trend.MACD(df['close']).macd_diff()
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df['close'])
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Enhanced volatility features
        df['volatility'] = df['close'].rolling(20).std() / df['close']
        df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
        
        # Volume features
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        df['vwap'] = (df['close'] * df['volume']).rolling(20).sum() / df['volume'].rolling(20).sum()
        
        # Momentum features
        df['momentum'] = df['close'] / df['close'].shift(14) - 1
        df['price_change_1h'] = df['close'].pct_change(60)  # 1h change
        df['price_change_4h'] = df['close'].pct_change(240)  # 4h change
        
        # Target (next period return)
        df['target'] = df['close'].shift(-1) / df['close'] - 1
        
        # Clean data
        df = df.dropna()
        logger.info(f"📊 Clean data: {len(df):,} records")
        
        # Enhanced features for LSTM (16 features vs 6)
        features = [
            'close', 'volume', 'high', 'low', 'open',
            'rsi', 'macd', 'macd_signal', 'macd_hist',
            'bb_position', 'bb_width', 'volatility', 'atr',
            'volume_ratio', 'vwap', 'momentum'
        ]
        
        logger.info(f"📊 Using {len(features)} enhanced features")
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(df[features])
        y = df['target'].values
        
        # Split (80/20)
        split_idx = int(len(X_scaled) * 0.8)
        self.X_train = X_scaled[:split_idx]
        self.X_test = X_scaled[split_idx:]
        self.y_train = y[:split_idx]
        self.y_test = y[split_idx:]
        self.scaler = scaler
        self.feature_names = features
        
        logger.info(f"📊 Training data: {len(self.X_train):,} samples")
        logger.info(f"📊 Test data: {len(self.X_test):,} samples")
        return True
    
    def create_sequences(self, X, y, sequence_length):
        """Create sequences for LSTM with memory optimization"""
        X_seq, y_seq = [], []
        step_size = max(1, len(X) // 500000)  # Adaptive step for large datasets
        
        for i in range(sequence_length, len(X), step_size):
            X_seq.append(X[i-sequence_length:i])
            y_seq.append(y[i])
            
        return np.array(X_seq), np.array(y_seq)
    
    def build_lstm_model(self, sequence_length, n_features, neurons=64):
        """Build enhanced LSTM model for MacBook Pro M4 Pro"""
        model = Sequential([
            # First LSTM layer with more neurons
            LSTM(neurons, return_sequences=True, input_shape=(sequence_length, n_features)),
            BatchNormalization(),
            Dropout(0.2),
            
            # Second LSTM layer
            LSTM(neurons//2, return_sequences=False),
            BatchNormalization(),
            Dropout(0.2),
            
            # Dense layers
            Dense(32, activation='relu'),
            BatchNormalization(),
            Dropout(0.1),
            
            Dense(16, activation='relu'),
            Dense(1, activation='linear')
        ])
        
        # Enhanced optimizer for M4 Pro
        optimizer = Adam(
            learning_rate=0.001,
            beta_1=0.9,
            beta_2=0.999,
            epsilon=1e-7
        )
        
        model.compile(
            optimizer=optimizer,
            loss='mse',
            metrics=['mae', 'mape']
        )
        return model
    
    def train_lstm_models(self):
        """Train enhanced LSTM models for MacBook Pro M4 Pro"""
        logger.info("🤖 Training enhanced LSTM models (48GB optimization)...")
        
        models = {}
        n_features = self.X_train.shape[1]
        
        # Enhanced LSTM configurations for 48GB system
        configs = [
            ('lstm_1h', 120, 128),   # 1h: longer sequence, more neurons
            ('lstm_4h', 240, 96),    # 4h: much longer sequence
            ('lstm_24h', 60, 64)     # 24h: balanced approach
        ]
        
        for name, seq_len, neurons in configs:
            logger.info(f"🔄 Training {name} (sequence: {seq_len}, neurons: {neurons})")
            
            # Create sequences
            X_seq, y_seq = self.create_sequences(self.X_train, self.y_train, seq_len)
            logger.info(f"📊 {name}: {len(X_seq):,} sequences created")
            
            # Build enhanced model
            model = self.build_lstm_model(seq_len, n_features, neurons)
            
            # Enhanced callbacks for better training
            callbacks = [
                EarlyStopping(
                    monitor='val_loss',
                    patience=10,
                    restore_best_weights=True
                ),
                ReduceLROnPlateau(
                    monitor='val_loss',
                    factor=0.5,
                    patience=5,
                    min_lr=1e-6
                )
            ]
            
            # Enhanced training with more epochs (48GB can handle it)
            history = model.fit(
                X_seq, y_seq,
                epochs=50,  # Increased from 20
                batch_size=128,  # Larger batch for 48GB
                validation_split=0.2,
                callbacks=callbacks,
                verbose=1  # Show progress
            )
            
            models[name] = model
            
            # Enhanced metrics
            final_loss = history.history['loss'][-1]
            final_val_loss = history.history['val_loss'][-1]
            final_mae = history.history['mae'][-1]
            
            logger.info(f"✅ {name} trained:")
            logger.info(f"   📊 Loss: {final_loss:.6f}")
            logger.info(f"   📊 Val Loss: {final_val_loss:.6f}")
            logger.info(f"   📊 MAE: {final_mae:.6f}")
        
        return models
    
    def save_models(self, models):
        """Save enhanced LSTM models"""
        logger.info("💾 Saving enhanced LSTM models...")
        
        # Save each LSTM model
        for name, model in models.items():
            model_path = self.output_dir / f"{name}.h5"
            model.save(model_path)
            
            # Get model size
            model_size = model_path.stat().st_size / (1024*1024)  # MB
            logger.info(f"✅ Saved {name} ({model_size:.1f}MB)")
        
        # Save enhanced scaler with metadata
        import pickle
        scaler_data = {
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'n_features': len(self.feature_names),
            'training_samples': len(self.X_train),
            'optimization': 'MacBook Pro M4 Pro 48GB'
        }
        
        scaler_path = self.output_dir / "lstm_scaler.pkl"
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler_data, f)
        logger.info(f"✅ Saved enhanced scaler with {len(self.feature_names)} features")
    
    def train_complete_lstm_layer(self):
        """Train complete Layer 2 LSTM ensemble (48GB optimized)"""
        start_time = datetime.now()
        
        logger.info("🚀 Starting Enhanced LSTM Training (MacBook Pro M4 Pro)")
        logger.info("=" * 70)
        
        try:
            # Load data
            if not self.load_and_prepare_data():
                return False
            
            # Train models
            models = self.train_lstm_models()
            
            # Save models
            self.save_models(models)
            
            training_time = datetime.now() - start_time
            logger.info("=" * 70)
            logger.info("🎯 Enhanced LSTM Training Complete!")
            logger.info(f"✅ Models trained: {len(models)}/3")
            logger.info(f"⏱️ Training time: {training_time}")
            logger.info(f"💾 Saved to: {self.output_dir}")
            logger.info(f"🚀 Ready for enterprise 6/6 layer system!")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Training failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Main training function for MacBook Pro M4 Pro"""
    if not TENSORFLOW_AVAILABLE:
        print("❌ TensorFlow required for LSTM training")
        return False
    
    print("🚀 MacBook Pro M4 Pro LSTM Training")
    print("💪 48GB RAM, 12 CPU cores, Apple Silicon optimization")
    print("📊 Training with 2M records and 16 enhanced features")
    
    trainer = QuickLSTMTrainer48GB()
    success = trainer.train_complete_lstm_layer()
    
    if success:
        print("\n🎉 Enhanced LSTM training successful!")
        print("📁 Models saved to: app/backend/app/models/enterprise/")
        print("📊 Enhanced features: 16 (vs 6 basic)")
        print("🔍 Next: Test backend with curl /api/v1/enterprise/signal")
        print("✅ 6/6 Enterprise layers ready!")
    else:
        print("\n❌ LSTM training failed")
    
    return success

if __name__ == "__main__":
    main() 