import asyncio
import types
import numpy as np
import pytest


def test_bb_position_basic_bounds():
    from app.backend.services.live_market_data import _calculate_bollinger_position

    prices = np.linspace(100.0, 110.0, 40)
    close_mid = 105.0
    close_upper = 110.0
    close_lower = 100.0

    bb_mid = _calculate_bollinger_position(prices, close_mid)
    bb_up = _calculate_bollinger_position(prices, close_upper)
    bb_lo = _calculate_bollinger_position(prices, close_lower)

    assert 0.0 <= bb_mid <= 1.0
    assert 0.0 <= bb_up <= 1.0
    assert 0.0 <= bb_lo <= 1.0
    assert bb_up > bb_mid > bb_lo


def test_macd_self_heal_scale():
    from app.backend.services.live_market_data import _calculate_macd

    # Large-scale prices to force raw MACD >> 1
    prices = np.linspace(100000.0, 100300.0, 200)
    macd_norm, macd_sig = _calculate_macd(prices)
    # Normalized MACD should be small relative to price scale
    assert abs(macd_norm) < 1.0
    assert np.isfinite(macd_norm)
    assert np.isfinite(macd_sig)


@pytest.mark.asyncio
async def test_regime_override_on_high_vol_ratio(monkeypatch):
    from app.backend.services.intelligent_exit_engine import IntelligentExitEngine

    # Stub emergency system: not halted
    async def _stub_get_emergency_system():
        class ES:
            async def is_trading_halted(self):
                return False
        return ES()

    import app.backend.services.intelligent_exit_engine as mod
    monkeypatch.setattr(mod, 'get_emergency_system', _stub_get_emergency_system)

    engine = IntelligentExitEngine()
    market_data = {"volume_ratio": 26.0, "volatility": 0.005, "trend_strength": 0.1}
    res = await engine._analyze_market_regime(market_data, current_price=100.0)
    assert res["regime"] == "high_volatility"


def test_pnl_percentage_long_short():
    from decimal import Decimal
    from app.backend.utils.money import calculate_pnl_percentage

    entry = Decimal("100")
    price_up = Decimal("101")
    price_down = Decimal("99")

    pnl_long_up = calculate_pnl_percentage(entry, price_up, "LONG")
    pnl_long_down = calculate_pnl_percentage(entry, price_down, "LONG")
    pnl_short_up = calculate_pnl_percentage(entry, price_up, "SHORT")
    pnl_short_down = calculate_pnl_percentage(entry, price_down, "SHORT")

    assert pnl_long_up > 0 and pnl_long_down < 0
    assert pnl_short_down > 0 and pnl_short_up < 0


