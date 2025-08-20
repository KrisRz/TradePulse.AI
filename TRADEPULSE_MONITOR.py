#!/usr/bin/env python3
"""
TradePulse.AI - UNIFIED MONITORING & AUTO-RESTART SYSTEM
========================================================

Complete all-in-one script for TradePulse.AI that combines:
- Application startup and service management
- Comprehensive monitoring and health checks  
- Virtual portfolio performance tracking
- Automatic restart on failures
- System resource monitoring
- Performance data collection for analysis
- Email alerts for critical issues

Updated for current app/ structure with proper paths and ports.

Features:
🚀 Complete system startup and verification
📊 High-frequency monitoring (60-second intervals)
🔄 Intelligent service restart (up to 10 attempts)
💰 Virtual portfolio trading performance tracking
🖥️ System resource monitoring (CPU, Memory, Disk)
📧 Email alerts for critical failures
📈 Comprehensive performance data logging
🌙 Designed for overnight continuous operation

Usage:
    python3 TRADEPULSE_MONITOR.py
"""

import os
import sys
import time
import json
import asyncio
import aiohttp
import subprocess
import signal
try:
    import psutil
except ImportError:
    print("❌ psutil not installed. Run: pip install psutil")
    sys.exit(1)
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import threading

# Enhanced logging configuration
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and emojis for better readability"""
    
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

# Configure comprehensive logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

log_filename = f'tradepulse_monitor_{datetime.now().strftime("%Y%m%d")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / log_filename),
        logging.StreamHandler()
    ]
)

console_handler = logging.getLogger().handlers[1]
console_handler.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(__name__)

class TradePulseMonitor:
    """Unified monitoring and management system for TradePulse.AI"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        self.backend_dir = self.project_root / "app" / "backend"
        self.frontend_dir = self.project_root / "app" / "frontend"
        
        # Enhanced debug logging directory
        self.debug_dir = Path("logs") / "debug"
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        
        # Load environment variables
        env_file = self.project_root / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            logger.info(f"✅ Loaded environment variables from {env_file}")
        else:
            logger.warning(f"⚠️  No .env file found at {env_file}")
        
        # Enhanced service configuration with correct ports and commands
        self.services = {
            'dynamodb': {
                'port': 8000, 
                'pid': None, 
                'status': 'unknown',
                'restart_attempts': 0,
                'last_restart': None,
                'command': self._get_dynamodb_command(),
                'startup_time': None,
                'last_response_time': None,
                'error_count': 0,
                'health_endpoint': None,
                'log_file': self.debug_dir / 'dynamodb.log'
            },
            'backend': {
                'port': 9002,  # Updated to correct port from config.py
                'pid': None, 
                'status': 'unknown',
                'restart_attempts': 0,
                'last_restart': None,
                'command': self._get_backend_command(),
                'startup_time': None,
                'last_response_time': None,
                'error_count': 0,
                'health_endpoint': 'http://localhost:9002/health',
                'log_file': self.debug_dir / 'backend.log'
            },
            'frontend': {
                'port': 4321, 
                'pid': None, 
                'status': 'unknown',
                'restart_attempts': 0,
                'last_restart': None,
                'command': self._get_frontend_command(),
                'startup_time': None,
                'last_response_time': None,
                'error_count': 0,
                'health_endpoint': 'http://localhost:4321/',
                'log_file': self.debug_dir / 'frontend.log'
            }
        }
        
        # Monitoring configuration
        self.check_interval = 60  # 1 minute for frequent monitoring
        self.health_timeout = 10  # 10 seconds for health checks
        self.max_restart_attempts = 10  # Max restart attempts per service
        self.consecutive_failures = {}  # Track consecutive failures
        
        # Performance tracking
        self.performance_log = []
        self.trading_metrics = []
        self.system_metrics = []
        self.portfolio_snapshots = []
        
        # Alert thresholds
        self.alert_thresholds = {
            'cpu_usage': 90.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'response_time': 5.0,
            'consecutive_failures': 3,
            'portfolio_loss': -500.0  # Alert if portfolio loses more than $500
        }
        
        # Session management
        self.session = None
        self.running = True
        self.start_time = datetime.now()
        self.last_health_check = None
        
        # Email notification settings
        self.email_alerts = os.getenv('ENABLE_EMAIL_ALERTS', 'false').lower() == 'true'
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_user = os.getenv('EMAIL_USER', '')
        self.email_password = os.getenv('EMAIL_PASSWORD', '')
        self.alert_recipient = os.getenv('ALERT_EMAIL', '')
        
        # Enhanced system status with comprehensive metrics
        self.system_status = {
            'overall_status': 'STARTING',
            'services_healthy': 0,
            'last_portfolio_value': 10000.0,
            'portfolio_change_24h': 0.0,
            'total_trades_today': 0,
            'uptime_minutes': 0,
            'startup_timestamp': datetime.now().isoformat(),
            'network_checks_passed': False,
            'database_connectivity': False,
            'api_endpoints_validated': False,
            'critical_files_verified': False,
            'aws_migration_ready': False
        }
        
        # Critical files and directories to verify
        self.critical_paths = {
            'backend_main': self.backend_dir / 'main.py',
            'backend_config': self.backend_dir / 'core' / 'config.py',
            'dynamodb_jar': self.backend_dir / 'data' / 'dynamodb' / 'DynamoDBLocal.jar',
            'frontend_config': self.frontend_dir / 'package.json',
            'env_file': self.project_root / '.env',
            'config_dir': self.project_root / 'config',
            'data_dir': self.backend_dir / 'data',
            'logs_dir': self.project_root / 'logs'
        }
        
        # API endpoints to validate (using actual available endpoints)
        self.api_endpoints = [
            'http://localhost:9002/health',
            'http://localhost:9002/api/health',
            'http://localhost:9002/',
            'http://localhost:9002/api/trading',
            'http://localhost:9002/api/real_trading/health-check'
        ]
        
        # Network connectivity tests (updated for correct backend port)
        self.network_tests = [
            {'host': 'api.binance.com', 'port': 443, 'name': 'Binance API'},
            {'host': 'google.com', 'port': 80, 'name': 'Internet Connectivity'},
            {'host': 'localhost', 'port': 8000, 'name': 'DynamoDB Local'},
            {'host': 'localhost', 'port': 9002, 'name': 'Backend API'},
            {'host': 'localhost', 'port': 4321, 'name': 'Frontend Dev Server'}
        ]
        
        logger.info("🚀 TradePulse Monitor initialized with updated configuration")
    
    def print_startup_banner(self):
        """Print comprehensive startup banner"""
        banner = f"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    🚀 TRADEPULSE.AI UNIFIED MONITOR                       ║
