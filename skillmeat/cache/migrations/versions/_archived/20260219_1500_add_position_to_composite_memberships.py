"""Add position column to composite_memberships table.

Revision ID: 20260219_1500_add_position_to_composite_memberships
Revises: 20260219_1400_drop_artifact_id_backup_columns
Create Date: 2026-02-19 15:00:00.000000+00:00

Summary
-------
Adds a nullable ``position`` column (INTEGER) to ``composite_memberships``.

The column captures the display order of a child artifact within its parent
composite.  It is nullable (rather than NOT NULL with a default) so that
existing membership rows continue to work without a data migration step — the
application treats ``NULL`` as "unordered" and places unordered members after
explicitly positioned ones.

SQLite Compatibility
--------------------
SQLite supports ``ALTER TABLE ... ADD COLUMN`` for nullable columns with no
``DEFAULT`` expression, which is exactly what we need here.  No table-rebuild
is required.
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

log = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "20260219_1500_add_position_to_composite_memberships"
down_revision: Union[str, None] = "20260219_1400_drop_artifact_id_backup_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable position column to composite_memberships."""
    connection = op.get_bind()

    log.info(
        "CUX-P1-06: Adding position column to composite_memberships"
    )

    # SQLite supports ADD COLUMN for nullable columns — no rebuild required.
    connection.execute(
        sa.text(
            "ALTER TABLE composite_memberships "
            "ADD COLUMN position INTEGER NULL"
        )
    )

    log.info(
        "CUX-P1-06: position column added to composite_memberships successfully"
    )


def downgrade() -> None:
    """Remove position column from composite_memberships.

    SQLite < 3.35.0 does not support DROP COLUMN, so we use the
    rename → create → copy → drop pattern for maximum compatibility.
    """
    connection = op.get_bind()

    log.info(
        "CUX-P1-06 downgrade: Removing position column from composite_memberships"
    )

    # Step 1: Drop any existing indexes on composite_memberships.
    connection.execute(
        sa.text(
            "DROP INDEX IF EXISTS idx_composite_memberships_composite_id"
        )
    )
    connection.execute(
        sa.text(
            "DROP INDEX IF EXISTS idx_composite_memberships_child_uuid"
        )
    )

    # Step 2: Rename live table to staging.
    connection.execute(
        sa.text("DROP TABLE IF EXISTS _composite_memberships_new")
    )
    connection.execute(
        sa.text(
            "ALTER TABLE composite_memberships "
            "RENAME TO _composite_memberships_new"
        )
    )

    # Step 3: Recreate table without position column.
    connection.execute(
        sa.text(
            """
            CREATE TABLE composite_memberships (
                collection_id        VARCHAR NOT NULL,
                composite_id         VARCHAR NOT NULL,
                child_artifact_uuid  VARCHAR NOT NULL,
                relationship_type    VARCHAR NOT NULL DEFAULT 'contains',
                pinned_version_hash  VARCHAR NULL,
                membership_metadata  TEXT NULL,
                created_at           DATETIME NOT NULL,
                PRIMARY KEY (collection_id, composite_id, child_artifact_uuid),
                FOREIGN KEY (composite_id)
                    REFERENCES composite_artifacts (id)
                    ON DELETE CASCADE,
                FOREIGN KEY (child_artifact_uuid)
                    REFERENCES artifacts (uuid)
                    ON DELETE CASCADE
            )
            """
        )
    )

    # Step 4: Copy all rows (excluding position).
    connection.execute(
        sa.text(
            """
            INSERT INTO composite_memberships
                (collection_id, composite_id, child_artifact_uuid,
                 relationship_type, pinned_version_hash,
                 membership_metadata, created_at)
            SELECT
                n.collection_id, n.composite_id, n.child_artifact_uuid,
                n.relationship_type, n.pinned_version_hash,
                n.membership_metadata, n.created_at
            FROM _composite_memberships_new n
            """
        )
    )

    row_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM composite_memberships")
    ).scalar()
    log.info(
        "CUX-P1-06 downgrade: Copied %d composite_memberships rows", row_count
    )

    # Step 5: Recreate indexes.
    connection.execute(
        sa.text(
            "CREATE INDEX idx_composite_memberships_composite_id "
            "ON composite_memberships (composite_id)"
        )
    )
    connection.execute(
        sa.text(
            "CREATE INDEX idx_composite_memberships_child_uuid "
            "ON composite_memberships (child_artifact_uuid)"
        )
    )

    # Step 6: Drop staging table.
    connection.execute(sa.text("DROP TABLE _composite_memberships_new"))

    log.info(
        "CUX-P1-06 downgrade: position column removed from composite_memberships"
    )
