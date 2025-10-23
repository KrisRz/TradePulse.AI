"""
Professional Environment Configuration System for TradePulse.AI

Enterprise-grade environment management with:
- Environment-specific configurations
- Validation and type safety
- Secrets management
- Feature flags
- Performance tuning per environment
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Union
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings
from pathlib import Path
import os


class Environment(str, Enum):
    """Supported environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseConfig(BaseSettings):
    """Database configuration per environment"""
    
    # DynamoDB Configuration
    dynamodb_endpoint: Optional[str] = Field(default="http://localhost:8000", env="DYNAMODB_ENDPOINT")
    dynamodb_region: str = Field(default="eu-west-2", env="DYNAMODB_REGION")
    
    # Connection pooling
    max_connections: int = Field(default=50, env="DB_MAX_CONNECTIONS")
    connection_timeout: int = Field(default=30, env="DB_CONNECTION_TIMEOUT")
    read_timeout: int = Field(default=60, env="DB_READ_TIMEOUT")
    
    # Retry configuration
    max_retries: int = Field(default=3, env="DB_MAX_RETRIES")
    retry_backoff_base: float = Field(default=1.0, env="DB_RETRY_BACKOFF_BASE")
    
    @field_validator('max_connections')
    @classmethod
    def validate_max_connections(cls, v):
        if v < 1 or v > 200:
            raise ValueError('max_connections must be between 1 and 200')
        return v
    
    @field_validator('connection_timeout', 'read_timeout')
    @classmethod
    def validate_timeouts(cls, v):
        if v < 1 or v > 300:
            raise ValueError('timeout must be between 1 and 300 seconds')
        return v


class SecurityConfig(BaseSettings):
    """Security configuration per environment"""
    
    # JWT Configuration
    secret_key: SecretStr = Field(
        default="dev-secret-key-change-in-production-must-be-at-least-32-characters-long", 
        env="SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # CORS Configuration
    allowed_origins: List[str] = Field(default=[], env="ALLOWED_ORIGINS")
    allowed_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE"], env="ALLOWED_METHODS")
    allowed_headers: List[str] = Field(default=["*"], env="ALLOWED_HEADERS")
    allow_credentials: bool = Field(default=True, env="ALLOW_CREDENTIALS")
    
    # Rate Limiting - INCREASED FOR DEVELOPMENT/DASHBOARD POLLING  
    rate_limit_requests: int = Field(default=1000, env="RATE_LIMIT_REQUESTS")  # Increased from 100
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")
    
    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v):
        if len(v.get_secret_value()) < 32:
            raise ValueError('Secret key must be at least 32 characters long')
        return v
    
    @field_validator('access_token_expire_minutes')
    @classmethod
    def validate_access_token_expire(cls, v):
        if v < 5 or v > 1440:  # 5 minutes to 24 hours
            raise ValueError('access_token_expire_minutes must be between 5 and 1440')
        return v


class APIConfig(BaseSettings):
    """API configuration per environment"""
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=9002, env="API_PORT")
    workers: int = Field(default=1, env="API_WORKERS")
    
    # Request Configuration
    max_request_size: int = Field(default=16 * 1024 * 1024, env="MAX_REQUEST_SIZE")  # 16MB
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    
    # Response Configuration
    enable_compression: bool = Field(default=True, env="ENABLE_COMPRESSION")
    compression_level: int = Field(default=6, env="COMPRESSION_LEVEL")
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        if v < 1024 or v > 65535:
            raise ValueError('port must be between 1024 and 65535')
        return v
    
    @field_validator('workers')
    @classmethod
    def validate_workers(cls, v):
        if v < 1 or v > 32:
            raise ValueError('workers must be between 1 and 32')
        return v


class ExternalServicesConfig(BaseSettings):
    """External services configuration"""
    
    # Binance API
    binance_api_key: Optional[SecretStr] = Field(default=None, env="BINANCE_API_KEY")
    binance_secret_key: Optional[SecretStr] = Field(default=None, env="BINANCE_SECRET_KEY")
    binance_testnet: bool = Field(default=True, env="BINANCE_TESTNET")
    binance_timeout: int = Field(default=10, env="BINANCE_TIMEOUT")
    
    # AWS Services
    aws_access_key_id: Optional[SecretStr] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[SecretStr] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="eu-west-2", env="AWS_REGION")
    
    # Model Storage
    model_bucket: Optional[str] = Field(default=None, env="MODEL_BUCKET")
    model_cache_ttl: int = Field(default=3600, env="MODEL_CACHE_TTL")  # 1 hour


class FeatureFlags(BaseSettings):
    """Feature flags per environment"""
    
    # Trading Features
    enable_live_trading: bool = Field(default=False, env="ENABLE_LIVE_TRADING")
    enable_paper_trading: bool = Field(default=True, env="ENABLE_PAPER_TRADING")
    enable_backtesting: bool = Field(default=True, env="ENABLE_BACKTESTING")
    
    # AI Features
    enable_ai_models: bool = Field(default=True, env="ENABLE_AI_MODELS")
    enable_model_training: bool = Field(default=False, env="ENABLE_MODEL_TRAINING")
    enable_auto_rebalancing: bool = Field(default=False, env="ENABLE_AUTO_REBALANCING")
    
    # Monitoring Features
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    enable_tracing: bool = Field(default=False, env="ENABLE_TRACING")
    enable_profiling: bool = Field(default=False, env="ENABLE_PROFILING")
    
    # Admin Features
    enable_admin_api: bool = Field(default=True, env="ENABLE_ADMIN_API")
    enable_debug_endpoints: bool = Field(default=False, env="ENABLE_DEBUG_ENDPOINTS")


