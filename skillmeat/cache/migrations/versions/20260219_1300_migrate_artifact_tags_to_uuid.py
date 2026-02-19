"""Migrate artifact_tags.artifact_id to artifact_uuid FK (CAI-P5-03).

Revision ID: 20260219_1300_migrate_artifact_tags_to_uuid
Revises: 20260219_1200_migrate_group_artifacts_to_uuid
Create Date: 2026-02-19 13:00:00.000000+00:00

Summary
-------
Adds ``artifact_uuid`` column to ``artifact_tags`` with a proper FK to
``artifacts.uuid`` (ON DELETE CASCADE), replacing the bare ``artifact_id``
string column (type:name format) that had no FK constraint to the artifacts
table.

Migration Strategy (shadow-column + full table rebuild)
--------------------------------------------------------
upgrade():
  1. Rename the live table to ``_artifact_tags_old`` (preserves all data
     including the original ``artifact_id`` values for rollback).
  2. Create a fresh ``artifact_tags`` table with the correct schema:
     PRIMARY KEY (artifact_uuid, tag_id), FK to artifacts.uuid.
     The ``_artifact_id_backup`` column carries the original string values
     forward so that downgrade() can restore them.
  3. Backfill: INSERT rows from the old table, resolving ``artifact_uuid``
     by joining against ``artifacts.id``.
  4. Log and skip orphan rows (no matching artifact in the cache).
  5. Recreate all indexes on the new table.
  6. Drop the staging table ``_artifact_tags_old``.

downgrade():
  1. Rename the live table to ``_artifact_tags_new`` (staging).
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
handles natively.  This is the same approach used by the P5-01 and P5-02
migrations.

The global ``render_as_batch=True`` in env.py applies only to
``batch_alter_table`` calls; the raw SQL path below bypasses it entirely
and is fully compatible with both SQLite and PostgreSQL.

Orphan Handling
---------------
Rows whose ``artifact_id`` (type:name format) has no matching ``artifacts.id``
in the cache cannot receive a valid ``artifact_uuid``.  These rows are skipped
during the INSERT and logged individually.  They are permanently lost after
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
revision: str = "20260219_1300_migrate_artifact_tags_to_uuid"
down_revision: Union[str, None] = "20260219_1200_migrate_group_artifacts_to_uuid"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Ordered list of all data columns (excluding composite PK parts).
# Used in both upgrade() and downgrade() INSERT SELECT statements to keep
# the column list DRY and easy to audit.
_DATA_COLS = ("created_at",)
_DATA_COLS_SQL = ", ".join(_DATA_COLS)


def upgrade() -> None:
    """Migrate artifact_tags.artifact_id to artifact_uuid FK.

    Steps:
      1. Rename artifact_tags → _artifact_tags_old.
      2. Create new artifact_tags with correct PK and FK.
      3. Backfill rows from old table; log and skip orphans.
      4. Recreate indexes.
      5. Drop _artifact_tags_old.
    """
    connection = op.get_bind()

    # ------------------------------------------------------------------
    # Step 1: Drop all existing indexes on artifact_tags before the
    # rename.  Use IF EXISTS for idempotency — some indexes may have been
    # created by a previous partial run or the initial schema migration.
    # ------------------------------------------------------------------
    for idx in (
        "idx_artifact_tags_artifact_id",
        "idx_artifact_tags_artifact_uuid",
        "idx_artifact_tags_tag_id",
        "idx_artifact_tags_created_at",
    ):
        connection.execute(sa.text(f"DROP INDEX IF EXISTS {idx}"))

    # ------------------------------------------------------------------
    # Step 2: Rename current table to staging name.
    # Clean up any leftover staging table from a prior failed run first.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text("DROP TABLE IF EXISTS _artifact_tags_old")
    )
    connection.execute(
        sa.text(
            "ALTER TABLE artifact_tags "
            "RENAME TO _artifact_tags_old"
        )
    )

    # ------------------------------------------------------------------
    # Step 3: Create the new table with the correct schema.
    #   - PRIMARY KEY (artifact_uuid, tag_id)
    #   - FK: artifact_uuid → artifacts.uuid ON DELETE CASCADE
    #   - FK: tag_id → tags.id ON DELETE CASCADE
    #   - _artifact_id_backup retains original type:name string for rollback
    # ------------------------------------------------------------------
    connection.execute(
        sa.text(
            """
            CREATE TABLE artifact_tags (
                artifact_uuid       VARCHAR NOT NULL,
                tag_id              VARCHAR NOT NULL,
                _artifact_id_backup VARCHAR NOT NULL,
                created_at          DATETIME NOT NULL,
                PRIMARY KEY (artifact_uuid, tag_id),
                CONSTRAINT fk_artifact_tags_artifact_uuid
                    FOREIGN KEY (artifact_uuid)
                    REFERENCES artifacts (uuid)
                    ON DELETE CASCADE,
                CONSTRAINT fk_artifact_tags_tag_id
                    FOREIGN KEY (tag_id)
                    REFERENCES tags (id)
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
            SELECT o.artifact_id, o.tag_id
            FROM _artifact_tags_old o
            WHERE NOT EXISTS (
                SELECT 1 FROM artifacts a WHERE a.id = o.artifact_id
            )
            """
        )
    ).fetchall()

    if orphans:
        for row in orphans:
            log.warning(
                "CAI-P5-03: Skipping orphaned artifact_tags row — "
                "artifact_id=%r tag_id=%r (no matching artifact in cache)",
                row[0],
                row[1],
            )
        log.info(
            "CAI-P5-03: %d orphaned artifact_tags rows will be dropped",
            len(orphans),
        )

    # ------------------------------------------------------------------
    # Step 5: Copy rows that have a matching artifact UUID.
    # The subquery join resolves artifact_id (type:name) → artifacts.uuid.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text(
            f"""
            INSERT INTO artifact_tags
                (artifact_uuid, tag_id, _artifact_id_backup,
                 {_DATA_COLS_SQL})
            SELECT
                a.uuid,
                o.tag_id,
                o.artifact_id,
                {", ".join(f"o.{c}" for c in _DATA_COLS)}
            FROM _artifact_tags_old o
            JOIN artifacts a ON a.id = o.artifact_id
            """
        )
    )

    inserted = connection.execute(
        sa.text("SELECT COUNT(*) FROM artifact_tags")
    ).scalar()
    log.info(
        "CAI-P5-03: Migrated %d artifact_tags rows to UUID FK",
        inserted,
    )

    # ------------------------------------------------------------------
    # Step 6: Recreate indexes on the new table.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text(
            "CREATE INDEX idx_artifact_tags_artifact_uuid "
            "ON artifact_tags (artifact_uuid)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX idx_artifact_tags_tag_id "
            "ON artifact_tags (tag_id)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX idx_artifact_tags_created_at "
            "ON artifact_tags (created_at)"
        )
    )

    # ------------------------------------------------------------------
    # Step 7: Drop the staging table.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text("DROP TABLE _artifact_tags_old")
    )


def downgrade() -> None:
    """Restore artifact_tags.artifact_id from _artifact_id_backup.

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
        "idx_artifact_tags_artifact_id",
        "idx_artifact_tags_artifact_uuid",
        "idx_artifact_tags_tag_id",
        "idx_artifact_tags_created_at",
    ):
        connection.execute(sa.text(f"DROP INDEX IF EXISTS {idx}"))

    # ------------------------------------------------------------------
    # Step 2: Rename migrated table to staging name.
    # Clean up any leftover staging table from a prior failed run first.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text("DROP TABLE IF EXISTS _artifact_tags_new")
    )
    connection.execute(
        sa.text(
            "ALTER TABLE artifact_tags "
            "RENAME TO _artifact_tags_new"
        )
    )

    # ------------------------------------------------------------------
    # Step 3: Recreate original table schema (no artifact_uuid, no FK to
    # artifacts).
    # ------------------------------------------------------------------
    connection.execute(
        sa.text(
            """
            CREATE TABLE artifact_tags (
                artifact_id VARCHAR NOT NULL,
                tag_id      VARCHAR NOT NULL,
                created_at  DATETIME NOT NULL,
                PRIMARY KEY (artifact_id, tag_id),
                FOREIGN KEY (tag_id)
                    REFERENCES tags (id)
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
            INSERT INTO artifact_tags
                (artifact_id, tag_id, {_DATA_COLS_SQL})
            SELECT
                n._artifact_id_backup,
                n.tag_id,
                {", ".join(f"n.{c}" for c in _DATA_COLS)}
            FROM _artifact_tags_new n
            """
        )
    )

    # ------------------------------------------------------------------
    # Step 5: Restore original indexes.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text(
            "CREATE INDEX idx_artifact_tags_artifact_id "
            "ON artifact_tags (artifact_id)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX idx_artifact_tags_tag_id "
            "ON artifact_tags (tag_id)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX idx_artifact_tags_created_at "
            "ON artifact_tags (created_at)"
        )
    )

    # ------------------------------------------------------------------
    # Step 6: Drop the staging table.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text("DROP TABLE _artifact_tags_new")
    )
