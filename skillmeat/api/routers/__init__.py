"""API routers package.

This package contains all API route handlers organized by domain.
"""

from . import (
    analytics,
    artifacts,
    bundles,
    cache,
    collections,
    deployments,
    health,
    marketplace,
    marketplace_sources,
    mcp,
    projects,
)

__all__ = [
    "analytics",
    "artifacts",
    "bundles",
    "cache",
    "collections",
    "deployments",
    "health",
    "marketplace",
    "marketplace_sources",
    "mcp",
    "projects",
]
