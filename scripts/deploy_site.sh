#!/usr/bin/env bash
# Publish web/ to tradepulseai.co.uk.
#
# Filenames are not content-hashed, so cache lifetimes are set per asset class
# instead: index.html always revalidates, code gets an hour, and the fonts and
# the chart library — which only ever change by being replaced — get a year.
# The invalidation at the end covers the gap for css/js.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/web"
BUCKET="${SITE_BUCKET:-tradepulseai-site-590183672693}"
DIST="${SITE_DISTRIBUTION:-EQ4R54KGO8TNU}"

[[ -f "$SRC/index.html" ]] || { echo "missing $SRC/index.html" >&2; exit 1; }

echo "→ immutable assets (fonts, vendor)"
aws s3 sync "$SRC/fonts" "s3://$BUCKET/fonts" \
  --delete --exclude "LICENSE.md" \
  --content-type "font/woff2" \
  --cache-control "public,max-age=31536000,immutable"

aws s3 sync "$SRC/vendor" "s3://$BUCKET/vendor" \
  --delete \
  --content-type "application/javascript; charset=utf-8" \
  --cache-control "public,max-age=31536000,immutable"

echo "→ code (css, js)"
aws s3 sync "$SRC/css" "s3://$BUCKET/css" \
  --delete \
  --content-type "text/css; charset=utf-8" \
  --cache-control "public,max-age=3600"

aws s3 sync "$SRC/js" "s3://$BUCKET/js" \
  --delete \
  --content-type "application/javascript; charset=utf-8" \
  --cache-control "public,max-age=3600"

echo "→ document"
aws s3 cp "$SRC/index.html" "s3://$BUCKET/index.html" \
  --content-type "text/html; charset=utf-8" \
  --cache-control "no-cache"

echo "→ invalidating edge caches"
ID=$(aws cloudfront create-invalidation \
  --distribution-id "$DIST" --paths '/*' \
  --query 'Invalidation.Id' --output text)
echo "  invalidation $ID"

echo "done: https://tradepulseai.co.uk"
