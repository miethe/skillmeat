"""Migrate collection_artifacts.artifact_id to artifact_uuid FK (CAI-P5-01).

Revision ID: 20260219_1000_migrate_collection_artifacts_to_uuid
Revises: 20260218_1100_add_composite_artifact_tables
Create Date: 2026-02-19 10:00:00.000000+00:00

Summary
-------
Adds ``artifact_uuid`` column to ``collection_artifacts`` with a proper FK
to ``artifacts.uuid`` (ON DELETE CASCADE), replacing the bare ``artifact_id``
string column that had no FK constraint.

Migration Strategy (shadow-column + full table rebuild)
--------------------------------------------------------
upgrade():
  1. Rename the live table to ``_collection_artifacts_old`` (preserves all
     data including the original ``artifact_id`` values for rollback).
  2. Create a fresh ``collection_artifacts`` table with the correct schema:
     PRIMARY KEY (collection_id, artifact_uuid), FK to artifacts.uuid.
     The ``_artifact_id_backup`` column carries the original string values
     forward so that downgrade() can restore them.
  3. Backfill: INSERT rows from the old table, resolving ``artifact_uuid``
     by joining against ``artifacts.id``.
  4. Log and skip orphan rows (no matching artifact in the cache).
  5. Recreate all indexes on the new table.
  6. Drop the staging table ``_collection_artifacts_old``.

downgrade():
  1. Rename the live table to ``_collection_artifacts_new`` (staging).
  2. Recreate the pre-migration table with ``artifact_id`` as PK component
     and no FK constraint.
  3. Copy data from ``_artifact_id_backup`` back into ``artifact_id``.
  4. Restore original indexes.
  5. Drop the staging table.

SQLite Compatibility
--------------------
SQLite does not support ALTER TABLE ... ADD PRIMARY KEY, ADD CONSTRAINT,
or DROP COLUMN.  This migration avoids all of those by using the classic
"rename → create new → INSERT SELECT → drop old" pattern, which SQLite
handles natively.  This is the same approach used by
``_migrate_artifact_tags_fk()`` in models.py.

The global ``render_as_batch=True`` in env.py applies only to
``batch_alter_table`` calls; the raw SQL path below bypasses it entirely
and is fully compatible with both SQLite and PostgreSQL.

Orphan Handling
---------------
Rows whose ``artifact_id`` has no matching ``artifacts.id`` in the cache
cannot receive a valid ``artifact_uuid``.  These rows are skipped during
the INSERT and logged individually.  They are permanently lost after
``upgrade()`` completes (the staging table is dropped).

Rollback Safety
---------------
``_artifact_id_backup`` carries the original ``artifact_id`` string values
through the upgraded schema so that ``downgrade()`` can restore the
pre-migration table exactly.
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


log = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "20260219_1000_migrate_collection_artifacts_to_uuid"
down_revision: Union[str, None] = "20260218_1100_add_composite_artifact_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Ordered list of all data columns (excluding composite PK parts).
# Used in both upgrade() and downgrade() INSERT SELECT statements to keep
# the column list DRY and easy to audit.
_DATA_COLS = (
    "added_at",
    "description",
    "author",
    "license",
    "tags_json",
    "version",
    "source",
    "origin",
    "origin_source",
    "resolved_sha",
    "resolved_version",
    "synced_at",
    "tools_json",
    "deployments_json",
)
_DATA_COLS_SQL = ", ".join(_DATA_COLS)


def upgrade() -> None:
    """Migrate collection_artifacts.artifact_id to artifact_uuid FK.

    Steps:
      1. Rename collection_artifacts → _collection_artifacts_old.
      2. Create new collection_artifacts with correct PK and FK.
      3. Backfill rows from old table; log and skip orphans.
      4. Recreate indexes.
      5. Drop _collection_artifacts_old.
    """
    connection = op.get_bind()

    # ------------------------------------------------------------------
    # Step 1: Drop all existing indexes on collection_artifacts before the
    # rename.  Use IF EXISTS for idempotency — some indexes may have been
    # created by a previous partial run or the initial schema migration.
    # ------------------------------------------------------------------
    for idx in (
        "idx_collection_artifacts_collection_id",
        "idx_collection_artifacts_artifact_id",
        "idx_collection_artifacts_artifact_uuid",
        "idx_collection_artifacts_added_at",
        "idx_collection_artifacts_synced_at",
        "idx_collection_artifacts_tools_json",
    ):
        connection.execute(sa.text(f"DROP INDEX IF EXISTS {idx}"))

    # ------------------------------------------------------------------
    # Step 2: Rename current table to staging name.
    # Clean up any leftover staging table from a prior failed run first.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text("DROP TABLE IF EXISTS _collection_artifacts_old")
    )
    connection.execute(
        sa.text(
            "ALTER TABLE collection_artifacts "
            "RENAME TO _collection_artifacts_old"
        )
    )

    # ------------------------------------------------------------------
    # Step 3: Create the new table with the correct schema.
    #   - PRIMARY KEY (collection_id, artifact_uuid)
    #   - FK: artifact_uuid → artifacts.uuid ON DELETE CASCADE
    #   - FK: collection_id → collections.id ON DELETE CASCADE
    #   - _artifact_id_backup retains original string for rollback safety
    # ------------------------------------------------------------------
    connection.execute(
        sa.text(
            """
            CREATE TABLE collection_artifacts (
                collection_id   VARCHAR NOT NULL,
                artifact_uuid   VARCHAR NOT NULL,
                _artifact_id_backup VARCHAR NOT NULL,
                added_at        DATETIME NOT NULL,
                description     TEXT,
                author          VARCHAR,
                license         VARCHAR,
                tags_json       TEXT,
                version         VARCHAR,
                source          VARCHAR,
                origin          VARCHAR,
                origin_source   VARCHAR,
                resolved_sha    VARCHAR(64),
                resolved_version VARCHAR,
                synced_at       DATETIME,
                tools_json      TEXT,
                deployments_json TEXT,
                PRIMARY KEY (collection_id, artifact_uuid),
                CONSTRAINT fk_collection_artifacts_artifact_uuid
                    FOREIGN KEY (artifact_uuid)
                    REFERENCES artifacts (uuid)
                    ON DELETE CASCADE,
                FOREIGN KEY (collection_id)
                    REFERENCES collections (id)
                    ON DELETE CASCADE
            )
            """
        )
    )

    # ------------------------------------------------------------------
    # Step 4: Identify orphan rows before insertion so we can log them.
    # An orphan is a row whose artifact_id does not match any artifacts.id.
    # ------------------------------------------------------------------
    orphans = connection.execute(
        sa.text(
            """
            SELECT o.collection_id, o.artifact_id
            FROM _collection_artifacts_old o
            WHERE NOT EXISTS (
                SELECT 1 FROM artifacts a WHERE a.id = o.artifact_id
            )
            """
        )
    ).fetchall()

    if orphans:
        for row in orphans:
            log.warning(
                "CAI-P5-01: Skipping orphaned collection_artifacts row — "
                "collection_id=%r artifact_id=%r (no matching artifact in cache)",
                row[0],
                row[1],
            )
        log.info(
            "CAI-P5-01: %d orphaned collection_artifacts rows will be dropped",
            len(orphans),
        )

    # ------------------------------------------------------------------
    # Step 5: Copy rows that have a matching artifact UUID.
    # The subquery join resolves artifact_id → artifacts.uuid inline.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text(
            f"""
            INSERT INTO collection_artifacts
                (collection_id, artifact_uuid, _artifact_id_backup,
                 {_DATA_COLS_SQL})
            SELECT
                o.collection_id,
                a.uuid,
                o.artifact_id,
                {", ".join(f"o.{c}" for c in _DATA_COLS)}
            FROM _collection_artifacts_old o
            JOIN artifacts a ON a.id = o.artifact_id
            """
        )
    )

    inserted = connection.execute(
        sa.text("SELECT COUNT(*) FROM collection_artifacts")
    ).scalar()
    log.info(
        "CAI-P5-01: Migrated %d collection_artifacts rows to UUID FK",
        inserted,
    )

    # ------------------------------------------------------------------
    # Step 6: Recreate indexes on the new table.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text(
            "CREATE INDEX idx_collection_artifacts_collection_id "
            "ON collection_artifacts (collection_id)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX idx_collection_artifacts_artifact_uuid "
            "ON collection_artifacts (artifact_uuid)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX idx_collection_artifacts_added_at "
            "ON collection_artifacts (added_at)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX idx_collection_artifacts_synced_at "
            "ON collection_artifacts (synced_at)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX idx_collection_artifacts_tools_json "
            "ON collection_artifacts (tools_json)"
        )
    )

    # ------------------------------------------------------------------
    # Step 7: Drop the staging table.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text("DROP TABLE _collection_artifacts_old")
    )


def downgrade() -> None:
    """Restore collection_artifacts.artifact_id from _artifact_id_backup.

    Steps:
      1. Rename current (migrated) table to staging name.
      2. Recreate original table: artifact_id as PK component, no UUID FK.
      3. Copy data from _artifact_id_backup back into artifact_id.
      4. Restore original indexes.
      5. Drop the staging table.

    Note: orphan rows that were dropped during upgrade() are permanently
    gone.  All other rows are restored with their original artifact_id
    string values.
    """
    connection = op.get_bind()

    # ------------------------------------------------------------------
    # Step 1: Drop all current indexes before rename.
    # ------------------------------------------------------------------
    for idx in (
        "idx_collection_artifacts_collection_id",
        "idx_collection_artifacts_artifact_id",
        "idx_collection_artifacts_artifact_uuid",
        "idx_collection_artifacts_added_at",
        "idx_collection_artifacts_synced_at",
        "idx_collection_artifacts_tools_json",
    ):
        connection.execute(sa.text(f"DROP INDEX IF EXISTS {idx}"))

    # ------------------------------------------------------------------
    # Step 2: Rename migrated table to staging name.
    # Clean up any leftover staging table from a prior failed run first.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text("DROP TABLE IF EXISTS _collection_artifacts_new")
    )
    connection.execute(
        sa.text(
            "ALTER TABLE collection_artifacts "
            "RENAME TO _collection_artifacts_new"
        )
    )

    # ------------------------------------------------------------------
    # Step 3: Recreate original table schema (no artifact_uuid, no FK).
    # ------------------------------------------------------------------
    connection.execute(
        sa.text(
            """
            CREATE TABLE collection_artifacts (
                collection_id   VARCHAR NOT NULL,
                artifact_id     VARCHAR NOT NULL,
                added_at        DATETIME NOT NULL,
                description     TEXT,
                author          VARCHAR,
                license         VARCHAR,
                tags_json       TEXT,
                version         VARCHAR,
                source          VARCHAR,
                origin          VARCHAR,
                origin_source   VARCHAR,
                resolved_sha    VARCHAR(64),
                resolved_version VARCHAR,
                synced_at       DATETIME,
                tools_json      TEXT,
                deployments_json TEXT,
                PRIMARY KEY (collection_id, artifact_id),
                FOREIGN KEY (collection_id)
                    REFERENCES collections (id)
                    ON DELETE CASCADE
            )
            """
        )
    )

    # ------------------------------------------------------------------
    # Step 4: Copy data — restore artifact_id from _artifact_id_backup.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text(
            f"""
            INSERT INTO collection_artifacts
                (collection_id, artifact_id, {_DATA_COLS_SQL})
            SELECT
                n.collection_id,
                n._artifact_id_backup,
                {", ".join(f"n.{c}" for c in _DATA_COLS)}
            FROM _collection_artifacts_new n
            """
        )
    )

    # ------------------------------------------------------------------
    # Step 5: Restore original indexes.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text(
            "CREATE INDEX idx_collection_artifacts_collection_id "
            "ON collection_artifacts (collection_id)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX idx_collection_artifacts_artifact_id "
            "ON collection_artifacts (artifact_id)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX idx_collection_artifacts_added_at "
            "ON collection_artifacts (added_at)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX idx_collection_artifacts_synced_at "
            "ON collection_artifacts (synced_at)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX idx_collection_artifacts_tools_json "
            "ON collection_artifacts (tools_json)"
        )
    )

    # ------------------------------------------------------------------
    # Step 6: Drop the staging table.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text("DROP TABLE _collection_artifacts_new")
    )
