"""API routers package.

This package contains all API route handlers organized by domain.
"""

from . import (
    analytics,
    artifacts,
    bundles,
    cache,
    collections,
    context_entities,
    context_sync,
    deployments,
    groups,
    health,
    marketplace,
    marketplace_sources,
    mcp,
    merge,
    project_templates,
    projects,
    tags,
    user_collections,
    versions,
)

__all__ = [
    "analytics",
    "artifacts",
    "bundles",
    "cache",
    "collections",
    "context_entities",
    "context_sync",
    "deployments",
    "groups",
    "health",
    "marketplace",
    "marketplace_sources",
    "mcp",
    "merge",
    "project_templates",
    "projects",
    "tags",
    "user_collections",
    "versions",
]
