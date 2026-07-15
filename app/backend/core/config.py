"""
Configuration management for TradePulse.AI backend
Uses Pydantic Settings for environment variable management
"""

import os
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field
import structlog

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Load environment variables from root .env first, then backend config .env
# This ensures professional/live keys stored at project root are picked up.
# ---------------------------------------------------------------------------
try:
    project_root = Path(__file__).resolve().parents[3]
    environment = os.getenv("ENVIRONMENT", "development")
    
    # Select env file based on ENVIRONMENT
    candidate_env_files = []
    
    # In production, SKIP root .env (contains Docker dummy AWS credentials)
    # In development, load root .env for Binance keys
    if environment != "production":
        candidate_env_files.append(project_root / ".env")
    
    if environment == "production":
        candidate_env_files.append(project_root / "app/backend/config/production.env")
    else:
        candidate_env_files.append(project_root / "app/backend/config/development.env")
    
    candidate_env_files.append(project_root / "app/backend/config/.env")

    loaded_any = False
    for env_path in candidate_env_files:
        if env_path.exists():
            load_dotenv(dotenv_path=str(env_path), override=False)
            loaded_any = True
            # Log once per file for traceability
            try:
                logger.info("ENV loaded", path=str(env_path))
            except Exception:
                pass

    if not loaded_any:
        try:
            logger.warning("No .env files found - relying on process env")
        except Exception:
            pass
except Exception as env_err:
    try:
        logger.warning("ENV preload failed", error=str(env_err))
    except Exception:
        pass

