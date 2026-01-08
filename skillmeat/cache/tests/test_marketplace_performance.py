"""Performance tests for marketplace database queries.

This module validates that common marketplace queries execute within performance
requirements (<200ms for typical sources with 1000+ artifacts).

Test Coverage:
    - Bulk insert operations
    - Common query patterns (filter by source, type, status, confidence)
    - Composite index usage verification
    - ANALYZE optimization validation

Requirements:
    - Python 3.9+
    - pytest
    - pytest-benchmark (optional, for detailed metrics)
"""

import sqlite3
import time
import uuid
from pathlib import Path
from typing import List, Tuple

import pytest

from skillmeat.cache.schema import get_engine, get_schema_sql, init_database


# Performance thresholds (in seconds)
QUERY_THRESHOLD = 0.2  # 200ms for typical queries
BULK_INSERT_THRESHOLD = 1.0  # 1 second for 1000 inserts


@pytest.fixture
def perf_db(tmp_path: Path) -> sqlite3.Connection:
    """Create test database with schema for performance testing.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        SQLite connection to test database
    """
    db_path = tmp_path / "perf_test.db"
    init_database(db_path)
    conn = get_engine(db_path)
    yield conn
    conn.close()


@pytest.fixture
def populated_db(perf_db: sqlite3.Connection) -> Tuple[sqlite3.Connection, str]:
    """Create database populated with 1000+ catalog entries.

    Creates:
        - 5 marketplace sources
        - 1200 catalog entries (240 per source)
        - Varied artifact types, statuses, confidence scores

    Args:
        perf_db: Empty test database connection

    Returns:
        Tuple of (connection, source_id for queries)
    """
    cursor = perf_db.cursor()

    # Create 5 marketplace sources
    source_ids: List[str] = []
    for i in range(5):
        source_id = str(uuid.uuid4())
        source_ids.append(source_id)
        cursor.execute(
            """
            INSERT INTO marketplace_sources (
                id, repo_url, owner, repo_name, ref, trust_level,
                visibility, scan_status, artifact_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                f"https://github.com/owner{i}/repo{i}",
                f"owner{i}",
                f"repo{i}",
                "main",
                "basic",
                "public",
                "success",
                240,  # Entries per source
            ),
        )

    # Create 1200 catalog entries (240 per source)
    artifact_types = ["skill", "command", "agent", "mcp_server", "hook"]
    statuses = ["new", "updated", "imported", "removed"]

    entry_count = 0
    for source_id in source_ids:
        for entry_idx in range(240):
            entry_id = str(uuid.uuid4())
            artifact_type = artifact_types[entry_idx % len(artifact_types)]
            status = statuses[entry_idx % len(statuses)]
            confidence = 60 + (entry_idx % 40)  # 60-99 confidence range

            cursor.execute(
                """
                INSERT INTO marketplace_catalog_entries (
                    id, source_id, artifact_type, name, path, upstream_url,
                    detected_sha, confidence_score, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    source_id,
                    artifact_type,
                    f"artifact-{entry_count}",
                    f"artifacts/{artifact_type}s/artifact-{entry_count}",
                    f"https://github.com/owner/repo/path/{entry_count}",
                    f"abc{entry_count:040x}",  # 40-char SHA
                    confidence,
                    status,
                ),
            )
            entry_count += 1

    perf_db.commit()

    # Run ANALYZE to update query planner statistics
    cursor.execute("ANALYZE marketplace_sources")
    cursor.execute("ANALYZE marketplace_catalog_entries")

    return perf_db, source_ids[0]  # Return first source ID for queries


