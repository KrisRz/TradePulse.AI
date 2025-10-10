#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════
# 🔍 TIER 2 VERIFICATION CHECK - Run in 2 Hours
# ═══════════════════════════════════════════════════════════════════════════

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║               🔍 TIER 2 VERIFICATION CHECK (2H Later)                ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

export AWS_ACCESS_KEY_ID="AKIAYS2NQFN2UDYJX5PC"
export AWS_SECRET_ACCESS_KEY="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"
export AWS_DEFAULT_REGION="eu-west-2"

echo "📊 Checking logs from last 2 hours..."
echo ""

# 1. Check for Tier 2 SELL signal generation
echo "═══════════════════════════════════════════════════════════════════════"
echo "1️⃣ TIER 2 SELL SIGNAL GENERATION"
echo "═══════════════════════════════════════════════════════════════════════"
TIER2_COUNT=$(aws logs tail /aws/apprunner/tradepulse-backend/fc591a233e1c40f99a2768c95712abad/application \
  --since 2h --format short | grep -c "STANDARD OVERBOUGHT OPPORTUNITY DETECTED (TIER 2)" || echo "0")
echo "✅ Tier 2 signals generated: $TIER2_COUNT"
echo ""

if [ "$TIER2_COUNT" -gt 0 ]; then
  echo "📋 Last Tier 2 signal details:"
  aws logs tail /aws/apprunner/tradepulse-backend/fc591a233e1c40f99a2768c95712abad/application \
    --since 2h --format short | grep -A 12 "STANDARD OVERBOUGHT OPPORTUNITY DETECTED (TIER 2)" | tail -15
  echo ""
fi

# 2. Check for actual SELL trade executions
echo "═══════════════════════════════════════════════════════════════════════"
echo "2️⃣ SELL TRADE EXECUTIONS"
echo "═══════════════════════════════════════════════════════════════════════"
SELL_EXEC_COUNT=$(aws logs tail /aws/apprunner/tradepulse-backend/fc591a233e1c40f99a2768c95712abad/application \
  --since 2h --format short | grep -c "OPENING NEW POSITION.*SELL" || echo "0")
echo "✅ SELL trades executed: $SELL_EXEC_COUNT"
echo ""

if [ "$SELL_EXEC_COUNT" -gt 0 ]; then
  echo "📋 SELL trade details:"
  aws logs tail /aws/apprunner/tradepulse-backend/fc591a233e1c40f99a2768c95712abad/application \
    --since 2h --format short | grep "OPENING NEW POSITION.*SELL"
  echo ""
fi

# 3. Check for Entry Engine rejections
echo "═══════════════════════════════════════════════════════════════════════"
echo "3️⃣ ENTRY ENGINE REJECTIONS"
echo "═══════════════════════════════════════════════════════════════════════"
REJECTED_COUNT=$(aws logs tail /aws/apprunner/tradepulse-backend/fc591a233e1c40f99a2768c95712abad/application \
  --since 2h --format short | grep -c "validator_rejected" || echo "0")
echo "⚠️ Signals rejected by validator: $REJECTED_COUNT"
echo ""

if [ "$REJECTED_COUNT" -gt 0 ]; then
  echo "📋 Last rejection reason:"
  aws logs tail /aws/apprunner/tradepulse-backend/fc591a233e1c40f99a2768c95712abad/application \
    --since 2h --format short | grep -B 2 "validator_rejected" | tail -5
  echo ""
fi

# 4. Check current market conditions
echo "═══════════════════════════════════════════════════════════════════════"
echo "4️⃣ CURRENT MARKET CONDITIONS"
echo "═══════════════════════════════════════════════════════════════════════"
aws logs tail /aws/apprunner/tradepulse-backend/fc591a233e1c40f99a2768c95712abad/application \
  --since 5m --format short | grep "Current Bitcoin price" | tail -1
echo ""
aws logs tail /aws/apprunner/tradepulse-backend/fc591a233e1c40f99a2768c95712abad/application \
  --since 5m --format short | grep "RSI SAFETY" | tail -1
echo ""

# 5. Check for Tier 1 signals
echo "═══════════════════════════════════════════════════════════════════════"
echo "5️⃣ TIER 1 EXTREME SIGNALS"
echo "═══════════════════════════════════════════════════════════════════════"
TIER1_COUNT=$(aws logs tail /aws/apprunner/tradepulse-backend/fc591a233e1c40f99a2768c95712abad/application \
  --since 2h --format short | grep -c "EXTREME OVERBOUGHT SCALP OPPORTUNITY DETECTED" || echo "0")
echo "✅ Tier 1 signals generated: $TIER1_COUNT"
echo ""

# 6. Summary
echo "═══════════════════════════════════════════════════════════════════════"
echo "📊 SUMMARY (Last 2 Hours)"
echo "═══════════════════════════════════════════════════════════════════════"
echo "• Tier 2 SELL signals: $TIER2_COUNT"
echo "• Tier 1 SELL signals: $TIER1_COUNT"
echo "• SELL trades executed: $SELL_EXEC_COUNT"
echo "• Validator rejections: $REJECTED_COUNT"
echo ""

# Interpretation
if [ "$SELL_EXEC_COUNT" -gt 0 ]; then
  echo "✅ SUCCESS: Tier 2 is generating AND executing SELL trades!"
elif [ "$TIER2_COUNT" -gt 0 ] && [ "$REJECTED_COUNT" -gt 0 ]; then
  echo "⚠️ PARTIAL: Tier 2 generating signals but Entry Engine filtering (low R/R)"
  echo "   → Expected during low volatility/Asian session"
  echo "   → Wait for NY session or higher volatility"
elif [ "$TIER2_COUNT" -gt 0 ]; then
  echo "⚠️ CHECK: Tier 2 generating signals but no executions"
  echo "   → Review Entry Engine logs for reason"
else
  echo "⏳ WAITING: No overbought conditions in last 2 hours"
  echo "   → Market may be oversold or neutral"
  echo "   → Check BUY signals instead"
fi
echo ""

echo "═══════════════════════════════════════════════════════════════════════"
echo ""

