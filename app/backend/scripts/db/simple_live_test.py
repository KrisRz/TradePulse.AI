#!/usr/bin/env python3
"""
Simple Live Database Test for TradePulse.AI
Test live data collection and database integration
"""

import boto3
import time
import json
from datetime import datetime

def test_dynamodb_connection():
    """Test DynamoDB Local connection"""
    try:
        dynamodb = boto3.client(
            'dynamodb',
            endpoint_url='http://localhost:8001',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
        
        # List tables
        response = dynamodb.list_tables()
        tables = response.get('TableNames', [])
        
        print(f"✅ Connected to DynamoDB Local")
        print(f"📊 Found {len(tables)} tables: {tables}")
        
        return dynamodb, True
        
    except Exception as e:
        print(f"❌ DynamoDB connection failed: {e}")
        return None, False

def test_live_candles_table(dynamodb):
    """Test live_candles table operations"""
    try:
        table_name = 'live_candles'
        
        # Check table exists
        response = dynamodb.describe_table(TableName=table_name)
        print(f"✅ Table '{table_name}' exists")
        
        # Scan for recent data
        response = dynamodb.scan(
            TableName=table_name,
            Limit=5
        )
        
        items = response.get('Items', [])
        print(f"📊 Found {len(items)} candle records")
        
        if items:
            print("🕒 Recent candles:")
            for item in items:
                timestamp = int(item['timestamp']['N'])
                dt = datetime.fromtimestamp(timestamp / 1000)
                symbol = item['symbol']['S']
                close = float(item['close']['N'])
                print(f"   {dt.strftime('%Y-%m-%d %H:%M:%S')} - {symbol}: ${close:,.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to test {table_name}: {e}")
        return False

def test_trading_signals_table(dynamodb):
    """Test trading_signals table operations"""
    try:
        table_name = 'trading_signals'
        
        # Check table exists
        response = dynamodb.describe_table(TableName=table_name)
        print(f"✅ Table '{table_name}' exists")
        
        # Scan for recent data
        response = dynamodb.scan(
            TableName=table_name,
            Limit=3
        )
        
        items = response.get('Items', [])
        print(f"📊 Found {len(items)} signal records")
        
        if items:
            print("🤖 Recent signals:")
            for item in items:
                timestamp = int(item['timestamp']['N'])
                dt = datetime.fromtimestamp(timestamp / 1000)
                signal_id = item['signal_id']['S']
                print(f"   {dt.strftime('%Y-%m-%d %H:%M:%S')} - {signal_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to test {table_name}: {e}")
        return False

def main():
    """Run comprehensive live database test"""
    print("🧪 TradePulse.AI - Live Database Integration Test")
    print("=" * 55)
    
    # Test DynamoDB connection
    dynamodb, connected = test_dynamodb_connection()
    if not connected:
        print("\n💡 Make sure DynamoDB Local is running on port 8001")
        return
    
    print()
    
    # Test tables
    success_count = 0
    
    if test_live_candles_table(dynamodb):
        success_count += 1
    
    print()
    
    if test_trading_signals_table(dynamodb):
        success_count += 1
    
    print()
    print("=" * 55)
    print(f"🎉 Test Results: {success_count}/2 tests passed")
    
    if success_count == 2:
        print("✅ Live database integration is working!")
        print("\n📋 Next steps:")
        print("1. Live data collection should be running")
        print("2. Check admin dashboard: http://localhost:8000/docs")
        print("3. Monitor live trading performance")
    else:
        print("⚠️  Some tests failed - check configuration")

if __name__ == '__main__':
    main() 