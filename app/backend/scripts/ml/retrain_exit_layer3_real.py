#!/usr/bin/env python3
"""
ENTERPRISE-GRADE LAYER 3 REVERSAL MODEL RETRAINING (REAL DATA)
===============================================================

Retrains the Layer 3 Exit Model using REAL historical market data:
- Real RSI, MACD, Bollinger Bands from actual candles
- Real volatility, trend strength, volume ratios
- NO approximations, NO mocks

Target Definition:
- EXIT (1): Positions that resulted in losses (PnL < -0.5%)
- HOLD (0): Positions that resulted in profits or small losses

Features: close, volume, rsi, macd, bb_position, volatility, trend_strength, volume_ratio

Author: TradePulse.AI Team
Date: 2025-10-31
"""

import os
import sys
import json
import pickle
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report, confusion_matrix

# Suppress warnings
warnings.filterwarnings('ignore')

# Add backend to path
current_script_dir = Path(__file__).parent
backend_dir = current_script_dir.parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use standard logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Configuration ---
# backend_dir = /Applications/Projects/TradePulse.AI/app
# So MODEL_PATH should be backend_dir / "backend" / "models" / "enterprise"
MODEL_PATH = backend_dir / "backend" / "models" / "enterprise"
TRAINING_DATA_PATH = backend_dir / "data" / "ml" / "training" / "exit_layer3" / "exit_layer3_training_data.json"

MODEL_FILENAME = "layer_3_reversal.pkl"
SCALER_FILENAME = "layer_3_reversal_scaler.pkl"
METADATA_FILENAME = "layer_3_reversal_metadata.json"

# Features expected by the Layer 3 Reversal model (8 features)
FEATURE_NAMES = [
    "close", "volume", "rsi", "macd", 
    "bb_position", "volatility", "trend_strength", "volume_ratio"
]


def load_training_data() -> pd.DataFrame:
    """Load prepared training data"""
    logger.info(f"📂 Loading training data from {TRAINING_DATA_PATH}...")
    
    with open(TRAINING_DATA_PATH, 'r') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    logger.info(f"✅ Loaded {len(df)} training examples")
    
    return df


def prepare_features_and_target(df: pd.DataFrame) -> tuple:
    """Prepare X (features) and y (target) from dataframe
    
    Target Definition:
    - EXIT (1): PnL < -0.5% (significant loss, should have exited)
    - HOLD (0): PnL >= -0.5% (profit or small loss, holding was OK)
    
    This trains the model to identify conditions that lead to losses.
    """
    logger.info("🔄 Preparing features and target...")
    
    # Extract features
    X = df[FEATURE_NAMES].copy()
    
    # Define target: 1 if should have exited (significant loss), 0 otherwise
    # Use -0.5% threshold for "significant loss"
    y = (df['pnl_percentage'] < -0.5).astype(int)
    
    logger.info(f"✅ Features shape: {X.shape}")
    logger.info(f"   Target distribution:")
    logger.info(f"      EXIT (1 - loss > 0.5%):  {np.sum(y == 1)} ({np.mean(y == 1):.1%})")
    logger.info(f"      HOLD (0 - profit/small): {np.sum(y == 0)} ({np.mean(y == 0):.1%})")
    
    # Check for NaN values
    if X.isnull().any().any():
        logger.warning("⚠️ Found NaN values in features, filling with defaults...")
        X = X.fillna({
            'close': df['close'].median(),
            'volume': df['volume'].median(),
            'rsi': 50.0,
            'macd': 0.0,
            'bb_position': 0.5,
            'volatility': 0.02,
            'trend_strength': 0.0,
            'volume_ratio': 1.0
        })
    
    return X, y