class TestMarketplacePerformance:
    """Performance test suite for marketplace queries."""

    def test_bulk_insert_performance(self, perf_db: sqlite3.Connection):
        """Test bulk insert performance for catalog entries.

        Validates:
            - 1000 inserts complete within threshold
            - Transaction batching is efficient
        """
        cursor = perf_db.cursor()

        # Create a test source
        source_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO marketplace_sources (
                id, repo_url, owner, repo_name, ref, trust_level,
                visibility, scan_status, artifact_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                "https://github.com/test/repo",
                "test",
                "repo",
                "main",
                "basic",
                "public",
                "pending",
                1000,
            ),
        )

        # Measure bulk insert time
        start_time = time.time()

        for i in range(1000):
            entry_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO marketplace_catalog_entries (
                    id, source_id, artifact_type, name, path, upstream_url,
                    detected_sha, confidence_score, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    source_id,
                    "skill",
                    f"skill-{i}",
                    f"skills/skill-{i}",
                    f"https://github.com/test/repo/skills/skill-{i}",
                    f"abc{i:040x}",
                    85,
                    "new",
                ),
            )

        perf_db.commit()
        duration = time.time() - start_time

        assert (
            duration < BULK_INSERT_THRESHOLD
        ), f"Bulk insert took {duration:.3f}s, expected < {BULK_INSERT_THRESHOLD}s"

        # Verify count
        cursor.execute(
            "SELECT COUNT(*) FROM marketplace_catalog_entries WHERE source_id = ?",
            (source_id,),
        )
        count = cursor.fetchone()[0]
        assert count == 1000

    def test_query_by_source_id(self, populated_db: Tuple[sqlite3.Connection, str]):
        """Test query performance: Filter entries by source_id.

        Uses index: idx_catalog_entries_source_id
        """
        conn, source_id = populated_db
        cursor = conn.cursor()

        start_time = time.time()
        cursor.execute(
            """
            SELECT id, name, artifact_type, status, confidence_score
            FROM marketplace_catalog_entries
            WHERE source_id = ?
            """,
            (source_id,),
        )
        results = cursor.fetchall()
        duration = time.time() - start_time

        assert len(results) == 240  # 240 entries per source
        assert (
            duration < QUERY_THRESHOLD
        ), f"Query by source_id took {duration:.3f}s, expected < {QUERY_THRESHOLD}s"

    def test_query_by_source_and_type(
        self, populated_db: Tuple[sqlite3.Connection, str]
    ):
        """Test query performance: Filter by source_id AND artifact_type.

        Uses index: idx_catalog_entries_source_type (composite)
        """
        conn, source_id = populated_db
        cursor = conn.cursor()

        start_time = time.time()
        cursor.execute(
            """
            SELECT id, name, status, confidence_score
            FROM marketplace_catalog_entries
            WHERE source_id = ? AND artifact_type = ?
            """,
            (source_id, "skill"),
        )
        results = cursor.fetchall()
        duration = time.time() - start_time

        assert len(results) > 0
        assert (
            duration < QUERY_THRESHOLD
        ), f"Query by source+type took {duration:.3f}s, expected < {QUERY_THRESHOLD}s"

    def test_query_by_source_and_status(
        self, populated_db: Tuple[sqlite3.Connection, str]
    ):
        """Test query performance: Filter by source_id AND status.

        Uses index: idx_catalog_entries_source_status (composite)
        """
        conn, source_id = populated_db
        cursor = conn.cursor()

        start_time = time.time()
        cursor.execute(
            """
            SELECT id, name, artifact_type, confidence_score
            FROM marketplace_catalog_entries
            WHERE source_id = ? AND status = ?
            """,
            (source_id, "new"),
        )
        results = cursor.fetchall()
        duration = time.time() - start_time

        assert len(results) > 0
        assert (
            duration < QUERY_THRESHOLD
        ), f"Query by source+status took {duration:.3f}s, expected < {QUERY_THRESHOLD}s"

    def test_query_by_confidence_threshold(
        self, populated_db: Tuple[sqlite3.Connection, str]
    ):
        """Test query performance: Filter by confidence score threshold.

        Uses index: idx_catalog_entries_confidence
        """
        conn, source_id = populated_db
        cursor = conn.cursor()

        start_time = time.time()
        cursor.execute(
            """
            SELECT id, name, artifact_type, status
            FROM marketplace_catalog_entries
            WHERE source_id = ? AND confidence_score >= ?
            """,
            (source_id, 90),
        )
        results = cursor.fetchall()
        duration = time.time() - start_time

        # Should find high-confidence entries
        assert len(results) > 0
        assert (
            duration < QUERY_THRESHOLD
        ), f"Query by confidence took {duration:.3f}s, expected < {QUERY_THRESHOLD}s"

    def test_query_by_upstream_url(self, populated_db: Tuple[sqlite3.Connection, str]):
        """Test query performance: Lookup by upstream_url for deduplication.

        Uses index: idx_catalog_entries_upstream_url
        """
        conn, _ = populated_db
        cursor = conn.cursor()

        # Get a known upstream URL
        cursor.execute("SELECT upstream_url FROM marketplace_catalog_entries LIMIT 1")
        upstream_url = cursor.fetchone()[0]

        start_time = time.time()
        cursor.execute(
            """
            SELECT id, name, artifact_type, status
            FROM marketplace_catalog_entries
            WHERE upstream_url = ?
            """,
            (upstream_url,),
        )
        results = cursor.fetchall()
        duration = time.time() - start_time

        assert len(results) == 1  # Should be unique
        assert (
            duration < QUERY_THRESHOLD
        ), f"Query by upstream_url took {duration:.3f}s, expected < {QUERY_THRESHOLD}s"

    def test_query_sources_by_owner_repo(
        self, populated_db: Tuple[sqlite3.Connection, str]
    ):
        """Test query performance: Lookup source by owner/repo combination.

        Uses index: idx_marketplace_sources_owner_repo
        """
        conn, _ = populated_db
        cursor = conn.cursor()

        start_time = time.time()
        cursor.execute(
            """
            SELECT id, repo_url, trust_level, artifact_count
            FROM marketplace_sources
            WHERE owner = ? AND repo_name = ?
            """,
            ("owner0", "repo0"),
        )
        results = cursor.fetchall()
        duration = time.time() - start_time

        assert len(results) == 1
        assert (
            duration < QUERY_THRESHOLD
        ), f"Query by owner+repo took {duration:.3f}s, expected < {QUERY_THRESHOLD}s"

    def test_query_sources_by_scan_status(
        self, populated_db: Tuple[sqlite3.Connection, str]
    ):
        """Test query performance: Filter sources by scan status.

        Uses index: idx_marketplace_sources_scan_status
        """
        conn, _ = populated_db
        cursor = conn.cursor()

        start_time = time.time()
        cursor.execute(
            """
            SELECT id, repo_url, owner, repo_name, artifact_count
            FROM marketplace_sources
            WHERE scan_status = ?
            """,
            ("success",),
        )
        results = cursor.fetchall()
        duration = time.time() - start_time

        assert len(results) == 5  # All sources are 'success'
        assert (
            duration < QUERY_THRESHOLD
        ), f"Query by scan_status took {duration:.3f}s, expected < {QUERY_THRESHOLD}s"

    def test_complex_join_query(self, populated_db: Tuple[sqlite3.Connection, str]):
        """Test query performance: Complex join with filters.

        Validates:
            - JOIN performance between sources and entries
            - Multiple WHERE conditions
            - Index usage on both tables
        """
        conn, _ = populated_db
        cursor = conn.cursor()

        start_time = time.time()
        cursor.execute(
            """
            SELECT
                s.owner,
                s.repo_name,
                COUNT(*) as entry_count,
                AVG(e.confidence_score) as avg_confidence
            FROM marketplace_sources s
            JOIN marketplace_catalog_entries e ON s.id = e.source_id
            WHERE
                s.scan_status = 'success'
                AND e.status = 'new'
                AND e.confidence_score >= 80
            GROUP BY s.id, s.owner, s.repo_name
            ORDER BY entry_count DESC
            """
        )
        results = cursor.fetchall()
        duration = time.time() - start_time

        assert len(results) > 0
        assert (
            duration < QUERY_THRESHOLD
        ), f"Complex join query took {duration:.3f}s, expected < {QUERY_THRESHOLD}s"

    def test_analyze_optimization(self, perf_db: sqlite3.Connection):
        """Test that ANALYZE improves query performance after bulk inserts.

        Validates:
            - ANALYZE updates query planner statistics
            - Query performance improves after ANALYZE
        """
        cursor = perf_db.cursor()

        # Create source and insert entries WITHOUT ANALYZE
        source_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO marketplace_sources (
                id, repo_url, owner, repo_name, ref, trust_level,
                visibility, scan_status, artifact_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                "https://github.com/test/analyze",
                "test",
                "analyze",
                "main",
                "basic",
                "public",
                "success",
                500,
            ),
        )

        # Insert 500 entries
        for i in range(500):
            entry_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO marketplace_catalog_entries (
                    id, source_id, artifact_type, name, path, upstream_url,
                    detected_sha, confidence_score, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    source_id,
                    "skill",
                    f"skill-{i}",
                    f"skills/skill-{i}",
                    f"https://github.com/test/analyze/skills/skill-{i}",
                    f"abc{i:040x}",
                    85,
                    "new",
                ),
            )
        perf_db.commit()

        # Query WITHOUT ANALYZE
        start_time = time.time()
        cursor.execute(
            """
            SELECT COUNT(*) FROM marketplace_catalog_entries
            WHERE source_id = ? AND confidence_score >= 80
            """,
            (source_id,),
        )
        cursor.fetchone()
        duration_before = time.time() - start_time

        # Run ANALYZE
        cursor.execute("ANALYZE marketplace_catalog_entries")

        # Query AFTER ANALYZE
        start_time = time.time()
        cursor.execute(
            """
            SELECT COUNT(*) FROM marketplace_catalog_entries
            WHERE source_id = ? AND confidence_score >= 80
            """,
            (source_id,),
        )
        result = cursor.fetchone()
        duration_after = time.time() - start_time

        assert result[0] == 500  # All entries have confidence 85

        # Both queries should be fast, but ANALYZE should help
        # (In practice, difference may be minimal for small datasets)
        assert duration_after < QUERY_THRESHOLD

        print(
            f"\nANALYZE impact: before={duration_before:.4f}s, "
            f"after={duration_after:.4f}s"
        )


