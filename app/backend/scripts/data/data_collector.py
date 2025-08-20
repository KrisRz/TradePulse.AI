"""
TradePulse.AI - Data Collector Lambda Handler
24/7 Market Data Collection for Real-Time Trading
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(event, context):
    """
    Lambda handler for 24/7 market data collection
    Triggered by EventBridge every 1 minute
    """
    try:
        logger.info("🔄 Data Collector Lambda triggered")
        
        # Import services after path setup
        from app.services.live_market_data import LiveMarketDataService
        from app.services.database import DatabaseService
        
        # Initialize services
        market_service = LiveMarketDataService()
        db_service = DatabaseService()
        
        # Collect current market data
        symbols = ['BTCUSDT', 'ETHUSDT']  # Focus on major pairs
        collected_data = []
        
        for symbol in symbols:
            try:
                # Get current price and candle data
                price_data = market_service.get_current_price(symbol)
                candle_data = market_service.get_latest_candles(symbol, '1m', 5)
                
                if price_data and candle_data:
                    # Store in DynamoDB
                    market_record = {
                        'symbol': symbol,
                        'timestamp': int(datetime.now(timezone.utc).timestamp()),
                        'price': float(price_data.get('price', 0)),
                        'volume': float(price_data.get('volume', 0)),
                        'change_24h': float(price_data.get('priceChangePercent', 0)),
                        'candles': candle_data[:5],  # Last 5 minutes
                        'collected_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Store in market_data table
                    db_service.put_item('market_data', market_record)
                    collected_data.append(symbol)
                    
                    logger.info(f"✅ Collected data for {symbol}: ${price_data.get('price', 'N/A')}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to collect data for {symbol}: {e}")
                continue
        
        # Return success response
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'success',
                'symbols_collected': collected_data,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'function': 'data_collector'
            })
        }
        
        logger.info(f"✅ Data collection completed for {len(collected_data)} symbols")
        return response
        
    except Exception as e:
        logger.error(f"❌ Data Collector Lambda error: {e}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'message': str(e),
                'function': 'data_collector',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        }

# For local testing
if __name__ == "__main__":
    test_event = {"source": "test"}
    test_context = {"function_name": "test"}
    result = handler(test_event, test_context)
    print(json.dumps(result, indent=2))
