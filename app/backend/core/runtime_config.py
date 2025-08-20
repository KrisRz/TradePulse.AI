"""
In-process runtime configuration store.

For single-node/local use this in-memory store. In production, back with Redis/DynamoDB
and keep a short-TTL cache here.
"""

import asyncio
from typing import Optional
from pathlib import Path
import json

from app.backend.schemas.runtime_config import RuntimeConfig
from app.backend.core.config import get_settings


class RuntimeConfigStore:
    """Thread-safe async runtime-config store.

    Defaults are derived from environment variables at startup but can be
    changed at runtime via admin API without restart.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._store_path = Path("logs/runtime_config.json")
        s = get_settings()
        default_cfg = RuntimeConfig(
            strict_live_stream=bool(s.STRICT_LIVE_STREAM),
            engine_enabled=True,
        )
        # Load persisted runtime-config if present to survive reloads
        if self._store_path.exists():
            try:
                data = json.loads(self._store_path.read_text())
                self._cfg: RuntimeConfig = RuntimeConfig(**data)
            except Exception:
                self._cfg = default_cfg
        else:
            self._cfg = default_cfg

    async def get(self) -> RuntimeConfig:
        async with self._lock:
            return self._cfg

    async def set(self, cfg: RuntimeConfig) -> RuntimeConfig:
        async with self._lock:
            self._cfg = cfg
            try:
                self._store_path.parent.mkdir(parents=True, exist_ok=True)
                self._store_path.write_text(self._cfg.model_dump_json())
            except Exception:
                # Non-fatal if we can't persist
                pass
            return self._cfg


runtime_config_store = RuntimeConfigStore()

__all__ = ["runtime_config_store", "RuntimeConfigStore"]


