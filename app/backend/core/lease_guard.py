"""
TradePulse.AI Singleton LeaseGuard
Ensures only one instance runs trading_brain_loop() during rolling deploys
"""

import os
import asyncio
import time
import uuid
import logging
from typing import Optional
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from app.backend.core.config import get_settings

logger = logging.getLogger(__name__)

class LeaseGuard:
    """
    DynamoDB-based distributed lock to ensure only one trading brain runs
    Critical for preventing double-trading during App Runner rolling deploys
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.is_leader = False
        self.instance_id = os.getenv("APP_RUNNER_SERVICE_ID", str(uuid.uuid4()))
        self.table_name = f"{self.settings.DYNAMODB_TABLE_PREFIX}runtime"
        self.lease_seconds = 60  # Lease duration
        self.renew_interval = 30  # Renew every 30s
        self._renew_task: Optional[asyncio.Task] = None
        
        # DynamoDB client
        self.ddb = boto3.client(
            "dynamodb",
            region_name=self.settings.DYNAMODB_REGION,  # Use DYNAMODB_REGION for consistency
            endpoint_url=self.settings.DYNAMODB_ENDPOINT if self.settings.is_development else None
        )
        
        # Lease key
        self.lease_key = {
            "pk": {"S": "brain#main"},
            "sk": {"S": "lease"}
        }
        
        logger.info(f"🔐 LeaseGuard initialized - Instance: {self.instance_id}")
    
    async def try_acquire_lease(self) -> bool:
        """
        Try to acquire the trading brain lease
        Returns True if successful, False if another instance holds it
        """
        now = int(time.time())
        
        try:
            logger.info("🔐 Attempting to acquire trading brain lease...")
            
            # Try to acquire lease with condition
            self.ddb.put_item(
                TableName=self.table_name,
                Item={
                    "pk": {"S": "brain#main"},
                    "sk": {"S": "lease"},
                    "lease_owner": {"S": self.instance_id},
                    "lease_until": {"N": str(now + self.lease_seconds)},
                    "acquired_at": {"S": datetime.now(timezone.utc).isoformat()},
                    "ttl": {"N": str(now + 86400)},  # 24h cleanup
                },
                # Conditional: only if no lease exists OR lease has expired
                ConditionExpression="attribute_not_exists(pk) OR lease_until < :now",
                ExpressionAttributeValues={
                    ":now": {"N": str(now)}
                }
            )
            
            self.is_leader = True
            logger.info(f"✅ Acquired trading brain lease - Instance {self.instance_id} is now LEADER")
            
            # Start renewal task
            if self._renew_task is None or self._renew_task.done():
                self._renew_task = asyncio.create_task(self._renewal_loop())
            
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            
            if error_code == "ConditionalCheckFailedException":
                # Another instance holds the lease
                try:
                    # Get current lease holder info
                    response = self.ddb.get_item(
                        TableName=self.table_name,
                        Key=self.lease_key
                    )
                    
                    if 'Item' in response:
                        owner = response['Item'].get('lease_owner', {}).get('S', 'unknown')
                        until = int(response['Item'].get('lease_until', {}).get('N', 0))
                        until_dt = datetime.fromtimestamp(until, tz=timezone.utc)
                        
                        logger.info(f"🔒 Lease held by {owner} until {until_dt.isoformat()}")
                    
                except Exception as get_error:
                    logger.warning(f"Could not get lease info: {get_error}")
                
                self.is_leader = False
                return False
            else:
                logger.error(f"❌ Failed to acquire lease: {e}")
                self.is_leader = False
                return False
    
    async def _renewal_loop(self):
        """Background task to renew the lease every 30 seconds"""
        while self.is_leader:
            try:
                await asyncio.sleep(self.renew_interval)
                
                if not self.is_leader:
                    break
                
                now = int(time.time())
                
                # Renew lease (only if we still own it)
                self.ddb.update_item(
                    TableName=self.table_name,
                    Key=self.lease_key,
                    ConditionExpression="lease_owner = :me",
                    UpdateExpression="SET lease_until = :until, #ttl = :ttl, renewed_at = :renewed",
                    ExpressionAttributeNames={
                        "#ttl": "ttl"
                    },
                    ExpressionAttributeValues={
                        ":me": {"S": self.instance_id},
                        ":until": {"N": str(now + self.lease_seconds)},
                        ":ttl": {"N": str(now + 86400)},
                        ":renewed": {"S": datetime.now(timezone.utc).isoformat()}
                    }
                )
                
                logger.debug(f"🔄 Lease renewed for instance {self.instance_id}")
                
            except ClientError as e:
                if e.response.get('Error', {}).get('Code') == "ConditionalCheckFailedException":
                    # We lost the lease
                    logger.warning(f"⚠️ Lost trading brain lease - another instance took over")
                    self.is_leader = False
                    break
                else:
                    logger.error(f"❌ Failed to renew lease: {e}")
                    # Continue trying - might be temporary network issue
                    
            except Exception as e:
                logger.error(f"❌ Unexpected error in lease renewal: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def release_lease(self):
        """Release the lease gracefully during shutdown"""
        if not self.is_leader:
            return
        
        try:
            logger.info(f"🔓 Releasing trading brain lease for instance {self.instance_id}")
            
            # Stop renewal task
            if self._renew_task and not self._renew_task.done():
                self._renew_task.cancel()
                try:
                    await self._renew_task
                except asyncio.CancelledError:
                    pass
            
            # Delete lease record (only if we own it)
            self.ddb.delete_item(
                TableName=self.table_name,
                Key=self.lease_key,
                ConditionExpression="lease_owner = :me",
                ExpressionAttributeValues={
                    ":me": {"S": self.instance_id}
                }
            )
            
            self.is_leader = False
            logger.info("✅ Trading brain lease released successfully")
            
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') != "ConditionalCheckFailedException":
                logger.warning(f"⚠️ Failed to release lease: {e}")
        except Exception as e:
            logger.error(f"❌ Error releasing lease: {e}")
    
    async def heartbeat(self):
        """Update heartbeat timestamp (for monitoring)"""
        if not self.is_leader:
            return
        
        try:
            now = int(time.time())
            
            # Update heartbeat without affecting lease
            self.ddb.update_item(
                TableName=self.table_name,
                Key=self.lease_key,
                ConditionExpression="lease_owner = :me",
                UpdateExpression="SET heartbeat_ts = :heartbeat, #ttl = :ttl",
                ExpressionAttributeNames={
                    "#ttl": "ttl"
                },
                ExpressionAttributeValues={
                    ":me": {"S": self.instance_id},
                    ":heartbeat": {"N": str(now)},
                    ":ttl": {"N": str(now + 86400)}
                }
            )
            
        except Exception as e:
            logger.debug(f"Heartbeat update failed: {e}")
    
    def get_status(self) -> dict:
        """Get current lease status for monitoring"""
        return {
            "is_leader": self.is_leader,
            "instance_id": self.instance_id,
            "lease_table": self.table_name,
            "renew_task_running": self._renew_task is not None and not self._renew_task.done()
        }

# Global singleton instance
_lease_guard: Optional[LeaseGuard] = None

def get_lease_guard() -> LeaseGuard:
    """Get or create the global lease guard instance"""
    global _lease_guard
    if _lease_guard is None:
        _lease_guard = LeaseGuard()
    return _lease_guard
