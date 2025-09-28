"""
CloudWatch Heartbeat Service for TradePulse.AI Brain Controller
Emits heartbeat metrics only when instance holds the trading lease
"""

import os
import time
import asyncio
import logging
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.backend.core.config import get_settings

logger = logging.getLogger(__name__)

class CloudWatchHeartbeat:
    """
    Simple CloudWatch heartbeat service
    Emits BrainHeartbeat metric every 30s when instance is trading leader
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.namespace = os.getenv("CW_NAMESPACE", "TradePulse/Brain")
        self.service_name = os.getenv("SERVICE_NAME", "tradepulse-brain")
        self.is_running = False
        
        # CloudWatch client with retries
        self.cloudwatch = boto3.client(
            "cloudwatch",
            region_name=self.settings.AWS_REGION,
            config=Config(retries={"max_attempts": 3})
        )
        
        logger.info(f"💓 CloudWatch Heartbeat initialized - Namespace: {self.namespace}, Service: {self.service_name}")
    
    async def heartbeat_loop(self, lease_guard):
        """
        Background heartbeat loop - runs parallel with lease renewal
        Only emits metrics when instance holds the trading lease
        """
        self.is_running = True
        logger.info("💓 Starting CloudWatch heartbeat loop")
        
        while self.is_running:
            try:
                # Wait 30 seconds between heartbeats
                await asyncio.sleep(30)
                
                # Only emit heartbeat if we're the trading leader
                if lease_guard.is_leader:
                    await self._emit_heartbeat()
                else:
                    logger.debug("💓 Skipping heartbeat - not trading leader")
                    
            except Exception as e:
                logger.error(f"💓 Heartbeat loop error: {e}")
                # Continue loop despite errors
                await asyncio.sleep(5)
        
        logger.info("💓 Heartbeat loop stopped")
    
    async def _emit_heartbeat(self):
        """Emit heartbeat metric to CloudWatch"""
        try:
            # Emit BrainHeartbeat metric
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[{
                    "MetricName": "BrainHeartbeat",
                    "Dimensions": [
                        {"Name": "Service", "Value": self.service_name}
                    ],
                    "Timestamp": time.time(),
                    "Value": 1.0,
                    "Unit": "Count",
                }]
            )
            
            logger.debug(f"💓 Heartbeat emitted to CloudWatch - Service: {self.service_name}")
            
        except ClientError as e:
            logger.warning(f"💓 Failed to emit heartbeat: {e}")
        except Exception as e:
            logger.error(f"💓 Unexpected heartbeat error: {e}")
    
    async def emit_startup_metric(self):
        """Emit startup metric when brain controller starts"""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[{
                    "MetricName": "BrainStartup",
                    "Dimensions": [
                        {"Name": "Service", "Value": self.service_name}
                    ],
                    "Timestamp": time.time(),
                    "Value": 1.0,
                    "Unit": "Count",
                }]
            )
            
            logger.info(f"💓 Brain startup metric emitted")
            
        except Exception as e:
            logger.warning(f"💓 Failed to emit startup metric: {e}")
    
    async def emit_shutdown_metric(self):
        """Emit shutdown metric when brain controller stops"""
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[{
                    "MetricName": "BrainShutdown",
                    "Dimensions": [
                        {"Name": "Service", "Value": self.service_name}
                    ],
                    "Timestamp": time.time(),
                    "Value": 1.0,
                    "Unit": "Count",
                }]
            )
            
            logger.info(f"💓 Brain shutdown metric emitted")
            
        except Exception as e:
            logger.warning(f"💓 Failed to emit shutdown metric: {e}")
    
    def stop(self):
        """Stop the heartbeat loop"""
        self.is_running = False

# Global singleton instance
_heartbeat_service: Optional[CloudWatchHeartbeat] = None

def get_heartbeat_service() -> CloudWatchHeartbeat:
    """Get or create the global heartbeat service"""
    global _heartbeat_service
    if _heartbeat_service is None:
        _heartbeat_service = CloudWatchHeartbeat()
    return _heartbeat_service
