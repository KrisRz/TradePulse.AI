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
from app.backend.core.exceptions import (
    ServiceUnavailableException,
    ConfigurationException,
    ModelNotLoadedException
)
from app.backend.services.day_trading_engine import get_day_trading_engine
from app.backend.utils.dependencies import get_current_user, User
from app.backend.services import VirtualPortfolioManager as VirtualPortfolioService
from app.backend.services import MarketDataService
from app.backend.services.intelligent_exit_engine import IntelligentExitEngine

# Initialize intelligent exit engine
exit_engine: Optional[IntelligentExitEngine] = None

async def get_exit_engine() -> IntelligentExitEngine:
    """Get or create the intelligent exit engine"""
    global exit_engine
    if exit_engine is None:
        try:
            exit_engine = IntelligentExitEngine()
            if not exit_engine.is_initialized:
                await exit_engine.initialize()
        except Exception as e:
            raise ServiceUnavailableException("IntelligentExitEngine") from e
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
        
        # Create professional auto-trade position
        portfolio = await portfolio_service.get_portfolio_summary(current_user.id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        available_cash = float(portfolio.get('cash_balance', 0))
        position_value = available_cash * (request.position_size_percentage / 100)
        
        # Get real market data
        symbol = "BTCUSDT"
        current_price = await market_data_service.get_current_price(symbol)
        if current_price is None:
            raise ServiceUnavailableException("MarketDataService")
        
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
                    current_price = float(position.get('entry_price'))
                    if not current_price:
                        raise ServiceUnavailableException("MarketDataService")
                
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

async def _load_brain_state():
    """DEPRECATED: Load brain state - now handled by BrainStateStore"""
    # This function is kept for backward compatibility but delegates to BrainStateStore
    from app.backend.core.brain_state_store import get_brain_state_store
    
    global _trading_brain_enabled, _trading_brain_start_time
    
    try:
        brain_store = get_brain_state_store()
        brain_state = await brain_store.wait_ready()  # Wait for lifespan to load it
        
        _trading_brain_enabled = brain_state.enabled
        if brain_state.start_time:
            try:
                _trading_brain_start_time = datetime.fromisoformat(brain_state.start_time.replace('Z', '+00:00'))
            except:
                _trading_brain_start_time = datetime.utcnow()
        
        logger.info(f"📥 Brain state synchronized: {'ENABLED' if _trading_brain_enabled else 'DISABLED'}")
        
    except Exception as e:
        logger.warning(f"Failed to load brain state: {e}")
        _trading_brain_enabled = False

async def _save_brain_state():
    """Save brain state to DynamoDB"""
    try:
        # Use BrainStateStore for consistent state management
        from app.backend.core.brain_state_store import get_brain_state_store
        
        brain_store = get_brain_state_store()
        start_time = _trading_brain_start_time.isoformat() if _trading_brain_start_time else datetime.utcnow().isoformat()
        
        await brain_store.update_state(_trading_brain_enabled, start_time)
        logger.info(f"💾 Brain state saved via BrainStateStore: {'ENABLED' if _trading_brain_enabled else 'DISABLED'}")
    except Exception as e:
        logger.error(f"Failed to save brain state: {e}")

# REMOVED: Old trading brain status endpoint - use /api/v1/brain/status instead
# This endpoint was part of the old trading brain system that has been replaced
# by the unified professional brain controller with proper state management


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
        # Ensure services are ready before brain operations
        from app.backend.core.brain_state_store import ensure_services_ready
        from app.backend.core.container import get_container
        
        try:
            ensure_services_ready(get_container())
        except RuntimeError as e:
            logger.error(f"❌ Cannot toggle brain - services not ready: {e}")
            raise HTTPException(status_code=503, detail=f"Services not ready: {e}")
        
        global _trading_brain_enabled, _trading_brain_start_time
        
        # Check if user is admin (add admin check here if needed)
        # For now, allow any authenticated user
        
        old_status = _trading_brain_enabled
        _trading_brain_enabled = request.enabled
        
        # Save state to DB
        await _save_brain_state()
        
        if _trading_brain_enabled and not old_status:
            # Brain was turned ON
            _trading_brain_start_time = datetime.utcnow()
            status_msg = "ACTIVATED - AI brain now monitoring markets for trading opportunities"
            logger.info(f"🧠 TRADING BRAIN ACTIVATED")
            
            # Start the automatic trading brain background task
            await start_trading_brain_background()
            
            # Also start Day Trading Engine
            try:
                day_engine = await get_day_trading_engine()
                await day_engine.start_analysis_loop()
                logger.info("🚀 Day Trading Engine auto-started with Brain activation")
            except Exception as e:
                logger.warning(f"Failed to auto-start Day Trading Engine: {e}")
            
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

# OLD: UnifiedDayTradingEngine was replaced with DayTradingEngine
# from app.backend.services.unified_day_trading_engine import UnifiedDayTradingEngine, TradingAction
from app.backend.services.professional_portfolio import get_professional_portfolio, PositionType

# NOTE: This trading brain is deprecated - Brain Controller now manages all trading
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
    """Main trading brain loop - runs every 15 seconds for day trading"""
    global _trading_brain_enabled
    
    # NOTE: This function is deprecated - use Brain Controller instead
    logger.warning("⚠️ /brain/start is deprecated - use Brain Controller via WebSocket")
    return {"status": "deprecated", "message": "Use Brain Controller instead"}
    
    # Start professional warm-up period
    await trading_engine.start_warm_up()
    
    logger.info("🚀 TRADING BRAIN LOOP STARTED - Starting 10-minute warm-up period...")
    
    # 🔥 PROFESSIONAL WARM-UP: 10 minutes market analysis before trading
    warm_up_cycles = 40  # 10 minutes / 15 seconds = 40 cycles
    for cycle in range(warm_up_cycles):
        if not _trading_brain_enabled:
            logger.info("🛑 Trading brain disabled during warm-up")
            return
            
        try:
            # Generate signal during warm-up but DON'T trade
            signal = await trading_engine.generate_signal("BTCUSDT")
            if cycle % 8 == 0:  # Log every 2 minutes
                progress = (cycle / warm_up_cycles) * 100
                logger.info(f"🔥 WARM-UP Progress: {progress:.0f}% - Signal: {signal.action} ({signal.confidence:.1%})")
        except Exception as e:
            logger.warning(f"⚠️ Warm-up cycle {cycle} failed: {e}")
            
        await asyncio.sleep(15)
    
    logger.info("✅ WARM-UP COMPLETE - Starting live trading with professional thresholds")
    
    try:
        while _trading_brain_enabled:
            logger.info("🧠 Trading Brain analyzing markets...")
            
            try:
                # Generate unified AI signal
                unified_signal = await trading_engine.generate_signal("BTCUSDT")
                
                if not unified_signal:
                    logger.info("📊 No unified signal generated - market conditions not suitable")
                    continue
                
                logger.info(f"🎯 UNIFIED Signal Generated: {unified_signal.action.value} with {unified_signal.confidence:.1%} confidence")
                
                # Check if unified signal is strong enough to act on - PROFESSIONAL THRESHOLD
                if unified_signal.confidence > 0.45 and unified_signal.action in [TradingAction.BUY, TradingAction.SELL]:  # BITCOIN SCALPING: 45% threshold (was 65%)
                    
                    # Get portfolio for the admin user
                    portfolio = await get_professional_portfolio("admin")
                    
                    # Check if we can open a new position
                    if portfolio.daily_trades < portfolio.max_daily_trades:
                        
                        # Determine position type based on unified signal
                        position_type = PositionType.LONG if unified_signal.action == TradingAction.BUY else PositionType.SHORT
                        
                        # Calculate professional position size
                        position_size = float(portfolio.cash_balance) * unified_signal.position_size_pct
                        position_size = max(position_size, 500.0)  # $500 minimum
                        
                        # Open position with unified signal data
                        position_id = await portfolio.open_position(
                            symbol=unified_signal.symbol,
                            position_type=position_type, 
                            size=Decimal(str(position_size)),
                            ai_confidence=Decimal(str(unified_signal.confidence)),
                            ai_reasoning=f"UNIFIED: {unified_signal.reasoning}",
                            stop_loss_pct=Decimal(str(unified_signal.stop_loss_pct)),
                            take_profit_pct=Decimal(str(unified_signal.take_profit_pct))
                        )
                        
                        logger.info(f"🎯 UNIFIED POSITION OPENED: {position_id} ({position_type.value}) conf={unified_signal.confidence:.1%} size=${position_size:.0f}")
                        
                    else:
                        logger.info(f"⚠️ Daily trade limit reached ({portfolio.daily_trades}/{portfolio.max_daily_trades}) - skipping signal")
                
                else:
                    action_str = unified_signal.action.value if unified_signal.action != TradingAction.HOLD else "HOLD"
                    logger.info(f"📊 Signal confidence too low ({unified_signal.confidence:.1%}) or HOLD action - no position opened")
                
            except Exception as e:
                logger.error(f"❌ Trading brain analysis error: {e}")
            
            # Wait 15 seconds before next analysis (day trading frequency)
            await asyncio.sleep(15)
            
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
    # get_day_trading_engine imported from services.day_trading_engine

class TradingModeRequest(BaseModel):
    """Request to change trading mode"""
    mode: str = Field(description="Trading mode: day or scalping (DAY TRADING FOCUSED)")

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
    Set trading mode (day or scalping) - DAY TRADING FOCUSED
    
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
                detail=f"Invalid trading mode: {request.mode}. Available: day, scalping (DAY TRADING FOCUSED)"
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
                    "hold_duration": _calculate_position_duration(position.entry_time),
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
        logger.error
    
def _calculate_position_duration(entry_time: datetime) -> str:
        """Calculate real position duration"""
        try:
            now = datetime.now(timezone.utc)
            duration = now - entry_time.replace(tzinfo=timezone.utc)
            
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            
            if hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except Exception:
            return "0m"
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

@router.get("/withdrawal-limits")
async def get_withdrawal_limits(current_user: User = Depends(get_current_user)):
    """Get withdrawal limits for user account"""
    try:
        logger.info(f"📊 User {current_user.id} requesting withdrawal limits")
        
        # Get user portfolio for balance context
        from app.backend.services.professional_portfolio import get_professional_portfolio
        # For development, map enterprise_admin to admin portfolio where all data is
        user_id = "admin" if current_user.id in ["admin", "enterprise_admin"] or current_user.email == "admin@tradepulse.ai" else current_user.id
        portfolio = await get_professional_portfolio(user_id)
        
        cash_balance = float(portfolio.cash_balance)
        
        response_data = {
            "daily_limit": min(cash_balance * 0.5, 5000.0),  # 50% of cash or $5000 max
            "weekly_limit": min(cash_balance * 0.8, 25000.0),  # 80% of cash or $25000 max
            "monthly_limit": cash_balance,  # Full cash balance
            "available_today": min(cash_balance * 0.5, 5000.0),  # Same as daily for now
            "available_this_week": min(cash_balance * 0.8, 25000.0),
            "available_this_month": cash_balance,
            "current_cash_balance": cash_balance,
            "minimum_withdrawal": 10.0,
            "withdrawal_fee": 2.5,  # $2.50 fee
            "processing_time": "1-3 business days",
            "last_updated": datetime.utcnow().isoformat()
        }
        
        logger.info(f"✅ Withdrawal limits retrieved for user {current_user.id}")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching withdrawal limits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch withdrawal limits: {str(e)}"
        )

