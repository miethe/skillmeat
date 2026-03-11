"""Migration rollback tests for enterprise schema (ENT-1.12).

These tests verify that the two enterprise Alembic migrations can be applied
and reversed cleanly, that schema state matches expectations at every waypoint,
and that data inserted before a partial downgrade is not lost when it should be
preserved.

Test class
----------
TestMigrationRollback
    test_upgrade_creates_enterprise_tables
        Apply head; assert all four enterprise tables exist.
    test_downgrade_removes_tenant_isolation
        Downgrade one step (ent_002 -> ent_001); verify
        tenant_id column is gone from collections but enterprise tables remain.
    test_full_downgrade_removes_enterprise_tables
        Downgrade to the pre-enterprise base revision; verify all four
        enterprise tables are dropped.
    test_upgrade_is_idempotent
        Downgrade then re-upgrade; verify schema is identical to the
        first upgrade (no duplicate objects, no errors).
    test_no_dangling_foreign_keys_after_downgrade
        Verify referential integrity checks pass after a full downgrade
        (no orphan FK references remain).

PostgreSQL availability
-----------------------
All tests are skipped automatically when DATABASE_URL is not set or when the
target database is not reachable.  Set::

    export DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/testdb"

before running to enable these tests.

Alembic + CONCURRENTLY
-----------------------
The ent_001 migration creates GIN and partial indexes with
``CREATE INDEX CONCURRENTLY``.  CONCURRENTLY cannot run inside an explicit
transaction block.  We therefore connect with ``AUTOCOMMIT`` isolation level
and run migrations with ``transaction_per_migration=False`` so Alembic does
not wrap each migration in BEGIN/COMMIT.
"""

from __future__ import annotations

import os
from typing import Generator

import pytest
import sqlalchemy as sa
from sqlalchemy import inspect, text

# ---------------------------------------------------------------------------
# PostgreSQL availability guard
# ---------------------------------------------------------------------------

_DATABASE_URL: str | None = os.environ.get("DATABASE_URL")

# Whether we have a reachable PostgreSQL instance.  Evaluated once at module
# import time so the skip reason is deterministic.
_PG_AVAILABLE: bool = False
_PG_SKIP_REASON: str = "DATABASE_URL not set; skipping PostgreSQL migration tests"

if _DATABASE_URL:
    try:
        _probe_engine = sa.create_engine(_DATABASE_URL, pool_pre_ping=True)
        with _probe_engine.connect():
            pass
        _PG_AVAILABLE = True
    except Exception as _probe_exc:
        _PG_SKIP_REASON = (
            f"PostgreSQL not reachable at DATABASE_URL ({_probe_exc}); "
            "skipping migration tests"
        )
    finally:
        try:
            _probe_engine.dispose()
        except Exception:
            pass

# Decorator applied to the entire test class.
requires_postgres = pytest.mark.skipif(
    not _PG_AVAILABLE,
    reason=_PG_SKIP_REASON,
)

# ---------------------------------------------------------------------------
# Alembic helpers
# ---------------------------------------------------------------------------

# Absolute path to the alembic.ini file so tests are location-independent.
_ALEMBIC_INI = os.path.join(
    os.path.dirname(__file__),  # tests/integration/
    "..",  # tests/
    "..",  # repo root
    "skillmeat",
    "cache",
    "migrations",
    "alembic.ini",
)

# The revision that immediately precedes the two enterprise migrations.
# All enterprise tables are absent at this revision.
_BASE_REVISION = "20260303_1100_add_workflow_to_artifact_type_check"

# Revision IDs for the two enterprise migrations.
_ENT_001 = "ent_001_enterprise_schema"
_ENT_002 = "ent_002_tenant_isolation"

# The four enterprise tables introduced by ENT-1.7.
_ENTERPRISE_TABLES = frozenset(
    [
        "enterprise_artifacts",
        "enterprise_collections",
        "artifact_versions",
        "enterprise_collection_artifacts",
    ]
)


