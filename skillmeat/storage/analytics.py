"""Analytics database management for SkillMeat.

Manages SQLite database for tracking artifact usage, deployments, updates, and
other analytics events. Provides retention policy management and data aggregation.
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class AnalyticsDB:
    """Manages SQLite analytics database with migrations and retention.

    The analytics database tracks usage events for artifacts across collections
    and projects, enabling insights into artifact popularity, deployment patterns,
    and usage trends.

    Database Features:
    - WAL mode for better concurrency
    - Version-based migration system
    - Automatic retention policy enforcement
    - Events table for raw event data
    - Usage summary table for aggregated statistics

    Thread Safety:
        The connection is created with check_same_thread=False to allow
        multi-threaded access. For production use with heavy concurrency,
        consider using connection pooling.

    Example:
        >>> db = AnalyticsDB()
        >>> db.record_event(
        ...     event_type="deploy",
        ...     artifact_name="canvas",
        ...     artifact_type="skill",
        ...     collection_name="default",
        ...     project_path="/home/user/project"
        ... )
        >>> db.cleanup_old_events(days=90)
        >>> db.close()
    """

    SCHEMA_VERSION = 1  # Increment on schema changes
    DEFAULT_RETENTION_DAYS = 90
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_MS = 100  # Initial retry delay in milliseconds

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize analytics database connection.

        Args:
            db_path: Path to SQLite database file. If None, uses default
                location at ~/.skillmeat/analytics.db

        Raises:
            sqlite3.Error: If database connection or initialization fails
        """
        if db_path is None:
            # Default location
            config_dir = Path.home() / ".skillmeat"
            config_dir.mkdir(parents=True, exist_ok=True)
            db_path = config_dir / "analytics.db"

        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None

        # Initialize database
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database with WAL mode and schema.

        Sets up:
        - SQLite connection with WAL journal mode
        - Foreign key enforcement
        - Row factory for dict-like access
        - Schema migrations

        Raises:
            sqlite3.Error: If database initialization fails
        """
        self.connection = sqlite3.connect(
            str(self.db_path), check_same_thread=False  # Allow multi-threaded access
        )

        # Use Row factory for dict-like access
        self.connection.row_factory = sqlite3.Row

        # Enable WAL mode for better concurrency
        # WAL allows multiple readers and one writer simultaneously
        self.connection.execute("PRAGMA journal_mode=WAL")

        # Enable foreign keys
        self.connection.execute("PRAGMA foreign_keys=ON")

        # Apply migrations
        self._apply_migrations()

    def _apply_migrations(self) -> None:
        """Apply database migrations in order.

        Creates migrations tracking table and applies any pending migrations
        based on the current schema version.

        Raises:
            sqlite3.Error: If migration fails
        """
        # Create migrations table
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS migrations (
                version INTEGER PRIMARY KEY,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Get current version
        cursor = self.connection.execute("SELECT MAX(version) FROM migrations")
        result = cursor.fetchone()
        current_version = result[0] if result[0] is not None else 0

        # Apply migrations in order
        migrations = self._get_migrations()
        for version, migration_sql in sorted(migrations.items()):
            if version > current_version:
                # Execute migration
                self.connection.executescript(migration_sql)

                # Record migration
                self.connection.execute(
                    "INSERT INTO migrations (version) VALUES (?)", (version,)
                )

                self.connection.commit()

    def _get_migrations(self) -> Dict[int, str]:
        """Return all migrations indexed by version.

        Returns:
            Dictionary mapping version number to SQL migration script

        Note:
            When adding new migrations:
            1. Increment SCHEMA_VERSION constant
            2. Add new entry with incremented version number
            3. Test migration against existing databases
        """
        return {
            1: """
                -- Initial schema

                -- Events table: Stores all analytics events
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,      -- 'deploy', 'update', 'sync', 'remove', 'search'
                    artifact_name TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,   -- 'skill', 'command', 'agent'
                    collection_name TEXT,
                    project_path TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT                  -- JSON blob for event-specific data
                );

                -- Indexes for efficient querying
                CREATE INDEX IF NOT EXISTS idx_event_type
                    ON events(event_type);

                CREATE INDEX IF NOT EXISTS idx_artifact_name
                    ON events(artifact_name);

                CREATE INDEX IF NOT EXISTS idx_timestamp
                    ON events(timestamp);

                CREATE INDEX IF NOT EXISTS idx_collection
                    ON events(collection_name);

                -- Composite index for common queries
                CREATE INDEX IF NOT EXISTS idx_artifact_type_name
                    ON events(artifact_type, artifact_name);

                -- Usage summary table: Aggregated statistics for fast lookups
                CREATE TABLE IF NOT EXISTS usage_summary (
                    artifact_name TEXT PRIMARY KEY,
                    artifact_type TEXT NOT NULL,
                    first_used DATETIME,
                    last_used DATETIME,
                    deploy_count INTEGER DEFAULT 0,
                    update_count INTEGER DEFAULT 0,
                    sync_count INTEGER DEFAULT 0,
                    remove_count INTEGER DEFAULT 0,
                    search_count INTEGER DEFAULT 0,
                    total_events INTEGER DEFAULT 0
                );

                -- Indexes for usage summary
                CREATE INDEX IF NOT EXISTS idx_last_used
                    ON usage_summary(last_used);

                CREATE INDEX IF NOT EXISTS idx_total_events
                    ON usage_summary(total_events);

                CREATE INDEX IF NOT EXISTS idx_usage_artifact_type
                    ON usage_summary(artifact_type);
            """
        }

    def record_event(
        self,
        event_type: str,
        artifact_name: str,
        artifact_type: str,
        collection_name: Optional[str] = None,
        project_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Record an analytics event.

        Args:
            event_type: Type of event (deploy, update, sync, remove, search)
            artifact_name: Name of artifact
            artifact_type: Type of artifact (skill, command, agent)
            collection_name: Name of collection (optional)
            project_path: Path to project (optional)
            metadata: Additional event-specific data (optional)

        Returns:
            ID of newly created event record

        Raises:
            sqlite3.Error: If database operation fails
            ValueError: If event_type or artifact_type is invalid

        Example:
            >>> db.record_event(
            ...     event_type="deploy",
            ...     artifact_name="canvas",
            ...     artifact_type="skill",
            ...     collection_name="default",
            ...     metadata={"version": "1.2.0"}
            ... )
        """
        # Validate event types
        valid_event_types = {"deploy", "update", "sync", "remove", "search"}
        if event_type not in valid_event_types:
            raise ValueError(
                f"Invalid event_type '{event_type}'. "
                f"Must be one of: {', '.join(sorted(valid_event_types))}"
            )

        valid_artifact_types = {"skill", "command", "agent"}
        if artifact_type not in valid_artifact_types:
            raise ValueError(
                f"Invalid artifact_type '{artifact_type}'. "
                f"Must be one of: {', '.join(sorted(valid_artifact_types))}"
            )

        metadata_json = json.dumps(metadata) if metadata else None

        # Insert event with retry logic for database locked scenarios
        cursor = self._execute_with_retry(
            """
            INSERT INTO events
                (event_type, artifact_name, artifact_type,
                 collection_name, project_path, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                event_type,
                artifact_name,
                artifact_type,
                collection_name,
                project_path,
                metadata_json,
            ),
        )

        # Update usage summary
        self._update_usage_summary(event_type, artifact_name, artifact_type)

        self.connection.commit()

        return cursor.lastrowid

    def _execute_with_retry(
        self, sql: str, parameters: Tuple = (), max_retries: Optional[int] = None
    ) -> sqlite3.Cursor:
        """Execute SQL with exponential backoff retry on database locked errors.

        Args:
            sql: SQL statement to execute
            parameters: Parameters for SQL statement
            max_retries: Maximum retry attempts (uses MAX_RETRY_ATTEMPTS if None)

        Returns:
            Cursor from successful execution

        Raises:
            sqlite3.OperationalError: If database remains locked after all retries
        """
        if max_retries is None:
            max_retries = self.MAX_RETRY_ATTEMPTS

        last_error = None
        delay_ms = self.RETRY_DELAY_MS

        for attempt in range(max_retries):
            try:
                return self.connection.execute(sql, parameters)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    last_error = e
                    if attempt < max_retries - 1:
                        # Exponential backoff
                        time.sleep(delay_ms / 1000.0)
                        delay_ms *= 2
                else:
                    # Different operational error, re-raise immediately
                    raise

        # All retries exhausted
        raise sqlite3.OperationalError(
            f"Database locked after {max_retries} attempts"
        ) from last_error

    def _update_usage_summary(
        self, event_type: str, artifact_name: str, artifact_type: str
    ) -> None:
        """Update usage summary table for an event.

        Uses UPSERT (INSERT ... ON CONFLICT) to atomically update or create
        the usage summary record.

        Args:
            event_type: Type of event (deploy, update, sync, remove, search)
            artifact_name: Name of artifact
            artifact_type: Type of artifact

        Raises:
            sqlite3.Error: If database operation fails
        """
        # Map event type to counter column
        counter_col = f"{event_type}_count"

        # Use UPSERT to atomically update or insert
        self._execute_with_retry(
            f"""
            INSERT INTO usage_summary
                (artifact_name, artifact_type, first_used, last_used,
                 {counter_col}, total_events)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, 1)
            ON CONFLICT(artifact_name) DO UPDATE SET
                last_used = CURRENT_TIMESTAMP,
                {counter_col} = {counter_col} + 1,
                total_events = total_events + 1
        """,
            (artifact_name, artifact_type),
        )

    def get_events(
        self,
        event_type: Optional[str] = None,
        artifact_name: Optional[str] = None,
        artifact_type: Optional[str] = None,
        collection_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query events with optional filtering.

        Args:
            event_type: Filter by event type (optional)
            artifact_name: Filter by artifact name (optional)
            artifact_type: Filter by artifact type (optional)
            collection_name: Filter by collection name (optional)
            limit: Maximum number of events to return
            offset: Number of events to skip

        Returns:
            List of event dictionaries, ordered by timestamp (newest first)

        Example:
            >>> events = db.get_events(
            ...     artifact_name="canvas",
            ...     event_type="deploy",
            ...     limit=10
            ... )
        """
        query = "SELECT * FROM events WHERE 1=1"
        params = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        if artifact_name:
            query += " AND artifact_name = ?"
            params.append(artifact_name)

        if artifact_type:
            query += " AND artifact_type = ?"
            params.append(artifact_type)

        if collection_name:
            query += " AND collection_name = ?"
            params.append(collection_name)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.connection.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_usage_summary(
        self, artifact_name: Optional[str] = None, artifact_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get usage summary statistics.

        Args:
            artifact_name: Filter by artifact name (optional)
            artifact_type: Filter by artifact type (optional)

        Returns:
            List of usage summary dictionaries

        Example:
            >>> summary = db.get_usage_summary(artifact_type="skill")
            >>> for artifact in summary:
            ...     print(f"{artifact['artifact_name']}: {artifact['total_events']} events")
        """
        query = "SELECT * FROM usage_summary WHERE 1=1"
        params = []

        if artifact_name:
            query += " AND artifact_name = ?"
            params.append(artifact_name)

        if artifact_type:
            query += " AND artifact_type = ?"
            params.append(artifact_type)

        query += " ORDER BY total_events DESC"

        cursor = self.connection.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_top_artifacts(
        self, artifact_type: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top artifacts by total events.

        Args:
            artifact_type: Filter by artifact type (optional)
            limit: Maximum number of artifacts to return

        Returns:
            List of usage summary dictionaries, ordered by total events

        Example:
            >>> top_skills = db.get_top_artifacts(artifact_type="skill", limit=5)
        """
        query = "SELECT * FROM usage_summary WHERE 1=1"
        params = []

        if artifact_type:
            query += " AND artifact_type = ?"
            params.append(artifact_type)

        query += " ORDER BY total_events DESC LIMIT ?"
        params.append(limit)

        cursor = self.connection.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def cleanup_old_events(self, days: int = DEFAULT_RETENTION_DAYS) -> int:
        """Remove events older than specified days (retention policy).

        This operation does NOT delete from usage_summary table, which retains
        aggregated statistics even after detailed events are removed.

        Args:
            days: Number of days to retain events (0 = keep forever)

        Returns:
            Number of events deleted

        Raises:
            ValueError: If days is negative

        Example:
            >>> deleted = db.cleanup_old_events(days=90)
            >>> print(f"Deleted {deleted} old events")
        """
        if days < 0:
            raise ValueError("Retention days must be non-negative")

        if days == 0:
            # Keep forever
            return 0

        cutoff = datetime.now() - timedelta(days=days)

        cursor = self._execute_with_retry(
            """
            DELETE FROM events
            WHERE timestamp < ?
        """,
            (cutoff,),
        )

        deleted = cursor.rowcount
        self.connection.commit()

        return deleted

    def vacuum(self) -> None:
        """Vacuum database to reclaim space after deletions.

        Should be called after cleanup_old_events() to reclaim disk space
        from deleted records.

        Note:
            VACUUM requires exclusive database access and can take time on
            large databases. Consider running during maintenance windows.

        Raises:
            sqlite3.Error: If vacuum operation fails
        """
        # Close and reopen connection as VACUUM cannot run in a transaction
        self.connection.commit()
        self.connection.execute("VACUUM")

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Dictionary containing:
            - total_events: Total number of events
            - total_artifacts: Total unique artifacts tracked
            - event_type_counts: Count by event type
            - artifact_type_counts: Count by artifact type
            - oldest_event: Timestamp of oldest event
            - newest_event: Timestamp of newest event
            - db_size_bytes: Database file size in bytes

        Example:
            >>> stats = db.get_stats()
            >>> print(f"Total events: {stats['total_events']}")
        """
        stats = {}

        # Total events
        cursor = self.connection.execute("SELECT COUNT(*) FROM events")
        stats["total_events"] = cursor.fetchone()[0]

        # Total unique artifacts
        cursor = self.connection.execute("SELECT COUNT(*) FROM usage_summary")
        stats["total_artifacts"] = cursor.fetchone()[0]

        # Event type counts
        cursor = self.connection.execute(
            """
            SELECT event_type, COUNT(*) as count
            FROM events
            GROUP BY event_type
        """
        )
        stats["event_type_counts"] = {row[0]: row[1] for row in cursor.fetchall()}

        # Artifact type counts
        cursor = self.connection.execute(
            """
            SELECT artifact_type, COUNT(DISTINCT artifact_name) as count
            FROM usage_summary
            GROUP BY artifact_type
        """
        )
        stats["artifact_type_counts"] = {row[0]: row[1] for row in cursor.fetchall()}

        # Oldest and newest events
        cursor = self.connection.execute(
            """
            SELECT MIN(timestamp), MAX(timestamp)
            FROM events
        """
        )
        oldest, newest = cursor.fetchone()
        stats["oldest_event"] = oldest
        stats["newest_event"] = newest

        # Database file size
        if self.db_path.exists():
            stats["db_size_bytes"] = self.db_path.stat().st_size
        else:
            stats["db_size_bytes"] = 0

        return stats

    def close(self) -> None:
        """Close database connection.

        Should be called when done with the database to ensure all changes
        are committed and resources are released.
        """
        if self.connection:
            self.connection.commit()
            self.connection.close()
            self.connection = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures connection is closed."""
        self.close()
        return False

    def __del__(self):
        """Destructor - ensures connection is closed."""
        self.close()
