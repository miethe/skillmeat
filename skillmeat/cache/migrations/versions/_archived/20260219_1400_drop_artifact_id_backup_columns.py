"""Drop _artifact_id_backup columns from artifact_tags and group_artifacts.

Revision ID: 20260219_1400_drop_artifact_id_backup_columns
Revises: 20260219_1300_migrate_artifact_tags_to_uuid
Create Date: 2026-02-19 14:00:00.000000+00:00

Summary
-------
Removes the ``_artifact_id_backup`` column from ``artifact_tags`` and
``group_artifacts``.  These columns were added by the CAI-P5-02 and
CAI-P5-03 migrations as a rollback safety net carrying the original
``artifact_id`` string values (type:name format).  The ORM models do not
include them, so any INSERT issued by SQLAlchemy hits a NOT NULL constraint
failure when the column is present but absent from the INSERT column list.

Migration Strategy (full table rebuild)
----------------------------------------
upgrade():
  For each table (artifact_tags, group_artifacts):
  1. Drop all existing indexes.
  2. Rename the live table to a staging name (e.g. ``_artifact_tags_old``).
  3. Create a fresh table with the correct schema (no ``_artifact_id_backup``).
  4. INSERT SELECT all rows from the staging table, excluding the backup col.
  5. Recreate indexes on the new table.
  6. Drop the staging table.

downgrade():
  For each table:
  1. Drop all current indexes.
  2. Rename the live table to a staging name.
  3. Recreate the table WITH ``_artifact_id_backup`` (VARCHAR NOT NULL).
  4. INSERT SELECT all rows, filling ``_artifact_id_backup`` with an empty
     string (the original artifact_id values are gone at this point; the
     column is required only for structural compatibility with the previous
     revision, not for functional rollback to the pre-P5 schema).
  5. Recreate indexes.
  6. Drop the staging table.

SQLite Compatibility
--------------------
SQLite does not support ALTER TABLE ... DROP COLUMN on versions prior to
3.35.0 (and the semantics differ even there).  This migration avoids
DROP COLUMN entirely by using the classic "rename → create new →
INSERT SELECT → drop old" pattern, which is compatible with all SQLite
versions.  This is the same approach used by the P5-01 through P5-03
migrations.

The global ``render_as_batch=True`` in env.py applies only to
``batch_alter_table`` calls; the raw SQL path below bypasses it and is
fully compatible with both SQLite and PostgreSQL.
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


log = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "20260219_1400_drop_artifact_id_backup_columns"
down_revision: Union[str, None] = "20260219_1300_migrate_artifact_tags_to_uuid"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Data columns for artifact_tags (excluding PK parts and backup col).
_AT_DATA_COLS = ("created_at",)
_AT_DATA_COLS_SQL = ", ".join(_AT_DATA_COLS)

# Data columns for group_artifacts (excluding PK parts and backup col).
_GA_DATA_COLS = ("position", "added_at")
_GA_DATA_COLS_SQL = ", ".join(_GA_DATA_COLS)


# ---------------------------------------------------------------------------
# artifact_tags helpers
# ---------------------------------------------------------------------------

_AT_INDEXES = (
    "idx_artifact_tags_artifact_uuid",
    "idx_artifact_tags_tag_id",
    "idx_artifact_tags_created_at",
)


def _drop_artifact_tags_indexes(connection: sa.engine.Connection) -> None:
    for idx in _AT_INDEXES:
        connection.execute(sa.text(f"DROP INDEX IF EXISTS {idx}"))


def _recreate_artifact_tags_indexes(connection: sa.engine.Connection) -> None:
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


# ---------------------------------------------------------------------------
# group_artifacts helpers
# ---------------------------------------------------------------------------

_GA_INDEXES = (
    "idx_group_artifacts_artifact_uuid",
    "idx_group_artifacts_group_id",
    "idx_group_artifacts_group_position",
    "idx_group_artifacts_added_at",
)


def _drop_group_artifacts_indexes(connection: sa.engine.Connection) -> None:
    for idx in _GA_INDEXES:
        connection.execute(sa.text(f"DROP INDEX IF EXISTS {idx}"))


def _recreate_group_artifacts_indexes(connection: sa.engine.Connection) -> None:
    connection.execute(
        sa.text(
            "CREATE INDEX idx_group_artifacts_group_id "
            "ON group_artifacts (group_id)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX idx_group_artifacts_artifact_uuid "
            "ON group_artifacts (artifact_uuid)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX idx_group_artifacts_group_position "
            "ON group_artifacts (group_id, position)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX idx_group_artifacts_added_at "
            "ON group_artifacts (added_at)"
        )
    )


# ===========================================================================
# upgrade
# ===========================================================================


def upgrade() -> None:
    """Remove _artifact_id_backup from artifact_tags and group_artifacts.

    Steps (per table):
      1. Drop all existing indexes.
      2. Rename live table to staging name.
      3. Create new table without _artifact_id_backup.
      4. INSERT SELECT (excluding _artifact_id_backup).
      5. Recreate indexes.
      6. Drop staging table.
    """
    connection = op.get_bind()

    # -----------------------------------------------------------------------
    # artifact_tags
    # -----------------------------------------------------------------------
    log.info("CAI-P5-08b: Rebuilding artifact_tags without _artifact_id_backup")

    # Step 1: Drop indexes.
    _drop_artifact_tags_indexes(connection)

    # Step 2: Rename to staging; clean up any prior failed run.
    connection.execute(sa.text("DROP TABLE IF EXISTS _artifact_tags_old"))
    connection.execute(
        sa.text("ALTER TABLE artifact_tags RENAME TO _artifact_tags_old")
    )

    # Step 3: Create new table without _artifact_id_backup.
    connection.execute(
        sa.text(
            """
            CREATE TABLE artifact_tags (
                artifact_uuid  VARCHAR NOT NULL,
                tag_id         VARCHAR NOT NULL,
                created_at     DATETIME NOT NULL,
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

    # Step 4: Copy all rows, excluding _artifact_id_backup.
    connection.execute(
        sa.text(
            f"""
            INSERT INTO artifact_tags
                (artifact_uuid, tag_id, {_AT_DATA_COLS_SQL})
            SELECT
                o.artifact_uuid,
                o.tag_id,
                {", ".join(f"o.{c}" for c in _AT_DATA_COLS)}
            FROM _artifact_tags_old o
            """
        )
    )

    at_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM artifact_tags")
    ).scalar()
    log.info("CAI-P5-08b: Copied %d artifact_tags rows", at_count)

    # Step 5: Recreate indexes.
    _recreate_artifact_tags_indexes(connection)

    # Step 6: Drop staging table.
    connection.execute(sa.text("DROP TABLE _artifact_tags_old"))

    # -----------------------------------------------------------------------
    # group_artifacts
    # -----------------------------------------------------------------------
    log.info(
        "CAI-P5-08b: Rebuilding group_artifacts without _artifact_id_backup"
    )

    # Step 1: Drop indexes.
    _drop_group_artifacts_indexes(connection)

    # Step 2: Rename to staging; clean up any prior failed run.
    connection.execute(sa.text("DROP TABLE IF EXISTS _group_artifacts_old"))
    connection.execute(
        sa.text("ALTER TABLE group_artifacts RENAME TO _group_artifacts_old")
    )

    # Step 3: Create new table without _artifact_id_backup.
    connection.execute(
        sa.text(
            """
            CREATE TABLE group_artifacts (
                group_id       VARCHAR NOT NULL,
                artifact_uuid  VARCHAR NOT NULL,
                position       INTEGER NOT NULL DEFAULT 0,
                added_at       DATETIME NOT NULL,
                PRIMARY KEY (group_id, artifact_uuid),
                CONSTRAINT fk_group_artifacts_artifact_uuid
                    FOREIGN KEY (artifact_uuid)
                    REFERENCES artifacts (uuid)
                    ON DELETE CASCADE,
                FOREIGN KEY (group_id)
                    REFERENCES groups (id)
                    ON DELETE CASCADE,
                CONSTRAINT check_group_artifact_position
                    CHECK (position >= 0)
            )
            """
        )
    )

    # Step 4: Copy all rows, excluding _artifact_id_backup.
    connection.execute(
        sa.text(
            f"""
            INSERT INTO group_artifacts
                (group_id, artifact_uuid, {_GA_DATA_COLS_SQL})
            SELECT
                o.group_id,
                o.artifact_uuid,
                {", ".join(f"o.{c}" for c in _GA_DATA_COLS)}
            FROM _group_artifacts_old o
            """
        )
    )

    ga_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM group_artifacts")
    ).scalar()
    log.info("CAI-P5-08b: Copied %d group_artifacts rows", ga_count)

    # Step 5: Recreate indexes.
    _recreate_group_artifacts_indexes(connection)

    # Step 6: Drop staging table.
    connection.execute(sa.text("DROP TABLE _group_artifacts_old"))


