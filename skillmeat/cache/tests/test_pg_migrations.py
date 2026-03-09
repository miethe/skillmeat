"""Integration tests for the full Alembic migration chain on PostgreSQL.

These tests exercise every migration revision from base to head (and back) against
a real PostgreSQL instance.  They are **integration tests** and will be skipped
automatically when PostgreSQL is not reachable.

Requirements
------------
* A running PostgreSQL instance accessible via ``TEST_DATABASE_URL`` (default:
  ``postgresql://localhost:5432/skillmeat_test``).
* The test database must exist and the connecting user must have CREATE / DROP
  privileges within it.  Each test tears down all tables it creates so the
  database can be shared across test runs.

Running
-------
.. code-block:: bash

    # With the default URL:
    pytest skillmeat/cache/tests/test_pg_migrations.py -v

    # With a custom URL:
    TEST_DATABASE_URL=postgresql://user:pass@host:5432/mydb \\
        pytest skillmeat/cache/tests/test_pg_migrations.py -v

Skipping
--------
If the database is not reachable the entire module is skipped with a clear
``pytest.skip`` message rather than raising connection errors.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_DB_URL = "postgresql://localhost:5432/skillmeat_test"
_ALEMBIC_INI = Path(__file__).parent.parent / "migrations" / "alembic.ini"
_MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"


# ---------------------------------------------------------------------------
# PostgreSQL availability check (module-level skip)
# ---------------------------------------------------------------------------


def _get_test_db_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", _DEFAULT_DB_URL)


def _pg_available(db_url: str) -> bool:
    """Return True if a connection to the PostgreSQL URL can be established."""
    try:
        engine = sa.create_engine(db_url, pool_pre_ping=True)
        with engine.connect():
            pass
        engine.dispose()
        return True
    except Exception:
        return False


# Evaluate availability once at collection time so the skip message is
# emitted for the whole module rather than test-by-test.
_DB_URL = _get_test_db_url()
if not _pg_available(_DB_URL):
    pytest.skip(
        f"PostgreSQL not available at {_DB_URL!r} — set TEST_DATABASE_URL to a "
        "reachable instance to run these integration tests.",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_alembic_cfg(db_url: str) -> AlembicConfig:
    """Build an AlembicConfig pointed at the test database."""
    cfg = AlembicConfig(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _drop_all_tables(engine: sa.engine.Engine) -> None:
    """Drop all user tables and the alembic_version tracking table.

    Uses ``DROP TABLE … CASCADE`` so that FK-dependent tables are removed
    without needing to resolve ordering.  Also removes PostgreSQL functions
    created by the ``updated_at`` trigger migrations.
    """
    with engine.begin() as conn:
        # Retrieve all table names in the public schema.
        result = conn.execute(
            sa.text(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                """
            )
        )
        tables = [row[0] for row in result]

        for table in tables:
            conn.execute(sa.text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))

        # Drop all user-defined functions that belong to the updated_at
        # trigger pattern (update_<table>_updated_at) to keep the schema clean.
        result = conn.execute(
            sa.text(
                """
                SELECT p.proname
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'public'
                  AND p.proname LIKE 'update_%'
                """
            )
        )
        funcs = [row[0] for row in result]
        for fn in funcs:
            conn.execute(sa.text(f"DROP FUNCTION IF EXISTS {fn}() CASCADE"))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pg_engine() -> Generator[sa.engine.Engine, None, None]:
    """Return a SQLAlchemy engine for the test PostgreSQL database."""
    engine = sa.create_engine(_DB_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_db(pg_engine: sa.engine.Engine) -> Generator[None, None, None]:
    """Drop all tables before each test to guarantee a clean slate.

    Using ``autouse=True`` means each test in this module starts with an empty
    database, eliminating order dependencies.
    """
    _drop_all_tables(pg_engine)
    yield
    # Post-test cleanup is intentionally omitted so that test failures can be
    # inspected against the final DB state.  The pre-test cleanup above
    # ensures the next test always starts clean regardless.


@pytest.fixture()
def alembic_cfg() -> AlembicConfig:
    """Return an AlembicConfig wired to the test database."""
    return _make_alembic_cfg(_DB_URL)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_upgrade_head_postgresql(
    alembic_cfg: AlembicConfig,
    pg_engine: sa.engine.Engine,
) -> None:
    """Run ``alembic upgrade head`` against PostgreSQL and verify it completes.

    Checks that:
    * The command runs without raising an exception.
    * The ``alembic_version`` table exists after the upgrade.
    * At least the ``projects`` table (created in the initial schema) exists,
      confirming that real DDL was executed.
    """
    alembic_command.upgrade(alembic_cfg, "head")

    inspector = sa.inspect(pg_engine)
    table_names = inspector.get_table_names()

    assert "alembic_version" in table_names, (
        "alembic_version table not found after upgrade head — Alembic did not "
        "track migrations correctly."
    )
    assert "projects" in table_names, (
        "projects table not found after upgrade head — initial schema migration "
        "may not have run."
    )
    assert "artifacts" in table_names, (
        "artifacts table not found after upgrade head."
    )


@pytest.mark.integration
def test_downgrade_base_postgresql(
    alembic_cfg: AlembicConfig,
    pg_engine: sa.engine.Engine,
) -> None:
    """Upgrade to head then downgrade to base; verify the schema is removed.

    After a full downgrade:
    * The ``alembic_version`` table should be absent (or empty) — all
      revisions have been rolled back.
    * The ``projects`` table should not exist — the initial schema was
      dropped by its downgrade step.
    """
    alembic_command.upgrade(alembic_cfg, "head")

    # Sanity-check that head was actually applied.
    inspector = sa.inspect(pg_engine)
    assert "projects" in inspector.get_table_names()

    alembic_command.downgrade(alembic_cfg, "base")

    inspector = sa.inspect(pg_engine)
    table_names = inspector.get_table_names()

    # After a full downgrade the alembic_version table should be gone or have
    # no rows (depends on the migration set's base downgrade implementation).
    if "alembic_version" in table_names:
        with pg_engine.connect() as conn:
            count = conn.execute(
                sa.text("SELECT COUNT(*) FROM alembic_version")
            ).scalar()
        assert count == 0, (
            "alembic_version still contains rows after downgrade to base."
        )

    assert "projects" not in table_names, (
        "projects table still exists after downgrade to base — initial schema "
        "downgrade did not drop it."
    )


@pytest.mark.integration
def test_updated_at_triggers_postgresql(
    alembic_cfg: AlembicConfig,
    pg_engine: sa.engine.Engine,
) -> None:
    """Verify that the ``updated_at`` trigger fires on the ``projects`` table.

    Steps:
    1. Upgrade to head.
    2. Insert a row into ``projects``.
    3. Capture the initial ``updated_at`` value.
    4. Wait a brief moment (use ``pg_sleep``) and UPDATE the row.
    5. Verify that ``updated_at`` changed — the trigger fired.
    """
    alembic_command.upgrade(alembic_cfg, "head")

    with pg_engine.begin() as conn:
        # Insert a minimal projects row.
        conn.execute(
            sa.text(
                """
                INSERT INTO projects (id, name, path)
                VALUES ('trigger-test', 'Trigger Test', '/tmp/trigger-test')
                """
            )
        )

        before = conn.execute(
            sa.text("SELECT updated_at FROM projects WHERE id = 'trigger-test'")
        ).scalar()

        # Sleep one second on the server side to guarantee a timestamp
        # difference that is visible in wall-clock precision.
        conn.execute(sa.text("SELECT pg_sleep(1)"))

        conn.execute(
            sa.text(
                "UPDATE projects SET name = 'Trigger Test Updated' "
                "WHERE id = 'trigger-test'"
            )
        )

        after = conn.execute(
            sa.text("SELECT updated_at FROM projects WHERE id = 'trigger-test'")
        ).scalar()

    assert before is not None, "updated_at was NULL after INSERT"
    assert after is not None, "updated_at was NULL after UPDATE"
    assert after > before, (
        f"updated_at did not change after UPDATE — trigger may not have fired. "
        f"before={before!r}, after={after!r}"
    )


@pytest.mark.integration
def test_fts5_skipped_on_postgresql(
    alembic_cfg: AlembicConfig,
    pg_engine: sa.engine.Engine,
) -> None:
    """Verify that the FTS5 virtual table is NOT created on PostgreSQL.

    The ``add_fts5_catalog_search`` migration guards FTS5 creation behind
    ``is_sqlite()``.  On PostgreSQL the migration should complete successfully
    but leave no ``artifact_fts`` table behind, while still creating all
    regular relational tables.
    """
    alembic_command.upgrade(alembic_cfg, "head")

    inspector = sa.inspect(pg_engine)
    table_names = inspector.get_table_names()

    # FTS5 virtual table must NOT exist on PostgreSQL.
    assert "artifact_fts" not in table_names, (
        "artifact_fts (FTS5 virtual table) was created on PostgreSQL — the "
        "dialect guard in add_fts5_catalog_search migration is not working."
    )

    # Confirm that the regular catalog table that FTS5 would index DOES exist.
    assert "marketplace_catalog_entries" in table_names, (
        "marketplace_catalog_entries table not found after upgrade head on "
        "PostgreSQL — a required migration may have failed."
    )

    # Spot-check a few more core tables to confirm the migration chain ran.
    for expected_table in ("artifacts", "projects", "collections"):
        assert expected_table in table_names, (
            f"Expected table {expected_table!r} not found after upgrade head "
            "on PostgreSQL."
        )


@pytest.mark.integration
def test_check_constraint_has_workflow(
    alembic_cfg: AlembicConfig,
    pg_engine: sa.engine.Engine,
) -> None:
    """Verify that the ``check_artifact_type`` CHECK constraint includes 'workflow'.

    The ``add_workflow_to_artifact_type_check`` migration extends the
    ``artifacts`` table constraint to allow ``type = 'workflow'``.  This test
    confirms:
    * The constraint exists in ``pg_constraint``.
    * The constraint definition text includes the ``'workflow'`` literal.
    * Inserting an artifact with ``type = 'workflow'`` succeeds.
    * Inserting an artifact with an invalid type raises an
      ``IntegrityError``.
    """
    alembic_command.upgrade(alembic_cfg, "head")

    with pg_engine.connect() as conn:
        result = conn.execute(
            sa.text(
                """
                SELECT pg_get_constraintdef(c.oid)
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                WHERE c.conname = 'check_artifact_type'
                  AND t.relname = 'artifacts'
                  AND c.contype = 'c'
                """
            )
        )
        row = result.fetchone()

    assert row is not None, (
        "check_artifact_type constraint not found on artifacts table after "
        "upgrade head — migration may not have run."
    )
    constraint_def: str = row[0]
    assert "workflow" in constraint_def, (
        f"'workflow' not found in check_artifact_type constraint definition: "
        f"{constraint_def!r}"
    )

    # Confirm a workflow artifact can actually be inserted.
    with pg_engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                INSERT INTO projects (id, name, path)
                VALUES ('wf-proj', 'WF Project', '/tmp/wf-proj')
                """
            )
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO artifacts (id, name, type, source, version, project_id)
                VALUES ('workflow:wf-test', 'wf-test', 'workflow',
                        'local', '1.0.0', 'wf-proj')
                """
            )
        )

    # Confirm an invalid type is rejected.
    with pytest.raises(IntegrityError):
        with pg_engine.begin() as conn:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO artifacts (id, name, type, source, version, project_id)
                    VALUES ('bad:bad-type', 'bad-type', 'totally_invalid_type',
                            'local', '1.0.0', 'wf-proj')
                    """
                )
            )
