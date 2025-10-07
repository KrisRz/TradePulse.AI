# 🚀 TRADEPULSE.AI BACKEND - COMPLETE PIPELINE DOCUMENTATION

**Data**: 2025-10-07  
**Cel**: Docker deployment preparation  
**Status**: Production-ready

---

## 📋 TABLE OF CONTENTS

1. [Environment Setup](#1-environment-setup)
2. [Startup Sequence](#2-startup-sequence)
3. [Service Initialization](#3-service-initialization)
4. [Trading Engines](#4-trading-engines)
5. [Brain Controller](#5-brain-controller)
6. [Runtime Flow](#6-runtime-flow)
7. [Shutdown Sequence](#7-shutdown-sequence)
8. [Docker Requirements](#8-docker-requirements)

---

## 1. ENVIRONMENT SETUP

### 1.1 Python Environment Variables (MUST SET FIRST)

```bash
# TensorFlow Configuration (BEFORE any imports!)
export TF_CPP_MIN_LOG_LEVEL=3
export TF_ENABLE_ONEDNN_OPTS=0
export TF_USE_LEGACY_KERAS=1
export TF_NUM_INTEROP_THREADS=1
export TF_NUM_INTRAOP_THREADS=1
export TF_DISABLE_MKL=1
export CUDA_VISIBLE_DEVICES=''
export TF_FORCE_GPU_ALLOW_GROWTH=true

# Python Warnings
export PYTHONWARNINGS=ignore
export PYTHONPATH=/app  # For Docker
```

### 1.2 Application Config

```bash
# Environment
export ENVIRONMENT=production  # or development
export HOST=0.0.0.0
export PORT=9002

# DynamoDB
export DYNAMODB_ENDPOINT=          # Empty for AWS, http://localhost:8000 for local
export DYNAMODB_REGION=eu-west-2
export DYNAMODB_TABLE_PREFIX=      # Empty usually

# AWS (optional if using IAM roles)
export AWS_REGION=eu-west-2
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...

# Security
export SECRET_KEY=your-secret-key-here

# Trading Mode
export TRADING_MODE=live  # or paper, backtest
```

### 1.3 Required Files/Directories

```
/app/
├── backend/
│   ├── main.py                    # Entry point
│   ├── core/
│   │   ├── application.py         # FastAPI app factory
│   │   ├── lifespan.py           # Lifecycle management
│   │   ├── container.py          # Dependency Injection
│   │   ├── config.py             # Settings
│   │   └── database.py           # DynamoDB client
│   ├── services/                 # All trading services
│   ├── brain/                    # Brain Controller FSM
│   └── models/                   # ML models
├── logs/                         # Log output
└── .env                          # Environment file
```

---

## 2. STARTUP SEQUENCE

### Phase 1: Python Initialization (0-2s)

```
main.py execution starts
│
├─> Set TensorFlow environment variables
├─> Import and configure TensorFlow
│   └─> tf.config.threading.set_*_parallelism_threads(1)
├─> Add project paths to sys.path
├─> Import FastAPI and core modules
└─> Initialize settings and logger
```

**Log Output:**
```
================================================================================
🚀 TradePulse.AI Backend Starting...
📍 Version: main.py loaded
🌍 Environment: production
🐍 Python: 3.11.x
================================================================================
✅ TensorFlow configured successfully
```

### Phase 2: FastAPI App Creation (2-3s)

```
create_application() called
│
├─> Create FastAPI instance with CORS
├─> Setup middleware (CORS, error handling)
├─> Register API routes (/api/v1/*)
│   ├─> /health, /ready
│   ├─> /api/v1/trading/*
│   ├─> /api/v1/engines/*
│   ├─> /api/v1/signals/*
│   └─> /api/v1/portfolio/*
├─> Setup lifespan handlers
└─> Return app instance
```

**Log Output:**
```
✅ FastAPI application created
✅ CORS middleware configured
✅ API routes registered
```

### Phase 3: Lifespan Startup (3-30s)

```
@asynccontextmanager lifespan() triggered
│
└─> ServiceManager.initialize_services()
    │
    ├─> STEP 1: Enhanced Initialization (Background)
    │   ├─> Historical market context pre-calculation
    │   └─> Daily recalculation service start
    │
    ├─> STEP 2: Feature Schema Validation
    │   └─> Validate ML feature schemas
    │
    ├─> STEP 3: DI Container Initialization
    │   ├─> _initialize_market_data_services()
    │   ├─> _initialize_ai_services()
    │   └─> _initialize_trading_services()
    │
    ├─> STEP 4: Brain State Load
    │   └─> get_brain_state_store().load_once()
    │
    ├─> STEP 5: Candle Persistence Start
    │   └─> start_candle_persistence()
    │
    ├─> STEP 6: Runtime Config Sync
    │   └─> sync_runtime_config()
    │
    ├─> STEP 7: Portfolio Cleanup
    │   └─> cleanup_old_portfolio_instances()
    │
    ├─> STEP 8: Brain Loop Start (if enabled)
    │   └─> brain_controller._main_trading_loop()
    │
    └─> STEP 9: Auto-start Trading Services
        └─> _auto_start_all_trading_services()
```

---

## 3. SERVICE INITIALIZATION

### 3.1 DI Container Registration Order

**File**: `app/backend/core/container.py`

```python
# PHASE 1: Core Services
1. Settings              → get_settings()
2. Database Client       → DynamoDBClient
3. Database Manager      → DatabaseManager
4. TensorFlow Service    → TensorFlowAsyncService

# PHASE 2: Market Data Layer
5. Live Market Data      → LiveMarketDataService
6. BTC Price Cache       → BTCPriceCache
7. Binance Hybrid Client → BinanceHybridClient

# PHASE 3: AI/ML Layer
8. TensorFlow Service (init)
9. Continuous Learning   → ContinuousLearningEngine
10. Entry Engine         → IntelligentEntryEngine
11. Exit Engine          → IntelligentExitEngine

# PHASE 4: Trading Layer
12. Professional Portfolio
13. Dynamic Risk Manager
14. Emergency Controls
15. Enterprise Trading Engine
16. Day Trading Engine
17. Session Aware Engine

# PHASE 5: Orchestration
18. Brain Controller     → BrainController (FSM)
19. Enhanced Persistence → EnhancedMarketPersistence
```

### 3.2 Initialization Flow Detail

#### 3.2.1 Market Data Services

```python
async def _initialize_market_data_services():
    """
    Initialize WebSocket streams and market data caching
    Duration: 2-5 seconds
    """
    
    1. get_live_market_data_service()
       ├─> Initialize WebSocket connections
       ├─> Connect to Binance streams
       ├─> Start price polling (every 5s)
       ├─> Subscribe to BTCUSDT kline@1m
       └─> Start background tasks
    
    2. get_btc_price_cache()
       ├─> Initialize cache
       ├─> Fetch initial BTC price
       └─> Start cache refresh (every 1s)
    
    3. Register in container as singletons
```

**Log Output:**
```
🔄 Initializing market data services...
📊 PIPELINE DEBUG: STEP 1 - Market Data Services
✅ Live Market Data Service initialized
✅ BTC Price Cache initialized
✅ PIPELINE DEBUG: STEP 1 COMPLETED - Market Data Services READY
```

#### 3.2.2 AI Services

```python
async def _initialize_ai_services():
    """
    Load ML models and initialize AI engines
    Duration: 5-15 seconds (model loading)
    """
    
    1. TensorFlowAsyncService.initialize()
       ├─> Load LSTM models from models/enterprise/
       │   ├─> lstm_1m.h5
       │   ├─> lstm_5m.h5
       │   ├─> lstm_15m.h5
       │   ├─> lstm_1h.h5
       │   ├─> lstm_4h.h5
       │   └─> lstm_24h.h5
       ├─> Warm up models with dummy input
       └─> Start prediction worker thread
    
    2. ContinuousLearningEngine.initialize()
       ├─> Load optimization state from DynamoDB
       ├─> Start optimization loop (every 1h)
       └─> Start model monitoring (every 12h)
    
    3. IntelligentEntryEngine.initialize()
       ├─> Load entry models
       ├─> Initialize historical context service
       ├─> Start warmup period (3 minutes)
       ├─> Pre-load historical data
       └─> Start price polling
    
    4. IntelligentExitEngine.initialize()
       ├─> Load exit models
       ├─> Initialize trailing stop engine
       └─> Start monitoring loops
```

**Log Output:**
```
🔄 Initializing AI services...
🤖 PIPELINE DEBUG: STEP 2 - AI Services (6-Layer Models)
📊 LSTM loaded: lstm_1m.h5 | timesteps=60 features=10
📊 LSTM loaded: lstm_5m.h5 | timesteps=60 features=10
... (all models)
✅ TensorFlow Async Service initialized successfully
🔥 Starting OPTIMIZED 3-minute phase-based warmup for day trading...
✅ AI services initialized
```

#### 3.2.3 Trading Services

```python
async def _initialize_trading_services():
    """
    Initialize all trading engines
    Duration: 3-8 seconds
    """
    
    1. ProfessionalPortfolio (singleton)
       ├─> Load portfolio state from DynamoDB
       ├─> Initialize position tracking
       └─> Start monitoring loops
    
    2. DynamicRiskManager
       ├─> Load risk parameters
       ├─> Initialize circuit breakers
       └─> Start risk monitoring
    
    3. EmergencyControlSystem
       ├─> Load emergency state from DynamoDB
       ├─> Initialize daily loss tracking
       └─> Check circuit breaker status
    
    4. EnterpriseTradingEngine
       ├─> Initialize 6-layer analysis
       ├─> Load ML models
       ├─> Connect to market data
       └─> Start signal generation
    
    5. DayTradingEngine
       ├─> Connect to all engines
       ├─> Initialize day trading validator
       ├─> Start coordination loops
       └─> Begin trading cycle (5-15s)
    
    6. SessionAwareTradingEngine
       ├─> Detect current trading session
       ├─> Adjust parameters for session
       └─> Start session monitoring
```

**Log Output:**
```
🔄 Initializing trading services...
✅ Professional Portfolio initialized
✅ Dynamic Risk Manager initialized
✅ Emergency Control System initialized
🚀 Initializing Day Trading Engine...
✅ Day Trading Engine initialized
✅ Trading services initialized
```

#### 3.2.4 Brain Controller

```python
async def get_brain_controller():
    """
    Initialize BRAIN FSM Orchestrator
    Duration: 1-2 seconds
    MOST IMPORTANT SERVICE
    """
    
    1. BrainController.__init__()
       ├─> Initialize FSM State Machine
       │   └─> States: INIT → WARMUP → MONITORING → TRADING → HALT
       ├─> Connect to existing engines from container
       │   ├─> day_trading_engine
       │   ├─> enterprise_engine
       │   ├─> entry_engine
       │   └─> exit_engine
       ├─> Initialize exit engine (if not exists)
       └─> Initialize optimization loops
    
    2. Register in container as singleton
    
    3. State transitions:
       INIT → WARMUP (on initialize())
       WARMUP → MONITORING (after engine warmup)
       MONITORING → TRADING (on first signal)
       TRADING ↔ HALT (circuit breakers)
```

**Log Output:**
```
================================================================================
🧠 BRAIN CONTROLLER: Starting initialization in DI container...
================================================================================
🧠 BRAIN CONTROLLER: Instance created: <BrainController>
🧠 BRAIN CONTROLLER: Instance type: <class 'BrainController'>
🧠 BRAIN CONTROLLER: Has state: True
✅ BRAIN CONTROLLER: Instance initialized - State: init
✅ BRAIN CONTROLLER: Current state = init
✅ BRAIN CONTROLLER: Registered in DI container
✅ BRAIN CONTROLLER: Successfully registered in DI container
================================================================================
```

---

## 4. TRADING ENGINES

### 4.1 Engine Hierarchy

```
Brain Controller (FSM Orchestrator)
│
├─> Day Trading Engine (5-15s cycle coordinator)
│   │
│   ├─> Enterprise Trading Engine (6-layer AI signal generator)
│   │   ├─> Layer 1: Market Regime Detection
│   │   ├─> Layer 2: LSTM Predictive Models (6 timeframes)
│   │   ├─> Layer 3: Technical Pattern Recognition
│   │   ├─> Layer 4: Multi-timeframe Technical Analysis
│   │   ├─> Layer 5: Price Direction Confidence
│   │   └─> Layer 6: Timing Optimization
│   │
│   ├─> Intelligent Entry Engine (entry point optimization)
│   │   ├─> Historical context validation
│   │   ├─> 6-layer consensus calculation
│   │   ├─> Day trading validator
│   │   ├─> Position sizing
│   │   └─> Entry timing
│   │
│   └─> Intelligent Exit Engine (position management)
│       ├─> Trailing stop optimization
│       ├─> Take profit management
│       ├─> Emergency exits
│       └─> Position monitoring
│
├─> Session Aware Engine (session-based parameter adjustment)
│
└─> Continuous Learning Engine (parameter optimization)
    ├─> Optimization loop (every 1h)
    └─> Model monitoring (every 12h)
```

### 4.2 Trading Cycle Flow

```
Every 5-15 seconds (configurable):

1. Day Trading Engine triggers cycle
   │
   ├─> Check circuit breakers
   ├─> Check emergency state
   ├─> Check portfolio limits
   │
   ├─> IF no open positions:
   │   │
   │   ├─> Enterprise Engine generates signal
   │   │   └─> 6-layer analysis → BUY/SELL/WAIT + confidence
   │   │
   │   ├─> IF signal = BUY/SELL:
   │   │   │
   │   │   ├─> Entry Engine analyzes opportunity
   │   │   │   ├─> Historical validation
   │   │   │   ├─> Day trading validator
   │   │   │   ├─> Risk checks
   │   │   │   └─> Returns: should_enter + confidence + position_size
   │   │   │
   │   │   ├─> IF should_enter = True:
   │   │   │   │
   │   │   │   ├─> Brain Controller validates
   │   │   │   ├─> Execute trade (virtual portfolio)
   │   │   │   ├─> Record decision in DynamoDB
   │   │   │   └─> Transition state: MONITORING → TRADING
   │   │   │
   │   │   └─> ELSE: WAIT
   │   │
   │   └─> ELSE: WAIT
   │
   └─> ELSE (have open positions):
       │
       ├─> Exit Engine monitors positions
       │   ├─> Check trailing stops
       │   ├─> Check take profit targets
       │   ├─> Check emergency conditions
       │   └─> Returns: should_exit + reason
       │
       ├─> IF should_exit = True:
       │   │
       │   ├─> Brain Controller validates
       │   ├─> Execute exit (close position)
       │   ├─> Record result in DynamoDB
       │   ├─> Update performance metrics
       │   └─> Transition state: TRADING → MONITORING
       │
       └─> ELSE: Continue monitoring
```

---

## 5. BRAIN CONTROLLER

### 5.1 FSM State Machine

```python
States:
  INIT        - Initial state
  WARMUP      - Warming up engines (3 minutes)
  MONITORING  - Watching market, no positions
  TRADING     - Active position(s) open
  HALT        - Emergency stop / circuit breaker

Transitions:
  INIT → WARMUP              (on initialize())
  WARMUP → MONITORING        (after warmup complete)
  MONITORING → TRADING       (on entry signal executed)
  TRADING → MONITORING       (on exit signal executed)
  ANY → HALT                 (circuit breaker triggered)
  HALT → MONITORING          (circuit breaker cleared)
```

### 5.2 Main Trading Loop

```python
async def _main_trading_loop():
    """
    Main Brain Controller loop - runs continuously
    Interval: 5-15 seconds
    """
    
    while True:
        try:
            # Get current state
            current_state = self.state.current_state
            
            # State-specific logic
            if current_state == BrainState.INIT:
                await self.initialize()
                
            elif current_state == BrainState.WARMUP:
                await self._warmup_phase()
                
            elif current_state == BrainState.MONITORING:
                await self._monitoring_phase()
                # Check for entry signals
                
            elif current_state == BrainState.TRADING:
                await self._trading_phase()
                # Monitor positions, check for exits
                
            elif current_state == BrainState.HALT:
                await self._halt_phase()
                # Wait for recovery
            
            # Sleep between cycles
            await asyncio.sleep(cycle_interval)
            
        except Exception as e:
            logger.error(f"Trading loop error: {e}")
            await asyncio.sleep(10)  # Backoff on error
```

---

## 6. RUNTIME FLOW

### 6.1 Typical Trading Session

```
00:00 - Application Start
├─> 00:00-00:30: Startup sequence (30s)
│   ├─> Initialize all services
│   ├─> Load ML models
│   ├─> Connect to market data
│   └─> Start trading loops
│
├─> 00:30-03:30: WARMUP Phase (3 minutes)
│   ├─> Collect price history
│   ├─> Build indicator buffers
│   ├─> Phase 1 (1 min): High thresholds
│   ├─> Phase 2 (2 min): Medium thresholds
│   └─> Phase 3 (3+ min): Standard thresholds
│
└─> 03:30+: OPERATIONAL Phase
    │
    ├─> MONITORING Mode (no positions)
    │   ├─> Every 5-15s:
    │   │   ├─> Generate AI signal
    │   │   ├─> Analyze entry opportunity
    │   │   └─> Execute if valid
    │   │
    │   └─> Background tasks:
    │       ├─> Market data streaming (real-time)
    │       ├─> Price cache update (every 1s)
    │       ├─> Candle persistence (every 1m)
    │       └─> Continuous learning (every 1h)
    │
    ├─> TRADING Mode (position open)
    │   ├─> Every 5-15s:
    │   │   ├─> Monitor position
    │   │   ├─> Check exit conditions
    │   │   └─> Execute exit if triggered
    │   │
    │   └─> Exit triggers:
    │       ├─> Trailing stop hit
    │       ├─> Take profit target
    │       ├─> Emergency condition
    │       └─> Circuit breaker
    │
    └─> Emergency/Circuit Breaker States
        ├─> Daily loss limit (-5%)
        ├─> Volume z-score (>3.5)
        ├─> Max concurrent positions (3)
        └─> Recovery cooldown (10-30 min)
```

### 6.2 Data Persistence

```python
# Continuous writes to DynamoDB:

1. Every 1 minute:
   └─> live_candles (closed 1m candles)

2. Every signal generation:
   └─> trading_signals (enterprise engine output)

3. Every trading decision:
   └─> trading_decisions (brain controller decisions)

4. Every trade execution:
   ├─> portfolio_positions (new position)
   └─> portfolio_closed_positions (closed position)

5. Every emergency event:
   └─> emergency_state (circuit breaker state)

6. Every hour:
   └─> learning_engine_state (optimization results)

7. Real-time:
   └─> tradepulse_market_data (all market data)
```

---

## 7. SHUTDOWN SEQUENCE

### 7.1 Graceful Shutdown

```python
@asynccontextmanager lifespan():
    # ... startup ...
    yield  # App runs
    # Shutdown begins:
    
    1. Stop Brain Controller
       ├─> Cancel main trading loop
       ├─> Close all open positions (emergency)
       └─> Save final state
    
    2. Stop Trading Engines
       ├─> Stop day trading engine
       ├─> Stop enterprise engine
       ├─> Stop continuous learning
       └─> Flush pending trades
    
    3. Stop Market Data
       ├─> Close WebSocket connections
       ├─> Stop price polling
       └─> Flush candle buffer
    
    4. Cleanup Resources
       ├─> Close DynamoDB connections
       ├─> Close TensorFlow sessions
       ├─> Cleanup portfolio instances
       └─> Flush logs
```

**Log Output:**
```
🛑 Shutting down TradePulse.AI services...
✅ Brain Controller stopped
✅ Trading engines stopped
✅ Market data services stopped
✅ Cleanup complete
```

---

## 8. DOCKER REQUIREMENTS

### 8.1 Dockerfile Structure

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc g++ make \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY .env ./

# Create logs directory
RUN mkdir -p /app/logs/debug

# Set environment variables (defaults)
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV TF_CPP_MIN_LOG_LEVEL=3
ENV TF_ENABLE_ONEDNN_OPTS=0
ENV CUDA_VISIBLE_DEVICES=""

# Expose port
EXPOSE 9002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:9002/health || exit 1

# Start application
CMD ["python", "-m", "app.backend.main"]
```

### 8.2 Required Environment Variables (Docker)

```bash
# MUST SET:
- AWS_REGION=eu-west-2
- AWS_ACCESS_KEY_ID=xxx        # Or use IAM role
- AWS_SECRET_ACCESS_KEY=xxx    # Or use IAM role
- SECRET_KEY=xxx
- ENVIRONMENT=production

# AUTO-CONFIGURED:
- DYNAMODB_ENDPOINT=            # Empty = use AWS
- DYNAMODB_REGION=eu-west-2
- HOST=0.0.0.0
- PORT=9002
- TRADING_MODE=live
```

### 8.3 Volume Mounts (Optional)

```bash
# Logs
-v /host/logs:/app/logs

# Models (if external)
-v /host/models:/app/backend/models

# Config override
-v /host/.env:/app/.env
```

### 8.4 Resource Requirements

```yaml
resources:
  limits:
    cpu: "2"
    memory: "4Gi"
  requests:
    cpu: "1"
    memory: "2Gi"
```

---

## 9. STARTUP CHECKLIST

### Before Docker Run:

- [ ] DynamoDB tables exist on AWS (11 core tables)
- [ ] AWS credentials configured (IAM role or keys)
- [ ] Environment variables set
- [ ] Models directory populated (6 LSTM models)
- [ ] Logs directory writable
- [ ] Port 9002 available
- [ ] Network access to:
  - DynamoDB (eu-west-2)
  - Binance API (stream.binance.com)

### After Docker Start:

- [ ] Health check passes (`/health` returns 200)
- [ ] Ready check passes (`/ready` returns 200)
- [ ] Engines status (`/api/v1/engines/status` shows all operational)
- [ ] Logs show no errors
- [ ] WebSocket connected to Binance
- [ ] Trading cycle running (check logs every 5-15s)

---

## 10. MONITORING

### Key Log Messages:

```
✅ TensorFlow configured successfully
✅ Market Data Services READY
✅ AI services initialized
✅ Trading services initialized
✅ BRAIN CONTROLLER: Successfully registered
✅ All TradePulse.AI services initialized successfully
Application startup complete.
```

### Health Endpoints:

```bash
# Always returns 200 if running
GET /health
→ {"status": "healthy", "timestamp": "..."}

# Returns 503 if not ready
GET /ready
→ {"status": "ready", "services": {...}}

# Engines status
GET /api/v1/engines/status
→ {"overall_status": "all_operational", ...}
```

---

## ✅ PRODUCTION READY

**Pipeline tested:**
- ✅ Local development
- ✅ DynamoDB Local
- ✅ AWS DynamoDB
- ✅ All engines operational
- ✅ Emergency controls working
- ✅ Continuous learning active

**Ready for Docker deployment!** 🚀
