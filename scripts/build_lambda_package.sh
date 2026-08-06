#!/bin/bash
# Build the paper-bot Lambda zip (M2/E4).
#
# Contents: app/backend/{paper_trading,backtesting} + package __init__ chain
# + `requests` (built for manylinux/x86_64 — Lambda's platform, not macOS).
# numpy/pandas come from the AWS managed AWSSDKPandas-Python311 layer;
# boto3 from the Lambda runtime itself.
#
# Usage:
#   scripts/build_lambda_package.sh            -> dist/paper_bot_lambda.zip
#   scripts/build_lambda_package.sh --shadow   -> dist/shadow_bot_lambda.zip
#
# Why the --shadow variant exists, when the CONTENTS are identical:
# `aws_lambda_function.paper_bot` keys its deployment off
# `filebase64sha256(var.lambda_zip_path)`. Rewriting that file to ship shadow
# code would change the hash and redeploy the M5 bot mid-window — forbidden
# while the paper window is open. A separate output path leaves the M5 zip
# byte-for-byte where it was, so `terraform plan` shows no change to it.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/dist/lambda_build"
ZIP="$ROOT/dist/paper_bot_lambda.zip"

if [[ "${1:-}" == "--shadow" ]]; then
  BUILD="$ROOT/dist/shadow_build"
  ZIP="$ROOT/dist/shadow_bot_lambda.zip"
fi

rm -rf "$BUILD" "$ZIP"
mkdir -p "$BUILD"

# --- app code (only the dependency-light packages the bot needs) ---
mkdir -p "$BUILD/app/backend"
touch "$BUILD/app/__init__.py" "$BUILD/app/backend/__init__.py"
cp -R "$ROOT/app/backend/paper_trading" "$BUILD/app/backend/"
cp -R "$ROOT/app/backend/backtesting"   "$BUILD/app/backend/"
find "$BUILD" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# --- third-party: exact pins, built for the Lambda platform ---
# Versions live in app/backend/requirements-lambda.txt so a rebuild ships the
# same bytes we validated, instead of whatever PyPI serves today.
"$ROOT/.venv/bin/pip" install -r "$ROOT/app/backend/requirements-lambda.txt" \
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
