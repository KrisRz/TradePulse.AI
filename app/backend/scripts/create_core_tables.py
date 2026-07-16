#!/usr/bin/env python3
"""
Create core DynamoDB tables required by the application
Matches Terraform definitions from dynamodb.tf and dynamodb-missing-tables.tf
"""

import boto3
import sys

ENDPOINT = "http://localhost:8000"
REGION = "eu-west-2"

# NOTE: the client is created lazily in _client() — CORE_TABLES is imported
# by core.database.ensure_required_tables, and importing this module must
# have no side effects.
_dynamodb = None


def _client():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.client(
            'dynamodb',
            endpoint_url=ENDPOINT,
            region_name=REGION,
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy',
        )
    return _dynamodb

# Core tables from dynamodb.tf (with tradepulse_ prefix)
CORE_TABLES = [
    {
        'TableName': 'tradepulse_signals',
        'BillingMode': 'PAY_PER_REQUEST',
        'KeySchema': [
            {'AttributeName': 'pk', 'KeyType': 'HASH'},
            {'AttributeName': 'sk', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'pk', 'AttributeType': 'S'},
            {'AttributeName': 'sk', 'AttributeType': 'S'},
            {'AttributeName': 'symbol', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'N'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'symbol-timestamp-index',
                'KeySchema': [
                    {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    },
    {
        'TableName': 'tradepulse_portfolio',
        'BillingMode': 'PAY_PER_REQUEST',
        'KeySchema': [
            {'AttributeName': 'pk', 'KeyType': 'HASH'},
            {'AttributeName': 'sk', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'pk', 'AttributeType': 'S'},
            {'AttributeName': 'sk', 'AttributeType': 'S'},
            {'AttributeName': 'user_id', 'AttributeType': 'S'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'user-id-index',
                'KeySchema': [
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    },
    {
        'TableName': 'tradepulse_positions',
        'BillingMode': 'PAY_PER_REQUEST',
        'KeySchema': [
            {'AttributeName': 'pk', 'KeyType': 'HASH'},
            {'AttributeName': 'sk', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'pk', 'AttributeType': 'S'},
            {'AttributeName': 'sk', 'AttributeType': 'S'},
            {'AttributeName': 'symbol', 'AttributeType': 'S'},
            {'AttributeName': 'status', 'AttributeType': 'S'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'symbol-status-index',
                'KeySchema': [
                    {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                    {'AttributeName': 'status', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    },
    {
        'TableName': 'tradepulse_analytics',
        'BillingMode': 'PAY_PER_REQUEST',
        'KeySchema': [
            {'AttributeName': 'pk', 'KeyType': 'HASH'},
            {'AttributeName': 'sk', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'pk', 'AttributeType': 'S'},
            {'AttributeName': 'sk', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'N'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'timestamp-index',
                'KeySchema': [
                    {'AttributeName': 'pk', 'KeyType': 'HASH'},
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    },
    {
        'TableName': 'tradepulse_brain_state',
        'BillingMode': 'PAY_PER_REQUEST',
        'KeySchema': [
            {'AttributeName': 'pk', 'KeyType': 'HASH'},
            {'AttributeName': 'sk', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'pk', 'AttributeType': 'S'},
            {'AttributeName': 'sk', 'AttributeType': 'S'}
        ]
    },
    {
        'TableName': 'runtime',
        'BillingMode': 'PAY_PER_REQUEST',
        'KeySchema': [
            {'AttributeName': 'pk', 'KeyType': 'HASH'},
            {'AttributeName': 'sk', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'pk', 'AttributeType': 'S'},
            {'AttributeName': 'sk', 'AttributeType': 'S'}
        ]
    },
    {
        'TableName': 'tradepulse_market_data',
        'BillingMode': 'PAY_PER_REQUEST',
        'KeySchema': [
            {'AttributeName': 'symbol', 'KeyType': 'HASH'},
            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'symbol', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'N'}
        ]
    },
    # Critical missing tables from dynamodb-missing-tables.tf
    {
        'TableName': 'position_results',
        'BillingMode': 'PAY_PER_REQUEST',
        'KeySchema': [
            {'AttributeName': 'position_id', 'KeyType': 'HASH'},
            {'AttributeName': 'closed_at', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'position_id', 'AttributeType': 'S'},
            {'AttributeName': 'closed_at', 'AttributeType': 'N'},
            {'AttributeName': 'symbol', 'AttributeType': 'S'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'symbol-closed_at-index',
                'KeySchema': [
                    {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                    {'AttributeName': 'closed_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    },
    {
        'TableName': 'trading_signals_v2',
        'BillingMode': 'PAY_PER_REQUEST',
        'KeySchema': [
            {'AttributeName': 'signal_id', 'KeyType': 'HASH'},
            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'signal_id', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'N'},
            {'AttributeName': 'symbol', 'AttributeType': 'S'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'symbol-timestamp-index',
                'KeySchema': [
                    {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    },
    {
        'TableName': 'position_tracker_stats',
        'BillingMode': 'PAY_PER_REQUEST',
        'KeySchema': [
            {'AttributeName': 'tracker_id', 'KeyType': 'HASH'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'tracker_id', 'AttributeType': 'S'}
        ]
    },
    {
        'TableName': 'emergency_state',
        'BillingMode': 'PAY_PER_REQUEST',
        'KeySchema': [
            {'AttributeName': 'id', 'KeyType': 'HASH'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'}
        ]
    },
    {
        'TableName': 'portfolio_positions',
        'BillingMode': 'PAY_PER_REQUEST',
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
                'IndexName': 'SymbolIndex',
                'KeySchema': [
                    {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                    {'AttributeName': 'status', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    },
    {
        'TableName': 'portfolio_closed_positions',
        'BillingMode': 'PAY_PER_REQUEST',
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
                'IndexName': 'SymbolClosedIndex',
                'KeySchema': [
                    {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                    {'AttributeName': 'closed_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    },
    {
        'TableName': 'trading_decisions',
        'BillingMode': 'PAY_PER_REQUEST',
        'KeySchema': [
            {'AttributeName': 'decision_id', 'KeyType': 'HASH'},
            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'decision_id', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'N'},
            {'AttributeName': 'day', 'AttributeType': 'S'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'DayIndex',
                'KeySchema': [
                    {'AttributeName': 'day', 'KeyType': 'HASH'},
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    }
]

def create_table(table_schema):
    """Create a single table if it doesn't exist"""
    table_name = table_schema['TableName']
    dynamodb = _client()

    try:
        # Check if table exists
        dynamodb.describe_table(TableName=table_name)
        print(f"✅ Table {table_name} already exists")
        return True
    except dynamodb.exceptions.ResourceNotFoundException:
        pass

    try:
        print(f"🔨 Creating table {table_name}...")
        dynamodb.create_table(**table_schema)
        print(f"✅ Created table {table_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to create {table_name}: {e}")
        return False

def main():
    print("🚀 Creating core DynamoDB tables...")
    print(f"📡 Endpoint: {ENDPOINT}")
    print()
    
    success = 0
    failed = 0
    
    for table_schema in CORE_TABLES:
        if create_table(table_schema):
            success += 1
        else:
            failed += 1
    
    print()
    print(f"📊 Results: {success} created/existing, {failed} failed")
    
    if failed > 0:
        sys.exit(1)
    
    print("🎉 All core tables ready!")

if __name__ == "__main__":
    main()

