"""
Pipeline Debug Logger - TradePulse.AI
====================================

Comprehensive debug logging utility for pipeline component status tracking
and operational visibility during startup and runtime.

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ComponentStatus(str, Enum):
    """Component status enumeration"""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"
    UNKNOWN = "unknown"

@dataclass
class ComponentInfo:
    """Component information structure"""
    name: str
    version: str
    purpose: str
    status: ComponentStatus
    initialization_time: Optional[datetime] = None
    error_message: Optional[str] = None
    dependencies: List[str] = None

class PipelineDebugLogger:
    """
    Comprehensive pipeline debug logger for component status tracking
    """
    
    def __init__(self):
        self.components: Dict[str, ComponentInfo] = {}
        self.startup_time = datetime.now(timezone.utc)
        self.is_logging_enabled = True
        
    def register_component(self, 
                          component_id: str, 
                          name: str, 
                          version: str, 
                          purpose: str,
                          dependencies: List[str] = None) -> None:
        """Register a pipeline component for tracking"""
        self.components[component_id] = ComponentInfo(
            name=name,
            version=version,
            purpose=purpose,
            status=ComponentStatus.INITIALIZING,
            dependencies=dependencies or []
        )
        
        if self.is_logging_enabled:
            logger.info(f"📊 PIPELINE DEBUG: Registered component '{name}' ({component_id})")
    
    def update_component_status(self, 
                               component_id: str, 
                               status: ComponentStatus,
                               error_message: str = None) -> None:
        """Update component status"""
        if component_id not in self.components:
            logger.warning(f"⚠️ PIPELINE DEBUG: Unknown component '{component_id}'")
            return
            
        component = self.components[component_id]
        old_status = component.status
        component.status = status
        component.error_message = error_message
        
        if status == ComponentStatus.READY:
            component.initialization_time = datetime.now(timezone.utc)
        
        if self.is_logging_enabled:
            status_emoji = {
                ComponentStatus.INITIALIZING: "🔄",
                ComponentStatus.READY: "✅",
                ComponentStatus.RUNNING: "🚀",
                ComponentStatus.ERROR: "❌",
                ComponentStatus.STOPPED: "⏹️",
                ComponentStatus.UNKNOWN: "❓"
            }
            
            emoji = status_emoji.get(status, "❓")
            logger.info(f"{emoji} PIPELINE DEBUG: {component.name} - {old_status.value} → {status.value}")
            
            if error_message:
                logger.error(f"💥 PIPELINE DEBUG: {component.name} - Error: {error_message}")
    
    def log_startup_banner(self) -> None:
        """Log comprehensive startup banner"""
        if not self.is_logging_enabled:
            return
            
        logger.info("=" * 100)
        logger.info("🔥 TRADEPULSE.AI PIPELINE DEBUG - COMPREHENSIVE COMPONENT TRACKING")
        logger.info("=" * 100)
        logger.info(f"🎯 Application: TradePulse.AI Enterprise Backend v1.0.0")
        logger.info(f"🎯 Mode: Professional Live Data Mode (NO MOCKS/FALLBACKS)")
        logger.info(f"🎯 Startup Time: {self.startup_time.isoformat()}")
        logger.info(f"🎯 Registered Components: {len(self.components)}")
        logger.info("=" * 100)
        logger.info("📊 PIPELINE ARCHITECTURE:")
        logger.info("  🧠 BRAIN Controller → FSM Orchestrator (INIT→WARMUP→RUNNING→HALT→COOLDOWN)")
        logger.info("  🤖 Enterprise Trading Engine → 6-Layer AI Signal Generation")
        logger.info("  📈 Intelligent Entry Engine → Entry Point Optimization")
        logger.info("  📉 Intelligent Exit Engine → Position Exit Management")
        logger.info("  🎯 Day Trading Engine → High-Frequency Coordination")
        logger.info("  📊 Live Market Data Service → Real-time WebSocket Streaming")
        logger.info("  🛡️ Dynamic Risk Manager → Risk Assessment & Controls")
        logger.info("  🚨 Emergency Control System → Safety & Circuit Breakers")
        logger.info("=" * 100)
    
    def log_component_status_summary(self) -> None:
        """Log comprehensive component status summary"""
        if not self.is_logging_enabled:
            return
            
        logger.info("=" * 100)
        logger.info("📊 PIPELINE DEBUG: COMPONENT STATUS SUMMARY")
        logger.info("=" * 100)
        
        status_counts = {status: 0 for status in ComponentStatus}
        
        for component_id, component in self.components.items():
            status_counts[component.status] += 1
            
            status_emoji = {
                ComponentStatus.INITIALIZING: "🔄",
                ComponentStatus.READY: "✅",
                ComponentStatus.RUNNING: "🚀",
                ComponentStatus.ERROR: "❌",
                ComponentStatus.STOPPED: "⏹️",
                ComponentStatus.UNKNOWN: "❓"
            }
            
            emoji = status_emoji.get(component.status, "❓")
            init_time = component.initialization_time.strftime("%H:%M:%S") if component.initialization_time else "N/A"
            
            logger.info(f"{emoji} {component.name} ({component_id})")
            logger.info(f"   Purpose: {component.purpose}")
            logger.info(f"   Status: {component.status.value.upper()}")
            logger.info(f"   Version: {component.version}")
            logger.info(f"   Init Time: {init_time}")
            
            if component.dependencies:
                logger.info(f"   Dependencies: {', '.join(component.dependencies)}")
            
            if component.error_message:
                logger.error(f"   Error: {component.error_message}")
            
            logger.info("")
        
        logger.info("📊 STATUS SUMMARY:")
        for status, count in status_counts.items():
            if count > 0:
                emoji = {
                    ComponentStatus.INITIALIZING: "🔄",
                    ComponentStatus.READY: "✅",
                    ComponentStatus.RUNNING: "🚀",
                    ComponentStatus.ERROR: "❌",
                    ComponentStatus.STOPPED: "⏹️",
                    ComponentStatus.UNKNOWN: "❓"
                }[status]
                logger.info(f"  {emoji} {status.value.upper()}: {count} components")
        
        logger.info("=" * 100)
    
    def log_pipeline_ready(self) -> None:
        """Log pipeline ready status"""
        if not self.is_logging_enabled:
            return
            
        ready_count = sum(1 for c in self.components.values() if c.status == ComponentStatus.READY)
        total_count = len(self.components)
        
        logger.info("=" * 100)
        logger.info("🎯 PIPELINE DEBUG: PIPELINE READINESS STATUS")
        logger.info("=" * 100)
        logger.info(f"✅ Components Ready: {ready_count}/{total_count}")
        
        if ready_count == total_count:
            logger.info("🚀 PIPELINE DEBUG: ALL COMPONENTS READY - PIPELINE OPERATIONAL")
            logger.info("🎯 PIPELINE DEBUG: Ready for live trading operations")
        else:
            logger.warning(f"⚠️ PIPELINE DEBUG: {total_count - ready_count} components not ready")
            
            not_ready = [c.name for c in self.components.values() if c.status != ComponentStatus.READY]
            logger.warning(f"⚠️ PIPELINE DEBUG: Not ready: {', '.join(not_ready)}")
        
        logger.info("=" * 100)
    
    def log_trading_cycle_start(self, cycle_number: int) -> None:
        """Log trading cycle start"""
        if self.is_logging_enabled:
            logger.info(f"🔄 PIPELINE DEBUG: Trading Cycle #{cycle_number} - Starting 7-step process")
    
    def log_trading_cycle_step(self, cycle_number: int, step: str, description: str) -> None:
        """Log trading cycle step"""
        if self.is_logging_enabled:
            logger.info(f"📊 PIPELINE DEBUG: Cycle #{cycle_number} - Step {step}: {description}")
    
    def log_trading_cycle_complete(self, cycle_number: int, duration_ms: float) -> None:
        """Log trading cycle completion"""
        if self.is_logging_enabled:
            logger.info(f"✅ PIPELINE DEBUG: Trading Cycle #{cycle_number} - Completed in {duration_ms:.1f}ms")
    
    def enable_logging(self) -> None:
        """Enable debug logging"""
        self.is_logging_enabled = True
        logger.info("🔊 PIPELINE DEBUG: Debug logging ENABLED")
    
    def disable_logging(self) -> None:
        """Disable debug logging"""
        logger.info("🔇 PIPELINE DEBUG: Debug logging DISABLED")
        self.is_logging_enabled = False

# Global pipeline debug logger instance
_pipeline_debug_logger = None

def get_pipeline_debug_logger() -> PipelineDebugLogger:
    """Get global pipeline debug logger instance"""
    global _pipeline_debug_logger
    if _pipeline_debug_logger is None:
        _pipeline_debug_logger = PipelineDebugLogger()
    return _pipeline_debug_logger

def register_pipeline_component(component_id: str, 
                               name: str, 
                               version: str, 
                               purpose: str,
                               dependencies: List[str] = None) -> None:
    """Register a pipeline component for tracking"""
    logger_instance = get_pipeline_debug_logger()
    logger_instance.register_component(component_id, name, version, purpose, dependencies)

def update_pipeline_component_status(component_id: str, 
                                    status: ComponentStatus,
                                    error_message: str = None) -> None:
    """Update pipeline component status"""
    logger_instance = get_pipeline_debug_logger()
    logger_instance.update_component_status(component_id, status, error_message)

def log_pipeline_startup_banner() -> None:
    """Log pipeline startup banner"""
    logger_instance = get_pipeline_debug_logger()
    logger_instance.log_startup_banner()

def log_pipeline_status_summary() -> None:
    """Log pipeline status summary"""
    logger_instance = get_pipeline_debug_logger()
    logger_instance.log_component_status_summary()

def log_pipeline_ready() -> None:
    """Log pipeline ready status"""
    logger_instance = get_pipeline_debug_logger()
    logger_instance.log_pipeline_ready()
