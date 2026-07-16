"""
Startup regression tests (M0/A7).

Guards the M0/A2 invariants:
- the full FastAPI app is importable WITHOUT a live database (import-time
  side effects were removed; a Lambda cold start / test run must not need
  DynamoDB),
- exactly two startup handlers exist: the application factory's phased
  init and the singleton lease handler — a third one historically loaded
  every ML model twice.
"""

import pytest


@pytest.fixture(scope="module")
def main_module():
    import app.backend.main as m

    return m


def test_app_imports_without_database(main_module):
    assert main_module.app is not None
    assert len(main_module.app.routes) > 100


def test_exactly_two_startup_handlers(main_module):
    handlers = main_module.app.router.on_startup
    names = [getattr(h, "__name__", str(h)) for h in handlers]
    assert len(handlers) == 2, f"expected 2 startup handlers, got {names}"
    assert "phase1_startup" in names
    assert "startup_event" in names


def test_container_core_registrations_are_factories(main_module):
    """Core services registered at import must be lazy factories — none may
    have been constructed (constructing them opens DB/TF resources)."""
    from app.backend.core.container import get_container

    container = get_container()
    for name in ["settings", "database_client", "database_manager"]:
        assert container.is_registered(name)
    # database clients must NOT be instantiated merely by importing the app
    assert "database_client" not in container._instances
    assert "database_manager" not in container._instances


def test_dead_startup_modules_are_gone():
    with pytest.raises(ImportError):
        import app.backend.core.lifespan  # noqa: F401
    with pytest.raises(ImportError):
        import app.backend.core.bootstrap  # noqa: F401
