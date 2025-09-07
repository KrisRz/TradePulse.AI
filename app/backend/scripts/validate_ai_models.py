#!/usr/bin/env python3
"""
Professional AI Model Validation Script for TradePulse.AI
=========================================================

Validates all AI models are loading correctly and producing valid outputs.
This is a critical pre-deployment check for professional trading systems.

Author: TradePulse.AI Development Team
Created: August 2025
Version: 1.0.0
"""

import sys
import os
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIModelValidator:
    """Professional AI Model Validation System"""
    
    def __init__(self):
        self.model_path = Path(__file__).parent.parent / "models" / "enterprise"
        self.validation_results = {}
        self.critical_errors = []
        self.warnings = []
        
    def validate_all_models(self) -> Dict[str, Any]:
        """Validate all AI models and return comprehensive report"""
        logger.info("🔍 Starting comprehensive AI model validation...")
        
        # Model files to validate
        model_files = {
            "Layer 1 - Market Regime": "layer_1_regime.pkl",
            "Layer 2 - LSTM 1h": "lstm_1h.h5", 
            "Layer 2 - LSTM 4h": "lstm_4h.h5",
            "Layer 2 - LSTM 24h": "lstm_24h.h5",
            "Layer 3 - Reversal Detection": "layer_3_reversal.pkl",
            "Layer 4 - Technical Filters": "layer_4_filters.pkl",
            "Layer 5 - Confidence Scoring": "layer_5_confidence.pkl",
            "Layer 6 - Adaptive Timing": "layer_6_timing.pkl",
            "Feature Scalers": "feature_scalers.pkl"
        }
        
        # Validate each model
        for model_name, filename in model_files.items():
            try:
                result = self._validate_single_model(model_name, filename)
                self.validation_results[model_name] = result
                
                if result["status"] == "CRITICAL_ERROR":
                    self.critical_errors.append(f"{model_name}: {result['error']}")
                elif result["status"] == "WARNING":
                    self.warnings.append(f"{model_name}: {result['message']}")
                    
            except Exception as e:
                error_msg = f"Validation failed for {model_name}: {e}"
                self.critical_errors.append(error_msg)
                self.validation_results[model_name] = {
                    "status": "CRITICAL_ERROR",
                    "error": str(e)
                }
        
        # Test enterprise trading engine integration
        try:
            self._validate_enterprise_integration()
        except Exception as e:
            self.critical_errors.append(f"Enterprise integration failed: {e}")
        
        return self._generate_report()
    
    def _validate_single_model(self, model_name: str, filename: str) -> Dict[str, Any]:
        """Validate a single AI model"""
        model_file = self.model_path / filename
        
        # Check file existence
        if not model_file.exists():
            return {
                "status": "CRITICAL_ERROR",
                "error": f"Model file not found: {model_file}",
                "file_exists": False
            }
        
        # Check file size
        file_size = model_file.stat().st_size
        if file_size < 1024:  # Less than 1KB is suspicious
            return {
                "status": "WARNING",
                "message": f"Model file suspiciously small: {file_size} bytes",
                "file_exists": True,
                "file_size": file_size
            }
        
        # Load and validate model
        try:
            if filename.endswith('.pkl'):
                return self._validate_pickle_model(model_name, model_file)
            elif filename.endswith('.h5'):
                return self._validate_tensorflow_model(model_name, model_file)
            else:
                return {
                    "status": "WARNING",
                    "message": f"Unknown model format: {filename}",
                    "file_exists": True,
                    "file_size": file_size
                }
                
        except Exception as e:
            return {
                "status": "CRITICAL_ERROR",
                "error": f"Failed to load model: {e}",
                "file_exists": True,
                "file_size": file_size
            }
    
    def _validate_pickle_model(self, model_name: str, model_file: Path) -> Dict[str, Any]:
        """Validate a pickle-based scikit-learn model"""
        with open(model_file, 'rb') as f:
            model = pickle.load(f)
        
        result = {
            "status": "HEALTHY",
            "file_exists": True,
            "file_size": model_file.stat().st_size,
            "model_type": type(model).__name__,
            "model_module": type(model).__module__
        }
        
        # Check if it's a scikit-learn model
        if hasattr(model, 'predict'):
            result["has_predict"] = True
            
            # Check expected features
            if hasattr(model, 'n_features_in_'):
                result["expected_features"] = model.n_features_in_
                
                # Test prediction with dummy data
                try:
                    dummy_features = np.random.random((1, model.n_features_in_))
                    prediction = model.predict(dummy_features)
                    result["test_prediction"] = float(prediction[0]) if len(prediction) > 0 else None
                    result["prediction_test"] = "PASSED"
                    
                    # For classification models, test predict_proba
                    if hasattr(model, 'predict_proba'):
                        proba = model.predict_proba(dummy_features)
                        result["has_predict_proba"] = True
                        result["test_probabilities"] = proba[0].tolist() if len(proba) > 0 else None
                        
                except Exception as e:
                    result["status"] = "WARNING"
                    result["prediction_test"] = f"FAILED: {e}"
            else:
                result["status"] = "WARNING"
                result["message"] = "Model missing n_features_in_ attribute"
        else:
            result["status"] = "CRITICAL_ERROR"
            result["error"] = "Model missing predict method"
        
        return result
    
    def _validate_tensorflow_model(self, model_name: str, model_file: Path) -> Dict[str, Any]:
        """Validate a TensorFlow/Keras model"""
        try:
            import tensorflow as tf
            
            # Load model
            model = tf.keras.models.load_model(model_file, compile=False)
            
            result = {
                "status": "HEALTHY",
                "file_exists": True,
                "file_size": model_file.stat().st_size,
                "model_type": "TensorFlow/Keras",
                "input_shape": str(model.input_shape) if hasattr(model, 'input_shape') else None,
                "output_shape": str(model.output_shape) if hasattr(model, 'output_shape') else None,
                "layers_count": len(model.layers) if hasattr(model, 'layers') else None
            }
            
            # Test prediction with dummy data
            try:
                if hasattr(model, 'input_shape') and model.input_shape:
                    # Create dummy input matching the expected shape
                    input_shape = model.input_shape
                    if input_shape[0] is None:  # Batch dimension
                        test_shape = (1,) + input_shape[1:]
                    else:
                        test_shape = input_shape
                    
                    dummy_input = np.random.random(test_shape)
                    prediction = model.predict(dummy_input, verbose=0)
                    result["test_prediction_shape"] = str(prediction.shape)
                    result["test_prediction_sample"] = float(prediction.flatten()[0]) if prediction.size > 0 else None
                    result["prediction_test"] = "PASSED"
                    
            except Exception as e:
                result["status"] = "WARNING"
                result["prediction_test"] = f"FAILED: {e}"
            
            return result
            
        except ImportError:
            return {
                "status": "CRITICAL_ERROR",
                "error": "TensorFlow not available for .h5 model validation",
                "file_exists": True,
                "file_size": model_file.stat().st_size
            }
    
    def _validate_enterprise_integration(self):
        """Test enterprise trading engine integration"""
        logger.info("🧠 Testing Enterprise Trading Engine integration...")
        
        # This will test if all models load correctly in the actual engine
        engine = EnterpriseTradingEngine()
        
        # The engine initialization will fail if models are not properly loaded
        # This is exactly what we want - fail fast for professional deployment
        
        self.validation_results["Enterprise Integration"] = {
            "status": "HEALTHY",
            "message": "Enterprise Trading Engine initialized successfully",
            "models_loaded": len(engine.models),
            "model_names": list(engine.models.keys())
        }
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        total_models = len(self.validation_results)
        healthy_models = sum(1 for r in self.validation_results.values() if r.get("status") == "HEALTHY")
        warning_models = sum(1 for r in self.validation_results.values() if r.get("status") == "WARNING")
        critical_models = sum(1 for r in self.validation_results.values() if r.get("status") == "CRITICAL_ERROR")
        
        overall_status = "HEALTHY"
        if critical_models > 0:
            overall_status = "CRITICAL_ERROR"
        elif warning_models > 0:
            overall_status = "WARNING"
        
        report = {
            "overall_status": overall_status,
            "summary": {
                "total_models": total_models,
                "healthy_models": healthy_models,
                "warning_models": warning_models,
                "critical_models": critical_models,
                "success_rate": f"{(healthy_models/total_models)*100:.1f}%" if total_models > 0 else "0%"
            },
            "critical_errors": self.critical_errors,
            "warnings": self.warnings,
            "detailed_results": self.validation_results,
            "deployment_ready": len(self.critical_errors) == 0,
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        if self.critical_errors:
            recommendations.append("🚨 CRITICAL: Fix all critical errors before deployment")
            recommendations.append("🔧 Run model retraining scripts for missing/broken models")
            
        if self.warnings:
            recommendations.append("⚠️ Review and address all warnings")
            recommendations.append("📊 Consider retraining models with suspicious file sizes")
            
        if not self.critical_errors and not self.warnings:
            recommendations.append("✅ All models validated successfully")
            recommendations.append("🚀 System ready for professional deployment")
            
        return recommendations


def main():
    """Main validation function"""
    print("🔍 TradePulse.AI Professional AI Model Validation")
    print("=" * 60)
    
    validator = AIModelValidator()
    report = validator.validate_all_models()
    
    # Print summary
    print(f"\n📊 VALIDATION SUMMARY")
    print(f"Overall Status: {report['overall_status']}")
    print(f"Total Models: {report['summary']['total_models']}")
    print(f"Healthy: {report['summary']['healthy_models']}")
    print(f"Warnings: {report['summary']['warning_models']}")
    print(f"Critical Errors: {report['summary']['critical_models']}")
    print(f"Success Rate: {report['summary']['success_rate']}")
    print(f"Deployment Ready: {'✅ YES' if report['deployment_ready'] else '❌ NO'}")
    
    # Print critical errors
    if report['critical_errors']:
        print(f"\n🚨 CRITICAL ERRORS:")
        for error in report['critical_errors']:
            print(f"  ❌ {error}")
    
    # Print warnings
    if report['warnings']:
        print(f"\n⚠️ WARNINGS:")
        for warning in report['warnings']:
            print(f"  ⚠️ {warning}")
    
    # Print recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    for rec in report['recommendations']:
        print(f"  {rec}")
    
    # Print detailed results
    print(f"\n📋 DETAILED RESULTS:")
    for model_name, result in report['detailed_results'].items():
        status_emoji = {"HEALTHY": "✅", "WARNING": "⚠️", "CRITICAL_ERROR": "❌"}.get(result['status'], "❓")
        print(f"  {status_emoji} {model_name}: {result['status']}")
        if result.get('model_type'):
            print(f"    Type: {result['model_type']}")
        if result.get('expected_features'):
            print(f"    Features: {result['expected_features']}")
        if result.get('file_size'):
            print(f"    Size: {result['file_size']:,} bytes")
    
    # Exit with appropriate code
    exit_code = 0 if report['deployment_ready'] else 1
    print(f"\n{'✅ VALIDATION PASSED' if exit_code == 0 else '❌ VALIDATION FAILED'}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

