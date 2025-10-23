#!/usr/bin/env python3
"""
EMERGENCY FIX: Layer 5 Inverse Retraining
Problem: Model learned backwards (high confidence = loss)
Solution: Train with PnL as ground truth, ignore historical ai_confidence
"""

import os
import sys
from pathlib import Path
import numpy as np
from datetime import datetime, timezone
import structlog
import joblib
from xgboost import XGBRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import boto3
import csv

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Load AWS credentials from CSV
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
MODEL_PATH.mkdir(exist_ok=True, parents=True)
BACKUP_PATH = MODEL_PATH / "backups"
BACKUP_PATH.mkdir(exist_ok=True, parents=True)

# DynamoDB config (LOCAL for testing, AWS for production)
USE_AWS = True  # Set to True to use AWS eu-west-2 data


class InverseLayer5Trainer:
    """
    EMERGENCY INVERSE TRAINING
    Fixes the backwards model by using PnL as ground truth
    """
    
    def __init__(self):
        self.db_client = None
        self.model = None
        self.scaler = StandardScaler()
        
    def initialize(self):
        """Initialize database connection"""
        logger.info("🔧 Initializing Inverse Layer 5 Trainer...")
        
        if USE_AWS:
            logger.info("📡 Using AWS DynamoDB (eu-west-2)")
            # Force AWS credentials usage
            os.environ.pop('DYNAMODB_ENDPOINT', None)  # Remove local endpoint
            os.environ['AWS_REGION'] = 'eu-west-2'
            os.environ['DYNAMODB_REGION'] = 'eu-west-2'
            self.db_client = DynamoDBClient(local_development=False)
        else:
            logger.info("💻 Using Local DynamoDB")
            self.db_client = DynamoDBClient(local_development=True)
        
    def fetch_training_data(self):
        """Fetch closed positions from DynamoDB"""
        logger.info("📦 Fetching training data from portfolio_closed_positions...")
        
        try:
            # Scan portfolio_closed_positions table
            items = self.db_client.scan_table('portfolio_closed_positions')
            
            logger.info(f"✅ Found {len(items)} closed positions")
            
            # Filter for valid data
            valid_items = []
            for item in items:
                # Must have PnL and market features
                if 'realized_pnl' in item and 'entry_price' in item and 'exit_price' in item:
                    valid_items.append(item)
            
            logger.info(f"✅ {len(valid_items)} positions with valid data")
            
            return valid_items
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch training data: {e}")
            return []
    
    def prepare_features_and_targets(self, positions):
        """
        INVERSE LOGIC: Use PnL outcome as target, ignore ai_confidence
        
        Target Engineering:
        - Winning trade (PnL > 0) → HIGH confidence target (0.75 - 0.90)
        - Losing trade (PnL < 0) → LOW confidence target (0.20 - 0.40)
        - Break-even (PnL ≈ 0) → MEDIUM confidence target (0.45 - 0.55)
        """
        logger.info("🔧 Preparing features with INVERSE LOGIC...")
        
        features = []
        targets = []
        
        winning_count = 0
        losing_count = 0
        breakeven_count = 0
        
        for pos in positions:
            try:
                # Extract market features
                entry_price = float(pos.get('entry_price', 0))
                exit_price = float(pos.get('exit_price', 0))
                size = float(pos.get('size', 0))
                realized_pnl = float(pos.get('realized_pnl', 0))
                
                if entry_price == 0 or size == 0:
                    continue
                
                # Calculate return percentage
                return_pct = ((exit_price - entry_price) / entry_price) * 100
                
                # Build feature vector (7 features for Layer 5)
                # Use price/volume/technical data, NOT ai_confidence!
                feature_vector = [
                    entry_price,  # Entry price level
                    exit_price / entry_price if entry_price > 0 else 1.0,  # Price ratio
                    size,  # Position size
                    abs(return_pct),  # Absolute return magnitude
                    1.0 if return_pct > 0 else 0.0,  # Win/loss indicator
                    float(pos.get('duration_minutes', 5.0)),  # Duration
                    abs(realized_pnl) if realized_pnl != 0 else 0.01,  # PnL magnitude
                ]
                
                # INVERSE TARGET ENGINEERING (THIS IS THE FIX!)
                # Based ONLY on PnL outcome, not historical confidence
                if realized_pnl > 1.0:  # Significant win
                    # Map to HIGH confidence (0.75-0.90)
                    # Better wins → higher target
                    target_confidence = min(0.90, 0.75 + (realized_pnl / 100.0))
                    winning_count += 1
                    
                elif realized_pnl < -1.0:  # Significant loss
                    # Map to LOW confidence (0.20-0.40)
                    # Worse losses → lower target
                    target_confidence = max(0.20, 0.40 - (abs(realized_pnl) / 100.0))
                    losing_count += 1
                    
                else:  # Break-even or tiny PnL
                    # Map to MEDIUM confidence (0.45-0.55)
                    target_confidence = 0.50
                    breakeven_count += 1
                
                features.append(feature_vector)
                targets.append(target_confidence)
                
            except Exception as e:
                logger.warning(f"⚠️  Skipping position: {e}")
                continue
        
        X = np.array(features, dtype=np.float32)
        y = np.array(targets, dtype=np.float32)
        
        logger.info(f"✅ Prepared {X.shape[0]} samples:")
        logger.info(f"   🟢 Winning trades: {winning_count} (target: HIGH confidence 0.75-0.90)")
        logger.info(f"   🔴 Losing trades: {losing_count} (target: LOW confidence 0.20-0.40)")
        logger.info(f"   ⚪ Break-even: {breakeven_count} (target: MEDIUM confidence 0.50)")
        logger.info(f"   📊 Target distribution: mean={y.mean():.3f}, std={y.std():.3f}")
        
        return X, y
    
    def train_model(self, X, y):
        """Train XGBoost model with inverse labels"""
        logger.info("🤖 Training XGBoost model with INVERSE logic...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=True
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train XGBoost with optimized hyperparameters
        self.model = XGBRegressor(
            objective='reg:squarederror',
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            gamma=0.1,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1
        )
        
        logger.info("   Training...")
        self.model.fit(
            X_train_scaled, y_train,
            eval_set=[(X_test_scaled, y_test)],
            verbose=False
        )
        
        # Evaluate
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)
        
        # Predictions
        train_pred = self.model.predict(X_train_scaled)
        test_pred = self.model.predict(X_test_scaled)
        
        # Calculate correlation (THIS SHOULD BE POSITIVE NOW!)
        train_corr = np.corrcoef(y_train, train_pred)[0, 1]
        test_corr = np.corrcoef(y_test, test_pred)[0, 1]
        
        logger.info(f"")
        logger.info(f"📊 TRAINING RESULTS:")
        logger.info(f"   Train R²: {train_score:.4f}")
        logger.info(f"   Test R²: {test_score:.4f}")
        logger.info(f"   Train Correlation: {train_corr:.4f}")
        logger.info(f"   Test Correlation: {test_corr:.4f}")
        
        if test_corr > 0.5 and test_score > 0.3:
            logger.info(f"   ✅ Model quality: GOOD (correlation > 0.5, R² > 0.3)")
            return True
        elif test_corr > 0.3:
            logger.warning(f"   ⚠️  Model quality: ACCEPTABLE (correlation > 0.3)")
            return True
        else:
            logger.error(f"   ❌ Model quality: POOR (correlation < 0.3)")
            return False
    
    def save_model(self):
        """Save trained model and scaler"""
        logger.info("💾 Saving model...")
        
        # Backup old model
        old_model_path = MODEL_PATH / "layer_5_confidence.pkl"
        if old_model_path.exists():
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_path = BACKUP_PATH / f"layer_5_confidence_BAD_{timestamp}.pkl"
            import shutil
            shutil.copy(old_model_path, backup_path)
            logger.info(f"   📦 Backed up OLD (bad) model to: {backup_path.name}")
        
        # Save new model
        model_path = MODEL_PATH / "layer_5_confidence.pkl"
        joblib.dump(self.model, model_path)
        logger.info(f"   ✅ Saved model: {model_path}")
        
        # Save scaler
        scaler_path = MODEL_PATH / "layer_5_scaler.pkl"
        joblib.dump(self.scaler, scaler_path)
        logger.info(f"   ✅ Saved scaler: {scaler_path}")
        
        # Save metadata
        metadata = {
            "version": "inverse_fix_1.0",
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "training_logic": "INVERSE - PnL outcome as ground truth",
            "note": "Fixed backwards model that learned high confidence = loss"
        }
        
        import json
        metadata_path = MODEL_PATH / "layer_5_inverse_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"   ✅ Saved metadata")


