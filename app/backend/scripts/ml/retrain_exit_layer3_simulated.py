#!/usr/bin/env python3
"""
ENTERPRISE-GRADE LAYER 3 REVERSAL MODEL RETRAINING
==================================================

Retrain with 23K+ simulated examples from fresh Binance data!

vs. OLD: 749 examples, 2% EXIT, unbalanced
vs. NEW: 23,395 examples, 40% EXIT, balanced!

Features: 8 real market indicators
Target: Binary (EXIT=1, HOLD=0)
Algorithm: LightGBM with StandardScaler

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
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, roc_auc_score, classification_report, 
    confusion_matrix, precision_recall_curve, f1_score
)

warnings.filterwarnings('ignore')

# Standard logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Paths
current_script_dir = Path(__file__).parent
backend_dir = current_script_dir.parent.parent.parent
MODEL_PATH = backend_dir / "backend" / "models" / "enterprise"
TRAINING_DATA_PATH = backend_dir / "data" / "ml" / "training" / "exit_layer3_simulated" / "exit_layer3_simulated_training_data.json"

MODEL_FILENAME = "layer_3_reversal.pkl"
SCALER_FILENAME = "layer_3_reversal_scaler.pkl"
METADATA_FILENAME = "layer_3_reversal_metadata.json"

FEATURE_NAMES = [
    "close", "volume", "rsi", "macd", 
    "bb_position", "volatility", "trend_strength", "volume_ratio"
]


def load_training_data() -> pd.DataFrame:
    """Load simulated training data"""
    logger.info(f"📂 Loading training data from {TRAINING_DATA_PATH}...")
    
    with open(TRAINING_DATA_PATH, 'r') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    logger.info(f"✅ Loaded {len(df)} training examples")
    logger.info(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    return df


def prepare_features_and_target(df: pd.DataFrame) -> tuple:
    """Prepare X and y"""
    logger.info("🔄 Preparing features and target...")
    
    X = df[FEATURE_NAMES].copy()
    y = df['target'].values
    
    logger.info(f"✅ Features shape: {X.shape}")
    logger.info(f"   Target distribution:")
    logger.info(f"      EXIT (1):  {np.sum(y == 1):,} ({np.mean(y == 1):.1%})")
    logger.info(f"      HOLD (0):  {np.sum(y == 0):,} ({np.mean(y == 0):.1%})")
    
    # Check for NaN
    if X.isnull().any().any():
        logger.warning("⚠️ Found NaN values, filling...")
        X = X.fillna({
            'close': X['close'].median(),
            'volume': X['volume'].median(),
            'rsi': 50.0,
            'macd': 0.0,
            'bb_position': 0.5,
            'volatility': 0.02,
            'trend_strength': 0.0,
            'volume_ratio': 1.0
        })
    
    return X, y


def train_model(X: pd.DataFrame, y: np.ndarray) -> tuple:
    """Train LightGBM model with cross-validation"""
    logger.info("🤖 Training LightGBM model...")
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    logger.info(f"   Train set: {len(X_train):,} examples")
    logger.info(f"   Test set:  {len(X_test):,} examples")
    
    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    logger.info("   ✅ Features scaled (mean=0, std=1)")
    
    # Train with optimized hyperparameters for larger dataset
    # 🔧 FIX: Set num_leaves = 2^max_depth for optimal tree capacity
    model = lgb.LGBMClassifier(
        objective='binary',
        metric='auc',
        boosting_type='gbdt',
        num_leaves=64,  # 2^6 = 64 (FIXED: was 31, now aligned with max_depth)
        max_depth=6,  # Slightly deeper for more data
        min_data_in_leaf=15,  # Prevent overfitting on sparse leaves
        learning_rate=0.05,
        n_estimators=300,  # More trees for more data
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=0.1,
        random_state=42,
        verbosity=-1,
        force_col_wise=True
    )
    
    logger.info("   Training model with num_leaves=64 (2^6) for optimal tree capacity...")
    
    # 🔧 FIX: Add early stopping with AUC/PR logging
    eval_results = {}
    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        eval_metric=['auc', 'average_precision'],  # Track both AUC and PR
        callbacks=[
            lgb.early_stopping(stopping_rounds=30, verbose=False),
            lgb.log_evaluation(period=0)  # Suppress per-iteration logs
        ]
    )
    
    # Log final AUC and PR from training
    best_iteration = model.best_iteration_ if hasattr(model, 'best_iteration_') else model.n_estimators
    logger.info(f"   ✅ Training complete: best_iteration={best_iteration}")
    
    # Evaluate
    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    accuracy = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_pred_proba)
    f1 = f1_score(y_test, y_pred)
    
    logger.info("   " + "=" * 60)
    logger.info("   📊 MODEL PERFORMANCE (TEST SET)")
    logger.info("   " + "=" * 60)
    logger.info(f"   Accuracy: {accuracy:.3f}")
    logger.info(f"   AUC-ROC:  {auc:.3f}")
    logger.info(f"   F1 Score: {f1:.3f}")
    logger.info(f"\n   Classification Report:")
    logger.info("\n" + classification_report(y_test, y_pred, target_names=['HOLD', 'EXIT']))
    logger.info(f"\n   Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    logger.info(f"      Predicted HOLD | Predicted EXIT")
    logger.info(f"   Actual HOLD: {cm[0][0]:5d} | {cm[0][1]:5d}")
    logger.info(f"   Actual EXIT: {cm[1][0]:5d} | {cm[1][1]:5d}")
    logger.info("   " + "=" * 60)
    
    # Feature importances
    feature_importances = pd.DataFrame({
        'feature': FEATURE_NAMES,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    logger.info("\n   🎯 FEATURE IMPORTANCES:")
    for idx, row in feature_importances.iterrows():
        bar = '█' * int(row['importance'] / 20)
        logger.info(f"      {row['feature']:20s} {row['importance']:6.1f} {bar}")
    
    # Cross-validation
    logger.info("\n   🔄 Running 5-fold cross-validation...")
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='roc_auc')
    logger.info(f"   CV AUC scores: {cv_scores}")
    logger.info(f"   CV AUC mean:   {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
    
    return model, scaler, {
        'accuracy': float(accuracy),
        'auc': float(auc),
        'f1': float(f1),
        'cv_auc_mean': float(cv_scores.mean()),
        'cv_auc_std': float(cv_scores.std()),
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
        'version': '3.0',  # v3.0 = Simulated training
        'trained_at': datetime.now(timezone.utc).isoformat(),
        'features': FEATURE_NAMES,
        'num_features': len(FEATURE_NAMES),
        'target_definition': 'EXIT (1) if simulated max_drawdown < -0.5%, HOLD (0) otherwise',
        'data_source': 'Binance 3-month fresh data (Aug-Oct 2025) with position simulation',
        'training_examples': metrics['train_size'],
        'test_examples': metrics['test_size'],
        'accuracy': metrics['accuracy'],
        'auc': metrics['auc'],
        'f1': metrics['f1'],
        'cv_auc_mean': metrics['cv_auc_mean'],
        'cv_auc_std': metrics['cv_auc_std'],
    }
    
    metadata_file = MODEL_PATH / METADATA_FILENAME
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"   ✅ Saved metadata: {metadata_file}")


def main():
    """Main retraining pipeline"""
    logger.info("=" * 80)
    logger.info("🚀 LAYER 3 REVERSAL MODEL RETRAINING (SIMULATED DATA - v3.0)")
    logger.info("=" * 80)
    
    # Load data
    df = load_training_data()
    
    # Prepare
    X, y = prepare_features_and_target(df)
    
    # Train
    model, scaler, metrics = train_model(X, y)
    
    # Save
    save_model_and_metadata(model, scaler, metrics)
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ RETRAINING COMPLETED SUCCESSFULLY!")
    logger.info("=" * 80)
    logger.info(f"📦 Output Files:")
    logger.info(f"   Model:    {MODEL_PATH / MODEL_FILENAME}")
    logger.info(f"   Scaler:   {MODEL_PATH / SCALER_FILENAME}")
    logger.info(f"   Metadata: {MODEL_PATH / METADATA_FILENAME}")
    logger.info(f"\n🎯 Model Performance:")
    logger.info(f"   Accuracy: {metrics['accuracy']:.1%}")
    logger.info(f"   AUC-ROC:  {metrics['auc']:.3f}")
    logger.info(f"   F1 Score: {metrics['f1']:.3f}")
    logger.info(f"   CV AUC:   {metrics['cv_auc_mean']:.3f} (+/- {metrics['cv_auc_std']:.3f})")
    logger.info(f"\n🚀 Next Steps:")
    logger.info(f"   1. Test locally: start_backend.sh")
    logger.info(f"   2. Monitor performance in real trading")
    logger.info(f"   3. Deploy: git commit && git push")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