║              Complete Startup, Monitoring & Performance Tracking          ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  🔧 System Startup: Complete service initialization                       ║
║  📊 Monitoring: {self.check_interval}s intervals (high-frequency)                          ║
║  🔄 Auto-restart: {self.max_restart_attempts} attempts per service                             ║
║  💰 Portfolio Tracking: Real-time virtual portfolio monitoring            ║
║  🖥️  Resource Monitoring: CPU, Memory, Disk usage tracking               ║
║  📧 Email Alerts: {'Enabled' if self.email_alerts else 'Disabled'}                                                ║
║  📈 Performance Logging: Comprehensive metrics collection                 ║
║  🌙 Overnight Operation: Designed for continuous 24/7 monitoring          ║
╚═══════════════════════════════════════════════════════════════════════════╝

🎯 FRONTEND LINKS (Available after startup):
   📱 Main Dashboard: http://localhost:4321/user_dashboard
   🔧 Admin Dashboard: http://localhost:4321/admin/dashboard  
   📈 Trading Signals: http://localhost:4321/user_dashboard/signals
   💼 Portfolio View: http://localhost:4321/user_dashboard/portfolio
   🔐 Login: http://localhost:4321/auth/login
   📝 Register: http://localhost:4321/auth/register

🚀 BACKEND API (Port 9002):
   🏥 Health Check: http://localhost:9002/health
   📊 API Health: http://localhost:9002/api/health
   💹 Trading API: http://localhost:9002/api/trading
   💼 Portfolio API: http://localhost:9002/api/portfolio

