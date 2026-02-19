"""Fix collection_artifacts PRIMARY KEY to (collection_id, artifact_uuid) (CAI-P5-01 repair).

Revision ID: 20260219_1100_fix_collection_artifacts_pk
Revises: 20260219_1000_migrate_collection_artifacts_to_uuid
Create Date: 2026-02-19 11:00:00.000000+00:00

Background
----------
The preceding migration (20260219_1000) was initially written using
Alembic's ``batch_alter_table`` with ``copy_from``.  Due to how SQLite's
batch rebuild carries through the PRIMARY KEY of the current table at each
step, the original ``(collection_id, artifact_id)`` PK became
``(collection_id, _artifact_id_backup)`` after the rename step — and was
then preserved unchanged through subsequent batch rebuilds, leaving
``artifact_uuid`` as a non-PK column.

The ORM model (``CollectionArtifact``) declares
``(collection_id, artifact_uuid)`` as the composite PK.  A fresh install
running the corrected ``20260219_1000`` migration will get the right schema;
this repair migration fixes existing databases that ran the original version.

This migration is idempotent with respect to data: no rows are added or
deleted.  It is a pure schema cleanup.

What this migration does
------------------------
upgrade():
  1. Check whether the PK is already ``(collection_id, artifact_uuid)``; if
     so, skip (idempotent guard).
  2. Rename the live table to a staging name.
  3. Recreate ``collection_artifacts`` with the correct schema:
     PRIMARY KEY (collection_id, artifact_uuid), dropping
     ``_artifact_id_backup`` (no longer needed after PK is correct).
  4. Copy data (excluding the backup column).
  5. Recreate indexes.
  6. Drop the staging table.

downgrade():
  Restores the post-20260219_1000 schema (before this repair):
  - Adds ``_artifact_id_backup`` back (filled from ``artifact_uuid``).
  - Restores PK ``(collection_id, _artifact_id_backup)``.
  Note: original string values of ``_artifact_id_backup`` are no longer
  available; the column is filled with ``artifact_uuid`` as a placeholder
  so the earlier downgrade can clean up.
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


log = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "20260219_1100_fix_collection_artifacts_pk"
down_revision: Union[str, None] = "20260219_1000_migrate_collection_artifacts_to_uuid"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Ordered data columns shared between upgrade() and downgrade().
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


def _get_pk_columns(connection: sa.engine.Connection) -> list[str]:
    """Return the current PRIMARY KEY column names for collection_artifacts."""
    rows = connection.execute(
        sa.text("PRAGMA table_info(collection_artifacts)")
    ).fetchall()
    # PRAGMA table_info columns: cid, name, type, notnull, dflt_value, pk
    # pk > 0 means part of PK; pk value is the 1-based ordinal position.
    pk_cols = sorted(
        [(row[5], row[1]) for row in rows if row[5] > 0],
        key=lambda x: x[0],
    )
    return [col for _, col in pk_cols]


def upgrade() -> None:
    """Repair collection_artifacts: set correct PK and drop backup column.

    Steps:
      1. Idempotent guard: skip if PK is already (collection_id, artifact_uuid).
      2. Rename collection_artifacts → staging table.
      3. Recreate collection_artifacts with correct PK, no _artifact_id_backup.
      4. Copy data from staging.
      5. Recreate indexes.
      6. Drop staging table.
    """
    connection = op.get_bind()

    # ------------------------------------------------------------------
    # Step 1: Idempotent guard.
    # Check both PK correctness and absence of _artifact_id_backup.
    # Both must be satisfied before we can skip the rebuild.
    # ------------------------------------------------------------------
    current_pk = _get_pk_columns(connection)
    col_names = [
        row[1]
        for row in connection.execute(
            sa.text("PRAGMA table_info(collection_artifacts)")
        ).fetchall()
    ]
    has_backup_col = "_artifact_id_backup" in col_names
    pk_correct = current_pk == ["collection_id", "artifact_uuid"]

    if pk_correct and not has_backup_col:
        log.info(
            "CAI-P5-01 repair: collection_artifacts already has correct PK "
            "(collection_id, artifact_uuid) and no _artifact_id_backup; skipping."
        )
        return

    log.info(
        "CAI-P5-01 repair: current PK=%r has_backup=%r; rebuilding.",
        current_pk,
        has_backup_col,
    )

    # ------------------------------------------------------------------
    # Step 2: Drop all existing indexes on collection_artifacts before the
    # rename.  Use IF EXISTS so this step is safe even if an index was
    # already dropped by a prior partial run.
    # ------------------------------------------------------------------
    for idx in (
        "idx_collection_artifacts_collection_id",
        "idx_collection_artifacts_artifact_uuid",
        "idx_collection_artifacts_artifact_id",
        "idx_collection_artifacts_added_at",
        "idx_collection_artifacts_synced_at",
        "idx_collection_artifacts_tools_json",
    ):
        connection.execute(sa.text(f"DROP INDEX IF EXISTS {idx}"))

    # ------------------------------------------------------------------
    # Step 3: Rename live table to staging.
    # Clean up any leftover staging table from a prior failed run first.
    # ------------------------------------------------------------------
    connection.execute(sa.text("DROP TABLE IF EXISTS _ca_repair_staging"))
    connection.execute(
        sa.text(
            "ALTER TABLE collection_artifacts "
            "RENAME TO _ca_repair_staging"
        )
    )

    # ------------------------------------------------------------------
    # Step 4: Recreate table with correct schema (no _artifact_id_backup).
    # ------------------------------------------------------------------
    connection.execute(
        sa.text(
            """
            CREATE TABLE collection_artifacts (
                collection_id   VARCHAR NOT NULL,
                artifact_uuid   VARCHAR NOT NULL,
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
    # Step 5: Copy data from staging (drop _artifact_id_backup).
    # ------------------------------------------------------------------
    connection.execute(
        sa.text(
            f"""
            INSERT INTO collection_artifacts
                (collection_id, artifact_uuid, {_DATA_COLS_SQL})
            SELECT
                collection_id,
                artifact_uuid,
                {_DATA_COLS_SQL}
            FROM _ca_repair_staging
            """
        )
    )

    copied = connection.execute(
        sa.text("SELECT COUNT(*) FROM collection_artifacts")
    ).scalar()
    log.info("CAI-P5-01 repair: copied %d rows into repaired table.", copied)

    # ------------------------------------------------------------------
    # Step 6: Recreate indexes.
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
    # Step 7: Drop staging table.
    # ------------------------------------------------------------------
    connection.execute(sa.text("DROP TABLE _ca_repair_staging"))

    log.info(
        "CAI-P5-01 repair: collection_artifacts PRIMARY KEY is now "
        "(collection_id, artifact_uuid); _artifact_id_backup removed."
    )


def downgrade() -> None:
    """Restore the post-20260219_1000 schema (before this repair).

    Restores ``_artifact_id_backup`` (filled from ``artifact_uuid``) and
    sets PK back to ``(collection_id, _artifact_id_backup)``.

    Note: the original type:name string values that were in
    ``_artifact_id_backup`` before the repair are no longer available.
    The column is re-populated with ``artifact_uuid`` values as a
    placeholder; the 20260219_1000 downgrade() will subsequently rename
    ``_artifact_id_backup`` → ``artifact_id`` and drop ``artifact_uuid``.
    """
    connection = op.get_bind()

    # ------------------------------------------------------------------
    # Step 1: Drop all current indexes before rename.
    # ------------------------------------------------------------------
    for idx in (
        "idx_collection_artifacts_collection_id",
        "idx_collection_artifacts_artifact_uuid",
        "idx_collection_artifacts_added_at",
        "idx_collection_artifacts_synced_at",
        "idx_collection_artifacts_tools_json",
    ):
        connection.execute(sa.text(f"DROP INDEX IF EXISTS {idx}"))

    # ------------------------------------------------------------------
    # Step 2: Rename repaired table to staging.
    # Clean up any leftover staging table from a prior failed run first.
    # ------------------------------------------------------------------
    connection.execute(sa.text("DROP TABLE IF EXISTS _ca_downgrade_staging"))
    connection.execute(
        sa.text(
            "ALTER TABLE collection_artifacts "
            "RENAME TO _ca_downgrade_staging"
        )
    )

    # ------------------------------------------------------------------
    # Step 3: Recreate the post-20260219_1000 schema with _artifact_id_backup
    # as part of the PK and artifact_uuid as a regular NOT NULL column.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text(
            """
            CREATE TABLE collection_artifacts (
                collection_id       VARCHAR NOT NULL,
                _artifact_id_backup VARCHAR NOT NULL,
                artifact_uuid       VARCHAR NOT NULL,
                added_at            DATETIME NOT NULL,
                description         TEXT,
                author              VARCHAR,
                license             VARCHAR,
                tags_json           TEXT,
                version             VARCHAR,
                source              VARCHAR,
                origin              VARCHAR,
                origin_source       VARCHAR,
                resolved_sha        VARCHAR(64),
                resolved_version    VARCHAR,
                synced_at           DATETIME,
                tools_json          TEXT,
                deployments_json    TEXT,
                PRIMARY KEY (collection_id, _artifact_id_backup),
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
    # Step 4: Copy data; fill _artifact_id_backup from artifact_uuid since
    # original string values are no longer available.
    # ------------------------------------------------------------------
    connection.execute(
        sa.text(
            f"""
            INSERT INTO collection_artifacts
                (collection_id, _artifact_id_backup, artifact_uuid,
                 {_DATA_COLS_SQL})
            SELECT
                collection_id,
                artifact_uuid,
                artifact_uuid,
                {_DATA_COLS_SQL}
            FROM _ca_downgrade_staging
            """
        )
    )

    # ------------------------------------------------------------------
    # Step 5: Recreate indexes matching the post-20260219_1000 state.
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
            "CREATE INDEX idx_collection_artifacts_artifact_id "
            "ON collection_artifacts (_artifact_id_backup)"
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
    # Step 6: Drop staging table.
    # ------------------------------------------------------------------
    connection.execute(sa.text("DROP TABLE _ca_downgrade_staging"))
