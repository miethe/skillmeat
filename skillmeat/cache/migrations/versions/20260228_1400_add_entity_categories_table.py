"""Add entity_categories table and entity_category_associations join table.

Revision ID: 20260228_1400_add_entity_categories_table
Revises: 20260228_1000_add_entity_type_configs_table
Create Date: 2026-02-28 14:00:00.000000+00:00

Background
----------
Context entity artifacts (skills, rules, specs, etc.) currently carry only a
free-text ``category`` string column on the ``artifacts`` table.  That column
remains untouched by this migration (purely additive).

This migration introduces a proper relational category system consisting of two
tables:

``entity_categories``
    Master list of named categories with optional scoping by entity type and/or
    platform.  Categories may be built-in (system-seeded) or user-defined.

``entity_category_associations``
    Many-to-many join table linking ``artifacts.uuid`` to
    ``entity_categories.id``.  Uses the stable ``artifacts.uuid`` column
    (rather than ``artifacts.id``) consistent with ``artifact_tags`` and
    other join tables in this schema (see ADR-007).

Tables created
--------------
``entity_categories``
  - ``id``                INTEGER  PK, AUTOINCREMENT
  - ``name``              TEXT(100) NOT NULL           human-readable label
  - ``slug``              TEXT(100) NOT NULL, UNIQUE   URL-safe identifier
  - ``description``       TEXT     nullable
  - ``color``             TEXT(7)  nullable            hex colour, e.g. "#3B82F6"
  - ``entity_type_slug``  TEXT(50) nullable            optional type scope
  - ``platform``          TEXT(50) nullable            optional platform scope
  - ``sort_order``        INTEGER  NOT NULL  default 0
  - ``is_builtin``        BOOLEAN  NOT NULL  default 0 (False)
  - ``created_at``        DATETIME NOT NULL
  - ``updated_at``        DATETIME NOT NULL

``entity_category_associations``
  - ``artifact_uuid``  TEXT  PK, FK → artifacts.uuid  CASCADE DELETE
  - ``category_id``    INTEGER  PK, FK → entity_categories.id  CASCADE DELETE
  - ``created_at``     DATETIME NOT NULL

Indexes
-------
``entity_categories``
  - ``uq_entity_categories_slug``                    UNIQUE on (slug)
  - ``idx_entity_categories_entity_type_platform``   on (entity_type_slug, platform)
  - ``idx_entity_categories_sort_order``             on (sort_order)
  - ``idx_entity_categories_is_builtin``             on (is_builtin)

``entity_category_associations``
  - ``idx_artifact_category_assoc_artifact_uuid``    on (artifact_uuid)
  - ``idx_artifact_category_assoc_category_id``      on (category_id)

Existing columns
----------------
The existing ``artifacts.category`` TEXT column is NOT modified.  The two
systems coexist; the relational table is the preferred path for new UI code.

Rollback
--------
Drop ``entity_category_associations`` first (FK dependency), then drop
``entity_categories`` and all associated indexes.  No other tables are
modified.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260228_1400_add_entity_categories_table"
down_revision: Union[str, None] = "20260228_1000_add_entity_type_configs_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create entity_categories and entity_category_associations tables.

    Purely additive — no existing tables or columns are modified.
    The existing artifacts.category TEXT column is preserved as-is.
    """
    # ------------------------------------------------------------------
    # 1. entity_categories — master category table
    # ------------------------------------------------------------------
    op.create_table(
        "entity_categories",
        # Primary key
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Identity fields
        sa.Column(
            "name",
            sa.String(100),
            nullable=False,
            comment="Human-readable label shown in the UI, e.g. 'Testing Utilities'",
        ),
        sa.Column(
            "slug",
            sa.String(100),
            nullable=False,
            comment="URL-safe machine identifier, e.g. 'testing-utilities'",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Optional longer description of the category's purpose",
        ),
        # Display hints
        sa.Column(
            "color",
            sa.String(7),
            nullable=True,
            comment="Hex colour code for UI badge rendering, e.g. '#3B82F6'",
        ),
        # Optional scope filters
        sa.Column(
            "entity_type_slug",
            sa.String(50),
            nullable=True,
            comment=(
                "When set, restrict this category to artifacts whose entity type "
                "matches this slug (e.g. 'skill', 'rule_file')"
            ),
        ),
        sa.Column(
            "platform",
            sa.String(50),
            nullable=True,
            comment=(
                "When set, restrict this category to artifacts targeting this "
                "platform (e.g. 'github-actions', 'cursor')"
            ),
        ),
        # Metadata flags
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Ascending display order in the UI",
        ),
        sa.Column(
            "is_builtin",
            sa.Boolean(),
            nullable=False,
            server_default="0",
            comment="True for system-seeded categories protected from deletion",
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
        "uq_entity_categories_slug",
        "entity_categories",
        ["slug"],
    )

    # Index: fast lookup by slug (also serves the unique constraint)
    op.create_index(
        "idx_entity_categories_slug",
        "entity_categories",
        ["slug"],
        unique=True,
    )

    # Index: composite filter by entity type + platform
    op.create_index(
        "idx_entity_categories_entity_type_platform",
        "entity_categories",
        ["entity_type_slug", "platform"],
    )

    # Index: ordered listing queries (e.g. Settings UI category picker)
    op.create_index(
        "idx_entity_categories_sort_order",
        "entity_categories",
        ["sort_order"],
    )

    # Index: filter built-in vs. user-defined categories
    op.create_index(
        "idx_entity_categories_is_builtin",
        "entity_categories",
        ["is_builtin"],
    )

    # ------------------------------------------------------------------
    # 2. entity_category_associations — many-to-many join table
    # ------------------------------------------------------------------
    # Uses artifacts.uuid (stable cross-context identity, ADR-007) rather than
    # artifacts.id, consistent with artifact_tags and other join tables.
    op.create_table(
        "entity_category_associations",
        sa.Column(
            "artifact_uuid",
            sa.String(),
            sa.ForeignKey("artifacts.uuid", ondelete="CASCADE"),
            primary_key=True,
            comment="FK to artifacts.uuid; CASCADE DELETE removes associations when artifact is deleted",
        ),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("entity_categories.id", ondelete="CASCADE"),
            primary_key=True,
            comment="FK to entity_categories.id; CASCADE DELETE removes associations when category is deleted",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            comment="Timestamp when category was applied to artifact (UTC)",
        ),
    )

    # Index: fast reverse lookup — given an artifact, find all its categories
    op.create_index(
        "idx_artifact_category_assoc_artifact_uuid",
        "entity_category_associations",
        ["artifact_uuid"],
    )

    # Index: fast forward lookup — given a category, find all its artifacts
    op.create_index(
        "idx_artifact_category_assoc_category_id",
        "entity_category_associations",
        ["category_id"],
    )


def downgrade() -> None:
    """Drop entity_category_associations and entity_categories tables.

    The join table must be dropped before the category table due to FK
    constraints.  The existing artifacts.category TEXT column is untouched.
    """
    # Drop join table first (FK dependency on entity_categories.id)
    op.drop_index(
        "idx_artifact_category_assoc_category_id", "entity_category_associations"
    )
    op.drop_index(
        "idx_artifact_category_assoc_artifact_uuid", "entity_category_associations"
    )
    op.drop_table("entity_category_associations")

    # Drop master category table
    op.drop_index("idx_entity_categories_is_builtin", "entity_categories")
    op.drop_index("idx_entity_categories_sort_order", "entity_categories")
    op.drop_index("idx_entity_categories_entity_type_platform", "entity_categories")
    op.drop_index("idx_entity_categories_slug", "entity_categories")
    op.drop_constraint("uq_entity_categories_slug", "entity_categories", type_="unique")
    op.drop_table("entity_categories")
