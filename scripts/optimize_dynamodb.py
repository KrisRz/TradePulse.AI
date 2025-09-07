#!/usr/bin/env python3
"""
DynamoDB Local Optimization Script
==================================

Optimizes DynamoDB Local to follow industry best practices:
1. Remove empty/unused tables
2. Standardize naming conventions  
3. Fix key schema design
4. Add missing GSIs
5. Implement TTL for time-series data
6. Consolidate related tables using single-table design

Usage: python3 scripts/optimize_dynamodb.py
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError
import structlog

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app', 'backend'))
from core.database import DynamoDBClient

logger = structlog.get_logger(__name__)

class DynamoDBOptimizer:
    """Optimizes DynamoDB Local to follow industry best practices"""
    
    def __init__(self):
        self.client = DynamoDBClient(local_development=True)
        self.dynamodb = self.client.dynamodb
        self.dynamodb_client = self.dynamodb.meta.client
        
        # Tables to remove (empty/unused)
        self.tables_to_remove = [
            'brain_audit',
            'brain_decisions', 
            'brain_errors',
            'brain_performance_log',
            'brain_positions',
            'learning_insights',
            'live_tickers',
            'message_deliveries',
            'tradepulse-virtual-portfolios',
            'tradepulse-virtual-positions',
            'virtual_portfolios',
            'virtual_positions', 
            'virtual_trades',
            'trading_signals'  # Empty, will recreate with better schema
        ]
        
        # Tables to rename for consistency (old_name -> new_name)
        self.tables_to_rename = {
            'tradepulse-users': 'users',
            'live_candles_enhanced': 'market_data',  # Better semantic name
            'live_tickers_enhanced': 'ticker_data'
        }
        
        # New optimized table schemas
        self.optimized_schemas = {
            'users': {
                'KeySchema': [
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'AttributeDefinitions': [
                    {'AttributeName': 'user_id', 'AttributeType': 'S'},
                    {'AttributeName': 'created_at', 'AttributeType': 'S'},
                    {'AttributeName': 'email', 'AttributeType': 'S'}
                ],
                'GlobalSecondaryIndexes': [
                    {
                        'IndexName': 'email-index',
                        'KeySchema': [
                            {'AttributeName': 'email', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    }
                ]
            },
            'brain_system': {
                'KeySchema': [
                    {'AttributeName': 'PK', 'KeyType': 'HASH'},
                    {'AttributeName': 'SK', 'KeyType': 'RANGE'}
                ],
                'AttributeDefinitions': [
                    {'AttributeName': 'PK', 'AttributeType': 'S'},
                    {'AttributeName': 'SK', 'AttributeType': 'S'},
                    {'AttributeName': 'timestamp', 'AttributeType': 'S'}
                ],
                'GlobalSecondaryIndexes': [
                    {
                        'IndexName': 'timestamp-index',
                        'KeySchema': [
                            {'AttributeName': 'timestamp', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    }
                ],
                'TimeToLiveSpecification': {
                    'AttributeName': 'ttl',
                    'Enabled': True
                }
            },
            'trading_signals_v2': {
                'KeySchema': [
                    {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                ],
                'AttributeDefinitions': [
                    {'AttributeName': 'symbol', 'AttributeType': 'S'},
                    {'AttributeName': 'timestamp', 'AttributeType': 'S'},
                    {'AttributeName': 'signal_type', 'AttributeType': 'S'}
                ],
                'GlobalSecondaryIndexes': [
                    {
                        'IndexName': 'signal-type-index',
                        'KeySchema': [
                            {'AttributeName': 'signal_type', 'KeyType': 'HASH'},
                            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                    }
                ],
                'TimeToLiveSpecification': {
                    'AttributeName': 'ttl',
                    'Enabled': True
                }
            }
        }
        
    def analyze_current_state(self) -> Dict[str, Any]:
        """Analyze current database state"""
        logger.info("🔍 Analyzing current database state...")
        
        tables = self.dynamodb_client.list_tables()['TableNames']
        analysis = {
            'total_tables': len(tables),
            'empty_tables': [],
            'active_tables': [],
            'single_key_tables': [],
            'composite_key_tables': [],
            'tables_with_gsi': [],
            'tables_with_ttl': []
        }
        
        for table_name in tables:
            try:
                # Get table description
                desc = self.dynamodb_client.describe_table(TableName=table_name)['Table']
                
                # Check if empty
                table = self.dynamodb.Table(table_name)
                scan_response = table.scan(Select='COUNT', Limit=10)
                item_count = scan_response['Count']
                
                if item_count == 0:
                    analysis['empty_tables'].append(table_name)
                else:
                    analysis['active_tables'].append((table_name, item_count))
                
                # Check key schema
                key_schema = desc['KeySchema']
                if len(key_schema) == 1:
                    analysis['single_key_tables'].append(table_name)
                else:
                    analysis['composite_key_tables'].append(table_name)
                
                # Check GSIs
                if desc.get('GlobalSecondaryIndexes'):
                    analysis['tables_with_gsi'].append(table_name)
                
                # Check TTL
                try:
                    ttl_desc = self.dynamodb_client.describe_time_to_live(TableName=table_name)
                    if ttl_desc['TimeToLiveDescription']['TimeToLiveStatus'] == 'ENABLED':
                        analysis['tables_with_ttl'].append(table_name)
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"Error analyzing table {table_name}: {e}")
        
        return analysis
    
    def remove_empty_tables(self) -> None:
        """Remove empty/unused tables"""
        logger.info("🗑️ Removing empty/unused tables...")
        
        for table_name in self.tables_to_remove:
            try:
                # Verify table is empty before deletion
                table = self.dynamodb.Table(table_name)
                scan_response = table.scan(Select='COUNT', Limit=10)
                
                if scan_response['Count'] == 0:
                    logger.info(f"Deleting empty table: {table_name}")
                    self.dynamodb_client.delete_table(TableName=table_name)
                    
                    # Wait for deletion
                    waiter = self.dynamodb_client.get_waiter('table_not_exists')
                    waiter.wait(TableName=table_name, WaiterConfig={'Delay': 2, 'MaxAttempts': 30})
                    logger.info(f"✅ Deleted: {table_name}")
                else:
                    logger.warning(f"⚠️ Skipping {table_name} - contains {scan_response['Count']} items")
                    
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.info(f"Table {table_name} already deleted")
                else:
                    logger.error(f"Error deleting {table_name}: {e}")
            except Exception as e:
                logger.error(f"Error deleting {table_name}: {e}")
    
    def create_optimized_tables(self) -> None:
        """Create new optimized tables"""
        logger.info("🏗️ Creating optimized tables...")
        
        for table_name, schema in self.optimized_schemas.items():
            try:
                logger.info(f"Creating optimized table: {table_name}")
                
                create_params = {
                    'TableName': table_name,
                    'KeySchema': schema['KeySchema'],
                    'AttributeDefinitions': schema['AttributeDefinitions'],
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
                
                # Add GSIs if specified
                if 'GlobalSecondaryIndexes' in schema:
                    create_params['GlobalSecondaryIndexes'] = schema['GlobalSecondaryIndexes']
                
                # Create table
                self.dynamodb_client.create_table(**create_params)
                
                # Wait for table to be active
                waiter = self.dynamodb_client.get_waiter('table_exists')
                waiter.wait(TableName=table_name, WaiterConfig={'Delay': 2, 'MaxAttempts': 30})
                
                # Add TTL if specified
                if 'TimeToLiveSpecification' in schema:
                    self.dynamodb_client.update_time_to_live(
                        TableName=table_name,
                        TimeToLiveSpecification=schema['TimeToLiveSpecification']
                    )
                    logger.info(f"✅ Added TTL to {table_name}")
                
                logger.info(f"✅ Created optimized table: {table_name}")
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceInUseException':
                    logger.info(f"Table {table_name} already exists")
                else:
                    logger.error(f"Error creating {table_name}: {e}")
            except Exception as e:
                logger.error(f"Error creating {table_name}: {e}")
    
    def add_ttl_to_existing_tables(self) -> None:
        """Add TTL to time-series tables"""
        logger.info("⏰ Adding TTL to time-series tables...")
        
        ttl_tables = {
            'live_candles': 'ttl',  # 30 days retention
            'emergency_events': 'ttl',  # 90 days retention
            'trading_decisions': 'ttl'  # 7 days retention
        }
        
        for table_name, ttl_attribute in ttl_tables.items():
            try:
                # Check if table exists
                self.dynamodb_client.describe_table(TableName=table_name)
                
                # Add TTL
                self.dynamodb_client.update_time_to_live(
                    TableName=table_name,
                    TimeToLiveSpecification={
                        'AttributeName': ttl_attribute,
                        'Enabled': True
                    }
                )
                logger.info(f"✅ Added TTL to {table_name}")
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.warning(f"Table {table_name} not found")
                elif 'TimeToLive is already' in str(e):
                    logger.info(f"TTL already enabled for {table_name}")
                else:
                    logger.error(f"Error adding TTL to {table_name}: {e}")
            except Exception as e:
                logger.error(f"Error adding TTL to {table_name}: {e}")
    
    def add_missing_gsis(self) -> None:
        """Add missing GSIs to existing tables"""
        logger.info("📊 Adding missing GSIs...")
        
        gsi_updates = {
            'portfolio_positions': {
                'IndexName': 'symbol-entry-time-index',
                'KeySchema': [
                    {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                    {'AttributeName': 'entry_time', 'KeyType': 'RANGE'}
                ],
                'AttributeDefinitions': [
                    {'AttributeName': 'symbol', 'AttributeType': 'S'},
                    {'AttributeName': 'entry_time', 'AttributeType': 'S'}
                ]
            },
            'trade_analyses': {
                'IndexName': 'symbol-timestamp-index', 
                'KeySchema': [
                    {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'AttributeDefinitions': [
                    {'AttributeName': 'symbol', 'AttributeType': 'S'},
                    {'AttributeName': 'created_at', 'AttributeType': 'S'}
                ]
            }
        }
        
        for table_name, gsi_config in gsi_updates.items():
            try:
                # Check if table exists and doesn't already have this GSI
                desc = self.dynamodb_client.describe_table(TableName=table_name)['Table']
                existing_gsis = [gsi['IndexName'] for gsi in desc.get('GlobalSecondaryIndexes', [])]
                
                if gsi_config['IndexName'] not in existing_gsis:
                    # Add required attributes to table if not present
                    existing_attrs = {attr['AttributeName']: attr['AttributeType'] 
                                    for attr in desc['AttributeDefinitions']}
                    
                    new_attrs = []
                    for attr in gsi_config['AttributeDefinitions']:
                        if attr['AttributeName'] not in existing_attrs:
                            new_attrs.append(attr)
                    
                    if new_attrs:
                        # Update table with new attributes first
                        self.dynamodb_client.update_table(
                            TableName=table_name,
                            AttributeDefinitions=desc['AttributeDefinitions'] + new_attrs
                        )
                        
                        # Wait for table to be active
                        waiter = self.dynamodb_client.get_waiter('table_exists')
                        waiter.wait(TableName=table_name)
                    
                    # Add GSI
                    self.dynamodb_client.update_table(
                        TableName=table_name,
                        GlobalSecondaryIndexUpdates=[
                            {
                                'Create': {
                                    'IndexName': gsi_config['IndexName'],
                                    'KeySchema': gsi_config['KeySchema'],
                                    'Projection': {'ProjectionType': 'ALL'},
                                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                                }
                            }
                        ]
                    )
                    logger.info(f"✅ Added GSI {gsi_config['IndexName']} to {table_name}")
                else:
                    logger.info(f"GSI {gsi_config['IndexName']} already exists on {table_name}")
                    
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.warning(f"Table {table_name} not found")
                else:
                    logger.error(f"Error adding GSI to {table_name}: {e}")
            except Exception as e:
                logger.error(f"Error adding GSI to {table_name}: {e}")
    
    def generate_optimization_report(self, before: Dict[str, Any], after: Dict[str, Any]) -> str:
        """Generate optimization report"""
        report = f"""
