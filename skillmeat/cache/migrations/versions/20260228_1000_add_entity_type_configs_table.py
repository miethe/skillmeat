"""Add entity_type_configs table for DB-backed context entity type definitions.

Revision ID: 20260228_1000_add_entity_type_configs_table
Revises: 20260227_0900_add_workflow_tables
Create Date: 2026-02-28 10:00:00.000000+00:00

Background
----------
The five context entity types (project_config, spec_file, rule_file,
context_file, progress_template) were previously defined only in code via
``skillmeat/core/validators/context_entity.py`` and
``skillmeat/core/platform_defaults.py``.

This migration introduces the ``entity_type_configs`` table so that entity type
definitions can be managed at runtime (e.g. via a future Settings UI) and
queried consistently from the DB cache without walking the filesystem or
importing validator code.

The initial five rows are seeded idempotently at application startup by
``skillmeat/cache/seed_entity_types.py``.

Tables created
--------------
``entity_type_configs``
  - ``id``                      INTEGER  PK, AUTOINCREMENT
  - ``slug``                    TEXT     NOT NULL, UNIQUE (e.g. "skill")
  - ``display_name``            TEXT     NOT NULL
  - ``description``             TEXT     nullable
  - ``icon``                    TEXT     nullable
  - ``path_prefix``             TEXT     nullable  default path prefix
  - ``required_frontmatter_keys`` JSON   nullable  list of required keys
  - ``optional_frontmatter_keys`` JSON   nullable  list of optional keys
  - ``validation_rules``        JSON     nullable  extra validation config
  - ``content_template``        TEXT     nullable  default Markdown template
  - ``is_builtin``              BOOLEAN  NOT NULL  default 1 (True)
  - ``sort_order``              INTEGER  NOT NULL  default 0
  - ``created_at``              DATETIME NOT NULL
  - ``updated_at``              DATETIME NOT NULL

Indexes
-------
  - ``uq_entity_type_configs_slug``         UNIQUE on (slug)
  - ``idx_entity_type_configs_sort_order``  on (sort_order)
  - ``idx_entity_type_configs_is_builtin``  on (is_builtin)

Rollback
--------
Drop ``entity_type_configs`` and all associated indexes. No other tables are
modified by this migration.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260228_1000_add_entity_type_configs_table"
down_revision: Union[str, None] = "20260227_0900_add_workflow_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create entity_type_configs table with indexes.

    Purely additive — no existing tables or columns are modified.
    """
    op.create_table(
        "entity_type_configs",
        # Primary key — auto-incrementing integer
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Identity fields
        sa.Column(
            "slug",
            sa.String(),
            nullable=False,
            comment="Machine-readable unique type identifier, e.g. 'skill'",
        ),
        sa.Column(
            "display_name",
            sa.String(),
            nullable=False,
            comment="Human-readable label shown in the UI",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Optional long-form description of this entity type",
        ),
        sa.Column(
            "icon",
            sa.String(),
            nullable=True,
            comment="Icon identifier for UI rendering",
        ),
        # Path configuration
        sa.Column(
            "path_prefix",
            sa.String(),
            nullable=True,
            comment="Default filesystem path prefix, e.g. '.claude/skills'",
        ),
        # Frontmatter schema stored as JSON arrays/objects
        sa.Column(
            "required_frontmatter_keys",
            sa.JSON(),
            nullable=True,
            comment="JSON array of frontmatter keys that MUST be present",
        ),
        sa.Column(
            "optional_frontmatter_keys",
            sa.JSON(),
            nullable=True,
            comment="JSON array of frontmatter keys that MAY be present",
        ),
        sa.Column(
            "validation_rules",
            sa.JSON(),
            nullable=True,
            comment="JSON object of additional validation configuration",
        ),
        # Content template
        sa.Column(
            "content_template",
            sa.Text(),
            nullable=True,
            comment="Default Markdown template for new entities of this type",
        ),
        # Metadata flags
        sa.Column(
            "is_builtin",
            sa.Boolean(),
            nullable=False,
            server_default="1",
            comment="True for the five shipped types; protected from deletion",
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Ascending display order in the UI",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            comment="Row creation timestamp (UTC)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            comment="Row last-modified timestamp (UTC)",
        ),
    )

    # Unique constraint on slug — enforced at DB level in addition to ORM
    op.create_unique_constraint(
        "uq_entity_type_configs_slug",
        "entity_type_configs",
        ["slug"],
    )

    # Index: fast lookup by slug (also serves the unique constraint)
    op.create_index(
        "idx_entity_type_configs_slug",
        "entity_type_configs",
        ["slug"],
        unique=True,
    )

    # Index: ordered listing queries (e.g. Settings UI dropdown)
    op.create_index(
        "idx_entity_type_configs_sort_order",
        "entity_type_configs",
        ["sort_order"],
    )

    # Index: filter built-in vs. user-defined types
    op.create_index(
        "idx_entity_type_configs_is_builtin",
        "entity_type_configs",
        ["is_builtin"],
    )


def downgrade() -> None:
    """Drop entity_type_configs and its indexes.

    All seeded rows (including the five built-in entity type definitions) will
    be permanently lost. No other tables are affected.
    """
    op.drop_index("idx_entity_type_configs_is_builtin", "entity_type_configs")
    op.drop_index("idx_entity_type_configs_sort_order", "entity_type_configs")
    op.drop_index("idx_entity_type_configs_slug", "entity_type_configs")
    op.drop_constraint(
        "uq_entity_type_configs_slug", "entity_type_configs", type_="unique"
    )
    op.drop_table("entity_type_configs")
