#!/usr/bin/env python3
"""
Migration: Move CLOSED positions from portfolio_positions to portfolio_closed_positions
Problem: 1042 positions with status=CLOSED are stuck in portfolio_positions
"""

import os
import sys
from pathlib import Path
import csv
from decimal import Decimal
from datetime import datetime, timezone

# Load AWS credentials
project_root = Path(__file__).parent.parent.parent.parent
creds_file = project_root / "Kris_accessKeys.csv"
if creds_file.exists():
    with open(creds_file, 'r') as f:
        lines = f.readlines()
        creds_line = lines[1].strip().split(',')
        os.environ['AWS_ACCESS_KEY_ID'] = creds_line[0]
        os.environ['AWS_SECRET_ACCESS_KEY'] = creds_line[1]

os.environ['AWS_REGION'] = 'eu-west-2'
os.environ['DYNAMODB_REGION'] = 'eu-west-2'

import boto3

# Connect to AWS London
dynamodb = boto3.resource(
    'dynamodb',
    region_name='eu-west-2'
)

print("="*80)
print("🔧 MIGRATION: Move CLOSED positions to proper table")
print("="*80)

# Get tables
table_positions = dynamodb.Table('portfolio_positions')
table_closed = dynamodb.Table('portfolio_closed_positions')

# Scan portfolio_positions
print("\n📦 Scanning portfolio_positions...")
response = table_positions.scan()
items = response.get('Items', [])

while 'LastEvaluatedKey' in response:
    response = table_positions.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response.get('Items', []))

print(f"✅ Found {len(items)} total positions")

# Filter CLOSED positions
closed_items = [item for item in items if item.get('status', '').upper() == 'CLOSED']
print(f"🔍 Found {len(closed_items)} CLOSED positions to migrate")

if not closed_items:
    print("\n✅ No migration needed - all positions in correct table")
    sys.exit(0)

# Ask for confirmation
print(f"\n⚠️  This will:")
print(f"   1. Copy {len(closed_items)} CLOSED positions to portfolio_closed_positions")
print(f"   2. Delete them from portfolio_positions")
print(f"\nProceed? (yes/no): ", end='')

confirmation = input().strip().lower()
if confirmation != 'yes':
    print("❌ Migration cancelled")
    sys.exit(1)

print(f"\n🚀 Starting migration...")

migrated = 0
skipped = 0
failed = 0

for item in closed_items:
    try:
        position_id = item.get('position_id')
        user_id = item.get('user_id', 'admin')
        
        # Check if already exists in closed table
        try:
            existing = table_closed.get_item(
                Key={'user_id': user_id, 'position_id': position_id}
            )
            if 'Item' in existing:
                print(f"⏭️  Skipping {position_id[:20]}... (already in closed table)")
                skipped += 1
                continue
        except:
            pass
        
        # Prepare closed position data
        closed_data = {
            'position_id': position_id,
            'user_id': user_id,
            'symbol': item.get('symbol', 'UNKNOWN'),
            'position_type': item.get('position_type', item.get('side', 'long')),
            'size': item.get('size'),
            'entry_price': item.get('entry_price'),
            'exit_price': item.get('exit_price', item.get('current_price')),
            'entry_time': item.get('entry_time'),
            'exit_time': item.get('exit_time', item.get('updated_at', datetime.now(timezone.utc).isoformat())),
            'realized_pnl': item.get('realized_pnl', item.get('unrealized_pnl', '0')),
            'status': 'closed',
            'closed_at': item.get('updated_at', datetime.now(timezone.utc).isoformat()),
            'created_at': item.get('created_at', datetime.now(timezone.utc).isoformat())
        }
        
        # Add optional fields
        for field in ['pnl_percentage', 'duration_minutes', 'ai_confidence', 'ai_reasoning', 
                      'stop_loss', 'take_profit']:
            if field in item:
                closed_data[field] = item[field]
        
        # 1. Write to closed positions table
        table_closed.put_item(Item=closed_data)
        
        # 2. Delete from positions table
        table_positions.delete_item(
            Key={'user_id': user_id, 'position_id': position_id}
        )
        
        migrated += 1
        if migrated % 10 == 0:
            print(f"   ✅ Migrated {migrated}/{len(closed_items)}...")
        
    except Exception as e:
        print(f"   ❌ Failed to migrate {position_id[:20]}...: {e}")
        failed += 1

print(f"\n" + "="*80)
print(f"📊 MIGRATION COMPLETE:")
print(f"   ✅ Migrated: {migrated}")
print(f"   ⏭️  Skipped (already in closed): {skipped}")
print(f"   ❌ Failed: {failed}")
print(f"="*80)

# Verify
print(f"\n🔍 Verifying...")
response_open = table_positions.scan(Select='COUNT')
response_closed = table_closed.scan(Select='COUNT')

open_count = response_open.get('Count', 0)
closed_count = response_closed.get('Count', 0)

print(f"\n📊 FINAL COUNTS:")
print(f"   portfolio_positions: {open_count}")
print(f"   portfolio_closed_positions: {closed_count}")

if open_count == 0:
    print(f"\n✅ SUCCESS: All closed positions migrated!")
else:
    # Check if remaining are actually OPEN
    response = table_positions.scan()
    remaining = response.get('Items', [])
    open_remaining = sum(1 for item in remaining if item.get('status', '').upper() == 'OPEN')
    closed_remaining = sum(1 for item in remaining if item.get('status', '').upper() == 'CLOSED')
    
    print(f"\n📊 Remaining in portfolio_positions:")
    print(f"   OPEN: {open_remaining}")
    print(f"   CLOSED: {closed_remaining}")
    
    if closed_remaining > 0:
        print(f"\n⚠️  WARNING: {closed_remaining} CLOSED positions still in portfolio_positions")
    else:
        print(f"\n✅ All CLOSED positions migrated successfully!")


