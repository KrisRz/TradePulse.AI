"""
Admin Runtime Config endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from app.backend.schemas.runtime_config import RuntimeConfig
from app.backend.core.runtime_config import runtime_config_store
from app.backend.utils.dependencies import require_admin_role


router = APIRouter(prefix="/admin/runtime-config", tags=["admin-runtime"])


@router.get("", response_model=RuntimeConfig)
async def get_runtime_config(_: Any = Depends(require_admin_role)) -> RuntimeConfig:
    return await runtime_config_store.get()


@router.put("", response_model=RuntimeConfig)
async def update_runtime_config(cfg: RuntimeConfig, _: Any = Depends(require_admin_role)) -> RuntimeConfig:
    return await runtime_config_store.set(cfg)


