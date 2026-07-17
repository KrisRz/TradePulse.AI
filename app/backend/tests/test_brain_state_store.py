"""Tests for BrainStateStore: env-aware DB client, write-before-cache, tz-aware timestamps."""

from unittest.mock import MagicMock, patch

import pytest

from app.backend.core.brain_state_store import BrainState, BrainStateStore


def _settings(is_dev: bool):
    s = MagicMock()
    s.is_development = is_dev
    return s


@pytest.mark.asyncio
async def test_update_state_respects_environment_not_hardcoded_local():
    store = BrainStateStore()
    with patch("app.backend.core.brain_state_store.DynamoDBClient") as client_cls, \
         patch("app.backend.core.config.get_settings", return_value=_settings(False)):
        await store.update_state(enabled=True)

    client_cls.assert_called_once_with(local_development=False)
    client_cls.return_value.put_item.assert_called_once()


@pytest.mark.asyncio
async def test_update_state_failed_write_leaves_cache_untouched():
    store = BrainStateStore()
    store._cache = BrainState(enabled=False, start_time="t0", last_updated="t0")

    with patch("app.backend.core.brain_state_store.DynamoDBClient") as client_cls, \
         patch("app.backend.core.config.get_settings", return_value=_settings(True)):
        client_cls.return_value.put_item.side_effect = RuntimeError("dynamo down")
        with pytest.raises(RuntimeError):
            await store.update_state(enabled=True)

    assert store._cache.enabled is False
    assert store._cache.start_time == "t0"


@pytest.mark.asyncio
async def test_update_state_success_updates_cache_with_tz_aware_timestamps():
    store = BrainStateStore()
    with patch("app.backend.core.brain_state_store.DynamoDBClient") as client_cls, \
         patch("app.backend.core.config.get_settings", return_value=_settings(True)):
        await store.update_state(enabled=True)

    table, item = client_cls.return_value.put_item.call_args.args
    assert table == "brain_portfolio_state"
    assert item["enabled"] is True
    assert "+00:00" in item["start_time"]
    assert "+00:00" in item["last_updated"]

    assert store._cache.enabled is True
    assert store._cache.last_updated == item["last_updated"]