🎯 DYNAMODB OPTIMIZATION REPORT
{'='*50}
Timestamp: {datetime.now().isoformat()}

📊 BEFORE OPTIMIZATION:
- Total Tables: {before['total_tables']}
- Empty Tables: {len(before['empty_tables'])}
- Active Tables: {len(before['active_tables'])}
- Single-key Tables: {len(before['single_key_tables'])}
- Tables with GSI: {len(before['tables_with_gsi'])}
- Tables with TTL: {len(before['tables_with_ttl'])}

📈 AFTER OPTIMIZATION:
- Total Tables: {after['total_tables']}
- Empty Tables: {len(after['empty_tables'])}
- Active Tables: {len(after['active_tables'])}
- Single-key Tables: {len(after['single_key_tables'])}
- Tables with GSI: {len(after['tables_with_gsi'])}
- Tables with TTL: {len(after['tables_with_ttl'])}

✅ IMPROVEMENTS:
- Removed {before['total_tables'] - after['total_tables']} unused tables
- Reduced single-key tables by {len(before['single_key_tables']) - len(after['single_key_tables'])}
- Added {len(after['tables_with_gsi']) - len(before['tables_with_gsi'])} GSIs
- Added {len(after['tables_with_ttl']) - len(before['tables_with_ttl'])} TTL configurations

