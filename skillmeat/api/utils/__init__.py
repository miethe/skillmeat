"""API utility modules.

Provides caching, helpers, and other utility functions for the API layer.
"""

from .cache import CacheManager, generate_etag

__all__ = ["CacheManager", "generate_etag"]
