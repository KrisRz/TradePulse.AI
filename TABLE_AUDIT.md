# DynamoDB Table Audit - AWS vs Code Requirements

**Date:** 2025-10-06  
**Purpose:** Identify missing tables causing deployment rollbacks

---

## ✅ TABLES IN AWS (40 total):

```
ai_vs_random_experiments
alert_notifications
announcements
brenda-nails-terraform-locks
exit_analysis_log
health_checks
invitations
learning_engine_state                 ← EXISTS! ✅
live_candles                           ← EXISTS! ✅
market_context_cache                   ← EXISTS! ✅
message_deliveries
messages
model_performance_metrics              ← EXISTS! ✅
notification_templates
portfolio_closed_positions             ← EXISTS! ✅
portfolio_positions                    ← EXISTS! ✅
position_monitoring_log
signal_accuracy_tracking
trade_analyses
trade_execution_metrics
tradepulse-live_candles-production    ← Production version ✅
tradepulse-users                       ← EXISTS! ✅
tradepulse_analytics                   ← EXISTS! ✅
tradepulse_brain_state                 ← EXISTS! ✅
tradepulse_market_data                 ← EXISTS! ✅
tradepulse_portfolio                   ← EXISTS! ✅
tradepulse_positions                   ← EXISTS! ✅
tradepulse_runtime                     ← EXISTS! ✅
tradepulse_signals                     ← EXISTS! ✅
trading_decisions
trading_patterns
trading_signals                        ← EXISTS! ✅
training_data                          ← EXISTS! ✅
user_activity_logs
user_notification_preferences
user_performance_showcases
users_enhanced
virtual_portfolios                     ← EXISTS! ✅
wby-webiny-8a9ac4d
wby-webiny-log-26531fb
```

---

## 📋 TABLES USED IN CODE:

### **From Code Analysis:**

#### **Continuous Learning Engine:**
- `learning_engine_state` ✅ EXISTS
- `position_results` ❌ **MISSING!**
- `model_performance_metrics` ✅ EXISTS

#### **Historical Market Context:**
- `market_context_cache` ✅ EXISTS
- `live_candles` ✅ EXISTS

#### **Exit Engine:**
- `position_results` ❌ **MISSING!**

#### **Model Retraining:**
- `position_results` ❌ **MISSING!**
- `trading_signals_v2` ❌ **MISSING!**

#### **Position Result Tracker:**
- `position_tracker_stats` ❌ **MISSING!**
- `position_results` ❌ **MISSING!**

#### **Portfolio:**
- `virtual_portfolios` ✅ EXISTS
- `portfolio_positions` ✅ EXISTS

---

## ❌ MISSING TABLES (Causing Rollback):

### **1. position_results** 🔴 CRITICAL
**Used by:**
- `continuous_learning_engine.py` (line 321)
- `intelligent_exit_engine.py` (line 365)
- `model_retraining_service.py` (line 173)
- `position_result_tracker.py` (line 195, 223)

**Purpose:** Stores closed position results for ML learning

**Schema:**
```
hash_key: position_id (String)
range_key: closed_at (Number - timestamp)
attributes:
  - symbol (String)
  - entry_price (Number)
  - exit_price (Number)
  - pnl (Number)
  - pnl_pct (Number)
  - duration_seconds (Number)
  - ai_confidence (Number)
  - signal_type (String)
  - exit_reason (String)
  - win (Boolean)
  
GSI: symbol-closed_at-index
```

---

### **2. trading_signals_v2** ⚠️ MEDIUM
**Used by:**
- `model_retraining_service.py` (line 186)

**Purpose:** Stores AI trading signals for retraining

**Schema:**
```
hash_key: signal_id (String)
range_key: timestamp (Number)
attributes:
  - symbol (String)
  - action (String)
  - confidence (Number)
  - reasoning (String)
  - layer_analysis (Map)
  
GSI: symbol-timestamp-index
```

---

### **3. position_tracker_stats** ⚠️ MEDIUM
**Used by:**
- `position_result_tracker.py` (line 84)

**Purpose:** Tracks position tracker statistics

**Schema:**
```
hash_key: tracker_id (String)
attributes:
  - total_positions (Number)
  - total_wins (Number)
  - total_losses (Number)
  - win_rate (Number)
  - avg_pnl (Number)
  - last_updated (Number)
```

---

## 🎯 IMPACT ANALYSIS:

### **Without position_results:**
- ❌ Continuous Learning Engine crashes on startup
- ❌ No adaptive parameter optimization
- ❌ No position tracking
- ❌ Model retraining fails
- ❌ **APP ROLLBACK!** (can't start)

### **Without trading_signals_v2:**
- ⚠️ Model retraining degraded (uses old signal table)
- ⚠️ Signal accuracy tracking incomplete

### **Without position_tracker_stats:**
- ⚠️ Position statistics not persisted
- ⚠️ Tracker resets on restart

---

## ✅ RECOMMENDATION:

**Priority 1: Create position_results** (CRITICAL - blocking deployment)
**Priority 2: Create trading_signals_v2** (MEDIUM - degrades functionality)
**Priority 3: Create position_tracker_stats** (LOW - minor impact)

---

## 📝 NEXT STEP:

Create terraform definitions for these 3 tables and apply!
