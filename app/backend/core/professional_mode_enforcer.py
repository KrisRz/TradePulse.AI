"""
Professional Mode Enforcer for TradePulse.AI
Ensures no fallbacks, mocks, or demos in professional deployment
"""

import logging
import inspect
from typing import Any, Callable, Dict, List
from functools import wraps
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ProfessionalModeEnforcer:
    """
    Enforces professional deployment standards
    
    - No fallback logic allowed
    - No mock data permitted
    - No demo calculations
    - Real data sources only
    - Professional error handling required
    """
    
    def __init__(self):
        self.is_professional_mode = True  # Always professional in production
        self.violations_detected = []
        self.enforcement_enabled = True
        
        # Banned patterns in professional mode
        self.banned_patterns = [
            'fallback', 'mock', 'demo', 'fake', 'dummy', 'test_data',
            'placeholder', 'sample', 'default_value', 'backup_calc'
        ]
        
        # Required data sources (must be real)
        self.required_real_sources = [
            'binance_api', 'live_market_data', 'dynamodb', 'real_portfolio'
        ]
    
    def enforce_no_fallbacks(self, func: Callable) -> Callable:
        """Decorator to enforce no fallback logic"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not self.enforcement_enabled:
                return func(*args, **kwargs)
            
            try:
                # Check function source for banned patterns
                source = inspect.getsource(func)
                
                for pattern in self.banned_patterns:
                    if pattern.lower() in source.lower():
                        violation = f"Function {func.__name__} contains banned pattern: {pattern}"
                        self.violations_detected.append({
                            'violation': violation,
                            'function': func.__name__,
                            'pattern': pattern,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        })
                        
                        logger.error(f"Professional mode violation: {violation}")
                        raise ProfessionalDeploymentException(
                            violation=violation,
                            component=func.__name__
                        )
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Validate result is not a fallback value
                if isinstance(result, (int, float)) and result == 0.5:
                    logger.warning(f"Suspicious fallback value 0.5 from {func.__name__}")
                
                return result
                
            except Exception as e:
                if "fallback" in str(e).lower() or "default" in str(e).lower():
                    raise NoFallbackException(
                        operation=func.__name__,
                        reason=str(e)
                    )
                raise
        
        return wrapper
    
    def validate_data_source(self, data: Any, source_name: str) -> bool:
        """Validate that data comes from real sources"""
        if not self.enforcement_enabled:
            return True
        
        # Check for mock/demo indicators
        if hasattr(data, '__dict__'):
            data_dict = data.__dict__
        elif isinstance(data, dict):
            data_dict = data
        else:
            return True  # Can't validate, assume valid
        
        # Look for mock indicators
        mock_indicators = ['mock', 'demo', 'fake', 'test', 'sample']
        
        for key, value in data_dict.items():
            key_lower = str(key).lower()
            value_str = str(value).lower()
            
            for indicator in mock_indicators:
                if indicator in key_lower or indicator in value_str:
                    violation = f"Mock/demo data detected in {source_name}: {key}={value}"
                    self.violations_detected.append({
                        'violation': violation,
                        'source': source_name,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                    
                    logger.error(f"Professional mode violation: {violation}")
                    raise RealDataRequiredException(
                        data_type=source_name,
                        source=key
                    )
        
        return True
    
    def require_real_data(self, data: Any, data_type: str):
        """Require that data is real (not mock/demo)"""
        if data is None:
            raise RealDataRequiredException(
                data_type=data_type,
                source="unknown"
            )
        
        self.validate_data_source(data, data_type)
        return data
    
    def get_violations_report(self) -> Dict[str, Any]:
        """Get report of professional mode violations"""
        return {
            'professional_mode_enabled': self.is_professional_mode,
            'enforcement_enabled': self.enforcement_enabled,
            'total_violations': len(self.violations_detected),
            'violations': self.violations_detected.copy(),
            'banned_patterns': self.banned_patterns,
            'required_real_sources': self.required_real_sources,
            'report_generated_at': datetime.now(timezone.utc).isoformat()
        }
    
    def enable_enforcement(self):
        """Enable professional mode enforcement"""
        self.enforcement_enabled = True
        logger.info("Professional mode enforcement ENABLED")
    
    def disable_enforcement(self):
        """Disable enforcement (for testing only)"""
        self.enforcement_enabled = False
        logger.warning("Professional mode enforcement DISABLED - testing mode only")


# Global enforcer instance
_professional_enforcer = None

def get_professional_enforcer() -> ProfessionalModeEnforcer:
    """Get global professional mode enforcer"""
    global _professional_enforcer
    
    if _professional_enforcer is None:
        _professional_enforcer = ProfessionalModeEnforcer()
    
    return _professional_enforcer


# Convenience decorators
def no_fallbacks(func: Callable) -> Callable:
    """Decorator to enforce no fallback logic"""
    enforcer = get_professional_enforcer()
    return enforcer.enforce_no_fallbacks(func)


def require_real_data(data_type: str):
    """Decorator to require real data"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            enforcer = get_professional_enforcer()
            return enforcer.require_real_data(result, data_type)
        return wrapper
    return decorator


# Import the new exceptions
from app.backend.core.exceptions import (
    ProfessionalDeploymentException, 
    NoFallbackException, 
    RealDataRequiredException
)
