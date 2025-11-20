"""API routers package.

This package contains all API route handlers organized by domain.
"""

from . import analytics, artifacts, bundles, collections, deployments, health, marketplace, sync

__all__ = [
    "health",
    "collections",
    "artifacts",
    "analytics",
    "bundles",
    "deployments",
    "marketplace",
    "sync",
]
