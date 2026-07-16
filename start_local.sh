#!/bin/bash
set -euo pipefail

ROOT="/Applications/TradePuls"
cd "$ROOT"

if ! docker ps --format '{{.Names}}' | grep -qx 'tradepulse-dynamodb'; then
  docker rm -f tradepulse-dynamodb >/dev/null 2>&1 || true
  docker run -d --name tradepulse-dynamodb -p 8000:8000 \
    amazon/dynamodb-local:latest \
    -jar DynamoDBLocal.jar -sharedDb -inMemory >/dev/null
  echo "Started DynamoDB Local on :8000"
fi

export PYENV_VERSION=3.11.9
if command -v pyenv >/dev/null 2>&1; then
  eval "$(pyenv init - 2>/dev/null || true)"
fi

if [ ! -d .venv ]; then
  python -m venv .venv
  source .venv/bin/activate
  pip install -r app/backend/requirements.txt
else
  source .venv/bin/activate
fi

export PYTHONPATH="$ROOT"
export TF_CPP_MIN_LOG_LEVEL=3 TF_ENABLE_ONEDNN_OPTS=0 TF_USE_LEGACY_KERAS=1
export TF_NUM_INTEROP_THREADS=1 TF_NUM_INTRAOP_THREADS=1 TF_DISABLE_MKL=1
export CUDA_VISIBLE_DEVICES="" DISABLE_LSTM=true
export AWS_ACCESS_KEY_ID=dummy AWS_SECRET_ACCESS_KEY=dummy
export DYNAMODB_ENDPOINT=http://127.0.0.1:8000 DYNAMODB_REGION=eu-west-2
export HOST=0.0.0.0 PORT=9002 ENVIRONMENT=development

if [ -f app/backend/config/development.env ]; then
  export $(grep -E '^(BINANCE_API_KEY|BINANCE_SECRET_KEY|AWS_REGION|ENVIRONMENT|DEBUG|LOG_LEVEL|API_HOST|API_PORT|SECRET_KEY|ENABLE_LIVE_TRADING|ENABLE_PAPER_TRADING|PROFESSIONAL_MODE|DAY_TRADING_MODE)=' app/backend/config/development.env | xargs)
fi

mkdir -p /tmp/tradepulse
lsof -t -i :9002 -sTCP:LISTEN | xargs kill -9 2>/dev/null || true
lsof -t -i :4321 -sTCP:LISTEN | xargs kill -9 2>/dev/null || true

(
  cd app/backend
  nohup python main.py > /tmp/tradepulse/backend.log 2>&1 &
  echo $! > /tmp/tradepulse/backend.pid
)

if [ ! -d app/frontend/node_modules ]; then
  (cd app/frontend && npm install)
fi

(
  cd app/frontend
  nohup npm run dev -- --host 0.0.0.0 --port 4321 > /tmp/tradepulse/frontend.log 2>&1 &
  echo $! > /tmp/tradepulse/frontend.pid
)

echo "Starting backend (:9002) and frontend (:4321)..."
for i in $(seq 1 60); do
  if curl -sf http://127.0.0.1:9002/health >/dev/null && curl -sfI http://127.0.0.1:4321 >/dev/null; then
    echo "Ready:"
    echo "  Frontend: http://localhost:4321"
    echo "  Backend:  http://localhost:9002/health"
    echo "  DynamoDB: http://localhost:8000"
    echo "Logs: /tmp/tradepulse/{backend,frontend}.log"
    exit 0
  fi
  sleep 2
done

echo "Timed out waiting for services. Check logs in /tmp/tradepulse/"
exit 1