def train_model(X: pd.DataFrame, y: pd.Series) -> tuple:
    """Train LightGBM model with proper validation"""
    logger.info("🤖 Training LightGBM model...")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    logger.info(f"   Train set: {len(X_train)} examples")
    logger.info(f"   Test set:  {len(X_test)} examples")
    
    # Scale features (CRITICAL for model performance!)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    logger.info("   ✅ Features scaled (mean=0, std=1)")
    
    # Train LightGBM with enterprise-grade parameters
    model = lgb.LGBMClassifier(
        objective='binary',
        metric='auc',
        boosting_type='gbdt',
        num_leaves=31,
        max_depth=5,
        learning_rate=0.05,
        n_estimators=200,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=0.1,
        random_state=42,
        verbosity=-1,
        force_col_wise=True
    )
    
    logger.info("   Training model...")
    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        eval_metric='auc',
        callbacks=[lgb.early_stopping(stopping_rounds=20, verbose=False)]
    )
    
    # Evaluate on test set
    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    accuracy = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_pred_proba)
    
    logger.info("   " + "=" * 60)
    logger.info("   📊 MODEL PERFORMANCE")
    logger.info("   " + "=" * 60)
    logger.info(f"   Accuracy: {accuracy:.3f}")
    logger.info(f"   AUC-ROC:  {auc:.3f}")
    logger.info(f"\n   Classification Report:")
    logger.info("\n" + classification_report(y_test, y_pred, target_names=['HOLD', 'EXIT']))
    logger.info(f"\n   Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    logger.info(f"      Predicted HOLD | Predicted EXIT")
    logger.info(f"   Actual HOLD: {cm[0][0]:4d} | {cm[0][1]:4d}")
    logger.info(f"   Actual EXIT: {cm[1][0]:4d} | {cm[1][1]:4d}")
    logger.info("   " + "=" * 60)
    
    # Feature importances
    feature_importances = pd.DataFrame({
        'feature': FEATURE_NAMES,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    logger.info("\n   🎯 FEATURE IMPORTANCES:")
    for idx, row in feature_importances.iterrows():
        bar = '█' * int(row['importance'] / 10)
        logger.info(f"      {row['feature']:20s} {row['importance']:6.1f} {bar}")
    
    return model, scaler, {
        'accuracy': float(accuracy),
        'auc': float(auc),
        'test_size': len(X_test),
        'train_size': len(X_train)
    }


def save_model_and_metadata(model, scaler, metrics: dict):
    """Save model, scaler, and metadata"""
    logger.info("💾 Saving model, scaler, and metadata...")
    
    # Save model
    model_file = MODEL_PATH / MODEL_FILENAME
    with open(model_file, 'wb') as f:
        pickle.dump(model, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info(f"   ✅ Saved model: {model_file}")
    
    # Save scaler
    scaler_file = MODEL_PATH / SCALER_FILENAME
    with open(scaler_file, 'wb') as f:
        pickle.dump(scaler, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.info(f"   ✅ Saved scaler: {scaler_file}")
    
    # Save metadata
    metadata = {
        'model_name': 'layer_3_reversal',
        'model_type': 'LightGBM',
        'version': '2.0',
        'trained_at': datetime.now(timezone.utc).isoformat(),
        'features': FEATURE_NAMES,
        'num_features': len(FEATURE_NAMES),
        'target_definition': 'EXIT (1) if PnL < -0.5%, HOLD (0) otherwise',
        'data_source': 'Real historical candles from DynamoDB (tradepulse_market_data)',
        'training_examples': metrics['train_size'],
        'test_examples': metrics['test_size'],
        'accuracy': metrics['accuracy'],
        'auc': metrics['auc'],
    }
    
    metadata_file = MODEL_PATH / METADATA_FILENAME
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"   ✅ Saved metadata: {metadata_file}")


def main():
    """Main retraining pipeline"""
    logger.info("=" * 80)
    logger.info("🚀 LAYER 3 REVERSAL MODEL RETRAINING (REAL DATA)")
    logger.info("=" * 80)
    
    # Step 1: Load training data
    df = load_training_data()
    
    # Step 2: Prepare features and target
    X, y = prepare_features_and_target(df)
    
    # Step 3: Train model
    model, scaler, metrics = train_model(X, y)
    
    # Step 4: Save model and metadata
    save_model_and_metadata(model, scaler, metrics)
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ RETRAINING COMPLETED SUCCESSFULLY!")
    logger.info("=" * 80)
    logger.info(f"📦 Output Files:")
    logger.info(f"   Model:    {MODEL_PATH / MODEL_FILENAME}")
    logger.info(f"   Scaler:   {MODEL_PATH / SCALER_FILENAME}")
    logger.info(f"   Metadata: {MODEL_PATH / METADATA_FILENAME}")
    logger.info(f"\n🚀 Next Steps:")
    logger.info(f"   1. Update Exit Engine to load scaler")
    logger.info(f"   2. Test locally: start_backend.sh")
    logger.info(f"   3. Deploy: git commit && git push")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