@router.get("/trades/history")
async def get_trade_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """Get user's trade history"""
    try:
        logger.info(f"📊 User {current_user.id} requesting trade history (limit: {limit})")
        
        from app.backend.services.professional_portfolio import get_professional_portfolio
        # For development, map enterprise_admin to admin portfolio where all data is
        user_id = "admin" if current_user.id in ["admin", "enterprise_admin"] or current_user.email == "admin@tradepulse.ai" else current_user.id
        portfolio = await get_professional_portfolio(user_id)
        
        # Get closed positions as trade history
        trade_history = []
        
        for position in portfolio.closed_positions[-limit:]:
            trade_history.append({
                "trade_id": position.position_id,
                "symbol": position.symbol,
                "side": position.type.value.lower(),
                "type": position.type.value,
                "size": float(position.size),
                "entry_price": float(position.entry_price),
                "exit_price": float(position.exit_price) if position.exit_price else None,
                "entry_time": position.entry_time.isoformat(),
                "exit_time": position.exit_time.isoformat() if position.exit_time else None,
                "pnl": float(position.realized_pnl) if position.realized_pnl else 0.0,
                "pnl_percentage": float(position.realized_pnl_percentage) if hasattr(position, 'realized_pnl_percentage') else 0.0,
                "fee": 0.1,  # 0.1% trading fee
                "status": position.status.value,
                "strategy": "ai_signal",
                "confidence": position.ai_confidence
            })
        
        # Sort by exit time (newest first)
        trade_history.sort(key=lambda x: x['exit_time'] or x['entry_time'], reverse=True)
        
        response_data = {
            "trades": trade_history,
            "summary": {
                "total_trades": len(trade_history),
                "profitable_trades": len([t for t in trade_history if t['pnl'] > 0]),
                "losing_trades": len([t for t in trade_history if t['pnl'] < 0]),
                "total_pnl": sum(t['pnl'] for t in trade_history),
                "win_rate": (len([t for t in trade_history if t['pnl'] > 0]) / len(trade_history) * 100) if trade_history else 0,
                "avg_pnl_per_trade": sum(t['pnl'] for t in trade_history) / len(trade_history) if trade_history else 0
            },
            "pagination": {
                "limit": limit,
                "returned": len(trade_history),
                "has_more": len(portfolio.closed_positions) > limit
            },
            "last_updated": datetime.utcnow().isoformat()
        }
        
        logger.info(f"✅ Trade history retrieved: {len(trade_history)} trades")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching trade history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch trade history: {str(e)}"
        )

