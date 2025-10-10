"""
Signal Decision Recorder - Track ALL trading decisions for ML learning
=====================================================================

Records every trading signal decision (ENTER + WAIT) to enable learning
from missed opportunities.

CRITICAL for day trading: Learn from signals we DIDN'T take!

Author: TradePulse.AI Development Team
Created: October 2025
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from decimal import Decimal

from app.backend.core.database import get_database_client

logger = logging.getLogger(__name__)


@dataclass
class SignalDecision:
    """Record of every trading signal decision"""
    decision_id: str
    timestamp: datetime
    symbol: str
    
    # Signal information
    signal_action: str  # BUY, SELL, HOLD
    signal_confidence: float
    signal_type: str  # primary, exploratory
    layer_analysis: Dict[str, Any]
    
    # Decision
    decision: str  # ENTER, WAIT, REJECT
    decision_reason: str
    decision_factors: Dict[str, Any]  # What caused WAIT?
    
    # Market context at decision time
    price_at_decision: float
    volume_ratio: float
    volatility: float
    rsi: float
    trend_strength: float
    
    # Phase and session context
    warmup_phase: int
    session: str
    
    # CRITICAL: Track what happened AFTER (filled by background job)
    price_after_1h: Optional[float] = None
    price_after_4h: Optional[float] = None
    price_after_24h: Optional[float] = None
    actual_move_pct_1h: Optional[float] = None
    actual_move_pct_4h: Optional[float] = None
    actual_move_pct_24h: Optional[float] = None
    
    # Learning metrics (calculated later)
    was_correct_decision: Optional[bool] = None
    missed_opportunity_pct: Optional[float] = None
    opportunity_cost_usd: Optional[float] = None


class SignalDecisionRecorder:
    """
    Records ALL trading decisions for machine learning analysis
    
    Enables learning from:
    - Signals that were executed (ENTER)
    - Signals that were rejected (WAIT)
    - Opportunity cost calculation
    - Threshold optimization
    """
    
    def __init__(self):
        self.db_client = None
        self.is_initialized = False
        self.decisions_recorded_count = 0
        
        logger.info("📝 Signal Decision Recorder initialized")
    
    async def initialize(self):
        """Initialize the recorder"""
        if self.is_initialized:
            return
        
        try:
            self.db_client = get_database_client()
            self.is_initialized = True
            logger.info("✅ Signal Decision Recorder ready")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Signal Decision Recorder: {e}")
            raise
    
    async def record_decision(
        self,
        signal: Any,  # TradingSignal object
        decision: str,  # ENTER, WAIT, REJECT
        decision_reason: str,
        decision_factors: Dict[str, Any],
        market_context: Dict[str, Any],
        session_context: Dict[str, Any]
    ) -> str:
        """
        Record a trading signal decision
        
        Args:
            signal: TradingSignal object from enterprise engine
            decision: ENTER, WAIT, or REJECT
            decision_reason: Why this decision was made
            decision_factors: Detailed factors (consensus_score, phase, etc.)
            market_context: Current market data (price, volume, volatility, etc.)
            session_context: Trading session info (warmup_phase, session_name)
        
        Returns:
            decision_id: Unique ID for this decision
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Generate unique decision ID
            timestamp = datetime.now(timezone.utc)
            decision_id = f"decision_{timestamp.strftime('%Y%m%d_%H%M%S')}_{self.decisions_recorded_count:04d}"
            
            # Extract market context
            price = market_context.get("price", 0.0)
            volume_ratio = market_context.get("volume_ratio", 1.0)
            volatility = market_context.get("volatility", 0.02)
            rsi = market_context.get("rsi", 50.0)
            trend_strength = market_context.get("trend_strength", 0.0)
            
            # Create decision record
            signal_decision = SignalDecision(
                decision_id=decision_id,
                timestamp=timestamp,
                symbol=signal.symbol if hasattr(signal, 'symbol') else "BTCUSDT",
                signal_action=signal.action if hasattr(signal, 'action') else "UNKNOWN",
                signal_confidence=float(signal.confidence) if hasattr(signal, 'confidence') else 0.0,
                signal_type=signal.signal_type if hasattr(signal, 'signal_type') else "exploratory",
                layer_analysis=signal.layer_analysis if hasattr(signal, 'layer_analysis') else {},
                decision=decision,
                decision_reason=decision_reason,
                decision_factors=decision_factors,
                price_at_decision=price,
                volume_ratio=volume_ratio,
                volatility=volatility,
                rsi=rsi,
                trend_strength=trend_strength,
                warmup_phase=session_context.get("warmup_phase", 3),
                session=session_context.get("session", "unknown")
            )
            
            # Save to DynamoDB
            await self._save_decision(signal_decision)
            
            self.decisions_recorded_count += 1
            
            # Log decision (abbreviated for WAIT, full for ENTER)
            if decision == "ENTER":
                logger.info(f"📝 DECISION RECORDED: {decision_id} → ENTER {signal_decision.signal_action} "
                           f"conf={signal_decision.signal_confidence:.2f} @${price:.2f}")
            else:
                logger.debug(f"📝 DECISION RECORDED: {decision_id} → WAIT "
                            f"reason={decision_reason} conf={signal_decision.signal_confidence:.2f}")
            
            return decision_id
            
        except Exception as e:
            logger.error(f"❌ Failed to record decision: {e}")
            return ""
    
    async def _save_decision(self, decision: SignalDecision):
        """Save decision to DynamoDB"""
        try:
            if not self.db_client:
                return
            
            # Convert to DynamoDB-friendly format
            decision_data = {
                "decision_id": decision.decision_id,  # PK
                "timestamp": int(decision.timestamp.timestamp()),  # SK
                "timestamp_iso": decision.timestamp.isoformat(),
                "symbol": decision.symbol,
                "signal_action": decision.signal_action,
                "signal_confidence": Decimal(str(decision.signal_confidence)),
                "signal_type": decision.signal_type,
                "layer_analysis": decision.layer_analysis,
                "decision": decision.decision,
                "decision_reason": decision.decision_reason,
                "decision_factors": decision.decision_factors,
                "price_at_decision": Decimal(str(decision.price_at_decision)),
                "volume_ratio": Decimal(str(decision.volume_ratio)),
                "volatility": Decimal(str(decision.volatility)),
                "rsi": Decimal(str(decision.rsi)),
                "trend_strength": Decimal(str(decision.trend_strength)),
                "warmup_phase": decision.warmup_phase,
                "session": decision.session,
                # Future prices (filled by background job)
                "price_after_1h": None,
                "price_after_4h": None,
                "price_after_24h": None,
                "actual_move_pct_1h": None,
                "actual_move_pct_4h": None,
                "actual_move_pct_24h": None,
                # Learning metrics (calculated later)
                "was_correct_decision": None,
                "missed_opportunity_pct": None,
                "opportunity_cost_usd": None
            }
            
            self.db_client.put_item("trading_decisions", decision_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to save decision to DynamoDB: {e}")
    
    async def get_recent_decisions(
        self,
        hours: int = 24,
        decision_filter: Optional[str] = None
    ) -> List[SignalDecision]:
        """
        Get recent trading decisions
        
        Args:
            hours: Lookback period in hours
            decision_filter: Optional filter ("ENTER", "WAIT", "REJECT")
        
        Returns:
            List of SignalDecision objects
        """
        try:
            if not self.db_client:
                return []
            
            # Scan trading_decisions table
            items = self.db_client.scan_table("trading_decisions")
            
            # Filter by time and decision type
            from datetime import timedelta
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            decisions = []
            for item in items:
                try:
                    timestamp = datetime.fromisoformat(item.get("timestamp_iso", ""))
                    if timestamp < cutoff_time:
                        continue
                    
                    if decision_filter and item.get("decision") != decision_filter:
                        continue
                    
                    # Convert back to SignalDecision
                    decision = SignalDecision(
                        decision_id=item.get("decision_id", ""),
                        timestamp=timestamp,
                        symbol=item.get("symbol", "BTCUSDT"),
                        signal_action=item.get("signal_action", ""),
                        signal_confidence=float(item.get("signal_confidence", 0)),
                        signal_type=item.get("signal_type", ""),
                        layer_analysis=item.get("layer_analysis", {}),
                        decision=item.get("decision", ""),
                        decision_reason=item.get("decision_reason", ""),
                        decision_factors=item.get("decision_factors", {}),
                        price_at_decision=float(item.get("price_at_decision", 0)),
                        volume_ratio=float(item.get("volume_ratio", 1.0)),
                        volatility=float(item.get("volatility", 0.02)),
                        rsi=float(item.get("rsi", 50.0)),
                        trend_strength=float(item.get("trend_strength", 0.0)),
                        warmup_phase=int(item.get("warmup_phase", 3)),
                        session=item.get("session", "unknown"),
                        price_after_1h=float(item.get("price_after_1h")) if item.get("price_after_1h") else None,
                        price_after_4h=float(item.get("price_after_4h")) if item.get("price_after_4h") else None,
                        price_after_24h=float(item.get("price_after_24h")) if item.get("price_after_24h") else None,
                        actual_move_pct_1h=float(item.get("actual_move_pct_1h")) if item.get("actual_move_pct_1h") else None,
                        actual_move_pct_4h=float(item.get("actual_move_pct_4h")) if item.get("actual_move_pct_4h") else None,
                        actual_move_pct_24h=float(item.get("actual_move_pct_24h")) if item.get("actual_move_pct_24h") else None,
                        was_correct_decision=item.get("was_correct_decision"),
                        missed_opportunity_pct=float(item.get("missed_opportunity_pct")) if item.get("missed_opportunity_pct") else None,
                        opportunity_cost_usd=float(item.get("opportunity_cost_usd")) if item.get("opportunity_cost_usd") else None
                    )
                    decisions.append(decision)
                    
                except Exception as parse_error:
                    logger.debug(f"Failed to parse decision item: {parse_error}")
                    continue
            
            return decisions
            
        except Exception as e:
            logger.error(f"❌ Failed to get recent decisions: {e}")
            return []
    
    async def get_wait_decisions_for_learning(self, hours: int = 24) -> List[SignalDecision]:
        """
        Get WAIT decisions for missed opportunity analysis
        
        Returns only WAIT decisions that can be analyzed for learning
        """
        return await self.get_recent_decisions(hours=hours, decision_filter="WAIT")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get recording statistics"""
        try:
            recent_decisions = await self.get_recent_decisions(hours=24)
            
            enter_count = sum(1 for d in recent_decisions if d.decision == "ENTER")
            wait_count = sum(1 for d in recent_decisions if d.decision == "WAIT")
            reject_count = sum(1 for d in recent_decisions if d.decision == "REJECT")
            
            return {
                "total_decisions_24h": len(recent_decisions),
                "enter_decisions": enter_count,
                "wait_decisions": wait_count,
                "reject_decisions": reject_count,
                "wait_rate": wait_count / len(recent_decisions) if recent_decisions else 0,
                "total_recorded": self.decisions_recorded_count
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get statistics: {e}")
            return {}


# Global instance
_recorder_instance = None


async def get_signal_decision_recorder() -> SignalDecisionRecorder:
    """Get or create global Signal Decision Recorder instance"""
    global _recorder_instance
    
    if _recorder_instance is None:
        _recorder_instance = SignalDecisionRecorder()
        await _recorder_instance.initialize()
    
    return _recorder_instance

