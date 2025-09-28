"""
Production Configuration Validation - TradePulse.AI
================================================

Strict configuration validation for production deployment
with fail-fast guarantees and zero tolerance for invalid configs.

Author: TradePulse.AI Development Team
Version: 1.0.0
"""

import os
import re
import logging

logger = logging.getLogger(__name__)

def must_env(name: str) -> str:
    """Get required environment variable or fail fast"""
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing required env: {name}")
    return v.strip().strip('"').strip("'")

def validate_prod_config():
    """Validate production configuration - FAIL FAST on any issues"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        logger.info("🔍 Validating PRODUCTION configuration...")
        
        # Binance API Keys (mainnet) - without these STOP
        try:
            key = must_env("BINANCE_API_KEY")
            sec = must_env("BINANCE_API_SECRET")
            
            # Validate key format (64 alphanumeric characters)
            if not re.fullmatch(r"[A-Za-z0-9]{64}", key):
                raise RuntimeError(f"BINANCE_API_KEY format invalid: expected 64 alphanumeric chars, got {len(key)} chars")
            
            if not re.fullmatch(r"[A-Za-z0-9]{64}", sec):
                raise RuntimeError(f"BINANCE_API_SECRET format invalid: expected 64 alphanumeric chars, got {len(sec)} chars")
            
            logger.info(f"✅ Binance API keys validated (64 chars each)")
            
        except Exception as e:
            logger.error(f"❌ Binance configuration validation failed: {e}")
            raise RuntimeError(f"PRODUCTION: Invalid Binance configuration - {e}")
        
        # DynamoDB configuration
        try:
            dynamodb_endpoint = os.getenv("DYNAMODB_ENDPOINT")
            if not dynamodb_endpoint or "localhost" in dynamodb_endpoint:
                raise RuntimeError("PRODUCTION: Cannot use localhost DynamoDB endpoint")
            
            # Should be AWS endpoint in production
            if not dynamodb_endpoint.startswith("https://dynamodb."):
                raise RuntimeError(f"PRODUCTION: Invalid DynamoDB endpoint: {dynamodb_endpoint}")
            
            logger.info(f"✅ DynamoDB endpoint validated: {dynamodb_endpoint}")
            
        except Exception as e:
            logger.error(f"❌ DynamoDB configuration validation failed: {e}")
            raise RuntimeError(f"PRODUCTION: Invalid DynamoDB configuration - {e}")
        
        # Security configuration
        try:
            secret_key = must_env("SECRET_KEY")
            if len(secret_key) < 32:
                raise RuntimeError("PRODUCTION: SECRET_KEY must be at least 32 characters")
            
            logger.info(f"✅ Security configuration validated")
            
        except Exception as e:
            logger.error(f"❌ Security configuration validation failed: {e}")
            raise RuntimeError(f"PRODUCTION: Invalid security configuration - {e}")
        
        logger.info("✅ PRODUCTION configuration validation PASSED")
    
    elif env == "development":
        logger.info("🔧 Development environment - skipping strict validation")
        
        # Optional development checks
        binance_private = os.getenv("ENABLE_PRIVATE_BINANCE", "false").lower() == "true"
        if binance_private:
            logger.info("🔑 Private Binance enabled in development")
        else:
            logger.info("🔑 Private Binance disabled in development - using public API only")
    
    else:
        raise RuntimeError(f"Unknown environment: {env}")

def validate_ml_versions():
    """Validate ML library versions for model compatibility"""
    try:
        import sklearn
        import xgboost as xgb
        import lightgbm as lgb
        
        expected_versions = {
            "sklearn": "1.7.1",
            "xgboost": "2.1.3", 
            "lightgbm": "4.3.0"
        }
        
        actual_versions = {
            "sklearn": sklearn.__version__,
            "xgboost": xgb.__version__,
            "lightgbm": lgb.__version__
        }
        
        for lib, expected in expected_versions.items():
            actual = actual_versions[lib]
            if actual != expected:
                logger.warning(f"⚠️ {lib} version mismatch: expected {expected}, got {actual}")
            else:
                logger.debug(f"✅ {lib} version correct: {actual}")
        
        logger.info("✅ ML library versions checked")
        
    except Exception as e:
        logger.error(f"❌ ML version validation failed: {e}")
        # Don't fail - just warn
        
# Export validation functions
__all__ = ["validate_prod_config", "validate_ml_versions", "must_env"]
