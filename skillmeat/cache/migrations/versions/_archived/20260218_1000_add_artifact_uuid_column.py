"""Add uuid column to artifacts table for stable cross-context identity (ADR-007).

Revision ID: 20260218_1000_add_artifact_uuid_column
Revises: 20260212_1800_add_group_metadata_fields
Create Date: 2026-02-18 10:00:00.000000+00:00

Migration Strategy:
    Phase 1 — Add column as nullable (SQLite supports ADD COLUMN with NULL default).
    Phase 2 — Backfill all existing rows with generated UUIDs.
              Uses lower(hex(randomblob(16))) which produces a 32-char lowercase hex
              string matching Python's uuid.uuid4().hex format (no dashes).
    Phase 3 — Apply NOT NULL constraint via batch_alter_table (required for SQLite;
              Alembic recreates the table under the hood with render_as_batch=True).
    Phase 4 — Create unique index ix_artifacts_uuid.

Background:
    The Artifact ORM model defines uuid as:
        uuid: Mapped[str] = mapped_column(
            String, unique=True, nullable=False,
            default=lambda: uuid.uuid4().hex, index=True
        )
    New rows get their UUID assigned by the ORM layer at insert time.
    Existing rows in the DB have no uuid value and must be backfilled here.

Rollback:
    Drop the unique index, then drop the column via batch_alter_table.
    The uuid column is additive — no other columns or tables are modified.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260218_1000_add_artifact_uuid_column"
down_revision: Union[str, None] = "20260212_1800_add_group_metadata_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add uuid column, backfill existing rows, enforce NOT NULL, create unique index.

    SQLite-safe sequence:
      1. Add column as nullable (no server_default needed — NULL is fine during backfill).
      2. Backfill all rows that have uuid IS NULL using lower(hex(randomblob(16))).
         randomblob(16) produces 16 random bytes; hex() encodes to 32 uppercase hex
         chars; lower() normalises to match uuid.uuid4().hex output.
      3. Alter the column to NOT NULL via batch_alter_table (table rebuild in SQLite).
      4. Create unique index ix_artifacts_uuid inside the same batch operation.
    """
    # Phase 1: Add the column as nullable so existing rows are not rejected.
    with op.batch_alter_table("artifacts", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "uuid",
                sa.String(),
                nullable=True,
                comment="Stable cross-context identity UUID (ADR-007); 32-char hex, no dashes",
            )
        )

    # Phase 2: Backfill all existing rows with a generated UUID.
    # lower(hex(randomblob(16))) produces the same format as uuid.uuid4().hex:
    # 32 lowercase hexadecimal characters, no hyphens.
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE artifacts "
            "SET uuid = lower(hex(randomblob(16))) "
            "WHERE uuid IS NULL"
        )
    )

    # Phase 3 & 4: Apply NOT NULL constraint and create unique index.
    # batch_alter_table triggers a full table rebuild in SQLite, which is the
    # only supported path for adding NOT NULL to an existing column.
    with op.batch_alter_table("artifacts", schema=None) as batch_op:
        batch_op.alter_column(
            "uuid",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.create_index(
            "ix_artifacts_uuid",
            ["uuid"],
            unique=True,
        )


def downgrade() -> None:
    """Drop unique index and remove uuid column from artifacts table."""
    with op.batch_alter_table("artifacts", schema=None) as batch_op:
        batch_op.drop_index("ix_artifacts_uuid")
        batch_op.drop_column("uuid")
