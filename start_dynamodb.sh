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

# Start DynamoDB Local with explicit dbPath
cd data/database/dynamodb
echo "Starting DynamoDB Local on port 8000..."
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb -dbPath . -port 8000 -cors '*' &

# Wait a moment and check if it started
sleep 3
if lsof -i :8000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "✅ DynamoDB Local started successfully on port 8000"
    echo "📊 Database file: /Applications/Projects/TradePulse.AI/data/database/dynamodb/shared-local-instance.db"
    echo "🔗 Use AWS CLI: aws dynamodb list-tables --endpoint-url http://localhost:8000 --region us-east-1"
else
    echo "❌ Failed to start DynamoDB Local"
    exit 1
fi
