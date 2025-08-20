#!/usr/bin/env python3
"""
TradePulse.AI - Database Table Setup
Creates all required DynamoDB tables for the trading system
"""

import boto3
import time
from datetime import datetime
from botocore.exceptions import ClientError

# DynamoDB connection
dynamodb = boto3.client(
    'dynamodb',
    endpoint_url='http://localhost:8000',
    region_name='eu-west-2',
    aws_access_key_id='fake',
    aws_secret_access_key='fake'
)

def create_table_with_retry(table_name, table_definition, max_retries=3):
    """Create a table with retry logic"""
    for attempt in range(max_retries):
        try:
            print(f"Creating table: {table_name} (attempt {attempt + 1})")
            response = dynamodb.create_table(**table_definition)
            print(f"✅ Created: {table_name}")
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                print(f"✅ Table {table_name} already exists")
                return None
            else:
                print(f"❌ Error creating {table_name}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise

def setup_live_candles_table():
    """Table for live Bitcoin price data"""
    table_definition = {
        'TableName': 'live_candles',
        'KeySchema': [
            {'AttributeName': 'symbol', 'KeyType': 'HASH'},  # BTCUSDT
            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}  # Unix timestamp
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'symbol', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'N'},
            {'AttributeName': 'date_hour', 'AttributeType': 'S'}  # For GSI
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'DateHourIndex',
                'KeySchema': [
                    {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                    {'AttributeName': 'date_hour', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    }
    return create_table_with_retry('live_candles', table_definition)

def setup_trading_signals_table():
    """Table for AI trading signals"""
    table_definition = {
        'TableName': 'trading_signals',
        'KeySchema': [
            {'AttributeName': 'signal_id', 'KeyType': 'HASH'},
            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'signal_id', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'N'},
            {'AttributeName': 'symbol', 'AttributeType': 'S'},
            {'AttributeName': 'created_date', 'AttributeType': 'S'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'SymbolDateIndex',
                'KeySchema': [
                    {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_date', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    }
    return create_table_with_retry('trading_signals', table_definition)

def setup_virtual_portfolios_table():
    """Table for virtual trading portfolios"""
    table_definition = {
        'TableName': 'virtual_portfolios',
        'KeySchema': [
            {'AttributeName': 'user_id', 'KeyType': 'HASH'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'user_id', 'AttributeType': 'S'},
            {'AttributeName': 'status', 'AttributeType': 'S'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'StatusIndex',
                'KeySchema': [
                    {'AttributeName': 'status', 'KeyType': 'HASH'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    }
    return create_table_with_retry('virtual_portfolios', table_definition)

def setup_virtual_positions_table():
    """Table for active trading positions"""
    table_definition = {
        'TableName': 'virtual_positions',
        'KeySchema': [
            {'AttributeName': 'position_id', 'KeyType': 'HASH'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'position_id', 'AttributeType': 'S'},
            {'AttributeName': 'user_id', 'AttributeType': 'S'},
            {'AttributeName': 'status', 'AttributeType': 'S'},
            {'AttributeName': 'symbol', 'AttributeType': 'S'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'UserStatusIndex',
                'KeySchema': [
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'status', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            },
            {
                'IndexName': 'SymbolStatusIndex',
                'KeySchema': [
                    {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                    {'AttributeName': 'status', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    }
    return create_table_with_retry('virtual_positions', table_definition)

def setup_virtual_trades_table():
    """Table for completed trades"""
    table_definition = {
        'TableName': 'virtual_trades',
        'KeySchema': [
            {'AttributeName': 'trade_id', 'KeyType': 'HASH'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'trade_id', 'AttributeType': 'S'},
            {'AttributeName': 'user_id', 'AttributeType': 'S'},
            {'AttributeName': 'created_at', 'AttributeType': 'S'},
            {'AttributeName': 'symbol', 'AttributeType': 'S'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'UserDateIndex',
                'KeySchema': [
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            },
            {
                'IndexName': 'SymbolDateIndex',
                'KeySchema': [
                    {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    }
    return create_table_with_retry('virtual_trades', table_definition)

def verify_tables():
    """Verify all tables are created and active"""
    required_tables = [
        'live_candles',
        'trading_signals', 
        'virtual_portfolios',
        'virtual_positions',
        'virtual_trades'
    ]
    
    print("\n🔍 Verifying tables...")
    for table_name in required_tables:
        try:
            response = dynamodb.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']
            item_count = response['Table']['ItemCount']
            print(f"✅ {table_name}: {status} ({item_count} items)")
        except ClientError as e:
            print(f"❌ {table_name}: {e.response['Error']['Message']}")
    
    return True

def create_sample_data():
    """Create sample data for testing"""
    print("\n📊 Creating sample data...")
    
    # Create AI trader portfolio
    dynamodb_resource = boto3.resource(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        region_name='eu-west-2',
        aws_access_key_id='fake',
        aws_secret_access_key='fake'
    )
    
    try:
        # Sample portfolio
        portfolios_table = dynamodb_resource.Table('virtual_portfolios')
        portfolios_table.put_item(Item={
            'user_id': 'ai_trader',
            'balance': 10000.0,
            'equity': 10000.0,
            'available_balance': 10000.0,
            'margin_used': 0.0,
            'total_pnl': 0.0,
            'daily_pnl': 0.0,
            'trade_count': 0,
            'win_count': 0,
            'loss_count': 0,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        })
        print("✅ Created AI trader portfolio")
        
        # Sample live candle
        candles_table = dynamodb_resource.Table('live_candles')
        current_timestamp = int(time.time())
        candles_table.put_item(Item={
            'symbol': 'BTCUSDT',
            'timestamp': current_timestamp,
            'open_price': 117500.0,
            'high_price': 117600.0,
            'low_price': 117400.0,
            'close_price': 117550.0,
            'volume': 150.5,
            'trade_count': 1250,
            'date_hour': datetime.utcnow().strftime('%Y-%m-%d-%H'),
            'created_at': datetime.utcnow().isoformat(),
            'ttl': current_timestamp + (7 * 24 * 60 * 60)  # 7 days TTL
        })
        print("✅ Created sample Bitcoin price data")
        
    except Exception as e:
        print(f"⚠️ Error creating sample data: {e}")

def main():
    """Main function to set up all database tables"""
    print("🚀 TradePulse.AI - Database Setup")
    print("=" * 50)
    
    try:
        # Test connection
        response = dynamodb.list_tables()
        print(f"✅ Connected to DynamoDB Local")
        print(f"📋 Existing tables: {response.get('TableNames', [])}")
        
        # Create all tables
        print("\n🏗️ Creating tables...")
        setup_live_candles_table()
        setup_trading_signals_table()
        setup_virtual_portfolios_table()
        setup_virtual_positions_table()
        setup_virtual_trades_table()
        
        # Wait for tables to become active
        print("\n⏳ Waiting for tables to become active...")
        time.sleep(3)
        
        # Verify tables
        verify_tables()
        
        # Create sample data
        create_sample_data()
        
        print("\n🎉 Database setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Test connection: python scripts/test_database_connection.py")
        print("2. Start live data collection: python scripts/test_live_data_collection.py")
        print("3. Run integration test: python scripts/test_full_integration.py")
        
    except ClientError as e:
        print(f"❌ Database connection failed: {e}")
        print("🔧 Make sure DynamoDB Local is running on port 8000")
    except Exception as e:
        print(f"❌ Setup failed: {e}")

if __name__ == '__main__':
    main() 