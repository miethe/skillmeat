"""API utility modules.

Provides caching, helpers, and other utility functions for the API layer.
"""

from .cache import CacheManager, generate_etag
from .error_handlers import (
    create_bad_request_error,
    create_conflict_error,
    create_internal_error,
    create_not_found_error,
    create_rate_limit_error,
    create_validation_error,
    validate_artifact_request,
)
from .fts5 import (
    check_fts5_available,
    is_fts5_available,
    reset_fts5_check,
)
from .github_cache import (
    DEFAULT_CONTENT_TTL,
    DEFAULT_TREE_TTL,
    GitHubFileCache,
    build_content_key,
    build_tree_key,
    get_github_file_cache,
    reset_github_file_cache,
)

__all__ = [
    # General cache utilities
    "CacheManager",
    "generate_etag",
    # GitHub file cache
    "GitHubFileCache",
    "get_github_file_cache",
    "reset_github_file_cache",
    "build_tree_key",
    "build_content_key",
    "DEFAULT_TREE_TTL",
    "DEFAULT_CONTENT_TTL",
    # Error handlers
    "create_bad_request_error",
    "create_conflict_error",
    "create_internal_error",
    "create_not_found_error",
    "create_rate_limit_error",
    "create_validation_error",
    "validate_artifact_request",
    # FTS5 detection
    "check_fts5_available",
    "is_fts5_available",
    "reset_fts5_check",
]