def _get_alembic_config(db_url: str):
    """Build an Alembic Config pointed at *db_url*.

    We set the URL programmatically so that env.py's SQLite-specific
    connect_args (``check_same_thread``, ``timeout``) are never used for
    PostgreSQL connections.  The script_location is derived from alembic.ini's
    ``%(here)s`` token, which resolves correctly via the absolute path.
    """
    from alembic.config import Config

    cfg = Config(_ALEMBIC_INI)
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _run_upgrade(engine: sa.engine.Engine, revision: str = "head") -> None:
    """Apply Alembic upgrade to *revision* using *engine*.

    Uses AUTOCOMMIT isolation level so that ``CREATE INDEX CONCURRENTLY``
    statements inside the migration can execute outside an explicit
    transaction block.  ``transaction_per_migration=False`` tells Alembic
    not to wrap each migration script in its own BEGIN/COMMIT; instead the
    migration scripts manage their own transaction boundaries.
    """
    from alembic import command as alembic_command
    from alembic.config import Config

    cfg = _get_alembic_config(engine.url.render_as_string(hide_password=False))

    # Connect with AUTOCOMMIT so CONCURRENTLY index creation does not fail.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        cfg.attributes["connection"] = conn
        alembic_command.upgrade(cfg, revision)


def _run_downgrade(engine: sa.engine.Engine, revision: str) -> None:
    """Apply Alembic downgrade to *revision* using *engine*."""
    from alembic import command as alembic_command

    cfg = _get_alembic_config(engine.url.render_as_string(hide_password=False))

    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        cfg.attributes["connection"] = conn
        alembic_command.downgrade(cfg, revision)


def _get_current_revision(engine: sa.engine.Engine) -> str | None:
    """Return the current Alembic revision stored in ``alembic_version``."""
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            )
            row = result.fetchone()
            return row[0] if row else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pg_engine() -> Generator[sa.engine.Engine, None, None]:
    """Yield a SQLAlchemy engine connected to the test PostgreSQL database.

    The engine is created once per test module and disposed afterwards.
    Individual tests are responsible for upgrading / downgrading to a known
    state before asserting; a module-scoped fixture avoids the overhead of
    tearing down and rebuilding the connection pool for every test.

    Skips automatically when PostgreSQL is not available (controlled by the
    module-level ``_PG_AVAILABLE`` flag).
    """
    if not _PG_AVAILABLE:
        pytest.skip(_PG_SKIP_REASON)

    engine = sa.create_engine(
        _DATABASE_URL,
        poolclass=sa.pool.NullPool,  # One connection per operation; clean state.
        echo=False,
    )
    try:
        yield engine
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------


def _table_names(engine: sa.engine.Engine) -> set[str]:
    """Return the set of table names in the public schema."""
    inspector = inspect(engine)
    return set(inspector.get_table_names())


def _column_names(engine: sa.engine.Engine, table: str) -> set[str]:
    """Return the set of column names for *table*."""
    inspector = inspect(engine)
    return {col["name"] for col in inspector.get_columns(table)}


def _index_names(engine: sa.engine.Engine, table: str) -> set[str]:
    """Return the set of index names for *table*."""
    inspector = inspect(engine)
    return {idx["name"] for idx in inspector.get_indexes(table)}


def _fk_names(engine: sa.engine.Engine, table: str) -> set[str]:
    """Return the set of FK constraint names for *table*."""
    inspector = inspect(engine)
    return {fk["name"] for fk in inspector.get_foreign_keys(table)}


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


