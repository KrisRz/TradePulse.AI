#!/usr/bin/env python3
"""
Professional Feature Scaler Generator for TradePulse.AI
Creates StandardScaler objects for each layer based on training data distribution
"""

import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from sklearn.preprocessing import StandardScaler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_professional_scalers():
    """Create professional feature scalers for each layer"""
    
    # Paths - absolute from current working directory
    data_path = Path("data/ml/historical/processed/BTCUSDT_1m_complete.parquet")
    models_dir = Path("app/backend/models/enterprise")
    
    logger.info(f"Loading training data from: {data_path}")
    
    # Load training data
    df = pd.read_parquet(data_path)
    logger.info(f"Loaded {len(df):,} records")
    
    # Calculate the same features as enterprise engine
    logger.info("Calculating features...")
    
    # Technical indicators (matching enterprise_trading_engine.py)
    df['rsi'] = calculate_rsi(df['close'].values)
    df['macd'], df['macd_signal'] = calculate_macd(df['close'].values)
    df['macd'] = df['macd'] - df['macd_signal']  # MACD difference
    df['bb_position'] = calculate_bb_position(df['close'].values)
    df['volatility'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean()
    df['trend_strength'] = calculate_trend_strength(df['close'].values)
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
    
    # Normalize features (matching live data normalization)
    sma20 = df['close'].rolling(20).mean()
    df['close_norm'] = np.clip(df['close'] / sma20, 0.5, 1.5)
    df['volume_scaled'] = np.clip(df['volume_ratio'], 0.1, 3.0)
    
    # Clean data
    df = df.dropna()
    logger.info(f"Clean data: {len(df):,} records")
    
    # Create scalers for each layer
    scalers = {}
    
    # Layer 4: Technical Filters (bb_position, volatility)
    layer_4_features = ['bb_position', 'volatility']
    layer_4_data = df[layer_4_features].values
    scalers['layer_4'] = StandardScaler()
    scalers['layer_4'].fit(layer_4_data)
    logger.info(f"✅ Layer 4 scaler created - features: {layer_4_features}")
    
    # Layer 5: Confidence Scoring (6 features - matching live data exactly)
    layer_5_features = ['close', 'volume', 'rsi', 'macd', 'bb_position', 'volatility']
    layer_5_data = df[layer_5_features].values
    scalers['layer_5'] = StandardScaler()
    scalers['layer_5'].fit(layer_5_data)
    logger.info(f"✅ Layer 5 scaler created - features: {layer_5_features}")
    
    # Save scalers
    scaler_path = models_dir / "feature_scalers.pkl"
    with open(scaler_path, "wb") as f:
        pickle.dump(scalers, f)
    
    logger.info(f"✅ Professional scalers saved to: {scaler_path}")
    
    # Log scaler statistics
    for layer, scaler in scalers.items():
        logger.info(f"📊 {layer} scaler - mean: {scaler.mean_}, scale: {scaler.scale_}")
    
    return scalers

def calculate_rsi(prices, period=14):
    """Calculate RSI (matching enterprise engine)"""
    prices = np.array(prices)
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    rsi_values = []
    for i in range(len(prices)):
        if i < period:
            rsi_values.append(50.0)
        else:
            avg_gain = np.mean(gains[i-period:i])
            avg_loss = np.mean(losses[i-period:i])
            if avg_loss == 0:
                rsi_values.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                rsi_values.append(rsi)
    
    return np.array(rsi_values)

def calculate_macd(prices):
    """Calculate MACD (matching enterprise engine)"""
    prices = np.array(prices)
    ema_12 = pd.Series(prices).ewm(span=12).mean().values
    ema_26 = pd.Series(prices).ewm(span=26).mean().values
    macd = ema_12 - ema_26
    macd_signal = pd.Series(macd).ewm(span=9).mean().values
    return macd, macd_signal

def calculate_bb_position(prices):
    """Calculate Bollinger Band position (matching enterprise engine)"""
    prices = pd.Series(prices)
    sma = prices.rolling(20).mean()
    std = prices.rolling(20).std()
    upper = sma + (2 * std)
    lower = sma - (2 * std)
    bb_pos = (prices - lower) / (upper - lower)
    return bb_pos.fillna(0.5).values

def calculate_trend_strength(prices):
    """Calculate trend strength (matching enterprise engine)"""
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
            trend_values.append(trend_strength)
    
    return np.array(trend_values)

if __name__ == "__main__":
    logger.info("🚀 Generating professional feature scalers...")
    scalers = create_professional_scalers()
    logger.info("✅ Professional scalers generated successfully!")
