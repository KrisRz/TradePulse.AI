"""
AWS SSM Parameter Store Configuration Reader
Reads secrets and configuration from SSM at startup (not from environment variables)
"""

import os
import logging
from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError

from app.backend.core.config import get_settings

logger = logging.getLogger(__name__)

class SSMConfigReader:
    """
    Reads configuration from AWS SSM Parameter Store
    Best practice: Load secrets at startup, not from environment variables
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.ssm = boto3.client(
            'ssm',
            region_name=self.settings.AWS_REGION
        )
        self.config_cache: Dict[str, str] = {}
        logger.info("🔐 SSM Config Reader initialized")
    
    async def load_secrets(self) -> Dict[str, str]:
        """
        Load all required secrets from SSM Parameter Store
        Returns dict with decrypted values
        """
        try:
            # Parameter paths based on terraform.tfvars configuration
            parameter_paths = {
                'BINANCE_API_KEY': f'/{self.settings.DYNAMODB_TABLE_PREFIX.rstrip("_")}/{self.settings.ENVIRONMENT}/BINANCE_API_KEY',
                'BINANCE_API_SECRET': f'/{self.settings.DYNAMODB_TABLE_PREFIX.rstrip("_")}/{self.settings.ENVIRONMENT}/BINANCE_API_SECRET',
            }
            
            logger.info(f"🔐 Loading secrets from SSM Parameter Store...")
            
            # Get parameters in batch
            response = self.ssm.get_parameters(
                Names=list(parameter_paths.values()),
                WithDecryption=True  # Decrypt SecureString parameters
            )
            
            # Map parameter names to values
            secrets = {}
            for param in response.get('Parameters', []):
                param_name = param['Name']
                param_value = param['Value']
                
                # Find the config key for this parameter path
                for config_key, param_path in parameter_paths.items():
                    if param_path == param_name:
                        secrets[config_key] = param_value
                        logger.info(f"✅ Loaded {config_key} from SSM")
                        break
            
            # Check for missing parameters
            invalid_params = response.get('InvalidParameters', [])
            if invalid_params:
                logger.error(f"❌ Missing SSM parameters: {invalid_params}")
                raise ValueError(f"Missing required SSM parameters: {invalid_params}")
            
            # Cache the secrets
            self.config_cache.update(secrets)
            
            logger.info(f"✅ Successfully loaded {len(secrets)} secrets from SSM")
            return secrets
            
        except ClientError as e:
            logger.error(f"❌ Failed to load secrets from SSM: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error loading SSM secrets: {e}")
            raise
    
    def get_secret(self, key: str) -> Optional[str]:
        """Get a cached secret value"""
        return self.config_cache.get(key)
    
    def get_binance_credentials(self) -> tuple[str, str]:
        """Get Binance API credentials"""
        api_key = self.get_secret('BINANCE_API_KEY')
        api_secret = self.get_secret('BINANCE_API_SECRET')
        
        if not api_key or not api_secret:
            raise ValueError("Binance API credentials not loaded from SSM")
        
        return api_key, api_secret
    
    async def validate_configuration(self) -> bool:
        """Validate that all required configuration is available"""
        try:
            # Check if running in AWS (has SSM access)
            if self.settings.is_development:
                logger.info("🔐 Development mode - skipping SSM validation")
                return True
            
            # Validate required secrets exist
            required_secrets = ['BINANCE_API_KEY', 'BINANCE_API_SECRET']
            missing_secrets = [key for key in required_secrets if not self.get_secret(key)]
            
            if missing_secrets:
                logger.error(f"❌ Missing required secrets: {missing_secrets}")
                return False
            
            logger.info("✅ All required secrets validated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            return False

# Global singleton instance
_ssm_config: Optional[SSMConfigReader] = None

def get_ssm_config() -> SSMConfigReader:
    """Get or create the global SSM config reader"""
    global _ssm_config
    if _ssm_config is None:
        _ssm_config = SSMConfigReader()
    return _ssm_config
