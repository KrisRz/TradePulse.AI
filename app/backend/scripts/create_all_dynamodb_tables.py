#!/usr/bin/env python3
"""
Complete DynamoDB Tables Setup for TradePulse.AI
Creates ALL required tables based on the database schemas
"""

import boto3
import os
import sys
import time
from botocore.exceptions import ClientError
from typing import Dict, Any, List

# Add backend to path
sys.path.append('/Applications/Projects/TradePulse.AI/app/backend')

# Set environment for DynamoDB Local
os.environ['ENVIRONMENT'] = 'development'
os.environ['DYNAMODB_ENDPOINT'] = 'http://localhost:8000'
os.environ['AWS_ACCESS_KEY_ID'] = 'dummy'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'dummy'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

def create_dynamodb_client():
    """Create DynamoDB client for local instance"""
    return boto3.client(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        region_name='us-east-1',
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

def create_table_from_schema(client, schema: Dict[str, Any]):
    """Create table from schema definition"""
    table_name = schema['TableName']
    
    if table_exists(client, table_name):
        print(f"✅ Table '{table_name}' already exists")
        return True
    
    try:
        print(f"🔧 Creating table: {table_name}")
        response = client.create_table(**schema)
        print(f"✅ Created table '{table_name}'")
        return True
        
    except ClientError as e:
        print(f"❌ Error creating table '{table_name}': {e}")
        return False

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
                time.sleep(2)
            else:
                print(f"⚠️ Table '{table_name}' status: {status}")
                time.sleep(2)
                
        except ClientError as e:
            print(f"❌ Error checking table status: {e}")
            return False
    
    print(f"❌ Timeout waiting for table '{table_name}' to become active")
    return False

def convert_billing_mode_to_provisioned(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Convert PAY_PER_REQUEST schemas to ProvisionedThroughput for DynamoDB Local"""
    if schema.get('BillingMode') == 'PAY_PER_REQUEST':
        # Remove BillingMode and add ProvisionedThroughput
        schema = schema.copy()
        del schema['BillingMode']
        schema['ProvisionedThroughput'] = {
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
        
        # Add provisioned throughput to GSIs
        if 'GlobalSecondaryIndexes' in schema:
            for gsi in schema['GlobalSecondaryIndexes']:
                if 'BillingMode' in gsi:
                    del gsi['BillingMode']
                if 'ProvisionedThroughput' not in gsi:
                    gsi['ProvisionedThroughput'] = {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
    
    # Remove features not supported by DynamoDB Local
    if 'StreamSpecification' in schema:
        del schema['StreamSpecification']
    if 'TimeToLiveSpecification' in schema:
        del schema['TimeToLiveSpecification']
    if 'Tags' in schema:
        del schema['Tags']
    
    return schema

def get_all_table_schemas() -> List[Dict[str, Any]]:
    """Get all table schemas from the database module"""
    try:
        from core.database import TableSchemas
        schemas = TableSchemas()
        
        # Get all schema methods
        schema_methods = [
            schemas.get_live_candles_schema(),
            schemas.get_signals_schema(),
            schemas.get_training_data_schema(),
            schemas.get_exit_analysis_log_schema(),
            schemas.get_position_monitoring_log_schema(),
            schemas.get_trade_execution_metrics_schema(),
            schemas.get_alert_notifications_schema(),
            schemas.get_users_schema(),
            schemas.get_virtual_portfolios_schema(),
            schemas.get_ai_vs_random_experiments_schema(),
            schemas.get_signal_accuracy_tracking_schema(),
            schemas.get_trading_patterns_schema(),
            schemas.get_user_performance_showcases_schema(),
            schemas.get_model_performance_metrics_schema(),
            schemas.get_users_enhanced_schema(),
            schemas.get_invitations_schema(),
            schemas.get_user_activity_logs_schema(),
            schemas.get_messages_schema(),
            schemas.get_message_deliveries_schema(),
            schemas.get_announcements_schema(),
            schemas.get_user_notification_preferences_schema(),
            schemas.get_notification_templates_schema()
        ]
        
        # Convert all schemas for DynamoDB Local compatibility
        converted_schemas = []
        for schema in schema_methods:
            converted_schemas.append(convert_billing_mode_to_provisioned(schema))
        
        # Add portfolio tables
        portfolio_schemas = get_portfolio_table_schemas()
        converted_schemas.extend(portfolio_schemas)
        
        return converted_schemas
        
    except Exception as e:
        print(f"❌ Error importing schemas: {e}")
        # Fallback to hardcoded essential schemas
        return get_essential_table_schemas()

def get_portfolio_table_schemas() -> List[Dict[str, Any]]:
    """Get portfolio-specific table schemas"""
    return [
        {
            'TableName': 'portfolio_positions',
            'KeySchema': [
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'position_id', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'position_id', 'AttributeType': 'S'},
                {'AttributeName': 'symbol', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'symbol-index',
                    'KeySchema': [{'AttributeName': 'symbol', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                },
                {
                    'IndexName': 'status-index',
                    'KeySchema': [{'AttributeName': 'status', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            'ProvisionedThroughput': {'ReadCapacityUnits': 10, 'WriteCapacityUnits': 10}
        },
        {
            'TableName': 'portfolio_closed_positions',
            'KeySchema': [
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'position_id', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'position_id', 'AttributeType': 'S'},
                {'AttributeName': 'symbol', 'AttributeType': 'S'},
                {'AttributeName': 'closed_at', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'symbol-index',
                    'KeySchema': [{'AttributeName': 'symbol', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                },
                {
                    'IndexName': 'closed-at-index',
                    'KeySchema': [{'AttributeName': 'closed_at', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            'ProvisionedThroughput': {'ReadCapacityUnits': 10, 'WriteCapacityUnits': 10}
        }
    ]

def get_essential_table_schemas() -> List[Dict[str, Any]]:
    """Essential table schemas as fallback"""
    return [
        {
            'TableName': 'live_candles',
            'KeySchema': [
                {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'symbol', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'},
                {'AttributeName': 'interval', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'interval-timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'interval', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 10, 'WriteCapacityUnits': 10}
                }
            ],
            'ProvisionedThroughput': {'ReadCapacityUnits': 25, 'WriteCapacityUnits': 25}
        },
        {
            'TableName': 'signals',
            'KeySchema': [
                {'AttributeName': 'signal_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'signal_id', 'AttributeType': 'S'},
                {'AttributeName': 'symbol', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'},
                {'AttributeName': 'signal_type', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'symbol-timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 10, 'WriteCapacityUnits': 10}
                },
                {
                    'IndexName': 'signal-type-index',
                    'KeySchema': [{'AttributeName': 'signal_type', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            'ProvisionedThroughput': {'ReadCapacityUnits': 15, 'WriteCapacityUnits': 15}
        },
        {
            'TableName': 'users',
            'KeySchema': [
                {'AttributeName': 'user_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'email', 'AttributeType': 'S'},
                {'AttributeName': 'username', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'email-index',
                    'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                },
                {
                    'IndexName': 'username-index',
                    'KeySchema': [{'AttributeName': 'username', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            'ProvisionedThroughput': {'ReadCapacityUnits': 10, 'WriteCapacityUnits': 10}
        },
        {
            'TableName': 'tradepulse-virtual-portfolios',
            'KeySchema': [
                {'AttributeName': 'user_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'created-at-index',
                    'KeySchema': [{'AttributeName': 'created_at', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            ],
            'ProvisionedThroughput': {'ReadCapacityUnits': 10, 'WriteCapacityUnits': 10}
        }
    ]

def main():
    """Create all required DynamoDB tables"""
    print("🚀 Creating ALL DynamoDB tables for TradePulse.AI...")
    
    try:
        client = create_dynamodb_client()
        
        # Test connection
        client.list_tables()
        print("✅ Connected to DynamoDB Local")
        
        # Get all table schemas
        print("📋 Loading table schemas...")
        all_schemas = get_all_table_schemas()
        print(f"📊 Found {len(all_schemas)} tables to create")
        
        # Create all tables
        created_tables = []
        failed_tables = []
        
        for schema in all_schemas:
            table_name = schema.get('TableName', 'unknown')
            if create_table_from_schema(client, schema):
                created_tables.append(table_name)
            else:
                failed_tables.append(table_name)
        
        # Wait for all tables to become active
        print("\n⏳ Waiting for all tables to become active...")
        for table_name in created_tables:
            if table_exists(client, table_name):
                wait_for_table_active(client, table_name)
        
        # List all tables
        print("\n📊 Current DynamoDB tables:")
        response = client.list_tables()
        for table in sorted(response['TableNames']):
            print(f"  ✅ {table}")
        
        # Summary
        print(f"\n🎉 Table creation complete!")
        print(f"✅ Successfully created: {len(created_tables)} tables")
        if failed_tables:
            print(f"❌ Failed to create: {len(failed_tables)} tables: {failed_tables}")
        
        print(f"📊 Total tables in DynamoDB Local: {len(response['TableNames'])}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
