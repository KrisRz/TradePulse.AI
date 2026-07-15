#!/usr/bin/env python3
"""
Professional Live-Compatible Model Retrainer for TradePulse.AI
Retrains Layer 4 and Layer 5 models to work with live data features
"""

import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, r2_score
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retrain_live_compatible_models():
    """Retrain Layer 4 and Layer 5 models for live data compatibility"""
    
    # Paths - absolute from current working directory
    data_path = Path("data/ml/historical/processed/BTCUSDT_1m_complete.parquet")
    models_dir = Path("app/backend/models/enterprise")
    
    logger.info(f"Loading training data from: {data_path}")
    
    # Load and prepare data
    df = pd.read_parquet(data_path)
    logger.info(f"Loaded {len(df):,} records")
    
    # Calculate features exactly as live engine does
    logger.info("Calculating features to match live data...")
    
    # Technical indicators (matching enterprise_trading_engine.py exactly)
    df['rsi_calc'] = calculate_rsi(df['close'].values)
    df['macd_calc'], df['macd_signal_calc'] = calculate_macd(df['close'].values)
    df['macd_diff'] = df['macd_calc'] - df['macd_signal_calc']
    df['bb_position_calc'] = calculate_bb_position(df['close'].values)
    df['volatility_calc'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean()
    df['trend_strength_calc'] = calculate_trend_strength(df['close'].values)
    df['volume_ratio_calc'] = df['volume'] / df['volume'].rolling(20).mean()
    
    # Normalize exactly as live engine
    sma20 = df['close'].rolling(20).mean()
    df['close_norm'] = np.clip(df['close'] / sma20, 0.5, 1.5)
    df['volume_scaled'] = np.clip(df['volume_ratio_calc'], 0.1, 3.0)
    
    # Clean data
    df = df.dropna()
    logger.info(f"Clean data: {len(df):,} records")
    
    # Create targets
    # Layer 4: Technical filter score (0-1, based on good trading conditions)
    df['filter_target'] = create_filter_target(df)
    
    # Layer 5: Confidence score (0-1, based on signal strength)
    df['confidence_target'] = create_confidence_target(df)
    
    # Prepare Layer 4 training data
    l4_features = ['bb_position_calc', 'volatility_calc']
    l4_X = df[l4_features].values
    l4_y = df['filter_target'].values
    
    # Prepare Layer 5 training data  
    l5_features = ['close_norm', 'volume_scaled', 'rsi_calc', 'macd_diff', 'bb_position_calc', 'volatility_calc', 'trend_strength_calc']
    l5_X = df[l5_features].values
    l5_y = df['confidence_target'].values
    
    # Train Layer 4 (Technical Filters)
    logger.info("Training Layer 4 (Technical Filters)...")
    l4_X_train, l4_X_test, l4_y_train, l4_y_test = train_test_split(l4_X, l4_y, test_size=0.2, random_state=42)
    
    l4_model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    l4_model.fit(l4_X_train, l4_y_train)
    l4_score = accuracy_score(l4_y_test, l4_model.predict(l4_X_test))
    
    logger.info(f"✅ Layer 4 trained - Accuracy: {l4_score:.4f}")
    
    # Train Layer 5 (Confidence Scoring)
    logger.info("Training Layer 5 (Confidence Scoring)...")
    l5_X_train, l5_X_test, l5_y_train, l5_y_test = train_test_split(l5_X, l5_y, test_size=0.2, random_state=42)
    
    l5_model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    l5_model.fit(l5_X_train, l5_y_train)
    l5_score = r2_score(l5_y_test, l5_model.predict(l5_X_test))
    
    logger.info(f"✅ Layer 5 trained - R2 Score: {l5_score:.4f}")
    
    # Create scalers for the exact features we use
    l4_scaler = StandardScaler()
    l4_scaler.fit(l4_X_train)
    
    l5_scaler = StandardScaler()
    l5_scaler.fit(l5_X_train)
    
    # Save models
    with open(models_dir / "layer_4_filters.pkl", "wb") as f:
        pickle.dump(l4_model, f)
    
    with open(models_dir / "layer_5_confidence.pkl", "wb") as f:
        pickle.dump(l5_model, f)
    
    # Save scalers
    scalers = {'layer_4': l4_scaler, 'layer_5': l5_scaler}
    with open(models_dir / "feature_scalers.pkl", "wb") as f:
        pickle.dump(scalers, f)
    
    logger.info("✅ Live-compatible models and scalers saved")
    
    # Update metadata
    metadata = {
        "training_date": pd.Timestamp.now().isoformat(),
        "layer_4": {
            "model_type": "RandomForestClassifier",
            "features": l4_features,
            "accuracy": float(l4_score),
            "samples_trained": len(l4_X_train)
        },
        "layer_5": {
            "model_type": "RandomForestRegressor", 
            "features": l5_features,
            "r2_score": float(l5_score),
            "samples_trained": len(l5_X_train)
        }
    }
    
    with open(models_dir / "live_compatible_metadata.json", "w") as f:
        import json
        json.dump(metadata, f, indent=2)
    
    logger.info("✅ Metadata updated")
    return True

def create_filter_target(df):
    """Create Layer 4 filter target (good trading conditions)"""
    # Good conditions: moderate volatility, not at BB extremes
    volatility_ok = (df['volatility_calc'] > 0.005) & (df['volatility_calc'] < 0.05)
    bb_ok = (df['bb_position_calc'] > 0.2) & (df['bb_position_calc'] < 0.8)
    volume_ok = df['volume_ratio_calc'] > 0.8
    
    return (volatility_ok & bb_ok & volume_ok).astype(int)

def create_confidence_target(df):
    """Create Layer 5 confidence target (signal strength)"""
    # Confidence based on multiple factors
    rsi_strength = np.where((df['rsi_calc'] > 30) & (df['rsi_calc'] < 70), 0.8, 0.4)
    trend_strength = np.clip(df['trend_strength_calc'], 0.0, 1.0)
    volume_strength = np.clip(df['volume_ratio_calc'] / 2.0, 0.0, 1.0)
    volatility_strength = np.where((df['volatility_calc'] > 0.01) & (df['volatility_calc'] < 0.04), 0.8, 0.4)
    
    confidence = (rsi_strength + trend_strength + volume_strength + volatility_strength) / 4.0
    return np.clip(confidence, 0.0, 1.0)

# Technical indicator functions (matching enterprise engine exactly)
def calculate_rsi(prices, period=14):
    """Calculate RSI exactly as enterprise engine"""
    prices = np.array(prices)
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    rsi_values = []
    for i in range(len(prices)):
        if i < period:
            rsi_values.append(50.0)
        else:
            avg_gain = np.mean(gains[max(0, i-period):i])
            avg_loss = np.mean(losses[max(0, i-period):i])
            if avg_loss == 0:
                rsi_values.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                rsi_values.append(rsi)
    
    return np.array(rsi_values)

def calculate_macd(prices):
    """Calculate MACD exactly as enterprise engine"""
    prices = pd.Series(prices)
    ema_12 = prices.ewm(span=12).mean()
    ema_26 = prices.ewm(span=26).mean()
    macd = ema_12 - ema_26
    macd_signal = macd.ewm(span=9).mean()
    return macd.values, macd_signal.values

def calculate_bb_position(prices):
    """Calculate BB position exactly as enterprise engine"""
    prices = pd.Series(prices)
    sma = prices.rolling(20).mean()
    std = prices.rolling(20).std()
    upper = sma + (2 * std)
    lower = sma - (2 * std)
    bb_pos = (prices - lower) / (upper - lower)
    return bb_pos.fillna(0.5).values

def calculate_trend_strength(prices):
    """Calculate trend strength exactly as enterprise engine"""
    prices = np.array(prices)
    trend_values = []
    
    for i in range(len(prices)):
        if i < 10:
            trend_values.append(0.5)
        else:
            x = np.arange(10)
            y = prices[i-10:i]
            slope = np.polyfit(x, y, 1)[0]
            trend_strength = np.tanh(abs(slope) / np.mean(y) * 100)
            trend_values.append(float(trend_strength))
    
    return np.array(trend_values)

if __name__ == "__main__":
    logger.info("🚀 Retraining models for live data compatibility...")
    success = retrain_live_compatible_models()
    if success:
        logger.info("✅ Live-compatible models created successfully!")
    else:
        logger.error("❌ Model retraining failed!")
