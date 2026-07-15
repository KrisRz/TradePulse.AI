#!/usr/bin/env python3
"""
Layer 5 Confidence Model - Enhanced Retraining (v2.0)
======================================================

ENTERPRISE-GRADE RETRAINING with fresh 3-month Binance data

Features:
- All 9 SSOT features (not just 6!)
- Session context (asian/european/us/overlap)
- Feature normalization (StandardScaler)
- Simulated confidence targets from actual market outcomes
- Day trading optimized (3-month fresh data)

Author: TradePulse.AI
Date: 2025-10-31
"""

import sys
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
import pickle

# Setup paths
script_dir = Path(__file__).parent
backend_dir = script_dir.parent.parent
sys.path.insert(0, str(backend_dir))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
app_dir = backend_dir.parent  # Go up from backend/ to app/
BINANCE_DATA_PATH = app_dir / "data" / "ml" / "historical" / "binance_fresh" / "BTCUSDT_1m_3months.parquet"
OUTPUT_DIR = backend_dir / "models" / "enterprise"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class Layer5EnhancedTrainer:
    """Enhanced Layer 5 Confidence Model Trainer"""
    
    # ALL 9 SSOT FEATURES (enterprise standard)
    FEATURE_NAMES = [
        'close',
        'volume',
        'rsi',
        'macd',
        'bb_position',
        'volatility',
        'trend_strength',
        'volume_ratio',
        'price_change_24h'
    ]
    
    # Session context features (additional)
    SESSION_FEATURES = [
        'session_asian',      # 1 if Asian session, 0 otherwise
        'session_european',   # 1 if European session, 0 otherwise
        'session_us',         # 1 if US session, 0 otherwise
        'session_overlap',    # 1 if overlap, 0 otherwise
        'hour_of_day',        # 0-23
        'volatility_regime'   # 0=low, 1=normal, 2=high
    ]
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.model = None
        self.feature_importances = None
        
    def load_binance_data(self) -> pd.DataFrame:
        """Load fresh 3-month Binance data"""
        logger.info(f"📂 Loading Binance data from {BINANCE_DATA_PATH}...")
        
        if not BINANCE_DATA_PATH.exists():
            raise FileNotFoundError(f"Binance data not found: {BINANCE_DATA_PATH}")
        
        # Load parquet
        df = pd.read_parquet(BINANCE_DATA_PATH)
        
        logger.info(f"✅ Loaded {len(df):,} candles")
        logger.info(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        return df
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all 9 SSOT features + session context"""
        logger.info("🔧 Calculating technical indicators...")
        
        df = df.copy()
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # 1. RSI (14-period)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 2. MACD (12, 26, 9)
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_12 - ema_26
        
        # 3. Bollinger Bands Position
        sma_20 = df['close'].rolling(window=20).mean()
        std_20 = df['close'].rolling(window=20).std()
        bb_upper = sma_20 + (std_20 * 2)
        bb_lower = sma_20 - (std_20 * 2)
        df['bb_position'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
        df['bb_position'] = df['bb_position'].clip(0, 1)
        
        # 4. Volatility (ATR-based)
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=14).mean()
        df['volatility'] = atr / df['close']
        
        # 5. Trend Strength (linear regression slope)
        def calc_trend(series):
            if len(series) < 2:
                return 0
            x = np.arange(len(series))
            slope = np.polyfit(x, series, 1)[0]
            return slope / series.iloc[-1] if series.iloc[-1] != 0 else 0
        
        df['trend_strength'] = df['close'].rolling(window=20).apply(calc_trend, raw=False)
        
        # 6. Volume Ratio (current vs 20-period average)
        avg_volume = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / avg_volume
        
        # 7. Price Change 24h (1440 candles = 24 hours)
        df['price_change_24h'] = ((df['close'] - df['close'].shift(1440)) / df['close'].shift(1440)) * 100
        
        # 8. Session Context
        df['hour_utc'] = pd.to_datetime(df['timestamp']).dt.hour
        
        # Session definitions (UTC hours)
        # Asian: 0-8 UTC, European: 7-15 UTC, US: 13-21 UTC
        df['session_asian'] = ((df['hour_utc'] >= 0) & (df['hour_utc'] < 8)).astype(int)
        df['session_european'] = ((df['hour_utc'] >= 7) & (df['hour_utc'] < 15)).astype(int)
        df['session_us'] = ((df['hour_utc'] >= 13) & (df['hour_utc'] < 21)).astype(int)
        df['session_overlap'] = ((df['session_asian'] + df['session_european'] + df['session_us']) > 1).astype(int)
        df['hour_of_day'] = df['hour_utc']
        
        # 9. Volatility Regime (0=low, 1=normal, 2=high)
        vol_20_mean = df['volatility'].rolling(window=1440).mean()  # 24h average
        df['volatility_regime'] = 1  # Default: normal
        df.loc[df['volatility'] < vol_20_mean * 0.7, 'volatility_regime'] = 0  # Low
        df.loc[df['volatility'] > vol_20_mean * 1.3, 'volatility_regime'] = 2  # High
        
        # Drop NaN rows (initial warmup period)
        df = df.dropna()
        
        logger.info(f"✅ Calculated indicators for {len(df):,} candles")
        
        return df
    
    def simulate_confidence_targets(self, df: pd.DataFrame, sample_interval: int = 15) -> pd.DataFrame:
        """
        Simulate confidence targets by looking ahead at trade outcomes.
        
        Strategy:
        - Sample every N minutes (potential entry points)
        - Look ahead 1-6 hours to see if a trade would be profitable
        - Assign confidence target based on:
          * High confidence (0.75-0.90): Strong profit potential (>1.5% gain)
          * Medium confidence (0.50-0.65): Moderate potential (0.5-1.5% gain)
          * Low confidence (0.20-0.40): High risk (potential loss >-0.5%)
        """
        logger.info(f"🎯 Simulating confidence targets (sample every {sample_interval} min)...")
        
        samples = []
        
        # Sample every N minutes
        for i in range(0, len(df), sample_interval):
            entry = df.iloc[i]
            entry_price = entry['close']
            entry_idx = i
            
            # Look ahead windows: 60min (1h), 120min (2h), 240min (4h), 360min (6h)
            lookahead_windows = [60, 120, 240, 360]
            
            max_gain = 0
            max_loss = 0
            
            for window in lookahead_windows:
                end_idx = min(entry_idx + window, len(df) - 1)
                if end_idx <= entry_idx:
                    continue
                
                # Get price action in this window
                future_prices = df.iloc[entry_idx:end_idx]['close'].values
                
                if len(future_prices) == 0:
                    continue
                
                # Calculate max gain/loss in this window
                window_max = np.max(future_prices)
                window_min = np.min(future_prices)
                
                gain_pct = ((window_max - entry_price) / entry_price) * 100
                loss_pct = ((window_min - entry_price) / entry_price) * 100
                
                max_gain = max(max_gain, gain_pct)
                max_loss = min(max_loss, loss_pct)
            
            # Assign confidence target based on profit potential
            if max_gain > 1.5 and max_loss > -0.5:
                # Strong profit potential with manageable risk
                confidence_target = np.random.uniform(0.75, 0.90)
            elif max_gain > 0.8 and max_loss > -0.8:
                # Moderate profit potential
                confidence_target = np.random.uniform(0.60, 0.75)
            elif max_gain > 0.3 and max_loss > -1.0:
                # Small profit potential
                confidence_target = np.random.uniform(0.45, 0.60)
            else:
                # High risk or sideways
                confidence_target = np.random.uniform(0.20, 0.45)
            
            # Build sample
            sample = {
                'close': entry['close'],
                'volume': entry['volume'],
                'rsi': entry['rsi'],
                'macd': entry['macd'],
                'bb_position': entry['bb_position'],
                'volatility': entry['volatility'],
                'trend_strength': entry['trend_strength'],
                'volume_ratio': entry['volume_ratio'],
                'price_change_24h': entry['price_change_24h'],
                'session_asian': entry['session_asian'],
                'session_european': entry['session_european'],
                'session_us': entry['session_us'],
                'session_overlap': entry['session_overlap'],
                'hour_of_day': entry['hour_of_day'],
                'volatility_regime': entry['volatility_regime'],
                'confidence_target': confidence_target,
                'max_gain': max_gain,
                'max_loss': max_loss
            }
            
            samples.append(sample)
        
        training_df = pd.DataFrame(samples)
        
        logger.info(f"✅ Generated {len(training_df):,} training samples")
        logger.info(f"   Confidence distribution:")
        logger.info(f"      Low (0.20-0.45):    {(training_df['confidence_target'] < 0.45).sum():,} ({(training_df['confidence_target'] < 0.45).sum() / len(training_df) * 100:.1f}%)")
        logger.info(f"      Medium (0.45-0.65): {((training_df['confidence_target'] >= 0.45) & (training_df['confidence_target'] < 0.65)).sum():,} ({((training_df['confidence_target'] >= 0.45) & (training_df['confidence_target'] < 0.65)).sum() / len(training_df) * 100:.1f}%)")
        logger.info(f"      High (0.65-0.90):   {(training_df['confidence_target'] >= 0.65).sum():,} ({(training_df['confidence_target'] >= 0.65).sum() / len(training_df) * 100:.1f}%)")
        
        return training_df
    
    def train_model(self, df: pd.DataFrame) -> Tuple[xgb.XGBRegressor, StandardScaler]:
        """Train XGBoost model with all features"""
        logger.info("🤖 Training XGBoost model...")
        
        # Prepare features and target
        all_features = self.FEATURE_NAMES + self.SESSION_FEATURES
        X = df[all_features].values
        y = df['confidence_target'].values
        
        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        logger.info(f"   Train set: {len(X_train):,} samples")
        logger.info(f"   Test set:  {len(X_test):,} samples")
        
        # Normalize features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        logger.info("   ✅ Features normalized (mean=0, std=1)")
        
        # Train XGBoost with optimized parameters
        self.model = xgb.XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            min_child_weight=5,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=0.1,
            random_state=42,
            n_jobs=-1,
            verbosity=0
        )
        
        logger.info("   Training model...")
        self.model.fit(
            X_train_scaled, y_train,
            eval_set=[(X_test_scaled, y_test)],
            verbose=False
        )
        
        # Evaluate
        y_pred_train = self.model.predict(X_train_scaled)
        y_pred_test = self.model.predict(X_test_scaled)
        
        train_mse = mean_squared_error(y_train, y_pred_train)
        test_mse = mean_squared_error(y_test, y_pred_test)
        test_mae = mean_absolute_error(y_test, y_pred_test)
        test_r2 = r2_score(y_test, y_pred_test)
        
        logger.info("   " + "=" * 60)
        logger.info("   📊 MODEL PERFORMANCE")
        logger.info("   " + "=" * 60)
        logger.info(f"   Train MSE: {train_mse:.4f}")
        logger.info(f"   Test MSE:  {test_mse:.4f}")
        logger.info(f"   Test MAE:  {test_mae:.4f}")
        logger.info(f"   Test R²:   {test_r2:.4f}")
        logger.info("   " + "=" * 60)
        
        # Feature importances
        self.feature_importances = self.model.feature_importances_
        feature_importance_df = pd.DataFrame({
            'feature': all_features,
            'importance': self.feature_importances
        }).sort_values('importance', ascending=False)
        
        logger.info("\n   🎯 FEATURE IMPORTANCES:")
        for _, row in feature_importance_df.iterrows():
            bar = '█' * int(row['importance'] * 100)
            logger.info(f"      {row['feature']:20s} {row['importance']:.4f} {bar}")
        
        # Cross-validation
        logger.info("\n   🔄 Running 5-fold cross-validation...")
        cv_scores = cross_val_score(
            self.model, X_train_scaled, y_train,
            cv=5, scoring='neg_mean_squared_error', n_jobs=-1
        )
        cv_mse = -cv_scores.mean()
        cv_std = cv_scores.std()
        
        logger.info(f"   CV MSE: {cv_mse:.4f} (+/- {cv_std:.4f})")
        
        return self.model, self.scaler
    
    def save_model(self):
        """Save model, scaler, and metadata"""
        logger.info("💾 Saving model, scaler, and metadata...")
        
        # Save model
        model_file = OUTPUT_DIR / "layer_5_confidence.pkl"
        with open(model_file, 'wb') as f:
            pickle.dump(self.model, f)
        logger.info(f"   ✅ Saved model: {model_file}")
        
        # Save scaler
        scaler_file = OUTPUT_DIR / "layer_5_confidence_scaler.pkl"
        with open(scaler_file, 'wb') as f:
            pickle.dump(self.scaler, f)
        logger.info(f"   ✅ Saved scaler: {scaler_file}")
        
        # Save metadata
        all_features = self.FEATURE_NAMES + self.SESSION_FEATURES
        metadata = {
            'model_type': 'XGBRegressor',
            'version': 'v2.0_enhanced',
            'trained_date': datetime.now().isoformat(),
            'n_features': len(all_features),
            'features': all_features,
            'core_features': self.FEATURE_NAMES,
            'session_features': self.SESSION_FEATURES,
            'feature_importances': {
                feat: float(imp)
                for feat, imp in zip(all_features, self.feature_importances)
            },
            'data_source': 'binance_3months_1m',
            'data_period': '2025-08-03 to 2025-10-31',
            'trading_mode': 'day_trading',
            'scaling': 'StandardScaler'
        }
        
        metadata_file = OUTPUT_DIR / "layer_5_confidence_metadata.json"
        import json
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"   ✅ Saved metadata: {metadata_file}")


def main():
    """Main training pipeline"""
    logger.info("=" * 70)
    logger.info("🚀 LAYER 5 CONFIDENCE MODEL - ENHANCED RETRAINING (v2.0)")
    logger.info("=" * 70)
    
    trainer = Layer5EnhancedTrainer()
    
    # 1. Load fresh Binance data
    df = trainer.load_binance_data()
    
    # 2. Calculate technical indicators
    df = trainer.calculate_technical_indicators(df)
    
    # 3. Simulate confidence targets
    training_df = trainer.simulate_confidence_targets(df, sample_interval=15)
    
    # Save training data
    app_dir = backend_dir.parent
    training_data_file = app_dir / "data" / "ml" / "training" / "layer5_enhanced" / "layer5_enhanced_training_data.parquet"
    training_data_file.parent.mkdir(parents=True, exist_ok=True)
    training_df.to_parquet(training_data_file)
    logger.info(f"💾 Saved training data: {training_data_file}")
    
    # 4. Train model
    model, scaler = trainer.train_model(training_df)
    
    # 5. Save model
    trainer.save_model()
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ RETRAINING COMPLETED SUCCESSFULLY!")
    logger.info("=" * 70)
    logger.info("📦 Output Files:")
    logger.info(f"   Model:    {OUTPUT_DIR / 'layer_5_confidence.pkl'}")
    logger.info(f"   Scaler:   {OUTPUT_DIR / 'layer_5_confidence_scaler.pkl'}")
    logger.info(f"   Metadata: {OUTPUT_DIR / 'layer_5_confidence_metadata.json'}")
    logger.info("\n🚀 Next Steps:")
    logger.info("   1. Test locally: restart backend")
    logger.info("   2. Monitor confidence distribution in logs")
    logger.info("   3. Verify confidence reaches >65% threshold")
    logger.info("   4. Deploy: git commit && git push")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()

