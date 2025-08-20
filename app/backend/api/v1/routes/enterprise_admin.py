from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from app.backend.utils.dependencies import require_admin_role, User
from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine
from app.backend.services.live_market_data import get_live_market_data_service

router = APIRouter()

@router.post("/models/reload")
async def reload_enterprise_models(_: User = Depends(require_admin_role)) -> Dict[str, Any]:
	"""Hot-reload enterprise AI models and metadata."""
	try:
		engine = EnterpriseTradingEngine()
		await engine.initialize()
		info = await engine.reload_models()
		return {"status": "success", "data": info}
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Model reload failed: {e}")


@router.get("/models/status")
async def enterprise_models_status(_: User = Depends(require_admin_role)) -> Dict[str, Any]:
	"""Return minimal model status for dashboard health card."""
	try:
		engine = EnterpriseTradingEngine()
		await engine.initialize()
		model_keys = sorted(list(engine.models.keys()))
		return {
			"status": "success",
			"data": {
				"initialized": engine.is_initialized,
				"model_count": len(model_keys),
				"models": model_keys
			}
		}
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Model status failed: {e}")


@router.get("/engine/health")
async def enterprise_engine_health(_: User = Depends(require_admin_role)) -> Dict[str, Any]:
	"""Lightweight engine health: engine init + WS status."""
	try:
		engine = EnterpriseTradingEngine()
		await engine.initialize()
		service = await get_live_market_data_service()
		market_ok = bool(service and service.is_running and service.get_market_summary())
		return {
			"status": "healthy" if (engine.is_initialized and market_ok) else "degraded",
			"engine_initialized": engine.is_initialized,
			"websocket_running": bool(service and service.is_running)
		}
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Engine health check failed: {e}")

@router.get("/engine/last-signal")
async def enterprise_engine_last_signal(_: User = Depends(require_admin_role)) -> Dict[str, Any]:
	"""Return a live snapshot of the latest signal layer outputs and confidence."""
	try:
		engine = EnterpriseTradingEngine()
		await engine.initialize()
		signal = await engine.generate_signal("BTCUSDT")
		la = getattr(signal, 'layer_analysis', {}) or {}
		# Convert numpy types to native for JSON
		def _to_native(obj):
			import numpy as _np
			if isinstance(obj, (float, int, str, bool)) or obj is None:
				return obj
			if isinstance(obj, (_np.floating, _np.integer)):
				return float(obj)
			if isinstance(obj, dict):
				return {k: _to_native(v) for k, v in obj.items()}
			if isinstance(obj, (list, tuple)):
				return [_to_native(v) for v in obj]
			return obj

		return {
			"symbol": signal.symbol,
			"action": signal.action,
			"confidence": float(signal.confidence),
			"price": float(signal.price),
			"layers": _to_native(la),
			"timestamp": signal.timestamp.isoformat(),
		}
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to get last signal: {e}")
