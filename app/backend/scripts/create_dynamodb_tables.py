#!/usr/bin/env python3
"""
Create DynamoDB Tables for TradePulse.AI
Professional table creation with proper schemas and indexes
"""

import boto3
import os
import sys
from botocore.exceptions import ClientError
import time

# Set environment for DynamoDB Local
os.environ['ENVIRONMENT'] = 'development'
os.environ['DYNAMODB_ENDPOINT'] = 'http://localhost:8000'
os.environ['AWS_ACCESS_KEY_ID'] = 'dummy'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'dummy'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-2'

def create_dynamodb_client():
    """Create DynamoDB client for local instance"""
    return boto3.client(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        region_name='eu-west-2',
        aws_access_key_id='dummy',
        aws_secret_access_key='dummy'
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

def create_portfolio_positions_table(client):
    """Create portfolio_positions table"""
    table_name = 'portfolio_positions'
    
    if table_exists(client, table_name):
        print(f"✅ Table '{table_name}' already exists")
        return
    
    try:
        response = client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'user_id',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'position_id',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'position_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'symbol',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'status',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'symbol-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'symbol',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
                {
                    'IndexName': 'status-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'status',
                            'KeyType': 'HASH'
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
        print(f"✅ Created table '{table_name}'")
        
    except ClientError as e:
        print(f"❌ Error creating table '{table_name}': {e}")

def create_portfolio_closed_positions_table(client):
    """Create portfolio_closed_positions table"""
    table_name = 'portfolio_closed_positions'
    
    if table_exists(client, table_name):
        print(f"✅ Table '{table_name}' already exists")
        return
    
    try:
        response = client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'user_id',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'position_id',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'position_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'symbol',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'closed_at',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'symbol-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'symbol',
                            'KeyType': 'HASH'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                },
                {
                    'IndexName': 'closed-at-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'closed_at',
                            'KeyType': 'HASH'
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
        print(f"✅ Created table '{table_name}'")
        
    except ClientError as e:
        print(f"❌ Error creating table '{table_name}': {e}")

def create_virtual_portfolios_table(client):
    """Create tradepulse-virtual-portfolios table"""
    table_name = 'tradepulse-virtual-portfolios'
    
    if table_exists(client, table_name):
        print(f"✅ Table '{table_name}' already exists")
        return
    
    try:
        response = client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'user_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'user_id',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'created_at',
                    'AttributeType': 'S'
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'created-at-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'created_at',
                            'KeyType': 'HASH'
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
        print(f"✅ Created table '{table_name}'")
        
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
    """Create all required DynamoDB tables"""
    print("🚀 Creating DynamoDB tables for TradePulse.AI...")
    
    try:
        client = create_dynamodb_client()
        
        # Test connection
        client.list_tables()
        print("✅ Connected to DynamoDB Local")
        
        # Create tables
        tables_to_create = [
            ('portfolio_positions', create_portfolio_positions_table),
            ('portfolio_closed_positions', create_portfolio_closed_positions_table),
            ('tradepulse-virtual-portfolios', create_virtual_portfolios_table)
        ]
        
        for table_name, create_func in tables_to_create:
            print(f"\n📋 Creating table: {table_name}")
            create_func(client)
            
            # Wait for table to become active
            if not table_exists(client, table_name):
                continue
                
            wait_for_table_active(client, table_name)
        
        # List all tables
        print("\n📊 Current tables:")
        response = client.list_tables()
        for table in response['TableNames']:
            print(f"  ✅ {table}")
        
        print("\n🎉 All DynamoDB tables created successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

