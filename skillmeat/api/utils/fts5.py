"""FTS5 feature detection utility.

This module provides detection of SQLite FTS5 (Full-Text Search) availability
at application startup and caches the result for use throughout the application.

FTS5 is a compile-time SQLite extension that may not be available on all systems.
The search repository uses this detection to decide whether to use FTS5 queries
or fall back to LIKE-based queries.

Usage:
    >>> from skillmeat.api.utils.fts5 import check_fts5_available, is_fts5_available
    >>> from skillmeat.cache.models import get_session
    >>>
    >>> # During startup
    >>> session = get_session()
    >>> check_fts5_available(session)
    >>> session.close()
    >>>
    >>> # Later in the application
    >>> if is_fts5_available():
    ...     # Use FTS5 queries
    ... else:
    ...     # Use LIKE fallback
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Module-level cache for FTS5 availability
_fts5_available: bool | None = None


def check_fts5_available(session: Session) -> bool:
    """Check if FTS5 is available in the current SQLite installation.

    This function checks whether the catalog_fts virtual table exists and
    can be queried. The result is cached after the first check.

    Args:
        session: SQLAlchemy database session

    Returns:
        True if FTS5 is available and working, False otherwise

    Example:
        >>> from skillmeat.cache.models import get_session
        >>> session = get_session()
        >>> try:
        ...     available = check_fts5_available(session)
        ...     print(f"FTS5 available: {available}")
        ... finally:
        ...     session.close()
    """
    global _fts5_available

    if _fts5_available is not None:
        return _fts5_available

    try:
        # Check if the FTS5 virtual table exists
        result = session.execute(
            text(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='catalog_fts'"
            )
        ).fetchone()

        if result is None:
            logger.info("FTS5 table not found, using LIKE-based search")
            _fts5_available = False
            return False

        # Try a simple FTS5 query to verify it works
        session.execute(text("SELECT * FROM catalog_fts LIMIT 0"))
        _fts5_available = True
        logger.info("FTS5 full-text search is available")
        return True

    except Exception as e:
        logger.warning(f"FTS5 not available: {e}. Using LIKE-based search fallback.")
        _fts5_available = False
        return False


def is_fts5_available() -> bool:
    """Return cached FTS5 availability status.

    This function returns the cached result from check_fts5_available().
    If check_fts5_available() hasn't been called yet, returns False.

    Returns:
        True if FTS5 was detected as available, False otherwise

    Example:
        >>> if is_fts5_available():
        ...     # Use FTS5 MATCH query
        ...     query = "SELECT * FROM catalog_fts WHERE catalog_fts MATCH ?"
        ... else:
        ...     # Use LIKE fallback
        ...     query = "SELECT * FROM catalog_entries WHERE name LIKE ?"
    """
    return _fts5_available or False


def reset_fts5_check() -> None:
    """Reset the cached FTS5 availability status.

    This function is primarily intended for testing purposes to allow
    re-checking FTS5 availability.

    Example:
        >>> reset_fts5_check()
        >>> assert is_fts5_available() == False  # Before check
        >>> check_fts5_available(session)
        >>> # Now reflects actual availability
    """
    global _fts5_available
    _fts5_available = None
