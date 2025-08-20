"""
Background Tasks System - Async Task Management for Trade Execution Layer
Manages background tasks, scheduling, and monitoring coordination
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Coroutine
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import signal
import traceback
from functools import wraps
import requests
import concurrent.futures

import structlog
from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Professional Auto Signal Scheduler
class AutoSignalScheduler:
    """Optimized automatic signal generation for aggressive day trading"""
    
    def __init__(self):
        self.is_running = False
        self.signal_interval = 180  # 3 minutes for optimal Bitcoin $500+ move detection
        self.last_signal_time = None
        self.signal_count = 0
        
    async def start(self):
        """Start automatic signal generation every 3 minutes"""
        if self.is_running:
            return
            
        self.is_running = True
        logger.info("🚀 AGGRESSIVE DAY TRADING SCHEDULER STARTED - 3 minute intervals")
        logger.info("🎯 Target: Bitcoin $500+ moves detection")
        
        # Start the signal generation loop
        asyncio.create_task(self._signal_loop())
        
    async def _signal_loop(self):
        """Main signal generation loop"""
        while self.is_running:
            try:
                await asyncio.sleep(self.signal_interval)
                await self._generate_signal()
            except Exception as e:
                logger.error(f"❌ Auto signal generation failed: {e}")
                await asyncio.sleep(20)  # Even shorter retry for aggressive trading
                
    async def _generate_signal(self):
        """Generate automatic trading signal using requests (stable)"""
        try:
            headers = {"Authorization": "Bearer enterprise_admin_token"}
            
            # Use requests in thread pool to avoid blocking
            def make_request():
                return requests.post(
                    f"{settings.BASE_URL}/api/signals/trigger-opportunity-test",
                    headers=headers,
                    timeout=30  # Increased from 10 to 30 seconds for model performance writes
                )
            
            # Run in thread pool
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                response = await loop.run_in_executor(executor, make_request)
                
                if response.status_code == 200:
                    result = response.json()
                    self.signal_count += 1
                    self.last_signal_time = datetime.now()
                    
                    status = result.get('test_result', {}).get('status', 'Unknown')
                    positions = result.get('test_result', {}).get('performance', {}).get('entry_engine_positions', 0)
                    logger.info(f"🎯 SIGNAL #{self.signal_count}: {status} | Positions: {positions}")
                else:
                    logger.warning(f"⚠️ Auto signal failed: HTTP {response.status_code}")
                        
        except Exception as e:
            logger.error(f"❌ Auto signal generation error: {e}")
    
    async def stop(self):
        """Stop automatic signal generation"""
        self.is_running = False
        logger.info(f"🛑 Aggressive scheduler stopped after {self.signal_count} signals")
        
    def get_performance_stats(self):
        """Get performance statistics"""
        uptime_minutes = ((datetime.now() - self.last_signal_time).total_seconds() / 60) if self.last_signal_time else 0
        signals_per_hour = (self.signal_count / max(uptime_minutes / 60, 0.1)) if uptime_minutes > 0 else 0
        
        return {
            "signals_generated": self.signal_count,
            "signals_per_hour": round(signals_per_hour, 1),
            "expected_signals_per_hour": 20,  # 60min / 3min = 20
            "uptime_minutes": round(uptime_minutes, 1)
        }


class TaskStatus(str, Enum):
    """Task status types"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(int, Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TaskConfig:
    """Task configuration"""
    name: str
    priority: TaskPriority
    max_retries: int
    retry_delay: float
    timeout: Optional[float]
    run_interval: Optional[float]  # For recurring tasks
    depends_on: List[str]  # Task dependencies
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskInfo:
    """Task information and status"""
    task_id: str
    name: str
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    retry_count: int
    error_message: Optional[str]
    result: Optional[Any]
    execution_time: Optional[float]
    config: TaskConfig
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'name': self.name,
            'status': self.status,
            'priority': self.priority,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'retry_count': self.retry_count,
            'error_message': self.error_message,
            'result': self.result,
            'execution_time': self.execution_time,
            'config': self.config.to_dict()
        }