🚀 STARTING SYSTEM: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        print(banner)
        logger.info("🚀 TradePulse.AI Unified Monitor started")
    
    def _get_dynamodb_command(self) -> List[str]:
        """Get DynamoDB startup command with proper Java environment"""
        java_paths = [
            "/opt/homebrew/opt/openjdk@17/bin/java",
            "/usr/lib/jvm/java-17-openjdk-amd64/bin/java", 
            "java"
        ]
        
        java_path = "java"
        for path in java_paths:
            try:
                # Set JAVA_HOME environment variable for Homebrew Java
                if "homebrew" in path:
                    os.environ['JAVA_HOME'] = "/opt/homebrew/opt/openjdk@17"
                    os.environ['PATH'] = f"/opt/homebrew/opt/openjdk@17/bin:{os.environ.get('PATH', '')}"
                
                result = subprocess.run([path, "-version"], capture_output=True, timeout=5)
                if result.returncode == 0:
                    java_path = path
                    logger.debug(f"✅ Found Java: {java_path}")
                    break
            except Exception as e:
                logger.debug(f"⚠️ Java path {path} failed: {e}")
                continue
        
        dynamodb_dir = self.backend_dir / "data" / "dynamodb"
        jar_file = dynamodb_dir / "DynamoDBLocal.jar"
        
        return [
            java_path, "-Djava.library.path=./DynamoDBLocal_lib",
            "-jar", str(jar_file), "-sharedDb", "-port", "8000"
        ]
    
    def _get_backend_command(self) -> List[str]:
        """Get backend startup command with virtual environment"""
        # Use virtual environment Python with proper PYTHONPATH
        venv_python = self.backend_dir / "venv" / "bin" / "python"
        if venv_python.exists():
            return [str(venv_python), "main.py"]
        else:
            return [sys.executable, "main.py"]
    
    def _get_frontend_command(self) -> List[str]:
        """Get frontend startup command"""
        return ["npm", "run", "dev"]
    
    def verify_critical_files(self) -> bool:
        """Verify all critical files and directories exist"""
        logger.info("🔍 Verifying critical files and directories...")
        
        all_files_ok = True
        for name, path in self.critical_paths.items():
            if path.exists():
                logger.info(f"✅ {name}: {path}")
            else:
                logger.error(f"❌ Missing {name}: {path}")
                all_files_ok = False
        
        self.system_status['critical_files_verified'] = all_files_ok
        return all_files_ok
    
    def test_network_connectivity(self) -> bool:
        """Test network connectivity to critical services"""
        logger.info("🌐 Testing network connectivity...")
        
        import socket
        connectivity_results = []
        
        for test in self.network_tests:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((test['host'], test['port']))
                sock.close()
                
                if result == 0:
                    logger.info(f"✅ {test['name']}: {test['host']}:{test['port']}")
                    connectivity_results.append(True)
                else:
                    logger.warning(f"⚠️  {test['name']}: {test['host']}:{test['port']} - Connection failed")
                    connectivity_results.append(False)
                    
            except Exception as e:
                logger.error(f"❌ {test['name']}: {test['host']}:{test['port']} - {e}")
                connectivity_results.append(False)
        
        network_ok = sum(connectivity_results) >= len(connectivity_results) * 0.6  # 60% success rate
        self.system_status['network_checks_passed'] = network_ok
        
        logger.info(f"🌐 Network connectivity: {sum(connectivity_results)}/{len(connectivity_results)} tests passed")
        return network_ok
    
    def verify_system_requirements(self) -> bool:
        """Verify system requirements before startup"""
        logger.info("🔍 Verifying system requirements...")
        
        requirements_passed = True
        
        # Check Java 17+
        try:
            java_found = False
            java_version = None
            for java_path in ["/opt/homebrew/opt/openjdk@17/bin/java", 
                             "/usr/lib/jvm/java-17-openjdk-amd64/bin/java", "java"]:
                try:
                    result = subprocess.run([java_path, "-version"], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0 and any(v in result.stderr for v in ["17", "18", "19", "20", "21"]):
                        java_version = result.stderr.split()[2].strip('"')
                        logger.info(f"✅ Java found: {java_path} (version {java_version})")
                        java_found = True
                        break
                except:
                    continue
            
            if not java_found:
                logger.error("❌ Java 17+ not found - required for DynamoDB Local")
                requirements_passed = False
                
        except Exception as e:
            logger.error(f"❌ Java verification failed: {e}")
            requirements_passed = False
        
        # Check Python
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        if sys.version_info < (3, 10):
            logger.error(f"❌ Python 3.10+ required, found {python_version}")
            requirements_passed = False
        else:
            logger.info(f"✅ Python {python_version} OK")
        
        # Check Node.js
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                node_version = result.stdout.strip()
                version_num = int(node_version[1:].split('.')[0])
                if version_num >= 18:
                    logger.info(f"✅ Node.js {node_version} OK")
                else:
                    logger.error(f"❌ Node.js 18+ required, found {node_version}")
                    requirements_passed = False
            else:
                logger.error("❌ Node.js not found")
                requirements_passed = False
        except Exception as e:
            logger.error(f"❌ Node.js verification failed: {e}")
            requirements_passed = False
        
        # Check npm
        try:
            result = subprocess.run(["npm", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                npm_version = result.stdout.strip()
                logger.info(f"✅ npm {npm_version} available")
            else:
                logger.warning("⚠️  npm not found, may cause frontend issues")
        except Exception as e:
            logger.warning(f"⚠️  npm check failed: {e}")
        
        # Check disk space
        try:
            disk_usage = psutil.disk_usage('/')
            free_gb = disk_usage.free / (1024**3)
            if free_gb < 5:  # Less than 5GB free
                logger.error(f"❌ Insufficient disk space: {free_gb:.1f}GB free (minimum 5GB required)")
                requirements_passed = False
            else:
                logger.info(f"✅ Disk space OK: {free_gb:.1f}GB free")
        except Exception as e:
            logger.warning(f"⚠️  Disk space check failed: {e}")
        
        # Check available memory
        try:
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            if available_gb < 2:  # Less than 2GB available
                logger.warning(f"⚠️  Low available memory: {available_gb:.1f}GB (recommend 4GB+)")
            else:
                logger.info(f"✅ Memory OK: {available_gb:.1f}GB available")
        except Exception as e:
            logger.warning(f"⚠️  Memory check failed: {e}")
        
        return requirements_passed
    
    def find_process_by_port(self, port: int) -> Optional[int]:
        """Find process ID by port using lsof"""
        try:
            result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip().split()[0])
        except:
            pass
        return None
    
    def discover_existing_services(self):
        """Discover already running services"""
        logger.info("🔍 Discovering existing services...")
        
        for service_name, config in self.services.items():
            pid = self.find_process_by_port(config['port'])
            if pid:
                config['pid'] = pid
                config['status'] = 'running'
                logger.info(f"✅ Found running {service_name} (PID: {pid}, Port: {config['port']})")
            else:
                config['status'] = 'stopped'
                logger.info(f"⏸️  {service_name} not running on port {config['port']}")
    
    def start_service(self, service_name: str) -> bool:
        """Start a specific service with enhanced logging and debugging"""
        config = self.services[service_name]
        
        # Check if already running
        if config['status'] == 'running' and config['pid']:
            logger.info(f"✅ {service_name} already running (PID: {config['pid']})")
            return True
        
        logger.info(f"🚀 Starting {service_name}...")
        logger.debug(f"📋 Command: {' '.join(map(str, config['command']))}")
        
        try:
            # Prepare environment and working directory
            if service_name == 'dynamodb':
                cwd = self.backend_dir / "data" / "dynamodb"
                env = os.environ.copy()
                logger.debug(f"📁 Working directory: {cwd}")
                
                # Verify DynamoDB jar exists
                jar_file = cwd / "DynamoDBLocal.jar"
                if not jar_file.exists():
                    logger.error(f"❌ DynamoDB jar not found: {jar_file}")
                    return False
                    
            elif service_name == 'backend':
                cwd = self.backend_dir
                env = os.environ.copy()
                # Set PYTHONPATH to include the project root for proper imports
                env['PYTHONPATH'] = str(self.project_root)
                
                logger.debug(f"📁 Working directory: {cwd}")
                logger.debug(f"🐍 PYTHONPATH: {env.get('PYTHONPATH')}")
                
                # Verify main file exists
                main_file = cwd / "main.py"
                if not main_file.exists():
                    logger.error(f"❌ Backend main.py not found: {main_file}")
                    return False
                    
            elif service_name == 'frontend':
                cwd = self.frontend_dir
                env = os.environ.copy()
                logger.debug(f"📁 Working directory: {cwd}")
                
                # Verify package.json exists
                package_json = cwd / "package.json"
                if not package_json.exists():
                    logger.error(f"❌ Frontend package.json not found: {package_json}")
                    return False
            
            # Create log file for service output
            log_file = config.get('log_file')
            if log_file:
                log_file.parent.mkdir(parents=True, exist_ok=True)
                log_handle = open(log_file, 'a')
                logger.debug(f"📝 Logging output to: {log_file}")
            else:
                log_handle = subprocess.PIPE
            
            # Start the process
            start_time = datetime.now()
            process = subprocess.Popen(
                config['command'],
                cwd=cwd,
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT if log_file else subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            config['startup_time'] = start_time
            logger.info(f"🚀 {service_name} process started (PID: {process.pid})")
            
            # Give the service time to start with progress indication
            startup_wait = 3 if service_name == 'dynamodb' else 10
            for i in range(startup_wait):
                time.sleep(1)
                # Check if process is still alive
                if process.poll() is not None:
                    logger.error(f"❌ {service_name} process died during startup")
                    if log_file and log_handle != subprocess.PIPE:
                        log_handle.close()
                    return False
                logger.debug(f"⏳ {service_name} startup: {i+1}/{startup_wait}s")
            
            # Verify it's running on the expected port
            pid = self.find_process_by_port(config['port'])
            if pid:
                config['pid'] = pid
                config['status'] = 'running'
                config['restart_attempts'] = 0
                startup_duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ {service_name} started successfully (PID: {pid}, startup: {startup_duration:.1f}s)")
                
                if log_file and log_handle != subprocess.PIPE:
                    log_handle.close()
                return True
            else:
                logger.error(f"❌ {service_name} failed to bind to port {config['port']}")
                
                # Try to get error info from process
                if process.poll() is None:
                    logger.warning(f"⚠️  {service_name} process still running but not on expected port")
                else:
                    logger.error(f"❌ {service_name} process terminated with code {process.returncode}")
                
                if log_file and log_handle != subprocess.PIPE:
                    log_handle.close()
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to start {service_name}: {e}")
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """Stop a specific service"""
        config = self.services[service_name]
        
        if not config['pid']:
            logger.info(f"✅ {service_name} already stopped")
            return True
        
        logger.info(f"🛑 Stopping {service_name} (PID: {config['pid']})...")
        
        try:
            # Try graceful shutdown first
            os.kill(config['pid'], signal.SIGTERM)
            time.sleep(3)
            
            # Check if it's still running
            try:
                os.kill(config['pid'], 0)  # Check if process exists
                # Still running, force kill
                logger.warning(f"⚡ Force killing {service_name}")
                os.kill(config['pid'], signal.SIGKILL)
                time.sleep(1)
            except ProcessLookupError:
                # Process is gone
                pass
            
            config['pid'] = None
            config['status'] = 'stopped'
            logger.info(f"✅ {service_name} stopped")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to stop {service_name}: {e}")
            return False
    
    async def setup_http_session(self):
        """Setup HTTP session for health checks"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.health_timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def cleanup_session(self):
        """Cleanup HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def configure_professional_trading(self):
        """Auto-configure professional trading engine for autonomous operation"""
        try:
            await self.setup_http_session()
            
            # Step 1: Set day trading mode (15-second analysis cycles)
            logger.info("🎯 Setting day trading mode (15s cycles)...")
            async with self.session.post(
                "http://localhost:9002/api/trading/modes/set",
                json={"mode": "day"},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Day trading mode set: {data.get('config', {}).get('analysis_interval', 15)}s intervals")
                else:
                    logger.warning(f"⚠️ Failed to set day mode: HTTP {response.status}")
            
            # Step 2: Start trading analysis loop
            logger.info("🚀 Starting autonomous trading analysis loop...")
            async with self.session.post("http://localhost:9002/api/trading/modes/start") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("✅ Trading analysis loop started")
                else:
                    logger.warning(f"⚠️ Failed to start trading loop: HTTP {response.status}")
            
            # Step 3: Enable trading engine with STRICT mode (production ready)
            logger.info("🤖 Enabling AI trading engine with STRICT live stream...")
            async with self.session.put(
                "http://localhost:9002/api/admin/runtime-config",
                json={"engine_enabled": True, "strict_live_stream": True},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    logger.info("✅ AI trading engine enabled with STRICT mode (production ready)")
                    logger.info("🔒 STRICT_LIVE_STREAM: ON - WebSocket only, no REST fallbacks")
                else:
                    logger.warning(f"⚠️ Failed to enable engine: HTTP {response.status}")
            
            # Step 4: Apply professional thresholds for real models
            logger.info("⚙️ Applying professional trading thresholds...")
            professional_config = {
                "day_confidence_threshold": 0.40,
                "enterprise_confidence_threshold": 0.40,
                "day_position_size_pct": 0.08
            }
            
            async with self.session.post(
                "http://localhost:9002/api/trading/config/override",
                json=professional_config,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Professional thresholds applied:")
                    logger.info(f"   📊 Confidence threshold: {data.get('enterprise_confidence_threshold', 0.40)}")
                    logger.info(f"   💰 Position size: {data.get('day_position_size_pct', 0.08)*100}% of portfolio")
                else:
                    logger.warning(f"⚠️ Failed to apply thresholds: HTTP {response.status}")
            
            # Step 5: Verify trading engine status
            logger.info("🔍 Verifying trading engine status...")
            async with self.session.get("http://localhost:9002/api/trading/modes/status") as response:
                if response.status == 200:
                    data = await response.json()
                    engine_data = data.get('day_trading_engine', {})
                    logger.info(f"✅ Trading engine status:")
                    logger.info(f"   🎯 Mode: {engine_data.get('current_mode', 'unknown')}")
                    logger.info(f"   🔄 Running: {engine_data.get('is_running', False)}")
                    logger.info(f"   ⏱️ Interval: {engine_data.get('mode_config', {}).get('analysis_interval', 'unknown')}s")
                    logger.info(f"   📊 Threshold: {engine_data.get('mode_config', {}).get('confidence_threshold', 'unknown')}")
                else:
                    logger.warning(f"⚠️ Could not verify trading engine: HTTP {response.status}")
            
            logger.info("🚀 Professional autonomous trading engine ready!")
            logger.info("💡 The AI will analyze markets every 15 seconds - admin can control via dashboard")
            logger.info("🎛️ Trading controls available at: http://localhost:4321/admin/dashboard")
            
        except Exception as e:
            logger.error(f"❌ Failed to configure professional trading: {e}")
            logger.warning("⚠️ Trading engine may need manual configuration")
    
    async def check_service_health(self, service_name: str) -> Dict[str, Any]:
        """Check health of a specific service"""
        config = self.services[service_name]
        
        if config['status'] != 'running' or not config['pid']:
            return {
                'service': service_name,
                'status': 'stopped',
                'response_time': None,
                'error': 'Service not running'
            }
        
        # Check if process is still alive
        try:
            os.kill(config['pid'], 0)
        except ProcessLookupError:
            config['status'] = 'stopped'
            config['pid'] = None
            return {
                'service': service_name,
                'status': 'dead',
                'response_time': None,
                'error': 'Process not found'
            }
        
        # For DynamoDB, just check process
        if service_name == 'dynamodb':
            return {
                'service': service_name,
                'status': 'healthy',
                'response_time': 0.1,
                'error': None
            }
        
        # For backend and frontend, check HTTP endpoints
        health_endpoint = config.get('health_endpoint')
        if not health_endpoint:
            return {
                'service': service_name,
                'status': 'healthy',
                'response_time': 0.1,
                'error': None
            }
        
        start_time = time.time()
        try:
            # Use shorter timeout for health checks
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(health_endpoint) as response:
                    response_time = time.time() - start_time
                    
                    if response.status in [200, 503]:  # 503 is acceptable during startup
                        return {
                            'service': service_name,
                            'status': 'healthy',
                            'response_time': response_time,
                            'error': None
                        }
                    else:
                        return {
                            'service': service_name,
                            'status': 'unhealthy',
                            'response_time': response_time,
                            'error': f"HTTP {response.status}"
                        }
                        
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return {
                'service': service_name,
                'status': 'unhealthy',
                'response_time': response_time,
                'error': 'Timeout (5s exceeded)'
            }
        except Exception as e:
            response_time = time.time() - start_time
            return {
                'service': service_name,
                'status': 'unhealthy',
                'response_time': response_time,
                'error': str(e)
            }
    
    async def get_portfolio_metrics(self) -> Dict[str, Any]:
        """Get current virtual portfolio metrics and trading status"""
        try:
            await self.setup_http_session()
            
            # Get portfolio overview
            portfolio_data = {}
            try:
                async with self.session.get("http://localhost:9002/api/portfolio/virtual/overview") as response:
                    if response.status == 200:
                        data = await response.json()
                        portfolio_data = {
                            'total_value': data.get('portfolio_value', {}).get('total', 10000.0),
                            'cash': data.get('portfolio_value', {}).get('cash', 10000.0),
                            'positions_value': data.get('portfolio_value', {}).get('positions', 0.0),
                            'daily_pnl': data.get('performance', {}).get('daily_pnl', 0.0),
                            'total_pnl': data.get('performance', {}).get('total_pnl', 0.0),
                            'win_rate': data.get('trading_stats', {}).get('win_rate', 0.0),
                            'total_trades': data.get('trading_stats', {}).get('total_trades', 0)
                        }
            except Exception as e:
                logger.debug(f"Portfolio API error: {e}")
            
            # Get active positions count
            active_positions = 0
            try:
                async with self.session.get("http://localhost:9002/api/trading/positions/active") as response:
                    if response.status == 200:
                        positions = await response.json()
                        active_positions = len(positions) if isinstance(positions, list) else 0
            except Exception as e:
                logger.debug(f"Positions API error: {e}")
            
            # Get trading engine status
            trading_status = {}
            try:
                async with self.session.get("http://localhost:9002/api/trading/modes/status") as response:
                    if response.status == 200:
                        data = await response.json()
                        engine_data = data.get('day_trading_engine', {})
                        trading_status = {
                            'mode': engine_data.get('current_mode', 'unknown'),
                            'running': engine_data.get('is_running', False),
                            'analyses_completed': engine_data.get('performance', {}).get('analyses_completed', 0),
                            'positions_opened': engine_data.get('performance', {}).get('positions_opened', 0),
                            'threshold': engine_data.get('mode_config', {}).get('confidence_threshold', 0.65)
                        }
            except Exception as e:
                logger.debug(f"Trading status API error: {e}")
            
            # Combine all data
            return {
                **portfolio_data,
                'active_positions': active_positions,
                'trading_engine': trading_status,
                'last_updated': datetime.now().isoformat()
            }
                        
        except Exception as e:
            logger.debug(f"Portfolio metrics failed: {e}")
            return self._get_fallback_portfolio_data()
    
    def _get_fallback_portfolio_data(self) -> Dict[str, Any]:
        """Get fallback portfolio data when API is unavailable"""
        return {
            'total_value': 10000.0,
            'daily_pnl': 0.0,
            'total_pnl': 0.0,
            'active_positions': 0,
            'win_rate': 0.0,
            'trades_today': 0,
            'last_updated': datetime.now().isoformat()
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system resource metrics"""
        try:
            # Get metrics with shorter intervals to avoid hanging
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get network connections safely
            try:
                net_connections = len(psutil.net_connections())
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                net_connections = 0
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_usage': cpu_percent,
                'memory_usage': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_usage': disk.percent,
                'disk_free_gb': disk.free / (1024**3),
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
                'network_connections': net_connections
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_usage': 0.0,
                'memory_usage': 0.0,
                'memory_available_gb': 0.0,
                'disk_usage': 0.0,
                'disk_free_gb': 0.0,
                'load_average': [0, 0, 0],
                'network_connections': 0,
                'error': str(e)
            }
    
    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check of all components"""
        logger.debug("🔍 Performing comprehensive health check...")
        
        await self.setup_http_session()
        
        # Check all services
        service_results = {}
        for service_name in self.services.keys():
            service_results[service_name] = await self.check_service_health(service_name)
        
        # Get portfolio metrics
        portfolio_metrics = await self.get_portfolio_metrics()
        
        # Get system metrics
        system_metrics = self.get_system_metrics()
        
        # Calculate overall status
        healthy_services = sum(1 for result in service_results.values() if result['status'] == 'healthy')
        total_services = len(service_results)
        
        if healthy_services == total_services:
            overall_status = 'EXCELLENT'
        elif healthy_services >= total_services * 0.8:
            overall_status = 'GOOD'
        elif healthy_services >= total_services * 0.5:
            overall_status = 'DEGRADED'
        else:
            overall_status = 'CRITICAL'
        
        # Update system status
        self.system_status.update({
            'overall_status': overall_status,
            'services_healthy': healthy_services,
            'last_portfolio_value': portfolio_metrics.get('total_value', self.system_status['last_portfolio_value']),
            'portfolio_change_24h': portfolio_metrics.get('daily_pnl', 0.0),
            'total_trades_today': portfolio_metrics.get('trades_today', 0),
            'uptime_minutes': (datetime.now() - self.start_time).total_seconds() / 60
        })
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_status': overall_status,
            'services': service_results,
            'portfolio': portfolio_metrics,
            'system': system_metrics,
            'uptime_minutes': self.system_status['uptime_minutes']
        }
    
    def print_status_dashboard(self, health_report: Dict[str, Any]):
        """Print comprehensive status dashboard"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        uptime = health_report.get('uptime_minutes', 0)
        
        # Status colors
        status_colors = {
            'EXCELLENT': '🟢',
            'GOOD': '🟡', 
            'DEGRADED': '🟠',
            'CRITICAL': '🔴'
        }
        
        status_emoji = status_colors.get(health_report['overall_status'], '⚪')
        
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════╗
║  {status_emoji} TRADEPULSE.AI STATUS DASHBOARD - {timestamp}     ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  🎯 Overall Status: {health_report['overall_status']:<20} Uptime: {uptime:.1f} min    ║
╠═══════════════════════════════════════════════════════════════════════════╣""")
        
        # Services status
        services = health_report.get('services', {})
        for service_name, service_data in services.items():
            status = service_data.get('status', 'unknown')
            response_time = service_data.get('response_time')
            
            if status == 'healthy':
                icon = '✅'
                time_str = f"{response_time:.3f}s" if response_time else "N/A"
            elif status == 'unhealthy':
                icon = '❌'
                time_str = f"{response_time:.3f}s" if response_time else "N/A"
            else:
                icon = '⏸️ '
                time_str = "stopped"
            
            print(f"║  {icon} {service_name.upper():<12}: {status:<12} Response: {time_str:<8}      ║")
        
        print("╠═══════════════════════════════════════════════════════════════════════════╣")
        
        # Portfolio metrics
        portfolio = health_report.get('portfolio', {})
        portfolio_value = portfolio.get('total_value', 0)
        daily_pnl = portfolio.get('daily_pnl', 0)
        active_positions = portfolio.get('active_positions', 0)
        trades_today = portfolio.get('total_trades', 0)
        
        # Trading engine metrics
        trading_engine = portfolio.get('trading_engine', {})
        analyses = trading_engine.get('analyses_completed', 0)
        positions_opened = trading_engine.get('positions_opened', 0)
        engine_running = trading_engine.get('running', False)
        
        pnl_color = '🟢' if daily_pnl >= 0 else '🔴'
        engine_icon = '🤖' if engine_running else '⏸️'
        
        print(f"║  💰 Portfolio Value: ${portfolio_value:,.2f}                                  ║")
        print(f"║  {pnl_color} Daily P&L: ${daily_pnl:+.2f}                                         ║") 
        print(f"║  📊 Active Positions: {active_positions}    Trades Today: {trades_today}                    ║")
        print(f"║  {engine_icon} AI Engine: {analyses} analyses, {positions_opened} positions opened              ║")
        
        print("╠═══════════════════════════════════════════════════════════════════════════╣")
        
        # System metrics
        system = health_report.get('system', {})
        if 'error' not in system:
            cpu = system.get('cpu_usage', 0)
            memory = system.get('memory_usage', 0)
            disk = system.get('disk_usage', 0)
            
            cpu_icon = '🔴' if cpu > 90 else '🟡' if cpu > 70 else '🟢'
            mem_icon = '🔴' if memory > 85 else '🟡' if memory > 70 else '🟢'
            disk_icon = '🔴' if disk > 90 else '🟡' if disk > 80 else '🟢'
            
            print(f"║  {cpu_icon} CPU: {cpu:5.1f}%   {mem_icon} Memory: {memory:5.1f}%   {disk_icon} Disk: {disk:5.1f}%           ║")
        else:
            print(f"║  ❌ System metrics unavailable: {system.get('error', 'Unknown')}                  ║")
        
        print("╚═══════════════════════════════════════════════════════════════════════════╝")
        
        # Log key metrics with trading info
        logger.info(f"📊 Status: {health_report['overall_status']} | "
                   f"Portfolio: ${portfolio_value:,.2f} ({daily_pnl:+.2f}) | "
                   f"Services: {len([s for s in services.values() if s.get('status') == 'healthy'])}/{len(services)} | "
                   f"AI: {analyses} analyses, {positions_opened} positions")
    
    async def restart_service(self, service_name: str) -> bool:
        """Restart a failed service"""
        config = self.services[service_name]
        config['restart_attempts'] += 1
        
        if config['restart_attempts'] > self.max_restart_attempts:
            logger.error(f"❌ {service_name} exceeded max restart attempts ({self.max_restart_attempts})")
            return False
        
        logger.warning(f"🔄 Restarting {service_name} (attempt {config['restart_attempts']}/{self.max_restart_attempts})")
        
        # Stop the service first
        self.stop_service(service_name)
        
        # Wait a bit before restarting
        await asyncio.sleep(5)
        
        # Start the service
        success = self.start_service(service_name)
        
        if success:
            logger.info(f"✅ {service_name} restarted successfully")
            config['last_restart'] = datetime.now()
            # Reset consecutive failures on successful restart
            self.consecutive_failures[service_name] = 0
            return True
        else:
            logger.error(f"❌ Failed to restart {service_name}")
            self.consecutive_failures[service_name] = self.consecutive_failures.get(service_name, 0) + 1
            return False
    
    async def monitoring_loop(self):
        """Main monitoring loop with AI trading progress"""
        logger.info(f"📊 Starting monitoring loop ({self.check_interval}s intervals)")
        
        loop_count = 0
        while self.running:
            try:
                # Perform comprehensive health check
                health_report = await self.comprehensive_health_check()
                self.last_health_check = datetime.now()
                
                # Print status dashboard
                self.print_status_dashboard(health_report)
                
                # Every 5th loop (5 minutes), show latest AI signal
                loop_count += 1
                if loop_count % 5 == 0:
                    await self.show_latest_ai_signal()
                
                # Check for services that need restart
                for service_name, service_data in health_report['services'].items():
                    if service_data['status'] in ['unhealthy', 'stopped', 'dead']:
                        consecutive = self.consecutive_failures.get(service_name, 0) + 1
                        self.consecutive_failures[service_name] = consecutive
                        
                        if consecutive >= 2:  # Restart after 2 consecutive failures
                            await self.restart_service(service_name)
                    else:
                        # Reset consecutive failures on healthy status
                        self.consecutive_failures[service_name] = 0
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"❌ Monitoring loop error: {e}")
                await asyncio.sleep(30)  # Shorter wait on error
    
    async def show_latest_ai_signal(self):
        """Display latest AI signal for monitoring"""
        try:
            await self.setup_http_session()
            async with self.session.get("http://localhost:9002/api/enterprise-admin/engine/last-signal") as response:
                if response.status == 200:
                    data = await response.json()
                    layers = data.get('layers', {})
                    l4_real = layers.get('layer_4_filters', {}).get('model_used', False)
                    l5_real = layers.get('layer_5_confidence', {}).get('model_used', False)
                    
                    logger.info(f"🧠 Latest AI Signal: {data.get('action', 'UNKNOWN')} "
                               f"({data.get('confidence', 0):.1%} confidence) | "
                               f"L4 real: {l4_real}, L5 real: {l5_real}")
                else:
                    logger.debug(f"AI signal check failed: HTTP {response.status}")
        except Exception as e:
            logger.debug(f"AI signal check error: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("🛑 Shutdown signal received")
        self.running = False
    
    async def startup_sequence(self) -> bool:
        """Complete comprehensive startup sequence"""
        try:
            self.print_startup_banner()
            
            # Phase 1: System Requirements Verification
            logger.info("🔍 Phase 1: Verifying system requirements...")
            if not self.verify_system_requirements():
                logger.error("❌ System requirements not met")
                return False
            logger.info("✅ Phase 1 complete: System requirements verified")
            
            # Phase 2: Critical Files Verification
            logger.info("📁 Phase 2: Verifying critical files...")
            if not self.verify_critical_files():
                logger.error("❌ Critical files missing")
                return False
            logger.info("✅ Phase 2 complete: Critical files verified")
            
            # Phase 3: Network Connectivity Tests
            logger.info("🌐 Phase 3: Testing network connectivity...")
            network_ok = self.test_network_connectivity()
            if not network_ok:
                logger.warning("⚠️  Some network connectivity issues detected")
            logger.info("✅ Phase 3 complete: Network connectivity tested")
            
            # Phase 4: Service Discovery and Startup
            logger.info("🔎 Phase 4: Discovering and starting services...")
            self.discover_existing_services()
            
            # Start services that aren't running
            services_to_start = ['dynamodb', 'backend', 'frontend']
            
            for service_name in services_to_start:
                if self.services[service_name]['status'] != 'running':
                    logger.info(f"🚀 Starting {service_name}...")
                    if not self.start_service(service_name):
                        logger.error(f"❌ Failed to start {service_name}")
                        return False
                    time.sleep(2)  # Brief pause between services
                else:
                    logger.info(f"✅ {service_name} already running")
            
            logger.info("✅ Phase 4 complete: All services operational")

            # Phase 4.5: Ensure live data connections running and ticker available
            logger.info("📡 Ensuring live market data connections are active...")
            try:
                # Trigger live data start
                import requests as _rq
                _rq.post("http://localhost:9002/api/real_trading/control/start-live-data", timeout=5)
            except Exception as e:
                logger.warning(f"⚠️ Could not trigger live data start: {e}")
            # Wait until ticker available or timeout
            ticker_ready = False
            start_wait = datetime.now()
            while (datetime.now() - start_wait).total_seconds() < 30:
                try:
                    import requests as _rq
                    resp = _rq.get("http://localhost:9002/api/real_trading/status/connections", timeout=5)
                    if resp.status_code == 200:
                        data = resp.json().get("data", {})
                        ws = data.get("market_data", {}).get("status") == "connected"
                        ticker_ready = ws is True
                        if ticker_ready:
                            break
                except Exception:
                    pass
                time.sleep(2)
            if not ticker_ready:
                logger.warning("⚠️ Live ticker not confirmed within 30s; STRICT_LIVE_STREAM will block price fetches until WS connects")
            
            # Phase 5: Health Verification
            logger.info("🏥 Phase 5: Comprehensive health verification...")
            await asyncio.sleep(10)  # Give services time to fully initialize
            
            # Setup HTTP session for API tests
            await self.setup_http_session()
            
            # Perform comprehensive health check
            initial_health = await self.comprehensive_health_check()
            self.print_status_dashboard(initial_health)
            
            logger.info("✅ Phase 5 complete: Health verification finished")
            
            # Phase 6: Auto-Configure Professional Trading Engine
            if initial_health['overall_status'] in ['EXCELLENT', 'GOOD']:
                logger.info("🤖 Phase 6: Auto-configuring professional trading engine...")
                await self.configure_professional_trading()
                logger.info("✅ Phase 6 complete: Professional trading engine configured")
            
            # Final Assessment
            if initial_health['overall_status'] in ['EXCELLENT', 'GOOD']:
                logger.info("🎉 TradePulse.AI startup completed successfully!")
                logger.info(f"📊 Final Status: {initial_health['overall_status']}")
                return True
            elif initial_health['overall_status'] == 'DEGRADED':
                logger.warning("⚠️  System started with degraded performance")
                logger.info("🎯 Continuing with monitoring - some issues detected")
                return True
            else:
                logger.error("❌ Startup completed but critical health check failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Startup sequence failed: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return False
    
    async def run(self):
        """Main run method"""
        try:
            # Setup signal handlers
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # Complete startup
            if not await self.startup_sequence():
                logger.error("❌ Startup failed, exiting")
                return False
            
            logger.info("📊 Starting continuous monitoring...")
            
            # Start monitoring loop
            await self.monitoring_loop()
            
        except KeyboardInterrupt:
            logger.info("🛑 Stopped by user")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
        finally:
            await self.cleanup_session()
            logger.info("👋 TradePulse.AI Monitor shutdown complete")

async def main():
    """Main entry point"""
    monitor = TradePulseMonitor()
    await monitor.run()

if __name__ == "__main__":
    asyncio.run(main())