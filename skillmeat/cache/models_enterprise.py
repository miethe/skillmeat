"""SQLAlchemy ORM models for enterprise (PostgreSQL) schema.

This module defines the enterprise-tier ORM models that map to the PostgreSQL
schema introduced by the enterprise-db-storage feature. These models are
intentionally separate from the SQLite-backed models in models.py and share
a dedicated DeclarativeBase (EnterpriseBase) so that enterprise table metadata
never contaminates the local-mode SQLite schema.

Tables defined here:
    - EnterpriseArtifact    (enterprise_artifacts)    — ENT-1.2
    - EnterpriseCollection  (enterprise_collections)  — ENT-1.4

Tables NOT yet defined (added in subsequent ENT tasks):
    - ArtifactVersion              (artifact_versions, PG)           — ENT-1.3
    - EnterpriseCollectionArtifact (enterprise_collection_artifacts)  — ENT-1.5

Design invariants:
    - All enterprise tables are PostgreSQL-only (UUID PKs, JSONB, TIMESTAMPTZ).
    - Every query against an enterprise table MUST include a tenant_id predicate.
    - EnterpriseBase is the single shared base for all enterprise models.
      Do NOT use the local-mode Base from models.py for these models.

Exports:
    EnterpriseBase: Shared DeclarativeBase for all enterprise ORM models.
    EnterpriseArtifact: Primary artifact store for enterprise deployments.
    EnterpriseCollection: Named artifact grouping per tenant.

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
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    # Forward references for relationships defined in later ENT tasks.
    # Imported under TYPE_CHECKING only to avoid circular imports at runtime.
    # String-based relationship() targets resolve lazily at mapper config time.
    from skillmeat.cache.models_enterprise import (  # noqa: F401
        ArtifactVersion,
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

    Both ENT-1.2 (EnterpriseArtifact / ArtifactVersion) and ENT-1.4
    (EnterpriseCollection) import and subclass this base. ENT-1.5
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
        versions:     Immutable content snapshots (ArtifactVersion, ENT-1.3).
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

    # ENT-1.3 defines ArtifactVersion. String reference resolves lazily at
    # mapper configuration time — no import needed here.
    versions: Mapped[List["ArtifactVersion"]] = relationship(
        "ArtifactVersion",
        back_populates="artifact",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="ArtifactVersion.created_at.desc()",
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
