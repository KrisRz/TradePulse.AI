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

    # Duplicate suppression (configurable at runtime) - DAY TRADING OPTIMIZED
    dup_active_window_sec: int = 5            # 5 seconds only for active positions  
    dup_active_price_delta_pct: float = 0.001 # 0.1% price similarity (very strict)
    dup_closed_window_sec: int = 30           # 30 seconds for closed positions (was 10s)
    dup_closed_price_delta_pct: float = 0.005 # 0.5% price similarity (was 0.1% - too strict)

    # Playbook override controls
    playbook_override_enabled: bool = True
    playbook_override_playbooks: List[str] = ["breakout"]
    playbook_override_min_consensus: float = 0.55
    playbook_override_min_timing: float = 0.70
    playbook_override_size_multiplier: float = 0.60
    playbook_override_max_spread_bps: float = 3.0
    playbook_override_max_slippage_bps: float = 400.0  # DAY TRADING: Volatility proxy needs higher tolerance (was 100)
    playbook_override_block_if_guard: Set[str] = {"breaker", "volatility", "cooldown", "duplicate"}
    require_macd_validator_pass: bool = True


__all__ = ["RuntimeConfig"]


