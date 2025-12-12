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
    groups,
    health,
    marketplace,
    marketplace_sources,
    mcp,
    projects,
    user_collections,
)

__all__ = [
    "analytics",
    "artifacts",
    "bundles",
    "cache",
    "collections",
    "deployments",
    "groups",
    "health",
    "marketplace",
    "marketplace_sources",
    "mcp",
    "projects",
    "user_collections",
]
