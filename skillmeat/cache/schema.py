"""SQLite cache database schema for SkillMeat.

This module defines the database schema for the persistent project cache,
including tables for projects, artifacts, metadata, and marketplace entries.

The schema is designed for:
- Fast query performance with strategic indexes
- Support for both local and marketplace artifacts
- TTL-based refresh strategies
- Concurrent read/write access (WAL mode)

Database Location:
    - Default: ~/.skillmeat/cache.db
    - Configurable via init_database(db_path)

Schema Version: 1.0.0
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

# Schema version for migration tracking
SCHEMA_VERSION = "1.0.0"


def get_schema_sql() -> str:
    """Get complete SQL schema definition.

    Returns:
        SQL string containing all CREATE TABLE and CREATE INDEX statements

    The schema includes:
        - projects: Project metadata and status
        - artifacts: Artifact metadata per project
        - artifact_metadata: Extended artifact metadata (YAML frontmatter)
        - marketplace: Cached marketplace artifact listings
        - marketplace_sources: GitHub repository sources for marketplace artifacts
        - marketplace_catalog_entries: Detected artifacts from marketplace sources
        - cache_metadata: Cache system metadata (version, TTL, etc.)

    Performance Considerations:
        - Indexes optimized for common query patterns
        - Composite indexes for multi-column queries
        - UNIQUE constraints for data integrity
        - CASCADE delete for automatic cleanup
        - Run ANALYZE after bulk inserts (>100 rows) to update query planner stats
    """
    return """
-- =============================================================================
-- Projects Table
-- =============================================================================
-- Stores project-level metadata and cache status
--
-- Key Indexes:
--   - idx_projects_status: Fast filtering by status (active/stale/error)
--   - idx_projects_last_fetched: TTL-based refresh queries
--   - idx_projects_path (UNIQUE): Enforce one cache entry per project path

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_fetched TIMESTAMP,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'stale', 'error')),
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_last_fetched ON projects(last_fetched);

-- =============================================================================
-- Artifacts Table
-- =============================================================================
-- Stores artifact metadata for each project
--
-- Key Indexes:
--   - idx_artifacts_project_id: Join performance for project queries
--   - idx_artifacts_type: Filter by artifact type (skill, agent, command, etc.)
--   - idx_artifacts_is_outdated: Find artifacts needing updates
--   - idx_artifacts_updated_at: Sort by recency
--   - idx_artifacts_name: Search by artifact name (for full-text search)
--   - idx_artifacts_project_type: Composite for "all skills in project X" queries
--   - idx_artifacts_outdated_type: Composite for "all outdated skills" queries
--
-- Foreign Keys:
--   - project_id → projects.id (CASCADE delete)

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook')),
    source TEXT,
    deployed_version TEXT,
    upstream_version TEXT,
    is_outdated BOOLEAN DEFAULT 0,
    local_modified BOOLEAN DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_artifacts_project_id ON artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(type);
CREATE INDEX IF NOT EXISTS idx_artifacts_is_outdated ON artifacts(is_outdated);
CREATE INDEX IF NOT EXISTS idx_artifacts_updated_at ON artifacts(updated_at);
CREATE INDEX IF NOT EXISTS idx_artifacts_name ON artifacts(name);
CREATE INDEX IF NOT EXISTS idx_artifacts_project_type ON artifacts(project_id, type);
CREATE INDEX IF NOT EXISTS idx_artifacts_outdated_type ON artifacts(is_outdated, type);

-- =============================================================================
-- Artifact Metadata Table
-- =============================================================================
-- Extended metadata from YAML frontmatter
--
-- Key Indexes:
--   - idx_metadata_tags: Tag-based search performance
--
-- Storage:
--   - metadata: Full YAML frontmatter as JSON (for exact preservation)
--   - description: Extracted for quick access
--   - tags: Comma-separated for searchability
--   - aliases: Comma-separated for alias resolution
--
-- Foreign Keys:
--   - artifact_id → artifacts.id (CASCADE delete)

