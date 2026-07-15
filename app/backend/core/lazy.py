"""
LazyProxy — defers singleton construction until first attribute access.

Module-level `service = get_service()` exports used to construct services
(and open DynamoDB connections) as an import side effect, which broke any
process that merely imported the package (tests, Lambda cold start, scripts).
Wrapping the getter keeps the import contract (`from x import service;
service.method()`) while deferring construction to first real use.
"""

from typing import Callable


class LazyProxy:
    """Transparent attribute-forwarding proxy around a singleton getter."""

    __slots__ = ("_getter",)

    def __init__(self, getter: Callable):
        object.__setattr__(self, "_getter", getter)

    def __getattr__(self, item):
        return getattr(object.__getattribute__(self, "_getter")(), item)

    def __setattr__(self, key, value):
        setattr(object.__getattribute__(self, "_getter")(), key, value)

    def __repr__(self):
        getter = object.__getattribute__(self, "_getter")
        return f"<LazyProxy for {getattr(getter, '__name__', getter)!r}>"
