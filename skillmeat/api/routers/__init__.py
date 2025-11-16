"""API routers package.

This package contains all API route handlers organized by domain.
"""

from . import health, collections, artifacts, analytics

__all__ = ["health", "collections", "artifacts", "analytics"]
