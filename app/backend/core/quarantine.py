"""Quarantine gate for the condemned enterprise engine stack.

Why this exists
---------------
The 2026-07-17 deep audit (docs/ANALIZA_6_WARSTW_2026-07-17.md, decision D11)
condemned the 6-layer enterprise stack: circular labels, leaky splits, dead
safety mechanisms, and a final confidence that never comes from the layers at
all. The verdict was explicit — do NOT retrain, do NOT repair layer-by-layer.
The 2026-07-21 E2E audit then found the quarantine had never been executed:
importing two routers instantiated the engine twice before any request, and a
local monolith start booted the entire condemned stack, continuous-learning
retraining loop included.

The production bot is safe purely by architecture (the Lambda ships only
``paper_trading`` + ``backtesting`` and never imports the monolith). This gate
makes the rest of the codebase match that reality: condemned classes refuse to
construct unless explicitly enabled.

Mechanism
---------
One choke point at the CLASS level. The condemned engines instantiate each
other lazily deep inside their methods (day -> enterprise/entry/exit,
session -> enterprise, exit -> enterprise, entry -> learning), so gating only
the app-factory boot would leave every one of those side doors open. A guard
in each condemned ``__init__`` closes all of them at once, loudly.

Enabling (research only)
------------------------
    ENTERPRISE_ENGINES=on python -m app.backend.scripts.validate_ai_models

The flag exists for offline research against the condemned models, not for
serving. Nothing on the live path reads it.
"""

from __future__ import annotations

import os

ENV_FLAG = "ENTERPRISE_ENGINES"

#: Classes guarded by this gate — kept here so tests and docs have one list.
QUARANTINED = (
    "EnterpriseTradingEngine",
    "IntelligentEntryEngine",
    "IntelligentExitEngine",
    "ContinuousLearningEngine",
    "BrainController",
)


class EnterpriseQuarantined(RuntimeError):
    """Raised when a condemned engine is constructed without the opt-in flag."""


def enterprise_enabled() -> bool:
    return os.environ.get(ENV_FLAG, "off").strip().lower() in ("1", "true", "on", "yes")


def quarantine_detail(name: str) -> str:
    return (
        f"{name} is quarantined: the 6-layer enterprise stack was condemned by "
        f"the 2026-07-17 audit (docs/ANALIZA_6_WARSTW_2026-07-17.md, D11 — do "
        f"not retrain, do not repair). Set {ENV_FLAG}=on only for offline "
        f"research against the condemned models."
    )


def assert_enterprise_enabled(name: str) -> None:
    """Constructor guard for condemned classes — first line of ``__init__``."""
    if not enterprise_enabled():
        raise EnterpriseQuarantined(quarantine_detail(name))
