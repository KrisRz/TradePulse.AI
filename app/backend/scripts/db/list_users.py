#!/usr/bin/env python3
"""
List Users in TradePulse.AI Database
Shows all users and their details for verification
"""

import boto3
import sys
import os
from datetime import datetime
from botocore.exceptions import ClientError
from pathlib import Path

def setup_aws_environment():
    """Set up AWS environment variables for local DynamoDB"""
    os.environ['AWS_ACCESS_KEY_ID'] = 'dummy'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'dummy'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['DYNAMODB_ENDPOINT'] = 'http://localhost:8000'

def list_users():
    """List all users in the database"""
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url='http://localhost:8000',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
        
        table = dynamodb.Table('tradepulse-users')
        
        # Scan all users
        response = table.scan()
        users = response.get('Items', [])
        
        if not users:
            print("❌ No users found in database")
            return
        
        print(f"👥 Found {len(users)} user(s):")
        print("=" * 80)
        
        for user in users:
            print(f"📧 Email: {user.get('email', 'N/A')}")
            print(f"🆔 ID: {user.get('id', 'N/A')}")
            print(f"👤 Name: {user.get('first_name', 'N/A')} {user.get('last_name', 'N/A')}")
            print(f"🔒 Role: {user.get('role', 'N/A')}")
            print(f"✅ Status: {user.get('status', 'N/A')}")
            print(f"📅 Created: {user.get('created_at', 'N/A')}")
            print(f"🔐 Has Password: {'Yes' if user.get('password_hash') else 'No'}")
            
            if user.get('permissions'):
                perms = user.get('permissions', {})
                print(f"🛡️ Permissions: {', '.join([k for k, v in perms.items() if v])}")
            
            print("-" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to list users: {e}")
        return False

def main():
    """Main function"""
    print("👥 TradePulse.AI - User List")
    print("=" * 50)
    
    # Set up environment
    setup_aws_environment()
    
    # List users
    list_users()

if __name__ == "__main__":
    main() 