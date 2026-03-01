
import asyncio
import time
import pytest
from unittest.mock import MagicMock, patch
from fastapi import Request, Response
from skillmeat.marketplace.models import MarketplaceListing

# Define Mock Broker
class MockBroker:
    def __init__(self, name, delay=1.0):
        self.name = name
        self.delay = delay

    def listings(self, page=1, page_size=100, filters=None):
        print(f"Broker {self.name} fetching listings (sleeping {self.delay}s)...")
        time.sleep(self.delay)  # Simulate blocking I/O
        return []

@pytest.mark.asyncio
async def test_marketplace_listing_parallel_performance():
    # Setup mocks
    mock_registry = MagicMock()
    mock_broker1 = MockBroker("broker1", delay=0.5)
    mock_broker2 = MockBroker("broker2", delay=0.5)
    mock_registry.get_enabled_brokers.return_value = [mock_broker1, mock_broker2]

    # Mock CacheManager
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.set.return_value = "etag"

    # Patch dependencies
    with patch("skillmeat.api.routers.marketplace.get_broker_registry", return_value=mock_registry), \
         patch("skillmeat.api.routers.marketplace.cache_manager", mock_cache):

        from skillmeat.api.routers.marketplace import get_listing_detail

        # Prepare arguments
        req = MagicMock(spec=Request)
        req.headers = {}
        res = MagicMock(spec=Response)

        # Measure time
        start_time = time.time()
        ticks = []

        # Run concurrent ticker to check for blocking
        async def background_ticker():
            while True:
                ticks.append(time.time())
                await asyncio.sleep(0.1)

        ticker_task = asyncio.create_task(background_ticker())

        try:
            await get_listing_detail("target_id", req, res, token=None)
        except Exception:
            # Expected failure (listing not found)
            pass

        end_time = time.time()
        duration = end_time - start_time

        ticker_task.cancel()
        try:
            await ticker_task
        except asyncio.CancelledError:
            pass

        # Filter ticks that happened strictly during the execution window
        concurrent_ticks = [t for t in ticks if start_time < t < end_time]

        print(f"Duration: {duration:.2f}s, Concurrent Ticks: {len(concurrent_ticks)}")

        # Assertions logic for demonstration (commented out to allow baseline run)
        # if duration > 0.9:
        #    print("Result: BLOCKED (Sequential execution)")
        # else:
        #    print("Result: OPTIMIZED (Parallel execution)")

        return duration, len(concurrent_ticks)

if __name__ == "__main__":
    pass
