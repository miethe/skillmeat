"""Persistent cache module for SkillMeat project and artifact metadata.

This module provides a SQLite-based cache for storing project and artifact
metadata to avoid expensive filesystem scans on every operation. The cache
enables <100ms load times for the web UI and faster CLI operations.

Cache Architecture:
    - SQLite database at ~/.skillmeat/cache.db
    - WAL mode for concurrent access
    - TTL-based refresh strategy
    - Support for local and marketplace artifacts

Main Components:
    - schema: Database schema definition and initialization
    - models: SQLAlchemy ORM models (future)
    - repository: Data access layer (future)

Example:
    >>> from skillmeat.cache.schema import init_database
    >>> init_database()  # Creates database with schema
"""

__version__ = "0.1.0"
