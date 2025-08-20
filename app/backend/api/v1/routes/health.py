"""
Health Check API - TradePulse.AI Enterprise
Professional health monitoring endpoints
"""

import time
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
import boto3
from botocore.exceptions import ClientError

from app.backend.core.config import get_settings
from app.backend.core.logging import get_logger
from app.backend.services import MarketDataService

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()

# Initialize market data service
market_data_service = MarketDataService()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "TradePulse.AI Enterprise Backend"
    }

@router.get("/live/bitcoin-price")
async def get_real_live_bitcoin_price() -> Dict[str, Any]:
    """Get REAL live Bitcoin price from Binance API - NO FALLBACKS"""
    try:
        price = await market_data_service.get_current_price("BTCUSDT")
        
        return {
            "symbol": "BTCUSDT", 
            "price": price,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "live_binance_api"
        }
        
    except Exception as e:
        logger.error(f"❌ Real Bitcoin price fetch failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Real Bitcoin price unavailable: {str(e)}"
        )


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with dependency verification"""
    start_time = time.time()
    health_status = {
        "status": "healthy",
        "service": "tradepulse-api",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "checks": {},
        "response_time_ms": 0
    }
    
    # Check DynamoDB connectivity
    dynamodb_status = await check_dynamodb_health()
    health_status["checks"]["dynamodb"] = dynamodb_status
    
    # Check S3 connectivity (for ML models)
    s3_status = await check_s3_health()
    health_status["checks"]["s3"] = s3_status
    
    # Overall status
    all_healthy = all(
        check["status"] == "healthy" 
        for check in health_status["checks"].values()
    )
    
    if not all_healthy:
        health_status["status"] = "unhealthy"
    
    # Calculate response time
    health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
    
    return health_status


async def check_dynamodb_health() -> Dict[str, Any]:
    """Check DynamoDB connectivity and table status"""
    try:
        # Initialize DynamoDB client
        if settings.DYNAMODB_ENDPOINT:
            # Local development
            dynamodb = boto3.client(
                'dynamodb',
                endpoint_url=settings.DYNAMODB_ENDPOINT,
                region_name=settings.DYNAMODB_REGION,
                aws_access_key_id='dummy',
                aws_secret_access_key='dummy'
            )
        else:
            # Production
            dynamodb = boto3.client('dynamodb', region_name=settings.AWS_REGION)
        
        # Try to list tables
        response = dynamodb.list_tables()
        
        # Check if required tables exist
        existing_tables = response.get('TableNames', [])
        required_tables = [
            settings.USERS_TABLE,
            settings.SIGNALS_TABLE,
            settings.TRADES_TABLE,
            settings.PORTFOLIOS_TABLE,
            settings.ANALYTICS_TABLE,
        ]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            return {
                "status": "degraded",
                "message": f"Missing tables: {missing_tables}",
                "existing_tables": len(existing_tables),
                "required_tables": len(required_tables)
            }
        
        return {
            "status": "healthy",
            "message": "All required tables exist",
            "tables_count": len(existing_tables)
        }
        
    except ClientError as e:
        logger.error("dynamodb_health_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "message": f"DynamoDB error: {e.response['Error']['Code']}",
            "error": str(e)
        }
    except Exception as e:
        logger.error("dynamodb_health_check_error", error=str(e))
        return {
            "status": "unhealthy",
            "message": "DynamoDB connectivity failed",
            "error": str(e)
        }


async def check_s3_health() -> Dict[str, Any]:
    """Check S3 connectivity for ML model storage"""
    try:
        s3 = boto3.client('s3', region_name=settings.AWS_REGION)
        
        # Try to head the model bucket
        s3.head_bucket(Bucket=settings.MODEL_BUCKET)
        
        return {
            "status": "healthy",
            "message": "S3 model bucket accessible",
            "bucket": settings.MODEL_BUCKET
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            return {
                "status": "degraded",
                "message": f"Model bucket not found: {settings.MODEL_BUCKET}",
                "error": error_code
            }
        else:
            logger.error("s3_health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "message": f"S3 error: {error_code}",
                "error": str(e)
            }
    except Exception as e:
        logger.error("s3_health_check_error", error=str(e))
        return {
            "status": "unhealthy",
            "message": "S3 connectivity failed",
            "error": str(e)
        }


@router.get("/health/trading")
async def trading_system_health() -> Dict[str, Any]:
    """Check trading system specific health"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "trading_checks": {}
    }
    
    # Check ML models availability
    ml_status = await check_ml_models_health()
    health_status["trading_checks"]["ml_models"] = ml_status
    
    # Check market data connectivity
    market_data_status = await check_market_data_health()
    health_status["trading_checks"]["market_data"] = market_data_status
    
    # Overall trading system status
    all_healthy = all(
        check["status"] == "healthy" 
        for check in health_status["trading_checks"].values()
    )
    
    if not all_healthy:
        health_status["status"] = "degraded"
    
    return health_status


async def check_ml_models_health() -> Dict[str, Any]:
    """Check ML models availability and status"""
    try:
        # TODO: Implement actual ML model health check
        # For now, just check if model bucket is accessible
        s3 = boto3.client('s3', region_name=settings.AWS_REGION)
        
        # List objects in model bucket
        response = s3.list_objects_v2(
            Bucket=settings.MODEL_BUCKET,
            Prefix=f"models/{settings.MODEL_VERSION}/",
            MaxKeys=10
        )
        
        model_files = response.get('Contents', [])
        
        return {
            "status": "healthy" if model_files else "degraded",
            "message": f"Found {len(model_files)} model files",
            "model_version": settings.MODEL_VERSION,
            "model_files_count": len(model_files)
        }
        
    except Exception as e:
        logger.error("ml_models_health_check_error", error=str(e))
        return {
            "status": "unhealthy",
            "message": "ML models health check failed",
            "error": str(e)
        }


async def check_real_market_data_health() -> Dict[str, Any]:
    """Check REAL market data connectivity (Binance API) - NO MOCKS"""
    try:
        # Real Binance API health check
        price = await market_data_service.get_current_price("BTCUSDT")
        
        return {
            "status": "healthy",
            "message": "Real Binance API connectivity operational",
            "current_btc_price": price,
            "data_source": "live_binance_api",
            "last_check": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("real_market_data_health_check_error", error=str(e))
        return {
            "status": "unhealthy", 
            "message": "Real Binance API connectivity failed",
            "error": str(e),
            "last_check": datetime.utcnow().isoformat()
        } 