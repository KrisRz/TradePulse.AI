#!/usr/bin/env python3
"""
Simple DynamoDB Table Setup for TradePulse.AI
Creates basic tables for live trading without complex imports
"""

import boto3
import os
from botocore.exceptions import ClientError

def create_dynamodb_client():
    """Create DynamoDB client for local development"""
    return boto3.client(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        region_name='us-east-1',
        aws_access_key_id='dummy',
        aws_secret_access_key='dummy'
    )

def create_table(dynamodb, table_name, key_schema, attribute_definitions):
    """Create a DynamoDB table"""
    try:
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"✅ Created table: {table_name}")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table {table_name} already exists")
            return True
        else:
            print(f"❌ Failed to create table {table_name}: {e}")
            return False

def main():
    """Setup basic DynamoDB tables"""
    print("🔧 TradePulse.AI - DynamoDB Table Setup")
    print("=" * 50)
    
    dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        region_name='us-east-1',
        aws_access_key_id='dummy',
        aws_secret_access_key='dummy'
    )
    
    # Test connection
    try:
        dynamodb_client = boto3.client(
            'dynamodb',
            endpoint_url='http://localhost:8000',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
        response = dynamodb_client.list_tables()
        print(f"✅ Connected to DynamoDB Local")
        print(f"📊 Existing tables: {response.get('TableNames', [])}")
    except Exception as e:
        print(f"❌ Failed to connect to DynamoDB Local: {e}")
        print("💡 Make sure DynamoDB Local is running on port 8000")
        return
    
    # Define basic tables for live trading
    tables = [
        {
            'name': 'live_candles',
            'key_schema': [
                {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            'attributes': [
                {'AttributeName': 'symbol', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'N'}
            ]
        },
        {
            'name': 'trading_signals',
            'key_schema': [
                {'AttributeName': 'timestamp', 'KeyType': 'HASH'},
                {'AttributeName': 'signal_id', 'KeyType': 'RANGE'}
            ],
            'attributes': [
                {'AttributeName': 'timestamp', 'AttributeType': 'N'},
                {'AttributeName': 'signal_id', 'AttributeType': 'S'}
            ]
        },
        {
            'name': 'virtual_portfolios',
            'key_schema': [
                {'AttributeName': 'portfolio_id', 'KeyType': 'HASH'}
            ],
            'attributes': [
                {'AttributeName': 'portfolio_id', 'AttributeType': 'S'}
            ]
        },
        {
            'name': 'virtual_positions',
            'key_schema': [
                {'AttributeName': 'position_id', 'KeyType': 'HASH'}
            ],
            'attributes': [
                {'AttributeName': 'position_id', 'AttributeType': 'S'}
            ]
        },
        {
            'name': 'virtual_trades',
            'key_schema': [
                {'AttributeName': 'trade_id', 'KeyType': 'HASH'}
            ],
            'attributes': [
                {'AttributeName': 'trade_id', 'AttributeType': 'S'}
            ]
        }
    ]
    
    # Create tables
    success_count = 0
    for table in tables:
        if create_table(dynamodb, table['name'], table['key_schema'], table['attributes']):
            success_count += 1
    
    print(f"\n🎉 Setup complete! {success_count}/{len(tables)} tables ready")
    print("\n📋 Next steps:")
    print("1. Start live data collection")
    print("2. Test database connection")
    print("3. Begin live trading")

if __name__ == '__main__':
    main() 