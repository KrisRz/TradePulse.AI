#!/bin/bash
# Frontend Manual Deployment Script
# Fixes API endpoint to use custom domain (api.tradepulseai.co.uk)

set -e  # Exit on error

echo "🚀 TradePulse.AI Frontend Deployment (API Fix)"
echo "================================================"
echo ""

# AWS Credentials
export AWS_ACCESS_KEY_ID="AKIAYS2NQFN2UDYJX5PC"
export AWS_SECRET_ACCESS_KEY="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"
export AWS_DEFAULT_REGION="eu-west-2"

# Configuration
S3_BUCKET="tradepulse-frontend-590183672693-eu-west-2"
CLOUDFRONT_DISTRIBUTION_ID="E22SS6RYLBCIY"
FRONTEND_DIR="/Applications/Projects/TradePulse.AI/app/frontend"

echo "📦 Step 1: Building frontend (production mode)..."
cd "$FRONTEND_DIR"
NODE_ENV=production npm run build:prod

if [ ! -d "dist" ]; then
  echo "❌ Error: dist/ directory not found after build"
  exit 1
fi

echo "✅ Build complete"
echo ""

echo "📤 Step 2: Syncing to S3 bucket: $S3_BUCKET"
# Sync static assets with long cache (1 year)
aws s3 sync dist/ s3://$S3_BUCKET \
  --delete \
  --exclude "*.html" \
  --exclude "*.json" \
  --cache-control "public, max-age=31536000, immutable"

# Sync HTML/JSON with short cache (no cache)
aws s3 sync dist/ s3://$S3_BUCKET \
  --exclude "*" \
  --include "*.html" \
  --include "*.json" \
  --cache-control "public, max-age=0, must-revalidate"

echo "✅ S3 sync complete"
echo ""

echo "🧹 Step 3: Invalidating CloudFront cache..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)

echo "✅ CloudFront invalidation created: $INVALIDATION_ID"
echo ""

echo "⏳ Step 4: Waiting for invalidation to complete..."
aws cloudfront wait invalidation-completed \
  --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
  --id "$INVALIDATION_ID" || echo "⚠️  Timeout waiting for invalidation (it will complete in background)"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║  ✅ FRONTEND DEPLOYMENT SUCCESSFUL!                            ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 Frontend URL: https://tradepulseai.co.uk"
echo "📊 Admin Dashboard: https://tradepulseai.co.uk/admin/dashboard"
echo "🔗 API Backend: https://api.tradepulseai.co.uk"
echo ""
echo "🧪 Test the fix:"
echo "   Open browser console at https://tradepulseai.co.uk/admin/dashboard"
echo "   Network tab should now show requests to: api.tradepulseai.co.uk"
echo "   (instead of mpmfdpmani.eu-west-2.awsapprunner.com)"
echo ""

