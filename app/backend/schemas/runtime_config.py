"""
Runtime configuration schema for admin-controlled toggles.
"""

from pydantic import BaseModel
from typing import List, Set


class RuntimeConfig(BaseModel):
    """Runtime-config flags that can be changed without process restarts.

    Attributes:
        strict_live_stream: When true, disallow REST fallbacks and require WS data.
        engine_enabled: When false, engines should skip live trading decisions.
    """

    strict_live_stream: bool
    engine_enabled: bool
    real_trading_enabled: bool = False

    # Duplicate suppression (configurable at runtime)
    dup_active_window_sec: int = 30          # active position duplicate window
    dup_active_price_delta_pct: float = 0.003 # 0.3% price similarity threshold
    dup_closed_window_sec: int = 600          # recently closed position window
    dup_closed_price_delta_pct: float = 0.008 # 0.8% price similarity threshold

    # Playbook override controls
    playbook_override_enabled: bool = True
    playbook_override_playbooks: List[str] = ["breakout"]
    playbook_override_min_consensus: float = 0.55
    playbook_override_min_timing: float = 0.70
    playbook_override_size_multiplier: float = 0.60
    playbook_override_max_spread_bps: float = 3.0
    playbook_override_max_slippage_bps: float = 6.0
    playbook_override_block_if_guard: Set[str] = {"breaker", "volatility", "cooldown", "duplicate"}
    require_macd_validator_pass: bool = True


__all__ = ["RuntimeConfig"]


