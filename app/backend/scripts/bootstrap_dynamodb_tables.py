#!/usr/bin/env python3
"""
Bootstrap script for DynamoDB Local table creation
Creates all required tables for TradePulse.AI application
"""

import os
import sys
import time
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import structlog

# Add the backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.database import TableSchemas

logger = structlog.get_logger(__name__)

# DynamoDB Local configuration
DYNAMODB_ENDPOINT = "http://localhost:8000"
DYNAMODB_REGION = "us-east-1"


def get_dynamodb_client():
    """Get DynamoDB client for local development"""
    config = Config(
        region_name=DYNAMODB_REGION,
        retries={"max_attempts": 3, "mode": "standard"},
        connect_timeout=10,
        read_timeout=30
    )
    
    return boto3.client(
        "dynamodb",
        endpoint_url=DYNAMODB_ENDPOINT,
        region_name=DYNAMODB_REGION,
        aws_access_key_id="dummy",
        aws_secret_access_key="dummy",
        config=config
    )


def wait_for_table_active(client, table_name: str, max_wait: int = 60):
    """Wait for table to become ACTIVE"""
    logger.info(f"Waiting for table {table_name} to become ACTIVE...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = client.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']
            
            if status == 'ACTIVE':
                logger.info(f"✅ Table {table_name} is ACTIVE")
                return True
            elif status in ['CREATING', 'UPDATING']:
                logger.info(f"⏳ Table {table_name} status: {status}")
                time.sleep(2)
            else:
                logger.error(f"❌ Table {table_name} has unexpected status: {status}")
                return False
                
        except ClientError as e:
            logger.error(f"Error checking table {table_name}: {e}")
            return False
    
    logger.error(f"❌ Table {table_name} did not become ACTIVE within {max_wait} seconds")
    return False


def table_exists(client, table_name: str) -> bool:
    """Check if table exists"""
    try:
        client.describe_table(TableName=table_name)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        raise


def create_table_if_not_exists(client, table_schema: dict) -> bool:
    """Create table if it doesn't exist"""
    table_name = table_schema['TableName']
    
    if table_exists(client, table_name):
        logger.info(f"✅ Table {table_name} already exists")
        return True
    
    try:
        logger.info(f"🔨 Creating table {table_name}...")
        client.create_table(**table_schema)
        
        # Wait for table to become active
        if wait_for_table_active(client, table_name):
            logger.info(f"✅ Successfully created table {table_name}")
            return True
        else:
            logger.error(f"❌ Failed to create table {table_name}")
            return False
            
    except ClientError as e:
        logger.error(f"❌ Error creating table {table_name}: {e}")
        return False


def bootstrap_all_tables():
    """Bootstrap all required DynamoDB tables"""
    logger.info("🚀 Starting DynamoDB table bootstrap...")
    
    try:
        client = get_dynamodb_client()
        
        # Test connection
        client.list_tables()
        logger.info("✅ Connected to DynamoDB Local")
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to DynamoDB Local: {e}")
        logger.error("💡 Make sure DynamoDB Local is running: ./start_dynamodb.sh")
        return False
    
    # Get all table schemas - create instance for non-static methods
    schemas = TableSchemas()
    table_schemas = [
        TableSchemas.get_live_candles_schema(),
        TableSchemas.get_signals_schema(),
        TableSchemas.get_training_data_schema(),
        TableSchemas.get_exit_analysis_log_schema(),
        TableSchemas.get_position_monitoring_log_schema(),
        TableSchemas.get_trade_execution_metrics_schema(),
        TableSchemas.get_alert_notifications_schema(),
        TableSchemas.get_users_schema(),
        TableSchemas.get_virtual_portfolios_schema(),
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
        schemas.get_notification_templates_schema(),
        TableSchemas.get_health_checks_schema(),
        TableSchemas.get_trade_analyses_schema()
    ]
    
    success_count = 0
    total_count = len(table_schemas)
    
    for schema in table_schemas:
        if create_table_if_not_exists(client, schema):
            success_count += 1
        else:
            logger.error(f"❌ Failed to create table {schema['TableName']}")
    
    logger.info(f"📊 Bootstrap complete: {success_count}/{total_count} tables ready")
    
    if success_count == total_count:
        logger.info("🎉 All tables created successfully!")
        return True
    else:
        logger.error(f"⚠️ {total_count - success_count} tables failed to create")
        return False


def list_existing_tables():
    """List all existing tables in DynamoDB Local"""
    try:
        client = get_dynamodb_client()
        response = client.list_tables()
        tables = response.get('TableNames', [])
        
        logger.info(f"📋 Existing tables in DynamoDB Local ({len(tables)}):")
        for table in sorted(tables):
            logger.info(f"  - {table}")
            
        return tables
        
    except Exception as e:
        logger.error(f"❌ Failed to list tables: {e}")
        return []


if __name__ == "__main__":
    # Configure logging
    import logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    logger.info("=== DynamoDB Local Table Bootstrap ===")
    
    # List existing tables first
    existing_tables = list_existing_tables()
    
    # Bootstrap all tables
    success = bootstrap_all_tables()
    
    if success:
        logger.info("\n✅ Bootstrap completed successfully!")
        logger.info("🚀 Backend can now start safely")
        sys.exit(0)
    else:
        logger.error("\n❌ Bootstrap failed!")
        logger.error("🔧 Check DynamoDB Local connection and table schemas")
        sys.exit(1)
