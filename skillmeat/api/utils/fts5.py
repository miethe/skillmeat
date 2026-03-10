"""FTS5 / full-text search backend detection utility.

This module detects which search backend is available at application startup
and caches the result for use throughout the application.

Supported backends (in preference order per dialect):

* **tsvector** – PostgreSQL with a pre-built ``search_vector`` column on
  ``marketplace_catalog_entries``.  Fastest for PG workloads.
* **fts5** – SQLite FTS5 virtual table (``catalog_fts``).  Available when
  SQLite was compiled with the FTS5 extension.
* **like** – Plain ``LIKE`` fallback. Works on every database but is slow
  on large tables.

Usage::

    >>> from skillmeat.api.utils.fts5 import detect_and_cache_backend, get_search_backend
    >>> from skillmeat.cache.models import get_session
    >>>
    >>> # During startup (called once)
    >>> session = get_session()
    >>> detect_and_cache_backend(session)
    >>> session.close()
    >>>
    >>> # Later in the application
    >>> from skillmeat.api.utils.fts5 import SearchBackendType, get_search_backend
    >>> if get_search_backend() == SearchBackendType.TSVECTOR:
    ...     # Use tsvector query
    ... elif get_search_backend() == SearchBackendType.FTS5:
    ...     # Use FTS5 MATCH query
    ... else:
    ...     # Use LIKE fallback

Backward-compatible helpers
---------------------------
All existing call-sites continue to work unchanged:

* :func:`check_fts5_available` – detect + cache + return bool (SQLite FTS5)
* :func:`is_fts5_available` – return cached bool (True iff backend is FTS5)
* :func:`reset_fts5_check` – reset both legacy and new caches (for tests)
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Search backend enum
# ---------------------------------------------------------------------------


class SearchBackendType(str, Enum):
    """Enumeration of supported full-text search backends.

    Values are plain strings so they can be serialised in JSON responses or
    log lines without extra conversion.
    """

    FTS5 = "fts5"
    TSVECTOR = "tsvector"
    LIKE = "like"


# ---------------------------------------------------------------------------
# Module-level caches (thread-safe for read-heavy access; writes happen once
# at startup before any request threads are active)
# ---------------------------------------------------------------------------

_cached_backend: Optional[SearchBackendType] = None

# Legacy cache retained so check_fts5_available() keeps its own contract
_fts5_available: Optional[bool] = None


# ---------------------------------------------------------------------------
# Core detection logic
# ---------------------------------------------------------------------------


def _check_sqlite_fts5(session: Session) -> bool:
    """Return True if the SQLite ``catalog_fts`` virtual table exists and works."""
    result = session.execute(
        text(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='catalog_fts'"
        )
    ).fetchone()

    if result is None:
        return False

    # Probe the table to confirm the FTS5 module is functional
    session.execute(text("SELECT * FROM catalog_fts LIMIT 0"))
    return True


def _check_pg_tsvector(session: Session) -> bool:
    """Return True if ``search_vector`` column exists in ``marketplace_catalog_entries``."""
    result = session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'marketplace_catalog_entries' "
            "AND column_name = 'search_vector'"
        )
    ).fetchone()
    return result is not None


def detect_search_backend(session: Session) -> SearchBackendType:
    """Probe the database and return the best available search backend.

    Detection is stateless — it does **not** update any module-level cache.
    Call :func:`detect_and_cache_backend` to detect and persist the result.

    Args:
        session: An active SQLAlchemy session.

    Returns:
        The :class:`SearchBackendType` that should be used for searches.
    """
    try:
        # Resolve the dialect name regardless of session binding style
        try:
            bind = session.get_bind()
        except Exception:
            bind = session.bind  # type: ignore[attr-defined]

        dialect_name: str = getattr(
            getattr(bind, "dialect", None), "name", ""
        ).lower()

        if dialect_name == "postgresql":
            try:
                if _check_pg_tsvector(session):
                    logger.info(
                        "Search backend detected: tsvector "
                        "(PostgreSQL search_vector column present)"
                    )
                    return SearchBackendType.TSVECTOR
                else:
                    logger.info(
                        "Search backend detected: like "
                        "(PostgreSQL, search_vector column absent)"
                    )
                    return SearchBackendType.LIKE
            except Exception as exc:
                logger.warning(
                    "tsvector detection failed, falling back to LIKE: %s", exc
                )
                return SearchBackendType.LIKE

        if dialect_name == "sqlite":
            try:
                if _check_sqlite_fts5(session):
                    logger.info(
                        "Search backend detected: fts5 "
                        "(SQLite catalog_fts virtual table available)"
                    )
                    return SearchBackendType.FTS5
                else:
                    logger.info(
                        "Search backend detected: like "
                        "(SQLite, FTS5 table not found)"
                    )
                    return SearchBackendType.LIKE
            except Exception as exc:
                logger.warning(
                    "FTS5 detection failed, falling back to LIKE: %s", exc
                )
                return SearchBackendType.LIKE

        # Unknown dialect — be conservative
        logger.info(
            "Search backend detected: like (unrecognised dialect %r)", dialect_name
        )
        return SearchBackendType.LIKE

    except Exception as exc:
        logger.warning(
            "Search backend detection failed entirely, falling back to LIKE: %s", exc
        )
        return SearchBackendType.LIKE


# ---------------------------------------------------------------------------
# Cached accessors
# ---------------------------------------------------------------------------


def get_search_backend() -> SearchBackendType:
    """Return the cached search backend type.

    Falls back to :attr:`SearchBackendType.LIKE` if
    :func:`detect_and_cache_backend` has not been called yet.

    Returns:
        The cached :class:`SearchBackendType`.
    """
    return _cached_backend if _cached_backend is not None else SearchBackendType.LIKE


def detect_and_cache_backend(session: Session) -> SearchBackendType:
    """Detect the search backend, cache the result, and return it.

    This should be called **once** during application startup.  Subsequent
    calls are cheap — they re-detect and overwrite the cache (idempotent).

    Args:
        session: An active SQLAlchemy session.

    Returns:
        The detected :class:`SearchBackendType`.
    """
    global _cached_backend, _fts5_available
    _cached_backend = detect_search_backend(session)
    # Keep legacy cache in sync
    _fts5_available = _cached_backend == SearchBackendType.FTS5
    return _cached_backend


# ---------------------------------------------------------------------------
# Backward-compatible helpers
# ---------------------------------------------------------------------------


def check_fts5_available(session: Session) -> bool:
    """Check if FTS5 is available and cache the result.

    This is the original public API for FTS5 detection.  Internally it now
    delegates to :func:`detect_and_cache_backend` so that both the legacy
    ``_fts5_available`` flag **and** the new ``_cached_backend`` are kept in
    sync from a single detection pass.

    Args:
        session: SQLAlchemy database session.

    Returns:
        ``True`` if FTS5 is available and working, ``False`` otherwise.

    Example::

        >>> from skillmeat.cache.models import get_session
        >>> session = get_session()
        >>> try:
        ...     available = check_fts5_available(session)
        ...     print(f"FTS5 available: {available}")
        ... finally:
        ...     session.close()
    """
    global _fts5_available

    # If the new cache is already populated, honour it (avoids a second probe
    # if detect_and_cache_backend was called first).
    if _cached_backend is not None:
        return _cached_backend == SearchBackendType.FTS5

    # Legacy fast path: if called repeatedly without reset
    if _fts5_available is not None:
        return _fts5_available

    detect_and_cache_backend(session)
    return _fts5_available  # type: ignore[return-value]  # set by detect_and_cache_backend


def is_fts5_available() -> bool:
    """Return cached FTS5 availability status.

    Returns ``True`` iff the detected backend is :attr:`SearchBackendType.FTS5`.
    Returns ``False`` when detection has not yet run.

    Returns:
        ``True`` if FTS5 was detected as available, ``False`` otherwise.

    Example::

        >>> if is_fts5_available():
        ...     query = "SELECT * FROM catalog_fts WHERE catalog_fts MATCH ?"
        ... else:
        ...     query = "SELECT * FROM catalog_entries WHERE name LIKE ?"
    """
    return get_search_backend() == SearchBackendType.FTS5


def is_tsvector_available() -> bool:
    """Return ``True`` iff the detected backend is PostgreSQL tsvector.

    Returns:
        ``True`` if tsvector search is available, ``False`` otherwise.

    Example::

        >>> if is_tsvector_available():
        ...     # Use tsvector-based search query
        ...     pass
    """
    return get_search_backend() == SearchBackendType.TSVECTOR


def reset_fts5_check() -> None:
    """Reset all cached search backend state.

    Clears both the new dialect-aware cache and the legacy FTS5 flag.  This
    is primarily intended for testing to allow re-detection.

    Example::

        >>> reset_fts5_check()
        >>> assert is_fts5_available() == False  # Before check
        >>> check_fts5_available(session)
        >>> # Now reflects actual availability
    """
    global _fts5_available, _cached_backend
    _fts5_available = None
    _cached_backend = None
