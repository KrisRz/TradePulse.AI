"""
Regression tests for the DI container (M0/A1).

The historical bug: factory detection used `callable(x) and not
hasattr(x, "__dict__")` — but Python functions/lambdas DO have __dict__,
so every factory landed in _instances uncalled, `_factories` stayed empty
and `get()` handed raw lambdas to callers. Additionally re-registration
was silently skipped, so swapping a factory for the initialized instance
during startup did nothing.
"""

import asyncio

import pytest

from app.backend.core.container import ServiceContainer, require_instance


class Dummy:
    """Stand-in service."""

    def __init__(self, value: int = 42):
        self.value = value


@pytest.fixture()
def container():
    return ServiceContainer()


def test_lambda_factory_is_called_not_returned(container):
    container.register_singleton("dummy", lambda: Dummy(7))
    got = container.get("dummy")
    assert isinstance(got, Dummy)
    assert got.value == 7


def test_function_factory_is_called(container):
    def make():
        return Dummy(13)

    container.register_singleton("dummy", make)
    assert container.get("dummy").value == 13


def test_class_registration_instantiates(container):
    container.register_singleton("dummy", Dummy)
    assert isinstance(container.get("dummy"), Dummy)


def test_instance_registration_returns_same_object(container):
    obj = Dummy(1)
    container.register_singleton("dummy", obj)
    assert container.get("dummy") is obj


def test_singleton_factory_called_once(container):
    calls = []

    def make():
        calls.append(1)
        return Dummy()

    container.register_singleton("dummy", make)
    a = container.get("dummy")
    b = container.get("dummy")
    assert a is b
    assert len(calls) == 1


def test_reregistration_replaces_factory_with_instance(container):
    container.register_singleton("svc", lambda: Dummy(1))
    real = Dummy(99)
    container.register_singleton("svc", real)
    assert container.get("svc") is real


def test_factory_receiving_container(container):
    container.register_singleton("dep", Dummy(5))
    container.register_singleton("svc", lambda c: Dummy(c.get("dep").value + 1))
    assert container.get("svc").value == 6


def test_async_factory_sync_get_raises_clear_error(container):
    async def make():
        return Dummy()

    container.register_singleton("svc", make)
    with pytest.raises(TypeError, match="async factory"):
        container.get("svc")


def test_async_factory_get_async(container):
    async def make():
        return Dummy(3)

    container.register_singleton("svc", make)
    got = asyncio.run(container.get_async("svc"))
    assert isinstance(got, Dummy)
    assert got.value == 3
    # cached as instance afterwards — sync get works now
    assert container.get("svc") is got


def test_require_instance_rejects_factories():
    with pytest.raises(TypeError):
        require_instance("x", lambda: 1)
    with pytest.raises(TypeError):
        require_instance("x", Dummy)
    obj = Dummy()
    assert require_instance("x", obj) is obj


def test_core_services_resolve_to_instances(container):
    # settings is registered as a factory (get_settings) at construction time
    settings = container.get("settings")
    assert not callable(settings) or hasattr(settings, "app_name") or hasattr(type(settings), "__mro__")
    # it must NOT be the raw get_settings function
    assert not callable(settings) or not hasattr(settings, "__wrapped__")
    assert settings.__class__.__name__ != "function"


def test_get_unregistered_raises_keyerror(container):
    with pytest.raises(KeyError):
        container.get("nope")


def test_sealed_container_rejects_registration(container):
    container.seal()
    with pytest.raises(RuntimeError):
        container.register_singleton("late", Dummy(1))
