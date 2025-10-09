#!/bin/bash

# TradePulse.AI Deployment Checklist
# Run this before deploying to production

echo "================================================================================"
echo "🚀 TRADEPULSE.AI - DEPLOYMENT CHECKLIST"
echo "================================================================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check function
check_item() {
    local description="$1"
    local command="$2"
    
    echo -n "Checking: $description... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ OK${NC}"
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        return 1
    fi
}

# Step 1: Environment
echo "📋 Step 1: Environment Check"
echo "────────────────────────────────────────────────────────────────────────────────"

check_item "Python 3.11+" "python3 --version | grep -E 'Python 3\.(11|12)'"
check_item "DynamoDB Local running" "curl -s http://localhost:8000 > /dev/null"
check_item "Virtual environment" "[ -d venv ] || [ -n \"$VIRTUAL_ENV\" ]"
check_item ".env file exists" "[ -f .env ]"
check_item "Development config exists" "[ -f app/backend/config/development.env ]"

echo ""

# Step 2: Dependencies
echo "📦 Step 2: Dependencies"
echo "────────────────────────────────────────────────────────────────────────────────"

check_item "Required Python packages" "python3 -c 'import xgboost, numpy, pandas, fastapi'"
check_item "Kalman filter package" "python3 -c 'from pykalman import KalmanFilter'"

echo ""

# Step 3: Model Files
echo "🤖 Step 3: Model Files"
echo "────────────────────────────────────────────────────────────────────────────────"

check_item "XGBoost models exist" "[ -f app/backend/models/enterprise/layer_1_regime.pkl ]"
check_item "LSTM models exist" "[ -f app/backend/models/enterprise/lstm_1m.h5 ]"
check_item "Feature scalers exist" "[ -f app/backend/models/enterprise/feature_scalers.pkl ]"

echo ""

# Step 4: New Features
echo "🎯 Step 4: New Features (Today's Improvements)"
echo "────────────────────────────────────────────────────────────────────────────────"

check_item "Kalman Filter module" "[ -f app/backend/services/kalman_price_filter.py ]"
check_item "Adaptive Position Sizer" "[ -f app/backend/services/adaptive_position_sizer.py ]"
check_item "Ensemble Meta-Learner" "[ -f app/backend/services/ensemble_meta_learner.py ]"
check_item "Regime Adaptive Engine" "[ -f app/backend/services/regime_adaptive_engine.py ]"
check_item "Enhanced reversal detection" "grep -q '_enhanced_volume_spike_detection' app/backend/services/enterprise_trading_engine.py"

echo ""

# Step 5: Configuration
echo "⚙️  Step 5: Configuration"
echo "────────────────────────────────────────────────────────────────────────────────"

check_item "Kalman filter enabled" "grep -q 'KALMAN_FILTER_ENABLED.*True' app/backend/core/config.py"
check_item "Day trading mode" "grep -q 'DAY_TRADING_LEARNING_MODE.*True' app/backend/core/config.py"
check_item "2h optimization cycles" "grep -q 'LEARNING_OPTIMIZATION_HOURS.*2' app/backend/core/config.py"

echo ""

# Step 6: Tests
echo "🧪 Step 6: Quick Smoke Test"
echo "────────────────────────────────────────────────────────────────────────────────"

check_item "Kalman Filter imports" "python3 -c 'from app.backend.services.kalman_price_filter import KalmanPriceFilter'"
check_item "Enterprise Engine imports" "python3 -c 'from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine'"
check_item "Continuous Learning imports" "python3 -c 'from app.backend.services.continuous_learning_engine import ContinuousLearningEngine'"

echo ""

# Step 7: Git Status
echo "📝 Step 7: Git Status"
echo "────────────────────────────────────────────────────────────────────────────────"

if command -v git &> /dev/null; then
    echo "Current branch: $(git branch --show-current)"
    echo "Uncommitted changes: $(git status --short | wc -l | xargs)"
    echo ""
    echo "Recent commits:"
    git log --oneline -3
else
    echo "⚠️  Git not available"
fi

echo ""
echo "================================================================================"
echo "📊 DEPLOYMENT CHECKLIST COMPLETE"
echo "================================================================================"
echo ""
echo "Next steps:"
echo "  1. Re-export XGBoost models:  python3 scripts/reexport_xgboost_models.py"
echo "  2. Start backend:             cd app/backend && python main.py"
echo "  3. Monitor logs:              python3 scripts/monitor_trading_logs.py"
echo "  4. Commit changes:            git add . && git commit -m 'Deploy: Day trading optimizations'"
echo "  5. Push to remote:            git push origin main"
echo ""
echo "================================================================================"