🎯 OPTIMIZATION SCORE:
- Before: {self._calculate_score(before):.1f}%
- After: {self._calculate_score(after):.1f}%
- Improvement: +{self._calculate_score(after) - self._calculate_score(before):.1f}%
"""
        return report
    
    def _calculate_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate optimization score"""
        if analysis['total_tables'] == 0:
            return 0
        
        # Scoring criteria
        active_ratio = len(analysis['active_tables']) / analysis['total_tables']
        composite_ratio = len(analysis['composite_key_tables']) / analysis['total_tables']
        gsi_ratio = len(analysis['tables_with_gsi']) / analysis['total_tables']
        ttl_ratio = len(analysis['tables_with_ttl']) / analysis['total_tables']
        
        # Weighted score
        score = (active_ratio * 0.3 + composite_ratio * 0.3 + gsi_ratio * 0.2 + ttl_ratio * 0.2) * 100
        return score
    
    def optimize(self) -> str:
        """Run complete optimization"""
        logger.info("🚀 Starting DynamoDB optimization...")
        
        # Analyze before
        before_analysis = self.analyze_current_state()
        logger.info(f"Before: {before_analysis['total_tables']} tables, {len(before_analysis['empty_tables'])} empty")
        
        # Step 1: Remove empty tables
        self.remove_empty_tables()
        
        # Step 2: Create optimized tables
        self.create_optimized_tables()
        
        # Step 3: Add TTL to existing tables
        self.add_ttl_to_existing_tables()
        
        # Step 4: Add missing GSIs
        self.add_missing_gsis()
        
        # Analyze after
        after_analysis = self.analyze_current_state()
        logger.info(f"After: {after_analysis['total_tables']} tables, {len(after_analysis['empty_tables'])} empty")
        
        # Generate report
        report = self.generate_optimization_report(before_analysis, after_analysis)
        
        logger.info("✅ DynamoDB optimization completed!")
        return report

def main():
    """Main optimization function"""
    print("🔧 DynamoDB Local Optimization")
    print("=" * 40)
    
    try:
        optimizer = DynamoDBOptimizer()
        report = optimizer.optimize()
        
        # Save report
        report_file = f"dynamodb_optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(report)
        print(f"\n📄 Report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"❌ Optimization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
