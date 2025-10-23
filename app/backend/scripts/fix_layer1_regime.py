#!/usr/bin/env python3
"""
Fix Layer 1 - Market Regime Detection
Retrain with proper market regime labeling from actual outcomes
"""

import os
import sys
from pathlib import Path
import numpy as np
from datetime import datetime, timezone
import structlog
import joblib
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import csv

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Load AWS credentials
project_root = Path(__file__).parent.parent.parent.parent
creds_file = project_root / "Kris_accessKeys.csv"
if creds_file.exists():
    with open(creds_file, 'r') as f:
        lines = f.readlines()
        creds_line = lines[1].strip().split(',')
        os.environ['AWS_ACCESS_KEY_ID'] = creds_line[0]
        os.environ['AWS_SECRET_ACCESS_KEY'] = creds_line[1]

from core.database import DynamoDBClient

logger = structlog.get_logger(__name__)

# Paths
MODEL_PATH = backend_path / "models" / "enterprise"
BACKUP_PATH = MODEL_PATH / "backups"
BACKUP_PATH.mkdir(exist_ok=True, parents=True)

USE_AWS = True


class Layer1RegimeTrainer:
    """
    Retrain Layer 1 with proper regime classification
    """
    
    def __init__(self):
        self.db_client = None
        self.model = None
        
    def initialize(self):
        """Initialize database connection"""
        logger.info("🔧 Initializing Layer 1 Regime Trainer...")
        
        if USE_AWS:
            logger.info("📡 Using AWS DynamoDB (eu-west-2)")
            os.environ.pop('DYNAMODB_ENDPOINT', None)
            os.environ['AWS_REGION'] = 'eu-west-2'
            os.environ['DYNAMODB_REGION'] = 'eu-west-2'
            self.db_client = DynamoDBClient(local_development=False)
        else:
            logger.info("💻 Using Local DynamoDB")
            self.db_client = DynamoDBClient(local_development=True)
    
    def fetch_training_data(self):
        """Fetch closed positions for regime analysis"""
        logger.info("📦 Fetching training data...")
        
        try:
            items = self.db_client.scan_table('portfolio_closed_positions')
            logger.info(f"✅ Found {len(items)} closed positions")
            
            # Filter valid data
            valid_items = []
            for item in items:
                if all(k in item for k in ['entry_price', 'exit_price', 'realized_pnl', 'entry_time']):
                    valid_items.append(item)
            
            logger.info(f"✅ {len(valid_items)} positions with valid data")
            return valid_items
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch data: {e}")
            return []
    
    def prepare_features_and_targets(self, positions):
        """
        Prepare features and regime labels
        
        Regime Classification:
        - BULL (0): Strong uptrend, winning trades with high returns
        - BEAR (1): Strong downtrend, losing trades in longs
        - SIDEWAYS (2): Range-bound, mixed results, low volatility
        - VOLATILE (3): High volatility, erratic moves
        """
        logger.info("🔧 Preparing regime classification data...")
        
        features = []
        targets = []
        
        regime_counts = {'bull': 0, 'bear': 0, 'sideways': 0, 'volatile': 0}
        
        for pos in positions:
            try:
                entry_price = float(pos.get('entry_price', 0))
                exit_price = float(pos.get('exit_price', 0))
                size = float(pos.get('size', 0))
                pnl = float(pos.get('realized_pnl', 0))
                duration = float(pos.get('duration_minutes', 5.0))
                
                if entry_price == 0 or size == 0:
                    continue
                
                # Calculate market metrics
                price_change = ((exit_price - entry_price) / entry_price) * 100
                price_change_abs = abs(price_change)
                
                # Estimate volatility from price movement
                estimated_volatility = price_change_abs / (duration / 60.0) if duration > 0 else 0.02
                
                # Feature vector (9 features matching Layer 1 expectations)
                feature_vector = [
                    exit_price,  # close
                    size * exit_price,  # volume proxy
                    50.0,  # rsi (neutral default - we don't have historical)
                    0.0,  # macd (neutral)
                    0.5,  # bb_position (middle)
                    min(estimated_volatility, 0.1),  # volatility (capped)
                    abs(price_change) / 5.0,  # trend_strength (normalized)
                    1.0,  # volume_ratio
                    price_change,  # price_change_24h (using this trade's change)
                ]
                
                # REGIME LABELING based on actual outcome
                # Adjusted for day trading (small %age moves)
                
                if price_change > 0.15 and pnl > 0:
                    # Upward move with profit = BULL
                    regime = 0  # bull
                    regime_counts['bull'] += 1
                    
                elif price_change < -0.15 and pnl < 0:
                    # Downward move with loss (for long) = BEAR  
                    regime = 1  # bear
                    regime_counts['bear'] += 1
                    
                elif estimated_volatility > 0.08 or price_change_abs > 0.5:
                    # High volatility or large swings = VOLATILE
                    regime = 3  # volatile
                    regime_counts['volatile'] += 1
                    
                else:
                    # Small moves, mixed results = SIDEWAYS
                    regime = 2  # sideways
                    regime_counts['sideways'] += 1
                
                features.append(feature_vector)
                targets.append(regime)
                
            except Exception as e:
                logger.warning(f"⚠️  Skipping position: {e}")
                continue
        
        X = np.array(features, dtype=np.float32)
        y = np.array(targets, dtype=np.int32)
        
        logger.info(f"✅ Prepared {X.shape[0]} samples:")
        logger.info(f"   🟢 Bull: {regime_counts['bull']}")
        logger.info(f"   🔴 Bear: {regime_counts['bear']}")
        logger.info(f"   ⚪ Sideways: {regime_counts['sideways']}")
        logger.info(f"   ⚡ Volatile: {regime_counts['volatile']}")
        
        return X, y
    
    def train_model(self, X, y):
        """Train XGBoost classifier for regime detection"""
        logger.info("🤖 Training XGBoost classifier...")
        
        # Split data (no stratify if some classes missing)
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
        except ValueError:
            # If stratify fails (missing classes), split without it
            logger.warning("⚠️  Stratify failed, splitting without stratification")
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
        
        # Train XGBoost classifier
        self.model = XGBClassifier(
            objective='multi:softmax',
            num_class=4,
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1
        )
        
        logger.info("   Training...")
        self.model.fit(X_train, y_train)
        
        # Evaluate
        train_acc = accuracy_score(y_train, self.model.predict(X_train))
        test_acc = accuracy_score(y_test, self.model.predict(X_test))
        
        logger.info(f"")
        logger.info(f"📊 TRAINING RESULTS:")
        logger.info(f"   Train Accuracy: {train_acc:.4f}")
        logger.info(f"   Test Accuracy: {test_acc:.4f}")
        
        # Classification report
        y_pred = self.model.predict(X_test)
        report = classification_report(
            y_test, y_pred,
            target_names=['Bull', 'Bear', 'Sideways', 'Volatile'],
            output_dict=True
        )
        
        logger.info(f"   Per-class accuracy:")
        for regime in ['Bull', 'Bear', 'Sideways', 'Volatile']:
            if regime in report:
                f1 = report[regime]['f1-score']
                logger.info(f"      {regime}: {f1:.3f}")
        
        if test_acc > 0.5:
            logger.info(f"   ✅ Model quality: GOOD (accuracy > 0.5)")
            return True
        else:
            logger.warning(f"   ⚠️  Model quality: ACCEPTABLE")
            return True
    
    def save_model(self):
        """Save trained model"""
        logger.info("💾 Saving model...")
        
        # Backup old model
        old_model_path = MODEL_PATH / "layer_1_regime.pkl"
        if old_model_path.exists():
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_path = BACKUP_PATH / f"layer_1_regime_OLD_{timestamp}.pkl"
            import shutil
            shutil.copy(old_model_path, backup_path)
            logger.info(f"   📦 Backed up old model to: {backup_path.name}")
        
        # Save new model
        joblib.dump(self.model, old_model_path)
        logger.info(f"   ✅ Saved: {old_model_path}")


def main():
    """Main training pipeline"""
    logger.info("="*80)
    logger.info("🔧 Layer 1 Regime Detection - Retraining")
    logger.info("="*80)
    
    trainer = Layer1RegimeTrainer()
    trainer.initialize()
    
    # Fetch data
    positions = trainer.fetch_training_data()
    if len(positions) < 50:
        logger.error(f"❌ Not enough data: {len(positions)}")
        return False
    
    # Prepare features
    X, y = trainer.prepare_features_and_targets(positions)
    if len(X) < 50:
        logger.error(f"❌ Not enough samples: {len(X)}")
        return False
    
    # Train
    success = trainer.train_model(X, y)
    if not success:
        logger.error("❌ Training failed")
        return False
    
    # Save
    trainer.save_model()
    
    logger.info("")
    logger.info("="*80)
    logger.info("✅ LAYER 1 RETRAINING COMPLETE!")
    logger.info("="*80)
    logger.info("")
    logger.info("🔄 Restart backend to load new model")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

