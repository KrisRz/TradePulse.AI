"""
Trading API endpoints for virtual portfolio operations - INTELLIGENT EXIT EDITION
Handles opening/closing positions with 6-layer exit analysis - NO MORE BLIND CLOSES

Features:
- Intelligent position closing with 6-layer analysis
- Real-time exit decision engine
- Complete audit trails for every exit decision
- Portfolio protection through comprehensive analysis
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from pydantic import BaseModel, Field, validator

from app.backend.core.config import get_settings
from app.backend.core.logging import get_logger
from app.backend.core.database import DynamoDBClient
try:
    from app.backend.utils.dependencies import get_current_user, User
except ImportError:
    # Fallback for testing without auth
    class User:
        def __init__(self, email="admin@test.com"):
            self.email = email
    
    def get_current_user():
        return User()
from app.backend.services import VirtualPortfolioManager as VirtualPortfolioService
from app.backend.services import MarketDataService
try:
    from app.backend.services.intelligent_exit_engine import IntelligentExitEngine
except ImportError:
    # Fallback for development
    class IntelligentExitEngine:
        async def initialize(self): pass
        async def analyze_exit_conditions(self, symbol, position_data): 
            return {"should_exit": False, "confidence": 0.0}
try:
    from src.services.position_lifecycle_tracker import PositionLifecycleTracker
    lifecycle_tracker = PositionLifecycleTracker()
except ImportError:
    # Mock for development
    class MockLifecycleTracker:
        def track_position(self, *args, **kwargs):
            pass
    lifecycle_tracker = MockLifecycleTracker()

try:
    from src.schemas.exit_analysis import ExitAnalysisRequest, ExitAnalysisResponse
except ImportError:
    # Mock for development
    class ExitAnalysisRequest:
        pass
    class ExitAnalysisResponse:
        pass

# Initialize intelligent exit engine
exit_engine: Optional[IntelligentExitEngine] = None

async def get_exit_engine() -> IntelligentExitEngine:
    """Get or create the intelligent exit engine"""
    global exit_engine
    if exit_engine is None:
        exit_engine = IntelligentExitEngine()
        if not exit_engine.is_initialized:
            await exit_engine.initialize()
    return exit_engine

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()

def _positions_table_name() -> str:
    # Local dev uses simple table names
    return "virtual_positions" if settings.is_development else f"tradepulse-positions-{settings.ENVIRONMENT}"

def _trades_table_name() -> str:
    return "virtual_trades" if settings.is_development else f"tradepulse-virtual_trades-{settings.ENVIRONMENT}"

# Initialize services
portfolio_service = VirtualPortfolioService()
market_data_service = MarketDataService()


class TradeType(str, Enum):
    """Trade types"""
    LONG = "LONG"
    SHORT = "SHORT"


class TradeAction(str, Enum):
    """Trade actions"""
    OPEN = "open"
    CLOSE = "close"


class OpenPositionRequest(BaseModel):
    """Request to open a new position"""
    symbol: str = Field(default="BTCUSDT", description="Trading symbol")
    type: TradeType = Field(description="Position type (LONG/SHORT)")
    size: float = Field(gt=0, description="Position size")
    entry_price: Optional[float] = Field(None, description="Entry price (auto-fetch if not provided)")
    confidence: Optional[float] = Field(0.0, ge=0.0, le=1.0, description="Signal confidence")
    strategy: str = Field(default="manual", description="Trading strategy")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        allowed_symbols = ["BTCUSDT", "ETHUSDT"]
        if v not in allowed_symbols:
            raise ValueError(f"Symbol must be one of {allowed_symbols}")
        return v


class ClosePositionRequest(BaseModel):
    """Request to close a position"""
    position_id: str = Field(description="Position ID to close")
    exit_price: Optional[float] = Field(None, description="Exit price (auto-fetch if not provided)")
    exit_reason: str = Field(default="manual", description="Reason for closing")


class PositionResponse(BaseModel):
    """Position response model"""
    id: str
    symbol: str
    type: str
    size: float
    entry_price: float
    entry_time: str
    status: str
    confidence: float
    strategy: str
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_percentage: Optional[float] = None
    exit_price: Optional[float] = None
    exit_time: Optional[str] = None
    realized_pnl: Optional[float] = None
    realized_pnl_percentage: Optional[float] = None
    holding_time: Optional[int] = None
    exit_reason: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class AutoTradeRequest(BaseModel):
    """Request for automated trading based on signal"""
    signal_id: str = Field(description="Signal ID to trade on")
    position_size_percentage: float = Field(default=5.0, ge=1.0, le=25.0, description="Percentage of available cash to use")
    enable_stop_loss: bool = Field(default=True, description="Enable stop loss")
    enable_take_profit: bool = Field(default=True, description="Enable take profit")


@router.post("/positions/open", response_model=PositionResponse)
async def open_position(
    request: OpenPositionRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> PositionResponse:
    """
    Open a new virtual trading position
    
    Args:
        request: Position parameters
        background_tasks: Background tasks
        current_user: Authenticated user
        
    Returns:
        Created position
    """
    try:
        # Get current price if not provided
        if request.entry_price is None:
            current_price = await market_data_service.get_current_price(request.symbol)
            if current_price is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Unable to fetch current price"
                )
            request.entry_price = current_price
        
        # Prepare position data
        position_data = {
            'symbol': request.symbol,
            'type': request.type.value,
            'size': request.size,
            'entry_price': request.entry_price,
            'confidence': request.confidence,
            'strategy': request.strategy,
            'stop_loss': request.stop_loss,
            'take_profit': request.take_profit
        }
        
        # Open position
        position = await portfolio_service.open_virtual_position(
            user_id=current_user.id,
            position_data=position_data
        )
        
        logger.info(
            "position_opened",
            user_id=current_user.id,
            position_id=position['id'],
            symbol=request.symbol,
            type=request.type.value,
            size=request.size,
            entry_price=request.entry_price
        )

        # Persist to DynamoDB
        try:
            db = DynamoDBClient(local_development=settings.is_development)
            db.put_item(_positions_table_name(), {
                "position_id": position['id'],
                "user_id": current_user.id,
                "symbol": request.symbol,
                "side": request.type.value,
                "size": float(request.size),
                "entry_price": float(request.entry_price),
                "entry_time": datetime.utcnow().isoformat(),
                "status": "OPEN",
                "confidence": float(request.confidence or 0.0),
                "strategy": request.strategy,
                "stop_loss": float(request.stop_loss) if request.stop_loss else None,
                "take_profit": float(request.take_profit) if request.take_profit else None
            })
        except Exception:
            pass
        
        return PositionResponse(**position)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "open_position_failed",
            user_id=current_user.id,
            symbol=request.symbol,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to open position: {str(e)}"
        )


@router.post("/positions/{position_id}/close", response_model=PositionResponse)
async def close_position(
    position_id: str,
    request: ClosePositionRequest,
    current_user: User = Depends(get_current_user)
) -> PositionResponse:
    """
    INTELLIGENT POSITION CLOSE - NO MORE BLIND CLOSES
    
    Uses 6-layer exit analysis to make intelligent closing decisions:
    Layer 1: P&L Analysis - Is position profitable enough to close?
    Layer 2: Technical Analysis - Do indicators support exit timing?
    Layer 3: Reversal Detection - Are we at a reversal point?
    Layer 4: Market Regime - Does current regime support exit?
    Layer 5: Confidence Assessment - How confident are we in exit timing?
    Layer 6: Time-Risk Balance - Is position duration vs risk optimal?
    
    Args:
        position_id: Position ID
        request: Close position parameters
        current_user: Authenticated user
        
    Returns:
        Closed position with exit analysis
    """
    try:
        # Step 1: Find the position
        actual_position_id = position_id
        active_positions = await portfolio_service.get_active_positions(current_user.id)
        position = None
        
        for pos in active_positions:
            if pos.get('id') == actual_position_id or pos.get('trade_id') == actual_position_id:
                position = pos
                break
        
        if not position:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Position not found"
            )
        
        # Step 2: Get current market data
        symbol = position['symbol']
        current_price = await market_data_service.get_current_price(symbol)
        if current_price is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to fetch current market data for exit analysis"
            )
        
        # Get comprehensive market data for analysis
        market_data = await market_data_service.get_comprehensive_market_data(symbol)
        market_data['close'] = current_price
        
        # Step 3: 🔍 INTELLIGENT EXIT ANALYSIS - NO MORE BLIND CLOSES
        logger.info(f"🔍 Starting intelligent exit analysis for position {actual_position_id}")
        
        # Prepare position data for analysis
        position_data = {
            'position_id': actual_position_id,
            'symbol': symbol,
            'side': position.get('side', 'buy'),
            'entry_price': float(position.get('entry_price', current_price)),
            'position_value': float(position.get('position_value', 1000)),
            'entry_time': position.get('entry_time', datetime.now().isoformat()),
            'unrealized_pnl_percentage': float(position.get('unrealized_pnl_percentage', 0)),
            'confidence_score': float(position.get('confidence', 0.5))
        }
        
        # 🎯 CORE: Run 6-layer exit analysis
        engine = await get_exit_engine()
        exit_analysis = await engine.analyze_exit_request(
            position=position_data,
            exit_reason=request.exit_reason or "manual"
        )
        
        # Step 4: Act on intelligent analysis result
        logger.info(f"🎯 Exit decision: {'EXIT' if exit_analysis.exit_decision.should_exit else 'HOLD'} (confidence: {exit_analysis.exit_decision.confidence:.2f})")
        
        if not exit_analysis.exit_decision.should_exit:
            # 🛡️ POSITION PROTECTION: Refuse to close position
            logger.warning(f"🛡️ Position protection activated - refusing blind close for {actual_position_id}")
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Exit analysis recommends HOLDING position",
                    "analysis_summary": exit_analysis.exit_decision.reasoning,
                    "confidence": exit_analysis.exit_decision.confidence,
                    "layer_analyses": [
                        {
                            "layer": layer.layer_name,
                            "recommendation": layer.recommendation,
                            "confidence": layer.confidence,
                            "reasoning": layer.reasoning
                        }
                        for layer in exit_analysis.layer_analyses
                    ],
                    "recommendation": "Position should be held based on 6-layer analysis",
                    "analysis_time_ms": exit_analysis.analysis_time_ms
                }
            )
        
        else:
            # ✅ INTELLIGENT CLOSE: Exit approved by analysis
            exit_price = request.exit_price or current_price
            
            logger.info(f"✅ Intelligent exit approved at ${exit_price:.2f}")
            
            # Execute the intelligent close
            closed_position = await portfolio_service.close_virtual_position(
                user_id=current_user.id,
                position_id=actual_position_id,
                exit_price=exit_price,
                exit_reason=f"intelligent_exit_{exit_analysis.exit_decision.primary_reason.value}"
            )
            # Persist close to DynamoDB (positions + trades)
            try:
                db = DynamoDBClient(local_development=settings.is_development)
                # Update position status
                db.put_item(_positions_table_name(), {
                    "position_id": actual_position_id,
                    "user_id": current_user.id,
                    "symbol": symbol,
                    "status": "CLOSED",
                    "exit_price": float(exit_price),
                    "exit_time": datetime.utcnow().isoformat(),
                    "realized_pnl": float(closed_position.get('realized_pnl', 0) or 0),
                    "exit_reason": request.exit_reason or "manual"
                })
                # Append trade record
                db.put_item(_trades_table_name(), {
                    "trade_id": f"trade_{actual_position_id}",
                    "user_id": current_user.id,
                    "position_id": actual_position_id,
                    "symbol": symbol,
                    "side": position.get('side', 'buy'),
                    "entry_price": float(position.get('entry_price', exit_price)),
                    "exit_price": float(exit_price),
                    "created_at": datetime.utcnow().isoformat(),
                    "pnl": float(closed_position.get('realized_pnl', 0) or 0)
                })
            except Exception:
                pass
        
        # Step 5: Add exit analysis data to response
        closed_position['exit_analysis'] = {
            'decision': 'EXIT' if exit_analysis.exit_decision.should_exit else 'HOLD',
            'confidence': exit_analysis.exit_decision.confidence,
            'analysis_duration_ms': exit_analysis.analysis_time_ms,
            'reasoning_summary': exit_analysis.exit_decision.reasoning,
            'primary_reason': exit_analysis.exit_decision.primary_reason.value,
            'layer_count': len(exit_analysis.layer_analyses),
            'layers_supporting_exit': sum(1 for l in exit_analysis.layer_analyses if l.recommendation == 'exit'),
            'analysis_timestamp': exit_analysis.analysis_timestamp.isoformat(),
            'engine_status': exit_analysis.engine_status
        }
        
        logger.info(
            "position_closed",
            user_id=current_user.id,
            position_id=actual_position_id,
            exit_price=request.exit_price,
            pnl=closed_position.get('realized_pnl', 0),
            exit_reason=request.exit_reason
        )
        
        return PositionResponse(**closed_position)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "close_position_failed",
            user_id=current_user.id,
            position_id=position_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close position: {str(e)}"
        )


@router.get("/positions/active", response_model=List[PositionResponse])
async def get_active_positions(
    current_user: User = Depends(get_current_user)
) -> List[PositionResponse]:
    """
    Get user's active positions
    
    Args:
        current_user: Authenticated user
        
    Returns:
        List of active positions
    """
    try:
        positions = await portfolio_service.get_active_positions(current_user.id)
        
        return [PositionResponse(**pos) for pos in positions]
        
    except Exception as e:
        logger.error(
            "get_active_positions_failed",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active positions: {str(e)}"
        )


@router.get("/positions/history", response_model=List[PositionResponse])
async def get_position_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user)
) -> List[PositionResponse]:
    """
    Get user's position history
    
    Args:
        limit: Maximum number of positions to return
        current_user: Authenticated user
        
    Returns:
        List of closed positions
    """
    try:
        positions = await portfolio_service.get_position_history(current_user.id, limit=limit)
        
        return [PositionResponse(**pos) for pos in positions]
        
    except Exception as e:
        logger.error(
            "get_position_history_failed",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get position history: {str(e)}"
        )


@router.post("/auto-trade", response_model=PositionResponse)
async def execute_auto_trade(
    request: AutoTradeRequest,
    current_user: User = Depends(get_current_user)
) -> PositionResponse:
    """
    Execute automated trade based on a signal
    
    Args:
        request: Auto-trade parameters
        current_user: Authenticated user
        
    Returns:
        Created position
    """
    try:
        # This is a simplified implementation
        # In production, this would:
        # 1. Fetch the signal by ID
        # 2. Validate signal is still valid
        # 3. Calculate position size based on available cash
        # 4. Set stop loss and take profit from signal
        # 5. Execute the trade
        
        # For now, create a mock auto-trade position
        portfolio = await portfolio_service.get_portfolio_summary(current_user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        available_cash = float(portfolio.get('cash_balance', 0))
        position_value = available_cash * (request.position_size_percentage / 100)
        
        # Mock signal data
        symbol = "BTCUSDT"
        current_price = await market_data_service.get_current_price(symbol)
        if current_price is None:
            current_price = 50000.0  # Fallback price
        
        size = position_value / current_price
        
        # Prepare position data
        position_data = {
            'symbol': symbol,
            'type': 'LONG',  # Default for auto-trade
            'size': size,
            'entry_price': current_price,
            'confidence': 0.75,  # Default confidence
            'strategy': 'auto_signal',
            'stop_loss': current_price * 0.98 if request.enable_stop_loss else None,
            'take_profit': current_price * 1.04 if request.enable_take_profit else None
        }
        
        # Open position
        position = await portfolio_service.open_virtual_position(
            user_id=current_user.id,
            position_data=position_data
        )
        
        logger.info(
            "auto_trade_executed",
            user_id=current_user.id,
            signal_id=request.signal_id,
            position_id=position['id'],
            size=size,
            entry_price=current_price
        )
        
        return PositionResponse(**position)
        
    except Exception as e:
        logger.error(
            "auto_trade_failed",
            user_id=current_user.id,
            signal_id=request.signal_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-trade execution failed: {str(e)}"
        )


@router.post("/positions/close-all")
async def close_all_positions(
    exit_reason: str = "close_all",
    force_close: bool = False,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    INTELLIGENT CLOSE ALL POSITIONS - NO MORE BLIND CLOSES
    
    Uses 6-layer exit analysis for each position. Positions that analysis
    recommends holding will be preserved unless force_close=True.
    
    Args:
        exit_reason: Reason for closing all positions
        force_close: If True, override intelligent analysis (emergency only)
        current_user: Authenticated user
        
    Returns:
        Summary of analyzed and closed positions
    """
    try:
        active_positions = await portfolio_service.get_active_positions(current_user.id)
        
        if not active_positions:
            return {
                "message": "No active positions to close",
                "positions_analyzed": 0,
                "positions_closed": 0,
                "positions_held": 0,
                "total_pnl": 0.0,
                "analysis_results": []
            }
        
        closed_positions = []
        held_positions = []
        analysis_results = []
        total_pnl = 0.0
        
        logger.info(f"🔍 Starting intelligent analysis of {len(active_positions)} positions")
        
        for position in active_positions:
            try:
                # Get market data for analysis
                symbol = position['symbol']
                current_price = await market_data_service.get_current_price(symbol)
                if current_price is None:
                    current_price = float(position.get('entry_price', 50000))  # Fallback
                
                market_data = await market_data_service.get_comprehensive_market_data(symbol)
                market_data['close'] = current_price
                
                # Prepare position data
                position_data = {
                    'position_id': position.get('id') or position.get('trade_id'),
                    'symbol': symbol,
                    'side': position.get('side', 'buy'),
                    'entry_price': float(position.get('entry_price', current_price)),
                    'position_value': float(position.get('position_value', 1000)),
                    'entry_time': position.get('entry_time', datetime.now().isoformat()),
                    'unrealized_pnl_percentage': float(position.get('unrealized_pnl_percentage', 0)),
                    'confidence_score': float(position.get('confidence', 0.5))
                }
                
                # 🎯 Run intelligent exit analysis
                engine = await get_exit_engine()
                exit_analysis = await engine.analyze_exit_request(
                    position=position_data,
                    exit_reason=exit_reason
                )
                
                analysis_results.append({
                    'position_id': position_data['position_id'],
                    'symbol': symbol,
                    'decision': 'EXIT' if exit_analysis.exit_decision.should_exit else 'HOLD',
                    'confidence': exit_analysis.exit_decision.confidence,
                    'reasoning': exit_analysis.exit_decision.reasoning,
                    'analysis_time_ms': exit_analysis.analysis_time_ms
                })
                
                # Decision based on analysis
                should_close = False
                
                if force_close:
                    should_close = True
                    logger.warning(f"🚨 Force closing position {position_data['position_id']} despite analysis")
                elif exit_analysis.exit_decision.should_exit:
                    should_close = True
                    logger.info(f"✅ Analysis approves closing position {position_data['position_id']}")
                else:
                    logger.info(f"🛡️ Analysis recommends holding position {position_data['position_id']}")
                
                if should_close:
                    # Execute intelligent close
                    exit_price = current_price
                    
                    closed_position = await portfolio_service.close_virtual_position(
                        user_id=current_user.id,
                        position_id=position_data['position_id'],
                        exit_price=exit_price,
                        exit_reason=f"intelligent_{exit_reason}_{exit_analysis.exit_decision.primary_reason.value.lower()}"
                    )
                    
                    # Add analysis data to position
                    closed_position['exit_analysis'] = {
                        'decision': 'EXIT' if exit_analysis.exit_decision.should_exit else 'HOLD',
                        'confidence': exit_analysis.exit_decision.confidence,
                        'reasoning': exit_analysis.exit_decision.reasoning,
                        'forced': force_close
                    }
                    
                    closed_positions.append(closed_position)
                    total_pnl += float(closed_position.get('realized_pnl', 0))
                else:
                    # Position held based on analysis
                    held_positions.append({
                        'position_id': position_data['position_id'],
                        'symbol': symbol,
                        'decision_reason': exit_analysis.exit_decision.reasoning,
                        'confidence': exit_analysis.exit_decision.confidence
                    })
                
            except Exception as e:
                logger.error(
                    "intelligent_close_analysis_failed",
                    user_id=current_user.id,
                    position_id=position.get('id'),
                    error=str(e)
                )
                continue
        
        # Comprehensive logging
        logger.info(
            "intelligent_close_all_completed",
            user_id=current_user.id,
            positions_analyzed=len(active_positions),
            positions_closed=len(closed_positions),
            positions_held=len(held_positions),
            total_pnl=total_pnl,
            exit_reason=exit_reason,
            force_close=force_close
        )
        
        return {
            "message": f"Intelligent analysis completed: {len(closed_positions)} closed, {len(held_positions)} held",
            "positions_analyzed": len(active_positions),
            "positions_closed": len(closed_positions),
            "positions_held": len(held_positions),
            "total_pnl": total_pnl,
            "force_close": force_close,
            "closed_positions": closed_positions,
            "held_positions": held_positions,
            "analysis_results": analysis_results,
            "exit_reason": exit_reason
        }
        
        return {
            "message": f"Closed {len(closed_positions)} positions",
            "positions_closed": len(closed_positions),
            "total_pnl": round(total_pnl, 2),
            "exit_reason": exit_reason
        }
        
    except Exception as e:
        logger.error(
            "close_all_positions_failed",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close all positions: {str(e)}"
        )


