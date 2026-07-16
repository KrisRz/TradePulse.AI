#!/bin/bash
# Runs one paper-trading step. Idempotent per bar (safe to run often).
# Intended for cron; logs to paper_state/bot.log.
set -euo pipefail

ROOT="/Applications/TradePuls"
cd "$ROOT"
mkdir -p paper_state

# Prevent overlapping runs (a step is quick, but be safe).
LOCK="paper_state/bot.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "$(date -u +%FT%TZ) another run in progress, skipping" >> paper_state/bot.log
  exit 0
fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT

export PYTHONPATH="$ROOT"
export TF_CPP_MIN_LOG_LEVEL=3

{
  echo "----- $(date -u +%FT%TZ) -----"
  "$ROOT/.venv/bin/python" -m app.backend.paper_trading.run step
} >> paper_state/bot.log 2>&1