class BackgroundTaskManager:
    """
    Background Task Manager for Trade Execution Layer
    
    Manages all background tasks including:
    - Position monitoring tasks
    - Data collection tasks
    - Alert management tasks
    - Performance tracking tasks
    - Cleanup tasks
    """
    
    def __init__(self):
        # Task storage
        self.tasks: Dict[str, TaskInfo] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.recurring_tasks: Dict[str, TaskInfo] = {}
        
        # Task execution state
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.worker_count = 5  # Number of worker coroutines
        self.workers: List[asyncio.Task] = []
        
        # Configuration
        self.config = {
            'max_concurrent_tasks': 50,
            'task_timeout_default': 300,  # 5 minutes
            'retry_delay_default': 60,    # 1 minute
            'max_retries_default': 3,
            'cleanup_interval': 600,      # 10 minutes
            'statistics_interval': 300,   # 5 minutes
            'heartbeat_interval': 30      # 30 seconds
        }
        
        # Performance tracking
        self.performance_stats = {
            'total_tasks_created': 0,
            'total_tasks_completed': 0,
            'total_tasks_failed': 0,
            'total_tasks_cancelled': 0,
            'average_execution_time': 0.0,
            'current_queue_size': 0,
            'current_running_tasks': 0,
            'uptime_seconds': 0.0,
            'worker_utilization': 0.0
        }
        
        # Signal handlers
        self.shutdown_event = asyncio.Event()
        self.setup_signal_handlers()
        
        # Task callbacks
        self.task_callbacks: Dict[str, List[Callable]] = {
            'on_task_start': [],
            'on_task_complete': [],
            'on_task_error': [],
            'on_task_retry': []
        }
        
        logger.info(
            "background_task_manager_initialized",
            worker_count=self.worker_count,
            config=self.config
        )
        # Schedule nightly retrain at 02:00 UTC and threshold calibration at 03:00 UTC
        self._nightly_retrain_task: Optional[asyncio.Task] = None
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except ValueError:
            # Signals not available in all environments
            pass
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_event.set()
    
    async def start(self):
        """Start the background task manager"""
        if self.is_running:
            logger.warning("background_task_manager_already_running")
            return
        
        self.is_running = True
        self.start_time = datetime.utcnow()
        
        logger.info("starting_background_task_manager")
        
        try:
            # Start worker coroutines
            for i in range(self.worker_count):
                worker = asyncio.create_task(
                    self._worker_loop(f"worker-{i}"),
                    name=f"background_worker_{i}"
                )
                self.workers.append(worker)
            
            # Start management tasks
            management_tasks = [
                asyncio.create_task(self._statistics_loop(), name="statistics_loop"),
                asyncio.create_task(self._cleanup_loop(), name="cleanup_loop"),
                asyncio.create_task(self._heartbeat_loop(), name="heartbeat_loop"),
                asyncio.create_task(self._recurring_tasks_loop(), name="recurring_tasks_loop"),
                asyncio.create_task(self._nightly_scheduler_loop(), name="nightly_scheduler_loop")
            ]
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            # Cancel management tasks
            for task in management_tasks:
                task.cancel()
            
            # Wait for management tasks to complete
            await asyncio.gather(*management_tasks, return_exceptions=True)
            
            logger.info("background_task_manager_started")
            
        except Exception as e:
            logger.error(
                "background_task_manager_start_failed",
                error=str(e),
                exc_info=True
            )
            raise
    
    async def stop(self):
        """Stop the background task manager"""
        if not self.is_running:
            logger.warning("background_task_manager_not_running")
            return
        
        logger.info("stopping_background_task_manager")
        
        self.is_running = False
        
        # Cancel all running tasks
        for task_id, task in self.running_tasks.items():
            if not task.done():
                task.cancel()
                
                # Update task info
                if task_id in self.tasks:
                    self.tasks[task_id].status = TaskStatus.CANCELLED
                    self.tasks[task_id].completed_at = datetime.utcnow()
        
        # Wait for running tasks to complete
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)
        
        # Cancel worker tasks
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to complete
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        
        # Update final statistics
        if self.start_time:
            self.performance_stats['uptime_seconds'] = (
                datetime.utcnow() - self.start_time
            ).total_seconds()
        
        logger.info(
            "background_task_manager_stopped",
            uptime_seconds=self.performance_stats['uptime_seconds'],
            total_tasks_completed=self.performance_stats['total_tasks_completed'],
            total_tasks_failed=self.performance_stats['total_tasks_failed']
        )
    
    async def submit_task(self, task_func: Callable, config: TaskConfig, *args, **kwargs) -> str:
        """
        Submit a task for execution
        
        Args:
            task_func: Function or coroutine to execute
            config: Task configuration
            *args: Task arguments
            **kwargs: Task keyword arguments
            
        Returns:
            Task ID
        """
        try:
            # Check if we're at capacity
            if len(self.tasks) >= self.config['max_concurrent_tasks']:
                logger.warning(
                    "task_queue_full",
                    current_tasks=len(self.tasks),
                    max_tasks=self.config['max_concurrent_tasks']
                )
                raise RuntimeError("Task queue is full")
            
            # Create task info
            task_id = str(uuid.uuid4())
            task_info = TaskInfo(
                task_id=task_id,
                name=config.name,
                status=TaskStatus.PENDING,
                priority=config.priority,
                created_at=datetime.utcnow(),
                started_at=None,
                completed_at=None,
                retry_count=0,
                error_message=None,
                result=None,
                execution_time=None,
                config=config
            )
            
            # Store task info
            self.tasks[task_id] = task_info
            
            # Create task wrapper
            task_wrapper = self._create_task_wrapper(task_func, task_info, *args, **kwargs)
            
            # Queue the task
            await self.task_queue.put((task_info.priority, task_id, task_wrapper))
            
            # Update statistics
            self.performance_stats['total_tasks_created'] += 1
            self.performance_stats['current_queue_size'] = self.task_queue.qsize()
            
            logger.info(
                "task_submitted",
                task_id=task_id,
                task_name=config.name,
                priority=config.priority,
                queue_size=self.task_queue.qsize()
            )
            
            return task_id
            
        except Exception as e:
            logger.error(
                "task_submission_failed",
                task_name=config.name,
                error=str(e),
                exc_info=True
            )
            raise
    
    def _create_task_wrapper(self, task_func: Callable, task_info: TaskInfo, *args, **kwargs):
        """Create a task wrapper with error handling and retries"""
        
        @wraps(task_func)
        async def wrapper():
            task_id = task_info.task_id
            
            try:
                # Update task status
                task_info.status = TaskStatus.RUNNING
                task_info.started_at = datetime.utcnow()
                
                # Call task start callbacks
                await self._call_task_callbacks('on_task_start', task_info)
                
                # Execute the task
                start_time = time.time()
                
                if asyncio.iscoroutinefunction(task_func):
                    result = await task_func(*args, **kwargs)
                else:
                    result = task_func(*args, **kwargs)
                
                execution_time = time.time() - start_time
                
                # Update task info
                task_info.status = TaskStatus.COMPLETED
                task_info.completed_at = datetime.utcnow()
                task_info.result = result
                task_info.execution_time = execution_time
                
                # Update statistics
                self.performance_stats['total_tasks_completed'] += 1
                self._update_average_execution_time(execution_time)
                
                # Call completion callbacks
                await self._call_task_callbacks('on_task_complete', task_info)
                
                logger.info(
                    "task_completed",
                    task_id=task_id,
                    task_name=task_info.name,
                    execution_time=execution_time
                )
                
                return result
                
            except Exception as e:
                error_message = str(e)
                task_info.error_message = error_message
                
                # Check if we should retry
                if task_info.retry_count < task_info.config.max_retries:
                    task_info.retry_count += 1
                    task_info.status = TaskStatus.RETRYING
                    
                    # Call retry callbacks
                    await self._call_task_callbacks('on_task_retry', task_info)
                    
                    logger.warning(
                        "task_retry",
                        task_id=task_id,
                        task_name=task_info.name,
                        retry_count=task_info.retry_count,
                        max_retries=task_info.config.max_retries,
                        error=error_message
                    )
                    
                    # Schedule retry
                    await asyncio.sleep(task_info.config.retry_delay)
                    
                    # Retry the task
                    return await wrapper()
                
                else:
                    # Max retries exceeded
                    task_info.status = TaskStatus.FAILED
                    task_info.completed_at = datetime.utcnow()
                    
                    # Update statistics
                    self.performance_stats['total_tasks_failed'] += 1
                    
                    # Call error callbacks
                    await self._call_task_callbacks('on_task_error', task_info)
                    
                    logger.error(
                        "task_failed",
                        task_id=task_id,
                        task_name=task_info.name,
                        retry_count=task_info.retry_count,
                        error=error_message,
                        traceback=traceback.format_exc()
                    )
                    
                    raise
        
        return wrapper
    
    async def _worker_loop(self, worker_name: str):
        """Worker loop that processes tasks from the queue"""
        logger.info(f"Starting worker: {worker_name}")
        
        while self.is_running:
            try:
                # Wait for a task with timeout
                try:
                    priority, task_id, task_wrapper = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Execute the task
                task = asyncio.create_task(task_wrapper(), name=f"task_{task_id}")
                self.running_tasks[task_id] = task
                
                # Update statistics
                self.performance_stats['current_running_tasks'] = len(self.running_tasks)
                self.performance_stats['current_queue_size'] = self.task_queue.qsize()
                
                # Wait for task completion
                try:
                    await task
                except Exception as e:
                    logger.error(
                        "worker_task_execution_failed",
                        worker_name=worker_name,
                        task_id=task_id,
                        error=str(e)
                    )
                finally:
                    # Remove from running tasks
                    self.running_tasks.pop(task_id, None)
                    self.performance_stats['current_running_tasks'] = len(self.running_tasks)
                
            except Exception as e:
                logger.error(
                    "worker_loop_error",
                    worker_name=worker_name,
                    error=str(e),
                    exc_info=True
                )
                await asyncio.sleep(1)
        
        logger.info(f"Worker stopped: {worker_name}")
    
    async def _statistics_loop(self):
        """Statistics tracking loop"""
        while self.is_running:
            try:
                await asyncio.sleep(self.config['statistics_interval'])
                
                # Update uptime
                if self.start_time:
                    self.performance_stats['uptime_seconds'] = (
                        datetime.utcnow() - self.start_time
                    ).total_seconds()
                
                # Calculate worker utilization
                if self.worker_count > 0:
                    self.performance_stats['worker_utilization'] = (
                        len(self.running_tasks) / self.worker_count
                    )
                
                # Log statistics
                logger.info(
                    "background_task_statistics",
                    **self.performance_stats
                )
                
            except Exception as e:
                logger.error(
                    "statistics_loop_error",
                    error=str(e),
                    exc_info=True
                )
    
    async def _cleanup_loop(self):
        """Cleanup loop for completed tasks"""
        while self.is_running:
            try:
                await asyncio.sleep(self.config['cleanup_interval'])
                
                # Clean up completed tasks older than 1 hour
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                
                tasks_to_remove = []
                for task_id, task_info in self.tasks.items():
                    if (task_info.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                        task_info.completed_at and task_info.completed_at < cutoff_time):
                        tasks_to_remove.append(task_id)
                
                for task_id in tasks_to_remove:
                    del self.tasks[task_id]
                
                if tasks_to_remove:
                    logger.info(
                        "task_cleanup_completed",
                        removed_tasks=len(tasks_to_remove),
                        remaining_tasks=len(self.tasks)
                    )
                
            except Exception as e:
                logger.error(
                    "cleanup_loop_error",
                    error=str(e),
                    exc_info=True
                )
    
    async def _heartbeat_loop(self):
        """Heartbeat loop for health monitoring"""
        while self.is_running:
            try:
                await asyncio.sleep(self.config['heartbeat_interval'])
                
                # Check system health
                health_status = {
                    'is_running': self.is_running,
                    'worker_count': len(self.workers),
                    'active_tasks': len(self.running_tasks),
                    'queued_tasks': self.task_queue.qsize(),
                    'total_tasks': len(self.tasks)
                }
                
                logger.debug("background_task_heartbeat", **health_status)
                
            except Exception as e:
                logger.error(
                    "heartbeat_loop_error",
                    error=str(e),
                    exc_info=True
                )

    async def _nightly_scheduler_loop(self):
        """Schedule nightly training/calibration and model reload."""
        while self.is_running:
            try:
                await asyncio.sleep(30)
                now = datetime.utcnow()
                # Kick at specific minutes to avoid drift (02:00 and 03:00 UTC)
                if now.hour == 2 and now.minute == 0:
                    try:
                        await self._run_nightly_training()
                    except Exception as e:
                        logger.error("nightly_training_failed", error=str(e), exc_info=True)
                    await asyncio.sleep(65)  # prevent double-fire within the same minute
                if now.hour == 3 and now.minute == 0:
                    try:
                        await self._run_threshold_calibration_and_reload()
                    except Exception as e:
                        logger.error("nightly_calibration_failed", error=str(e), exc_info=True)
                    await asyncio.sleep(65)
            except Exception as e:
                logger.error("nightly_scheduler_loop_error", error=str(e), exc_info=True)

    async def _run_nightly_training(self):
        """Run pro short-horizon LSTM training for 1m and 5m."""
        loop = asyncio.get_event_loop()
        import subprocess
        cmds = [
            [sys.executable, "app/backend/scripts/ml/train_pro_short_lstm.py", "--interval", "1m"],
            [sys.executable, "app/backend/scripts/ml/train_pro_short_lstm.py", "--interval", "5m"],
        ]
        for cmd in cmds:
            logger.info("nightly_training_start", cmd=" ".join(cmd))
            proc = await loop.run_in_executor(None, lambda: subprocess.run(cmd, capture_output=True, text=True))
            logger.info("nightly_training_result", returncode=proc.returncode)
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr or proc.stdout)

    async def _run_threshold_calibration_and_reload(self):
        """Calibrate thresholds and hot-reload the enterprise models into the engine."""
        loop = asyncio.get_event_loop()
        import subprocess, requests as rq
        cmds = [
            [sys.executable, "app/backend/scripts/ml/calibrate_short_lstm_thresholds.py", "--interval", "1m"],
            [sys.executable, "app/backend/scripts/ml/calibrate_short_lstm_thresholds.py", "--interval", "5m"],
        ]
        for cmd in cmds:
            logger.info("nightly_calibration_start", cmd=" ".join(cmd))
            proc = await loop.run_in_executor(None, lambda: subprocess.run(cmd, capture_output=True, text=True))
            logger.info("nightly_calibration_result", returncode=proc.returncode)
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr or proc.stdout)
        # Hot-reload enterprise models
        try:
            base = settings.BASE_URL or "http://localhost:9002"
            resp = rq.post(f"{base}/api/enterprise/models/reload", timeout=30)
            logger.info("enterprise_models_reload_status", status_code=getattr(resp, 'status_code', 'n/a'))
        except Exception as e:
            logger.error("enterprise_models_reload_failed", error=str(e), exc_info=True)
    
    async def _recurring_tasks_loop(self):
        """Loop for managing recurring tasks"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = datetime.utcnow()
                
                for task_id, task_info in self.recurring_tasks.items():
                    if task_info.config.run_interval is None:
                        continue
                    
                    # Check if it's time to run the task
                    if (task_info.completed_at is None or 
                        (current_time - task_info.completed_at).total_seconds() >= task_info.config.run_interval):
                        
                        # Reschedule the task
                        # This would need to be implemented with the original task function
                        logger.debug(
                            "recurring_task_due",
                            task_id=task_id,
                            task_name=task_info.name
                        )
                
            except Exception as e:
                logger.error(
                    "recurring_tasks_loop_error",
                    error=str(e),
                    exc_info=True
                )
    
    async def _call_task_callbacks(self, event_type: str, task_info: TaskInfo):
        """Call task callbacks for specific events"""
        try:
            callbacks = self.task_callbacks.get(event_type, [])
            
            for callback in callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(task_info)
                    else:
                        callback(task_info)
                except Exception as e:
                    logger.error(
                        "task_callback_error",
                        event_type=event_type,
                        task_id=task_info.task_id,
                        error=str(e)
                    )
        except Exception as e:
            logger.error(
                "task_callback_system_error",
                event_type=event_type,
                error=str(e),
                exc_info=True
            )
    
    def _update_average_execution_time(self, execution_time: float):
        """Update average execution time"""
        total_completed = self.performance_stats['total_tasks_completed']
        current_avg = self.performance_stats['average_execution_time']
        
        if total_completed > 0:
            self.performance_stats['average_execution_time'] = (
                (current_avg * (total_completed - 1) + execution_time) / total_completed
            )
    
    def add_task_callback(self, event_type: str, callback: Callable):
        """Add task callback for specific events"""
        if event_type in self.task_callbacks:
            self.task_callbacks[event_type].append(callback)
    
    def remove_task_callback(self, event_type: str, callback: Callable):
        """Remove task callback"""
        if event_type in self.task_callbacks and callback in self.task_callbacks[event_type]:
            self.task_callbacks[event_type].remove(callback)
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a specific task"""
        try:
            if task_id in self.running_tasks:
                task = self.running_tasks[task_id]
                task.cancel()
                
                # Update task info
                if task_id in self.tasks:
                    self.tasks[task_id].status = TaskStatus.CANCELLED
                    self.tasks[task_id].completed_at = datetime.utcnow()
                
                # Update statistics
                self.performance_stats['total_tasks_cancelled'] += 1
                
                logger.info(
                    "task_cancelled",
                    task_id=task_id
                )
                
                return True
            else:
                logger.warning(
                    "task_not_running",
                    task_id=task_id
                )
                return False
                
        except Exception as e:
            logger.error(
                "task_cancellation_failed",
                task_id=task_id,
                error=str(e),
                exc_info=True
            )
            return False
    
    def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """Get task status"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> Dict[str, TaskInfo]:
        """Get all tasks"""
        return self.tasks.copy()
    
    def get_running_tasks(self) -> Dict[str, TaskInfo]:
        """Get running tasks"""
        return {
            task_id: task_info for task_id, task_info in self.tasks.items()
            if task_info.status == TaskStatus.RUNNING
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get task manager statistics"""
        return {
            'performance_stats': self.performance_stats,
            'task_counts': {
                'total': len(self.tasks),
                'running': len(self.running_tasks),
                'queued': self.task_queue.qsize(),
                'completed': len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]),
                'failed': len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED]),
                'cancelled': len([t for t in self.tasks.values() if t.status == TaskStatus.CANCELLED])
            },
            'configuration': self.config,
            'is_running': self.is_running,
            'worker_count': len(self.workers)
        }


# Global task manager instance
task_manager = BackgroundTaskManager()


# Convenience functions
async def submit_task(task_func: Callable, name: str, priority: TaskPriority = TaskPriority.NORMAL, 
                     max_retries: int = 3, retry_delay: float = 60.0, timeout: Optional[float] = None,
                     run_interval: Optional[float] = None, depends_on: Optional[List[str]] = None,
                     *args, **kwargs) -> str:
    """Submit a task to the global task manager"""
    
    config = TaskConfig(
        name=name,
        priority=priority,
        max_retries=max_retries,
        retry_delay=retry_delay,
        timeout=timeout,
        run_interval=run_interval,
        depends_on=depends_on if depends_on is not None else []
    )
    
    return await task_manager.submit_task(task_func, config, *args, **kwargs)


async def start_task_manager():
    """Start the global task manager"""
    await task_manager.start()


async def stop_task_manager():
    """Stop the global task manager"""
    await task_manager.stop()


def get_task_manager() -> BackgroundTaskManager:
    """Get the global task manager instance"""
    return task_manager 