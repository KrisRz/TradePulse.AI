#!/bin/bash
# Start DynamoDB Local for TradePulse.AI

cd /Applications/Projects/TradePulse.AI

# Set Java environment
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"

# Kill any existing DynamoDB processes
pkill -f "DynamoDBLocal" || true

# Create database directory if it doesn't exist
mkdir -p data/database/dynamodb

# Auto-download DynamoDB Local if not present
cd data/database/dynamodb
if [ ! -f "DynamoDBLocal.jar" ] || [ ! -d "DynamoDBLocal_lib" ]; then
    echo "📦 DynamoDB Local not found, downloading..."
    cd /Applications/Projects/TradePulse.AI
    ./scripts/setup_dynamodb_local.sh
    cd data/database/dynamodb
fi
echo "Starting DynamoDB Local on port 8000..."
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb -dbPath . -port 8000 -cors '*' &

# Wait a moment and check if it started
sleep 3
if lsof -i :8000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "✅ DynamoDB Local started successfully on port 8000"
    echo "📊 Database file: /Applications/Projects/TradePulse.AI/data/database/dynamodb/shared-local-instance.db"
    echo "🔗 Use AWS CLI: aws dynamodb list-tables --endpoint-url http://localhost:8000 --region us-east-1"
    # Bootstrap required tables automatically
    echo "🛠  Bootstrapping DynamoDB tables..."
    cd /Applications/Projects/TradePulse.AI
    if [ -x .venv/bin/python ]; then PY=.venv/bin/python; elif [ -x venv/bin/python ]; then PY=venv/bin/python; else PY=python3; fi
    DYNAMODB_ENDPOINT=http://localhost:8000 AWS_DEFAULT_REGION=us-east-1 AWS_ACCESS_KEY_ID=dummy AWS_SECRET_ACCESS_KEY=dummy \
    $PY app/backend/scripts/bootstrap_dynamodb_tables.py || echo "⚠️ Table bootstrap script failed; check logs."
else
    echo "❌ Failed to start DynamoDB Local"
    exit 1
fi
