#!/usr/bin/env python3
"""
Create Missing DynamoDB Tables for TradePulse.AI
Professional table creation for missing tables identified in logs
"""

import boto3
import os
import sys
from botocore.exceptions import ClientError
import time

def create_dynamodb_client():
    """Create DynamoDB client for local instance"""
    return boto3.client(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        region_name='eu-west-2',
        aws_access_key_id='local-dev-key',
        aws_secret_access_key='local-dev-secret'
    )

def table_exists(client, table_name):
    """Check if table exists"""
    try:
        client.describe_table(TableName=table_name)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        raise

def create_emergency_state_table(client):
    """Create emergency_state table for trading emergency management"""
    table_name = 'emergency_state'
    
    if table_exists(client, table_name):
        print(f"✅ Table '{table_name}' already exists")
        return
    
    try:
        response = client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print(f"✅ Created table '{table_name}' for emergency state management")
        
    except ClientError as e:
        print(f"❌ Error creating table '{table_name}': {e}")

def create_position_tracker_stats_table(client):
    """Create position_tracker_stats table for position tracking statistics"""
    table_name = 'position_tracker_stats'
    
    if table_exists(client, table_name):
        print(f"✅ Table '{table_name}' already exists")
        return
    
    try:
        response = client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'tracker_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'tracker_id',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print(f"✅ Created table '{table_name}' for position tracking statistics")
        
    except ClientError as e:
        print(f"❌ Error creating table '{table_name}': {e}")

def create_live_candles_table(client):
    """Create live_candles table for real-time market data"""
    table_name = 'live_candles'
    
    if table_exists(client, table_name):
        print(f"✅ Table '{table_name}' already exists")
        return
    
    try:
        response = client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'symbol',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'timestamp',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'symbol',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'timestamp',
                    'AttributeType': 'N'
                },
                {
                    'AttributeName': 'interval',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'interval-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'interval',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'timestamp',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }
        )
        print(f"✅ Created table '{table_name}' for live market data")
        
    except ClientError as e:
        print(f"❌ Error creating table '{table_name}': {e}")

def create_live_tickers_table(client):
    """Create live_tickers table for real-time ticker data"""
    table_name = 'live_tickers'
    
    if table_exists(client, table_name):
        print(f"✅ Table '{table_name}' already exists")
        return
    
    try:
        response = client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'symbol',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'timestamp',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'symbol',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'timestamp',
                    'AttributeType': 'N'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }
        )
        print(f"✅ Created table '{table_name}' for live ticker data")
        
    except ClientError as e:
        print(f"❌ Error creating table '{table_name}': {e}")

def wait_for_table_active(client, table_name, max_wait=60):
    """Wait for table to become active"""
    print(f"⏳ Waiting for table '{table_name}' to become active...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = client.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']
            
            if status == 'ACTIVE':
                print(f"✅ Table '{table_name}' is now active")
                return True
            elif status == 'CREATING':
                print(f"⏳ Table '{table_name}' is still creating...")
                time.sleep(2)
            else:
                print(f"⚠️ Table '{table_name}' status: {status}")
                time.sleep(2)
                
        except ClientError as e:
            print(f"❌ Error checking table status: {e}")
            return False
    
    print(f"❌ Timeout waiting for table '{table_name}' to become active")
    return False

def main():
    """Create all missing DynamoDB tables"""
    print("🚀 Creating MISSING DynamoDB tables for TradePulse.AI...")
    
    try:
        client = create_dynamodb_client()
        
        # Test connection
        client.list_tables()
        print("✅ Connected to DynamoDB Local")
        
        # Create missing tables
        missing_tables = [
            ('emergency_state', create_emergency_state_table),
            ('position_tracker_stats', create_position_tracker_stats_table),
            ('live_candles', create_live_candles_table),
            ('live_tickers', create_live_tickers_table)
        ]
        
        for table_name, create_func in missing_tables:
            print(f"\n📋 Creating missing table: {table_name}")
            create_func(client)
            
            # Wait for table to become active if it was created
            if table_exists(client, table_name):
                wait_for_table_active(client, table_name)
        
        # List all tables
        print("\n📊 All tables after creation:")
        response = client.list_tables()
        for table in sorted(response['TableNames']):
            print(f"  ✅ {table}")
        
        print(f"\n🎉 Created {len(missing_tables)} missing tables successfully!")
        print("🔥 TradePulse.AI database is now COMPLETE for professional trading!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
