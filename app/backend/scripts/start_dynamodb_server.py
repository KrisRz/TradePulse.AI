#!/usr/bin/env python3
"""
Professional DynamoDB Local Server using Moto
==============================================

Starts a professional DynamoDB-compatible server for development and testing.
Uses Moto library to provide full DynamoDB API compatibility.

Usage:
    python3 start_dynamodb_server.py [--port 8000] [--host 0.0.0.0]

Author: TradePulse.AI Development Team
Created: August 2025
Version: 1.0.0
"""

import argparse
import logging
import sys
import threading
import time
from moto.server import run_simple
from moto import mock_dynamodb

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/Applications/Projects/TradePulse.AI/app/backend/moto_dynamodb.log')
    ]
)

logger = logging.getLogger(__name__)

def start_dynamodb_server(host: str = "0.0.0.0", port: int = 8000):
    """Start professional DynamoDB server using Moto"""
    
    logger.info(f"🚀 Starting Professional DynamoDB Server on {host}:{port}")
    logger.info("📊 Using Moto library for full DynamoDB API compatibility")
    
    try:
        # Start the Moto DynamoDB server
        run_simple(
            hostname=host,
            port=port,
            application=None,
            threaded=True,
            use_reloader=False,
            use_debugger=False,
            passthrough_errors=False
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 DynamoDB Server stopped by user")
    except Exception as e:
        logger.error(f"❌ DynamoDB Server error: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Professional DynamoDB Local Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    
    args = parser.parse_args()
    
    if args.daemon:
        logger.info("🔧 Starting DynamoDB Server as daemon...")
        thread = threading.Thread(
            target=start_dynamodb_server,
            args=(args.host, args.port),
            daemon=True
        )
        thread.start()
        
        # Keep main thread alive
        try:
            while thread.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Daemon stopped")
    else:
        start_dynamodb_server(args.host, args.port)

if __name__ == "__main__":
    main()
