"""
Professional Scaler Persistence System for TradePulse.AI
Ensures deterministic preprocessing by persisting scaler parameters from training
"""

import json
import pickle
import hashlib
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScalerParameters:
    """Scaler parameters with metadata"""
    scaler_type: str
    feature_name: str
    parameters: Dict[str, Any]
    training_commit: str
    created_at: str
    checksum: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScalerParameters':
        """Create from dictionary"""
        return cls(**data)


class ScalerPersistenceManager:
    """
    Professional scaler persistence manager
    Implements your requirement: persist scaler params from training, don't recompute at runtime
    """
    
    def __init__(self, scalers_dir: str = "config/scalers"):
        self.scalers_dir = Path(scalers_dir)
        self.scalers_dir.mkdir(exist_ok=True)
        self.loaded_scalers: Dict[str, ScalerParameters] = {}
        self._load_all_scalers()
    
    def _load_all_scalers(self) -> None:
        """Load all persisted scalers"""
        try:
            scaler_files = list(self.scalers_dir.glob("*.json"))
            
            for scaler_file in scaler_files:
                try:
                    with open(scaler_file, 'r') as f:
                        scaler_data = json.load(f)
                    
                    scaler_params = ScalerParameters.from_dict(scaler_data)
                    self.loaded_scalers[scaler_params.feature_name] = scaler_params
                    
                except Exception as e:
                    logger.warning(f"Failed to load scaler {scaler_file}: {e}")
            
            logger.info(f"✅ Loaded {len(self.loaded_scalers)} persisted scalers")
            
        except Exception as e:
            logger.error(f"Failed to load scalers: {e}")
    
    def save_scaler_parameters(self, 
                             feature_name: str,
                             scaler_type: str,
                             parameters: Dict[str, Any],
                             training_commit: str = "unknown") -> str:
        """
        Save scaler parameters from training
        Returns checksum for verification
        """
        try:
            from datetime import datetime, timezone
            
            # Calculate checksum
            param_str = json.dumps(parameters, sort_keys=True)
            checksum = hashlib.sha256(param_str.encode()).hexdigest()
            
            # Create scaler parameters object
            scaler_params = ScalerParameters(
                scaler_type=scaler_type,
                feature_name=feature_name,
                parameters=parameters,
                training_commit=training_commit,
                created_at=datetime.now(timezone.utc).isoformat(),
                checksum=checksum
            )
            
            # Save to file
            scaler_file = self.scalers_dir / f"{feature_name}_{scaler_type}.json"
            with open(scaler_file, 'w') as f:
                json.dump(scaler_params.to_dict(), f, indent=2)
            
            # Update loaded scalers
            self.loaded_scalers[feature_name] = scaler_params
            
            logger.info(f"✅ Saved scaler parameters: {feature_name} ({scaler_type})")
            return checksum
            
        except Exception as e:
            logger.error(f"Failed to save scaler parameters for {feature_name}: {e}")
            raise
    
    def get_scaler_parameters(self, feature_name: str) -> Optional[ScalerParameters]:
        """Get persisted scaler parameters for a feature"""
        return self.loaded_scalers.get(feature_name)
    
    def apply_scaling(self, feature_name: str, value: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """
        Apply persisted scaling to a feature value
        Uses training-time parameters, no runtime recomputation
        """
        scaler_params = self.get_scaler_parameters(feature_name)
        
        if not scaler_params:
            logger.warning(f"No scaler parameters found for {feature_name}, returning original value")
            return value
        
        try:
            scaler_type = scaler_params.scaler_type
            params = scaler_params.parameters
            
            if scaler_type == "minmax":
                return self._apply_minmax_scaling(value, params)
            elif scaler_type == "standard":
                return self._apply_standard_scaling(value, params)
            elif scaler_type == "log_minmax":
                return self._apply_log_minmax_scaling(value, params)
            elif scaler_type == "robust":
                return self._apply_robust_scaling(value, params)
            else:
                logger.warning(f"Unknown scaler type: {scaler_type}")
                return value
                
        except Exception as e:
            logger.error(f"Scaling failed for {feature_name}: {e}")
            return value
    
    def _apply_minmax_scaling(self, value: Union[float, np.ndarray], params: Dict[str, Any]) -> Union[float, np.ndarray]:
        """Apply MinMax scaling using persisted parameters"""
        min_val = params['min']
        max_val = params['max']
        scale = params.get('scale', max_val - min_val)
        
        if scale == 0:
            return 0.0
        
        return (value - min_val) / scale
    
    def _apply_standard_scaling(self, value: Union[float, np.ndarray], params: Dict[str, Any]) -> Union[float, np.ndarray]:
        """Apply Standard scaling using persisted parameters"""
        mean = params['mean']
        std = params['std']
        
        if std == 0:
            return 0.0
        
        return (value - mean) / std
    
    def _apply_log_minmax_scaling(self, value: Union[float, np.ndarray], params: Dict[str, Any]) -> Union[float, np.ndarray]:
        """Apply Log-MinMax scaling using persisted parameters"""
        # First apply log transform
        log_value = np.log1p(np.maximum(value, 0))  # log1p for numerical stability
        
        # Then apply minmax
        return self._apply_minmax_scaling(log_value, params)
    
    def _apply_robust_scaling(self, value: Union[float, np.ndarray], params: Dict[str, Any]) -> Union[float, np.ndarray]:
        """Apply Robust scaling using persisted parameters"""
        median = params['median']
        iqr = params['iqr']
        
        if iqr == 0:
            return 0.0
        
        return (value - median) / iqr
    
    def verify_scaler_integrity(self) -> Dict[str, bool]:
        """Verify integrity of all loaded scalers"""
        results = {}
        
        for feature_name, scaler_params in self.loaded_scalers.items():
            try:
                # Recalculate checksum
                param_str = json.dumps(scaler_params.parameters, sort_keys=True)
                calculated_checksum = hashlib.sha256(param_str.encode()).hexdigest()
                
                # Compare with stored checksum
                is_valid = calculated_checksum == scaler_params.checksum
                results[feature_name] = is_valid
                
                if not is_valid:
                    logger.error(f"❌ Scaler integrity check failed for {feature_name}")
                
            except Exception as e:
                logger.error(f"Integrity check error for {feature_name}: {e}")
                results[feature_name] = False
        
        return results
    
    def create_default_scalers(self) -> None:
        """Create default scaler parameters for TradePulse.AI features"""
        
        # Default scalers based on typical BTC trading data
        default_scalers = {
            "close": {
                "type": "minmax",
                "params": {"min": 10000.0, "max": 100000.0, "scale": 90000.0}
            },
            "volume": {
                "type": "log_minmax", 
                "params": {"min": 0.0, "max": 10.0, "scale": 10.0}
            },
            "rsi": {
                "type": "minmax",
                "params": {"min": 0.0, "max": 100.0, "scale": 100.0}
            },
            "macd": {
                "type": "standard",
                "params": {"mean": 0.0, "std": 500.0}
            },
            "bb_position": {
                "type": "minmax",
                "params": {"min": 0.0, "max": 1.0, "scale": 1.0}
            },
            "volatility": {
                "type": "log_minmax",
                "params": {"min": -5.0, "max": 0.0, "scale": 5.0}
            },
            "trend_strength": {
                "type": "minmax",
                "params": {"min": 0.0, "max": 1.0, "scale": 1.0}
            },
            "volume_ratio": {
                "type": "log_minmax",
                "params": {"min": -2.0, "max": 2.0, "scale": 4.0}
            }
        }
        
        for feature_name, scaler_config in default_scalers.items():
            if feature_name not in self.loaded_scalers:
                self.save_scaler_parameters(
                    feature_name=feature_name,
                    scaler_type=scaler_config["type"],
                    parameters=scaler_config["params"],
                    training_commit="default_v1.0.0"
                )
        
        logger.info("✅ Created default scaler parameters")


# Global scaler manager instance
_scaler_manager: Optional[ScalerPersistenceManager] = None

def get_scaler_manager() -> ScalerPersistenceManager:
    """Get global scaler manager instance"""
    global _scaler_manager
    if _scaler_manager is None:
        _scaler_manager = ScalerPersistenceManager()
        # Create defaults if none exist
        if not _scaler_manager.loaded_scalers:
            _scaler_manager.create_default_scalers()
    return _scaler_manager


def apply_deterministic_scaling(feature_name: str, value: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """
    Apply deterministic scaling using persisted training parameters
    No runtime recomputation - uses exact training-time scalers
    """
    manager = get_scaler_manager()
    return manager.apply_scaling(feature_name, value)


def verify_scaler_checksums() -> bool:
    """
    Verify all scaler checksums match
    Returns True if all scalers are valid
    """
    manager = get_scaler_manager()
    results = manager.verify_scaler_integrity()
    
    all_valid = all(results.values())
    
    if all_valid:
        logger.info("✅ All scaler checksums verified")
    else:
        invalid_scalers = [name for name, valid in results.items() if not valid]
        logger.error(f"❌ Invalid scaler checksums: {invalid_scalers}")
    
    return all_valid
