"""Load testing for SkillMeat cache API endpoints.

Run with: locust -f tests/load/locustfile.py --host http://localhost:8000

This simulates realistic load patterns with:
- High frequency status checks (50% of requests)
- Medium frequency project listings (30% of requests)
- Medium frequency artifact searches (20% of requests)
- Low frequency cache refresh operations (10% of requests)

The task weights (numbers in @task decorator) determine request frequency.
Higher numbers = more frequent requests.

Usage:
    1. Start the API server:
       $ skillmeat web dev --api-only

    2. Run the load test:
       $ locust -f tests/load/locustfile.py --host http://localhost:8000

    3. Open browser to http://localhost:8089 to control the test

    4. Recommended starting parameters:
       - Users: 10
       - Spawn rate: 2 users/second
       - Duration: 30+ seconds

Expected Results:
    - All endpoints should respond within 200ms under normal load
    - No database lock errors
    - Cache hit rate should improve over time
    - System should handle 50+ concurrent users without degradation
"""

from __future__ import annotations

from locust import HttpUser, between, task


class CacheLoadTest(HttpUser):
    """Load test simulating cache API usage.

    Simulates realistic user behavior with:
    - Random wait times between requests (100-500ms)
    - Weighted task distribution matching real-world usage patterns
    - Proper error handling and response validation
    """

    # Wait 100-500ms between requests (realistic user behavior)
    wait_time = between(0.1, 0.5)

    @task(5)
    def get_status(self) -> None:
        """High frequency: Get cache status.

        Weight: 5 (highest frequency)
        Endpoint: GET /api/v1/cache/status
        Expected: 200 OK with JSON status data
        """
        with self.client.get("/api/v1/cache/status", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Got status code {response.status_code}")
            elif not response.json():
                response.failure("Empty response body")

    @task(3)
    def list_projects(self) -> None:
        """Medium frequency: List all projects.

        Weight: 3 (medium-high frequency)
        Endpoint: GET /api/v1/cache/projects
        Expected: 200 OK with JSON array of projects
        """
        with self.client.get("/api/v1/cache/projects", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Got status code {response.status_code}")
            elif not isinstance(response.json(), list):
                response.failure("Response is not a list")

    @task(2)
    def search_artifacts(self) -> None:
        """Medium frequency: Search artifacts.

        Weight: 2 (medium frequency)
        Endpoint: GET /api/v1/cache/search
        Expected: 200 OK with JSON search results
        """
        # Vary search queries to test different cache behavior
        queries = ["test", "skill", "api", "cache", "web"]
        import random

        query = random.choice(queries)

        with self.client.get(
            f"/api/v1/cache/search?query={query}", catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Got status code {response.status_code}")
            elif (
                "results" not in response.json() and "artifacts" not in response.json()
            ):
                # Accept either results or artifacts key (depending on API design)
                response.failure("Missing results/artifacts in response")

    @task(1)
    def refresh_cache(self) -> None:
        """Low frequency: Trigger cache refresh.

        Weight: 1 (lowest frequency)
        Endpoint: POST /api/v1/cache/refresh
        Expected: 200 OK or 202 Accepted
        """
        with self.client.post(
            "/api/v1/cache/refresh", json={}, catch_response=True
        ) as response:
            if response.status_code not in [200, 202]:
                response.failure(f"Got status code {response.status_code}")

    def on_start(self) -> None:
        """Called when a simulated user starts.

        This is a good place to perform authentication or setup tasks
        that should happen once per user session.
        """
        # For now, no special setup needed
        # In the future, could add authentication here
        pass


class StressTest(HttpUser):
    """Stress test with minimal wait times.

    Use this class to find breaking points by overwhelming the system.
    Run with: locust -f tests/load/locustfile.py --host http://localhost:8000 StressTest
    """

    # Minimal wait time to stress the system
    wait_time = between(0.01, 0.05)

    @task(10)
    def rapid_status_checks(self) -> None:
        """Rapid-fire status checks."""
        self.client.get("/api/v1/cache/status")

    @task(5)
    def rapid_project_list(self) -> None:
        """Rapid-fire project listings."""
        self.client.get("/api/v1/cache/projects")

    @task(1)
    def rapid_refresh(self) -> None:
        """Rapid-fire refresh requests."""
        self.client.post("/api/v1/cache/refresh", json={})
