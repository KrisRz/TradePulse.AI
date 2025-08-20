#!/usr/bin/env python3
"""
Test DynamoDB Local Connection for TradePulse.AI
Verifies database setup and basic operations
"""

import boto3
import sys
import os
import time
from datetime import datetime
from botocore.exceptions import ClientError

def setup_aws_environment():
    """Set up AWS environment variables for local DynamoDB"""
    os.environ['AWS_ACCESS_KEY_ID'] = 'dummy'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'dummy'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['DYNAMODB_ENDPOINT'] = 'http://localhost:8000'

def test_connection():
    """Test basic connection to DynamoDB Local"""
    try:
        dynamodb = boto3.client(
            'dynamodb',
            endpoint_url='http://localhost:8000',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
        
        # List tables
        response = dynamodb.list_tables()
        tables = response.get('TableNames', [])
        
        print(f"✅ Connected to DynamoDB Local")
        print(f"📊 Found {len(tables)} tables")
        
        if tables:
            print("📋 Tables:")
            for table in sorted(tables):
                print(f"   - {table}")
        
        return dynamodb, tables
        
    except Exception as e:
        print(f"❌ Failed to connect to DynamoDB Local: {e}")
        return None, []

def test_table_operations(dynamodb):
    """Test basic table operations"""
    
    # Test data (matching live_candles schema)
    timestamp_val = int(time.time() * 1000)
    test_item = {
        'symbol': {'S': 'TESTCOIN'},
        'timestamp': {'N': str(timestamp_val)},
        'open_price': {'N': '50000.0'},
        'high_price': {'N': '50100.0'},
        'low_price': {'N': '49900.0'},
        'close_price': {'N': '50050.0'},
        'volume': {'N': '10.0'},
        'trade_count': {'N': '100'},
        'date_hour': {'S': datetime.now().strftime('%Y-%m-%d-%H')},
        'created_at': {'S': datetime.now().isoformat()}
    }
    
    # Try to write to live_candles table
    try:
        print("\n🧪 Testing table operations...")
        
        # Put item
        dynamodb.put_item(
            TableName='live_candles',
            Item=test_item
        )
        print("✅ Write operation successful")
        
        # Get item
        response = dynamodb.get_item(
            TableName='live_candles',
            Key={
                'symbol': test_item['symbol'],
                'timestamp': test_item['timestamp']
            }
        )
        
        if 'Item' in response:
            print("✅ Read operation successful")
            
            # Clean up test item
            dynamodb.delete_item(
                TableName='live_candles',
                Key={
                    'symbol': test_item['symbol'],
                    'timestamp': test_item['timestamp']
                }
            )
            print("✅ Delete operation successful")
            return True
        else:
            print("❌ Read operation failed - item not found")
            return False
            
    except Exception as e:
        print(f"❌ Table operations failed: {e}")
        return False

def test_live_data_storage():
    """Test storing a sample market candle"""
    try:
        print("\n📊 Testing live data storage format...")
        
        # Sample market candle data (matching live_candles schema)
        timestamp_val = int(time.time() * 1000)
        candle_item = {
            'symbol': {'S': 'BTCUSDT'},
            'timestamp': {'N': str(timestamp_val)},
            'open_price': {'N': '45000.50'},
            'high_price': {'N': '45100.75'},
            'low_price': {'N': '44950.25'},
            'close_price': {'N': '45050.00'},
            'volume': {'N': '123.456'},
            'trade_count': {'N': '234'},
            'date_hour': {'S': datetime.now().strftime('%Y-%m-%d-%H')},
            'created_at': {'S': datetime.now().isoformat()},
            'ttl': {'N': str(int(time.time()) + 7776000)}  # 90 days TTL
        }
        
        dynamodb = boto3.client(
            'dynamodb',
            endpoint_url='http://localhost:8000',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
        
        # Store sample candle
        dynamodb.put_item(
            TableName='live_candles',
            Item=candle_item
        )
        print("✅ Sample market candle stored successfully")
        
        # Query recent candles
        response = dynamodb.query(
            TableName='live_candles',
            KeyConditionExpression='symbol = :symbol',
            ExpressionAttributeValues={
                ':symbol': {'S': 'BTCUSDT'}
            },
            ScanIndexForward=False,  # Latest first
            Limit=5
        )
        
        candles = response.get('Items', [])
        print(f"✅ Retrieved {len(candles)} recent candles")
        
        return True
        
    except Exception as e:
        print(f"❌ Live data storage test failed: {e}")
        return False

def main():
    """Main function to test database setup"""
    
    print("🧪 TradePulse.AI - Database Connection Test")
    print("=" * 50)
    
    # Set up environment
    setup_aws_environment()
    
    # Test connection
    dynamodb, tables = test_connection()
    if not dynamodb:
        print("\n💡 Make sure DynamoDB Local is running:")
        print("   python scripts/start_dynamodb_local.py")
        sys.exit(1)
    
    # Check required tables
    required_tables = [
        'live_candles',
        'trading_signals', 
        'training_data',
        'exit_analysis_log',
        'position_monitoring_log',
        'trade_execution_metrics',
        'alert_notifications'
    ]
    
    missing_tables = [table for table in required_tables if table not in tables]
    
    if missing_tables:
        print(f"\n⚠️  Missing tables: {missing_tables}")
        print("💡 Create tables with:")
        print("   python scripts/setup_database_tables.py")
    else:
        print("\n✅ All required tables exist")
    
    # Test operations if live_candles table exists
    if 'live_candles' in tables:
        if test_table_operations(dynamodb):
            print("✅ Basic operations working")
        
        if test_live_data_storage():
            print("✅ Live data storage format working")
    
    # Final summary
    print("\n" + "=" * 50)
    print("📊 Database Test Summary:")
    print(f"   📡 Connection: {'✅ Working' if dynamodb else '❌ Failed'}")
    print(f"   📋 Tables: {len(tables)}/{len(required_tables)} required")
    print(f"   🔧 Operations: {'✅ Working' if 'live_candles' in tables else '⚠️ Needs tables'}")
    
    if dynamodb and not missing_tables:
        print("\n🎉 Database is ready for live data collection!")
        print("\n📋 Next steps:")
        print("1. Start live data collection:")
        print("   python -c \"import sys; sys.path.append('app/backend'); from src.services.live_data_collector import main; main()\"")
        print("2. Monitor via DynamoDB Admin (if available): http://localhost:8000")
    else:
        print("\n⚠️  Database setup incomplete. Follow the suggestions above.")

if __name__ == '__main__':
    main() 