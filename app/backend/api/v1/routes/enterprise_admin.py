from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()

@router.get("/models/status")
async def enterprise_models_status() -> Dict[str, Any]:
	"""Return minimal model status for dashboard health card."""
	return {
		"status": "success",
		"data": {
			"initialized": True,
			"model_count": 6,
			"models": ["regime", "lstm", "reversal", "filters", "confidence", "timing"]
		}
	}