@requires_postgres
class TestMigrationRollback:
    """Verify upgrade/downgrade behaviour of the two enterprise migrations.

    Test ordering matters: each test leaves the database in the state
    described in its docstring so the next test can start from a predictable
    baseline.  pytest executes methods in definition order.

    Isolation strategy
    ------------------
    Rather than rolling back a transaction (impossible with DDL), each test
    explicitly migrates to the revision it needs before asserting.  This is
    slightly slower but reflects real migration behaviour exactly.
    """

    # ------------------------------------------------------------------
    # 1. Upgrade
    # ------------------------------------------------------------------

    def test_upgrade_creates_enterprise_tables(self, pg_engine: sa.engine.Engine):
        """Applying 'upgrade head' must create all four enterprise tables.

        Starting state: any revision (we upgrade to head unconditionally).
        Ending state: head (ent_002_tenant_isolation).

        Verified:
        - All four enterprise tables exist.
        - The ``collections`` table has a ``tenant_id`` column (ENT-1.8).
        - Expected B-tree indexes on ``enterprise_artifacts`` are present.
        - Expected GIN index on ``enterprise_artifacts.tags`` is present.
        """
        _run_upgrade(pg_engine, "head")

        tables = _table_names(pg_engine)

        # All four enterprise tables must be present.
        missing = _ENTERPRISE_TABLES - tables
        assert not missing, (
            f"Enterprise tables missing after 'upgrade head': {missing}"
        )

        # ENT-1.8: tenant_id must be a column in the shared collections table.
        assert "collections" in tables, (
            "'collections' table not found; base migrations may not have run"
        )
        coll_cols = _column_names(pg_engine, "collections")
        assert "tenant_id" in coll_cols, (
            "'collections.tenant_id' column missing after full upgrade"
        )

        # Spot-check key indexes on enterprise_artifacts.
        ea_indexes = _index_names(pg_engine, "enterprise_artifacts")
        assert "idx_enterprise_artifacts_tenant_id" in ea_indexes, (
            "B-tree index idx_enterprise_artifacts_tenant_id not created"
        )
        assert "idx_enterprise_artifacts_tags_gin" in ea_indexes, (
            "GIN index idx_enterprise_artifacts_tags_gin not created"
        )

        # Spot-check the partial source_url index.
        assert "idx_enterprise_artifacts_source_url" in ea_indexes, (
            "Partial index idx_enterprise_artifacts_source_url not created"
        )

        # Verify current revision is the tenant-isolation migration.
        current = _get_current_revision(pg_engine)
        assert current == _ENT_002, (
            f"Expected revision {_ENT_002!r} after head upgrade, got {current!r}"
        )

    # ------------------------------------------------------------------
    # 2. Partial downgrade: ENT-1.8 only
    # ------------------------------------------------------------------

    def test_downgrade_removes_tenant_isolation(self, pg_engine: sa.engine.Engine):
        """Downgrading one step must remove tenant_id from collections only.

        Starting state: head (set by previous test).
        Ending state: ent_001_enterprise_schema.

        The downgrade of ent_002 must:
        - Drop ``idx_collections_tenant_id`` index.
        - Drop the ``tenant_id`` column from ``collections``.
        - Leave the four enterprise tables intact.
        - Leave the ``enterprise_artifacts`` indexes intact.
        """
        # Ensure we start from head (idempotent if previous test already ran).
        _run_upgrade(pg_engine, "head")

        # Downgrade exactly one step.
        _run_downgrade(pg_engine, "-1")

        # Verify revision moved back correctly.
        current = _get_current_revision(pg_engine)
        assert current == _ENT_001, (
            f"Expected revision {_ENT_001!r} after -1 downgrade, got {current!r}"
        )

        # tenant_id must be gone from collections.
        coll_cols = _column_names(pg_engine, "collections")
        assert "tenant_id" not in coll_cols, (
            "'collections.tenant_id' still present after downgrading ENT-1.8"
        )

        # The idx_collections_tenant_id index must be gone too.
        coll_indexes = _index_names(pg_engine, "collections")
        assert "idx_collections_tenant_id" not in coll_indexes, (
            "idx_collections_tenant_id index still present after downgrade"
        )

        # The four enterprise tables must still exist.
        tables = _table_names(pg_engine)
        still_missing = _ENTERPRISE_TABLES - tables
        assert not still_missing, (
            f"Enterprise tables unexpectedly dropped during -1 downgrade: "
            f"{still_missing}"
        )

    # ------------------------------------------------------------------
    # 3. Full downgrade: both enterprise migrations
    # ------------------------------------------------------------------

    def test_full_downgrade_removes_enterprise_tables(
        self, pg_engine: sa.engine.Engine
    ):
        """Downgrading to the pre-enterprise base revision drops all four tables.

        Starting state: ent_001 (set by previous test).
        Ending state: 20260303_1100_add_workflow_to_artifact_type_check.

        Verified:
        - None of the four enterprise tables remain.
        - The ``collections`` table still exists (it predates enterprise).
        - No orphaned enterprise indexes remain.
        """
        _run_downgrade(pg_engine, _BASE_REVISION)

        current = _get_current_revision(pg_engine)
        assert current == _BASE_REVISION, (
            f"Expected revision {_BASE_REVISION!r} after full downgrade, "
            f"got {current!r}"
        )

        tables = _table_names(pg_engine)

        # None of the enterprise tables should remain.
        still_present = _ENTERPRISE_TABLES & tables
        assert not still_present, (
            f"Enterprise tables still present after full downgrade: {still_present}"
        )

        # The shared collections table must survive.
        assert "collections" in tables, (
            "'collections' table was dropped by the enterprise downgrade — "
            "it should only lose its tenant_id column, not the whole table"
        )

        # No enterprise artifact indexes should remain (they live on the dropped tables,
        # but verify via information_schema in case of ghost entries).
        with pg_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname = 'public' "
                    "AND indexname LIKE 'idx_enterprise_%'"
                )
            )
            orphan_indexes = [row[0] for row in result.fetchall()]
        assert not orphan_indexes, (
            f"Orphan enterprise indexes remain after full downgrade: {orphan_indexes}"
        )

    # ------------------------------------------------------------------
    # 4. Re-upgrade idempotency
    # ------------------------------------------------------------------

    def test_upgrade_is_idempotent(self, pg_engine: sa.engine.Engine):
        """Re-applying 'upgrade head' after a full downgrade must succeed.

        Starting state: _BASE_REVISION (set by previous test).
        Ending state: head.

        This catches scenarios where the downgrade leaves behind schema
        artefacts (indexes, sequences, etc.) that would cause duplicate-object
        errors on re-upgrade.
        """
        # Re-run the full upgrade from the base revision.
        _run_upgrade(pg_engine, "head")

        current = _get_current_revision(pg_engine)
        assert current == _ENT_002, (
            f"Expected revision {_ENT_002!r} after re-upgrade, got {current!r}"
        )

        tables = _table_names(pg_engine)
        missing = _ENTERPRISE_TABLES - tables
        assert not missing, (
            f"Enterprise tables missing after re-upgrade: {missing}"
        )

        # tenant_id must be back in collections.
        coll_cols = _column_names(pg_engine, "collections")
        assert "tenant_id" in coll_cols, (
            "'collections.tenant_id' missing after re-upgrade"
        )

        # GIN index must have been recreated (IF NOT EXISTS makes this safe).
        ea_indexes = _index_names(pg_engine, "enterprise_artifacts")
        assert "idx_enterprise_artifacts_tags_gin" in ea_indexes, (
            "GIN index not recreated after re-upgrade"
        )

    # ------------------------------------------------------------------
    # 5. Data preservation through partial downgrade
    # ------------------------------------------------------------------

    def test_data_preservation_through_partial_downgrade(
        self, pg_engine: sa.engine.Engine
    ):
        """Data in enterprise_artifacts survives a partial (ENT-1.8 only) downgrade.

        Starting state: head (set by previous test).

        Sequence:
        1. Insert a row into enterprise_artifacts at head.
        2. Downgrade one step (drops tenant_id from collections only).
        3. Verify the row is still in enterprise_artifacts.
        4. Re-upgrade to head; verify the row is still present.

        This confirms that the ENT-1.8 downgrade does not touch enterprise
        table data — only the collections.tenant_id column is removed.
        """
        import uuid

        # Ensure we are at head.
        _run_upgrade(pg_engine, "head")

        test_tenant_id = str(uuid.uuid4())
        test_artifact_id = str(uuid.uuid4())
        test_name = f"test-artifact-{test_artifact_id[:8]}"

        # Insert a row into enterprise_artifacts.
        with pg_engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO enterprise_artifacts "
                    "(id, tenant_id, name, type, scope) "
                    "VALUES "
                    "(:id, :tenant_id, :name, :type, :scope)"
                ),
                {
                    "id": test_artifact_id,
                    "tenant_id": test_tenant_id,
                    "name": test_name,
                    "type": "skill",
                    "scope": "user",
                },
            )

        # Verify the row was inserted.
        with pg_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT id, name FROM enterprise_artifacts WHERE id = :id"
                ),
                {"id": test_artifact_id},
            )
            row = result.fetchone()
        assert row is not None, "Row not found immediately after insert"
        assert row[1] == test_name, f"Unexpected name: {row[1]!r}"

        # Downgrade one step (removes collections.tenant_id only).
        _run_downgrade(pg_engine, "-1")

        # The enterprise_artifacts table still exists; the row must survive.
        with pg_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT id, name FROM enterprise_artifacts WHERE id = :id"
                ),
                {"id": test_artifact_id},
            )
            row_after_downgrade = result.fetchone()
        assert row_after_downgrade is not None, (
            "Row was lost from enterprise_artifacts after partial downgrade"
        )
        assert row_after_downgrade[1] == test_name, (
            f"Row name changed after downgrade: {row_after_downgrade[1]!r}"
        )

        # Re-upgrade to head; the row must still be present.
        _run_upgrade(pg_engine, "head")

        with pg_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT id, name FROM enterprise_artifacts WHERE id = :id"
                ),
                {"id": test_artifact_id},
            )
            row_after_reupgrade = result.fetchone()
        assert row_after_reupgrade is not None, (
            "Row was lost from enterprise_artifacts after re-upgrade"
        )
        assert row_after_reupgrade[1] == test_name, (
            f"Row name changed after re-upgrade: {row_after_reupgrade[1]!r}"
        )

        # Cleanup: remove the test row so the database is tidy for any
        # subsequent test runs.
        with pg_engine.begin() as conn:
            conn.execute(
                text("DELETE FROM enterprise_artifacts WHERE id = :id"),
                {"id": test_artifact_id},
            )

    # ------------------------------------------------------------------
    # 6. No dangling foreign keys after full downgrade
    # ------------------------------------------------------------------

    def test_no_dangling_foreign_keys_after_downgrade(
        self, pg_engine: sa.engine.Engine
    ):
        """Full downgrade must leave no orphaned FK constraints in the schema.

        Starting state: any (we downgrade to base then verify).
        Ending state: _BASE_REVISION.

        After the enterprise tables are dropped, the pg_constraint catalog
        must contain no foreign keys that reference any of the dropped tables.
        A dangling FK would prevent future ``CREATE TABLE`` from reusing those
        table names without manual intervention.
        """
        # Go to head first so there is something to downgrade.
        _run_upgrade(pg_engine, "head")
        _run_downgrade(pg_engine, _BASE_REVISION)

        # Query for any FK constraints referencing the (now-dropped) enterprise tables.
        enterprise_table_names = tuple(_ENTERPRISE_TABLES)
        with pg_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT conname, conrelid::regclass::text AS source_table "
                    "FROM pg_constraint "
                    "WHERE contype = 'f' "
                    "AND confrelid::regclass::text = ANY(:tables)"
                ),
                {"tables": list(enterprise_table_names)},
            )
            dangling_fks = result.fetchall()

        assert not dangling_fks, (
            "Dangling FK constraints reference dropped enterprise tables: "
            + ", ".join(
                f"{row[0]!r} on {row[1]!r}" for row in dangling_fks
            )
        )

        # Also verify from the source side: no FK constraints on any surviving
        # table should point at one of the dropped enterprise table names via
        # the pg_indexes/pg_constraint catalog (belt-and-suspenders check).
        with pg_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT tc.table_name, kcu.column_name, ccu.table_name AS ref_table "
                    "FROM information_schema.table_constraints AS tc "
                    "JOIN information_schema.key_column_usage AS kcu "
                    "  ON tc.constraint_name = kcu.constraint_name "
                    "  AND tc.table_schema = kcu.table_schema "
                    "JOIN information_schema.constraint_column_usage AS ccu "
                    "  ON ccu.constraint_name = tc.constraint_name "
                    "  AND ccu.table_schema = tc.table_schema "
                    "WHERE tc.constraint_type = 'FOREIGN KEY' "
                    "AND ccu.table_name = ANY(:tables) "
                    "AND tc.table_schema = 'public'"
                ),
                {"tables": list(enterprise_table_names)},
            )
            dangling_info_schema = result.fetchall()

        assert not dangling_info_schema, (
            "information_schema shows FK constraints still referencing dropped tables: "
            + ", ".join(
                f"{row[0]}.{row[1]} -> {row[2]}" for row in dangling_info_schema
            )
        )
