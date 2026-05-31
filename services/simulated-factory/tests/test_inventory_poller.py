"""Tests for the InventoryPoller adapter."""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from simulated_factory.adapters.inventory_poller import InventoryPoller


@pytest.fixture
def poller():
    return InventoryPoller(url="http://inventory:8103")


class TestGetCache:
    def test_returns_empty_before_first_fetch(self, poller):
        assert poller.get_cache() == {"grid": None, "rows": 0, "cols": 0}

    def test_returns_cached_data(self, poller):
        poller._cache = {"grid": [[1, 2]], "rows": 1, "cols": 2}
        assert poller.get_cache() == {"grid": [[1, 2]], "rows": 1, "cols": 2}


class TestStartStop:
    @pytest.mark.asyncio
    async def test_start_creates_task(self, poller):
        with patch(
            "simulated_factory.adapters.inventory_poller.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"grid": [[1]], "rows": 1, "cols": 1}
            mock_client.get = AsyncMock(return_value=response)

            await poller.start()
            assert poller._task is not None
            assert not poller._task.done()

            # Let one poll cycle complete
            await asyncio.sleep(0.05)
            assert poller.get_cache() == {"grid": [[1]], "rows": 1, "cols": 1}

            await poller.stop()
            assert poller._task is None

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self, poller):
        with patch(
            "simulated_factory.adapters.inventory_poller.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client
            mock_client.get = AsyncMock(
                return_value=MagicMock(status_code=404)
            )

            await poller.start()
            task1 = poller._task
            await poller.start()
            assert poller._task is task1

            await poller.stop()

    @pytest.mark.asyncio
    async def test_stop_when_not_started(self, poller):
        await poller.stop()  # should not raise


class TestPollingBehavior:
    @pytest.mark.asyncio
    async def test_non_200_does_not_update_cache(self, poller):
        with patch(
            "simulated_factory.adapters.inventory_poller.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            response = MagicMock()
            response.status_code = 500
            mock_client.get = AsyncMock(return_value=response)

            await poller.start()
            await asyncio.sleep(0.05)
            assert poller.get_cache() == {"grid": None, "rows": 0, "cols": 0}
            await poller.stop()

    @pytest.mark.asyncio
    async def test_exception_does_not_crash_poller(self, poller):
        with patch(
            "simulated_factory.adapters.inventory_poller.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client
            mock_client.get = AsyncMock(side_effect=Exception("network down"))

            await poller.start()
            await asyncio.sleep(0.05)
            # Task should still be running
            assert poller._task is not None
            assert not poller._task.done()
            await poller.stop()
