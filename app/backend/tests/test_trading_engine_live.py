"""
Day Trading Engine Test Suite - TradePulse.AI
============================================

Live-data tests for the consolidated engine APIs under `app.backend.services.*`.
Targets:
- DayTradingEngine (mode control, status)
- EnterpriseTradingEngine (signal generation)
- ProfessionalPortfolio (open/close with live price)
"""

import pytest
from decimal import Decimal

from app.backend.services.day_trading_engine import (
    DayTradingEngine,
    TradingMode,
)
from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine
from app.backend.services.professional_portfolio import (
    get_professional_portfolio,
    PositionType,
)
from app.backend.services.live_market_data import get_live_bitcoin_price


@pytest.mark.asyncio
async def test_enterprise_engine_generates_signal_live():
    engine = EnterpriseTradingEngine()
    await engine.initialize()
    signal = await engine.generate_signal("BTCUSDT")

    assert signal.symbol == "BTCUSDT"
    assert signal.price > 0
    assert 0.0 <= signal.confidence <= 1.0
    assert signal.action in {"BUY", "SELL", "HOLD"}


@pytest.mark.asyncio
async def test_day_trading_engine_init_and_status():
    engine = DayTradingEngine()
    await engine.initialize()

    status = engine.get_engine_status()
    assert status["is_initialized"] is True
    assert status["current_mode"] in {m.value for m in engine.mode_configs.keys()}
    assert "mode_config" in status and "performance" in status

    # Switch to day-trading mode
    result = engine.set_trading_mode(TradingMode.DAY_TRADING)
    assert result["new_mode"] == TradingMode.DAY_TRADING.value


@pytest.mark.asyncio
async def test_portfolio_open_and_close_live_price():
    # Ensure we can read live price
    price = await get_live_bitcoin_price()
    assert price > 0

    portfolio = await get_professional_portfolio("pytest_user")
    starting_cash = portfolio.cash_balance

    position_id = await portfolio.open_position(
        symbol="BTCUSDT",
        position_type=PositionType.LONG,
        size=Decimal("0.001"),
        ai_confidence=0.7,
        stop_loss_pct=Decimal("0.01"),
        take_profit_pct=Decimal("0.02"),
    )

    assert position_id in portfolio.positions

    # Close promptly using current live price
    pnl = await portfolio.close_position(position_id, reason="test_close")
    assert position_id not in portfolio.positions
    assert pnl.as_tuple()  # Decimal instance
    assert portfolio.cash_balance > 0


