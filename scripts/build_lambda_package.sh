#!/bin/bash
# Build the paper-bot Lambda zip (M2/E4).
#
# Contents: app/backend/{paper_trading,backtesting} + package __init__ chain
# + `requests` (built for manylinux/x86_64 — Lambda's platform, not macOS).
# numpy/pandas come from the AWS managed AWSSDKPandas-Python311 layer;
# boto3 from the Lambda runtime itself.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/dist/lambda_build"
ZIP="$ROOT/dist/paper_bot_lambda.zip"

rm -rf "$BUILD" "$ZIP"
mkdir -p "$BUILD"

# --- app code (only the dependency-light packages the bot needs) ---
mkdir -p "$BUILD/app/backend"
touch "$BUILD/app/__init__.py" "$BUILD/app/backend/__init__.py"
cp -R "$ROOT/app/backend/paper_trading" "$BUILD/app/backend/"
cp -R "$ROOT/app/backend/backtesting"   "$BUILD/app/backend/"
find "$BUILD" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# --- third-party: requests for the Lambda platform ---
# urllib3 pinned <2.1: the Lambda runtime's botocore imports urllib3 from
# /var/task if present, and botocore requires <2.1 on py3.10+.
"$ROOT/.venv/bin/pip" install requests "urllib3<2.1" \
    --target "$BUILD" \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.11 \
    --only-binary=:all: \
    --quiet

# numpy/pandas must NOT be in the zip (layer provides them)
rm -rf "$BUILD"/numpy* "$BUILD"/pandas* 2>/dev/null || true

( cd "$BUILD" && zip -qr "$ZIP" . )
echo "Built: $ZIP ($(du -h "$ZIP" | cut -f1))"
