# 🔄 TRADEPULSE_MONITOR.py - UPDATES SUMMARY

**Updated for current backend structure and dependencies**

---

## 🎯 **CRITICAL UPDATES MADE**

### **1. Backend Startup Command Fixed**
```python
# OLD (incorrect):
return [sys.executable, "-m", "app.main"]

# NEW (correct):
return [sys.executable, "professional_trading_backend.py"]
```

### **2. Virtual Environment Integration**
- ✅ Automatically detects and uses `venv/bin/python` if available
- ✅ Proper PYTHONPATH configuration
- ✅ Environment variable inheritance

### **3. API Endpoints Updated**
```python
# Updated to match current backend structure:
self.api_endpoints = [
    'http://localhost:9001/health/health',           # ✅ Correct health endpoint
    'http://localhost:9001/api/signals/',            # ✅ Trading signals
    'http://localhost:9001/api/portfolio/virtual/overview',  # ✅ Portfolio data
    'http://localhost:9001/api/analytics/overview',  # ✅ Analytics
    'http://localhost:9001/'                         # ✅ Root endpoint
]
```

### **4. Java Environment Configuration**
- ✅ Proper JAVA_HOME setting for Homebrew Java 17
- ✅ PATH environment variable updates
- ✅ Enhanced Java detection with debugging

### **5. Portfolio Monitoring Updated**
- ✅ Uses real `/api/portfolio/virtual/overview` endpoint
- ✅ Handles authentication (401) gracefully
- ✅ Proper data mapping from new API structure

### **6. Trading Brain Monitoring**
- ✅ Monitors `/api/signals/` endpoint for brain activity
- ✅ Tests signal generation capability
- ✅ Graceful handling of authentication requirements

### **7. Critical Files Verification**
```python
# Updated to match current structure:
'backend_main': self.backend_dir / 'professional_trading_backend.py',  # ✅ Correct main file
'backend_config': self.backend_dir / 'core' / 'config.py',            # ✅ Config location
```

---

## 🚀 **OVERNIGHT TESTING INSTRUCTIONS**

### **Step 1: Pre-Flight Check**
```bash
# Ensure all dependencies are installed
cd /Applications/Projects/TradePulse.AI/app/backend
source venv/bin/activate
./install_dependencies.sh

# Verify Java is available
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"
java -version
```

### **Step 2: Start Overnight Monitoring**
```bash
# Navigate to project root
cd /Applications/Projects/TradePulse.AI

# Start the monitor (will run continuously)
python3 TRADEPULSE_MONITOR.py
```

### **Step 3: Monitor Output**
The script will display a comprehensive dashboard every 60 seconds:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  🟢 TRADEPULSE.AI STATUS DASHBOARD - 2025-08-16 00:05:30     ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  🎯 Overall Status: EXCELLENT           Uptime: 120.5 min    ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  ✅ DYNAMODB     : healthy       Response: N/A              ║
║  ✅ BACKEND      : healthy       Response: 0.045s           ║
║  ✅ FRONTEND     : healthy       Response: 0.023s           ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  💰 Portfolio Value: $10,000.00                                  ║
║  🟢 Daily P&L: $+125.50                                         ║
║  📊 Active Positions: 3    Trades Today: 12                    ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  🟢 CPU: 25.1%   🟢 Memory: 45.2%   🟢 Disk: 65.8%           ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## 🧠 **TRADING BRAIN MONITORING**

### **What the Monitor Checks:**
1. **Signal Endpoint Responsiveness**: `/api/signals/` returns 200/401
2. **Signal Generation Capability**: `/api/signals/generate` endpoint active
3. **Portfolio Updates**: Real portfolio data from `/api/portfolio/virtual/overview`
4. **System Health**: CPU, Memory, Disk usage monitoring
5. **Service Restart**: Automatic restart on failures (up to 10 attempts)