def main():
    """Main training pipeline"""
    logger.info("="*80)
    logger.info("🚨 EMERGENCY: Layer 5 INVERSE Retraining")
    logger.info("="*80)
    
    trainer = InverseLayer5Trainer()
    
    # Initialize
    trainer.initialize()
    
    # Fetch data
    positions = trainer.fetch_training_data()
    if len(positions) < 50:
        logger.error(f"❌ Not enough data: {len(positions)} positions (need >= 50)")
        return False
    
    # Prepare features with INVERSE logic
    X, y = trainer.prepare_features_and_targets(positions)
    if len(X) < 50:
        logger.error(f"❌ Not enough valid samples: {len(X)}")
        return False
    
    # Train
    success = trainer.train_model(X, y)
    if not success:
        logger.error("❌ Training failed - model quality too poor")
        return False
    
    # Save
    trainer.save_model()
    
    logger.info("")
    logger.info("="*80)
    logger.info("✅ INVERSE RETRAINING COMPLETE!")
    logger.info("="*80)
    logger.info("")
    logger.info("🔄 Next steps:")
    logger.info("   1. Restart backend to load new model")
    logger.info("   2. Monitor confidence values (should be 0.5-0.8 now)")
    logger.info("   3. System should start opening positions again")
    logger.info("")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