# ===========================================================================
# downgrade
# ===========================================================================


def downgrade() -> None:
    """Restore _artifact_id_backup column to artifact_tags and group_artifacts.

    The original artifact_id string values (type:name format) are gone at
    this point.  The backup column is recreated with an empty-string default
    so that the schema matches the previous revision (P5-03 / P5-02) and the
    migration chain can be re-applied if needed.

    Steps (per table):
      1. Drop all current indexes.
      2. Rename live table to staging name.
      3. Create table WITH _artifact_id_backup (VARCHAR NOT NULL default '').
      4. INSERT SELECT all rows, setting _artifact_id_backup = ''.
      5. Recreate indexes.
      6. Drop staging table.
    """
    connection = op.get_bind()

    # -----------------------------------------------------------------------
    # artifact_tags
    # -----------------------------------------------------------------------
    log.info(
        "CAI-P5-08b downgrade: Restoring _artifact_id_backup to artifact_tags"
    )

    # Step 1: Drop indexes.
    _drop_artifact_tags_indexes(connection)

    # Step 2: Rename to staging; clean up any prior failed run.
    connection.execute(sa.text("DROP TABLE IF EXISTS _artifact_tags_new"))
    connection.execute(
        sa.text("ALTER TABLE artifact_tags RENAME TO _artifact_tags_new")
    )

    # Step 3: Recreate table with _artifact_id_backup (empty string default).
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

    # Step 4: Copy rows; _artifact_id_backup is filled with empty string.
    connection.execute(
        sa.text(
            f"""
            INSERT INTO artifact_tags
                (artifact_uuid, tag_id, _artifact_id_backup, {_AT_DATA_COLS_SQL})
            SELECT
                n.artifact_uuid,
                n.tag_id,
                '',
                {", ".join(f"n.{c}" for c in _AT_DATA_COLS)}
            FROM _artifact_tags_new n
            """
        )
    )

    # Step 5: Recreate indexes.
    _recreate_artifact_tags_indexes(connection)

    # Step 6: Drop staging table.
    connection.execute(sa.text("DROP TABLE _artifact_tags_new"))

    # -----------------------------------------------------------------------
    # group_artifacts
    # -----------------------------------------------------------------------
    log.info(
        "CAI-P5-08b downgrade: Restoring _artifact_id_backup to group_artifacts"
    )

    # Step 1: Drop indexes.
    _drop_group_artifacts_indexes(connection)

    # Step 2: Rename to staging; clean up any prior failed run.
    connection.execute(sa.text("DROP TABLE IF EXISTS _group_artifacts_new"))
    connection.execute(
        sa.text("ALTER TABLE group_artifacts RENAME TO _group_artifacts_new")
    )

    # Step 3: Recreate table with _artifact_id_backup.
    connection.execute(
        sa.text(
            """
            CREATE TABLE group_artifacts (
                group_id            VARCHAR NOT NULL,
                artifact_uuid       VARCHAR NOT NULL,
                _artifact_id_backup VARCHAR NOT NULL,
                position            INTEGER NOT NULL DEFAULT 0,
                added_at            DATETIME NOT NULL,
                PRIMARY KEY (group_id, artifact_uuid),
                CONSTRAINT fk_group_artifacts_artifact_uuid
                    FOREIGN KEY (artifact_uuid)
                    REFERENCES artifacts (uuid)
                    ON DELETE CASCADE,
                FOREIGN KEY (group_id)
                    REFERENCES groups (id)
                    ON DELETE CASCADE,
                CONSTRAINT check_group_artifact_position
                    CHECK (position >= 0)
            )
            """
        )
    )

    # Step 4: Copy rows; _artifact_id_backup is filled with empty string.
    connection.execute(
        sa.text(
            f"""
            INSERT INTO group_artifacts
                (group_id, artifact_uuid, _artifact_id_backup, {_GA_DATA_COLS_SQL})
            SELECT
                n.group_id,
                n.artifact_uuid,
                '',
                {", ".join(f"n.{c}" for c in _GA_DATA_COLS)}
            FROM _group_artifacts_new n
            """
        )
    )

    # Step 5: Recreate indexes.
    _recreate_group_artifacts_indexes(connection)

    # Step 6: Drop staging table.
    connection.execute(sa.text("DROP TABLE _group_artifacts_new"))
