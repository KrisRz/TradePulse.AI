#!/usr/bin/env python3
"""
Re-export XGBoost models to new format
Fixes legacy model format warnings
"""

import pickle
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def reexport_xgboost_model(model_path: Path):
    """Re-export a single XGBoost model to new format"""
    print(f"Processing: {model_path.name}")
    
    try:
        # Load legacy model
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        
        # Check if it's an XGBoost model
        if not hasattr(model, 'save_model'):
            print(f"  ⚠️  Not an XGBoost model, skipping")
            return False
        
        # Create backup
        backup_path = model_path.with_suffix('.pkl.backup')
        if not backup_path.exists():
            print(f"  📦 Creating backup: {backup_path.name}")
            os.rename(model_path, backup_path)
        else:
            print(f"  ✅ Backup already exists: {backup_path.name}")
        
        # Save in new format (JSON)
        new_model_path = model_path.with_suffix('.json')
        print(f"  💾 Saving to new format: {new_model_path.name}")
        model.save_model(new_model_path)
        
        # Save as pickle again (with updated serialization)
        print(f"  💾 Saving updated pickle: {model_path.name}")
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        print(f"  ✅ Successfully re-exported {model_path.name}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    print("=" * 80)
    print("🔧 RE-EXPORTING XGBOOST MODELS TO NEW FORMAT")
    print("=" * 80)
    print()
    
    # Models directory
    models_dir = project_root / "app" / "backend" / "models" / "enterprise"
    
    if not models_dir.exists():
        print(f"❌ Models directory not found: {models_dir}")
        sys.exit(1)
    
    print(f"📂 Models directory: {models_dir}")
    print()
    
    # Find all XGBoost models
    xgboost_models = [
        "layer_1_regime.pkl",
        "layer_3_reversal.pkl",
        "layer_4_filters.pkl",
        "layer_5_confidence.pkl",
        "layer_6_timing.pkl"
    ]
    
    success_count = 0
    total_count = 0
    
    for model_name in xgboost_models:
        model_path = models_dir / model_name
        
        if not model_path.exists():
            print(f"⚠️  Model not found: {model_name}")
            continue
        
        total_count += 1
        if reexport_xgboost_model(model_path):
            success_count += 1
        print()
    
    print("=" * 80)
    print(f"📊 SUMMARY")
    print("=" * 80)
    print(f"Total models: {total_count}")
    print(f"✅ Successfully re-exported: {success_count}")
    print(f"❌ Failed: {total_count - success_count}")
    print()
    
    if success_count == total_count:
        print("🎉 All models re-exported successfully!")
        print("✅ Legacy format warnings should be gone")
    else:
        print("⚠️  Some models failed to re-export")
        print("   Check the errors above")
    
    print("=" * 80)

if __name__ == "__main__":
    main()

