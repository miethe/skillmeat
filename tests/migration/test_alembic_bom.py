"""Alembic migration tests for the SkillBOM attestation tables.

Verifies that:
1. A fresh SQLite database receives all six BOM tables, their indexes, and
   foreign-key constraints after running the two BOM migrations to head.
2. Existing data (artifact rows) is preserved across the migration.
3. ``alembic downgrade`` correctly reverses both migrations.
4. Re-upgrading after a downgrade produces the same schema (idempotency).

All tests run on SQLite only (no external database required) and create an
isolated temp database for each test so they are fully independent.

Migration chain covered
-----------------------
20260311_0003_add_skillbom_attestation_tables  (6 new tables)
20260312_0001_add_bom_signature_fields         (adds signing_key_id column)

Pre-BOM base revision
---------------------
``ent_008_enterprise_parity_tables``  — the down_revision of the first BOM
migration.  We stamp the temp database at this revision before running the
BOM-specific upgrades, so the test is scoped to only the BOM delta.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator, List, Set

import pytest
import sqlalchemy as sa
from sqlalchemy import inspect, text

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

# Absolute path to alembic.ini so tests are location-independent.
_ALEMBIC_INI = str(
    Path(__file__).resolve().parents[2]
    / "skillmeat"
    / "cache"
    / "migrations"
    / "alembic.ini"
)

# Revision IDs
_PRE_BOM_REVISION = "ent_008_enterprise_parity_tables"
_BOM_REV_1 = "20260311_0003_add_skillbom_attestation_tables"
_BOM_REV_2 = "20260312_0001_add_bom_signature_fields"

# The six tables introduced by the first BOM migration.
_BOM_TABLES: frozenset[str] = frozenset(
    [
        "attestation_records",
        "artifact_history_events",
        "bom_snapshots",
        "attestation_policies",
        "bom_metadata",
        "scope_validators",
    ]
)

# Expected indexes on each BOM table (subset — spot-check the important ones).
_EXPECTED_INDEXES: dict[str, Set[str]] = {
    "attestation_records": {
        "idx_attestation_records_owner",
        "idx_attestation_records_artifact_id",
    },
    "artifact_history_events": {
        "idx_artifact_history_artifact_ts",
        "idx_artifact_history_type_ts",
        "idx_artifact_history_actor_id",
    },
    "bom_snapshots": {
        "idx_bom_snapshots_project_created",
        "idx_bom_snapshots_commit_sha",
    },
    "attestation_policies": {
        "idx_attestation_policies_tenant_id",
        "idx_attestation_policies_name",
    },
    "scope_validators": {
        "idx_scope_validators_scope_pattern",
        "idx_scope_validators_owner_type",
    },
}


# ---------------------------------------------------------------------------
# SQLite engine factory
# ---------------------------------------------------------------------------


def _sqlite_url(db_path: Path) -> str:
    return f"sqlite:///{db_path}"


def _create_engine(db_path: Path) -> sa.engine.Engine:
    engine = sa.create_engine(
        _sqlite_url(db_path),
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    # Enable FK enforcement on every new connection.
    @sa.event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


# ---------------------------------------------------------------------------
# Alembic helpers
# ---------------------------------------------------------------------------


def _get_alembic_config(db_url: str):
    """Build an Alembic Config pointed at *db_url*."""
    from alembic.config import Config

    cfg = Config(_ALEMBIC_INI)
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _run_upgrade(engine: sa.engine.Engine, revision: str = "head") -> None:
    from alembic import command as alembic_command

    cfg = _get_alembic_config(engine.url.render_as_string(hide_password=False))
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        alembic_command.upgrade(cfg, revision)


def _run_downgrade(engine: sa.engine.Engine, revision: str) -> None:
    from alembic import command as alembic_command

    cfg = _get_alembic_config(engine.url.render_as_string(hide_password=False))
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        alembic_command.downgrade(cfg, revision)


def _stamp(engine: sa.engine.Engine, revision: str) -> None:
    """Stamp the database at *revision* without running any migration SQL."""
    from alembic import command as alembic_command

    cfg = _get_alembic_config(engine.url.render_as_string(hide_password=False))
    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        alembic_command.stamp(cfg, revision)


def _current_revision(engine: sa.engine.Engine) -> str | None:
    """Return the current Alembic revision or None if alembic_version is absent."""
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
# Schema introspection helpers
# ---------------------------------------------------------------------------


def _table_names(engine: sa.engine.Engine) -> Set[str]:
    return set(inspect(engine).get_table_names())


def _column_names(engine: sa.engine.Engine, table: str) -> Set[str]:
    return {col["name"] for col in inspect(engine).get_columns(table)}


def _index_names(engine: sa.engine.Engine, table: str) -> Set[str]:
    """Return index names for *table*, using a fresh connection to avoid SQLite
    schema-cache staleness after DDL changes."""
    # SQLite connections cache the schema; invalidate before inspecting.
    engine.dispose()
    return {idx["name"] for idx in inspect(engine).get_indexes(table)}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fresh_db(tmp_path: Path) -> Generator[sa.engine.Engine, None, None]:
    """Yield a SQLAlchemy engine backed by a fresh, pre-stamped SQLite file.

    The database is stamped at ``_PRE_BOM_REVISION`` so tests apply only the
    two BOM-specific migrations rather than the full history.  We create the
    ``artifacts`` table manually with the minimum schema needed so the BOM
    migrations' FK constraints can resolve.
    """
    db_file = tmp_path / "test_bom_migration.db"
    engine = _create_engine(db_file)

    # Create the artifacts table (pre-requisite for BOM FK constraints).
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    source TEXT,
                    project_id TEXT,
                    deployed_version TEXT,
                    upstream_version TEXT,
                    content TEXT,
                    content_hash TEXT,
                    uuid TEXT,
                    artifact_metadata TEXT,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )

    # Stamp at the pre-BOM revision so Alembic only runs the BOM delta.
    _stamp(engine, _PRE_BOM_REVISION)

    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def upgraded_db(fresh_db: sa.engine.Engine) -> sa.engine.Engine:
    """Yield a *fresh_db* engine with both BOM migrations applied."""
    _run_upgrade(fresh_db, _BOM_REV_2)
    return fresh_db


# ---------------------------------------------------------------------------
# Test: Fresh schema — table creation
# ---------------------------------------------------------------------------


class TestFreshSchemaBomMigration:
    """Apply BOM migrations on a fresh SQLite DB and verify schema state."""

    def test_all_bom_tables_created(self, upgraded_db: sa.engine.Engine) -> None:
        """All six BOM tables must exist after upgrading to head."""
        tables = _table_names(upgraded_db)
        missing = _BOM_TABLES - tables
        assert not missing, f"BOM tables missing after upgrade: {missing}"

    def test_attestation_records_columns(self, upgraded_db: sa.engine.Engine) -> None:
        """attestation_records must have all required columns."""
        cols = _column_names(upgraded_db, "attestation_records")
        required = {"id", "artifact_id", "owner_type", "owner_id", "visibility",
                    "created_at", "updated_at"}
        missing = required - cols
        assert not missing, (
            f"attestation_records missing columns: {missing}"
        )

    def test_artifact_history_events_columns(
        self, upgraded_db: sa.engine.Engine
    ) -> None:
        """artifact_history_events must have all required columns."""
        cols = _column_names(upgraded_db, "artifact_history_events")
        required = {"id", "artifact_id", "event_type", "owner_type", "timestamp"}
        missing = required - cols
        assert not missing, (
            f"artifact_history_events missing columns: {missing}"
        )

    def test_bom_snapshots_columns(self, upgraded_db: sa.engine.Engine) -> None:
        """bom_snapshots must have all required columns including signing_key_id."""
        cols = _column_names(upgraded_db, "bom_snapshots")
        # Core columns from migration 1
        required = {"id", "project_id", "commit_sha", "bom_json",
                    "signature", "signature_algorithm", "owner_type", "created_at"}
        missing = required - cols
        assert not missing, f"bom_snapshots missing columns: {missing}"

        # signing_key_id added by migration 2
        assert "signing_key_id" in cols, (
            "bom_snapshots.signing_key_id column missing — "
            "migration 20260312_0001_add_bom_signature_fields may not have run"
        )

    def test_expected_indexes_created(self, upgraded_db: sa.engine.Engine) -> None:
        """Spot-check that critical indexes exist on the BOM tables."""
        for table, expected in _EXPECTED_INDEXES.items():
            actual = _index_names(upgraded_db, table)
            missing = expected - actual
            assert not missing, (
                f"Table {table!r} missing indexes after upgrade: {missing}"
            )

    def test_alembic_revision_is_bom_rev_2(
        self, upgraded_db: sa.engine.Engine
    ) -> None:
        """Alembic version table must record the latest BOM revision."""
        current = _current_revision(upgraded_db)
        assert current == _BOM_REV_2, (
            f"Expected alembic revision {_BOM_REV_2!r} after upgrade, got {current!r}"
        )

    def test_foreign_key_constraint_on_attestation_records(
        self, upgraded_db: sa.engine.Engine
    ) -> None:
        """Inserting an attestation_record with a non-existent artifact_id
        must raise an IntegrityError (FK enforced)."""
        from datetime import datetime

        with upgraded_db.connect() as conn:
            # FK enforcement is enabled via event listener.
            with pytest.raises(Exception):
                conn.execute(
                    text(
                        """
                        INSERT INTO attestation_records
                            (artifact_id, owner_type, owner_id, visibility,
                             created_at, updated_at)
                        VALUES
                            (:aid, 'user', 'owner-1', 'private', :ts, :ts)
                        """
                    ),
                    {"aid": "nonexistent:artifact", "ts": datetime.utcnow()},
                )
                conn.commit()

    def test_foreign_key_cascade_delete_on_history_events(
        self, upgraded_db: sa.engine.Engine
    ) -> None:
        """Deleting an artifact must cascade-delete its history events."""
        from datetime import datetime

        now = datetime.utcnow()

        with upgraded_db.begin() as conn:
            # Insert parent artifact.
            conn.execute(
                text(
                    "INSERT INTO artifacts (id, name, type) "
                    "VALUES ('skill:cascade-test', 'cascade-test', 'skill')"
                )
            )
            # Insert history event referencing the artifact.
            conn.execute(
                text(
                    """
                    INSERT INTO artifact_history_events
                        (artifact_id, event_type, owner_type, timestamp)
                    VALUES ('skill:cascade-test', 'create', 'user', :ts)
                    """
                ),
                {"ts": now},
            )

        # Verify the event exists.
        with upgraded_db.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT COUNT(*) FROM artifact_history_events "
                    "WHERE artifact_id = 'skill:cascade-test'"
                )
            ).scalar()
        assert row == 1, "History event was not inserted"

        # Delete the artifact — cascade should remove history events.
        with upgraded_db.begin() as conn:
            conn.execute(
                text("DELETE FROM artifacts WHERE id = 'skill:cascade-test'")
            )

        with upgraded_db.connect() as conn:
            remaining = conn.execute(
                text(
                    "SELECT COUNT(*) FROM artifact_history_events "
                    "WHERE artifact_id = 'skill:cascade-test'"
                )
            ).scalar()
        assert remaining == 0, (
            "Cascade delete did not remove artifact_history_events rows"
        )


# ---------------------------------------------------------------------------
# Test: Data preservation
# ---------------------------------------------------------------------------


class TestDataPreservation:
    """Existing artifact rows survive the BOM migration."""

    def test_artifact_rows_preserved_after_upgrade(
        self, fresh_db: sa.engine.Engine
    ) -> None:
        """Rows inserted before migration must still be present after upgrade."""
        # Insert two artifact rows before migrating.
        with fresh_db.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO artifacts (id, name, type) VALUES "
                    "('skill:pre-migration-a', 'pre-migration-a', 'skill'), "
                    "('command:pre-migration-b', 'pre-migration-b', 'command')"
                )
            )

        # Run both BOM migrations.
        _run_upgrade(fresh_db, _BOM_REV_2)

        # Verify both rows survived.
        with fresh_db.connect() as conn:
            count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM artifacts "
                    "WHERE id IN ('skill:pre-migration-a', 'command:pre-migration-b')"
                )
            ).scalar()
        assert count == 2, (
            f"Expected 2 pre-migration artifact rows after upgrade, found {count}"
        )

    def test_artifact_data_intact_after_upgrade(
        self, fresh_db: sa.engine.Engine
    ) -> None:
        """Column values of existing artifact rows must be unchanged."""
        with fresh_db.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO artifacts (id, name, type, source) "
                    "VALUES ('skill:data-check', 'data-check', 'skill', 'owner/repo')"
                )
            )

        _run_upgrade(fresh_db, _BOM_REV_2)

        with fresh_db.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT id, name, type, source FROM artifacts "
                    "WHERE id = 'skill:data-check'"
                )
            ).fetchone()

        assert row is not None, "Artifact row missing after upgrade"
        assert row[0] == "skill:data-check"
        assert row[1] == "data-check"
        assert row[2] == "skill"
        assert row[3] == "owner/repo"


# ---------------------------------------------------------------------------
# Test: Rollback / Downgrade
# ---------------------------------------------------------------------------


class TestRollback:
    """Alembic downgrade reverses BOM migrations cleanly."""

    def test_downgrade_step1_removes_signing_key_id(
        self, upgraded_db: sa.engine.Engine
    ) -> None:
        """Downgrading one step must remove the signing_key_id column."""
        # Verify column exists before downgrade.
        assert "signing_key_id" in _column_names(upgraded_db, "bom_snapshots"), (
            "Pre-condition failed: signing_key_id should exist before downgrade"
        )

        _run_downgrade(upgraded_db, _BOM_REV_1)

        cols = _column_names(upgraded_db, "bom_snapshots")
        assert "signing_key_id" not in cols, (
            "signing_key_id still present after downgrading migration 2"
        )

        current = _current_revision(upgraded_db)
        assert current == _BOM_REV_1, (
            f"Expected revision {_BOM_REV_1!r} after -1 downgrade, got {current!r}"
        )

    def test_full_downgrade_removes_all_bom_tables(
        self, upgraded_db: sa.engine.Engine
    ) -> None:
        """Full downgrade to pre-BOM revision must drop all six BOM tables."""
        _run_downgrade(upgraded_db, _PRE_BOM_REVISION)

        tables = _table_names(upgraded_db)
        still_present = _BOM_TABLES & tables
        assert not still_present, (
            f"BOM tables still present after full downgrade: {still_present}"
        )

        # Non-BOM tables must survive.
        assert "artifacts" in tables, (
            "artifacts table was unexpectedly dropped by BOM downgrade"
        )

        current = _current_revision(upgraded_db)
        assert current == _PRE_BOM_REVISION, (
            f"Expected revision {_PRE_BOM_REVISION!r} after full downgrade, "
            f"got {current!r}"
        )

    def test_downgrade_removes_bom_indexes(
        self, upgraded_db: sa.engine.Engine
    ) -> None:
        """After full downgrade, BOM table indexes must no longer exist."""
        _run_downgrade(upgraded_db, _PRE_BOM_REVISION)

        # bom_snapshots table is gone; inspecting it should raise or return empty.
        inspector = inspect(upgraded_db)
        table_names = inspector.get_table_names()
        for table in _BOM_TABLES:
            assert table not in table_names, (
                f"Table {table!r} unexpectedly survives downgrade"
            )

    def test_reupgrade_after_downgrade_restores_schema(
        self, upgraded_db: sa.engine.Engine
    ) -> None:
        """Re-upgrading after a full downgrade must recreate the complete schema."""
        # Full downgrade first.
        _run_downgrade(upgraded_db, _PRE_BOM_REVISION)

        # Re-upgrade.
        _run_upgrade(upgraded_db, _BOM_REV_2)

        tables = _table_names(upgraded_db)
        missing = _BOM_TABLES - tables
        assert not missing, (
            f"BOM tables missing after re-upgrade: {missing}"
        )

        # signing_key_id must be back.
        cols = _column_names(upgraded_db, "bom_snapshots")
        assert "signing_key_id" in cols, (
            "signing_key_id missing from bom_snapshots after re-upgrade"
        )

        current = _current_revision(upgraded_db)
        assert current == _BOM_REV_2, (
            f"Expected revision {_BOM_REV_2!r} after re-upgrade, got {current!r}"
        )
