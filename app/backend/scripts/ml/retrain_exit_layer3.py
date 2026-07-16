#!/usr/bin/env python3
"""
Retrain Layer 3 Reversal Model for Exit Engine
Uses recent closed positions from DynamoDB production data
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

import boto3
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score
import pickle
import json
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Configuration
DYNAMODB_TABLE = "portfolio_closed_positions"
REGION = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")
MIN_TRADES = 100  # Reduced for testing
OUTPUT_PATH = Path("app/backend/models/enterprise/")

def decimal_to_float(obj):
    """Convert Decimal to float"""
    if isinstance(obj, Decimal):
        return float(obj)
    return obj

def fetch_closed_positions():
    """Fetch recent closed positions from DynamoDB"""
    print("📡 Connecting to DynamoDB...")
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table(DYNAMODB_TABLE)
    
    print(f"📊 Scanning table: {DYNAMODB_TABLE}")
    response = table.scan()
    positions = response['Items']
    
    # Continue scanning if there are more items
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        positions.extend(response['Items'])
        print(f"   ... fetched {len(positions)} positions so far")
    
    print(f"✅ Fetched {len(positions)} closed positions")
    return positions

def calculate_exit_features_from_position(pos):
    """
    Calculate exit features from position data
    
    In production, these would be fetched from market data at exit time.
    For training, we reconstruct approximate values from position metadata.
    """
    try:
        exit_price = decimal_to_float(pos.get('exit_price', 0))
        entry_price = decimal_to_float(pos.get('entry_price', 0))
        
        if exit_price == 0 or entry_price == 0:
            return None
        
        # Price change % during hold
        price_change_pct = (exit_price - entry_price) / entry_price
        
        # Approximate RSI based on price change
        # Large price increase = overbought RSI
        # Large price decrease = oversold RSI
        if price_change_pct > 0.05:
            rsi_approx = 70 + min(price_change_pct * 200, 25)  # 70-95
        elif price_change_pct < -0.05:
            rsi_approx = 30 - min(abs(price_change_pct) * 200, 25)  # 5-30
        else:
            rsi_approx = 50 + price_change_pct * 400  # 30-70
        
        # Approximate MACD based on momentum
        hold_time_minutes = decimal_to_float(pos.get('hold_time_minutes', 60))
        macd_approx = price_change_pct / max(hold_time_minutes / 60, 0.1)  # Velocity
        
        # Bollinger position: 0-1 where 0.5 is middle
        # Higher if price moved up significantly
        bb_position_approx = 0.5 + price_change_pct * 5
        bb_position_approx = max(0.0, min(1.0, bb_position_approx))
        
        # Volatility approximation
        volatility_approx = abs(price_change_pct) / max(hold_time_minutes / 1440, 0.01)  # Daily vol
        volatility_approx = max(0.01, min(0.10, volatility_approx))
        
        # Trend strength: stronger if consistent direction
        trend_strength_approx = min(abs(price_change_pct) * 10, 1.0)
        
        # Volume ratio approximation (default to 1.0 if not available)
        volume_ratio_approx = 1.0
        
        features = {
            'close': exit_price,
            'volume': 1000000,  # Default volume (will be normalized anyway)
            'rsi': rsi_approx,
            'macd': macd_approx,
            'bb_position': bb_position_approx,
            'volatility': volatility_approx,
            'trend_strength': trend_strength_approx,
            'volume_ratio': volume_ratio_approx
        }
        
        return features
        
    except Exception as e:
        print(f"⚠️ Error calculating features: {e}")
        return None

def prepare_training_data(positions):
    """Prepare training data from closed positions"""
    
    print("🔄 Preparing training data...")
    data = []
    skipped = 0
    
    for i, pos in enumerate(positions):
        try:
            # Calculate PnL
            pnl_pct = decimal_to_float(pos.get('pnl_percentage', 0))
            
            # Target: Should model have detected exit signal?
            # Good exit: profit > 0.5% (model should say "exit" with high confidence)
            # Bad timing: loss > -1% (model should say "exit" to cut loss)
            # Hold: -1% < PnL < 0.5% (model should say "hold" or low confidence)
            
            if pnl_pct > 0.005:  # Profit > 0.5%
                target = 1  # Model should detect exit signal
            elif pnl_pct < -0.01:  # Loss > -1%
                target = 1  # Model should detect exit signal (cut loss)
            else:
                target = 0  # Hold, unclear
            
            # Calculate features at exit time
            features = calculate_exit_features_from_position(pos)
            
            if features is None:
                skipped += 1
                continue
            
            data.append({
                **features,
                'target': target,
                'pnl_pct': pnl_pct,
                'position_id': pos.get('position_id', 'unknown'),
                'hold_time_minutes': decimal_to_float(pos.get('hold_time_minutes', 0))
            })
            
            if (i + 1) % 100 == 0:
                print(f"   Processed {i+1}/{len(positions)} positions...")
            
        except Exception as e:
            skipped += 1
            continue
    
    df = pd.DataFrame(data)
    print(f"✅ Prepared {len(df)} training examples (skipped {skipped})")
    print(f"   Exit signals (target=1): {(df['target'] == 1).sum()} ({(df['target'] == 1).sum()/len(df)*100:.1f}%)")
    print(f"   Hold signals (target=0): {(df['target'] == 0).sum()} ({(df['target'] == 0).sum()/len(df)*100:.1f}%)")
    print(f"   Avg PnL: {df['pnl_pct'].mean()*100:.2f}%")
    print(f"   Avg hold time: {df['hold_time_minutes'].mean():.1f} minutes")
    
    return df

def train_reversal_model(df):
    """Train LightGBM reversal detection model"""
    
    print("\n🤖 Training LightGBM classifier...")
    
    # Feature columns (in specific order!)
    feature_cols = [
        'close', 'volume', 'rsi', 'macd',
        'bb_position', 'volatility', 'trend_strength', 'volume_ratio'
    ]
    
    print(f"📊 Features: {feature_cols}")
    
    X = df[feature_cols].values
    y = df['target'].values
    
    print(f"   X shape: {X.shape}")
    print(f"   y shape: {y.shape}")
    print(f"   y distribution: {np.bincount(y)}")
    
    # Normalize features (CRITICAL!)
    print("🔧 Fitting StandardScaler...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    print(f"   Scaled mean: {X_scaled.mean(axis=0)}")
    print(f"   Scaled std: {X_scaled.std(axis=0)}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"   Train size: {len(X_train)}")
    print(f"   Test size: {len(X_test)}")
    
    # Train model
    model = LGBMClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.05,
        num_leaves=31,
        random_state=42,
        verbose=-1  # Suppress training output
    )
    
    print("🔄 Training model...")
    model.fit(X_train, y_train)
    
    # Evaluate
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    
    # Get predictions for detailed metrics
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    print(f"\n✅ Model trained!")
    print(f"   Train accuracy: {train_score:.1%}")
    print(f"   Test accuracy: {test_score:.1%}")
    
    try:
        auc = roc_auc_score(y_test, y_pred_proba)
        print(f"   Test AUC: {auc:.3f}")
    except:
        print(f"   Test AUC: N/A")
    
    print("\n📊 Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['Hold', 'Exit']))
    
    # Feature importances
    print("\n📈 Feature Importances:")
    importances = model.feature_importances_
    for feat, imp in sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True):
        print(f"   {feat:20s}: {imp:.3f} {'█' * int(imp * 50)}")
    
    # Test prediction distribution
    print("\n🧪 Prediction Distribution:")
    proba_bins = [0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
    proba_counts, _ = np.histogram(y_pred_proba, bins=proba_bins)
    for i in range(len(proba_bins) - 1):
        pct = proba_counts[i] / len(y_pred_proba) * 100
        print(f"   {proba_bins[i]:.1f}-{proba_bins[i+1]:.1f}: {proba_counts[i]:4d} ({pct:5.1f}%)")
    
    return model, scaler, feature_cols

def save_model_with_metadata(model, scaler, feature_cols):
    """Save model, scaler, and metadata"""
    
    print("\n💾 Saving model, scaler, and metadata...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save new model
    model_path = OUTPUT_PATH / "layer_3_reversal.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"   ✅ Saved model to {model_path}")
    
    # Save scaler
    scaler_path = OUTPUT_PATH / "layer_3_reversal_scaler.pkl"
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    print(f"   ✅ Saved scaler to {scaler_path}")
    
    # Save metadata
    metadata = {
        'version': '2.0',
        'trained_at': datetime.now().isoformat(),
        'feature_count': len(feature_cols),
        'feature_names': feature_cols,
        'model_type': 'LGBMClassifier',
        'scaler': 'StandardScaler',
        'hyperparameters': {
            'n_estimators': 100,
            'max_depth': 5,
            'learning_rate': 0.05,
            'num_leaves': 31
        },
        'notes': f'Retrained with live trade data from production. Timestamp: {timestamp}'
    }
    
    metadata_path = OUTPUT_PATH / "layer_3_reversal_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"   ✅ Saved metadata to {metadata_path}")

def test_model_predictions(model, scaler):
    """Test model with sample data to ensure it works"""
    
    print("\n🧪 Testing model with sample data...")
    
    # Test case 1: Normal market conditions
    test_case_1 = np.array([[
        109000,  # close
        1000000,  # volume  
        50,  # rsi (neutral)
        0.0,  # macd (neutral)
        0.5,  # bb_position (middle)
        0.02,  # volatility (normal)
        0.5,  # trend_strength (neutral)
        1.0   # volume_ratio (normal)
    ]], dtype=np.float32)
    
    # Test case 2: Overbought conditions (should signal exit)
    test_case_2 = np.array([[
        110000,  # close (higher)
        1500000,  # volume (higher)
        85,  # rsi (overbought)
        -0.05,  # macd (bearish)
        0.95,  # bb_position (near upper band)
        0.04,  # volatility (elevated)
        0.8,  # trend_strength (strong)
        2.0   # volume_ratio (high)
    ]], dtype=np.float32)
    
    # Test case 3: Oversold conditions (should not signal exit)
    test_case_3 = np.array([[
        108000,  # close (lower)
        800000,  # volume (lower)
        25,  # rsi (oversold)
        0.02,  # macd (bullish)
        0.15,  # bb_position (near lower band)
        0.03,  # volatility (normal)
        0.3,  # trend_strength (weak)
        0.8   # volume_ratio (low)
    ]], dtype=np.float32)
    
    test_cases = [
        ("Normal market", test_case_1),
        ("Overbought (should exit)", test_case_2),
        ("Oversold (should hold)", test_case_3)
    ]
    
    for name, test_data in test_cases:
        # Scale
        test_scaled = scaler.transform(test_data)
        
        # Predict
        pred_class = model.predict(test_scaled)[0]
        pred_proba = model.predict_proba(test_scaled)[0]
        
        print(f"\n   {name}:")
        print(f"      Class: {'EXIT' if pred_class == 1 else 'HOLD'}")
        print(f"      Probability (exit): {pred_proba[1]:.3f}")
        print(f"      Probability (hold): {pred_proba[0]:.3f}")
        
        # Sanity check
        if pred_proba[1] == 0.000:
            print(f"      ⚠️ WARNING: Model returns 0.000 probability!")

def main():
    print("=" * 70)
    print("🚀 LAYER 3 REVERSAL MODEL RETRAINING")
    print("=" * 70)
    
    # Check AWS credentials
    if not os.getenv("AWS_ACCESS_KEY_ID"):
        print("❌ AWS_ACCESS_KEY_ID not set!")
        print("   Run: export AWS_ACCESS_KEY_ID=...")
        return 1
    
    try:
        # Step 1: Fetch data
        print("\n📡 Step 1: Fetching closed positions from DynamoDB...")
        positions = fetch_closed_positions()
        
        if len(positions) < MIN_TRADES:
            print(f"❌ Not enough trades: {len(positions)} < {MIN_TRADES}")
            return 1
        
        # Step 2: Prepare training data
        print("\n🔄 Step 2: Preparing training data...")
        df = prepare_training_data(positions)
        
        if len(df) < MIN_TRADES:
            print(f"❌ Not enough valid examples: {len(df)} < {MIN_TRADES}")
            return 1
        
        # Step 3: Train model
        print("\n🤖 Step 3: Training model...")
        model, scaler, feature_cols = train_reversal_model(df)
        
        # Step 4: Test model
        print("\n🧪 Step 4: Testing model...")
        test_model_predictions(model, scaler)
        
        # Step 5: Save model
        print("\n💾 Step 5: Saving model and metadata...")
        save_model_with_metadata(model, scaler, feature_cols)
        
        print("\n" + "=" * 70)
        print("✅ RETRAINING COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print(f"\n📦 Output Files:")
        print(f"   Model:    {OUTPUT_PATH}/layer_3_reversal.pkl")
        print(f"   Scaler:   {OUTPUT_PATH}/layer_3_reversal_scaler.pkl")
        print(f"   Metadata: {OUTPUT_PATH}/layer_3_reversal_metadata.json")
        print(f"\n🚀 Next Steps:")
        print(f"   1. Validate: python app/backend/scripts/validate_exit_models.py")
        print(f"   2. Test locally: start_backend.sh")
        print(f"   3. Deploy: git add app/backend/models/ && git commit && git push")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

