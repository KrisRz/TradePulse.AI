#!/usr/bin/env python3
"""
Professional Environment Setup Script for TradePulse.AI
======================================================

Sets up environment variables for professional deployment.
Ensures Binance API keys are configured for live data access.

Usage:
    python3 setup_environment.py --api-key YOUR_KEY --secret-key YOUR_SECRET

Author: TradePulse.AI Development Team
Created: August 2025
Version: 1.0.0
"""

import os
import sys
import argparse
from pathlib import Path

def setup_environment(api_key: str = None, secret_key: str = None, testnet: bool = False):
    """Setup environment variables for professional deployment"""
    
    print("🔧 Setting up TradePulse.AI Professional Environment...")
    
    # Core environment variables
    env_vars = {
        "ENVIRONMENT": "development",
        "DYNAMODB_ENDPOINT": "http://localhost:8000",
        "SECRET_KEY": "dev-secret-key-change-in-production-must-be-at-least-32-characters-long",
        "BINANCE_TESTNET": "false" if not testnet else "true",
        "BINANCE_TIMEOUT": "30",
        "ENABLE_LIVE_TRADING": "true",
        "STRICT_LIVE_STREAM": "true"
    }
    
    # Add API keys if provided
    if api_key:
        env_vars["BINANCE_API_KEY"] = api_key
        print(f"✅ Binance API Key configured: {api_key[:8]}...")
    else:
        env_vars["BINANCE_API_KEY"] = "your-real-binance-api-key-here"
        print("⚠️ Binance API Key placeholder set - replace with real key!")
    
    if secret_key:
        env_vars["BINANCE_SECRET_KEY"] = secret_key
        print(f"✅ Binance Secret Key configured: {secret_key[:8]}...")
    else:
        env_vars["BINANCE_SECRET_KEY"] = "your-real-binance-secret-key-here"
        print("⚠️ Binance Secret Key placeholder set - replace with real key!")
    
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"🔧 {key}={value}")
    
    # Create environment export script
    script_content = "#!/bin/bash\n"
    script_content += "# TradePulse.AI Environment Variables\n"
    script_content += "# Source this file: source setup_env.sh\n\n"
    
    for key, value in env_vars.items():
        script_content += f'export {key}="{value}"\n'
    
    script_content += '\necho "✅ TradePulse.AI environment variables loaded"\n'
    
    # Write to setup script
    script_path = Path(__file__).parent / "setup_env.sh"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Make executable
    os.chmod(script_path, 0o755)
    
    print(f"📝 Environment script created: {script_path}")
    print("🚀 To use: source app/backend/scripts/setup_env.sh")
    
    return env_vars

def validate_api_keys():
    """Validate that API keys are configured"""
    api_key = os.environ.get("BINANCE_API_KEY")
    secret_key = os.environ.get("BINANCE_SECRET_KEY")
    
    if not api_key or api_key == "your-real-binance-api-key-here":
        print("❌ BINANCE_API_KEY not configured!")
        return False
    
    if not secret_key or secret_key == "your-real-binance-secret-key-here":
        print("❌ BINANCE_SECRET_KEY not configured!")
        return False
    
    print("✅ Binance API keys are configured")
    return True

def main():
    parser = argparse.ArgumentParser(description="Setup TradePulse.AI environment")
    parser.add_argument("--api-key", help="Binance API Key")
    parser.add_argument("--secret-key", help="Binance Secret Key")
    parser.add_argument("--testnet", action="store_true", help="Use Binance testnet")
    parser.add_argument("--validate", action="store_true", help="Validate current environment")
    
    args = parser.parse_args()
    
    if args.validate:
        if validate_api_keys():
            print("✅ Environment validation passed")
            sys.exit(0)
        else:
            print("❌ Environment validation failed")
            sys.exit(1)
    
    # Setup environment
    env_vars = setup_environment(args.api_key, args.secret_key, args.testnet)
    
    print("\n🎯 NEXT STEPS:")
    print("1. Add your real Binance API keys:")
    print("   export BINANCE_API_KEY='your-real-api-key'")
    print("   export BINANCE_SECRET_KEY='your-real-secret-key'")
    print("2. Or run: source app/backend/scripts/setup_env.sh")
    print("3. Start backend: python3 app/backend/main.py")
    
    if not args.api_key or not args.secret_key:
        print("\n⚠️ WARNING: Using placeholder API keys - replace with real keys for live data!")

if __name__ == "__main__":
    main()

