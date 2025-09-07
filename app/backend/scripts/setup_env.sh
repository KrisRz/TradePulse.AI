#!/bin/bash
# TradePulse.AI Environment Variables
# Source this file: source setup_env.sh

export ENVIRONMENT="development"
export DYNAMODB_ENDPOINT="http://localhost:8000"
export SECRET_KEY="dev-secret-key-change-in-production-must-be-at-least-32-characters-long"
export BINANCE_TESTNET="false"
export BINANCE_TIMEOUT="30"
export ENABLE_LIVE_TRADING="true"
export STRICT_LIVE_STREAM="true"
export BINANCE_API_KEY="bWgI1vnxd9R4lIGMouwlHyuDxTkvAlxkEGcSVdsC4MehZ3HPDXwGLjbDc8c2rtBz"
export BINANCE_SECRET_KEY="VDFuE0f5PYtDKNZ3S4LWt1nZySQlHEg3yvVdwEt96UHGxRdBAzAyNSCz0Tv3pJ1Q"

echo "✅ TradePulse.AI environment variables loaded"