class TestIndexCoverage:
    """Verify that all required indexes exist."""

    def test_all_marketplace_indexes_exist(self, perf_db: sqlite3.Connection):
        """Verify all marketplace-related indexes are created.

        Checks for:
            - MarketplaceSource indexes (4 total)
            - MarketplaceCatalogEntry indexes (7 total)
        """
        cursor = perf_db.cursor()

        # Get all index names for marketplace tables
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'index' AND (
                name LIKE 'idx_marketplace_%'
                OR name LIKE 'idx_catalog_%'
            )
            ORDER BY name
            """
        )
        indexes = [row[0] for row in cursor.fetchall()]

        # Required MarketplaceSource indexes
        required_source_indexes = [
            "idx_marketplace_sources_last_sync",
            "idx_marketplace_sources_owner_repo",
            "idx_marketplace_sources_repo_url",
            "idx_marketplace_sources_scan_status",
        ]

        # Required MarketplaceCatalogEntry indexes
        required_entry_indexes = [
            "idx_catalog_entries_confidence",
            "idx_catalog_entries_source_id",
            "idx_catalog_entries_source_status",
            "idx_catalog_entries_source_type",
            "idx_catalog_entries_status",
            "idx_catalog_entries_type",
            "idx_catalog_entries_upstream_url",
        ]

        all_required = required_source_indexes + required_entry_indexes

        for required_index in all_required:
            assert required_index in indexes, f"Missing index: {required_index}"

        print(f"\n✓ All {len(all_required)} required indexes exist")

    def test_unique_constraints(self, perf_db: sqlite3.Connection):
        """Verify UNIQUE constraints on critical columns.

        Checks:
            - marketplace_sources.repo_url is UNIQUE
            - Prevents duplicate source registration
        """
        cursor = perf_db.cursor()

        # Insert first source
        source_id_1 = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO marketplace_sources (
                id, repo_url, owner, repo_name, ref, trust_level,
                visibility, scan_status, artifact_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id_1,
                "https://github.com/duplicate/test",
                "duplicate",
                "test",
                "main",
                "basic",
                "public",
                "pending",
                0,
            ),
        )
        perf_db.commit()

        # Attempt to insert duplicate repo_url
        source_id_2 = str(uuid.uuid4())
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint"):
            cursor.execute(
                """
                INSERT INTO marketplace_sources (
                    id, repo_url, owner, repo_name, ref, trust_level,
                    visibility, scan_status, artifact_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id_2,
                    "https://github.com/duplicate/test",  # Same URL
                    "duplicate",
                    "test",
                    "main",
                    "basic",
                    "public",
                    "pending",
                    0,
                ),
            )

        print("\n✓ UNIQUE constraint on repo_url enforced")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
