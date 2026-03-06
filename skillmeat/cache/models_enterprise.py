"""SQLAlchemy ORM models for enterprise (PostgreSQL) schema.

This module defines the enterprise-tier ORM models that map to the PostgreSQL
schema introduced by the enterprise-db-storage feature. These models are
intentionally separate from the SQLite-backed models in models.py and share
a dedicated DeclarativeBase (EnterpriseBase) so that enterprise table metadata
never contaminates the local-mode SQLite schema.

Tables defined here:
    - EnterpriseArtifact           (enterprise_artifacts)             — ENT-1.2
    - EnterpriseArtifactVersion    (artifact_versions, PG)            — ENT-1.3
    - EnterpriseCollection         (enterprise_collections)           — ENT-1.4
    - EnterpriseCollectionArtifact (enterprise_collection_artifacts)  — ENT-1.5

Naming note (ENT-1.3):
    The local-mode SQLite schema (models.py) contains an ``ArtifactVersion``
    class backed by a same-named SQLite table used for change-origin tracking.
    To avoid a class-name collision at import time the enterprise counterpart is
    named ``EnterpriseArtifactVersion``. It maps to the PostgreSQL
    ``artifact_versions`` table, which lives in a different database engine and
    is unrelated to the SQLite table of the same DDL name.

Design invariants:
    - All enterprise tables are PostgreSQL-only (UUID PKs, JSONB, TIMESTAMPTZ).
    - Every query against an enterprise table MUST include a tenant_id predicate.
    - EnterpriseBase is the single shared base for all enterprise models.
      Do NOT use the local-mode Base from models.py for these models.

Exports:
    EnterpriseBase: Shared DeclarativeBase for all enterprise ORM models.
    EnterpriseArtifact: Primary artifact store for enterprise deployments.
    EnterpriseArtifactVersion: Immutable content snapshot per artifact version.
    EnterpriseCollection: Named artifact grouping per tenant.
    EnterpriseCollectionArtifact: Junction table linking collections to artifacts.

References:
    docs/project_plans/architecture/enterprise-db-schema-v1.md
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    # Forward references for relationships whose classes are defined later in
    # this same module.  Imported under TYPE_CHECKING only so that static type
    # checkers can resolve the Mapped[] annotations on relationship() fields.
    # At runtime the string-based relationship() targets resolve lazily at
    # SQLAlchemy mapper configuration time — no import is needed.
    from skillmeat.cache.models_enterprise import (  # noqa: F401
        EnterpriseArtifactVersion,
        EnterpriseCollectionArtifact,
    )


# =============================================================================
# Enterprise DeclarativeBase
# =============================================================================


class EnterpriseBase(DeclarativeBase):
    """Shared DeclarativeBase for all enterprise (PostgreSQL) ORM models.

    This base is separate from the local-mode ``Base`` in models.py so that
    enterprise table metadata is never mixed into the SQLite schema used by the
    CLI's local cache.

    ENT-1.2 (EnterpriseArtifact), ENT-1.3 (EnterpriseArtifactVersion), and
    ENT-1.4 (EnterpriseCollection) all subclass this base. ENT-1.5
    (EnterpriseCollectionArtifact) likewise imports it.
    """

    pass


# =============================================================================
# EnterpriseArtifact model  (ENT-1.2)
# =============================================================================


class EnterpriseArtifact(EnterpriseBase):
    """Primary artifact store for enterprise (cloud/PostgreSQL) deployments.

    Each row represents one artifact belonging to one tenant. This is the
    PostgreSQL-native counterpart to the SQLite-backed ``Artifact`` model in
    models.py. The two schemas are intentionally parallel and do not share
    tables or rows at runtime.

    Tenant isolation invariant:
        Every query against this table MUST include a ``WHERE tenant_id = ?``
        predicate. Omitting it is a security defect that leaks cross-tenant
        data. See the repository layer (ENT-2.x) for the TenantScopedRepository
        base class that enforces this rule structurally.

    Attributes:
        id:           UUID primary key, server-generated via gen_random_uuid().
        tenant_id:    Tenant scope; every query MUST filter by this column.
        name:         Human-readable artifact name (e.g. "canvas-design").
        artifact_type: Artifact type matching existing type vocabulary.
        description:  Optional human-readable description from frontmatter.
        source_url:   GitHub origin URL for upstream sync tracking.
        scope:        Storage scope — 'user' (global) or 'local' (project).
        tags:         JSONB array of tag strings; GIN-indexed for containment.
        custom_fields: Arbitrary JSONB key-value pairs for extensibility.
        is_active:    Soft-delete flag; False = logically deleted, row retained.
        created_at:   Timezone-aware creation timestamp (server default: now()).
        updated_at:   Timezone-aware last-modified timestamp (app-managed).
        created_by:   User ID or "system"; NULL until PRD-2 AuthContext lands.
        versions:     Immutable content snapshots (EnterpriseArtifactVersion, ENT-1.3).
        collection_memberships: Junction rows linking to collections (ENT-1.5).

    Constraints:
        uq_enterprise_artifacts_tenant_name_type:
            UNIQUE (tenant_id, name, type) — one artifact of a given type per
            name per tenant.
        ck_enterprise_artifacts_type:
            type must be one of the recognised artifact type values.
        ck_enterprise_artifacts_scope:
            scope must be 'user' or 'local'.
        ck_enterprise_artifacts_name_length:
            name must be 1–255 characters.

    Indexes:
        idx_enterprise_artifacts_tenant_id:       (tenant_id)
        idx_enterprise_artifacts_tenant_type:     (tenant_id, type)
        idx_enterprise_artifacts_tenant_created_at: (tenant_id, created_at)
        idx_enterprise_artifacts_tags_gin:        GIN (tags jsonb_path_ops)
        idx_enterprise_artifacts_source_url:      (source_url) WHERE NOT NULL
            — partial index; declared in the Alembic migration (ENT-1.7) with
            CONCURRENTLY to avoid table locks during deployment.

    Schema reference:
        docs/project_plans/architecture/enterprise-db-schema-v1.md §2.1
    """

    __tablename__ = "enterprise_artifacts"

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique artifact identifier; FK target for artifact_versions and enterprise_collection_artifacts",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
    )

    # -------------------------------------------------------------------------
    # Core metadata
    # -------------------------------------------------------------------------

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable artifact name, e.g. canvas-design, dev-execution",
    )
    # The DDL column is named 'type'; Python attribute is artifact_type to avoid
    # shadowing the built-in and for clarity at call sites.
    artifact_type: Mapped[str] = mapped_column(
        "type",
        String(50),
        nullable=False,
        comment="Artifact type; matches ck_enterprise_artifacts_type values",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional human-readable description from frontmatter",
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="GitHub origin URL (github:owner/repo/path); used for upstream sync",
    )
    scope: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="user",
        server_default=text("'user'"),
        comment="user = global collection; local = project-scoped",
    )

    # -------------------------------------------------------------------------
    # Flexible storage
    # -------------------------------------------------------------------------

    tags: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
        comment="Array of tag strings for filtering; GIN-indexed for @> containment queries",
    )
    custom_fields: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Arbitrary key-value pairs for schema-less extensibility",
    )

    # -------------------------------------------------------------------------
    # Soft-delete flag
    # -------------------------------------------------------------------------

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="Soft-delete: False = logically deleted but row retained for audit",
    )

    # -------------------------------------------------------------------------
    # Audit
    # -------------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        comment="Timezone-aware creation timestamp; server-generated",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=datetime.utcnow,
        comment="Timezone-aware last-modified timestamp; updated by app on every write",
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User ID or 'system'; NULL until PRD-2 AuthContext is available",
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------

    # ENT-1.3: EnterpriseArtifactVersion is defined below in this same module.
    # The string reference resolves lazily at mapper configuration time.
    versions: Mapped[List["EnterpriseArtifactVersion"]] = relationship(
        "EnterpriseArtifactVersion",
        back_populates="artifact",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="EnterpriseArtifactVersion.created_at.desc()",
    )

    # ENT-1.5 defines EnterpriseCollectionArtifact. Same lazy resolution.
    collection_memberships: Mapped[List["EnterpriseCollectionArtifact"]] = relationship(
        "EnterpriseCollectionArtifact",
        back_populates="artifact",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # -------------------------------------------------------------------------
    # Table-level constraints and indexes
    # -------------------------------------------------------------------------

    __table_args__ = (
        # Unique: one artifact of a given type per name per tenant
        UniqueConstraint(
            "tenant_id",
            "name",
            "type",
            name="uq_enterprise_artifacts_tenant_name_type",
        ),
        # Check: restrict to valid artifact type vocabulary
        CheckConstraint(
            "type IN ("
            "'skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', "
            "'workflow', 'composite', 'project_config', 'spec_file', "
            "'rule_file', 'context_file', 'progress_template'"
            ")",
            name="ck_enterprise_artifacts_type",
        ),
        # Check: scope must be 'user' or 'local'
        CheckConstraint(
            "scope IN ('user', 'local')",
            name="ck_enterprise_artifacts_scope",
        ),
        # Check: name must be between 1 and 255 characters
        CheckConstraint(
            "length(name) > 0 AND length(name) <= 255",
            name="ck_enterprise_artifacts_name_length",
        ),
        # B-tree: primary tenant filter (every query starts here)
        Index(
            "idx_enterprise_artifacts_tenant_id",
            "tenant_id",
        ),
        # B-tree: type-filtered listing within a tenant
        Index(
            "idx_enterprise_artifacts_tenant_type",
            "tenant_id",
            "type",
        ),
        # B-tree: default sort order (newest artifacts first per tenant)
        Index(
            "idx_enterprise_artifacts_tenant_created_at",
            "tenant_id",
            "created_at",
        ),
        # GIN: JSONB tag containment — supports tags @> '["frontend"]'::jsonb
        # The Alembic migration (ENT-1.7) must create this with CONCURRENTLY
        # and postgresql_ops={"tags": "jsonb_path_ops"} to avoid table locks.
        Index(
            "idx_enterprise_artifacts_tags_gin",
            "tags",
            postgresql_using="gin",
            postgresql_ops={"tags": "jsonb_path_ops"},
        ),
        # Partial B-tree: source_url lookup for upstream sync matching.
        # The WHERE clause (source_url IS NOT NULL) must be declared in the
        # Alembic migration using postgresql_where; SQLAlchemy Index() does
        # not render WHERE portably enough for inline declaration here.
        # Migration snippet (ENT-1.7):
        #   op.create_index(
        #       "idx_enterprise_artifacts_source_url", "enterprise_artifacts",
        #       ["source_url"],
        #       postgresql_where="source_url IS NOT NULL",
        #       postgresql_concurrently=True,
        #   )
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseArtifact."""
        return (
            f"<EnterpriseArtifact("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"artifact_type={self.artifact_type!r}, "
            f"name={self.name!r}, "
            f"is_active={self.is_active!r}"
            f")>"
        )


