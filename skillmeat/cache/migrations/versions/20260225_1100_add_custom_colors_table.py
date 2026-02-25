"""Add custom_colors table for the site-wide color palette registry.

Revision ID: 20260225_1100_add_custom_colors_table
Revises: 20260225_1000_add_deployment_set_tags_junction
Create Date: 2026-02-25 11:00:00.000000+00:00

Background
----------
Part of the color-icon-management feature.  Users can maintain a personal
palette of custom hex colors that appear alongside the curated preset swatches
in the site-wide color picker.  Each color is uniquely identified by its hex
code (``#rrggbb`` or ``#rgb``) and may carry an optional human-readable label.

Table created
-------------
``custom_colors``
    - ``id`` (String, primary key, UUID hex)
    - ``hex`` (String(7), NOT NULL, UNIQUE) — CSS hex string e.g. ``#7c3aed``
    - ``name`` (String(64), nullable) — optional human-readable label
    - ``created_at`` (DateTime, NOT NULL) — UTC timestamp of first registration
    - CheckConstraint: ``hex LIKE '#______' OR hex LIKE '#___'``
      (7-char or 4-char hex strings accepted)
    - Indexes: ``idx_custom_colors_hex`` (UNIQUE)

Rollback
--------
Drop ``custom_colors``.  No other tables or columns are modified.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision: str = "20260225_1100_add_custom_colors_table"
down_revision: Union[str, None] = "20260225_1000_add_deployment_set_tags_junction"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create custom_colors table with hex uniqueness constraint and index."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_tables = inspector.get_table_names()

    if "custom_colors" not in existing_tables:
        op.create_table(
            "custom_colors",
            sa.Column(
                "id",
                sa.String(),
                primary_key=True,
                comment="Unique color identifier (UUID hex)",
            ),
            sa.Column(
                "hex",
                sa.String(7),
                nullable=False,
                comment="CSS hex color string including leading '#', e.g. #7c3aed",
            ),
            sa.Column(
                "name",
                sa.String(64),
                nullable=True,
                comment="Optional human-readable label for the color",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                comment="UTC timestamp when the color was first registered",
            ),
            sa.CheckConstraint(
                "hex LIKE '#______' OR hex LIKE '#___'",
                name="check_custom_color_hex_format",
            ),
        )

        op.create_index(
            "idx_custom_colors_hex",
            "custom_colors",
            ["hex"],
            unique=True,
        )


def downgrade() -> None:
    """Drop custom_colors table.

    All stored custom color entries will be permanently lost.
    """
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_tables = inspector.get_table_names()

    if "custom_colors" in existing_tables:
        existing_indexes = {
            idx["name"] for idx in inspector.get_indexes("custom_colors")
        }
        if "idx_custom_colors_hex" in existing_indexes:
            op.drop_index("idx_custom_colors_hex", table_name="custom_colors")
        op.drop_table("custom_colors")
