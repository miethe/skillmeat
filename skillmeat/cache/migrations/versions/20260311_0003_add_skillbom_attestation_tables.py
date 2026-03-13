"""Add SkillBOM attestation tables (skillbom-attestation)

Revision ID: 20260311_0003_add_skillbom_attestation_tables
Revises: ent_008_enterprise_parity_tables
Create Date: 2026-03-11 00:03:00.000000+00:00

Background
----------
skillbom-attestation feature — introduces six new tables supporting
Bill-of-Materials (BOM) generation, attestation records, audit history,
enterprise attestation policies, BOM metadata versioning, and RBAC scope
validation.

Tables Created
--------------
1. ``attestation_records`` — Owner-scoped attestation metadata for an artifact.
   One artifact can have multiple records from different owners.
2. ``artifact_history_events`` — Immutable audit log entries for artifact
   lifecycle events (create, update, delete, deploy, undeploy, sync).
3. ``bom_snapshots`` — Point-in-time BOM snapshots for a project or collection,
   optionally tied to a git commit and cryptographically signed.
4. ``attestation_policies`` — Enterprise policy definitions for enforcing
   attestation requirements (tenant-scoped; nullable in local mode).
5. ``bom_metadata`` — BOM schema/format/generator version metadata, one row
   per BOM generation run.
6. ``scope_validators`` — Authoritative list of recognised RBAC scope patterns
   used to validate scopes on attestation records.

Dialect Strategy
----------------
All six tables are created with dialect-agnostic Alembic operations:
* ``op.create_table()`` — supported by both SQLite and PostgreSQL.
* ``sa.JSON()`` — maps to TEXT on SQLite and JSONB/JSON on PostgreSQL.
* ``sa.Text()`` — long text columns (diff_json, bom_json, etc.).
* ``sa.CheckConstraint()`` — expressed using ANSI SQL ``IN`` predicate,
  which works on both SQLite and PostgreSQL.
* ``create_updated_at_trigger()`` from dialect_helpers — handles SQLite
  AFTER UPDATE triggers and PostgreSQL PL/pgSQL functions/triggers.

Foreign keys reference ``artifacts.id`` via CASCADE delete.  The
``commit_sha`` column on ``bom_snapshots`` carries a non-unique index
(nullable values cannot form a unique constraint reliably across dialects
without partial-index support that SQLite does not provide).

Downgrade
---------
Drops the six tables in reverse dependency order (tables with FKs first,
then standalone tables).  Triggers and trigger functions created by
``create_updated_at_trigger`` are dropped automatically via
``drop_updated_at_trigger``.

Schema reference
----------------
skillmeat/cache/models.py  (AttestationRecord, ArtifactHistoryEvent,
                             BomSnapshot, AttestationPolicy, BomMetadata,
                             ScopeValidator)
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from skillmeat.cache.migrations.dialect_helpers import (
    create_updated_at_trigger,
    drop_updated_at_trigger,
)

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "20260311_0003_add_skillbom_attestation_tables"
down_revision: Union[str, None] = "ent_008_enterprise_parity_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Create the six SkillBOM attestation tables."""

    # ------------------------------------------------------------------
    # 1. attestation_records
    # ------------------------------------------------------------------
    op.create_table(
        "attestation_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "artifact_id",
            sa.String(),
            sa.ForeignKey("artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("owner_type", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("roles", sa.JSON(), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=True),
        sa.Column("visibility", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "idx_attestation_records_owner",
        "attestation_records",
        ["owner_type", "owner_id"],
    )
    op.create_index(
        "idx_attestation_records_artifact_id",
        "attestation_records",
        ["artifact_id"],
    )
    create_updated_at_trigger("attestation_records")

    # ------------------------------------------------------------------
    # 2. artifact_history_events
    # ------------------------------------------------------------------
    op.create_table(
        "artifact_history_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "artifact_id",
            sa.String(),
            sa.ForeignKey("artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=True),
        sa.Column("owner_type", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("diff_json", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.CheckConstraint(
            "event_type IN ('create', 'update', 'delete', 'deploy', 'undeploy', 'sync')",
            name="check_artifact_history_event_type",
        ),
    )
    op.create_index(
        "idx_artifact_history_artifact_ts",
        "artifact_history_events",
        ["artifact_id", "timestamp"],
    )
    op.create_index(
        "idx_artifact_history_type_ts",
        "artifact_history_events",
        ["event_type", "timestamp"],
    )
    op.create_index(
        "idx_artifact_history_actor_id",
        "artifact_history_events",
        ["actor_id"],
    )

    # ------------------------------------------------------------------
    # 3. bom_snapshots
    # ------------------------------------------------------------------
    op.create_table(
        "bom_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("commit_sha", sa.String(), nullable=True),
        sa.Column("bom_json", sa.Text(), nullable=False),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("signature_algorithm", sa.String(), nullable=True),
        sa.Column("owner_type", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "idx_bom_snapshots_project_created",
        "bom_snapshots",
        ["project_id", "created_at"],
    )
    # Non-unique index on commit_sha: nullable unique is not reliably
    # portable across SQLite and PostgreSQL without partial indexes.
    op.create_index(
        "idx_bom_snapshots_commit_sha",
        "bom_snapshots",
        ["commit_sha"],
    )

    # ------------------------------------------------------------------
    # 4. attestation_policies
    # ------------------------------------------------------------------
    op.create_table(
        "attestation_policies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("required_artifacts", sa.JSON(), nullable=True),
        sa.Column("required_scopes", sa.JSON(), nullable=True),
        sa.Column("compliance_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "idx_attestation_policies_tenant_id",
        "attestation_policies",
        ["tenant_id"],
    )
    op.create_index(
        "idx_attestation_policies_name",
        "attestation_policies",
        ["name"],
    )
    create_updated_at_trigger("attestation_policies")

    # ------------------------------------------------------------------
    # 5. bom_metadata
    # ------------------------------------------------------------------
    op.create_table(
        "bom_metadata",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "schema_version",
            sa.String(),
            nullable=False,
            server_default="1.0.0",
        ),
        sa.Column("format_version", sa.String(), nullable=True),
        sa.Column("generator_version", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # ------------------------------------------------------------------
    # 6. scope_validators
    # ------------------------------------------------------------------
    op.create_table(
        "scope_validators",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope_pattern", sa.String(), nullable=False, unique=True),
        sa.Column("owner_type", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "idx_scope_validators_scope_pattern",
        "scope_validators",
        ["scope_pattern"],
        unique=True,
    )
    op.create_index(
        "idx_scope_validators_owner_type",
        "scope_validators",
        ["owner_type"],
    )

    log.info("upgrade: created 6 SkillBOM attestation tables.")


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Drop the six SkillBOM attestation tables in reverse dependency order."""

    # Tables with no FKs first, then FK-bearing tables last.

    # 6. scope_validators (no FK)
    op.drop_index("idx_scope_validators_owner_type", table_name="scope_validators")
    op.drop_index("idx_scope_validators_scope_pattern", table_name="scope_validators")
    op.drop_table("scope_validators")

    # 5. bom_metadata (no FK)
    op.drop_table("bom_metadata")

    # 4. attestation_policies (no FK to artifacts)
    drop_updated_at_trigger("attestation_policies")
    op.drop_index(
        "idx_attestation_policies_name", table_name="attestation_policies"
    )
    op.drop_index(
        "idx_attestation_policies_tenant_id", table_name="attestation_policies"
    )
    op.drop_table("attestation_policies")

    # 3. bom_snapshots (no FK to artifacts)
    op.drop_index("idx_bom_snapshots_commit_sha", table_name="bom_snapshots")
    op.drop_index("idx_bom_snapshots_project_created", table_name="bom_snapshots")
    op.drop_table("bom_snapshots")

    # 2. artifact_history_events (FK → artifacts)
    op.drop_index(
        "idx_artifact_history_actor_id", table_name="artifact_history_events"
    )
    op.drop_index(
        "idx_artifact_history_type_ts", table_name="artifact_history_events"
    )
    op.drop_index(
        "idx_artifact_history_artifact_ts", table_name="artifact_history_events"
    )
    op.drop_table("artifact_history_events")

    # 1. attestation_records (FK → artifacts)
    drop_updated_at_trigger("attestation_records")
    op.drop_index(
        "idx_attestation_records_artifact_id", table_name="attestation_records"
    )
    op.drop_index(
        "idx_attestation_records_owner", table_name="attestation_records"
    )
    op.drop_table("attestation_records")

    log.info("downgrade: dropped 6 SkillBOM attestation tables.")
