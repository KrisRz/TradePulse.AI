"""
Configuration management for TradePulse.AI backend
Uses Pydantic Settings for environment variable management
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import structlog

logger = structlog.get_logger()

class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Application settings
    APP_NAME: str = "TradePulse.AI"
    ENVIRONMENT: str = Field(default="dev", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    VERSION: str = "1.0.0"
    
    # Server settings
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=9002, env="PORT")
    API_PREFIX: str = Field(default="/api", env="API_PREFIX")
    
    # URLs
    BASE_URL: str = Field(default="http://localhost:9002", env="BASE_URL")
    FRONTEND_URL: str = Field(default="http://localhost:4321", env="FRONTEND_URL")
    
    # Security settings
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    ALGORITHM: str = "HS256"
    
    # AWS settings
    AWS_REGION: str = Field(default="eu-west-2", env="AWS_REGION")
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    
    # DynamoDB settings
    DYNAMODB_ENDPOINT: Optional[str] = Field(default="http://localhost:8000", env="DYNAMODB_ENDPOINT")
    DYNAMODB_REGION: str = Field(default="us-east-1", env="DYNAMODB_REGION")
    
    # DynamoDB table names
    SIGNALS_TABLE: str = Field(default="trading_signals", env="SIGNALS_TABLE")
    TRADES_TABLE: str = Field(default="trading_trades", env="TRADES_TABLE")
    PORTFOLIOS_TABLE: str = Field(default="virtual_portfolios", env="PORTFOLIOS_TABLE")
    USERS_TABLE: str = Field(default="tradepulse_users", env="USERS_TABLE")
    ANALYTICS_TABLE: str = Field(default="tradepulse_analytics", env="ANALYTICS_TABLE")
    
    # Binance API Configuration
    BINANCE_API_KEY: Optional[str] = Field(default=None, env="BINANCE_API_KEY")
    BINANCE_SECRET_KEY: Optional[str] = Field(default=None, env="BINANCE_SECRET_KEY") 
    BINANCE_TESTNET: bool = Field(default=False, env="BINANCE_TESTNET")
    
    # Market data settings
    BINANCE_API_URL: str = "https://api.binance.com/api/v3"
    MARKET_DATA_CACHE_TTL: int = Field(default=60, env="MARKET_DATA_CACHE_TTL")  # seconds
    # Enforce WebSocket-only decision paths (no REST fallback during runtime decisions)
    STRICT_LIVE_STREAM: bool = Field(default=False, env="STRICT_LIVE_STREAM")
    
    # ML and trading settings
    MODEL_S3_BUCKET: str = Field(default="tradepulse-models", env="MODEL_S3_BUCKET")
    DEFAULT_STARTING_BALANCE: float = Field(default=10000.0, env="DEFAULT_STARTING_BALANCE")
    MAX_POSITION_SIZE_PERCENTAGE: float = Field(default=25.0, env="MAX_POSITION_SIZE_PERCENTAGE")
    DEFAULT_STOP_LOSS_PERCENTAGE: float = Field(default=2.0, env="DEFAULT_STOP_LOSS_PERCENTAGE")
    DEFAULT_TAKE_PROFIT_PERCENTAGE: float = Field(default=4.0, env="DEFAULT_TAKE_PROFIT_PERCENTAGE")
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds
    
    # Redis settings (for caching and rate limiting)
    REDIS_URL: Optional[str] = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Discord webhook for notifications
    DISCORD_WEBHOOK_URL: Optional[str] = Field(default=None, env="DISCORD_WEBHOOK_URL")
    
    # Production overrides
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() in ["dev", "development"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from environment


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)"""
    global _settings
    _settings = Settings()
    return _settings 