#!/usr/bin/env python3
"""
Create Admin User for TradePulse.AI
Creates the admin user in DynamoDB with proper password hashing
"""

import boto3
import bcrypt
import sys
import os
import uuid
from datetime import datetime
from botocore.exceptions import ClientError
from pathlib import Path

# Add the backend source to Python path
sys.path.append(str(Path(__file__).parent.parent / "apps" / "backend"))

def setup_aws_environment():
    """Set up AWS environment variables for local DynamoDB"""
    os.environ['AWS_ACCESS_KEY_ID'] = 'dummy'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'dummy'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['DYNAMODB_ENDPOINT'] = 'http://localhost:8000'

def test_dynamodb_connection():
    """Test connection to DynamoDB Local"""
    try:
        dynamodb = boto3.client(
            'dynamodb',
            endpoint_url='http://localhost:8000',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
        
        # Try to list tables
        response = dynamodb.list_tables()
        print(f"✅ Connected to DynamoDB Local ({len(response.get('TableNames', []))} tables)")
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to DynamoDB Local: {e}")
        print("💡 Make sure DynamoDB Local is running:")
        print("   docker-compose -f docker-compose.dev.yml up dynamodb-local")
        return False

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_users_table():
    """Create users table if it doesn't exist"""
    try:
        dynamodb = boto3.client(
            'dynamodb',
            endpoint_url='http://localhost:8000',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
        
        # Check if table exists
        try:
            response = dynamodb.describe_table(TableName='tradepulse-users')
            print(f"✅ Users table already exists")
            return True
        except dynamodb.exceptions.ResourceNotFoundException:
            pass
        
        # Create users table
        print("🔨 Creating users table...")
        
        table_config = {
            'TableName': 'tradepulse-users',
            'KeySchema': [
                {'AttributeName': 'id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'id', 'AttributeType': 'S'},
                {'AttributeName': 'email', 'AttributeType': 'S'}
            ],
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'EmailIndex',
                    'KeySchema': [
                        {'AttributeName': 'email', 'KeyType': 'HASH'}
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
        
        response = dynamodb.create_table(**table_config)
        print(f"✅ Created users table")
        
        # Wait for table to be active
        print(f"⏳ Waiting for table to be active...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName='tradepulse-users')
        print(f"✅ Users table is active")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create users table: {e}")
        return False

def create_admin_user(email: str, password: str):
    """Create admin user in DynamoDB"""
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url='http://localhost:8000',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
        
        table = dynamodb.Table('tradepulse-users')
        
        # Check if user already exists
        try:
            response = table.query(
                IndexName='EmailIndex',
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={':email': email}
            )
            
            if response.get('Items'):
                print(f"⚠️  User with email {email} already exists")
                return False
                
        except Exception as e:
            print(f"Warning: Could not check existing user: {e}")
        
        # Generate user ID
        user_id = f"admin_{int(datetime.utcnow().timestamp())}"
        
        # Hash password
        password_hash = hash_password(password)
        
        # Create user record
        user_item = {
            'id': user_id,
            'email': email,
            'password_hash': password_hash,
            'role': 'admin',
            'status': 'active',
            'first_name': 'Admin',
            'last_name': 'User',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'last_login': None,
            'login_count': 0,
            'preferences': {
                'notifications_enabled': True,
                'theme': 'dark',
                'timezone': 'UTC'
            },
            'permissions': {
                'admin_panel': True,
                'user_management': True,
                'system_config': True,
                'view_all_trades': True,
                'manage_signals': True
            }
        }
        
        # Store user
        table.put_item(Item=user_item)
        
        print(f"✅ Created admin user: {email}")
        print(f"   User ID: {user_id}")
        print(f"   Role: admin")
        print(f"   Status: active")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create admin user: {e}")
        return False

def create_virtual_portfolio(user_id: str):
    """Create virtual portfolio for the admin user"""
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url='http://localhost:8000',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
        
        # Check if portfolios table exists
        try:
            table = dynamodb.Table('tradepulse-virtual-portfolios')
        except:
            print("⚠️  Virtual portfolios table doesn't exist yet")
            return False
        
        portfolio_id = f"portfolio_{user_id}"
        
        portfolio_item = {
            'user_id': user_id,
            'portfolio_id': portfolio_id,
            'balance': 10000.0,  # Starting balance
            'initial_balance': 10000.0,
            'equity': 10000.0,
            'available_balance': 10000.0,
            'unrealized_pnl': 0.0,
            'realized_pnl': 0.0,
            'total_deposits': 10000.0,
            'total_withdrawals': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'current_drawdown': 0.0,
            'max_drawdown': 0.0,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'status': 'active'
        }
        
        table.put_item(Item=portfolio_item)
        print(f"✅ Created virtual portfolio: {portfolio_id}")
        print(f"   Starting balance: $10,000")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Could not create virtual portfolio: {e}")
        return False

def main():
    """Main function to create admin user"""
    
    print("👤 TradePulse.AI - Admin User Creation")
    print("=" * 50)
    
    # Admin credentials
    admin_email = "krisgrzepka@gmail.com"
    admin_password = "admin1234"
    
    print(f"Creating admin user: {admin_email}")
    print(f"Password: {admin_password}")
    print()
    
    # Set up environment
    setup_aws_environment()
    
    # Test connection
    if not test_dynamodb_connection():
        sys.exit(1)
    
    # Create users table if needed
    if not create_users_table():
        sys.exit(1)
    
    # Create admin user
    if create_admin_user(admin_email, admin_password):
        print()
        # Try to create virtual portfolio
        user_id = f"admin_{int(datetime.utcnow().timestamp())}"
        create_virtual_portfolio(user_id)
        
        print("\n" + "=" * 50)
        print("🎉 Admin user created successfully!")
        print()
        print("📋 Login Details:")
        print(f"   Email: {admin_email}")
        print(f"   Password: {admin_password}")
        print(f"   Role: admin")
        print()
        print("🔗 Next steps:")
        print("1. Start frontend: cd app/frontend && pnpm dev")
        print("2. Start backend: cd app/backend && python -m uvicorn main:app --reload")
        print("3. Login at: http://localhost:4321/auth/login")
    else:
        print("\n❌ Failed to create admin user")
        sys.exit(1)

if __name__ == "__main__":
    main() 