### **Trading Brain Status Indicators:**
- ✅ **ALIVE**: Signals endpoint responding, generation working
- ⚠️ **DEGRADED**: Endpoint responding but generation issues
- ❌ **DEAD**: No response from signals endpoint

---

## 📊 **OVERNIGHT DATA COLLECTION**

### **Files Generated:**
- `performance_data_YYYYMMDD.json` - Performance metrics
- `system_metrics_YYYYMMDD.json` - System resource usage
- `current_status.json` - Real-time status
- `logs/debug/debug_summary_YYYYMMDD_HHMMSS.json` - Debug info
- `logs/tradepulse_monitor_YYYYMMDD.log` - Full logs

### **Key Metrics Tracked:**
- Portfolio value changes
- Trading signal generation frequency
- System resource usage patterns
- Service restart events
- API response times
- Error rates and patterns

---

## 🔧 **TROUBLESHOOTING**

### **Common Issues & Solutions:**

#### **1. Backend Won't Start**
```bash
# Check virtual environment
cd /Applications/Projects/TradePulse.AI/app/backend
source venv/bin/activate
python professional_trading_backend.py
```

#### **2. DynamoDB Local Issues**
```bash
# Verify Java installation
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"
java -version

# Start DynamoDB manually
cd /Applications/Projects/TradePulse.AI/app/backend/data/dynamodb
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb -port 8000
```

#### **3. Frontend Issues**
```bash
# Check Node.js and npm
cd /Applications/Projects/TradePulse.AI/app/frontend
npm install
npm run dev
```

#### **4. Monitor Script Issues**
```bash
# Check Python dependencies
pip3 install aiohttp psutil python-dotenv requests

# Run with debug output
python3 TRADEPULSE_MONITOR.py 2>&1 | tee monitor_debug.log
```

---

## 🌙 **OVERNIGHT OPERATION FEATURES**

### **Automatic Recovery:**
- **Service Restart**: Up to 10 attempts per service
- **Health Monitoring**: 60-second intervals
- **Alert System**: Email notifications (if configured)
- **Performance Logging**: Continuous data collection

### **Safety Features:**
- **Graceful Shutdown**: SIGINT/SIGTERM handling
- **Resource Monitoring**: CPU/Memory/Disk alerts
- **Error Logging**: Comprehensive error tracking
- **Fallback Data**: Continues operation even with API issues

### **Trading Brain Verification:**
- **Signal Generation**: Tests every monitoring cycle
- **Endpoint Health**: Verifies all critical APIs
- **Portfolio Tracking**: Real-time P&L monitoring
- **Performance Metrics**: Win rate, trade count tracking

---

## 🎯 **SUCCESS CRITERIA FOR OVERNIGHT TEST**

### **✅ EXCELLENT Performance:**
- All 3 services running continuously
- API response times < 1 second
- No service restarts required
- Trading brain generating signals
- Portfolio data updating correctly

### **🟡 GOOD Performance:**
- 1-2 minor service restarts
- Occasional API timeouts (< 5%)
- Trading brain mostly responsive
- System resources within limits

### **🔴 CRITICAL Issues:**
- Multiple service failures
- Trading brain unresponsive for > 10 minutes
- System resource exhaustion
- Continuous restart loops

---

## 📈 **EXPECTED OVERNIGHT BEHAVIOR**

### **Normal Operation:**
- Dashboard updates every 60 seconds
- Occasional signal generation attempts
- Stable portfolio value (virtual trading)
- Gradual log file growth
- Consistent system resource usage

### **Warning Signs:**
- Frequent service restarts
- High CPU/Memory usage
- API timeouts increasing
- Portfolio API failures
- Java/DynamoDB crashes

---

**Status**: ✅ **MONITOR UPDATED AND READY FOR OVERNIGHT TESTING**

The TRADEPULSE_MONITOR.py script is now fully updated to work with your current backend structure, dependencies, and API endpoints. It's ready for overnight operation to verify the trading brain stays alive and operational! 🚀🧠
