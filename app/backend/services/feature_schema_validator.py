"""
Professional Feature Schema Validator for TradePulse.AI
Implements your production-grade feature integrity system with checksums
"""

import json
import hashlib
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

# Import scaler verification
from app.backend.services.scaler_persistence import verify_scaler_checksums

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of feature validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    corrected_features: Optional[np.ndarray] = None
    feature_order: Optional[List[str]] = None


class FeatureSchemaValidator:
    """
    Production-grade feature schema validator with checksums
    Implements fail-fast validation as per your requirements
    """
    
    def __init__(self, schema_path: Optional[str] = None):
        self.schema_path = schema_path or "config/FEATURE_SCHEMA.json"
        self.schema: Dict[str, Any] = {}
        self.schema_checksum: str = ""
        self._load_schema()
    
    def _load_schema(self) -> None:
        """Load and validate feature schema"""
        try:
            schema_file = Path(self.schema_path)
            if not schema_file.exists():
                raise FileNotFoundError(f"Feature schema not found: {self.schema_path}")
            
            with open(schema_file, 'r') as f:
                content = f.read()
                self.schema = json.loads(content)
            
            # Calculate and verify checksum
            schema_content = json.dumps(self.schema['features'], sort_keys=True)
            calculated_checksum = hashlib.sha256(schema_content.encode()).hexdigest()
            
            stored_checksum = self.schema.get('checksum', '').replace('sha256:', '')
            
            if stored_checksum and stored_checksum != calculated_checksum:
                logger.warning(f"Schema checksum mismatch: stored={stored_checksum[:8]}..., calculated={calculated_checksum[:8]}...")
            
            self.schema_checksum = calculated_checksum
            
            logger.info(f"✅ Feature schema loaded: {self.schema['schema_version']}")
            logger.debug(f"Schema checksum: {calculated_checksum[:16]}...")
            
        except Exception as e:
            logger.error(f"Failed to load feature schema: {e}")
            raise
    
    def validate_on_boot(self) -> bool:
        """
        Boot-time validation - must complete within 5 seconds
        Returns True if system can proceed, False to abort
        """
        start_time = logger.info("🔍 Boot-time feature schema validation...")
        
        try:
            # Verify schema integrity
            if not self.schema:
                logger.error("❌ Feature schema is empty")
                return False
            
            # Verify required sections
            required_sections = ['features', 'model_requirements', 'validation_rules']
            for section in required_sections:
                if section not in self.schema:
                    logger.error(f"❌ Missing required schema section: {section}")
                    return False
            
            # Verify feature definitions
            features = self.schema['features']['feature_definitions']
            standard_order = self.schema['features']['standard_order']
            
            if len(features) != len(standard_order):
                logger.error(f"❌ Feature count mismatch: definitions={len(features)}, order={len(standard_order)}")
                return False
            
            # Verify all features in standard order are defined
            for feature_name in standard_order:
                if feature_name not in features:
                    logger.error(f"❌ Feature '{feature_name}' in standard_order but not defined")
                    return False
            
            # Verify model requirements
            for model_name, requirements in self.schema['model_requirements'].items():
                expected_count = requirements['expected_features']
                feature_order = requirements['feature_order']
                
                if len(feature_order) != expected_count:
                    logger.error(f"❌ Model {model_name}: feature count mismatch")
                    return False
            
            # Verify scaler parameter integrity
            if not verify_scaler_checksums():
                logger.error("❌ Scaler checksum verification failed")
                return False
            
            logger.info("✅ Boot-time validation passed - system can proceed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Boot-time validation failed: {e}")
            return False
    
    def validate_inference_input(self, 
                                features: Dict[str, Any], 
                                model_name: str,
                                layer_name: str = "") -> ValidationResult:
        """
        Pre-inference validation - must complete within 5 seconds
        Validates feature integrity before model inference
        """
        errors = []
        warnings = []
        
        try:
            # Get model requirements
            if model_name not in self.schema['model_requirements']:
                # Try to match by model type
                model_type = self._detect_model_type(model_name)
                if model_type not in self.schema['model_requirements']:
                    errors.append(f"Unknown model type: {model_name}")
                    return ValidationResult(False, errors, warnings)
                model_requirements = self.schema['model_requirements'][model_type]
            else:
                model_requirements = self.schema['model_requirements'][model_name]
            
            expected_features = model_requirements['expected_features']
            required_order = model_requirements['feature_order']
            expected_dtype = model_requirements['dtype']
            
            # Validate feature count
            if len(features) < expected_features:
                missing = set(required_order) - set(features.keys())
                errors.append(f"Missing features: {missing}")
            
            # Validate feature names and order
            available_features = [f for f in required_order if f in features]
            if len(available_features) != expected_features:
                warnings.append(f"Feature count mismatch: expected {expected_features}, got {len(available_features)}")
            
            # Validate feature values
            validated_features = {}
            for feature_name in required_order:
                if feature_name in features:
                    validated_value = self._validate_feature_value(feature_name, features[feature_name])
                    validated_features[feature_name] = validated_value
                else:
                    # Use default value
                    default_value = self._get_default_value(feature_name)
                    validated_features[feature_name] = default_value
                    warnings.append(f"Using default for missing feature: {feature_name}")
            
            # Create feature array in correct order
            feature_array = np.array([validated_features[f] for f in required_order], dtype=expected_dtype)
            feature_array = feature_array.reshape(1, -1)
            
            # Final shape validation
            expected_shape = model_requirements['input_shape']
            if list(feature_array.shape) != expected_shape[:len(feature_array.shape)]:
                errors.append(f"Shape mismatch: expected {expected_shape}, got {feature_array.shape}")
            
            is_valid = len(errors) == 0
            
            if is_valid:
                logger.debug(f"✅ {layer_name}: Feature validation passed")
            else:
                logger.error(f"❌ {layer_name}: Feature validation failed: {errors}")
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                corrected_features=feature_array if is_valid else None,
                feature_order=required_order
            )
            
        except Exception as e:
            errors.append(f"Validation exception: {e}")
            return ValidationResult(False, errors, warnings)
    
    def _detect_model_type(self, model_name: str) -> str:
        """Detect model type from model name or class"""
        model_name_lower = model_name.lower()
        
        if 'lgb' in model_name_lower or 'lightgbm' in model_name_lower:
            if 'classifier' in model_name_lower:
                return 'lightgbm_classifier'
            else:
                return 'lightgbm_regressor'
        elif 'lstm' in model_name_lower:
            return 'lstm_ensemble'
        else:
            # Default to LightGBM classifier
            return 'lightgbm_classifier'
    
    def _validate_feature_value(self, feature_name: str, value: Any) -> float:
        """Validate and normalize a single feature value"""
        try:
            feature_def = self.schema['features']['feature_definitions'][feature_name]
            
            # Convert to float
            float_value = float(value)
            
            # Handle NaN/inf
            if not np.isfinite(float_value):
                logger.warning(f"Invalid value for {feature_name}: {value}, using default")
                return feature_def['default_value']
            
            # Clip to valid range
            min_val = feature_def['min_value']
            max_val = feature_def['max_value']
            
            if float_value < min_val or float_value > max_val:
                clipped = np.clip(float_value, min_val, max_val)
                logger.debug(f"Clipped {feature_name}: {float_value} → {clipped}")
                return clipped
            
            return float_value
            
        except Exception as e:
            logger.error(f"Feature validation error for {feature_name}: {e}")
            return self._get_default_value(feature_name)
    
    def _get_default_value(self, feature_name: str) -> float:
        """Get default value for a feature"""
        try:
            return self.schema['features']['feature_definitions'][feature_name]['default_value']
        except KeyError:
            logger.warning(f"No default value for {feature_name}, using 0.0")
            return 0.0
    
    def get_feature_order(self, model_name: str) -> List[str]:
        """Get required feature order for a model"""
        try:
            model_type = self._detect_model_type(model_name)
            return self.schema['model_requirements'][model_type]['feature_order']
        except KeyError:
            return self.schema['features']['standard_order']
    
    def get_expected_shape(self, model_name: str) -> List[int]:
        """Get expected input shape for a model"""
        try:
            model_type = self._detect_model_type(model_name)
            return self.schema['model_requirements'][model_type]['input_shape']
        except KeyError:
            return [1, 8]  # Default shape
    
    def should_fail_fast(self) -> bool:
        """Check if validation should fail fast on errors"""
        return self.schema.get('validation_rules', {}).get('fail_on_mismatch', True)
    
    def update_checksum(self) -> str:
        """Recalculate and update schema checksum"""
        schema_content = json.dumps(self.schema['features'], sort_keys=True)
        new_checksum = hashlib.sha256(schema_content.encode()).hexdigest()
        
        # Update schema file
        self.schema['checksum'] = f"sha256:{new_checksum}"
        
        with open(self.schema_path, 'w') as f:
            json.dump(self.schema, f, indent=2)
        
        self.schema_checksum = new_checksum
        logger.info(f"✅ Schema checksum updated: {new_checksum[:16]}...")
        
        return new_checksum


# Global validator instance
_validator: Optional[FeatureSchemaValidator] = None

def get_feature_validator() -> FeatureSchemaValidator:
    """Get global feature validator instance"""
    global _validator
    if _validator is None:
        _validator = FeatureSchemaValidator()
    return _validator


def validate_features_for_model(features: Dict[str, Any], 
                              model_name: str,
                              layer_name: str = "") -> Tuple[bool, np.ndarray]:
    """
    Convenience function for feature validation
    Returns (is_valid, feature_array)
    """
    validator = get_feature_validator()
    result = validator.validate_inference_input(features, model_name, layer_name)
    
    if not result.is_valid and validator.should_fail_fast():
        error_msg = f"Feature validation failed for {layer_name}: {result.errors}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    return result.is_valid, result.corrected_features


def boot_time_validation() -> bool:
    """
    Boot-time feature schema validation
    Must be called during application startup
    """
    try:
        validator = get_feature_validator()
        return validator.validate_on_boot()
    except Exception as e:
        logger.error(f"Boot-time validation failed: {e}")
        return False
