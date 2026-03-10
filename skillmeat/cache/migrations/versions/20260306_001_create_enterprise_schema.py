"""create enterprise schema: enterprise_artifacts, artifact_versions, enterprise_collections, enterprise_collection_artifacts

Revision ID: 20260306_001_create_enterprise_schema
Revises: 001_consolidated_schema
Create Date: 2026-03-06 00:01:00.000000+00:00

Background
----------
This migration introduces the four PostgreSQL-native enterprise tables required
by the enterprise-db-storage feature (ENT phase 1).  The existing SQLite cache
is left completely untouched — the migration is a no-op on any non-PostgreSQL
dialect.

Tables created (dependency order)
----------------------------------
1. enterprise_artifacts
       Primary artifact store for enterprise (cloud/PostgreSQL) deployments.
       UUID PK, JSONB tags/custom_fields, soft-delete via is_active.

2. enterprise_collections
       Named grouping of artifacts scoped to a single tenant.
       UUID PK, one optional default per tenant (enforced at app layer).

3. artifact_versions
       Immutable content snapshot per artifact version.
       FK -> enterprise_artifacts.id ON DELETE CASCADE.
       SHA256 content_hash is globally unique for cross-tenant deduplication.

4. enterprise_collection_artifacts
       Junction table linking collections to artifacts with ordering.
       FK -> enterprise_collections.id ON DELETE CASCADE.
       FK -> enterprise_artifacts.id ON DELETE CASCADE.

Indexes
-------
Most indexes use op.create_index().  The GIN index on enterprise_artifacts.tags
is created with raw SQL via op.execute() so that CONCURRENTLY can be used,
avoiding a full table lock during initial deployment.

Partial indexes (source_url IS NOT NULL and commit_sha IS NOT NULL) likewise
use op.execute() with CONCURRENTLY.

The is_default partial index on enterprise_collections uses op.create_index()
with postgresql_where because CONCURRENTLY is incompatible with CREATE TABLE
followed immediately by CREATE INDEX CONCURRENTLY in the same transaction.

Downgrade order
---------------
4. enterprise_collection_artifacts
3. artifact_versions
2. enterprise_collections
1. enterprise_artifacts

Schema reference
----------------
docs/project_plans/architecture/enterprise-db-schema-v1.md
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "20260306_001_create_enterprise_schema"
down_revision: Union[str, None] = "001_consolidated_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Dialect guard
# ---------------------------------------------------------------------------


def _is_postgresql() -> bool:
    """Return True when the migration is running against a PostgreSQL database."""
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Create the four enterprise tables (PostgreSQL only)."""
    if not _is_postgresql():
        return  # No-op for SQLite and any other non-PostgreSQL dialect

    # ------------------------------------------------------------------
    # 1. enterprise_artifacts
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_artifacts",
        # Identity
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment=(
                "Globally unique artifact identifier; FK target for "
                "artifact_versions and enterprise_collection_artifacts"
            ),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        # Core metadata
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Human-readable artifact name, e.g. canvas-design, dev-execution",
        ),
        sa.Column(
            "type",
            sa.String(50),
            nullable=False,
            comment="Artifact type; matches ck_enterprise_artifacts_type values",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Optional human-readable description from frontmatter",
        ),
        sa.Column(
            "source_url",
            sa.String(512),
            nullable=True,
            comment="GitHub origin URL (github:owner/repo/path); used for upstream sync",
        ),
        sa.Column(
            "scope",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'user'"),
            comment="user = global collection; local = project-scoped",
        ),
        # Flexible storage
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment=(
                "Array of tag strings for filtering; "
                "GIN-indexed for @> containment queries"
            ),
        ),
        sa.Column(
            "custom_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Arbitrary key-value pairs for schema-less extensibility",
        ),
        # Soft-delete
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
            comment="Soft-delete: False = logically deleted but row retained for audit",
        ),
        # Audit
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Timezone-aware creation timestamp; server-generated",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment=(
                "Timezone-aware last-modified timestamp; "
                "updated by app on every write"
            ),
        ),
        sa.Column(
            "created_by",
            sa.String(255),
            nullable=True,
            comment="User ID or 'system'; NULL until PRD-2 AuthContext is available",
        ),
        # Named constraints
        sa.UniqueConstraint(
            "tenant_id",
            "name",
            "type",
            name="uq_enterprise_artifacts_tenant_name_type",
        ),
        sa.CheckConstraint(
            "type IN ("
            "'skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', "
            "'workflow', 'composite', 'project_config', 'spec_file', "
            "'rule_file', 'context_file', 'progress_template'"
            ")",
            name="ck_enterprise_artifacts_type",
        ),
        sa.CheckConstraint(
            "scope IN ('user', 'local')",
            name="ck_enterprise_artifacts_scope",
        ),
        sa.CheckConstraint(
            "length(name) > 0 AND length(name) <= 255",
            name="ck_enterprise_artifacts_name_length",
        ),
    )

    # B-tree indexes on enterprise_artifacts
    op.create_index(
        "idx_enterprise_artifacts_tenant_id",
        "enterprise_artifacts",
        ["tenant_id"],
    )
    op.create_index(
        "idx_enterprise_artifacts_tenant_type",
        "enterprise_artifacts",
        ["tenant_id", "type"],
    )
    op.create_index(
        "idx_enterprise_artifacts_tenant_created_at",
        "enterprise_artifacts",
        ["tenant_id", "created_at"],
    )

    # GIN index on tags — created with CONCURRENTLY via raw SQL to avoid
    # a full table lock during deployment.  CONCURRENTLY requires that the
    # statement runs outside an explicit transaction block; Alembic's
    # op.execute() satisfies this when autocommit is in effect for the
    # connection.  See ENT-1.7 migration guidance in the schema doc.
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "idx_enterprise_artifacts_tags_gin "
        "ON enterprise_artifacts USING GIN (tags jsonb_path_ops)"
    )

    # Partial B-tree: source_url lookup for upstream sync (NOT NULL rows only)
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "idx_enterprise_artifacts_source_url "
        "ON enterprise_artifacts (source_url) "
        "WHERE source_url IS NOT NULL"
    )

    # ------------------------------------------------------------------
    # 2. enterprise_collections
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_collections",
        # Identity
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique collection identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        # Core metadata
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Human-readable collection name; unique within a tenant",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Optional free-text description",
        ),
        sa.Column(
            "is_default",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
            comment=(
                "When TRUE, CLI uses this collection implicitly for deploy. "
                "At most one TRUE per tenant; enforced at application layer."
            ),
        ),
        sa.Column(
            "created_by",
            sa.String(255),
            nullable=True,
            comment="User ID or 'system'; NULL until PRD-2 AuthContext is available",
        ),
        # Audit
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Timezone-aware creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Timezone-aware last-modified timestamp; updated on every write",
        ),
        # Named constraints
        sa.UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_enterprise_collections_tenant_name",
        ),
        sa.CheckConstraint(
            "length(name) > 0 AND length(name) <= 255",
            name="ck_enterprise_collections_name_length",
        ),
    )

    # B-tree indexes on enterprise_collections
    op.create_index(
        "idx_enterprise_collections_tenant_id",
        "enterprise_collections",
        ["tenant_id"],
    )
    op.create_index(
        "idx_enterprise_collections_tenant_name",
        "enterprise_collections",
        ["tenant_id", "name"],
    )

    # Partial B-tree: accelerates the single-row "which collection is default?"
    # query without indexing the overwhelming majority of FALSE rows.
    op.create_index(
        "idx_enterprise_collections_tenant_default",
        "enterprise_collections",
        ["tenant_id", "is_default"],
        postgresql_where=sa.text("is_default = TRUE"),
    )

    # ------------------------------------------------------------------
    # 3. artifact_versions
    # ------------------------------------------------------------------
    op.create_table(
        "artifact_versions",
        # Identity
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Version record primary key; globally unique",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment=(
                "Denormalized tenant scope for query performance; "
                "must equal the parent artifact's tenant_id — validated at write time"
            ),
        ),
        # Foreign key
        sa.Column(
            "artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_artifacts.id",
                ondelete="CASCADE",
                name="fk_artifact_versions_artifact_id",
            ),
            nullable=False,
            comment=(
                "Parent artifact; cascade-deletes all version rows "
                "when artifact is removed"
            ),
        ),
        # Version labeling
        sa.Column(
            "version_tag",
            sa.String(100),
            nullable=False,
            comment=(
                "Human-readable version label, e.g. 'v1.2.0', 'latest', "
                "or a short SHA prefix. Unique per artifact."
            ),
        ),
        # Content
        sa.Column(
            "content_hash",
            sa.String(64),
            nullable=False,
            comment=(
                "SHA256 hex digest of markdown_payload (64 chars). "
                "Globally unique — enables cross-tenant deduplication."
            ),
        ),
        sa.Column(
            "markdown_payload",
            sa.Text,
            nullable=False,
            comment=(
                "Full Markdown content of the artifact at this version; "
                "no size cap in Phase 1"
            ),
        ),
        # Git provenance
        sa.Column(
            "commit_sha",
            sa.String(40),
            nullable=True,
            comment=(
                "GitHub commit SHA (40 chars) for the source of this version. "
                "NULL for versions not sourced from GitHub."
            ),
        ),
        # Audit
        sa.Column(
            "changelog",
            sa.Text,
            nullable=True,
            comment="Optional free-text description of changes introduced in this version",
        ),
        sa.Column(
            "created_by",
            sa.String(255),
            nullable=True,
            comment="User ID or 'system'; NULL until PRD-2 AuthContext is available",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment=(
                "Immutable creation timestamp; server-generated. "
                "This column is NEVER updated — versions are write-once."
            ),
        ),
        # Named constraints
        sa.UniqueConstraint(
            "artifact_id",
            "version_tag",
            name="uq_artifact_versions_artifact_version",
        ),
        sa.UniqueConstraint(
            "content_hash",
            name="uq_artifact_versions_content_hash",
        ),
        sa.CheckConstraint(
            "length(content_hash) = 64",
            name="ck_artifact_versions_content_hash_length",
        ),
        sa.CheckConstraint(
            "commit_sha IS NULL OR length(commit_sha) = 40",
            name="ck_artifact_versions_commit_sha_length",
        ),
    )

    # B-tree indexes on artifact_versions
    op.create_index(
        "idx_artifact_versions_tenant_id",
        "artifact_versions",
        ["tenant_id"],
    )
    op.create_index(
        "idx_artifact_versions_artifact_id",
        "artifact_versions",
        ["artifact_id"],
    )
    op.create_index(
        "idx_artifact_versions_artifact_created",
        "artifact_versions",
        ["artifact_id", "created_at"],
    )
    op.create_index(
        "idx_artifact_versions_tenant_created",
        "artifact_versions",
        ["tenant_id", "created_at"],
    )

    # Partial B-tree: upstream sync check "have we already ingested this commit?"
    # CONCURRENTLY keeps the table available during index build.
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "idx_artifact_versions_commit_sha "
        "ON artifact_versions (commit_sha) "
        "WHERE commit_sha IS NOT NULL"
    )

    # ------------------------------------------------------------------
    # 4. enterprise_collection_artifacts
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_collection_artifacts",
        # Identity
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique join-row identifier",
        ),
        # Foreign keys
        sa.Column(
            "collection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_collections.id",
                ondelete="CASCADE",
                name="fk_collection_artifacts_collection_id",
            ),
            nullable=False,
            comment=(
                "Parent collection; cascade-deletes this row "
                "when collection is removed"
            ),
        ),
        sa.Column(
            "artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_artifacts.id",
                ondelete="CASCADE",
                name="fk_collection_artifacts_artifact_id",
            ),
            nullable=False,
            comment=(
                "Member artifact; cascade-deletes this row "
                "when artifact is removed"
            ),
        ),
        # Ordering and audit
        sa.Column(
            "order_index",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment=(
                "0-based position of the artifact within the collection; "
                "lower = earlier"
            ),
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment=(
                "Timezone-aware timestamp when the artifact "
                "was added to the collection"
            ),
        ),
        sa.Column(
            "added_by",
            sa.String(255),
            nullable=True,
            comment="User ID or 'system'; NULL until PRD-2 AuthContext is available",
        ),
        # Named constraints
        sa.UniqueConstraint(
            "collection_id",
            "artifact_id",
            name="uq_collection_artifacts_collection_artifact",
        ),
    )

    # B-tree indexes on enterprise_collection_artifacts
    op.create_index(
        "idx_collection_artifacts_collection_id",
        "enterprise_collection_artifacts",
        ["collection_id"],
    )
    op.create_index(
        "idx_collection_artifacts_artifact_id",
        "enterprise_collection_artifacts",
        ["artifact_id"],
    )
    op.create_index(
        "idx_collection_artifacts_collection_order",
        "enterprise_collection_artifacts",
        ["collection_id", "order_index"],
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Drop the four enterprise tables in reverse dependency order (PostgreSQL only)."""
    if not _is_postgresql():
        return  # No-op for SQLite and any other non-PostgreSQL dialect

    # Drop in reverse dependency order so FK constraints are satisfied.

    # 4. enterprise_collection_artifacts (references both collections + artifacts)
    op.drop_index(
        "idx_collection_artifacts_collection_order",
        table_name="enterprise_collection_artifacts",
    )
    op.drop_index(
        "idx_collection_artifacts_artifact_id",
        table_name="enterprise_collection_artifacts",
    )
    op.drop_index(
        "idx_collection_artifacts_collection_id",
        table_name="enterprise_collection_artifacts",
    )
    op.drop_table("enterprise_collection_artifacts")

    # 3. artifact_versions (references enterprise_artifacts)
    op.execute("DROP INDEX IF EXISTS idx_artifact_versions_commit_sha")
    op.drop_index(
        "idx_artifact_versions_tenant_created",
        table_name="artifact_versions",
    )
    op.drop_index(
        "idx_artifact_versions_artifact_created",
        table_name="artifact_versions",
    )
    op.drop_index(
        "idx_artifact_versions_artifact_id",
        table_name="artifact_versions",
    )
    op.drop_index(
        "idx_artifact_versions_tenant_id",
        table_name="artifact_versions",
    )
    op.drop_table("artifact_versions")

    # 2. enterprise_collections (no FKs to enterprise_artifacts)
    op.drop_index(
        "idx_enterprise_collections_tenant_default",
        table_name="enterprise_collections",
    )
    op.drop_index(
        "idx_enterprise_collections_tenant_name",
        table_name="enterprise_collections",
    )
    op.drop_index(
        "idx_enterprise_collections_tenant_id",
        table_name="enterprise_collections",
    )
    op.drop_table("enterprise_collections")

    # 1. enterprise_artifacts (no FK dependencies remain after steps 3 + 4)
    op.execute("DROP INDEX IF EXISTS idx_enterprise_artifacts_source_url")
    op.execute("DROP INDEX IF EXISTS idx_enterprise_artifacts_tags_gin")
    op.drop_index(
        "idx_enterprise_artifacts_tenant_created_at",
        table_name="enterprise_artifacts",
    )
    op.drop_index(
        "idx_enterprise_artifacts_tenant_type",
        table_name="enterprise_artifacts",
    )
    op.drop_index(
        "idx_enterprise_artifacts_tenant_id",
        table_name="enterprise_artifacts",
    )
    op.drop_table("enterprise_artifacts")
