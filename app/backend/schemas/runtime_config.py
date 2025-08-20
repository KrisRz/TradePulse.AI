"""
Runtime configuration schema for admin-controlled toggles.
"""

from pydantic import BaseModel


class RuntimeConfig(BaseModel):
    """Runtime-config flags that can be changed without process restarts.

    Attributes:
        strict_live_stream: When true, disallow REST fallbacks and require WS data.
        engine_enabled: When false, engines should skip live trading decisions.
    """

    strict_live_stream: bool
    engine_enabled: bool


__all__ = ["RuntimeConfig"]


