"""The condemned enterprise stack must refuse to boot — quarantine gate tests.

The 2026-07-17 audit condemned the 6-layer stack (D11: retrain nothing, repair
nothing); the 2026-07-21 E2E audit found it still booted everywhere — router
imports instantiated the engine twice before any request, and a local monolith
start ran the whole stack including the continuous-learning retraining loop.

These tests pin the fix at its choke point: the constructors. Every side door
(engines instantiating each other lazily inside methods, dependency helpers,
router imports) funnels through ``__init__``, so guarding there closes all of
them — and these tests fail loudly if anyone ever removes a guard.
"""

from __future__ import annotations

import pytest

from app.backend.core.quarantine import (
    ENV_FLAG,
    QUARANTINED,
    EnterpriseQuarantined,
    enterprise_enabled,
    quarantine_detail,
)


# ------------------------------------------------------------------ the flag --
def test_quarantine_is_the_default(monkeypatch):
    monkeypatch.delenv(ENV_FLAG, raising=False)
    assert enterprise_enabled() is False


@pytest.mark.parametrize("value", ["on", "1", "true", "yes", "ON", " True "])
def test_explicit_opt_in_values(monkeypatch, value):
    monkeypatch.setenv(ENV_FLAG, value)
    assert enterprise_enabled() is True


@pytest.mark.parametrize("value", ["off", "0", "false", "no", "", "banana"])
def test_everything_else_stays_quarantined(monkeypatch, value):
    monkeypatch.setenv(ENV_FLAG, value)
    assert enterprise_enabled() is False


def test_the_detail_names_the_verdict():
    detail = quarantine_detail("EnterpriseTradingEngine")
    assert "D11" in detail and "ANALIZA_6_WARSTW" in detail


# ------------------------------------------------- condemned constructors ----
def _condemned_classes():
    from app.backend.brain.brain_controller import BrainController
    from app.backend.services.continuous_learning_engine import ContinuousLearningEngine
    from app.backend.services.enterprise_trading_engine import EnterpriseTradingEngine
    from app.backend.services.intelligent_entry_engine import IntelligentEntryEngine
    from app.backend.services.intelligent_exit_engine import IntelligentExitEngine

    return [EnterpriseTradingEngine, IntelligentEntryEngine, IntelligentExitEngine,
            ContinuousLearningEngine, BrainController]


def test_every_condemned_class_refuses_to_construct(monkeypatch):
    monkeypatch.delenv(ENV_FLAG, raising=False)
    for cls in _condemned_classes():
        with pytest.raises(EnterpriseQuarantined):
            cls()


def test_the_guard_list_matches_the_guarded_classes():
    """QUARANTINED is the documented contract — keep it in sync with reality."""
    assert {c.__name__ for c in _condemned_classes()} == set(QUARANTINED)


# -------------------------------------------------------------- entry points --
def test_dependency_helper_returns_503_not_an_engine(monkeypatch):
    from fastapi import HTTPException

    from app.backend.utils.dependencies import get_enterprise_trading_engine

    monkeypatch.delenv(ENV_FLAG, raising=False)
    with pytest.raises(HTTPException) as err:
        get_enterprise_trading_engine()
    assert err.value.status_code == 503


def test_enterprise_router_import_does_not_instantiate_the_engine(monkeypatch):
    """Importing the router used to boot the 6-layer stack before any request."""
    monkeypatch.delenv(ENV_FLAG, raising=False)
    from app.backend.api.v1.routes import enterprise as mod

    assert mod._enterprise_trading_engine is None

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as err:
        mod._engine()
    assert err.value.status_code == 503
    assert mod._enterprise_trading_engine is None   # still not constructed


def test_admin_router_no_longer_carries_a_module_level_engine():
    from app.backend.api.v1.routes import admin as mod

    assert not hasattr(mod, "trading_engine")