class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # We preload .env files above using python-dotenv to allow multiple sources.
    # Avoid hard-coding a single env_file path here.
    model_config = {
        "env_file": None,
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "allow"  # Allow extra fields from environment
    }
    
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
    DYNAMODB_REGION: str = Field(default="eu-west-2", env="DYNAMODB_REGION")
    
    # DynamoDB table configuration
    DYNAMODB_TABLE_PREFIX: str = Field(default="", env="DYNAMODB_TABLE_PREFIX")
    
    # DynamoDB table names
    SIGNALS_TABLE: str = Field(default="trading_signals", env="SIGNALS_TABLE")
    TRADES_TABLE: str = Field(default="trading_trades", env="TRADES_TABLE")
    PORTFOLIOS_TABLE: str = Field(default="tradepulse-virtual-portfolios", env="PORTFOLIOS_TABLE")
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
    
    # Professional mode settings
    PROFESSIONAL_MODE: bool = Field(default=False, env="PROFESSIONAL_MODE")
    
    # ML and trading settings
    MODEL_S3_BUCKET: str = Field(default="tradepulse-models", env="MODEL_S3_BUCKET")
    DEFAULT_STARTING_BALANCE: float = Field(default=10000.0, env="DEFAULT_STARTING_BALANCE")
    MAX_POSITION_SIZE_PERCENTAGE: float = Field(default=25.0, env="MAX_POSITION_SIZE_PERCENTAGE")
    DEFAULT_STOP_LOSS_PERCENTAGE: float = Field(default=2.0, env="DEFAULT_STOP_LOSS_PERCENTAGE")
    DEFAULT_TAKE_PROFIT_PERCENTAGE: float = Field(default=4.0, env="DEFAULT_TAKE_PROFIT_PERCENTAGE")
    
    # 🎯 DAY TRADING: Kalman Filter for noise reduction
    KALMAN_FILTER_ENABLED: bool = Field(default=True, env="KALMAN_FILTER_ENABLED")
    KALMAN_SMOOTHING_STRENGTH: float = Field(default=0.8, env="KALMAN_SMOOTHING_STRENGTH")  # 0.5-2.0 range

    # 🧠 DAY TRADING: Continuous Learning - Fast Optimization
    DAY_TRADING_LEARNING_MODE: bool = Field(default=True, env="DAY_TRADING_LEARNING_MODE")
    # Fast optimization cycles (2h instead of 24h for day trading)
    LEARNING_OPTIMIZATION_HOURS: float = Field(default=2.0, env="LEARNING_OPTIMIZATION_HOURS")  # 2h for day trading
    # Lower sample requirements (5-8 positions instead of 20)
    LEARNING_MIN_SAMPLES: int = Field(default=6, env="LEARNING_MIN_SAMPLES")  # 6 positions for day trading
    # Auto-apply confidence threshold (lower for faster adaptation)
    LEARNING_CONFIDENCE_THRESHOLD: float = Field(default=0.70, env="LEARNING_CONFIDENCE_THRESHOLD")  # 70% (was 75%)
    # Model monitoring cycles (6h instead of 12h)
    LEARNING_MODEL_MONITORING_HOURS: float = Field(default=6.0, env="LEARNING_MODEL_MONITORING_HOURS")
    # Weighted learning - recency weight factor (higher = more weight to recent data)
    LEARNING_RECENCY_WEIGHT: float = Field(default=1.5, env="LEARNING_RECENCY_WEIGHT")  # 1.5x weight for newest data
    # Confidence decay per hour (old recommendations lose confidence)
    LEARNING_CONFIDENCE_DECAY_PER_HOUR: float = Field(default=0.02, env="LEARNING_CONFIDENCE_DECAY_PER_HOUR")  # -2%/hour
    # Quick reaction mode - emergency optimization for critical issues
    LEARNING_QUICK_REACTION_ENABLED: bool = Field(default=True, env="LEARNING_QUICK_REACTION_ENABLED")
    # Quick reaction threshold - min loss % to trigger emergency optimization
    LEARNING_QUICK_REACTION_LOSS_PCT: float = Field(default=3.0, env="LEARNING_QUICK_REACTION_LOSS_PCT")  # -3% triggers emergency

    # Duplicate suppression defaults (can be overridden by runtime config)
    DUP_ACTIVE_WINDOW_SEC: int = Field(default=30, env="DUP_ACTIVE_WINDOW_SEC")
    DUP_ACTIVE_PRICE_DELTA_PCT: float = Field(default=0.003, env="DUP_ACTIVE_PRICE_DELTA_PCT")
    DUP_CLOSED_WINDOW_SEC: int = Field(default=600, env="DUP_CLOSED_WINDOW_SEC")  # Original production default
    DUP_CLOSED_PRICE_DELTA_PCT: float = Field(default=0.008, env="DUP_CLOSED_PRICE_DELTA_PCT")

    # Entry cooldown - AGGRESSIVE SCALPING
    ENTRY_COOLDOWN_SECONDS: int = Field(default=3, env="ENTRY_COOLDOWN_SECONDS")  # 3s for micro-scalping

    # Position limits
    MAX_CONCURRENT_POSITIONS: int = Field(default=9, env="MAX_CONCURRENT_POSITIONS")
    
    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    
    # Rate limiting - INCREASED FOR DEVELOPMENT/DASHBOARD POLLING
    RATE_LIMIT_REQUESTS: int = Field(default=1000, env="RATE_LIMIT_REQUESTS")  # Increased from 100
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
    
    # Config moved to model_config above for Pydantic v2 compatibility


# Global settings instance
_settings: Optional[Settings] = None


INSECURE_SECRET_KEYS = {
    "dev-secret-key-change-in-production",
    "dev-secret-key-change-in-production-must-be-at-least-32-characters-long",
    "changeme",
    "",
}


def _validate_security(settings: "Settings") -> None:
    """Fail fast if production is misconfigured with insecure defaults.

    A publicly-known SECRET_KEY lets anyone forge admin JWTs, so production
    must never boot with one. Runs on every settings construction so it
    cannot be bypassed via reload_settings().
    """
    if settings.is_production and settings.SECRET_KEY in INSECURE_SECRET_KEYS:
        raise RuntimeError(
            "SECRET_KEY is set to an insecure default in a production "
            "environment. Provide a strong SECRET_KEY via environment "
            "variable or SSM before deploying."
        )


def get_settings() -> Settings:
    """Get application settings (singleton pattern)"""
    global _settings
    if _settings is None:
        _settings = Settings()
        _validate_security(_settings)
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)"""
    global _settings
    _settings = Settings()
    _validate_security(_settings)
    return _settings