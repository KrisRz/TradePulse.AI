"""
TradePulse.AI Unified Data Flow System - Real-time Pipeline Integration
=====================================================================

High-performance, unified data flow system integrating enhanced persistence,
hybrid client, and all trading services into a seamless real-time pipeline.
Designed for enterprise-grade performance with live market data only.

Author: TradePulse.AI Development Team
Created: August 2025
Version: 4.1.0
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from decimal import Decimal

# Core service imports for integration
from app.backend.services.enhanced_market_persistence import EnhancedMarketPersistence, PersistenceConfig
from app.backend.services.binance_hybrid_client import BinanceHybridClient, get_live_price_hybrid, get_live_candles_hybrid
from app.backend.services.live_market_data import get_live_market_data_service
from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine
from app.backend.services.intelligent_entry_engine import IntelligentEntryEngine
from app.backend.services.intelligent_exit_engine import IntelligentExitEngine
from app.backend.services.dynamic_risk_manager import DynamicRiskManager
from app.backend.services.emergency_controls import EmergencyControlSystem
from app.backend.services.professional_portfolio import get_professional_portfolio

logger = logging.getLogger(__name__)

class DataSourcePriority(Enum):
    """Data source priority levels"""
    PRIMARY = "primary"      # WebSocket streams
    SECONDARY = "secondary"  # REST API fallback
    TERTIARY = "tertiary"    # Enhanced persistence cache
    FALLBACK = "fallback"    # Database historical

class DataQuality(Enum):
    """Data quality levels"""
    EXCELLENT = "excellent"  # Real-time, validated, complete
    GOOD = "good"           # Recent, mostly complete
    ACCEPTABLE = "acceptable" # Older but usable
    POOR = "poor"           # Gaps or quality issues

@dataclass
class DataFlowConfig:
    """Configuration for unified data flow"""
    # Performance settings
    max_concurrent_streams: int = 10
    data_batch_size: int = 100
    processing_timeout_seconds: float = 5.0
    
    # Quality settings
    min_data_quality: DataQuality = DataQuality.ACCEPTABLE
    data_validation_enabled: bool = True
    deduplication_enabled: bool = True
    
    # Source priorities
    enable_websocket: bool = True
    enable_rest_fallback: bool = True
    enable_persistence_cache: bool = True
    
    # Integration settings
    auto_persist_data: bool = True
    enable_signal_routing: bool = True
    enable_risk_integration: bool = True

@dataclass
class DataFlowMetrics:
    """Data flow performance metrics"""
    total_data_points: int = 0
    data_points_per_second: float = 0.0
    average_latency_ms: float = 0.0
    data_quality_distribution: Dict[str, int] = field(default_factory=dict)
    source_utilization: Dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class UnifiedDataFlow:
    """
    Unified Data Flow System
    
    Features:
    - Seamless integration of enhanced persistence with hybrid client
    - Real-time data quality monitoring and validation
    - Intelligent source failover and data fusion
    - High-performance streaming with enterprise-grade reliability
    - Complete integration with all trading services
    """
    
    def __init__(self, config: DataFlowConfig = None):
        self.config = config or DataFlowConfig()
        self.is_running = False
        self.start_time = None
        
        # Core components
        self.enhanced_persistence = None
        self.hybrid_client = None
        self.market_data_service = None
        
        # Trading engines
        self.enterprise_engine = None
        self.entry_engine = None
        self.exit_engine = None
        self.risk_manager = None
        self.emergency_controls = None
        self.portfolio = None
        
        # Data flow management
        self.data_streams = {}
        self.stream_tasks = []
        self.data_subscribers = {}  # service -> callback functions
        
        # Performance tracking
        self.metrics = DataFlowMetrics()
        self.performance_history = []
        
        # Data routing
        self.signal_handlers = {}
        self.data_processors = {}
        
        # State management
        self.last_market_data = {}
        self.current_signals = {}
        self.active_positions = {}

    async def initialize(self) -> Dict[str, Any]:
        """Initialize unified data flow system"""
        try:
            logger.info("🚀 Initializing Unified Data Flow System...")
            
            # Initialize enhanced persistence with high-performance config
            persistence_config = PersistenceConfig(
                batch_size=200,  # Higher batch size for better performance
                batch_timeout_seconds=15.0,  # Faster processing
                validation_enabled=True,
                deduplication_enabled=True,
                analytics_enabled=True
            )
            
            self.enhanced_persistence = EnhancedMarketPersistence(persistence_config)
            await self.enhanced_persistence.initialize()
            
            # Initialize hybrid client
            self.hybrid_client = BinanceHybridClient()
            await self.hybrid_client.initialize()
            
            # Start WebSocket streams for real-time data
            await self.hybrid_client.start_websocket_stream("ticker", "BTCUSDT")
            await self.hybrid_client.start_websocket_stream("kline_1m", "BTCUSDT")
            
            # Initialize market data service
            self.market_data_service = await get_live_market_data_service()
            
            # Initialize trading engines
            await self._initialize_trading_engines()
            
            # Setup data flow routing
            await self._setup_data_routing()
            
            # Initialize performance tracking
            await self._initialize_performance_tracking()
            
            self.start_time = datetime.now(timezone.utc)
            logger.info("✅ Unified Data Flow System initialized successfully")
            
            return {
                "status": "success",
                "components_initialized": 7,
                "data_streams_configured": len(self.data_streams),
                "performance_tracking": "active"
            }
            
        except Exception as e:
            logger.error(f"❌ Unified data flow initialization failed: {e}")
            raise RuntimeError(f"Data flow initialization failed: {e}")

    async def _initialize_trading_engines(self):
        """Initialize all trading engines for integration"""
        
        # Enterprise trading engine
        self.enterprise_engine = EnterpriseTradingEngine()
        await self.enterprise_engine.initialize()
        
        # Entry and exit engines
        self.entry_engine = IntelligentEntryEngine()
        await self.entry_engine.initialize()
        
        self.exit_engine = IntelligentExitEngine()
        await self.exit_engine.initialize()
        
        # Risk management
        self.risk_manager = DynamicRiskManager()
        
        # Emergency controls
        self.emergency_controls = EmergencyControlSystem()
        
        # Portfolio management
        self.portfolio = await get_professional_portfolio("system")
        
        logger.info("✅ All trading engines initialized for data flow integration")

    async def _setup_data_routing(self):
        """Setup intelligent data routing between components"""
        
        # Register data processors
        self.data_processors = {
            "market_data": self._process_market_data,
            "trading_signal": self._process_trading_signal,
            "risk_assessment": self._process_risk_assessment,
            "position_update": self._process_position_update,
            "emergency_event": self._process_emergency_event
        }
        
        # Register signal handlers for trading engines
        self.signal_handlers = {
            "enterprise_signal": self._handle_enterprise_signal,
            "entry_signal": self._handle_entry_signal,
            "exit_signal": self._handle_exit_signal,
            "risk_signal": self._handle_risk_signal,
            "emergency_signal": self._handle_emergency_signal
        }
        
        # Setup data subscribers
        self.data_subscribers = {
            "enhanced_persistence": [self._route_to_persistence],
            "enterprise_engine": [self._route_to_enterprise],
            "risk_manager": [self._route_to_risk_manager],
            "entry_engine": [self._route_to_entry_engine],
            "exit_engine": [self._route_to_exit_engine],
            "portfolio": [self._route_to_portfolio]
        }

    async def _initialize_performance_tracking(self):
        """Initialize comprehensive performance tracking"""
        
        # Initialize metrics
        self.metrics.data_quality_distribution = {
            "excellent": 0,
            "good": 0,
            "acceptable": 0,
            "poor": 0
        }
        
        self.metrics.source_utilization = {
            "websocket": 0,
            "rest_api": 0,
            "persistence_cache": 0,
            "database": 0
        }

    async def start(self) -> Dict[str, Any]:
        """Start unified data flow processing"""
        try:
            logger.info("🚀 Starting Unified Data Flow...")
            
            self.is_running = True
            
            # Start main data flow loop
            main_flow_task = asyncio.create_task(self._main_data_flow_loop())
            self.stream_tasks.append(main_flow_task)
            
            # Start signal processing loop
            signal_processing_task = asyncio.create_task(self._signal_processing_loop())
            self.stream_tasks.append(signal_processing_task)
            
            # Start performance monitoring
            performance_task = asyncio.create_task(self._performance_monitoring_loop())
            self.stream_tasks.append(performance_task)
            
            logger.info("✅ Unified Data Flow started successfully")
            
            return {
                "status": "success",
                "active_streams": len(self.stream_tasks),
                "data_flow": "active",
                "performance_monitoring": "active"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to start unified data flow: {e}")
            raise RuntimeError(f"Data flow start failed: {e}")

    async def _main_data_flow_loop(self):
        """Main data flow processing loop"""
        while self.is_running:
            try:
                start_time = time.time()
                
                # Get fresh market data from hybrid client
                market_data = await self._get_unified_market_data()
                
                if market_data:
                    # Process through enhanced persistence
                    await self._process_through_enhanced_persistence(market_data)
                    
                    # Route to trading engines
                    await self._route_market_data_to_engines(market_data)
                    
                    # Update performance metrics
                    processing_time = (time.time() - start_time) * 1000
                    await self._update_performance_metrics(processing_time, market_data)
                
                # Control loop frequency (15-second cycles for day trading)
                await asyncio.sleep(15.0)
                
            except Exception as e:
                logger.error(f"Main data flow error: {e}")
                self.metrics.error_count += 1
                await asyncio.sleep(5.0)  # Brief pause on error

    async def _get_unified_market_data(self) -> Optional[Dict[str, Any]]:
        """Get unified market data from multiple sources with intelligent fallback"""
        try:
            # Primary source: Hybrid client (WebSocket + REST)
            price_data = await get_live_price_hybrid()
            candles_data = await get_live_candles_hybrid(limit=200)
            
            if price_data and candles_data["candles"]:
                unified_data = {
                    "timestamp": datetime.now(timezone.utc),
                    "symbol": "BTCUSDT",
                    "price": price_data["price"],
                    "price_source": price_data["source"],
                    "candles": candles_data["candles"][-100:],  # Last 100 candles
                    "candles_source": candles_data["source"],
                    "candles_count": len(candles_data["candles"]),
                    "data_quality": self._assess_data_quality(price_data, candles_data)
                }
                
                # Update source utilization metrics
                self.metrics.source_utilization[price_data["source"]] += 1
                
                return unified_data
            
        except Exception as e:
            logger.error(f"Failed to get unified market data: {e}")
            self.metrics.error_count += 1
        
        return None

    def _assess_data_quality(self, price_data: Dict, candles_data: Dict) -> DataQuality:
        """Assess overall data quality"""
        
        # Check data freshness and completeness
        if (price_data.get("source") == "websocket" and 
            candles_data.get("source") == "websocket" and
            len(candles_data.get("candles", [])) >= 100):
            return DataQuality.EXCELLENT
        
        elif (price_data and candles_data.get("candles") and
              len(candles_data["candles"]) >= 50):
            return DataQuality.GOOD
        
        elif price_data and candles_data.get("candles"):
            return DataQuality.ACCEPTABLE
        
        else:
            return DataQuality.POOR

    async def _process_through_enhanced_persistence(self, market_data: Dict[str, Any]):
        """Process data through enhanced persistence layer"""
        try:
            # Process current price tick
            ticker_data = {
                "symbol": market_data["symbol"],
                "price": market_data["price"],
                "timestamp": int(market_data["timestamp"].timestamp() * 1000),
                "source": market_data["price_source"]
            }
            
            # Ingest ticker data
            await self.enhanced_persistence.ingest_market_data(ticker_data, "ticker")
            
            # Process recent candles
            for candle in market_data["candles"][-5:]:  # Process last 5 candles
                candle_data = {
                    "symbol": market_data["symbol"],
                    "timestamp": candle.get("timestamp", candle.get("close_time")),
                    "interval": "1m",
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"],
                    "volume": candle["volume"],
                    "source": market_data["candles_source"]
                }
                
                # Ingest candle data with quality validation
                result = await self.enhanced_persistence.ingest_market_data(candle_data, "candle")
                
                # Track quality distribution
                quality_score = result.get("quality_score", 0.0)
                if quality_score >= 0.9:
                    self.metrics.data_quality_distribution["excellent"] += 1
                elif quality_score >= 0.8:
                    self.metrics.data_quality_distribution["good"] += 1
                elif quality_score >= 0.7:
                    self.metrics.data_quality_distribution["acceptable"] += 1
                else:
                    self.metrics.data_quality_distribution["poor"] += 1
            
        except Exception as e:
            logger.error(f"Enhanced persistence processing error: {e}")
            self.metrics.error_count += 1

    async def _route_market_data_to_engines(self, market_data: Dict[str, Any]):
        """Route market data to all trading engines"""
        try:
            # Store latest market data
            self.last_market_data = market_data
            
            # Route to all subscribers
            for subscriber, callbacks in self.data_subscribers.items():
                for callback in callbacks:
                    try:
                        await callback(market_data)
                    except Exception as e:
                        logger.error(f"Error routing to {subscriber}: {e}")
            
        except Exception as e:
            logger.error(f"Market data routing error: {e}")
            self.metrics.error_count += 1

    async def _signal_processing_loop(self):
        """Process trading signals from all engines"""
        while self.is_running:
            try:
                if not self.last_market_data:
                    await asyncio.sleep(1.0)
                    continue
                
                # Generate enterprise signal
                enterprise_signal = await self._generate_enterprise_signal()
                
                if enterprise_signal:
                    # Process through risk management
                    risk_assessment = await self._process_risk_assessment(enterprise_signal)
                    
                    # Route through entry/exit engines
                    if enterprise_signal.get("action") in ["BUY", "SELL"]:
                        await self._process_entry_exit_signals(enterprise_signal, risk_assessment)
                
                # Control signal processing frequency
                await asyncio.sleep(15.0)  # 15-second cycles
                
            except Exception as e:
                logger.error(f"Signal processing error: {e}")
                await asyncio.sleep(5.0)

    async def _generate_enterprise_signal(self) -> Optional[Dict[str, Any]]:
        """Generate signal from enterprise engine"""
        try:
            if not self.enterprise_engine:
                return None
            
            # Generate signal using current market data
            signal = await self.enterprise_engine.generate_signal("BTCUSDT")
            
            if signal:
                signal_data = {
                    "symbol": signal.symbol,
                    "action": signal.action,
                    "confidence": signal.confidence,
                    "price": signal.price,
                    "reasoning": signal.reasoning,
                    "risk_score": signal.risk_score,
                    "timestamp": signal.timestamp,
                    "layer_analysis": signal.layer_analysis
                }
                
                self.current_signals["enterprise"] = signal_data
                return signal_data
            
        except Exception as e:
            logger.error(f"Enterprise signal generation error: {e}")
            self.metrics.error_count += 1
        
        return None

    async def _process_risk_assessment(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Process risk assessment for trading signal"""
        try:
            if not self.risk_manager:
                return {"risk_score": 0.5, "block_reason": None}
            
            # Create mock risk context for assessment
            risk_context = await self.risk_manager.assess_pre_trade(
                signal=signal,
                portfolio=self.portfolio,
                candles=self.last_market_data.get("candles", []),
                tick={"price": self.last_market_data.get("price", 0)}
            )
            
            risk_data = {
                "risk_score": risk_context.risk_score,
                "block_reason": risk_context.block_reason,
                "volatility": risk_context.market_volatility,
                "position_heat": risk_context.position_heat,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.current_signals["risk"] = risk_data
            return risk_data
            
        except Exception as e:
            logger.error(f"Risk assessment error: {e}")
            return {"risk_score": 0.8, "block_reason": "risk_assessment_failed"}

    async def _process_entry_exit_signals(self, signal: Dict[str, Any], risk: Dict[str, Any]):
        """Process entry and exit signals"""
        try:
            # Skip if risk blocks the trade
            if risk.get("block_reason"):
                logger.info(f"🛡️ Trade blocked by risk: {risk['block_reason']}")
                return
            
            # Process entry signal
            if signal["action"] in ["BUY", "SELL"]:
                entry_decision = await self._process_entry_signal(signal, risk)
                
                if entry_decision and entry_decision.get("should_enter"):
                    await self._execute_position_entry(signal, risk, entry_decision)
            
            # Process exit signals for existing positions
            await self._process_exit_signals()
            
        except Exception as e:
            logger.error(f"Entry/exit processing error: {e}")

    async def _process_entry_signal(self, signal: Dict[str, Any], risk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process entry signal through entry engine"""
        try:
            if not self.entry_engine:
                return None
            
            # Use entry engine to analyze entry opportunity
            entry_analysis = await self.entry_engine.analyze_entry_opportunity(
                signal=signal,
                current_price=self.last_market_data.get("price", 0),
                candles=self.last_market_data.get("candles", []),
                portfolio=self.portfolio,
                risk_context=risk
            )
            
            return {
                "should_enter": entry_analysis.should_enter,
                "confidence": entry_analysis.confidence,
                "reasoning": entry_analysis.entry_reason.value if hasattr(entry_analysis, 'entry_reason') else "ai_analysis",
                "recommended_size": getattr(entry_analysis, 'recommended_size', 0.02)
            }
            
        except Exception as e:
            logger.error(f"Entry signal processing error: {e}")
            return None

    async def _process_exit_signals(self):
        """Process exit signals for active positions"""
        try:
            if not self.exit_engine or not self.portfolio:
                return
            
            # Get active positions
            positions = await self.portfolio.get_active_positions()
            
            for position in positions:
                exit_analysis = await self.exit_engine.analyze_exit_opportunity(
                    position=position,
                    current_price=self.last_market_data.get("price", 0),
                    candles=self.last_market_data.get("candles", [])
                )
                
                if exit_analysis and exit_analysis.should_exit:
                    await self._execute_position_exit(position, exit_analysis)
            
        except Exception as e:
            logger.error(f"Exit signal processing error: {e}")

    async def _execute_position_entry(self, signal: Dict[str, Any], risk: Dict[str, Any], entry: Dict[str, Any]):
        """Execute position entry"""
        try:
            if not self.portfolio:
                return
            
            # Calculate position size
            size = await self.risk_manager.position_size(
                signal=signal,
                risk_ctx=risk,
                portfolio=self.portfolio,
                tick={"price": self.last_market_data.get("price", 0)}
            )
            
            # Open position
            from app.backend.services.professional_portfolio import PositionType
            position_type = PositionType.LONG if signal["action"] == "BUY" else PositionType.SHORT
            
            position_id = await self.portfolio.open_position(
                symbol=signal["symbol"],
                position_type=position_type,
                size=size,
                ai_confidence=signal["confidence"],
                ai_reasoning=f"{signal['reasoning']} | Entry: {entry['reasoning']}"
            )
            
            logger.info(f"💰 Position opened: {position_id} | {signal['action']} {size} @ ${self.last_market_data.get('price', 0)}")
            
        except Exception as e:
            logger.error(f"Position entry execution error: {e}")

    async def _execute_position_exit(self, position: Any, exit_analysis: Any):
        """Execute position exit"""
        try:
            await self.portfolio.close_position(
                position.position_id,
                reason=exit_analysis.exit_reason
            )
            
            logger.info(f"💰 Position closed: {position.position_id} | Reason: {exit_analysis.exit_reason}")
            
        except Exception as e:
            logger.error(f"Position exit execution error: {e}")

    # Data routing callbacks
    async def _route_to_persistence(self, data: Dict[str, Any]):
        """Route data to enhanced persistence"""
        # Already handled in main flow
        pass

    async def _route_to_enterprise(self, data: Dict[str, Any]):
        """Route data to enterprise engine"""
        # Market data routing handled in signal generation
        pass

    async def _route_to_risk_manager(self, data: Dict[str, Any]):
        """Route data to risk manager"""
        # Risk assessment handled in signal processing
        pass

    async def _route_to_entry_engine(self, data: Dict[str, Any]):
        """Route data to entry engine"""
        # Entry analysis handled in signal processing
        pass

    async def _route_to_exit_engine(self, data: Dict[str, Any]):
        """Route data to exit engine"""
        # Exit analysis handled in signal processing
        pass

    async def _route_to_portfolio(self, data: Dict[str, Any]):
        """Route data to portfolio"""
        # Portfolio updates handled in position management
        pass

    async def _performance_monitoring_loop(self):
        """Continuous performance monitoring"""
        while self.is_running:
            try:
                # Update metrics
                current_time = datetime.now(timezone.utc)
                uptime_seconds = (current_time - self.start_time).total_seconds()
                
                # Calculate throughput
                if uptime_seconds > 0:
                    self.metrics.data_points_per_second = self.metrics.total_data_points / uptime_seconds
                
                # Update last updated time
                self.metrics.last_updated = current_time
                
                # Log performance summary
                if self.metrics.total_data_points > 0 and self.metrics.total_data_points % 100 == 0:
                    logger.info(f"📊 Performance: {self.metrics.data_points_per_second:.1f} data points/sec, "
                              f"{self.metrics.average_latency_ms:.1f}ms avg latency, "
                              f"{self.metrics.error_count} errors")
                
                await asyncio.sleep(60.0)  # Update every minute
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(10.0)

    async def _update_performance_metrics(self, processing_time_ms: float, market_data: Dict[str, Any]):
        """Update performance metrics"""
        self.metrics.total_data_points += 1
        
        # Update average latency with exponential moving average
        alpha = 0.1
        if self.metrics.average_latency_ms == 0:
            self.metrics.average_latency_ms = processing_time_ms
        else:
            self.metrics.average_latency_ms = (alpha * processing_time_ms + 
                                            (1 - alpha) * self.metrics.average_latency_ms)

    async def get_unified_status(self) -> Dict[str, Any]:
        """Get comprehensive unified data flow status"""
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0
        
        return {
            "status": "running" if self.is_running else "stopped",
            "uptime_seconds": uptime,
            "components": {
                "enhanced_persistence": "active" if self.enhanced_persistence else "inactive",
                "hybrid_client": "active" if self.hybrid_client else "inactive",
                "trading_engines": len([e for e in [self.enterprise_engine, self.entry_engine, self.exit_engine] if e])
            },
            "performance": {
                "total_data_points": self.metrics.total_data_points,
                "data_points_per_second": self.metrics.data_points_per_second,
                "average_latency_ms": self.metrics.average_latency_ms,
                "error_count": self.metrics.error_count,
                "data_quality_distribution": self.metrics.data_quality_distribution,
                "source_utilization": self.metrics.source_utilization
            },
            "current_state": {
                "last_market_data_timestamp": self.last_market_data.get("timestamp"),
                "current_price": self.last_market_data.get("price"),
                "active_signals": len(self.current_signals),
                "active_streams": len(self.stream_tasks)
            }
        }

    async def shutdown(self):
        """Graceful shutdown of unified data flow"""
        logger.info("🛑 Shutting down Unified Data Flow...")
        
        self.is_running = False
        
        # Cancel all stream tasks
        for task in self.stream_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.stream_tasks, return_exceptions=True)
        
        # Shutdown components
        if self.enhanced_persistence:
            await self.enhanced_persistence.shutdown()
        
        if self.hybrid_client:
            await self.hybrid_client.shutdown()
        
        logger.info("✅ Unified Data Flow shutdown complete")


# Global unified data flow instance
_unified_data_flow = None

async def get_unified_data_flow(config: DataFlowConfig = None) -> UnifiedDataFlow:
    """Get or create unified data flow instance"""
    global _unified_data_flow
    if _unified_data_flow is None:
        _unified_data_flow = UnifiedDataFlow(config)
        await _unified_data_flow.initialize()
    return _unified_data_flow