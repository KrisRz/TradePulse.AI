"""
Latest-signal API for the 6-Layer AI Signal Intelligence dashboard.

Serves the REAL enterprise engine's latest signal (the previous version
fabricated everything, including a $110,000 BTC price). A short in-module
cache keeps dashboard polling from re-running the full 6-layer analysis
on every request.
"""

import time
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter

router = APIRouter()

_CACHE_TTL_SECONDS = 30
_cache: Dict[str, Any] = {"at": 0.0, "data": None}


def _to_native(obj: Any) -> Any:
    """Recursively convert numpy scalars/arrays to JSON-safe Python types."""
    import numpy as np

    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_native(v) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def _unavailable(reason: str) -> Dict[str, Any]:
    """Honest degraded response — no fabricated numbers."""
    return {
        "status": "unavailable",
        "reason": reason,
        "signal": None,
        "layer_analysis": None,
        "engine_status": {"initialized": False, "status": "unavailable"},
        "last_updated": datetime.utcnow().isoformat(),
    }


@router.get("/latest")
async def get_latest_signals() -> Dict[str, Any]:
    """Latest real 6-layer signal (cached for a short interval)."""
    now = time.monotonic()
    if _cache["data"] is not None and now - _cache["at"] < _CACHE_TTL_SECONDS:
        return _cache["data"]

    try:
        from app.backend.core.container import get_container

        engine = get_container().get("enterprise_trading_engine")
    except Exception as e:
        return _unavailable(f"engine lookup failed: {e}")

    if engine is None or not getattr(engine, "is_initialized", False):
        return _unavailable("enterprise engine not initialized")

    try:
        signal = await engine.generate_signal("BTCUSDT")
    except Exception as e:
        return _unavailable(f"signal generation failed: {e}")

    if signal is None:
        return _unavailable("engine returned no signal (safety gate or missing data)")

    models = getattr(engine, "models", {}) or {}
    response: Dict[str, Any] = {
        "status": "success",
        "signal": {
            "symbol": signal.symbol,
            "action": signal.action,
            "confidence": float(signal.confidence),
            "price": float(signal.price),
            "timestamp": signal.timestamp.isoformat() if hasattr(signal.timestamp, "isoformat") else str(signal.timestamp),
            "signal_type": signal.signal_type,
            "reasoning": signal.reasoning,
        },
        "layer_analysis": _to_native(signal.layer_analysis),
        "engine_status": {
            "initialized": True,
            "model_count": len(models),
            "available_models": sorted(models.keys()),
            "status": "operational",
        },
        "last_updated": datetime.utcnow().isoformat(),
    }
    _cache["data"] = response
    _cache["at"] = now
    return response