class EnvironmentSettings(BaseSettings):
    """Main environment settings"""
    
    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    debug: bool = Field(default=False, env="DEBUG")
    log_level: LogLevel = Field(default=LogLevel.INFO, env="LOG_LEVEL")
    
    # Application
    app_name: str = Field(default="TradePulse.AI", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    
    # Configuration objects
    database: DatabaseConfig = DatabaseConfig()
    security: SecurityConfig = SecurityConfig()
    api: APIConfig = APIConfig()
    external_services: ExternalServicesConfig = ExternalServicesConfig()
    features: FeatureFlags = FeatureFlags()
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        if v not in Environment:
            raise ValueError(f'Environment must be one of: {list(Environment)}')
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,  # Allow case-insensitive env var matching
        "extra": "ignore",  # Ignore extra fields
        "env_prefix": ""  # No prefix for env vars
    }


def get_environment_config() -> EnvironmentSettings:
    """Get environment configuration with validation"""
    return EnvironmentSettings()


def get_environment_specific_config(env: Environment) -> Dict[str, Any]:
    """Get environment-specific configuration overrides"""
    
    configs = {
        Environment.DEVELOPMENT: {
            "debug": True,
            "log_level": LogLevel.DEBUG,
            "database": {
                "dynamodb_endpoint": "http://localhost:8000",
                "max_connections": 10,
            },
            "security": {
                "allowed_origins": ["http://localhost:4321", "http://localhost:3000"],
                "access_token_expire_minutes": 60,  # Longer for development
            },
            "api": {
                "workers": 1,
                "enable_compression": False,  # Disable for easier debugging
            },
            "external_services": {
                "binance_testnet": True,
                "binance_timeout": 30,  # Longer timeout for development
            },
            "features": {
                "enable_live_trading": False,
                "enable_debug_endpoints": True,
                "enable_profiling": True,
            }
        },
        
        Environment.STAGING: {
            "debug": False,
            "log_level": LogLevel.INFO,
            "database": {
                "max_connections": 25,
                "connection_timeout": 20,
            },
            "security": {
                "allowed_origins": ["https://staging.tradepulse.ai"],
                "access_token_expire_minutes": 30,
            },
            "api": {
                "workers": 2,
                "enable_compression": True,
            },
            "external_services": {
                "binance_testnet": True,  # Still use testnet in staging
                "binance_timeout": 15,
            },
            "features": {
                "enable_live_trading": False,  # Paper trading only in staging
                "enable_debug_endpoints": False,
                "enable_tracing": True,
            }
        },
        
        Environment.PRODUCTION: {
            "debug": False,
            "log_level": LogLevel.WARNING,
            "database": {
                "max_connections": 50,
                "connection_timeout": 10,
                "read_timeout": 30,
            },
            "security": {
                "allowed_origins": ["https://tradepulse.ai", "https://app.tradepulse.ai"],
                "access_token_expire_minutes": 15,  # Shorter for security
                "rate_limit_requests": 1000,
            },
            "api": {
                "workers": 4,
                "enable_compression": True,
                "compression_level": 9,
            },
            "external_services": {
                "binance_testnet": False,  # Live trading in production
                "binance_timeout": 10,
            },
            "features": {
                "enable_live_trading": True,
                "enable_debug_endpoints": False,
                "enable_metrics": True,
                "enable_tracing": True,
            }
        }
    }
    
    return configs.get(env, {})


def load_environment_config(env_file: Optional[str] = None) -> EnvironmentSettings:
    """Load and validate environment configuration"""
    
    # Set environment file if provided
    if env_file and Path(env_file).exists():
        os.environ.setdefault("ENV_FILE", env_file)
    
    # Load base configuration
    config = get_environment_config()
    
    # Apply environment-specific overrides
    env_overrides = get_environment_specific_config(config.environment)
    
    # Merge configurations (simplified - in production, use deep merge)
    for key, value in env_overrides.items():
        if hasattr(config, key):
            if isinstance(value, dict):
                # Update nested configuration
                nested_config = getattr(config, key)
                for nested_key, nested_value in value.items():
                    if hasattr(nested_config, nested_key):
                        setattr(nested_config, nested_key, nested_value)
            else:
                setattr(config, key, value)
    
    return config


# Global configuration instance
_config: Optional[EnvironmentSettings] = None

def get_config() -> EnvironmentSettings:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = load_environment_config()
    return _config


def reload_config(env_file: Optional[str] = None) -> EnvironmentSettings:
    """Reload configuration (useful for testing)"""
    global _config
    _config = None
    if env_file:
        _config = load_environment_config(env_file)
    else:
        _config = load_environment_config()
    return _config
