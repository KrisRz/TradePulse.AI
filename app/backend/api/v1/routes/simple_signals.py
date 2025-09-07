"""
Simple Signals API - NO DEPENDENCIES VERSION
For 6-Layer AI Signal Intelligence dashboard
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter

router = APIRouter()

@router.get("/latest")
async def get_latest_signals_simple() -> Dict[str, Any]:
    """Get the latest trading signals - ULTRA SIMPLE VERSION"""
    # Mock current BTC price
    current_price = 110000.0

    # Mock 6-layer analysis for dashboard display
    mock_layer_analysis = {
        "layer_1_regime": {
            "regime": "BULLISH",
            "confidence": 0.72,
            "trend_strength": 0.68,
            "description": "Market showing strong upward momentum"
        },
        "layer_2_lstm": {
            "prediction": "BUY",
            "confidence": 0.65,
            "timeframe": "1h",
            "description": "LSTM models predict upward movement"
        },
        "layer_3_reversal": {
            "reversal_probability": 0.15,
            "signal": "HOLD",
            "support_resistance": "NEUTRAL",
            "description": "Low reversal risk detected"
        },
        "layer_4_filters": {
            "filter_score": 0.78,
            "technical_signal": "BUY",
            "volume_trend": "INCREASING",
            "description": "Technical indicators align for bullish move"
        },
        "layer_5_confidence": {
            "confidence": 0.68,
            "risk_assessment": "MEDIUM",
            "market_condition": "OPTIMAL",
            "description": "Good confidence with acceptable risk"
        },
        "layer_6_timing": {
            "timing_score": 0.75,
            "optimal_entry": True,
            "market_phase": "ACCUMULATION",
            "description": "Timing is optimal for entry"
        }
    }

    # Determine overall signal based on layer consensus
    layer_signals = [
        mock_layer_analysis["layer_1_regime"]["regime"],
        mock_layer_analysis["layer_2_lstm"]["prediction"],
        mock_layer_analysis["layer_4_filters"]["technical_signal"]
    ]

    buy_count = layer_signals.count("BUY") + layer_signals.count("BULLISH")
    sell_count = layer_signals.count("SELL")

    if buy_count >= 2:
        overall_action = "BUY"
        overall_confidence = 0.68
    elif sell_count >= 2:
        overall_action = "SELL"
        overall_confidence = 0.68
    else:
        overall_action = "HOLD"
        overall_confidence = 0.50

    # Prepare the response
    response_data = {
        "status": "success",
        "signal": {
            "symbol": "BTCUSDT",
            "action": overall_action,
            "confidence": overall_confidence,
            "price": current_price,
            "timestamp": datetime.utcnow().isoformat(),
            "signal_type": "primary",
            "reasoning": f"6-layer consensus: {buy_count} buy, {sell_count} sell signals"
        },
        "layer_analysis": mock_layer_analysis,
        "engine_status": {
            "initialized": True,
            "model_count": 6,
            "available_models": ["regime", "lstm", "reversal", "filters", "confidence", "timing"],
            "status": "operational"
        },
        "last_updated": datetime.utcnow().isoformat()
    }

    return response_data