# =============================================================================
# EnterpriseArtifactVersion model  (ENT-1.3)
# =============================================================================


class EnterpriseArtifactVersion(EnterpriseBase):
    """Immutable content snapshot for a single version of an enterprise artifact.

    Each row captures one version of an artifact's Markdown payload.  Rows are
    write-once: they are never updated after insertion.  The ``content_hash``
    column (SHA256 hex digest of ``markdown_payload``) is globally unique across
    all tenants, enabling cross-tenant deduplication without exposing content:
    the repository checks for an existing row by hash before inserting, then
    re-uses the existing row's ID if the hash already exists.  See Section 5 of
    the schema reference for the full deduplication rationale.

    Naming rationale:
        The local-mode SQLite cache has an ``ArtifactVersion`` model in
        ``models.py`` that tracks change-origin history for the CLI.  That model
        is backed by a same-named SQLite table and is unrelated to this class.
        This class is named ``EnterpriseArtifactVersion`` to avoid a Python
        class-name collision when both modules are imported into the same
        process.  At the DDL level the table is named ``artifact_versions`` and
        lives in the PostgreSQL database, not the SQLite database.

    Tenant isolation invariant:
        ``tenant_id`` is denormalized from the parent ``EnterpriseArtifact`` row
        for query performance.  The application layer (ENT-2.x repository) is
        responsible for ensuring that ``tenant_id`` on this row matches
        ``tenant_id`` on the parent artifact at write time.  There is no DB
        foreign key from ``tenant_id`` to a ``tenants`` table in Phase 1.

    Immutability invariant:
        No UPDATE is ever issued against this table.  To supersede a version the
        caller inserts a new row.  The ``content_hash`` uniqueness constraint is
        the deduplication guard: identical content always maps to the same row.

    Attributes:
        id:               UUID PK, server-generated via gen_random_uuid().
        tenant_id:        Denormalized tenant scope for efficient querying.
        artifact_id:      FK to enterprise_artifacts.id; CASCADE on delete.
        version_tag:      Human-readable label, e.g. "v1.2.0", "latest", SHA prefix.
        content_hash:     SHA256 hex digest (64 chars) of markdown_payload; globally unique.
        markdown_payload: Full Markdown content of the artifact at this version.
        commit_sha:       GitHub commit SHA (40 chars) for git-provenance tracing; nullable.
        changelog:        Optional free-text description of changes in this version.
        created_by:       User ID or "system"; NULL until PRD-2 AuthContext lands.
        created_at:       Immutable creation timestamp; server-generated.
        artifact:         Many-to-one back-reference to EnterpriseArtifact.

    Constraints:
        fk_artifact_versions_artifact_id:
            FK (artifact_id) -> enterprise_artifacts(id) ON DELETE CASCADE
        uq_artifact_versions_artifact_version:
            UNIQUE (artifact_id, version_tag) — one tag per artifact
        uq_artifact_versions_content_hash:
            UNIQUE (content_hash) — global deduplication across all tenants
        ck_artifact_versions_content_hash_length:
            length(content_hash) = 64 — SHA256 hex is exactly 64 chars
        ck_artifact_versions_commit_sha_length:
            commit_sha IS NULL OR length(commit_sha) = 40 — full SHA1 is 40 chars

    Indexes:
        idx_artifact_versions_tenant_id:
            (tenant_id) — mandatory per-tenant filter on version queries
        idx_artifact_versions_artifact_id:
            (artifact_id) — covers the FK and single-artifact version listing
        idx_artifact_versions_artifact_created:
            (artifact_id, created_at DESC) — paginated version history per artifact
        idx_artifact_versions_tenant_created:
            (tenant_id, created_at DESC) — recent-versions queries across a tenant
        idx_artifact_versions_commit_sha:
            (commit_sha) WHERE NOT NULL — upstream sync: commit already ingested?

    Schema reference:
        docs/project_plans/architecture/enterprise-db-schema-v1.md §2.2
    """

    __tablename__ = "artifact_versions"

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Version record primary key; globally unique",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment=(
            "Denormalized tenant scope for query performance; "
            "must equal the parent artifact's tenant_id — validated at write time"
        ),
    )

    # -------------------------------------------------------------------------
    # Foreign key
    # -------------------------------------------------------------------------

    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_artifacts.id",
            ondelete="CASCADE",
            name="fk_artifact_versions_artifact_id",
        ),
        nullable=False,
        comment="Parent artifact; cascade-deletes all version rows when artifact is removed",
    )

    # -------------------------------------------------------------------------
    # Version labeling
    # -------------------------------------------------------------------------

    version_tag: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment=(
            "Human-readable version label, e.g. 'v1.2.0', 'latest', or a short SHA prefix. "
            "Unique per artifact (enforced by uq_artifact_versions_artifact_version)."
        ),
    )

    # -------------------------------------------------------------------------
    # Content
    # -------------------------------------------------------------------------

    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment=(
            "SHA256 hex digest of markdown_payload (64 chars). "
            "Globally unique — enables cross-tenant deduplication without exposing content. "
            "Repository MUST check for an existing row by hash before inserting."
        ),
    )
    markdown_payload: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full Markdown content of the artifact at this version; no size cap in Phase 1",
    )

    # -------------------------------------------------------------------------
    # Git provenance
    # -------------------------------------------------------------------------

    commit_sha: Mapped[Optional[str]] = mapped_column(
        String(40),
        nullable=True,
        comment=(
            "GitHub commit SHA (40 chars) for the source of this version. "
            "NULL for versions not sourced from GitHub. "
            "Checked via idx_artifact_versions_commit_sha during upstream sync."
        ),
    )

    # -------------------------------------------------------------------------
    # Audit
    # -------------------------------------------------------------------------

    changelog: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional free-text description of changes introduced in this version",
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User ID or 'system'; NULL until PRD-2 AuthContext is available",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        comment=(
            "Immutable creation timestamp; server-generated. "
            "This column is NEVER updated — versions are write-once."
        ),
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------

    artifact: Mapped["EnterpriseArtifact"] = relationship(
        "EnterpriseArtifact",
        back_populates="versions",
        lazy="joined",
    )

    # -------------------------------------------------------------------------
    # Table-level constraints and indexes
    # -------------------------------------------------------------------------

    __table_args__ = (
        # Unique: one version_tag per artifact
        UniqueConstraint(
            "artifact_id",
            "version_tag",
            name="uq_artifact_versions_artifact_version",
        ),
        # Unique: global content deduplication by SHA256 hash
        UniqueConstraint(
            "content_hash",
            name="uq_artifact_versions_content_hash",
        ),
        # Check: SHA256 hex digest is exactly 64 characters
        CheckConstraint(
            "length(content_hash) = 64",
            name="ck_artifact_versions_content_hash_length",
        ),
        # Check: GitHub SHA1 is exactly 40 characters when present
        CheckConstraint(
            "commit_sha IS NULL OR length(commit_sha) = 40",
            name="ck_artifact_versions_commit_sha_length",
        ),
        # B-tree: mandatory per-tenant filter on cross-artifact version queries
        Index(
            "idx_artifact_versions_tenant_id",
            "tenant_id",
        ),
        # B-tree: covers the FK and single-artifact "list all versions" query
        Index(
            "idx_artifact_versions_artifact_id",
            "artifact_id",
        ),
        # B-tree composite: paginated version history for a single artifact,
        # newest first — satisfies the EnterpriseArtifact.versions order_by
        Index(
            "idx_artifact_versions_artifact_created",
            "artifact_id",
            "created_at",
        ),
        # B-tree composite: recent-versions queries across an entire tenant
        # (e.g. "show me the last 20 changes across all my artifacts")
        Index(
            "idx_artifact_versions_tenant_created",
            "tenant_id",
            "created_at",
        ),
        # Partial B-tree: upstream sync check "have we already ingested this
        # commit?".  The WHERE clause keeps the index small by excluding the
        # majority of rows where commit_sha IS NULL.
        # The postgresql_where must be declared in the Alembic migration with
        # CONCURRENTLY to avoid table locks; it is noted here for reference.
        # Migration snippet (ENT-1.7):
        #   op.create_index(
        #       "idx_artifact_versions_commit_sha", "artifact_versions",
        #       ["commit_sha"],
        #       postgresql_where="commit_sha IS NOT NULL",
        #       postgresql_concurrently=True,
        #   )
    )

    # -------------------------------------------------------------------------
    # Dunder methods
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseArtifactVersion."""
        return (
            f"<EnterpriseArtifactVersion("
            f"id={self.id!r}, "
            f"artifact_id={self.artifact_id!r}, "
            f"version_tag={self.version_tag!r}, "
            f"content_hash={self.content_hash!r}"
            f")>"
        )


# =============================================================================
# EnterpriseCollection model  (ENT-1.4)
# =============================================================================


class EnterpriseCollection(EnterpriseBase):
    """Named grouping of enterprise artifacts scoped to a single tenant.

    Mirrors the intent of the existing local-mode ``Collection`` table but is
    PostgreSQL-native, tenant-scoped, and uses UUID primary keys.

    One collection per tenant may be designated as default (``is_default=True``).
    The uniqueness of the default flag is enforced at the application/repository
    layer (not by a database constraint) to keep cross-PostgreSQL-version
    compatibility simple. The repository ``set_default`` method clears
    ``is_default`` on all sibling collections in the same transaction before
    setting the new default.

    Attributes:
        id:           UUID primary key, generated server-side.
        tenant_id:    Tenant scope.  Every query MUST filter by this column.
        name:         Human-readable collection name; unique per tenant.
        description:  Optional free-text description.
        is_default:   When True the CLI uses this collection implicitly.
        created_by:   User ID or ``"system"``; NULL until PRD-2 AuthContext.
        created_at:   Timezone-aware creation timestamp.
        updated_at:   Timezone-aware last-modified timestamp.
        memberships:  Ordered list of EnterpriseCollectionArtifact join rows.

    Constraints:
        pk_enterprise_collections:          PRIMARY KEY (id)
        uq_enterprise_collections_tenant_name:
                                            UNIQUE (tenant_id, name)
        ck_enterprise_collections_name_length:
                                            length(name) BETWEEN 1 AND 255

    Indexes:
        idx_enterprise_collections_tenant_id:
                                            (tenant_id)
        idx_enterprise_collections_tenant_name:
                                            (tenant_id, name)
        idx_enterprise_collections_tenant_default:
                                            (tenant_id, is_default)
                                            WHERE is_default = TRUE  [partial]

    Schema reference:
        docs/project_plans/architecture/enterprise-db-schema-v1.md §2.3
    """

    __tablename__ = "enterprise_collections"

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique collection identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
    )

    # -------------------------------------------------------------------------
    # Core metadata
    # -------------------------------------------------------------------------

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable collection name; unique within a tenant",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional free-text description",
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment=(
            "When TRUE, CLI uses this collection implicitly for deploy. "
            "At most one TRUE per tenant; enforced at application layer."
        ),
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User ID or 'system'; NULL until PRD-2 AuthContext is available",
    )

    # -------------------------------------------------------------------------
    # Audit
    # -------------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        comment="Timezone-aware creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=datetime.utcnow,
        comment="Timezone-aware last-modified timestamp; updated on every write",
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------

    # ENT-1.5 defines EnterpriseCollectionArtifact.  The string reference
    # resolves at mapper configuration time; no circular-import risk.
    memberships: Mapped[List["EnterpriseCollectionArtifact"]] = relationship(
        "EnterpriseCollectionArtifact",
        back_populates="collection",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="EnterpriseCollectionArtifact.order_index",
    )

    # -------------------------------------------------------------------------
    # Table-level constraints and indexes
    # -------------------------------------------------------------------------

    __table_args__ = (
        # Uniqueness: one name per tenant
        UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_enterprise_collections_tenant_name",
        ),
        # Guard against empty or overlong names (mirrors DDL CHECK)
        CheckConstraint(
            "length(name) > 0 AND length(name) <= 255",
            name="ck_enterprise_collections_name_length",
        ),
        # B-tree on tenant for the mandatory per-query tenant filter
        # (the simple index=True on tenant_id above covers this, but we add an
        # explicit named index here to match the migration-generated name)
        Index(
            "idx_enterprise_collections_tenant_id",
            "tenant_id",
        ),
        # B-tree on (tenant_id, name) for alphabetical listing within a tenant
        Index(
            "idx_enterprise_collections_tenant_name",
            "tenant_id",
            "name",
        ),
        # Partial B-tree: accelerates the single-row "which collection is
        # default?" query without indexing the overwhelming majority of rows
        # where is_default = FALSE.  postgresql_where is a no-op on non-PG
        # dialects (SQLite in tests) and will be ignored gracefully.
        Index(
            "idx_enterprise_collections_tenant_default",
            "tenant_id",
            "is_default",
            postgresql_where=text("is_default = TRUE"),
        ),
    )

    # -------------------------------------------------------------------------
    # Dunder methods
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<EnterpriseCollection("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"name={self.name!r}, "
            f"is_default={self.is_default!r}"
            f")>"
        )


# =============================================================================
# EnterpriseCollectionArtifact model  (ENT-1.5)
# =============================================================================


class EnterpriseCollectionArtifact(EnterpriseBase):
    """Junction table linking enterprise collections to enterprise artifacts.

    Each row represents the membership of one artifact in one collection,
    carrying an ``order_index`` so that artifacts can be presented in a
    deterministic, user-controlled order within a collection.

    Cascade behaviour:
        Deleting an ``EnterpriseCollection`` cascades to all of its membership
        rows (ON DELETE CASCADE on ``collection_id``).  Likewise, deleting an
        ``EnterpriseArtifact`` cascades to all membership rows that reference it
        (ON DELETE CASCADE on ``artifact_id``).  No orphaned join rows can exist
        after either parent is removed.

    Unique membership invariant:
        ``uq_collection_artifacts_collection_artifact`` ensures that the same
        artifact cannot be added to the same collection twice.

    Ordering:
        ``order_index`` is a 0-based integer managed by the application.  The
        ``EnterpriseCollection.memberships`` relationship is ordered by this
        column ascending so callers receive a stable sequence without an
        explicit ORDER BY.

    Attributes:
        id:            UUID primary key, server-generated via gen_random_uuid().
        collection_id: FK → enterprise_collections.id, NOT NULL, CASCADE.
        artifact_id:   FK → enterprise_artifacts.id, NOT NULL, CASCADE.
        order_index:   Ordering position within the collection; default 0.
        added_at:      Timezone-aware timestamp when artifact was added.
        added_by:      User ID or "system"; NULL until PRD-2 AuthContext.
        collection:    Many-to-one back-reference to EnterpriseCollection.
        artifact:      Many-to-one back-reference to EnterpriseArtifact.

    Constraints:
        uq_collection_artifacts_collection_artifact:
            UNIQUE (collection_id, artifact_id)

    Indexes:
        idx_collection_artifacts_collection_id:   (collection_id)
        idx_collection_artifacts_artifact_id:     (artifact_id)
        idx_collection_artifacts_collection_order: (collection_id, order_index)

    Schema reference:
        docs/project_plans/architecture/enterprise-db-schema-v1.md §2.4
    """

    __tablename__ = "enterprise_collection_artifacts"

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique join-row identifier",
    )

    # -------------------------------------------------------------------------
    # Foreign keys
    # -------------------------------------------------------------------------

    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enterprise_collections.id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent collection; cascade-deletes this row when collection is removed",
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("enterprise_artifacts.id", ondelete="CASCADE"),
        nullable=False,
        comment="Member artifact; cascade-deletes this row when artifact is removed",
    )

    # -------------------------------------------------------------------------
    # Ordering and audit
    # -------------------------------------------------------------------------

    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="0-based position of the artifact within the collection; lower = earlier",
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        comment="Timezone-aware timestamp when the artifact was added to the collection",
    )
    added_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User ID or 'system'; NULL until PRD-2 AuthContext is available",
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------

    collection: Mapped["EnterpriseCollection"] = relationship(
        "EnterpriseCollection",
        back_populates="memberships",
        lazy="joined",
    )
    artifact: Mapped["EnterpriseArtifact"] = relationship(
        "EnterpriseArtifact",
        back_populates="collection_memberships",
        lazy="joined",
    )

    # -------------------------------------------------------------------------
    # Table-level constraints and indexes
    # -------------------------------------------------------------------------

    __table_args__ = (
        # Uniqueness: one artifact per collection (no duplicates)
        UniqueConstraint(
            "collection_id",
            "artifact_id",
            name="uq_collection_artifacts_collection_artifact",
        ),
        # B-tree: primary filter when loading a collection's members
        Index(
            "idx_collection_artifacts_collection_id",
            "collection_id",
        ),
        # B-tree: reverse lookup — which collections contain a given artifact?
        Index(
            "idx_collection_artifacts_artifact_id",
            "artifact_id",
        ),
        # B-tree composite: ordered membership scan within a single collection
        # (used by EnterpriseCollection.memberships order_by clause)
        Index(
            "idx_collection_artifacts_collection_order",
            "collection_id",
            "order_index",
        ),
    )

    # -------------------------------------------------------------------------
    # Dunder methods
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseCollectionArtifact."""
        return (
            f"<EnterpriseCollectionArtifact("
            f"id={self.id!r}, "
            f"collection_id={self.collection_id!r}, "
            f"artifact_id={self.artifact_id!r}, "
            f"order_index={self.order_index!r}"
            f")>"
        )
