"""Add composite_artifacts and composite_memberships tables (composite artifact infrastructure).

Revision ID: 20260218_1100_add_composite_artifact_tables
Revises: 20260218_1000_add_artifact_uuid_column
Create Date: 2026-02-18 11:00:00.000000+00:00

Background
----------
Part of the composite artifact infrastructure (CAI) feature.  A
CompositeArtifact bundles one or more child artifacts into a single
deployable unit.  CompositeMembership tracks which child artifacts belong
to which composite, referencing each child by its stable UUID column
(``artifacts.uuid``) rather than the mutable ``type:name`` primary key —
satisfying the ADR-007 cross-context identity requirement.

Tables created
--------------
1. ``composite_artifacts``
   - Primary key: ``id`` (String, ``type:name`` format, e.g. ``"composite:my-plugin"``)
   - ``collection_id`` (String, non-null) — owning collection
   - ``composite_type`` (String, non-null, default ``"plugin"``) — variant classifier
   - ``display_name`` (String, nullable) — human-readable label
   - ``description`` (Text, nullable)
   - ``metadata_json`` (Text, nullable) — raw JSON for future extension
   - ``created_at`` / ``updated_at`` (DateTime, non-null)
   - CheckConstraint: composite_type IN ('plugin', 'stack', 'suite')
   - Indexes: ``idx_composite_artifacts_collection_id``,
             ``idx_composite_artifacts_composite_type``

2. ``composite_memberships``
   - Composite primary key: (collection_id, composite_id, child_artifact_uuid)
   - ``composite_id`` → ``composite_artifacts.id`` ON DELETE CASCADE
   - ``child_artifact_uuid`` → ``artifacts.uuid`` ON DELETE CASCADE
     *** FK targets artifacts.uuid, NOT artifacts.id ***
   - ``relationship_type`` (String, default ``"contains"``)
   - ``pinned_version_hash`` (String, nullable)
   - ``membership_metadata`` (Text, nullable)
   - ``created_at`` (DateTime, non-null)
   - Indexes: ``idx_composite_memberships_composite_id``,
             ``idx_composite_memberships_child_uuid``

Rollback
--------
Drop ``composite_memberships`` first (child side of FK), then
``composite_artifacts``.  No other tables or columns are modified.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260218_1100_add_composite_artifact_tables"
down_revision: Union[str, None] = "20260218_1000_add_artifact_uuid_column"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create composite_artifacts then composite_memberships tables.

    Order matters: composite_artifacts must exist before composite_memberships
    can declare its FK to ``composite_artifacts.id``.  Both tables are created
    as new additions; no existing tables or columns are modified.
    """
    # -------------------------------------------------------------------------
    # 1. composite_artifacts
    # -------------------------------------------------------------------------
    op.create_table(
        "composite_artifacts",
        # Primary key — type:name string (e.g., "composite:my-plugin")
        sa.Column("id", sa.String(), primary_key=True),
        # Owning collection identifier (non-null; denormalised on memberships too)
        sa.Column("collection_id", sa.String(), nullable=False),
        # Variant classifier — maps to CompositeType enum
        sa.Column(
            "composite_type",
            sa.String(),
            nullable=False,
            server_default="plugin",
            comment="Composite variant: 'plugin' | 'stack' | 'suite'",
        ),
        # Display fields
        sa.Column(
            "display_name",
            sa.String(),
            nullable=True,
            comment="Human-readable label for the composite",
        ),
        sa.Column("description", sa.Text(), nullable=True),
        # Extensibility — raw JSON string kept as Text to avoid schema churn
        sa.Column(
            "metadata_json",
            sa.Text(),
            nullable=True,
            comment="Raw JSON string for future extension fields",
        ),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # Constraint: only recognised composite types
        sa.CheckConstraint(
            "composite_type IN ('plugin', 'stack', 'suite')",
            name="check_composite_artifact_type",
        ),
    )

    # Indexes on composite_artifacts
    op.create_index(
        "idx_composite_artifacts_collection_id",
        "composite_artifacts",
        ["collection_id"],
    )
    op.create_index(
        "idx_composite_artifacts_composite_type",
        "composite_artifacts",
        ["composite_type"],
    )

    # -------------------------------------------------------------------------
    # 2. composite_memberships
    # -------------------------------------------------------------------------
    # IMPORTANT: child_artifact_uuid FK must reference artifacts.uuid (the stable
    # cross-context identity column added by the previous migration), NOT artifacts.id
    # (the mutable type:name primary key).  Autogenerated migrations sometimes
    # default to the PK; this hand-written migration is explicit.
    op.create_table(
        "composite_memberships",
        # Composite primary key: (collection_id, composite_id, child_artifact_uuid)
        sa.Column("collection_id", sa.String(), primary_key=True, nullable=False),
        sa.Column(
            "composite_id",
            sa.String(),
            sa.ForeignKey("composite_artifacts.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
            comment="FK to composite_artifacts.id — CASCADE DELETE",
        ),
        sa.Column(
            "child_artifact_uuid",
            sa.String(),
            sa.ForeignKey("artifacts.uuid", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
            comment="FK to artifacts.uuid (ADR-007 stable identity) — CASCADE DELETE",
        ),
        # Edge semantics — reserved for future graph-style queries
        sa.Column(
            "relationship_type",
            sa.String(),
            nullable=False,
            server_default="contains",
            comment="Semantic label for the membership edge (default: 'contains')",
        ),
        # Optional version pin — None means "track latest"
        sa.Column(
            "pinned_version_hash",
            sa.String(),
            nullable=True,
            comment="Content hash locking the child to a specific snapshot",
        ),
        # Extensibility — raw JSON string for future per-membership metadata
        sa.Column(
            "membership_metadata",
            sa.Text(),
            nullable=True,
            comment="Raw JSON string for future per-edge metadata",
        ),
        # Timestamp
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Index: fast child lookup by parent composite
    op.create_index(
        "idx_composite_memberships_composite_id",
        "composite_memberships",
        ["composite_id"],
    )
    # Index: reverse lookup — all composites containing a given child artifact
    op.create_index(
        "idx_composite_memberships_child_uuid",
        "composite_memberships",
        ["child_artifact_uuid"],
    )


def downgrade() -> None:
    """Drop composite_memberships then composite_artifacts.

    Tables are dropped in reverse dependency order: the child table
    (composite_memberships) is dropped first so its FK to composite_artifacts
    is removed before the parent table is dropped.  All composite artifact data
    and membership associations will be permanently lost.
    """
    # Drop child table first (FK references composite_artifacts and artifacts)
    op.drop_index("idx_composite_memberships_child_uuid", "composite_memberships")
    op.drop_index("idx_composite_memberships_composite_id", "composite_memberships")
    op.drop_table("composite_memberships")

    # Drop parent table last
    op.drop_index("idx_composite_artifacts_composite_type", "composite_artifacts")
    op.drop_index("idx_composite_artifacts_collection_id", "composite_artifacts")
    op.drop_table("composite_artifacts")