CREATE TABLE IF NOT EXISTS artifact_metadata (
    artifact_id TEXT PRIMARY KEY,
    metadata TEXT,
    description TEXT,
    tags TEXT,
    aliases TEXT,
    FOREIGN KEY (artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_metadata_tags ON artifact_metadata(tags);

-- =============================================================================
-- Marketplace Table
-- =============================================================================
-- Cached marketplace artifact listings
--
-- Key Indexes:
--   - idx_marketplace_type: Filter marketplace by artifact type
--   - idx_marketplace_name: Fast lookup by artifact name
--
-- TTL:
--   - cached_at timestamp enables TTL-based refresh
--   - Typically refresh every 1-6 hours depending on load

CREATE TABLE IF NOT EXISTS marketplace (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook')),
    url TEXT NOT NULL,
    description TEXT,
    cached_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data TEXT
);

CREATE INDEX IF NOT EXISTS idx_marketplace_type ON marketplace(type);
CREATE INDEX IF NOT EXISTS idx_marketplace_name ON marketplace(name);

-- =============================================================================
-- Marketplace Sources Table
-- =============================================================================
-- GitHub repository sources for marketplace artifacts
--
-- Key Indexes:
--   - idx_marketplace_sources_repo_url (UNIQUE): One entry per repo URL
--   - idx_marketplace_sources_last_sync: TTL-based refresh queries
--   - idx_marketplace_sources_scan_status: Filter by scan status
--   - idx_marketplace_sources_owner_repo: Lookup by owner/repo combination
--
-- Trust Levels:
--   - untrusted: User-added repositories, not verified
--   - basic: Basic verification performed
--   - verified: Manually verified by maintainers
--   - official: Official Anthropic/Claude repositories
--
-- Visibility:
--   - private: Requires authentication, not publicly listed
--   - internal: Authenticated users only
--   - public: Publicly accessible repositories
--
-- Scan Status:
--   - pending: Awaiting first scan
--   - scanning: Currently being scanned
--   - success: Last scan completed successfully
--   - error: Last scan failed (see last_error)

CREATE TABLE IF NOT EXISTS marketplace_sources (
    id TEXT PRIMARY KEY,
    repo_url TEXT NOT NULL UNIQUE,
    owner TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    ref TEXT NOT NULL DEFAULT 'main',
    root_hint TEXT,
    manual_map TEXT,
    access_token_id TEXT,
    trust_level TEXT NOT NULL DEFAULT 'basic' CHECK(trust_level IN ('untrusted', 'basic', 'verified', 'official')),
    visibility TEXT NOT NULL DEFAULT 'public' CHECK(visibility IN ('private', 'internal', 'public')),
    last_sync_at TIMESTAMP,
    last_error TEXT,
    scan_status TEXT NOT NULL DEFAULT 'pending' CHECK(scan_status IN ('pending', 'scanning', 'success', 'error')),
    artifact_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_marketplace_sources_repo_url ON marketplace_sources(repo_url);
CREATE INDEX IF NOT EXISTS idx_marketplace_sources_last_sync ON marketplace_sources(last_sync_at);
CREATE INDEX IF NOT EXISTS idx_marketplace_sources_scan_status ON marketplace_sources(scan_status);
CREATE INDEX IF NOT EXISTS idx_marketplace_sources_owner_repo ON marketplace_sources(owner, repo_name);

-- =============================================================================
-- Marketplace Catalog Entries Table
-- =============================================================================
-- Detected artifacts from marketplace source repositories
--
-- Key Indexes:
--   - idx_catalog_entries_source_id: Query by source repository
--   - idx_catalog_entries_status: Filter by import status
--   - idx_catalog_entries_type: Filter by artifact type
--   - idx_catalog_entries_upstream_url: Deduplication on upstream URL
--   - idx_catalog_entries_source_status: Composite for filtered queries by source+status
--   - idx_catalog_entries_source_type: Composite for queries by source+artifact_type
--   - idx_catalog_entries_confidence: Filter by confidence score threshold
--
-- Status Values:
--   - new: Newly detected artifact, not yet imported
--   - updated: Existing artifact with upstream changes detected
--   - removed: Previously detected artifact no longer found
--   - imported: Artifact successfully imported to user collection
--
-- Foreign Keys:
--   - source_id → marketplace_sources.id (CASCADE delete)

CREATE TABLE IF NOT EXISTS marketplace_catalog_entries (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL CHECK(artifact_type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', 'composite', 'project_config', 'spec_file', 'rule_file', 'context_file', 'progress_template')),
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    upstream_url TEXT NOT NULL,
    detected_version TEXT,
    detected_sha TEXT,
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confidence_score INTEGER NOT NULL CHECK(confidence_score >= 0 AND confidence_score <= 100),
    status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new', 'updated', 'removed', 'imported', 'excluded')),
    import_date TIMESTAMP,
    import_id TEXT,
    metadata_json TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES marketplace_sources(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_catalog_entries_source_id ON marketplace_catalog_entries(source_id);
CREATE INDEX IF NOT EXISTS idx_catalog_entries_status ON marketplace_catalog_entries(status);
CREATE INDEX IF NOT EXISTS idx_catalog_entries_type ON marketplace_catalog_entries(artifact_type);
CREATE INDEX IF NOT EXISTS idx_catalog_entries_upstream_url ON marketplace_catalog_entries(upstream_url);
CREATE INDEX IF NOT EXISTS idx_catalog_entries_source_status ON marketplace_catalog_entries(source_id, status);
CREATE INDEX IF NOT EXISTS idx_catalog_entries_source_type ON marketplace_catalog_entries(source_id, artifact_type);
CREATE INDEX IF NOT EXISTS idx_catalog_entries_confidence ON marketplace_catalog_entries(confidence_score);

-- =============================================================================
-- Cache Metadata Table
-- =============================================================================
-- System metadata for cache management
--
-- Common Keys:
--   - schema_version: Database schema version
--   - last_vacuum: Last VACUUM operation timestamp
--   - last_analyze: Last ANALYZE operation timestamp
--   - total_projects: Cached count for performance
--   - total_artifacts: Cached count for performance

CREATE TABLE IF NOT EXISTS cache_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- Triggers for automatic updated_at maintenance
-- =============================================================================

CREATE TRIGGER IF NOT EXISTS projects_updated_at
AFTER UPDATE ON projects
FOR EACH ROW
BEGIN
    UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS artifacts_updated_at
AFTER UPDATE ON artifacts
FOR EACH ROW
BEGIN
    UPDATE artifacts SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS cache_metadata_updated_at
AFTER UPDATE ON cache_metadata
FOR EACH ROW
BEGIN
    UPDATE cache_metadata SET updated_at = CURRENT_TIMESTAMP WHERE key = NEW.key;
END;

CREATE TRIGGER IF NOT EXISTS marketplace_sources_updated_at
AFTER UPDATE ON marketplace_sources
FOR EACH ROW
BEGIN
    UPDATE marketplace_sources SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS marketplace_catalog_entries_updated_at
AFTER UPDATE ON marketplace_catalog_entries
FOR EACH ROW
BEGIN
    UPDATE marketplace_catalog_entries SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
"""


def get_pragma_sql() -> str:
    """Get SQLite PRAGMA configuration statements.

    Returns:
        SQL string containing PRAGMA statements for performance optimization

    Configuration:
        - journal_mode=WAL: Write-Ahead Logging for concurrent access
        - synchronous=NORMAL: Balance between safety and performance
        - foreign_keys=ON: Enforce foreign key constraints
        - temp_store=MEMORY: Use memory for temporary storage
        - cache_size=-64000: 64MB cache (negative = KB)
        - mmap_size=268435456: 256MB memory-mapped I/O
    """
    return """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA temp_store = MEMORY;
PRAGMA cache_size = -64000;
PRAGMA mmap_size = 268435456;
"""


def init_database(db_path: Optional[str | Path] = None) -> None:
    """Initialize cache database with schema.

    Creates the database file and applies the schema. This function is
    idempotent - it can be called multiple times safely.

    Args:
        db_path: Path to database file. If None, uses default location
                 at ~/.skillmeat/cache.db

    Raises:
        sqlite3.Error: If database creation or schema application fails
        IOError: If directory creation fails

    Example:
        >>> from skillmeat.cache.schema import init_database
        >>> init_database()  # Uses default location
        >>> init_database("/custom/path/cache.db")  # Custom location
    """
    # Resolve database path
    if db_path is None:
        config_dir = Path.home() / ".skillmeat" / "cache"
        config_dir.mkdir(parents=True, exist_ok=True)
        db_path = config_dir / "cache.db"
    else:
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

    # Connect and initialize
    conn = sqlite3.connect(str(db_path))
    try:
        # Apply PRAGMA settings
        conn.executescript(get_pragma_sql())

        # Apply schema
        conn.executescript(get_schema_sql())

        # Initialize cache metadata
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO cache_metadata (key, value)
            VALUES ('schema_version', ?)
            """,
            (SCHEMA_VERSION,),
        )

        conn.commit()
    finally:
        conn.close()


def get_engine(db_path: Optional[str | Path] = None) -> sqlite3.Connection:
    """Get SQLite database connection with proper settings.

    Creates a connection with:
    - Row factory for dict-like access
    - Foreign key enforcement
    - WAL mode for concurrency
    - Optimized PRAGMA settings

    Args:
        db_path: Path to database file. If None, uses default location
                 at ~/.skillmeat/cache.db

    Returns:
        sqlite3.Connection with optimal settings configured

    Raises:
        sqlite3.Error: If connection fails

    Example:
        >>> from skillmeat.cache.schema import get_engine
        >>> conn = get_engine()
        >>> try:
        ...     cursor = conn.cursor()
        ...     cursor.execute("SELECT * FROM projects")
        ...     projects = cursor.fetchall()
        ... finally:
        ...     conn.close()

    Note:
        For SQLAlchemy integration (TASK-1.3), use the create_engine()
        function in models.py instead. This function is for raw SQLite access.
    """
    # Resolve database path
    if db_path is None:
        db_path = Path.home() / ".skillmeat" / "cache" / "cache.db"
    else:
        db_path = Path(db_path)

    # Ensure database exists
    if not db_path.exists():
        init_database(db_path)

    # Create connection with optimal settings
    conn = sqlite3.connect(
        str(db_path),
        check_same_thread=False,  # Allow multi-threaded access
        timeout=30.0,  # 30 second lock timeout
    )

    # Use Row factory for dict-like access
    conn.row_factory = sqlite3.Row

    # Apply PRAGMA settings
    conn.executescript(get_pragma_sql())

    return conn


def vacuum_database(db_path: Optional[str | Path] = None) -> None:
    """Vacuum database to reclaim space and optimize performance.

    Should be run periodically (weekly/monthly) to:
    - Reclaim space from deleted rows
    - Defragment database file
    - Update internal statistics
    - Optimize query performance

    Args:
        db_path: Path to database file. If None, uses default location

    Raises:
        sqlite3.Error: If vacuum operation fails

    Warning:
        VACUUM requires exclusive lock and creates a full database copy.
        Do not run during high-traffic periods.

    Example:
        >>> from skillmeat.cache.schema import vacuum_database
        >>> vacuum_database()  # Optimize default database
    """
    conn = get_engine(db_path)
    try:
        # VACUUM cannot be run in a transaction
        conn.isolation_level = None
        conn.execute("VACUUM")
        conn.execute("ANALYZE")

        # Update metadata
        conn.execute(
            """
            INSERT OR REPLACE INTO cache_metadata (key, value)
            VALUES ('last_vacuum', datetime('now'))
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_schema_version(db_path: Optional[str | Path] = None) -> Optional[str]:
    """Get current schema version from database.

    Args:
        db_path: Path to database file. If None, uses default location

    Returns:
        Schema version string or None if not initialized

    Raises:
        sqlite3.Error: If query fails

    Example:
        >>> from skillmeat.cache.schema import get_schema_version
        >>> version = get_schema_version()
        >>> print(f"Schema version: {version}")
        Schema version: 1.0.0
    """
    conn = get_engine(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM cache_metadata WHERE key = 'schema_version'")
        row = cursor.fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def reset_database(db_path: Optional[str | Path] = None) -> None:
    """Reset database by dropping all tables and reinitializing.

    WARNING: This destroys all cached data. Use only for testing or
    when cache corruption is detected.

    Args:
        db_path: Path to database file. If None, uses default location

    Raises:
        sqlite3.Error: If reset operation fails

    Example:
        >>> from skillmeat.cache.schema import reset_database
        >>> reset_database()  # Drops and recreates all tables
    """
    # Resolve database path
    if db_path is None:
        db_path = Path.home() / ".skillmeat" / "cache" / "cache.db"
    else:
        db_path = Path(db_path)

    if not db_path.exists():
        # Nothing to reset
        init_database(db_path)
        return

    conn = sqlite3.connect(str(db_path))
    try:
        # Drop all tables
        cursor = conn.cursor()

        # Get all table names
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            """
        )
        tables = [row[0] for row in cursor.fetchall()]

        # Drop each table
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")

        conn.commit()
    finally:
        conn.close()

    # Reinitialize with fresh schema
    init_database(db_path)
