#!/bin/bash
# TradePulse.AI Backend Startup Script
# Fixes environment and dependency issues

cd /Applications/Projects/TradePulse.AI

set -euo pipefail

# FORCE Python 3.11.9 via pyenv
if command -v pyenv >/dev/null 2>&1; then
    export PYENV_VERSION=3.11.9
    eval "$(pyenv init --path 2>/dev/null || true)"
    eval "$(pyenv init - 2>/dev/null || true)"
    echo "🐍 Using Python $(python --version) via pyenv"
else
    echo "⚠️  pyenv not found, using system Python: $(python3 --version)"
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Base environment
export PYTHONPATH="/Applications/Projects/TradePulse.AI"

# TensorFlow configuration to prevent mutex blocking
export TF_CPP_MIN_LOG_LEVEL=3
export CUDA_VISIBLE_DEVICES=""
export TF_ENABLE_ONEDNN_OPTS=0
export TF_FORCE_GPU_ALLOW_GROWTH=true
export TF_GPU_THREAD_MODE=gpu_private
export TF_USE_LEGACY_KERAS=1
export TF_NUM_INTEROP_THREADS=1
export TF_NUM_INTRAOP_THREADS=1
export TF_DISABLE_MKL=1

# Enable LSTM with safe recursion limits
export DISABLE_LSTM=false

# Load development environment variables (Binance, AWS, API host/port, etc.) if present
if [ -f app/backend/config/development.env ]; then
  # Only load selected keys; keep existing exports unchanged
  export $(grep -E '^(BINANCE_API_KEY|BINANCE_SECRET_KEY|AWS_REGION|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|DYNAMODB_ENDPOINT|ENVIRONMENT|DEBUG|LOG_LEVEL|API_HOST|API_PORT)=' app/backend/config/development.env | xargs)
fi

# FORCE DynamoDB Local credentials (override system AWS credentials)
export AWS_ACCESS_KEY_ID=dummy
export AWS_SECRET_ACCESS_KEY=dummy
export DYNAMODB_ENDPOINT=http://localhost:8000
export DYNAMODB_REGION=us-east-1

# Defaults and mappings
export ENVIRONMENT="${ENVIRONMENT:-development}"
export DEBUG="${DEBUG:-true}"
export DYNAMODB_ENDPOINT="${DYNAMODB_ENDPOINT:-http://localhost:8000}"
export SECRET_KEY="${SECRET_KEY:-tradepulse-ai-dev-secret-key-2024-enterprise-grade-secure-token-for-jwt-authentication}"
export HOST="${HOST:-${API_HOST:-0.0.0.0}}"
export PORT="${PORT:-${API_PORT:-9002}}"

# Ensure single instance on desired port - FORCE CLEANUP
echo "🔍 Checking if port ${PORT} is in use..."
EXISTING_PIDS=$(lsof -t -i :"$PORT" -sTCP:LISTEN || true)

if [ -n "${EXISTING_PIDS}" ]; then
  echo "🛑 Port ${PORT} occupied by PID(s): ${EXISTING_PIDS}"
  echo "🔨 Force killing existing process(es)..."
  kill -9 ${EXISTING_PIDS} 2>/dev/null || true
  sleep 2
  
  # Verify port is free
  STILL_RUNNING=$(lsof -t -i :"$PORT" -sTCP:LISTEN || true)
  if [ -n "${STILL_RUNNING}" ]; then
    echo "❌ ERROR: Failed to free port ${PORT}, PID ${STILL_RUNNING} still running"
    echo "💡 Try manually: kill -9 ${STILL_RUNNING}"
    exit 1
  fi
  echo "✅ Port ${PORT} is now free"
else
  echo "✅ Port ${PORT} is free - ready to start"
fi

# Quick preflight checks
if ! lsof -i :8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "⚠️  DynamoDB Local not listening on 8000. Start it before backend (or set DYNAMODB_ENDPOINT)."
fi

# Optional: show short credential fingerprints (first 4 chars) for verification only
if [ -n "${BINANCE_API_KEY:-}" ] && [ -n "${BINANCE_SECRET_KEY:-}" ]; then
  echo "🔑 Binance creds detected: K=$(printf "%s" "$BINANCE_API_KEY" | cut -c1-4)*** S=$(printf "%s" "$BINANCE_SECRET_KEY" | cut -c1-4)***"
  
  # Validate key format (should be 64 alphanumeric chars)
  KEY_LEN=$(echo -n "$BINANCE_API_KEY" | wc -c | tr -d ' ')
  SECRET_LEN=$(echo -n "$BINANCE_SECRET_KEY" | wc -c | tr -d ' ')
  
  if [ "$KEY_LEN" -ne 64 ]; then
    echo "⚠️  WARNING: BINANCE_API_KEY should be 64 chars, got $KEY_LEN"
  fi
  if [ "$SECRET_LEN" -ne 64 ]; then
    echo "⚠️  WARNING: BINANCE_SECRET_KEY should be 64 chars, got $SECRET_LEN"
  fi
else
  echo "⚠️  Binance API credentials not set; client will use public endpoints."
fi

# Install any missing lightweight runtime deps
echo "📦 Installing missing dependencies..."
python3 -m pip install tenacity fastapi uvicorn pydantic[email] python-jose[cryptography] bcrypt psutil aiohttp websockets requests boto3 python-dotenv prometheus-client --quiet

# Install TensorFlow if not present (with proper configuration)
if ! python3 -c "import tensorflow" 2>/dev/null; then
    echo "🧠 Installing TensorFlow for continuous learning..."
    python3 -m pip install tensorflow --quiet
fi

echo "✅ Dependencies installed"

# Start backend with full trading engine initialization
cd app/backend
echo "🚀 Starting TradePulse.AI Backend on ${HOST}:${PORT}..."
echo "🧠 PROFESSIONAL MODE: All trading engines will initialize during startup"
echo "🎯 Trading Engines: Enterprise AI, Day Trading, Entry/Exit, Brain Controller"
echo "📊 Confidence Thresholds: Lowered to 35% for aggressive scalping mode"
echo "⚡ Analysis Interval: 12 seconds for high-frequency trading"
echo "🔥 Position Management: Max 8 positions, 2% size each"

# Start backend in background
python3 main.py &
BACKEND_PID=$!

echo "⏳ Waiting for backend to be ready..."
sleep 30

# Auto-start Day Trading Engine
echo "🚀 AUTO-START: Starting Day Trading Engine..."
curl -X POST http://localhost:${PORT}/api/trading/modes/start

echo "✅ COMPLETE: TradePulse.AI is fully operational!"
echo "📊 Day Trading Engine is analyzing market every ~21s (adaptive based on volatility)"
echo "🎯 Ready for day trading with 70% confidence threshold (balanced for sideways markets)"

# Keep backend running in foreground
wait $BACKEND_PID

