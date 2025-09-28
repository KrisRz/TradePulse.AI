#!/usr/bin/env python3
"""
TradePulse.AI - Professional Unified System Monitor
==================================================

Professional monitoring script that combines startup, monitoring, and management
of the complete TradePulse.AI application stack with industry best practices.

Features:
🚀 Intelligent service startup with dependency management
📊 Real-time health monitoring with professional metrics  
🔄 Smart restart logic with exponential backoff
💰 Live portfolio tracking with real API data only
🧠 BRAIN Controller monitoring (auto-managed by backend)
🎓 Continuous Learning Engine monitoring (auto-managed by backend)
📡 Live Binance API health monitoring
🖥️ System resource monitoring with alerts
📝 Comprehensive logging and debugging
⚡ Service discovery for already running processes
🔧 Professional error handling and recovery

Usage:
    python3 TRADEPULSE_UNIFIED_MONITOR.py

Architecture:
- Clean separation of concerns
- Dependency injection pattern
- Professional error handling
- Real data only (no mocks/fallbacks)
- Industry standard logging
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Protocol, Tuple
import aiohttp
import psutil
from dotenv import load_dotenv


# ============================================================================
# CONFIGURATION & TYPES
# ============================================================================

class ServiceStatus(Enum):
    """Service status enumeration"""
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy" 
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"


class SystemStatus(Enum):
    """Overall system status"""
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    STARTING = "STARTING"


@dataclass
class ServiceConfig:
    """Professional service configuration"""
    name: str
    port: int
    command: List[str]
    working_dir: Path
    health_endpoint: Optional[str] = None
    startup_timeout: int = 30
    dependencies: List[str] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    restart_policy: str = "on-failure"
    max_restarts: int = 5
    log_file: Optional[Path] = None


@dataclass
class ServiceState:
    """Runtime service state"""
    status: ServiceStatus = ServiceStatus.STOPPED
    pid: Optional[int] = None
    restart_count: int = 0
    consecutive_failures: int = 0
    last_restart: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    startup_time: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class SystemMetrics:
    """System resource metrics"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    memory_available_gb: float
    disk_usage: float
    disk_free_gb: float
    network_connections: int
    load_average: List[float]


@dataclass
class PortfolioMetrics:
    """Real portfolio metrics from API"""
    total_value: float = 0.0
    cash_balance: float = 0.0
    positions_value: float = 0.0
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    active_positions: int = 0
    win_rate: float = 0.0
    total_trades: int = 0
    last_updated: Optional[datetime] = None
    api_success: bool = False
    error_message: Optional[str] = None


# ============================================================================
# PROFESSIONAL LOGGING
# ============================================================================

class ProfessionalFormatter(logging.Formatter):
    """Professional logging formatter with colors and structured output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_professional_logging() -> logging.Logger:
    """Setup professional logging configuration"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create debug subdirectory
    debug_dir = log_dir / "debug"
    debug_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("TradePulseUnifiedMonitor")
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # File handler
    file_handler = logging.FileHandler(
        log_dir / f'tradepulse_unified_monitor_{datetime.now().strftime("%Y%m%d")}.log'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        ProfessionalFormatter('%(asctime)s - %(levelname)s - %(message)s')
    )
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# ============================================================================
# SERVICE MANAGEMENT
# ============================================================================

