"""Add applicable_platforms and frontmatter_schema columns to entity_type_configs.

Revision ID: 20260301_1000_add_custom_type_fields
Revises: 20260228_1400_add_entity_categories_table
Create Date: 2026-03-01 10:00:00.000000+00:00

Background
----------
Phase 5 of the Context Entity Creation Overhaul (CECO-5.1) adds support for
custom entity types.  Two new columns are needed on ``entity_type_configs``:

``applicable_platforms``
    JSON list of platform slugs this type applies to.  ``NULL`` means the type
    is applicable to all platforms.  Allows custom types to be scoped to
    specific deployment targets (e.g. only visible when a Claude Code project
    is detected).

``frontmatter_schema``
    JSON Schema subset (``required`` + ``properties``) used to validate the
    frontmatter of entities with this custom type.  ``NULL`` means no
    structured frontmatter validation is performed beyond the
    ``required_frontmatter_keys`` list already present on the table.

    Expected shape::

        {
            "required": ["title", "version"],
            "properties": {
                "title":   {"type": "string"},
                "version": {"type": "number"}
            }
        }

Both columns are nullable and default to NULL so that all existing rows
(including the five built-in types) are unaffected.

Tables modified
---------------
``entity_type_configs``
  - ADD ``applicable_platforms``  JSON  nullable  (platform scope list)
  - ADD ``frontmatter_schema``    JSON  nullable  (JSON Schema subset)

Rollback
--------
Drop the two columns.  No other tables are affected.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision: str = "20260301_1000_add_custom_type_fields"
down_revision: Union[str, None] = "20260228_1400_add_entity_categories_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add applicable_platforms and frontmatter_schema columns.

    Uses ``sa_inspect`` to check for column existence before adding so the
    migration is idempotent on databases that already have the columns (e.g.
    when ``Base.metadata.create_all()`` was called before migration).
    """
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_columns = {
        col["name"] for col in inspector.get_columns("entity_type_configs")
    }

    if "applicable_platforms" not in existing_columns:
        op.add_column(
            "entity_type_configs",
            sa.Column(
                "applicable_platforms",
                sa.JSON(),
                nullable=True,
                comment=(
                    "JSON list of platform slugs this type applies to. "
                    "NULL means applicable to all platforms."
                ),
            ),
        )

    if "frontmatter_schema" not in existing_columns:
        op.add_column(
            "entity_type_configs",
            sa.Column(
                "frontmatter_schema",
                sa.JSON(),
                nullable=True,
                comment=(
                    "JSON Schema subset for validating custom type frontmatter. "
                    'Structure: {"required": ["key1"], "properties": {"key1": {"type": "string"}}}'
                ),
            ),
        )


def downgrade() -> None:
    """Drop applicable_platforms and frontmatter_schema columns.

    All platform-scope and frontmatter-schema data stored in these columns
    will be permanently lost.  No other tables are affected.
    """
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_columns = {
        col["name"] for col in inspector.get_columns("entity_type_configs")
    }

    if "frontmatter_schema" in existing_columns:
        op.drop_column("entity_type_configs", "frontmatter_schema")

    if "applicable_platforms" in existing_columns:
        op.drop_column("entity_type_configs", "applicable_platforms")