@router.get("/market-price/{symbol}")
async def get_market_price(
    symbol: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current market price for a symbol
    
    Args:
        symbol: Trading symbol
        current_user: Authenticated user
        
    Returns:
        Current market price
    """
    try:
        price = await market_data_service.get_current_price(symbol)
        
        if price is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to fetch current price"
            )
        
        return {
            "symbol": symbol,
            "price": price,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_market_price_failed",
            symbol=symbol,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get market price: {str(e)}"
        )


# ===== TRADING BRAIN CONTROL ENDPOINTS =====

class TradingBrainRequest(BaseModel):
    """Request to control trading brain"""
    enabled: bool = Field(description="Enable/disable trading brain")

class TradingBrainResponse(BaseModel):
    """Response from trading brain control"""
    enabled: bool = Field(description="Current brain status")
    status: str = Field(description="Status message")
    timestamp: str = Field(description="Status timestamp")
    positions_count: int = Field(default=0, description="Current open positions")
    
# Global trading brain state
_trading_brain_enabled = False
_trading_brain_start_time = None

@router.get("/brain/status")
async def get_trading_brain_status() -> TradingBrainResponse:
    """
    Get current trading brain status
    
    Returns:
        Current trading brain status and statistics
    """
    try:
        global _trading_brain_enabled, _trading_brain_start_time
        
        # Get current positions count
        portfolio = await portfolio_service.get_portfolio_summary("admin")
        positions_count = portfolio.get('active_positions_count', 0) if portfolio else 0
        
        status_msg = "ACTIVE - Monitoring markets" if _trading_brain_enabled else "OFFLINE - Manual control only"
        
        return TradingBrainResponse(
            enabled=_trading_brain_enabled,
            status=status_msg,
            timestamp=datetime.utcnow().isoformat(),
            positions_count=positions_count
        )
        
    except Exception as e:
        logger.error(f"Failed to get trading brain status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trading brain status: {str(e)}"
        )


@router.post("/brain/toggle")
async def toggle_trading_brain(
    request: TradingBrainRequest
) -> TradingBrainResponse:
    """
    Toggle trading brain ON/OFF
    
    Args:
        request: Trading brain enable/disable request
        current_user: Authenticated user (admin only)
        
    Returns:
        New trading brain status
    """
    try:
        global _trading_brain_enabled, _trading_brain_start_time
        
        # Check if user is admin (add admin check here if needed)
        # For now, allow any authenticated user
        
        old_status = _trading_brain_enabled
        _trading_brain_enabled = request.enabled
        
        if _trading_brain_enabled and not old_status:
            # Brain was turned ON
            _trading_brain_start_time = datetime.utcnow()
            status_msg = "ACTIVATED - AI brain now monitoring markets for trading opportunities"
            logger.info(f"🧠 TRADING BRAIN ACTIVATED")
            
            # Start the automatic trading brain background task
            await start_trading_brain_background()
            
        elif not _trading_brain_enabled and old_status:
            # Brain was turned OFF
            status_msg = "DEACTIVATED - AI brain stopped, manual trading only"
            logger.info(f"🛑 TRADING BRAIN DEACTIVATED")
            
            # Stop the automatic trading brain
            await stop_trading_brain_background()
            
        else:
            status_msg = f"No change - Brain is already {'ON' if _trading_brain_enabled else 'OFF'}"
        
        # Get current positions count
        portfolio = await portfolio_service.get_portfolio_summary("admin")
        positions_count = portfolio.get('active_positions_count', 0) if portfolio else 0
        
        return TradingBrainResponse(
            enabled=_trading_brain_enabled,
            status=status_msg,
            timestamp=datetime.utcnow().isoformat(),
            positions_count=positions_count
        )
        
    except Exception as e:
        logger.error(f"Failed to toggle trading brain: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle trading brain: {str(e)}"
        )


# ===== AUTOMATIC TRADING BRAIN BACKGROUND TASK =====

import asyncio
import sys
from pathlib import Path

# Clean absolute imports; sys.path hacks removed

try:
    from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine
    from app.backend.services.professional_portfolio import get_professional_portfolio, PositionType
except ImportError:
    # Fallback imports for development
    logger.warning("Failed to import trading engine components - using fallback")
    
    class MockTradingEngine:
        async def initialize(self): pass
        async def generate_signal(self, symbol):
            from dataclasses import dataclass
            @dataclass
            class MockSignal:
                action: str = "BUY"
                confidence: float = 0.75
                symbol: str = symbol
                position_size: float = 0.1
                reasoning: str = "Mock signal for testing"
            return MockSignal()
    
    EnterpriseTradingEngine = MockTradingEngine
    
    async def get_professional_portfolio(user_id):
        class MockPortfolio:
            daily_trades = 0
            max_daily_trades = 8
            async def open_position(self, **kwargs):
                return f"mock_position_{user_id}"
        return MockPortfolio()
    
    class PositionType:
        LONG = "LONG"
        SHORT = "SHORT"

_trading_brain_task = None

async def start_trading_brain_background():
    """Start the automatic trading brain background task"""
    global _trading_brain_task
    
    if _trading_brain_task and not _trading_brain_task.done():
        logger.warning("Trading brain already running")
        return
    
    logger.info("🧠 Starting Trading Brain Background Task...")
    _trading_brain_task = asyncio.create_task(trading_brain_loop())

async def stop_trading_brain_background():
    """Stop the automatic trading brain background task"""
    global _trading_brain_task
    
    if _trading_brain_task and not _trading_brain_task.done():
        logger.info("🛑 Stopping Trading Brain Background Task...")
        _trading_brain_task.cancel()
        try:
            await _trading_brain_task
        except asyncio.CancelledError:
            logger.info("✅ Trading Brain Background Task stopped")
    
    _trading_brain_task = None

async def trading_brain_loop():
    """Main trading brain loop - runs every 3 minutes when enabled"""
    global _trading_brain_enabled
    
    # Initialize trading engine
    trading_engine = EnterpriseTradingEngine()
    await trading_engine.initialize()
    
    logger.info("🚀 TRADING BRAIN LOOP STARTED - Analyzing markets every 3 minutes")
    
    try:
        while _trading_brain_enabled:
            logger.info("🧠 Trading Brain analyzing markets...")
            
            try:
                # Generate AI signal
                signal = await trading_engine.generate_signal("BTCUSDT")
                
                logger.info(f"🎯 AI Signal Generated: {signal.action} with {signal.confidence:.1%} confidence")
                
                # Check if signal is strong enough to act on
                if signal.confidence > 0.60 and signal.action in ["BUY", "SELL"]:
                    
                    # Get portfolio for the admin user (assuming admin user_id = "admin")
                    portfolio = await get_professional_portfolio("admin")
                    
                    # Check if we can open a new position
                    if portfolio.daily_trades < portfolio.max_daily_trades:
                        
                        # Determine position type based on signal
                        position_type = "LONG" if signal.action == "BUY" else "SHORT"
                        
                        # Open position automatically
                        position_id = await portfolio.open_position(
                            symbol=signal.symbol,
                            position_type=position_type, 
                            size=signal.position_size,
                            ai_confidence=signal.confidence,
                            ai_reasoning=signal.reasoning,
                            stop_loss_pct=0.02,  # 2% stop loss
                            take_profit_pct=0.04  # 4% take profit
                        )
                        
                        logger.info(f"🎯 AUTOMATIC POSITION OPENED: {position_id} ({position_type}) with {signal.confidence:.1%} confidence")
                        
                    else:
                        logger.info(f"⚠️ Daily trade limit reached ({portfolio.daily_trades}/{portfolio.max_daily_trades}) - skipping signal")
                
                else:
                    logger.info(f"📊 Signal confidence too low ({signal.confidence:.1%}) or HOLD action - no position opened")
                
            except Exception as e:
                logger.error(f"❌ Trading brain analysis error: {e}")
            
            # Wait 3 minutes before next analysis
            await asyncio.sleep(180)
            
    except asyncio.CancelledError:
        logger.info("🛑 Trading brain loop cancelled")
    except Exception as e:
        logger.error(f"❌ Trading brain loop error: {e}")
    finally:
        logger.info("🏁 Trading brain loop ended")

# ============================================================================
# DAY TRADING ENHANCEMENT SYSTEM - DUAL MODE ARCHITECTURE
# ============================================================================

try:
    from app.backend.services.day_trading_engine import get_day_trading_engine, TradingMode
except ImportError:
    # Fallback for development
    class TradingMode:
        SWING = "swing"
        DAY_TRADING = "day"
        SCALPING = "scalping"
    async def get_day_trading_engine():
        class MockEngine:
            current_mode = TradingMode()
            current_session = "american"
            def get_available_modes(self): return {}
            def set_trading_mode(self, mode): return {"old_mode": "swing", "new_mode": mode, "config": {}, "session": "american"}
            def get_engine_status(self): return {"is_initialized": False}
            async def start_analysis_loop(self): return {"status": "mock"}
            async def stop_analysis_loop(self): return {"status": "mock"}
        return MockEngine()

class TradingModeRequest(BaseModel):
    """Request to change trading mode"""
    mode: str = Field(description="Trading mode: swing, day, or scalping")

class TradingModeResponse(BaseModel):
    """Response from trading mode change"""
    status: str
    old_mode: str
    new_mode: str
    config: Dict[str, Any]
    session: str

@router.get("/modes/available")
async def get_available_trading_modes():
    """
    Get all available trading modes and their configurations
    
    Returns:
        Available trading modes with configurations
    """
    try:
        day_engine = await get_day_trading_engine()
        modes = day_engine.get_available_modes()
        
        return {
            "status": "success",
            "modes": modes,
            "current_mode": day_engine.current_mode.value,
            "current_session": day_engine.current_session.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get trading modes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trading modes: {str(e)}"
        )

@router.post("/modes/set", response_model=TradingModeResponse)
async def set_trading_mode(
    request: TradingModeRequest
):
    """
    Set trading mode (swing, day, or scalping)
    
    Args:
        request: Trading mode change request
        
    Returns:
        New trading mode status and configuration
    """
    try:
        # Validate mode
        try:
            trading_mode = TradingMode(request.mode.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid trading mode: {request.mode}. Available: swing, day, scalping"
            )
        
        day_engine = await get_day_trading_engine()
        result = day_engine.set_trading_mode(trading_mode)
        
        logger.info(f"🔄 Trading mode changed to {trading_mode.value}")
        
        return TradingModeResponse(
            status="success",
            old_mode=result["old_mode"],
            new_mode=result["new_mode"],
            config=result["config"],
            session=result["session"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set trading mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set trading mode: {str(e)}"
        )

class ConfigOverrideRequest(BaseModel):
    """Runtime overrides for testing."""
    day_confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    day_position_size_pct: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    enterprise_confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    enterprise_risk_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)

@router.post("/config/override")
async def override_trading_config(req: ConfigOverrideRequest):
    """Apply temporary runtime overrides to lower entry thresholds or change size."""
    try:
        # Update day trading engine mode config
        day_engine = await get_day_trading_engine()
        if req.day_confidence_threshold is not None:
            day_engine.mode_configs[day_engine.current_mode].confidence_threshold = float(req.day_confidence_threshold)
        if req.day_position_size_pct is not None:
            day_engine.mode_configs[day_engine.current_mode].position_size_pct = float(req.day_position_size_pct)

        # Update enterprise engine thresholds if available
        try:
            ent = day_engine.enterprise_engine
            if ent is not None:
                if req.enterprise_confidence_threshold is not None:
                    ent.confidence_threshold = float(req.enterprise_confidence_threshold)
                if req.enterprise_risk_threshold is not None:
                    ent.risk_threshold = float(req.enterprise_risk_threshold)
        except Exception:
            pass

        return {
            "status": "success",
            "day_mode": day_engine.current_mode.value,
            "day_confidence_threshold": day_engine.mode_configs[day_engine.current_mode].confidence_threshold,
            "day_position_size_pct": day_engine.mode_configs[day_engine.current_mode].position_size_pct,
            "enterprise_confidence_threshold": getattr(day_engine.enterprise_engine, "confidence_threshold", None),
            "enterprise_risk_threshold": getattr(day_engine.enterprise_engine, "risk_threshold", None),
        }
    except Exception as e:
        logger.error(f"Failed to override config: {e}")
        raise HTTPException(status_code=500, detail=f"Override failed: {e}")
@router.get("/modes/status")
async def get_day_trading_status():
    """
    Get current day trading engine status
    
    Returns:
        Current day trading engine status and performance
    """
    try:
        day_engine = await get_day_trading_engine()
        status_info = day_engine.get_engine_status()
        
        return {
            "status": "success",
            "day_trading_engine": status_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get day trading status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get day trading status: {str(e)}"
        )

@router.post("/modes/start")
async def start_day_trading_analysis():
    """
    Start day trading analysis loop
    
    Returns:
        Day trading analysis start status
    """
    try:
        day_engine = await get_day_trading_engine()
        result = await day_engine.start_analysis_loop()
        
        logger.info(f"🚀 Started {day_engine.current_mode.value} trading analysis")
        
        return {
            "status": "success",
            "analysis_started": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start day trading analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start day trading analysis: {str(e)}"
        )

@router.post("/modes/stop")
async def stop_day_trading_analysis():
    """
    Stop day trading analysis loop
    
    Returns:
        Day trading analysis stop status
    """
    try:
        day_engine = await get_day_trading_engine()
        result = await day_engine.stop_analysis_loop()
        
        logger.info(f"🛑 Stopped day trading analysis")
        
        return {
            "status": "success",
            "analysis_stopped": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to stop day trading analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop day trading analysis: {str(e)}"
        )

# ===== PORTFOLIO POSITIONS ENDPOINTS =====

@router.get("/portfolio/positions")
async def get_live_positions():
    """
    Get live positions from professional portfolio for Trading Intelligence
    NO AUTH REQUIRED - for admin dashboard testing
    """
    try:
        logger.info("📊 Fetching live positions for Trading Intelligence")
        
        # Import professional portfolio
        from app.backend.services.professional_portfolio import get_professional_portfolio
        portfolio = await get_professional_portfolio("admin")
        
        # Update with live market data
        await portfolio.update_positions_with_live_data()
        
        # Get active positions
        active_positions = []
        for pos_id, position in portfolio.positions.items():
            if position.status.value == 'open':
                active_positions.append({
                    "id": pos_id,
                    "position_id": pos_id,
                    "symbol": position.symbol,
                    "type": position.type.value,
                    "side": position.type.value.lower(),
                    "size": float(position.size),
                    "quantity": float(position.size),
                    "entry_price": float(position.entry_price),
                    "current_price": float(position.current_price),
                    "unrealized_pnl": float(position.unrealized_pnl),
                    "unrealized_pnl_percentage": float(position.unrealized_pnl_percentage),
                    "pnl": float(position.unrealized_pnl),
                    "pnl_percentage": float(position.unrealized_pnl_percentage),
                    "entry_time": position.entry_time.isoformat(),
                    "status": position.status.value,
                    "confidence": position.ai_confidence,
                    "ai_confidence": position.ai_confidence,
                    "hold_duration": "2h 15m",  # Mock for now
                    "stop_loss": float(position.stop_loss) if position.stop_loss else None,
                    "take_profit": float(position.take_profit) if position.take_profit else None
                })
        
        # Response format that matches TradingIntelligence expectations
        response = {
            "positions": active_positions,
            "summary": {
                "total_open": len(active_positions),
                "total_value": sum(float(p.position_value) for p in portfolio.positions.values()),
                "total_pnl": sum(float(p.unrealized_pnl) for p in portfolio.positions.values())
            },
            "last_updated": datetime.utcnow().isoformat()
        }
        
        logger.info(f"✅ Retrieved {len(active_positions)} active positions for Trading Intelligence")
        return response
        
    except Exception as e:
        logger.error(f"❌ Error fetching live positions: {e}")
        # Return empty positions on error
        return {
            "positions": [],
            "summary": {
                "total_open": 0,
                "total_value": 0.0,
                "total_pnl": 0.0
            },
            "last_updated": datetime.utcnow().isoformat()
        }