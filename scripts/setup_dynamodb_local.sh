#!/bin/bash
# Setup DynamoDB Local for TradePulse.AI
# Downloads and configures DynamoDB Local if not present

set -euo pipefail

cd "$(dirname "$0")/.."

echo "🚀 TradePulse.AI - DynamoDB Local Setup"
echo "======================================"

# Check if Java 17+ is available
if ! command -v java &> /dev/null; then
    echo "❌ Java is required but not found"
    echo "💡 Install with: brew install openjdk@17"
    exit 1
fi

# Set Java environment
export JAVA_HOME=${JAVA_HOME:-/opt/homebrew/opt/openjdk@17}
export PATH="$JAVA_HOME/bin:$PATH"

# Verify Java version
JAVA_VERSION=$(java -version 2>&1 | head -1 | cut -d'"' -f2 | cut -d'.' -f1)
if [ "$JAVA_VERSION" -lt 17 ]; then
    echo "❌ Java 17+ required, found version $JAVA_VERSION"
    echo "💡 Install with: brew install openjdk@17"
    exit 1
fi

echo "✅ Java $JAVA_VERSION found"

# Create database directory
mkdir -p data/database/dynamodb
cd data/database/dynamodb

# Check if DynamoDB Local is already present
if [ -f "DynamoDBLocal.jar" ] && [ -d "DynamoDBLocal_lib" ]; then
    echo "✅ DynamoDB Local already installed"
    exit 0
fi

echo "📦 Downloading DynamoDB Local..."

# Download DynamoDB Local
DYNAMODB_URL="https://d1ni2b6xgvw0s0.cloudfront.net/v2.x/dynamodb_local_latest.tar.gz"
curl -L -o dynamodb_local_latest.tar.gz "$DYNAMODB_URL"

if [ ! -f "dynamodb_local_latest.tar.gz" ]; then
    echo "❌ Failed to download DynamoDB Local"
    exit 1
fi

echo "📦 Extracting DynamoDB Local..."
tar -xzf dynamodb_local_latest.tar.gz

# Verify extraction
if [ ! -f "DynamoDBLocal.jar" ] || [ ! -d "DynamoDBLocal_lib" ]; then
    echo "❌ Failed to extract DynamoDB Local"
    exit 1
fi

# Clean up
rm -f dynamodb_local_latest.tar.gz

echo "✅ DynamoDB Local installed successfully"
echo "📊 Location: $(pwd)"
echo "🚀 Ready to start with: ./start_dynamodb.sh"

# Save metadata
cat > dynamodb-local-metadata.json << EOF
{
  "installed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "version": "latest",
  "download_url": "$DYNAMODB_URL",
  "java_version": "$JAVA_VERSION"
}
EOF

echo "📋 Installation metadata saved"