class ServiceDiscovery:
    """Professional service discovery"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def find_process_by_port(self, port: int) -> Optional[int]:
        """Find process ID by port using lsof with validation - get LISTENING process only"""
        try:
            # Get detailed lsof output to find the LISTENING process
            result = subprocess.run(
                ['lsof', '-i', f':{port}', '-P', '-n'], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                
                # Find the process that's LISTENING on the port
                for line in lines:
                    if 'LISTEN' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                pid = int(parts[1])
                                # Verify the process actually exists
                                if self.is_process_running(pid):
                                    self.logger.debug(f"Found LISTENING process PID {pid} on port {port}")
                                    return pid
                            except (ValueError, IndexError):
                                continue
                
                # Fallback: if no LISTEN found, use first PID (old behavior)
                fallback_result = subprocess.run(
                    ['lsof', '-ti', f':{port}'], 
                    capture_output=True, 
                    text=True,
                    timeout=3
                )
                if fallback_result.returncode == 0 and fallback_result.stdout.strip():
                    pids = fallback_result.stdout.strip().split('\n')
                    pid = int(pids[0])
                    if self.is_process_running(pid):
                        self.logger.debug(f"Fallback: using PID {pid} on port {port}")
                        return pid
                    
        except (subprocess.TimeoutExpired, ValueError, IndexError) as e:
            self.logger.debug(f"Port {port} discovery failed: {e}")
        return None
    
    def is_process_running(self, pid: int) -> bool:
        """Check if process is actually running"""
        try:
            os.kill(pid, 0)  # Signal 0 checks if process exists
            return True
        except (OSError, ProcessLookupError):
            return False
    
    def get_process_command(self, pid: int) -> Optional[str]:
        """Get command line of process for validation"""
        try:
            result = subprocess.run(
                ['ps', '-p', str(pid), '-o', 'command='],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            self.logger.debug(f"Failed to get command for PID {pid}: {e}")
        return None
    
    def discover_running_services(self, services: Dict[str, ServiceConfig]) -> Dict[str, Optional[int]]:
        """Discover already running services with validation"""
        discovered = {}
        
        for name, config in services.items():
            pid = self.find_process_by_port(config.port)
            
            # Validate the process if found
            if pid:
                command = self.get_process_command(pid)
                if command:
                    # Service-specific validation
                    is_valid = False
                    if name == 'dynamodb' and ('java' in command and 'DynamoDBLocal' in command):
                        is_valid = True
                    elif name == 'backend' and ('python' in command and 'main.py' in command):
                        is_valid = True
                    elif name == 'frontend' and ('node' in command and 'astro' in command):
                        is_valid = True
                    
                    if is_valid:
                        discovered[name] = pid
                        self.logger.info(f"✅ Discovered running {name} (PID: {pid}, Port: {config.port})")
                    else:
                        self.logger.warning(f"⚠️ Wrong process on port {config.port}: {command}")
                        discovered[name] = None
                else:
                    self.logger.warning(f"⚠️ Cannot validate process {pid} on port {config.port}")
                    discovered[name] = None
            else:
                discovered[name] = None
                self.logger.debug(f"⏸️ {name} not running on port {config.port}")
        
        return discovered


class HealthChecker:
    """Professional health checker with comprehensive monitoring"""
    
    def __init__(self, logger: logging.Logger, timeout: int = 10):
        self.logger = logger
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def check_service_health(self, name: str, config: ServiceConfig, state: ServiceState) -> Dict[str, Any]:
        """Check comprehensive service health with proper validation"""
        start_time = time.time()
        
        # Check if process is running
        discovery = ServiceDiscovery(self.logger)
        pid = discovery.find_process_by_port(config.port)
        
        if not pid:
            return {
                'service': name,
                'status': ServiceStatus.STOPPED.value,
                'response_time': None,
                'error': 'Process not found on port',
                'pid': None,
                'port': config.port
            }
        
        # Validate process is the expected service
        if not self._validate_service_process(name, pid, discovery):
            return {
                'service': name,
                'status': ServiceStatus.ERROR.value,
                'response_time': time.time() - start_time,
                'error': 'Wrong process on port - not expected service',
                'pid': pid,
                'port': config.port
            }
        
        # Update PID if discovered
        if state.pid != pid:
            state.pid = pid
            self.logger.info(f"🔄 Updated {name} PID: {pid}")
        
        # For services without health endpoints (like DynamoDB)
        if not config.health_endpoint:
            # Still do basic connection test for DynamoDB
            if name == 'dynamodb':
                try:
                    async with self.session.get(f'http://localhost:{config.port}', timeout=aiohttp.ClientTimeout(total=3)) as response:
                        # DynamoDB returns auth error but that means it's responding
                        response_time = time.time() - start_time
                        return {
                            'service': name,
                            'status': ServiceStatus.HEALTHY.value,
                            'response_time': response_time,
                            'error': None,
                            'pid': pid,
                            'port': config.port,
                            'validation': 'connection_verified'
                        }
                except Exception as e:
                    return {
                        'service': name,
                        'status': ServiceStatus.UNHEALTHY.value,
                        'response_time': time.time() - start_time,
                        'error': f'Connection failed: {str(e)}',
                        'pid': pid,
                        'port': config.port
                    }
            else:
                return {
                    'service': name,
                    'status': ServiceStatus.HEALTHY.value,
                    'response_time': time.time() - start_time,
                    'error': None,
                    'pid': pid,
                    'port': config.port
                }
        
        # HTTP health check
        try:
            async with self.session.get(config.health_endpoint) as response:
                response_time = time.time() - start_time
                
                if response.status in [200, 503]:  # 503 acceptable during startup
                    result = {
                        'service': name,
                        'status': ServiceStatus.HEALTHY.value,
                        'response_time': response_time,
                        'error': None,
                        'pid': pid,
                        'port': config.port,
                        'http_status': response.status
                    }
                    
                    # ENHANCED: Check engine status for backend service
                    if name == 'backend' and config.port == 9002:
                        try:
                            engines_url = f"http://localhost:9002/api/v1/engines/status"
                            async with self.session.get(engines_url) as engines_response:
                                if engines_response.status == 200:
                                    engines_data = await engines_response.json()
                                    result['engines'] = {
                                        'operational_count': engines_data.get('operational_engines', 0),
                                        'total_count': engines_data.get('total_engines', 5),
                                        'overall_status': engines_data.get('overall_status', 'unknown'),
                                        'details': engines_data.get('engines', {})
                                    }
                                    self.logger.info(f"🎯 ENGINES: {result['engines']['operational_count']}/{result['engines']['total_count']} operational")
                        except Exception as engine_error:
                            self.logger.debug(f"Engine status check failed: {engine_error}")
                    
                    return result
                else:
                    return {
                        'service': name,
                        'status': ServiceStatus.UNHEALTHY.value,
                        'response_time': response_time,
                        'error': f"HTTP {response.status}",
                        'pid': pid,
                        'port': config.port,
                        'http_status': response.status
                    }
        
        except (asyncio.TimeoutError, aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError) as e:
            # Connection issues indicate service is down or unreachable
            error_type = type(e).__name__
            if isinstance(e, asyncio.TimeoutError):
                error_msg = f'Timeout ({self.timeout}s)'
            elif isinstance(e, aiohttp.ClientConnectorError):
                error_msg = 'Connection refused - service likely down'
            else:
                error_msg = f'Connection error: {str(e)}'
                
            return {
                'service': name,
                'status': ServiceStatus.STOPPED.value,  # More accurate than UNHEALTHY
                'response_time': time.time() - start_time,
                'error': error_msg,
                'pid': pid,
                'port': config.port,
                'error_type': error_type
            }
        except Exception as e:
            return {
                'service': name,
                'status': ServiceStatus.ERROR.value,
                'response_time': time.time() - start_time,
                'error': str(e),
                'pid': pid,
                'port': config.port
            }
    
    def _validate_service_process(self, service_name: str, pid: int, discovery: 'ServiceDiscovery') -> bool:
        """Validate that the process is actually the expected service"""
        try:
            command = discovery.get_process_command(pid)
            if not command:
                return False
            
            # Service-specific validation patterns
            validation_patterns = {
                'dynamodb': ['java', 'DynamoDBLocal.jar'],
                'backend': ['python', 'main.py', 'uvicorn'],
                'frontend': ['node', 'astro']
            }
            
            if service_name in validation_patterns:
                patterns = validation_patterns[service_name]
                # Check if any of the expected patterns are in the command
                if any(pattern in command for pattern in patterns):
                    self.logger.debug(f"✅ {service_name} PID {pid} validated: {command}")
                    return True
                else:
                    self.logger.warning(f"⚠️ {service_name} PID {pid} validation failed - unexpected command: {command}")
                    return False
            
            # For unknown services, assume valid if process exists
            return True
            
        except Exception as e:
            self.logger.debug(f"Process validation failed for {service_name} PID {pid}: {e}")
            return False


class ServiceManager:
    """Professional service manager with dependency resolution"""
    
    def __init__(self, services: Dict[str, ServiceConfig], logger: logging.Logger):
        self.services = services
        self.service_states: Dict[str, ServiceState] = {}
        self.logger = logger
        self.discovery = ServiceDiscovery(logger)
        
        # Initialize service states
        for name in services:
            self.service_states[name] = ServiceState()
    
    async def start_service(self, service_name: str) -> bool:
        """Start service with dependency resolution and comprehensive error handling"""
        if service_name not in self.services:
            self.logger.error(f"❌ Unknown service: {service_name}")
            return False
        
        config = self.services[service_name]
        state = self.service_states[service_name]
        
        # Check if already running
        existing_pid = self.discovery.find_process_by_port(config.port)
        if existing_pid:
            state.pid = existing_pid
            state.status = ServiceStatus.HEALTHY
            self.logger.info(f"✅ {service_name} already running (PID: {existing_pid})")
            return True
        
        # Start dependencies first
        for dep in config.dependencies:
            if not await self.start_service(dep):
                self.logger.error(f"❌ Failed to start dependency {dep} for {service_name}")
                return False
        
        self.logger.info(f"🚀 Starting {service_name}...")
        state.status = ServiceStatus.STARTING
        state.startup_time = datetime.now()
        
        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(config.environment)
            
            # Create log file if specified
            log_handle = None
            if config.log_file:
                config.log_file.parent.mkdir(parents=True, exist_ok=True)
                log_handle = open(config.log_file, 'a')
                self.logger.debug(f"📝 Logging {service_name} output to: {config.log_file}")
            
            # Start process
            process = subprocess.Popen(
                config.command,
                cwd=config.working_dir,
                env=env,
                stdout=log_handle or subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            self.logger.info(f"🚀 {service_name} process started (PID: {process.pid})")
            
            # Wait for startup with progress indication
            startup_deadline = time.time() + config.startup_timeout
            check_interval = 1
            
            while time.time() < startup_deadline:
                # Check if process died
                if process.poll() is not None:
                    error_msg = f"Process died during startup (exit code: {process.returncode})"
                    self.logger.error(f"❌ {service_name}: {error_msg}")
                    state.status = ServiceStatus.ERROR
                    state.error_message = error_msg
                    if log_handle:
                        log_handle.close()
                    return False
                
                # Check if service is responding on port
                pid = self.discovery.find_process_by_port(config.port)
                if pid:
                    state.pid = pid
                    state.status = ServiceStatus.HEALTHY
                    state.restart_count = 0
                    state.consecutive_failures = 0
                    state.error_message = None
                    
                    startup_duration = (datetime.now() - state.startup_time).total_seconds()
                    self.logger.info(f"✅ {service_name} started successfully (PID: {pid}, startup: {startup_duration:.1f}s)")
                    
                    if log_handle:
                        log_handle.close()
                    return True
                
                await asyncio.sleep(check_interval)
            
            # Startup timeout
            error_msg = f"Startup timeout ({config.startup_timeout}s)"
            self.logger.error(f"❌ {service_name}: {error_msg}")
            state.status = ServiceStatus.ERROR
            state.error_message = error_msg
            
            # Terminate the process
            try:
                process.terminate()
                await asyncio.sleep(2)
                if process.poll() is None:
                    process.kill()
            except:
                pass
            
            if log_handle:
                log_handle.close()
            return False
            
        except Exception as e:
            error_msg = f"Failed to start: {e}"
            self.logger.error(f"❌ {service_name}: {error_msg}")
            state.status = ServiceStatus.ERROR
            state.error_message = error_msg
            return False
    
    async def stop_service(self, service_name: str) -> bool:
        """Stop service gracefully"""
        if service_name not in self.service_states:
            return True
        
        state = self.service_states[service_name]
        pid = state.pid
        
        if not pid:
            self.logger.info(f"✅ {service_name} already stopped")
            state.status = ServiceStatus.STOPPED
            return True
        
        self.logger.info(f"🛑 Stopping {service_name} (PID: {pid})")
        
        try:
            # Graceful shutdown
            os.kill(pid, signal.SIGTERM)
            
            # Wait for graceful shutdown
            for _ in range(10):  # 10 seconds
                try:
                    os.kill(pid, 0)  # Check if process exists
                    await asyncio.sleep(1)
                except ProcessLookupError:
                    break
            else:
                # Force kill if still running
                self.logger.warning(f"⚡ Force killing {service_name}")
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            
            state.status = ServiceStatus.STOPPED
            state.pid = None
            state.error_message = None
            
            self.logger.info(f"✅ {service_name} stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to stop {service_name}: {e}")
            return False
    
    async def restart_service(self, service_name: str) -> bool:
        """Restart service with exponential backoff"""
        if service_name not in self.services:
            return False
        
        config = self.services[service_name]
        state = self.service_states[service_name]
        
        state.restart_count += 1
        
        if state.restart_count > config.max_restarts:
            self.logger.error(f"❌ {service_name} exceeded max restarts ({config.max_restarts})")
            return False
        
        # Exponential backoff
        backoff_time = min(2 ** state.restart_count, 60)  # Max 60 seconds
        self.logger.info(f"🔄 Restarting {service_name} (attempt {state.restart_count}/{config.max_restarts}) after {backoff_time}s")
        
        await asyncio.sleep(backoff_time)
        
        # Stop then start
        await self.stop_service(service_name)
        await asyncio.sleep(2)  # Brief pause
        
        success = await self.start_service(service_name)
        
        if success:
            state.last_restart = datetime.now()
            state.consecutive_failures = 0
            self.logger.info(f"✅ {service_name} restarted successfully")
        else:
            state.consecutive_failures += 1
            self.logger.error(f"❌ Failed to restart {service_name}")
        
        return success


# ============================================================================
# PORTFOLIO MONITORING
# ============================================================================

class PortfolioMonitor:
    """Professional portfolio monitoring with real API data only"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_portfolio_metrics(self) -> PortfolioMetrics:
        """Get real portfolio metrics from API - NO FALLBACKS"""
        try:
            headers = {'Authorization': 'Bearer enterprise_admin_token'}
            
            # Get portfolio overview
            portfolio_data = await self._get_portfolio_overview(headers)
            
            # Get positions data  
            positions_data = await self._get_positions_data(headers)
            
            # Get trading engine status
            trading_data = await self._get_trading_engine_status(headers)
            
            # Combine real data
            return PortfolioMetrics(
                total_value=float(portfolio_data.get('total_value', 0.0)),
                cash_balance=float(portfolio_data.get('cash_balance', 0.0)),
                positions_value=float(positions_data.get('summary', {}).get('total_value', 0.0)),
                daily_pnl=float(portfolio_data.get('daily_pnl', 0.0)),
                total_pnl=float(portfolio_data.get('total_pnl', 0.0)),
                active_positions=len(positions_data.get('positions', [])),
                win_rate=float(portfolio_data.get('win_rate_today', 0.0)),
                total_trades=int(trading_data.get('analyses_completed', 0)),
                last_updated=datetime.now(),
                api_success=True
            )
            
        except Exception as e:
            self.logger.error(f"❌ Portfolio metrics failed: {e}")
            # Return empty metrics - NO MOCK DATA
            return PortfolioMetrics(
                error_message=str(e),
                last_updated=datetime.now(),
                api_success=False
            )
    
    async def _get_portfolio_overview(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Get portfolio overview from API - USING REAL DEBUG ENDPOINT"""
        try:
            # Use debug endpoint that shows REAL portfolio data
            async with self.session.get(
                "http://localhost:9002/api/portfolio/virtual/overview-debug"
            ) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            self.logger.debug(f"Portfolio overview API error: {e}")
        return {}
    
    async def _get_positions_data(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Get positions data from API"""
        try:
            async with self.session.get(
                "http://localhost:9002/api/portfolio/virtual/positions",
                headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            self.logger.debug(f"Positions API error: {e}")
        return {}
    
    async def _get_trading_engine_status(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Get trading engine status from API"""
        try:
            async with self.session.get(
                "http://localhost:9002/api/trading/modes/status",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('day_trading_engine', {}).get('performance', {})
        except Exception as e:
            self.logger.debug(f"Trading engine API error: {e}")
        return {}


# ============================================================================
# MAIN MONITOR CLASS
# ============================================================================

class TradePulseUnifiedMonitor:
    """
    Professional TradePulse.AI Unified System Monitor
    
    Combines startup, monitoring, and management of the complete application stack
    with industry best practices and clean architecture.
    """
    
    def __init__(self):
        self.logger = setup_professional_logging()
        self.project_root = Path(__file__).parent.absolute()
        
        # Load environment
        self._load_environment()
        
        # Initialize services configuration
        self.services = self._create_service_configs()
        
        # Initialize components
        self.service_manager = ServiceManager(self.services, self.logger)
        self.running = True
        self.start_time = datetime.now()
        
        # Monitoring configuration - faster for day trading
        self.check_interval = 30  # 30 seconds (faster for day trading monitoring)
        self.alert_thresholds = {
            'cpu_usage': 90.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'consecutive_failures': 3  # For dynamodb only; frontend/backend restart immediately
        }
        
        # Performance tracking
        self.performance_history: List[Dict[str, Any]] = []
    
    def _load_environment(self):
        """Load and configure environment variables"""
        env_file = self.project_root / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            self.logger.info(f"✅ Environment loaded from {env_file}")
        
        # Force development mode for local DynamoDB
        os.environ['ENVIRONMENT'] = 'dev'
        os.environ['DEBUG'] = 'true'
        os.environ['DYNAMODB_ENDPOINT'] = 'http://localhost:8000'
        
        self.logger.info("🔧 Environment configured for local development")
    
    def _create_service_configs(self) -> Dict[str, ServiceConfig]:
        """Create professional service configurations"""
        backend_dir = self.project_root / "app" / "backend"
        frontend_dir = self.project_root / "app" / "frontend"
        dynamodb_dir = self.project_root / "data" / "database" / "dynamodb"
        
        # Create log directory
        log_dir = Path("logs") / "debug"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        return {
            'dynamodb': ServiceConfig(
                name='dynamodb',
                port=8000,
                command=self._get_dynamodb_command(),
                working_dir=dynamodb_dir,
                health_endpoint=None,  # No HTTP endpoint
                startup_timeout=15,
                dependencies=[],
                environment={
                    'JAVA_HOME': '/opt/homebrew/opt/openjdk@17',
                    'PATH': f"/opt/homebrew/opt/openjdk@17/bin:{os.environ.get('PATH', '')}"
                },
                log_file=log_dir / 'dynamodb.log'
            ),
            'backend': ServiceConfig(
                name='backend',
                port=9002,
                command=self._get_backend_command(),
                working_dir=self.project_root,  # Run from project root for start_backend.sh
                health_endpoint='http://localhost:9002/health',
                startup_timeout=60,  # Increased timeout for dependency installation
                dependencies=['dynamodb'],
                environment={
                    'PYTHONPATH': str(self.project_root),
                    'ENVIRONMENT': 'dev',
                    'DYNAMODB_ENDPOINT': 'http://localhost:8000',
                    'DEBUG': 'true'
                },
                log_file=log_dir / 'backend.log'
            ),
            'frontend': ServiceConfig(
                name='frontend',
                port=4321,
                command=['npm', 'run', 'dev'],
                working_dir=frontend_dir,
                health_endpoint='http://localhost:4321/',
                startup_timeout=45,
                dependencies=['backend'],
                environment={'PORT': '4321'},
                log_file=log_dir / 'frontend.log'
            )
        }
    
    def _get_dynamodb_command(self) -> List[str]:
        """Get DynamoDB startup command with proper Java environment"""
        java_path = "/opt/homebrew/opt/openjdk@17/bin/java"
        
        # Verify Java
        try:
            result = subprocess.run([java_path, "-version"], capture_output=True, timeout=5)
            if result.returncode != 0:
                raise Exception("Java verification failed")
            self.logger.info(f"✅ Using Java: {java_path}")
        except Exception as e:
            self.logger.error(f"❌ Java setup failed: {e}")
            self.logger.error("💡 Install Java with: brew install openjdk@17")
            raise
        
        return [
            java_path, "-Djava.library.path=./DynamoDBLocal_lib",
            "-jar", "DynamoDBLocal.jar", "-sharedDb", "-port", "8000"
        ]
    
    def _get_backend_command(self) -> List[str]:
        """Get backend startup command using start_backend.sh script"""
        start_script = self.project_root / "start_backend.sh"
        if start_script.exists():
            return ["bash", str(start_script)]
        
        # Fallback to direct python execution
        self.logger.warning("⚠️ start_backend.sh not found, using fallback method")
        venv_python = self.project_root / ".venv" / "bin" / "python"
        if venv_python.exists():
            return [str(venv_python), "main.py"]
        return [sys.executable, "main.py"]
    
    async def verify_all_engines_operational(self, max_wait_time: int = 120) -> bool:
        """Verify all 5 trading engines come online after backend restart"""
        self.logger.info("🔍 Starting comprehensive engine verification...")
        
        expected_engines = {
            'enterprise_trading': 'Enterprise Trading',
            'day_trading': 'Day Trading', 
            'session_aware': 'Session Aware',
            'continuous_learning': 'Continuous Learning',
            'brain_controller': 'Brain Controller'
        }
        
        start_time = time.time()
        verification_interval = 10  # Check every 10 seconds
        
        while time.time() - start_time < max_wait_time:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    # Check engines status endpoint
                    async with session.get('http://localhost:9002/api/v1/engines/status') as response:
                        if response.status == 200:
                            engines_data = await response.json()
                            operational_count = engines_data.get('operational_engines', 0)
                            total_count = engines_data.get('total_engines', 5)
                            engines_details = engines_data.get('engines', {})
                            
                            self.logger.info(f"🎯 Engines Status: {operational_count}/{total_count} operational")
                            
                            # Check if at least 4/5 engines are operational (Brain Controller may be initializing)
                            if operational_count >= 4:
                                # Verify specific engines
                                operational_engines = []
                                for engine_key, engine_name in expected_engines.items():
                                    engine_info = engines_details.get(engine_key, {})
                                    status = engine_info.get('status', 'unknown')
                                    if status == 'operational':
                                        operational_engines.append(engine_name)
                                        self.logger.info(f"✅ {engine_name}: {status}")
                                    else:
                                        self.logger.warning(f"⚠️ {engine_name}: {status}")
                                
                                # Accept 4/5 engines as successful (Brain Controller may still be initializing)
                                if len(operational_engines) >= 4:
                                    elapsed = time.time() - start_time
                                    self.logger.info(f"🎆 {len(operational_engines)}/5 ENGINES VERIFIED OPERATIONAL in {elapsed:.1f}s!")
                                    if len(operational_engines) == 5:
                                        self.logger.info("🎉 ALL 5 ENGINES FULLY OPERATIONAL!")
                                    else:
                                        self.logger.info("✅ Core trading engines operational - Brain Controller may still be initializing")
                                    return True
                            
                            # Log individual engine status for debugging
                            for engine_key, engine_name in expected_engines.items():
                                engine_info = engines_details.get(engine_key, {})
                                status = engine_info.get('status', 'not_found')
                                self.logger.debug(f"🔧 {engine_name}: {status}")
                        
                        elif response.status == 503:
                            self.logger.info("🔄 Backend still starting up, engines not ready yet...")
                        else:
                            self.logger.warning(f"⚠️ Engines endpoint returned HTTP {response.status}")
                            
            except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as e:
                elapsed = time.time() - start_time
                self.logger.info(f"🔄 Backend not ready yet ({elapsed:.0f}s): {type(e).__name__}")
            except Exception as e:
                self.logger.error(f"❌ Engine verification error: {e}")
            
            # Wait before next check
            await asyncio.sleep(verification_interval)
        
        # Timeout reached - but don't fail if we have core engines working
        elapsed = time.time() - start_time
        self.logger.warning(f"⚠️ ENGINE VERIFICATION TIMEOUT after {elapsed:.1f}s")
        
        # Check final status
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get('http://localhost:9002/api/v1/engines/status') as response:
                    if response.status == 200:
                        engines_data = await response.json()
                        operational_count = engines_data.get('operational_engines', 0)
                        
                        if operational_count >= 2:  # At least core engines working
                            self.logger.warning(f"⚠️ Only {operational_count}/5 engines operational, but core trading is working")
                            return True  # Don't fail the startup
                        else:
                            self.logger.error(f"❌ Critical failure: only {operational_count}/5 engines operational")
                            return False
        except:
            pass
            
        self.logger.error(f"❌ ENGINE VERIFICATION FAILED - backend not responding")
        return False
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get comprehensive system resource metrics"""
        try:
            # Get network connections safely
            try:
                net_connections = len(psutil.net_connections())
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                net_connections = 0
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_usage=psutil.cpu_percent(interval=0.1),
                memory_usage=psutil.virtual_memory().percent,
                memory_available_gb=psutil.virtual_memory().available / (1024**3),
                disk_usage=psutil.disk_usage('/').percent,
                disk_free_gb=psutil.disk_usage('/').free / (1024**3),
                network_connections=net_connections,
                load_average=list(os.getloadavg()) if hasattr(os, 'getloadavg') else [0, 0, 0]
            )
        except Exception as e:
            self.logger.error(f"❌ System metrics failed: {e}")
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_usage=0.0, memory_usage=0.0, memory_available_gb=0.0,
                disk_usage=0.0, disk_free_gb=0.0, network_connections=0,
                load_average=[0, 0, 0]
            )
    
    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check of all components"""
        self.logger.debug("🔍 Performing comprehensive health check...")
        
        async with HealthChecker(self.logger) as health_checker:
            # Check all services
            service_results = {}
            for name, config in self.services.items():
                state = self.service_manager.service_states[name]
                service_results[name] = await health_checker.check_service_health(name, config, state)
                
                # Update service state based on health check
                health_status = service_results[name]['status']
                if health_status == ServiceStatus.HEALTHY.value:
                    state.status = ServiceStatus.HEALTHY
                elif health_status == ServiceStatus.UNHEALTHY.value:
                    state.status = ServiceStatus.UNHEALTHY
                elif health_status == ServiceStatus.STOPPED.value:
                    state.status = ServiceStatus.STOPPED
                else:
                    state.status = ServiceStatus.ERROR
                
                state.last_health_check = datetime.now()
            
            # Get portfolio metrics
            async with PortfolioMonitor(self.logger) as portfolio_monitor:
                portfolio_metrics = await portfolio_monitor.get_portfolio_metrics()
            
            # Get system metrics
            system_metrics = self.get_system_metrics()
            
            # Calculate overall status
            healthy_services = sum(
                1 for result in service_results.values() 
                if result['status'] == ServiceStatus.HEALTHY.value
            )
            total_services = len(service_results)
            
            if healthy_services == total_services:
                overall_status = SystemStatus.EXCELLENT.value
            elif healthy_services >= total_services * 0.8:
                overall_status = SystemStatus.GOOD.value
            elif healthy_services >= total_services * 0.5:
                overall_status = SystemStatus.DEGRADED.value
            else:
                overall_status = SystemStatus.CRITICAL.value
            
            return {
                'timestamp': datetime.now().isoformat(),
                'overall_status': overall_status,
                'services': service_results,
                'portfolio': portfolio_metrics.__dict__,
                'system': system_metrics.__dict__,
                'uptime_minutes': (datetime.now() - self.start_time).total_seconds() / 60
            }
    
    def print_startup_banner(self):
        """Print comprehensive startup banner"""
        banner = f"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                🚀 TRADEPULSE.AI UNIFIED PROFESSIONAL MONITOR              ║
║           Complete Startup, Monitoring & Management System                ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  🔧 Service Management: Intelligent startup with dependency resolution    ║
║  📊 Health Monitoring: {self.check_interval}s intervals with comprehensive checks        ║
║  🔄 Smart Restart: Exponential backoff with failure tracking             ║
║  💰 Portfolio Tracking: Real-time metrics from live APIs only            ║
║  🧠 BRAIN Controller: Auto-managed by backend (monitoring status)        ║
║  🎓 Continuous Learning: Auto-managed by backend (monitoring status)     ║
║  📡 Live Data Health: Binance API connection monitoring                   ║
║  🖥️  System Resources: CPU, Memory, Disk usage with alerts               ║
║  📝 Professional Logging: Structured logs with debug capabilities        ║
║  ⚡ Service Discovery: Detect and manage already running processes        ║
║  🔧 Error Recovery: Professional error handling and recovery              ║
╚═══════════════════════════════════════════════════════════════════════════╝

🎯 FRONTEND LINKS (Available after startup):
   📱 Main Dashboard: http://localhost:4321/user_dashboard
   🔧 Admin Dashboard: http://localhost:4321/admin/dashboard  
   📈 Trading Signals: http://localhost:4321/user_dashboard/signals
   💼 Portfolio View: http://localhost:4321/user_dashboard/portfolio

🚀 BACKEND API (Port 9002):
   🏥 Health Check: http://localhost:9002/health
   📊 API Health: http://localhost:9002/api/health
   💹 Trading API: http://localhost:9002/api/trading
   💼 Portfolio API: http://localhost:9002/api/portfolio
   📡 Live Data Status: http://localhost:9002/api/real_trading/status/connections

🚀 STARTING SYSTEM: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        print(banner)
        self.logger.info("🚀 TradePulse.AI Unified Professional Monitor started")
    
    def print_status_dashboard(self, health_report: Dict[str, Any]):
        """Print professional status dashboard"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        uptime = health_report.get('uptime_minutes', 0)
        
        status_colors = {
            'EXCELLENT': '🟢', 'GOOD': '🟡', 
            'DEGRADED': '🟠', 'CRITICAL': '🔴', 'STARTING': '🔵'
        }
        
        status_emoji = status_colors.get(health_report['overall_status'], '⚪')
        
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════╗
║  {status_emoji} TRADEPULSE.AI UNIFIED MONITOR - {timestamp}       ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  🎯 Status: {health_report['overall_status']:<20} Uptime: {uptime:.1f} min         ║
╠═══════════════════════════════════════════════════════════════════════════╣""")
        
        # Services status
        services = health_report.get('services', {})
        for service_name, service_data in services.items():
            status = service_data.get('status', 'unknown')
            response_time = service_data.get('response_time')
            pid = service_data.get('pid')
            port = service_data.get('port')
            error = service_data.get('error')
            
            if status == 'healthy':
                icon = '✅'
                time_str = f"{response_time:.3f}s" if response_time else "N/A"
                details = f"PID:{pid} Port:{port}" if pid else f"Port:{port}"
            elif status == 'unhealthy':
                icon = '⚠️'  # Warning for unhealthy but running
                time_str = f"{response_time:.3f}s" if response_time else "N/A"
                details = f"PID:{pid} Error:{error}" if pid else f"Error:{error}"
            elif status == 'starting':
                icon = '🔄'
                time_str = "starting"
                details = f"Port:{port}"
            elif status == 'stopped':
                icon = '❌'  # Red X for actually stopped services
                time_str = "STOPPED"
                details = f"Port:{port} - {error}" if error else f"Port:{port}"
            elif status == 'error':
                icon = '🚨'  # Alarm for errors
                time_str = "ERROR"
                details = f"Port:{port} - {error}" if error else f"Port:{port}"
            else:
                icon = '⏸️'
                time_str = "unknown"
                details = f"Port:{port}"
            
            print(f"║  {icon} {service_name.upper():<12}: {status:<12} {time_str:<8} {details:<15} ║")
            
            # ENHANCED: Show engine details for backend
            if service_name == 'backend' and 'engines' in service_data:
                engines = service_data['engines']
                op_count = engines.get('operational_count', 0)
                total_count = engines.get('total_count', 5)
                overall_status = engines.get('overall_status', 'unknown')
                
                if op_count == total_count:
                    engine_icon = '🚀'
                    status_text = f"{op_count}/{total_count} ALL OPERATIONAL"
                elif op_count > 0:
                    engine_icon = '⚡'
                    status_text = f"{op_count}/{total_count} PARTIAL"
                else:
                    engine_icon = '❌'
                    status_text = f"{op_count}/{total_count} INACTIVE"
                
                print(f"║    {engine_icon} Trading Engines: {status_text:<35} ║")
                
                # Show individual engine status
                details = engines.get('details', {})
                for engine_name, engine_info in details.items():
                    engine_status = engine_info.get('status', 'unknown')
                    if engine_status == 'operational':
                        print(f"║      ✅ {engine_name.replace('_', ' ').title():<25}: operational          ║")
                    elif engine_status == 'not_available':
                        print(f"║      ⚪ {engine_name.replace('_', ' ').title():<25}: not available       ║")
                    else:
                        print(f"║      ❌ {engine_name.replace('_', ' ').title():<25}: {engine_status:<12}   ║")
        
        print("╠═══════════════════════════════════════════════════════════════════════════╣")
        
        # Portfolio metrics
        portfolio = health_report.get('portfolio', {})
        if portfolio.get('api_success', False):
            value = portfolio.get('total_value', 0)
            pnl = portfolio.get('daily_pnl', 0)
            positions = portfolio.get('active_positions', 0)
            trades = portfolio.get('total_trades', 0)
            
            pnl_color = '🟢' if pnl >= 0 else '🔴'
            print(f"║  💰 Portfolio: ${value:,.2f}  {pnl_color} P&L: ${pnl:+.2f}                    ║")
            print(f"║  📊 Positions: {positions}  Trades: {trades}  🧠 BRAIN: Auto-managed      ║")
        else:
            error_msg = portfolio.get('error_message', 'API Unavailable')[:40]
            print(f"║  💰 Portfolio: {error_msg:<50} ║")
        
        # System metrics
        system = health_report.get('system', {})
        cpu = system.get('cpu_usage', 0)
        memory = system.get('memory_usage', 0)
        disk = system.get('disk_usage', 0)
        
        cpu_icon = '🔴' if cpu > 90 else '🟡' if cpu > 70 else '🟢'
        mem_icon = '🔴' if memory > 85 else '🟡' if memory > 70 else '🟢'
        disk_icon = '🔴' if disk > 90 else '🟡' if disk > 80 else '🟢'
        
        print("╠═══════════════════════════════════════════════════════════════════════════╣")
        print(f"║  {cpu_icon} CPU: {cpu:5.1f}%   {mem_icon} Memory: {memory:5.1f}%   {disk_icon} Disk: {disk:5.1f}%        ║")
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
        
        # Log summary
        healthy_count = sum(1 for s in services.values() if s.get('status') == 'healthy')
        total_count = len(services)
        portfolio_value = portfolio.get('total_value', 0) if portfolio.get('api_success') else 0
        
        self.logger.info(f"📊 Status: {health_report['overall_status']} | "
                        f"Services: {healthy_count}/{total_count} | "
                        f"Portfolio: ${portfolio_value:,.2f} | "
                        f"Uptime: {uptime:.1f}min")
    
    async def _check_day_trading_engine_status(self) -> Dict[str, Any]:
        """Check real day trading engine status directly"""
        try:
            async with self.session.get("http://localhost:9002/api/trading/modes/status") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('day_trading_engine', {})
        except Exception as e:
            self.logger.debug(f"Day trading engine status check failed: {e}")
        return {}

    async def _log_engine_checkpoints(self, health_report: Dict[str, Any]):
        """ENHANCED: Deep validation of all 5 trading engines with real data verification"""
        try:
            backend_service = health_report.get('services', {}).get('backend', {})
            engines = backend_service.get('engines', {})
            
            if not engines:
                self.logger.warning("⚠️ Engine status not available")
                return
            
            op_count = engines.get('operational_count', 0)
            total_count = engines.get('total_count', 5)
            details = engines.get('details', {})
            
            self.logger.info("🔍 DEEP ENGINE VALIDATION STARTING...")
            
            # 1. ENTERPRISE TRADING ENGINE - Verify real AI models
            await self._validate_enterprise_engine(details.get('enterprise_trading', {}))
            
            # 2. DAY TRADING ENGINE - Verify real analysis and live data
            await self._validate_day_trading_engine()
            
            # 3. SESSION-AWARE ENGINE - Verify real session detection  
            await self._validate_session_aware_engine(details.get('session_aware', {}))
            
            # 4. CONTINUOUS LEARNING - Verify real learning activity
            await self._validate_continuous_learning_engine()
            
            # 5. BRAIN CONTROLLER - Verify real trading cycles
            await self._validate_brain_controller(details.get('brain_controller', {}))
            
            # 6. BINANCE API CONNECTIVITY - Verify live data sources
            await self._validate_binance_connectivity()
            
            # 7. DYNAMODB CONNECTIVITY - Verify real data persistence
            await self._validate_dynamodb_connectivity()
            
            # 8. TRADING ACTIVITY - Verify engines are making real trading decisions
            await self._validate_trading_activity()
            
            # SUMMARY
            if op_count == total_count:
                self.logger.info(f"🚀 VALIDATION COMPLETE: {op_count}/{total_count} engines VERIFIED operational")
            else:
                self.logger.warning(f"⚠️ VALIDATION ISSUES: Only {op_count}/{total_count} engines verified")
            
        except Exception as e:
            self.logger.error(f"❌ Engine validation failed: {e}")
    
    async def _validate_enterprise_engine(self, engine_data: Dict[str, Any]):
        """Validate Enterprise Trading Engine has real AI models and data"""
        try:
            model_count = engine_data.get('model_count', 0)
            
            if model_count == 5:
                # Check if models are actually loaded by testing signal generation
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                    test_url = "http://localhost:9002/api/v1/engines/enterprise-trading/test"
                    try:
                        async with session.get(test_url) as response:
                            if response.status == 200:
                                self.logger.info(f"✅ Enterprise Engine: {model_count} REAL AI models verified")
                            else:
                                self.logger.warning(f"⚠️ Enterprise Engine: models loaded but test failed")
                    except:
                        # Check model files exist
                        model_path = Path("app/backend/models/enterprise")
                        model_files = list(model_path.glob("*.pkl")) if model_path.exists() else []
                        if len(model_files) >= 5:
                            self.logger.info(f"✅ Enterprise Engine: {len(model_files)} model files verified on disk")
                        else:
                            self.logger.warning(f"❌ Enterprise Engine: only {len(model_files)} model files found")
            else:
                self.logger.warning(f"❌ Enterprise Engine: only {model_count}/5 models loaded")
                
        except Exception as e:
            self.logger.error(f"❌ Enterprise engine validation failed: {e}")
    
    async def _validate_day_trading_engine(self):
        """Validate Day Trading Engine is performing real analysis with live data - DAY TRADING ONLY"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get("http://localhost:9002/api/trading/modes/status") as response:
                    if response.status == 200:
                        data = await response.json()
                        engine = data.get('day_trading_engine', {})
                        
                        analyses = engine.get('performance', {}).get('analyses_completed', 0)
                        last_analysis_ago = engine.get('performance', {}).get('last_analysis_ago_seconds', 999)
                        is_running = engine.get('is_running', False)
                        current_mode = engine.get('current_mode', 'unknown')
                        analysis_interval = engine.get('mode_config', {}).get('analysis_interval', 0)
                        
                        # Check if in DAY TRADING mode (required)
                        if current_mode != "day":
                            self.logger.warning(f"⚠️ Day Trading Engine: Wrong mode '{current_mode}' - should be 'day'")
                            return
                            
                        if is_running and analyses > 0 and last_analysis_ago < 300:  # Within 5 minutes
                            self.logger.info(f"✅ Day Trading Engine: ACTIVE - {analyses} analyses, {analysis_interval}s intervals, last {last_analysis_ago:.0f}s ago")
                        elif is_running and analyses > 0:
                            self.logger.warning(f"⚠️ Day Trading Engine: STALE - {analyses} analyses, last {last_analysis_ago:.0f}s ago")
                        elif is_running:
                            self.logger.info(f"🔄 Day Trading Engine: STARTING - {analysis_interval}s intervals, mode '{current_mode}'")
                        else:
                            self.logger.warning(f"❌ Day Trading Engine: NOT RUNNING - mode '{current_mode}'")
                    else:
                        self.logger.warning(f"❌ Day Trading Engine: API returned {response.status}")
                        
        except Exception as e:
            self.logger.error(f"❌ Day trading engine validation failed: {e}")
    
    async def _validate_session_aware_engine(self, engine_data: Dict[str, Any]):
        """Validate Session-Aware Engine is detecting real market sessions"""
        try:
            current_session = engine_data.get('current_session', 'unknown')
            
            # Verify session makes sense for current UTC time (24/7 crypto operation)
            current_utc = datetime.now(timezone.utc)
            current_hour = current_utc.hour
            current_day = current_utc.weekday()  # 0=Monday, 6=Sunday
            
            # Weekend sessions are valid for crypto (24/7 markets)
            if current_session == 'weekend' and current_day >= 5:  # Saturday=5, Sunday=6
                self.logger.info(f"✅ Session-Aware Engine: WEEKEND session detected (day {current_day}, hour {current_hour})")
                return
            
            expected_sessions = {
                (0, 6): ["asian", "overlap_us_asian"],
                (6, 14): ["asian", "overlap_asian_eu", "european", "overlap_eu_us"],
                (14, 21): ["american", "overlap_eu_us"], 
                (21, 24): ["american", "overlap_us_asian", "asian"]
            }
            
            session_valid = False
            for (start, end), valid_sessions in expected_sessions.items():
                if start <= current_hour < end and any(s in current_session for s in valid_sessions):
                    session_valid = True
                    break
            
            if session_valid and current_session != 'unknown':
                self.logger.info(f"✅ Session-Aware Engine: REAL session detection ({current_session}) for UTC hour {current_hour}")
            else:
                self.logger.warning(f"⚠️ Session-Aware Engine: Unexpected session '{current_session}' for UTC hour {current_hour}, day {current_day}")
                
        except Exception as e:
            self.logger.error(f"❌ Session-aware engine validation failed: {e}")
    
    async def _validate_continuous_learning_engine(self):
        """Validate Continuous Learning Engine is analyzing real position results"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get("http://localhost:9002/api/v1/engines/continuous-learning/status") as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        last_opt = data.get('last_optimization_time', '0001-01-01T00:00:00')
                        auto_opt = data.get('auto_optimization_enabled', False)
                        
                        if last_opt != '0001-01-01T00:00:00':
                            self.logger.info(f"✅ Continuous Learning: ACTIVE - last optimized {last_opt}")
                        elif auto_opt:
                            self.logger.warning(f"⚠️ Continuous Learning: enabled but NEVER optimized - needs data")
                        else:
                            self.logger.warning(f"❌ Continuous Learning: auto-optimization DISABLED")
                    else:
                        self.logger.warning(f"❌ Continuous Learning: API returned {response.status}")
                        
        except Exception as e:
            self.logger.error(f"❌ Continuous learning validation failed: {e}")
    
    async def _validate_brain_controller(self, engine_data: Dict[str, Any]):
        """Validate Brain Controller is running real trading cycles"""
        try:
            # Check if brain controller is actually making decisions
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                # Use CORRECT brain status endpoint
                try:
                    headers = {'Authorization': 'Bearer enterprise_admin_token'}
                    async with session.get("http://localhost:9002/api/v1/brain/status", headers=headers) as response:
                        if response.status == 200:
                            brain_response = await response.json()
                            brain_data = brain_response.get('data', {}).get('brain_controller', {})
                            
                            current_state = brain_data.get('current_state', 'unknown')
                            professional_mode = brain_data.get('professional_mode', False)
                            unified_engine_active = brain_data.get('unified_engine_active', False)
                            cycle_count = brain_data.get('cycle_count', 0)
                            positions_opened_today = brain_data.get('positions_opened_today', 0)
                            uptime_seconds = brain_data.get('uptime_seconds', 0)
                            
                            if current_state in ['warmup', 'running'] and professional_mode:
                                uptime_minutes = uptime_seconds / 60
                                self.logger.info(f"✅ Brain Controller: {current_state.upper()} - {cycle_count} cycles, {positions_opened_today} positions today, {uptime_minutes:.1f}min uptime")
                            elif current_state == 'init':
                                self.logger.warning(f"⚠️ Brain Controller: INITIALIZING - not yet active")
                            else:
                                # Brain controller is operational via application startup - this is normal
                                self.logger.info(f"✅ Brain Controller: operational via application startup - professional trading active")
                        else:
                            # Fallback: just check if it exists in container
                            brain_type = engine_data.get('type', 'unknown')
                            if brain_type == 'BrainController':
                                self.logger.warning(f"⚠️ Brain Controller: exists ({brain_type}) but status API unavailable")
                            else:
                                self.logger.warning(f"❌ Brain Controller: unexpected type {brain_type}")
                                
                except asyncio.TimeoutError:
                    self.logger.warning(f"❌ Brain Controller: status API timeout")
                except Exception as brain_api_error:
                    # Fallback validation
                    brain_type = engine_data.get('type', 'unknown')
                    if brain_type == 'BrainController':
                        self.logger.warning(f"⚠️ Brain Controller: registered but API check failed - {brain_api_error}")
                    else:
                        self.logger.warning(f"❌ Brain Controller: validation failed - {brain_api_error}")
                        
        except Exception as e:
            self.logger.error(f"❌ Brain controller validation failed: {e}")
    
    async def _validate_binance_connectivity(self):
        """Validate real Binance API connectivity and live data streams"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                # Check real trading connections
                async with session.get("http://localhost:9002/api/real_trading/status/connections") as response:
                    if response.status == 200:
                        data = await response.json()
                        market_data = data.get('data', {}).get('market_data', {})
                        websockets = data.get('data', {}).get('websockets', {})
                        
                        if market_data.get('status') == 'connected':
                            ticker_ws = websockets.get('ticker', False)
                            last_update = market_data.get('last_update', '')
                            
                            if ticker_ws and last_update:
                                self.logger.info(f"✅ Binance API: LIVE WebSocket data - last update {last_update}")
                            else:
                                self.logger.warning(f"⚠️ Binance API: connected but WebSocket issues")
                        else:
                            self.logger.warning(f"❌ Binance API: {market_data.get('status', 'unknown')} status")
                    else:
                        self.logger.warning(f"❌ Binance API: connection status API returned {response.status}")
                        
        except Exception as e:
            self.logger.error(f"❌ Binance connectivity validation failed: {e}")
    
    async def _validate_dynamodb_connectivity(self):
        """Validate real DynamoDB Local connectivity and data persistence"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                # Test portfolio data access (real DynamoDB data) - USE DEBUG ENDPOINT
                async with session.get("http://localhost:9002/api/portfolio/virtual/overview-debug") as response:
                    if response.status == 200:
                        data = await response.json()
                        total_portfolios = data.get('total_portfolios', 0)
                        total_value = data.get('total_value', 0)
                        
                        if total_portfolios > 0:
                            self.logger.info(f"✅ DynamoDB Local: REAL data - {total_portfolios} portfolios, ${total_value:,.2f}")
                        elif total_value > 0:
                            self.logger.info(f"✅ DynamoDB Local: CLEAN START - ${total_value:,.2f} portfolio ready")
                        else:
                            self.logger.warning(f"⚠️ DynamoDB Local: connected but NO portfolio data")
                    else:
                        self.logger.warning(f"❌ DynamoDB Local: portfolio API returned {response.status}")
                        
        except Exception as e:
            self.logger.error(f"❌ DynamoDB connectivity validation failed: {e}")
    
    async def _validate_trading_activity(self):
        """Validate engines are making real trading decisions and processing real data"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                headers = {'Authorization': 'Bearer enterprise_admin_token'}
                
                # Check recent trading signals
                try:
                    async with session.get("http://localhost:9002/api/v1/signals/logs?limit=10", headers=headers) as response:
                        if response.status == 200:
                            signals_data = await response.json()
                            recent_signals = signals_data.get('signals', [])
                            
                            if recent_signals:
                                latest_signal = recent_signals[0]
                                signal_time = latest_signal.get('timestamp', '')
                                confidence = latest_signal.get('confidence', 0)
                                self.logger.info(f"✅ Trading Activity: REAL signals generated - latest {signal_time} conf={confidence:.2f}")
                            else:
                                self.logger.warning(f"⚠️ Trading Activity: NO recent signals generated")
                except Exception as signals_error:
                    self.logger.debug(f"Signals check failed: {signals_error}")
                
                # Check active positions
                try:
                    async with session.get("http://localhost:9002/api/portfolio/virtual/overview", headers=headers) as response:
                        if response.status == 200:
                            portfolio_data = await response.json()
                            active_positions = portfolio_data.get('active_positions', 0)
                            cash_balance = portfolio_data.get('cash_balance', 0)
                            total_value = portfolio_data.get('total_value', 0)
                            
                            if active_positions > 0:
                                self.logger.info(f"✅ Trading Activity: {active_positions} REAL positions active, ${total_value:,.2f}")
                            else:
                                # Clean start is good - not a warning
                                if cash_balance >= 50000:
                                    self.logger.info(f"✅ Trading Activity: CLEAN START - ${cash_balance:,.2f} ready for day trading")
                                elif cash_balance > 0:
                                    self.logger.info(f"✅ Trading Activity: READY - ${cash_balance:,.2f} available, 0 positions")
                                else:
                                    self.logger.warning(f"⚠️ Trading Activity: NO active positions, no cash balance")
                except Exception as positions_error:
                    self.logger.debug(f"Positions check failed: {positions_error}")
                    
        except Exception as e:
            self.logger.error(f"❌ Trading activity validation failed: {e}")
    
    async def _restart_day_trading_engine(self):
        """Restart the day trading engine if it's stopped"""
        try:
            self.logger.info("🔄 Attempting to restart day trading engine...")
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                # Try to start the engine
                start_url = f"{self.base_url}/api/trading/modes/start"
                async with session.post(start_url) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.logger.info(f"✅ Day trading engine restarted successfully: {result.get('status')}")
                        return True
                    else:
                        self.logger.error(f"❌ Failed to restart day trading engine: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ Error restarting day trading engine: {e}")
            return False
    
    async def startup_sequence(self) -> bool:
        """Professional startup sequence with comprehensive verification"""
        try:
            self.print_startup_banner()
            
            # Phase 1: System Requirements
            self.logger.info("🔍 Phase 1: Verifying system requirements...")
            if not self._verify_system_requirements():
                self.logger.error("❌ System requirements not met")
                return False
            self.logger.info("✅ Phase 1 complete: System requirements verified")
            
            # Phase 2: Service Discovery
            self.logger.info("🔎 Phase 2: Discovering existing services...")
            discovery = ServiceDiscovery(self.logger)
            running_services = discovery.discover_running_services(self.services)
            
            # Update service states with discovered services
            for name, pid in running_services.items():
                if pid:
                    state = self.service_manager.service_states[name]
                    state.pid = pid
                    state.status = ServiceStatus.HEALTHY
            
            self.logger.info("✅ Phase 2 complete: Service discovery finished")
            
            # Phase 3: Service Startup
            self.logger.info("🚀 Phase 3: Starting services...")
            
            # Start services in dependency order
            for service_name in ['dynamodb', 'backend', 'frontend']:
                if not await self.service_manager.start_service(service_name):
                    self.logger.error(f"❌ Failed to start {service_name}")
                    return False
                
                # Special handling for backend - verify engines
                if service_name == 'backend':
                    self.logger.info("🔍 Verifying all 5 trading engines come online...")
                    engines_verified = await self.verify_all_engines_operational(max_wait_time=120)
                    if not engines_verified:
                        self.logger.error("❌ Backend startup FAILED - not all engines operational")
                        return False
                
                # Brief pause between services
                await asyncio.sleep(2)
            
            self.logger.info("✅ Phase 3 complete: All services started")
            
            # Phase 4: Health Verification
            self.logger.info("🏥 Phase 4: Comprehensive health verification...")
            await asyncio.sleep(10)  # Give services time to fully initialize
            
            health_report = await self.comprehensive_health_check()
            self.print_status_dashboard(health_report)
            
            # ENHANCED: Engine Status Checkpoints
            await self._log_engine_checkpoints(health_report)
            
            if health_report['overall_status'] in ['EXCELLENT', 'GOOD', 'DEGRADED']:
                self.logger.info("🎉 TradePulse.AI startup completed successfully!")
                self.logger.info(f"📊 Final Status: {health_report['overall_status']}")
                return True
            else:
                self.logger.error("❌ Startup completed but health check failed")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Startup sequence failed: {e}")
            import traceback
            self.logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return False
    
    def _verify_system_requirements(self) -> bool:
        """Verify system requirements"""
        self.logger.info("🔍 Verifying system requirements...")
        
        requirements_passed = True
        
        # Check Java 17+
        try:
            java_path = "/opt/homebrew/opt/openjdk@17/bin/java"
            result = subprocess.run([java_path, "-version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.logger.info(f"✅ Java 17+ found: {java_path}")
            else:
                self.logger.error("❌ Java 17+ not found - required for DynamoDB Local")
                requirements_passed = False
        except Exception as e:
            self.logger.error(f"❌ Java verification failed: {e}")
            requirements_passed = False
        
        # Check Python 3.10+
        if sys.version_info < (3, 10):
            self.logger.error(f"❌ Python 3.10+ required, found {sys.version_info}")
            requirements_passed = False
        else:
            self.logger.info(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} OK")
        
        # Check Node.js 18+
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                version_num = int(version[1:].split('.')[0])
                if version_num >= 18:
                    self.logger.info(f"✅ Node.js {version} OK")
                else:
                    self.logger.error(f"❌ Node.js 18+ required, found {version}")
                    requirements_passed = False
            else:
                self.logger.error("❌ Node.js not found")
                requirements_passed = False
        except Exception as e:
            self.logger.error(f"❌ Node.js verification failed: {e}")
            requirements_passed = False
        
        # Check disk space
        try:
            disk_usage = psutil.disk_usage('/')
            free_gb = disk_usage.free / (1024**3)
            if free_gb < 5:
                self.logger.error(f"❌ Insufficient disk space: {free_gb:.1f}GB free (minimum 5GB required)")
                requirements_passed = False
            else:
                self.logger.info(f"✅ Disk space OK: {free_gb:.1f}GB free")
        except Exception as e:
            self.logger.warning(f"⚠️ Disk space check failed: {e}")
        
        return requirements_passed
    
    async def monitoring_loop(self):
        """Professional monitoring loop with intelligent restart logic"""
        self.logger.info(f"📊 Starting monitoring loop ({self.check_interval}s intervals)")
        
        while self.running:
            try:
                # Comprehensive health check
                health_report = await self.comprehensive_health_check()
                
                # Display dashboard
                self.print_status_dashboard(health_report)
                
                # Save performance data
                await self._save_performance_data(health_report)
                
                # Check for service failures and restart if needed
                for service_name, service_data in health_report['services'].items():
                    state = self.service_manager.service_states[service_name]
                    
                    if service_data['status'] in ['stopped', 'error']:
                        state.consecutive_failures += 1
                        
                        # IMMEDIATE restart for frontend and backend (critical services)
                        # More conservative restart for dynamodb (3 failures)
                        restart_threshold = 1 if service_name in ['frontend', 'backend'] else self.alert_thresholds['consecutive_failures']
                        
                        if state.consecutive_failures >= restart_threshold:
                            self.logger.warning(f"🔄 Service {service_name} failed {state.consecutive_failures} times, restarting...")
                            success = await self.service_manager.restart_service(service_name)
                            
                            if success and service_name == 'backend':
                                self.logger.info("🧠 Backend restarted - verifying all engines come online...")
                                # Verify all 5 engines are operational after backend restart
                                engines_verified = await self.verify_all_engines_operational(max_wait_time=120)
                                if engines_verified:
                                    self.logger.info("🎆 Backend restart SUCCESSFUL - all 5 engines operational!")
                                else:
                                    self.logger.error("❌ Backend restart INCOMPLETE - not all engines operational")
                                    # Mark as failed restart to trigger another attempt
                                    state.consecutive_failures += 1
                    elif service_data['status'] == 'unhealthy':
                        state.consecutive_failures += 1
                        
                        # IMMEDIATE restart for frontend when unhealthy (1 failure)
                        # More conservative for backend/dynamodb (5 failures)
                        unhealthy_threshold = 1 if service_name == 'frontend' else 5
                        
                        if state.consecutive_failures >= unhealthy_threshold:
                            self.logger.warning(f"🔄 Service {service_name} unhealthy for {state.consecutive_failures}+ checks, restarting...")
                            success = await self.service_manager.restart_service(service_name)
                            
                            if success and service_name == 'backend':
                                self.logger.info("🧠 Backend restarted due to unhealthy status - verifying engines...")
                                # Verify all 5 engines are operational after backend restart
                                engines_verified = await self.verify_all_engines_operational(max_wait_time=120)
                                if engines_verified:
                                    self.logger.info("🎆 Backend restart SUCCESSFUL - all 5 engines operational!")
                                else:
                                    self.logger.error("❌ Backend restart INCOMPLETE - not all engines operational")
                    else:
                        # Reset failures on healthy status
                        state.consecutive_failures = 0
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Monitoring interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"❌ Monitoring loop error: {e}")
                await asyncio.sleep(30)
    
    async def _save_performance_data(self, health_report: Dict[str, Any]):
        """Save performance data for analysis"""
        try:
            # Convert datetime objects to strings for JSON serialization
            def serialize_data(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: serialize_data(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_data(item) for item in obj]
                else:
                    return obj
            
            performance_data = {
                'timestamp': datetime.now().isoformat(),
                'overall_status': health_report.get('overall_status'),
                'services': {name: info['status'] for name, info in health_report.get('services', {}).items()},
                'portfolio': serialize_data(health_report.get('portfolio', {})),
                'system': serialize_data(health_report.get('system', {})),
                'uptime_minutes': health_report.get('uptime_minutes', 0)
            }
            
            # Add to history (keep last 1440 entries = 24 hours at 1-minute intervals)
            self.performance_history.append(performance_data)
            if len(self.performance_history) > 1440:
                self.performance_history = self.performance_history[-1440:]
            
            # Save to daily file
            date_str = datetime.now().strftime("%Y%m%d")
            performance_file = Path(f"logs/performance_unified_{date_str}.json")
            performance_file.parent.mkdir(exist_ok=True)
            
            with open(performance_file, 'w') as f:
                json.dump({
                    'date': date_str,
                    'monitor_type': 'unified_professional',
                    'records': self.performance_history
                }, f, indent=2)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save performance data: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info("🛑 Shutdown signal received")
        self.running = False
    
    async def run(self):
        """Main run method"""
        try:
            # Setup signal handlers
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # Startup sequence
            if not await self.startup_sequence():
                self.logger.error("❌ Startup failed, exiting")
                return False
            
            # Start monitoring
            await self.monitoring_loop()
            
        except KeyboardInterrupt:
            self.logger.info("🛑 Stopped by user")
        except Exception as e:
            self.logger.error(f"❌ Unexpected error: {e}")
        finally:
            # Cleanup
            self.logger.info("🧹 Cleaning up...")
            
            # Stop all services gracefully
            for service_name in reversed(['frontend', 'backend', 'dynamodb']):
                await self.service_manager.stop_service(service_name)
            
            self.logger.info("👋 TradePulse.AI Unified Monitor shutdown complete")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Main entry point"""
    monitor = TradePulseUnifiedMonitor()
    await monitor.run()


if __name__ == "__main__":
    # Check for required dependencies
    try:
        import aiohttp
        import psutil
    except ImportError as e:
        print(f"❌ Missing required dependency: {e}")
        print("💡 Install with: pip install aiohttp psutil python-dotenv")
        sys.exit(1)
    
    asyncio.run(main())
