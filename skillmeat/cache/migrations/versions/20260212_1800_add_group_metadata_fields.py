"""Add metadata fields to groups table.

Revision ID: 20260212_1800_add_group_metadata_fields
Revises: 20260209_1700_add_memory_anchor_and_provenance_columns
Create Date: 2026-02-12 18:00:00.000000+00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260212_1800_add_group_metadata_fields"
down_revision: Union[str, None] = "20260209_1700_add_memory_anchor_and_provenance_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add group metadata fields for management hub UX."""
    op.add_column(
        "groups",
        sa.Column(
            "tags_json",
            sa.Text(),
            nullable=False,
            server_default="[]",
            comment="JSON-serialized list of group-local tags",
        ),
    )
    op.add_column(
        "groups",
        sa.Column(
            "color",
            sa.String(length=32),
            nullable=False,
            server_default="slate",
            comment="Visual accent token for group cards",
        ),
    )
    op.add_column(
        "groups",
        sa.Column(
            "icon",
            sa.String(length=32),
            nullable=False,
            server_default="layers",
            comment="Icon token for group cards",
        ),
    )

    # Explicitly backfill in case SQLite backends preserve nulls for existing rows.
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE groups "
            "SET tags_json = COALESCE(tags_json, '[]'), "
            "color = COALESCE(color, 'slate'), "
            "icon = COALESCE(icon, 'layers')"
        )
    )


def downgrade() -> None:
    """Drop group metadata fields."""
    op.drop_column("groups", "icon")
    op.drop_column("groups", "color")
    op.drop_column("groups", "tags_json")
