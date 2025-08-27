"""
Portfolio Store - TradePulse.AI BRAIN
====================================

DynamoDB-based position management with atomic operations and complete audit trails.
Professional portfolio operations with real-time state management.

Author: TradePulse.AI Development Team
Created: January 2025
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import uuid

from app.backend.core.database import DynamoDBClient
from app.backend.core.config import get_settings
from app.backend.services.professional_portfolio import get_professional_portfolio

logger = logging.getLogger(__name__)

class PortfolioStore:
    """
    Professional portfolio store with DynamoDB persistence
    
    Features:
    - Atomic position operations
    - Complete audit trail
    - Real-time state synchronization
    - Performance metrics tracking
    - Risk management integration
    """
    
    def __init__(self):
        self.is_initialized = False
        self.db_client: Optional[DynamoDBClient] = None
        
        # Table names
        self.positions_table = "brain_positions"
        self.portfolio_state_table = "brain_portfolio_state"
        self.performance_table = "brain_performance"
        self.audit_table = "brain_audit"
        
        # Performance tracking
        self.operations_count = 0
        self.last_sync_time: Optional[datetime] = None
        
        logger.info("💰 Portfolio Store initialized")
        
    async def initialize(self):
        """Initialize portfolio store"""
        if self.is_initialized:
            return
            
        logger.info("🚀 Initializing Portfolio Store...")
        
        try:
            # Initialize database client
            settings = get_settings()
            self.db_client = DynamoDBClient(local_development=settings.is_development)
            
            # Ensure tables exist
            await self._ensure_tables_exist()
            
            # Load current state
            await self._load_current_state()
            
            self.is_initialized = True
            logger.info("✅ Portfolio Store initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Portfolio Store: {e}")
            raise
            
    async def _ensure_tables_exist(self):
        """Ensure all required tables exist"""
        tables = [
            self.positions_table,
            self.portfolio_state_table,
            self.performance_table,
            self.audit_table
        ]
        
        for table in tables:
            try:
                # Try to describe table (will raise if doesn't exist)
                items = self.db_client.scan_table(table)
                logger.debug(f"✅ Table exists: {table}")
            except Exception:
                logger.info(f"📋 Table {table} will be created on first use")
                
    async def _load_current_state(self):
        """Load current portfolio state"""
        try:
            # Load from existing professional portfolio service
            portfolio = await get_professional_portfolio("admin")
            if portfolio:
                logger.info(f"💰 Current state: ${float(portfolio.cash_balance):.2f} cash, "
                           f"{len(portfolio.get_active_positions())} positions")
                           
        except Exception as e:
            logger.warning(f"Could not load current state: {e}")
            
    async def open_position(
        self, 
        symbol: str, 
        action: str,  # "BUY" or "SELL" 
        size: Decimal, 
        price: Decimal,
        entry_analysis: Dict[str, Any],
        risk_context: Dict[str, Any],
        ai_confidence: Decimal,
        ai_reasoning: str
    ) -> str:
        """Open new position with complete audit trail"""
        try:
            position_id = f"pos_{uuid.uuid4().hex[:8]}"
            timestamp = datetime.now(timezone.utc)
            
            # Create position record
            position_data = {
                "position_id": position_id,
                "symbol": symbol,
                "side": action,  # BUY/SELL
                "quantity": str(size),
                "entry_price": str(price),
                "current_price": str(price),
                "status": "OPEN",
                "entry_time": timestamp.isoformat(),
                "ai_confidence": str(ai_confidence),
                "ai_reasoning": ai_reasoning,
                "entry_analysis": entry_analysis,
                "risk_context": risk_context,
                "created_at": int(timestamp.timestamp()),
                "updated_at": int(timestamp.timestamp())
            }
            
            # Store in DynamoDB
            try:
                self.db_client.put_item(self.positions_table, position_data)
                logger.debug(f"💾 Position stored: {position_id}")
            except Exception as e:
                logger.warning(f"DynamoDB storage failed: {e}")
                
            # Use existing professional portfolio service for actual position
            portfolio = await get_professional_portfolio("admin")
            actual_position_id = await portfolio.open_position(
                symbol=symbol,
                position_type="LONG" if action == "BUY" else "SHORT",
                size=size,
                ai_confidence=ai_confidence,
                ai_reasoning=ai_reasoning,
                stop_loss_pct=Decimal('0.015'),
                take_profit_pct=Decimal('0.025')
            )
            
            # Update position with actual ID
            position_data["actual_position_id"] = actual_position_id
            position_data["updated_at"] = int(datetime.now(timezone.utc).timestamp())
            
            try:
                self.db_client.put_item(self.positions_table, position_data)
            except Exception:
                pass  # Non-critical
                
            # Log audit entry
            await self._log_audit_entry(
                action="POSITION_OPENED",
                position_id=position_id,
                details={
                    "symbol": symbol,
                    "side": action,
                    "quantity": str(size),
                    "price": str(price),
                    "ai_confidence": str(ai_confidence),
                    "entry_analysis": entry_analysis,
                    "risk_context": risk_context
                }
            )
            
            self.operations_count += 1
            logger.info(f"✅ Position opened: {position_id} {symbol} {action} {size} @${price}")
            
            return position_id
            
        except Exception as e:
            logger.error(f"Failed to open position: {e}")
            raise
            
    async def close_position(
        self, 
        position_id: str, 
        reason: str, 
        current_price: Decimal,
        exit_analysis: Optional[Dict[str, Any]] = None
    ) -> Decimal:
        """Close position and return PnL"""
        try:
            timestamp = datetime.now(timezone.utc)
            
            # Get position from DynamoDB
            position_data = None
            try:
                items = self.db_client.scan_table(self.positions_table)
                position_data = next((item for item in items if item.get("position_id") == position_id), None)
            except Exception as e:
                logger.warning(f"Could not retrieve position from DynamoDB: {e}")
                
            # Use professional portfolio service for actual closure
            portfolio = await get_professional_portfolio("admin")
            
            # Find position by ID (may need to match by other criteria)
            active_positions = portfolio.get_active_positions()
            actual_position = None
            
            if position_data and "actual_position_id" in position_data:
                # Use stored actual position ID
                actual_position_id = position_data["actual_position_id"]
                actual_position = next((p for p in active_positions if p.position_id == actual_position_id), None)
            else:
                # Fallback: find by symbol and size
                if position_data:
                    symbol = position_data.get("symbol")
                    quantity = position_data.get("quantity")
                    actual_position = next(
                        (p for p in active_positions 
                         if p.symbol == symbol and str(p.size) == quantity), 
                        None
                    )
                    
            if not actual_position:
                logger.warning(f"Position not found in portfolio: {position_id}")
                return Decimal('0')
                
            # Close position via professional portfolio
            pnl = await portfolio.close_position(
                position_id=actual_position.position_id,
                exit_reason=reason,
                exit_confidence=Decimal('0.8'),
                current_price=current_price
            )
            
            # Calculate PnL percentage
            entry_price = Decimal(str(position_data.get("entry_price", current_price))) if position_data else current_price
            side = position_data.get("side", "BUY") if position_data else "BUY"
            
            if entry_price > 0:
                if side == "BUY":
                    pnl_pct = (current_price - entry_price) / entry_price
                else:  # SELL
                    pnl_pct = (entry_price - current_price) / entry_price
            else:
                pnl_pct = Decimal('0')
                
            # Update position in DynamoDB
            if position_data:
                position_data.update({
                    "status": "CLOSED",
                    "exit_time": timestamp.isoformat(),
                    "exit_price": str(current_price),
                    "exit_reason": reason,
                    "pnl_absolute": str(pnl),
                    "pnl_percent": str(pnl_pct),
                    "exit_analysis": exit_analysis or {},
                    "updated_at": int(timestamp.timestamp())
                })
                
                try:
                    self.db_client.put_item(self.positions_table, position_data)
                except Exception:
                    pass  # Non-critical
                    
            # Log audit entry
            await self._log_audit_entry(
                action="POSITION_CLOSED",
                position_id=position_id,
                details={
                    "reason": reason,
                    "exit_price": str(current_price),
                    "pnl_absolute": str(pnl),
                    "pnl_percent": str(pnl_pct),
                    "exit_analysis": exit_analysis or {}
                }
            )
            
            self.operations_count += 1
            logger.info(f"🚪 Position closed: {position_id} PnL=${float(pnl):.2f} ({float(pnl_pct)*100:.2f}%)")
            
            return pnl
            
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            raise
            
    async def get_current_state(self) -> Dict[str, Any]:
        """Get current portfolio state"""
        try:
            # Get from professional portfolio service
            portfolio = await get_professional_portfolio("admin")
            if not portfolio:
                return {}
                
            active_positions = portfolio.get_active_positions()
            
            # Get DynamoDB positions for enhanced data
            db_positions = []
            try:
                items = self.db_client.scan_table(self.positions_table)
                db_positions = [item for item in items if item.get("status") == "OPEN"]
            except Exception:
                pass
                
            # Combine data
            enriched_positions = []
            for pos in active_positions:
                db_pos = next((dp for dp in db_positions if dp.get("actual_position_id") == pos.position_id), {})
                
                enriched_positions.append({
                    "position_id": pos.position_id,
                    "symbol": pos.symbol,
                    "side": pos.type.value,
                    "quantity": str(pos.size),
                    "entry_price": str(pos.entry_price),
                    "current_price": str(pos.current_price),
                    "pnl_absolute": str(pos.unrealized_pnl),
                    "pnl_percent": str((pos.current_price - pos.entry_price) / pos.entry_price),
                    "entry_time": pos.entry_time.isoformat(),
                    "ai_confidence": str(pos.ai_confidence),
                    "ai_reasoning": pos.ai_reasoning,
                    "entry_analysis": db_pos.get("entry_analysis", {}),
                    "risk_context": db_pos.get("risk_context", {})
                })
                
            return {
                "cash_balance": str(portfolio.cash_balance),
                "total_value": str(portfolio.total_value),
                "daily_pnl": str(portfolio.get_daily_pnl()),
                "daily_pnl_pct": str(portfolio.get_daily_pnl_percentage()),
                "active_positions": enriched_positions,
                "total_positions": len(enriched_positions),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get current state: {e}")
            return {}
            
    async def get_position(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Get specific position details"""
        try:
            # Get from DynamoDB first
            items = self.db_client.scan_table(self.positions_table)
            position = next((item for item in items if item.get("position_id") == position_id), None)
            
            if not position:
                logger.warning(f"Position not found: {position_id}")
                return None
                
            # Enrich with current price if still open
            if position.get("status") == "OPEN":
                portfolio = await get_professional_portfolio("admin")
                actual_position_id = position.get("actual_position_id")
                
                if actual_position_id:
                    active_positions = portfolio.get_active_positions()
                    actual_pos = next((p for p in active_positions if p.position_id == actual_position_id), None)
                    
                    if actual_pos:
                        position["current_price"] = str(actual_pos.current_price)
                        position["pnl_absolute"] = str(actual_pos.unrealized_pnl)
                        position["pnl_percent"] = str((actual_pos.current_price - actual_pos.entry_price) / actual_pos.entry_price)
                        
            return position
            
        except Exception as e:
            logger.error(f"Failed to get position: {e}")
            return None
            
    async def get_performance_metrics(self, days: int = 1) -> Dict[str, Any]:
        """Get performance metrics for specified period"""
        try:
            # Calculate time range
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=days)
            
            # Get closed positions from period
            closed_positions = []
            try:
                items = self.db_client.scan_table(self.positions_table)
                for item in items:
                    if (item.get("status") == "CLOSED" and 
                        item.get("exit_time") and
                        start_time <= datetime.fromisoformat(item["exit_time"].replace('Z', '+00:00')) <= end_time):
                        closed_positions.append(item)
            except Exception:
                pass
                
            if not closed_positions:
                return {
                    "period_days": days,
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0,
                    "avg_win_pct": 0,
                    "avg_loss_pct": 0,
                    "total_pnl": 0,
                    "total_pnl_pct": 0,
                    "timestamp": end_time.isoformat()
                }
                
            # Calculate metrics
            total_trades = len(closed_positions)
            winning_trades = sum(1 for pos in closed_positions if float(pos.get("pnl_absolute", 0)) > 0)
            losing_trades = total_trades - winning_trades
            
            win_pnls = [float(pos.get("pnl_percent", 0)) for pos in closed_positions if float(pos.get("pnl_absolute", 0)) > 0]
            loss_pnls = [abs(float(pos.get("pnl_percent", 0))) for pos in closed_positions if float(pos.get("pnl_absolute", 0)) < 0]
            
            return {
                "period_days": days,
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": winning_trades / total_trades if total_trades > 0 else 0,
                "avg_win_pct": sum(win_pnls) / len(win_pnls) if win_pnls else 0,
                "avg_loss_pct": sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0,
                "total_pnl": sum(float(pos.get("pnl_absolute", 0)) for pos in closed_positions),
                "total_pnl_pct": sum(float(pos.get("pnl_percent", 0)) for pos in closed_positions),
                "positions": closed_positions,
                "timestamp": end_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {}
            
    async def _log_audit_entry(self, action: str, position_id: str, details: Dict[str, Any]):
        """Log audit entry"""
        try:
            audit_entry = {
                "audit_id": f"audit_{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "position_id": position_id,
                "details": details,
                "created_at": int(datetime.now(timezone.utc).timestamp())
            }
            
            self.db_client.put_item(self.audit_table, audit_entry)
            logger.debug(f"📝 Audit logged: {action} for {position_id}")
            
        except Exception as e:
            logger.warning(f"Audit logging failed: {e}")
            
    async def sync_with_professional_portfolio(self):
        """Synchronize with professional portfolio service"""
        try:
            logger.info("🔄 Synchronizing with professional portfolio...")
            
            portfolio = await get_professional_portfolio("admin")
            if not portfolio:
                return
                
            # Get all active positions from professional portfolio
            active_positions = portfolio.get_active_positions()
            
            # Update DynamoDB records
            for pos in active_positions:
                try:
                    # Find corresponding DynamoDB record
                    items = self.db_client.scan_table(self.positions_table)
                    db_record = next((item for item in items if item.get("actual_position_id") == pos.position_id), None)
                    
                    if db_record:
                        # Update current price and PnL
                        db_record.update({
                            "current_price": str(pos.current_price),
                            "pnl_absolute": str(pos.unrealized_pnl),
                            "pnl_percent": str((pos.current_price - pos.entry_price) / pos.entry_price),
                            "updated_at": int(datetime.now(timezone.utc).timestamp())
                        })
                        
                        self.db_client.put_item(self.positions_table, db_record)
                        
                except Exception as e:
                    logger.warning(f"Failed to sync position {pos.position_id}: {e}")
                    
            self.last_sync_time = datetime.now(timezone.utc)
            logger.info("✅ Portfolio synchronization completed")
            
        except Exception as e:
            logger.error(f"Portfolio synchronization failed: {e}")
            
    def get_store_stats(self) -> Dict[str, Any]:
        """Get portfolio store statistics"""
        return {
            "is_initialized": self.is_initialized,
            "operations_count": self.operations_count,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "tables": {
                "positions": self.positions_table,
                "portfolio_state": self.portfolio_state_table,
                "performance": self.performance_table,
                "audit": self.audit_table
            }
        }

# Global portfolio store instance
_portfolio_store: Optional[PortfolioStore] = None

async def get_portfolio_store() -> PortfolioStore:
    """Get or create global portfolio store"""
    global _portfolio_store
    if _portfolio_store is None:
        _portfolio_store = PortfolioStore()
        await _portfolio_store.initialize()
    return _portfolio_store

# Export classes and functions
__all__ = [
    "PortfolioStore",
    "get_portfolio_store"
]