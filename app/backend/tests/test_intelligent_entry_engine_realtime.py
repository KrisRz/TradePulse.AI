import asyncio
import os
import time

import pytest

from app.backend.services.intelligent_entry_engine import IntelligentEntryEngine


@pytest.mark.asyncio
async def test_cooldown_enforced_10s():
    engine = IntelligentEntryEngine()
    # Avoid init dependencies; rely on cooldown logic path only
    engine.is_initialized = True

    symbol = "BTCUSDT"
    signal_data = {"action": "BUY", "confidence": 0.8, "signal_type": "primary"}
    user_portfolio = {"available_cash": 10000, "active_positions": [], "max_positions": 5, "daily_trades": 0}

    # First analysis (may or may not complete depending on live services)
    _ = await engine.analyze_entry_opportunity(symbol, signal_data, user_portfolio)

    # Immediate second call should be throttled by cooldown
    result2 = await engine.analyze_entry_opportunity(symbol, signal_data, user_portfolio)

    assert result2.should_enter is False
    assert result2.entry_reason.name in ("POOR_TIMING", "INSUFFICIENT_CONFIDENCE", "WEAK_SIGNAL")
    assert isinstance(result2.layer_analysis, dict)
    assert result2.layer_analysis.get("cooldown_status") == "active"


@pytest.mark.asyncio
async def test_no_fallback_without_historical_context():
    engine = IntelligentEntryEngine()
    # Bypass initialize to avoid external data requirement; enforce strict path
    engine.is_initialized = True
    engine.is_warmed_up = True
    engine.historical_context = None

    symbol = "BTCUSDT-NOFH"
    signal_data = {"action": "BUY", "confidence": 0.8, "signal_type": "primary"}
    user_portfolio = {"available_cash": 10000, "active_positions": [], "max_positions": 5, "daily_trades": 0}

    result = await engine.analyze_entry_opportunity(symbol, signal_data, user_portfolio)

    assert result.should_enter is False
    # Error should surface explicitly due to strict no-fallback; exact message may vary
    assert isinstance(result.layer_analysis, dict)
    err = result.layer_analysis.get("error", "")
    assert isinstance(err, str) and len(err) > 0


