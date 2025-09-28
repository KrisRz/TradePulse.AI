"""
Feature Vectorizer for ML Models
Converts feature dictionaries to model-ready vectors
"""

from typing import Dict, List
from .registry import get_feature_spec

def make_feature_vector(features: Dict[str, float]) -> List[float]:
    """Make feature vector in exact model order (8 features for reversal model)"""
    spec = get_feature_spec()
    vector = []
    
    for feature_name in spec:
        value = features.get(feature_name, 0.0)
        vector.append(float(value))
    
    return vector

def validate_feature_vector(vector: List[float], expected_size: int = 8) -> bool:
    """Validate feature vector size matches model expectations"""
    if len(vector) != expected_size:
        return False
    
    # Check for NaN/inf values
    for value in vector:
        if not isinstance(value, (int, float)) or value != value:  # NaN check
            return False
    
    return True
