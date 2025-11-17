"""Locust load testing suite for SkillMeat API.

This module provides comprehensive load tests for all major API endpoints,
simulating realistic user behavior patterns and concurrent access scenarios.

Usage:
    locust -f tests/performance/locustfile.py --headless --users 100 --spawn-rate 10 --run-time 5m --host http://localhost:8000

For web UI:
    locust -f tests/performance/locustfile.py --host http://localhost:8000
"""

import random
from locust import HttpUser, task, between, SequentialTaskSet


class MarketplaceBrowsingTaskSet(SequentialTaskSet):
    """Sequential task set simulating typical marketplace browsing behavior."""

    def on_start(self):
        """Initialize with auth token if needed."""
        # For now, assume public access. Add auth if needed:
        # response = self.client.post("/api/auth/token", json={
        #     "username": "test_user",
        #     "password": "test_pass"
        # })
        # self.token = response.json()["token"]
        # self.headers = {"Authorization": f"Bearer {self.token}"}
        self.headers = {}

    @task
    def browse_listings(self):
        """Browse marketplace listings."""
        self.client.get(
            "/api/marketplace/listings",
            headers=self.headers,
            params={"limit": 50},
            name="/api/marketplace/listings [browse]"
        )

    @task
    def search_listings(self):
        """Search listings with filters."""
        tags = ["productivity", "automation", "python", "javascript", "testing"]
        queries = ["tool", "framework", "helper", "utility", "automation"]

        self.client.get(
            "/api/marketplace/listings",
            headers=self.headers,
            params={
                "query": random.choice(queries),
                "tags": random.choice(tags),
                "limit": 20
            },
            name="/api/marketplace/listings [search]"
        )

    @task
    def view_listing_detail(self):
        """View a specific listing."""
        # Simulate clicking on one of the first 100 listings
        listing_id = f"skillmeat-{random.randint(1, 100)}"
        self.client.get(
            f"/api/marketplace/listings/{listing_id}",
            headers=self.headers,
            name="/api/marketplace/listings/{id}"
        )


class CollectionManagementTaskSet(SequentialTaskSet):
    """Sequential task set simulating collection management operations."""

    def on_start(self):
        """Initialize headers."""
        self.headers = {}

    @task
    def list_collections(self):
        """List all collections."""
        self.client.get(
            "/api/collections",
            headers=self.headers,
            name="/api/collections [list]"
        )

    @task
    def get_collection_detail(self):
        """Get details for a specific collection."""
        # Assume default collection exists
        self.client.get(
            "/api/collections/default",
            headers=self.headers,
            name="/api/collections/{id}"
        )

    @task
    def list_artifacts(self):
        """List artifacts in a collection."""
        self.client.get(
            "/api/collections/default/artifacts",
            headers=self.headers,
            name="/api/collections/{id}/artifacts"
        )


class MCPOperationsTaskSet(SequentialTaskSet):
    """Sequential task set for MCP server operations."""

    def on_start(self):
        """Initialize headers."""
        self.headers = {}

    @task
    def check_mcp_health(self):
        """Check MCP server health."""
        self.client.get(
            "/api/mcp/health",
            headers=self.headers,
            name="/api/mcp/health"
        )

    @task
    def list_mcp_servers(self):
        """List all MCP servers."""
        self.client.get(
            "/api/mcp/servers",
            headers=self.headers,
            name="/api/mcp/servers"
        )


class BundleOperationsTaskSet(SequentialTaskSet):
    """Sequential task set for bundle operations."""

    def on_start(self):
        """Initialize headers."""
        self.headers = {}

    @task
    def export_bundle(self):
        """Export a bundle."""
        self.client.post(
            "/api/sharing/export",
            headers=self.headers,
            json={
                "artifacts": [f"artifact-{i}" for i in range(1, 6)],
                "name": f"test-bundle-{random.randint(1, 1000)}"
            },
            name="/api/sharing/export"
        )

    @task
    def list_bundles(self):
        """List available bundles."""
        self.client.get(
            "/api/sharing/bundles",
            headers=self.headers,
            name="/api/sharing/bundles"
        )


class AnalyticsTaskSet(SequentialTaskSet):
    """Sequential task set for analytics operations."""

    def on_start(self):
        """Initialize headers."""
        self.headers = {}

    @task
    def get_usage_stats(self):
        """Get usage statistics."""
        self.client.get(
            "/api/analytics/usage",
            headers=self.headers,
            params={"days": 30},
            name="/api/analytics/usage"
        )

    @task
    def get_top_artifacts(self):
        """Get top artifacts."""
        self.client.get(
            "/api/analytics/top-artifacts",
            headers=self.headers,
            params={"limit": 20},
            name="/api/analytics/top-artifacts"
        )


class SkillMeatUser(HttpUser):
    """Simulated user with mixed workload patterns."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    # Weight distribution of different user types
    tasks = {
        MarketplaceBrowsingTaskSet: 5,    # 50% marketplace browsing
        CollectionManagementTaskSet: 2,   # 20% collection management
        MCPOperationsTaskSet: 1,          # 10% MCP operations
        BundleOperationsTaskSet: 1,       # 10% bundle operations
        AnalyticsTaskSet: 1,              # 10% analytics
    }


class MarketplaceBrowsingUser(HttpUser):
    """User focused on marketplace browsing (most common pattern)."""

    wait_time = between(1, 3)
    tasks = [MarketplaceBrowsingTaskSet]


class PowerUser(HttpUser):
    """Power user with heavier operations and shorter wait times."""

    wait_time = between(0.5, 2)
    tasks = {
        CollectionManagementTaskSet: 3,
        BundleOperationsTaskSet: 2,
        MarketplaceBrowsingTaskSet: 1,
    }


class AdminUser(HttpUser):
    """Admin user focused on health checks and monitoring."""

    wait_time = between(2, 5)
    tasks = {
        MCPOperationsTaskSet: 3,
        AnalyticsTaskSet: 2,
    }


# Simple single-task users for focused load testing
class MarketplaceOnlyUser(HttpUser):
    """User that only browses marketplace listings."""

    wait_time = between(1, 2)

    @task(5)
    def browse_marketplace(self):
        """Most common operation."""
        self.client.get(
            "/api/marketplace/listings",
            params={"limit": 50},
            name="/api/marketplace/listings [browse]"
        )

    @task(3)
    def search_marketplace(self):
        """Search with filters."""
        tags = ["productivity", "automation", "python", "javascript"]
        self.client.get(
            "/api/marketplace/listings",
            params={
                "query": "tool",
                "tags": random.choice(tags),
                "limit": 20
            },
            name="/api/marketplace/listings [search]"
        )

    @task(2)
    def view_listing_detail(self):
        """View single listing."""
        listing_id = f"skillmeat-{random.randint(1, 100)}"
        self.client.get(
            f"/api/marketplace/listings/{listing_id}",
            name="/api/marketplace/listings/{id}"
        )


class HealthCheckUser(HttpUser):
    """User that performs frequent health checks."""

    wait_time = between(0.5, 1.5)

    @task
    def check_mcp_health(self):
        """MCP health check."""
        self.client.get("/api/mcp/health", name="/api/mcp/health")

    @task
    def check_api_health(self):
        """API health check."""
        self.client.get("/health", name="/health")
