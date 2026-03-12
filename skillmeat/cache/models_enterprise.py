"""SQLAlchemy ORM models for enterprise (PostgreSQL) schema.

This module defines the enterprise-tier ORM models that map to the PostgreSQL
schema introduced by the enterprise-db-storage feature. These models are
intentionally separate from the SQLite-backed models in models.py and share
a dedicated DeclarativeBase (EnterpriseBase) so that enterprise table metadata
never contaminates the local-mode SQLite schema.

Tables defined here:
    - EnterpriseArtifact                    (enterprise_artifacts)                        — ENT-1.2
    - EnterpriseArtifactVersion             (artifact_versions, PG)                       — ENT-1.3
    - EnterpriseCollection                  (enterprise_collections)                      — ENT-1.4
    - EnterpriseCollectionArtifact          (enterprise_collection_artifacts)             — ENT-1.5
    - EnterpriseUser                        (enterprise_users)                            — DB-001
    - EnterpriseTeam                        (enterprise_teams)                            — DB-001
    - EnterpriseTeamMember                  (enterprise_team_members)                     — DB-001
    - EnterpriseTag                         (enterprise_tags)                             — ENT2-2.1
    - EnterpriseArtifactTag                 (enterprise_artifact_tags)                    — ENT2-2.1
    - EnterpriseGroup                       (enterprise_groups)                           — ENT2-2.1
    - EnterpriseGroupArtifact               (enterprise_group_artifacts)                  — ENT2-2.1
    - EnterpriseSettings                    (enterprise_settings)                         — ENT2-2.1
    - EnterpriseEntityTypeConfig            (enterprise_entity_type_configs)              — ENT2-2.1
    - EnterpriseEntityCategory              (enterprise_entity_categories)                — ENT2-2.1
    - EnterpriseContextEntity               (enterprise_context_entities)                 — ENT2-2.2
    - EnterpriseEntityCategoryAssociation   (enterprise_entity_category_associations)     — ENT2-2.2
    - EnterpriseProject                     (enterprise_projects)                         — ENT2-2.3
    - EnterpriseProjectArtifact             (enterprise_project_artifacts)                — ENT2-2.3
    - EnterpriseDeployment                  (enterprise_deployments)                      — ENT2-2.3
    - EnterpriseDeploymentSet               (enterprise_deployment_sets)                  — ENT2-2.3
    - EnterpriseDeploymentSetMember         (enterprise_deployment_set_members)           — ENT2-2.3
    - EnterpriseDeploymentSetTag            (enterprise_deployment_set_tags)              — ENT2-2.3
    - EnterpriseDeploymentProfile           (enterprise_deployment_profiles)              — ENT2-2.3
    - EnterpriseMarketplaceSource           (enterprise_marketplace_sources)              — ENT2-2.4
    - EnterpriseMarketplaceCatalogEntry     (enterprise_marketplace_catalog_entries)      — ENT2-2.4

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
    EnterpriseUser: Enterprise user account scoped to a tenant.
    EnterpriseTeam: Named user group scoped to a tenant.
    EnterpriseTeamMember: Junction table linking users to teams.
    EnterpriseTag: Tenant-scoped label for artifacts.
    EnterpriseArtifactTag: Junction table linking tags to artifacts.
    EnterpriseGroup: Named grouping of artifacts within a collection.
    EnterpriseGroupArtifact: Junction table linking groups to artifacts.
    EnterpriseSettings: One-row-per-tenant configuration store.
    EnterpriseEntityTypeConfig: Display configuration for artifact entity types.
    EnterpriseEntityCategory: Category taxonomy for context entities.
    EnterpriseContextEntity: Tenant-scoped context entity (CLAUDE.md, rules, specs).
    EnterpriseEntityCategoryAssociation: Junction linking context entities to categories.
    EnterpriseProject: Enterprise project record (informational path, DB-backed).
    EnterpriseProjectArtifact: Junction table tracking deployed artifacts per project.
    EnterpriseDeployment: Per-deployment record linking artifact to project.
    EnterpriseDeploymentSet: Named group of artifacts for coordinated deployment.
    EnterpriseDeploymentSetMember: Junction table linking artifacts to deployment sets.
    EnterpriseDeploymentSetTag: String tags for deployment sets.
    EnterpriseDeploymentProfile: Deployment configuration profile (scope, path, rules).
    EnterpriseMarketplaceSource: Registered GitHub repo for marketplace scanning.
    EnterpriseMarketplaceCatalogEntry: Discovered artifact listing from a scanned source.

References:
    docs/project_plans/architecture/enterprise-db-schema-v1.md
    .claude/findings/ENT2_TRIAGE.md
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
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
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
    # Ownership and visibility  (DB-003)
    # -------------------------------------------------------------------------

    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="UUID of the user who owns this artifact; NULL = system/unowned",
    )
    owner_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        default="user",
        comment="Owner type; stores OwnerType enum value, e.g. 'user' or 'team'",
    )
    visibility: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        default="private",
        comment="Visibility level; stores Visibility enum value, e.g. 'private', 'internal', 'public'",
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
        # B-tree: owner lookup — find all artifacts owned by a given user (DB-003)
        Index(
            "ix_enterprise_artifacts_owner_id",
            "owner_id",
        ),
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
    # Ownership and visibility  (DB-003)
    # -------------------------------------------------------------------------

    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="UUID of the user who owns this collection; NULL = system/unowned",
    )
    owner_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        default="user",
        comment="Owner type; stores OwnerType enum value, e.g. 'user' or 'team'",
    )
    visibility: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        default="private",
        comment="Visibility level; stores Visibility enum value, e.g. 'private', 'internal', 'public'",
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
        # B-tree: owner lookup — find all collections owned by a given user (DB-003)
        Index(
            "ix_enterprise_collections_owner_id",
            "owner_id",
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
        idx_ent_ca_collection_id:   (collection_id)
        idx_ent_ca_artifact_id:     (artifact_id)
        idx_ent_ca_collection_order: (collection_id, order_index)

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
            "idx_ent_ca_collection_id",
            "collection_id",
        ),
        # B-tree: reverse lookup — which collections contain a given artifact?
        Index(
            "idx_ent_ca_artifact_id",
            "artifact_id",
        ),
        # B-tree composite: ordered membership scan within a single collection
        # (used by EnterpriseCollection.memberships order_by clause)
        Index(
            "idx_ent_ca_collection_order",
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


# =============================================================================
# EnterpriseUser model  (AAA/RBAC Foundation — PRD-2, DB-001)
# =============================================================================


class EnterpriseUser(EnterpriseBase):
    """Enterprise user account scoped to a single tenant.

    Stores the identity and system-level role for each user within a tenant.
    The ``clerk_user_id`` column provides the mapping to the Clerk-managed
    external identity; it is nullable so that service accounts and seed rows
    can be created before Clerk integration is active.

    Tenant isolation invariant:
        Every query against this table MUST include a ``WHERE tenant_id = ?``
        predicate.  The repository layer (PRD-2 AAA repositories) enforces this
        structurally via a ``TenantScopedRepository`` base class.

    Attributes:
        id:            UUID PK, server-generated via gen_random_uuid().
        tenant_id:     Tenant scope; every query MUST filter by this column.
        clerk_user_id: External Clerk user identifier; unique within a tenant
                       when set.
        email:         User email address; unique within a tenant when set.
        display_name:  Optional human-readable display name.
        role:          System-wide role string; stores a ``UserRole`` enum value.
                       Defaults to ``"viewer"``.
        is_active:     Soft-delete flag.
        created_at:    Timezone-aware creation timestamp (server default: now()).
        updated_at:    Timezone-aware last-modified timestamp (app-managed).
        created_by:    User ID or ``"system"``; NULL until AuthContext is fully
                       wired.
        team_memberships: Back-reference to ``EnterpriseTeamMember`` rows.

    Constraints:
        uq_enterprise_users_tenant_clerk: UNIQUE (tenant_id, clerk_user_id)
        uq_enterprise_users_tenant_email: UNIQUE (tenant_id, email)

    Indexes:
        idx_enterprise_users_tenant_id:    (tenant_id)
        idx_enterprise_users_tenant_clerk: (tenant_id, clerk_user_id)
        idx_enterprise_users_tenant_email: (tenant_id, email)
        idx_enterprise_users_tenant_role:  (tenant_id, role)

    Schema reference:
        docs/project_plans/architecture/enterprise-db-schema-v1.md §3 (PRD-2)
    """

    __tablename__ = "enterprise_users"

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique user identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
    )

    # -------------------------------------------------------------------------
    # External identity
    # -------------------------------------------------------------------------

    clerk_user_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment=(
            "Clerk user_id for the external authentication provider. "
            "NULL for service accounts or before Clerk integration is active. "
            "Unique within a tenant (uq_enterprise_users_tenant_clerk)."
        ),
    )

    # -------------------------------------------------------------------------
    # Contact
    # -------------------------------------------------------------------------

    email: Mapped[Optional[str]] = mapped_column(
        String(320),
        nullable=True,
        comment=(
            "User email address. "
            "Unique within a tenant (uq_enterprise_users_tenant_email) when set."
        ),
    )
    display_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Human-readable display name shown in the UI",
    )

    # -------------------------------------------------------------------------
    # Role
    # -------------------------------------------------------------------------

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="viewer",
        server_default=text("'viewer'"),
        comment=(
            "System-wide role; one of UserRole enum values "
            "(viewer, team_member, team_admin, system_admin)"
        ),
    )

    # -------------------------------------------------------------------------
    # Soft-delete
    # -------------------------------------------------------------------------

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="Soft-delete: False = account disabled, row retained for audit",
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
        comment="User ID or 'system'; NULL until PRD-2 AuthContext is fully wired",
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------

    team_memberships: Mapped[List["EnterpriseTeamMember"]] = relationship(
        "EnterpriseTeamMember",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # -------------------------------------------------------------------------
    # Table-level constraints and indexes
    # -------------------------------------------------------------------------

    __table_args__ = (
        # Unique: one account per Clerk user_id per tenant
        UniqueConstraint(
            "tenant_id",
            "clerk_user_id",
            name="uq_enterprise_users_tenant_clerk",
        ),
        # Unique: one account per email address per tenant
        UniqueConstraint(
            "tenant_id",
            "email",
            name="uq_enterprise_users_tenant_email",
        ),
        # B-tree: mandatory per-tenant filter (every query starts here)
        Index(
            "idx_enterprise_users_tenant_id",
            "tenant_id",
        ),
        # B-tree: Clerk user_id lookup during authentication
        Index(
            "idx_enterprise_users_tenant_clerk",
            "tenant_id",
            "clerk_user_id",
        ),
        # B-tree: email lookup for invitation and login flows
        Index(
            "idx_enterprise_users_tenant_email",
            "tenant_id",
            "email",
        ),
        # B-tree: role-filtered listing (e.g. "show all system admins")
        Index(
            "idx_enterprise_users_tenant_role",
            "tenant_id",
            "role",
        ),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseUser."""
        return (
            f"<EnterpriseUser("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"email={self.email!r}, "
            f"role={self.role!r}, "
            f"is_active={self.is_active!r}"
            f")>"
        )


# =============================================================================
# EnterpriseTeam model  (AAA/RBAC Foundation — PRD-2, DB-001)
# =============================================================================


class EnterpriseTeam(EnterpriseBase):
    """Named group of enterprise users scoped to a single tenant.

    Teams allow multiple users to share ownership of artifacts and deployment
    sets within the same tenant.  One team name is unique per tenant.

    Tenant isolation invariant:
        Every query MUST include ``WHERE tenant_id = ?``.

    Attributes:
        id:          UUID PK, server-generated via gen_random_uuid().
        tenant_id:   Tenant scope.
        name:        Human-readable team name; unique within a tenant.
        description: Optional free-text description.
        is_active:   Soft-delete flag.
        created_at:  Timezone-aware creation timestamp.
        updated_at:  Timezone-aware last-modified timestamp.
        created_by:  User ID or ``"system"``; NULL until AuthContext is wired.
        members:     Back-reference to ``EnterpriseTeamMember`` rows.

    Constraints:
        uq_enterprise_teams_tenant_name: UNIQUE (tenant_id, name)

    Indexes:
        idx_enterprise_teams_tenant_id:   (tenant_id)
        idx_enterprise_teams_tenant_name: (tenant_id, name)

    Schema reference:
        docs/project_plans/architecture/enterprise-db-schema-v1.md §3 (PRD-2)
    """

    __tablename__ = "enterprise_teams"

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique team identifier",
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
        comment="Human-readable team name; unique within a tenant",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional free-text description of the team's purpose",
    )

    # -------------------------------------------------------------------------
    # Soft-delete
    # -------------------------------------------------------------------------

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="Soft-delete: False = team dissolved, row retained for audit",
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
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User ID or 'system'; NULL until PRD-2 AuthContext is fully wired",
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------

    members: Mapped[List["EnterpriseTeamMember"]] = relationship(
        "EnterpriseTeamMember",
        back_populates="team",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # -------------------------------------------------------------------------
    # Table-level constraints and indexes
    # -------------------------------------------------------------------------

    __table_args__ = (
        # Unique: one team name per tenant
        UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_enterprise_teams_tenant_name",
        ),
        # B-tree: mandatory per-tenant filter
        Index(
            "idx_enterprise_teams_tenant_id",
            "tenant_id",
        ),
        # B-tree: name lookup within a tenant
        Index(
            "idx_enterprise_teams_tenant_name",
            "tenant_id",
            "name",
        ),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseTeam."""
        return (
            f"<EnterpriseTeam("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"name={self.name!r}, "
            f"is_active={self.is_active!r}"
            f")>"
        )


# =============================================================================
# EnterpriseTeamMember model  (AAA/RBAC Foundation — PRD-2, DB-001)
# =============================================================================


class EnterpriseTeamMember(EnterpriseBase):
    """Junction table recording an enterprise user's membership in a team.

    Each row grants one user membership in one team at a specific team-level
    role.  Both ``team_id`` and ``user_id`` carry ``ON DELETE CASCADE`` foreign
    keys so orphaned membership rows are automatically removed when either the
    team or the user is deleted.

    ``tenant_id`` is denormalized from the parent ``EnterpriseTeam`` row for
    query performance — every cross-membership query can be filtered by tenant
    without joining back to the teams table.

    Tenant isolation invariant:
        Every query MUST include ``WHERE tenant_id = ?``.

    Attributes:
        id:         UUID PK, server-generated via gen_random_uuid().
        tenant_id:  Denormalized tenant scope for efficient querying.
        team_id:    FK → enterprise_teams.id, CASCADE on delete.
        user_id:    FK → enterprise_users.id, CASCADE on delete.
        role:       Team-level role string; stores a ``UserRole`` enum value.
                    Defaults to ``"team_member"``.
        joined_at:  UTC timestamp when the user joined (immutable after insert).
        created_by: User ID or ``"system"``; NULL until AuthContext is wired.
        team:       Many-to-one back-reference to ``EnterpriseTeam``.
        user:       Many-to-one back-reference to ``EnterpriseUser``.

    Constraints:
        uq_enterprise_team_members_tenant_team_user:
            UNIQUE (tenant_id, team_id, user_id) — one membership per user per team
            per tenant.

    Indexes:
        idx_enterprise_team_members_tenant_id:   (tenant_id)
        idx_enterprise_team_members_team_id:     (team_id)
        idx_enterprise_team_members_user_id:     (user_id)

    Schema reference:
        docs/project_plans/architecture/enterprise-db-schema-v1.md §3 (PRD-2)
    """

    __tablename__ = "enterprise_team_members"

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique membership row identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment=(
            "Denormalized tenant scope for query performance; "
            "must equal the parent team's tenant_id — validated at write time"
        ),
    )

    # -------------------------------------------------------------------------
    # Foreign keys
    # -------------------------------------------------------------------------

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_teams.id",
            ondelete="CASCADE",
            name="fk_enterprise_team_members_team_id",
        ),
        nullable=False,
        comment="Parent team; cascade-deletes this membership when team is removed",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_users.id",
            ondelete="CASCADE",
            name="fk_enterprise_team_members_user_id",
        ),
        nullable=False,
        comment="Member user; cascade-deletes this membership when user is removed",
    )

    # -------------------------------------------------------------------------
    # Team-level role
    # -------------------------------------------------------------------------

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="team_member",
        server_default=text("'team_member'"),
        comment="Role within the team; one of team_admin, team_member",
    )

    # -------------------------------------------------------------------------
    # Audit
    # -------------------------------------------------------------------------

    # joined_at is intentionally NOT an onupdate column — join date is immutable
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        comment="Timezone-aware timestamp when the user joined the team; immutable",
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User ID or 'system'; NULL until PRD-2 AuthContext is fully wired",
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------

    team: Mapped["EnterpriseTeam"] = relationship(
        "EnterpriseTeam",
        back_populates="members",
        lazy="joined",
    )
    user: Mapped["EnterpriseUser"] = relationship(
        "EnterpriseUser",
        back_populates="team_memberships",
        lazy="joined",
    )

    # -------------------------------------------------------------------------
    # Table-level constraints and indexes
    # -------------------------------------------------------------------------

    __table_args__ = (
        # Unique: one membership row per (tenant, team, user) triple
        UniqueConstraint(
            "tenant_id",
            "team_id",
            "user_id",
            name="uq_enterprise_team_members_tenant_team_user",
        ),
        # B-tree: mandatory per-tenant filter on cross-team membership queries
        Index(
            "idx_enterprise_team_members_tenant_id",
            "tenant_id",
        ),
        # B-tree: list all members of a given team
        Index(
            "idx_enterprise_team_members_team_id",
            "team_id",
        ),
        # B-tree: reverse lookup — which teams is a user in?
        Index(
            "idx_enterprise_team_members_user_id",
            "user_id",
        ),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseTeamMember."""
        return (
            f"<EnterpriseTeamMember("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"team_id={self.team_id!r}, "
            f"user_id={self.user_id!r}, "
            f"role={self.role!r}"
            f")>"
        )


# =============================================================================
# EnterpriseTag model  (ENT2-2.1)
# =============================================================================


class EnterpriseTag(EnterpriseBase):
    """Tenant-scoped label that can be applied to enterprise artifacts.

    Tags are lightweight string identifiers (with an optional display colour)
    used to categorise and filter artifacts within a tenant.  The ``slug``
    column provides a URL-safe normalised identifier derived from ``name`` at
    write time by the repository layer.

    Tenant isolation invariant:
        Every query MUST include ``WHERE tenant_id = ?``.

    Attributes:
        id:         UUID PK, client-generated via uuid.uuid4.
        tenant_id:  Tenant scope; every query MUST filter by this column.
        name:       Human-readable label, e.g. "frontend", "experimental".
        slug:       URL-safe normalised form of name, e.g. "frontend".
        color:      Optional hex or CSS colour for UI display.
        created_at: Timezone-aware creation timestamp.
        updated_at: Timezone-aware last-modified timestamp.
        artifact_tags: Back-reference to EnterpriseArtifactTag join rows.

    Constraints:
        uq_enterprise_tags_tenant_slug: UNIQUE (tenant_id, slug)

    Indexes:
        idx_enterprise_tags_tenant_id:   (tenant_id)
        idx_enterprise_tags_tenant_slug: (tenant_id, slug)
    """

    __tablename__ = "enterprise_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique tag identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable tag label, e.g. 'frontend', 'experimental'",
    )
    slug: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="URL-safe normalised form of name; unique within a tenant",
    )
    color: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional hex or CSS colour string for UI display, e.g. '#3B82F6'",
    )
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

    artifact_tags: Mapped[List["EnterpriseArtifactTag"]] = relationship(
        "EnterpriseArtifactTag",
        back_populates="tag",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "slug",
            name="uq_enterprise_tags_tenant_slug",
        ),
        Index("idx_enterprise_tags_tenant_id", "tenant_id"),
        Index("idx_enterprise_tags_tenant_slug", "tenant_id", "slug"),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseTag."""
        return (
            f"<EnterpriseTag("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"name={self.name!r}, "
            f"slug={self.slug!r}"
            f")>"
        )


# =============================================================================
# EnterpriseArtifactTag model  (ENT2-2.1 — join table)
# =============================================================================


class EnterpriseArtifactTag(EnterpriseBase):
    """Junction table associating enterprise artifacts with tags.

    Each row records that one artifact belongs to one tag within a tenant.
    Both FK columns carry ``ON DELETE CASCADE`` so orphaned rows are removed
    automatically when either the artifact or the tag is deleted.

    ``tenant_id`` is denormalized for query performance and to support
    tenant-scoped bulk queries without joining parent tables.

    Constraints:
        uq_enterprise_artifact_tags_tenant_tag_artifact:
            UNIQUE (tenant_id, tag_id, artifact_uuid) — one membership per pair

    Indexes:
        idx_ent_atag_tenant_id:    (tenant_id)
        idx_ent_atag_tag_id:       (tag_id)
        idx_ent_atag_artifact_uuid: (artifact_uuid)
    """

    __tablename__ = "enterprise_artifact_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique join-row identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Denormalized tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_tags.id",
            ondelete="CASCADE",
            name="fk_enterprise_artifact_tags_tag_id",
        ),
        nullable=False,
        comment="Parent tag; cascade-deletes this row when tag is removed",
    )
    artifact_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_artifacts.id",
            ondelete="CASCADE",
            name="fk_enterprise_artifact_tags_artifact_uuid",
        ),
        nullable=False,
        comment="Tagged artifact; cascade-deletes this row when artifact is removed",
    )

    tag: Mapped["EnterpriseTag"] = relationship(
        "EnterpriseTag",
        back_populates="artifact_tags",
        lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "tag_id",
            "artifact_uuid",
            name="uq_enterprise_artifact_tags_tenant_tag_artifact",
        ),
        Index("idx_ent_atag_tenant_id", "tenant_id"),
        Index("idx_ent_atag_tag_id", "tag_id"),
        Index("idx_ent_atag_artifact_uuid", "artifact_uuid"),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseArtifactTag."""
        return (
            f"<EnterpriseArtifactTag("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"tag_id={self.tag_id!r}, "
            f"artifact_uuid={self.artifact_uuid!r}"
            f")>"
        )


# =============================================================================
# EnterpriseGroup model  (ENT2-2.1)
# =============================================================================


class EnterpriseGroup(EnterpriseBase):
    """Named grouping of artifacts within a collection, scoped to a tenant.

    Groups allow users to organise artifacts into named sections within a
    collection.  The ``position`` column controls display order.  An optional
    ``collection_id`` FK ties a group to a specific collection; NULL means the
    group is collection-agnostic.

    Tenant isolation invariant:
        Every query MUST include ``WHERE tenant_id = ?``.

    Attributes:
        id:            UUID PK.
        tenant_id:     Tenant scope.
        name:          Human-readable group name.
        collection_id: Optional FK to enterprise_collections.id.
        description:   Optional free-text description.
        position:      Display order within the collection; lower = earlier.
        created_at:    Timezone-aware creation timestamp.
        updated_at:    Timezone-aware last-modified timestamp.
        group_artifacts: Back-reference to EnterpriseGroupArtifact join rows.

    Indexes:
        idx_enterprise_groups_tenant_id:         (tenant_id)
        idx_enterprise_groups_collection_id:     (collection_id)
        idx_enterprise_groups_tenant_collection: (tenant_id, collection_id)
    """

    __tablename__ = "enterprise_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique group identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    name: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable group name displayed in the UI",
    )
    collection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_collections.id",
            ondelete="SET NULL",
            name="fk_enterprise_groups_collection_id",
        ),
        nullable=True,
        comment="Optional parent collection; NULL = collection-agnostic group",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional free-text description of the group",
    )
    position: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=0,
        server_default=text("0"),
        comment="Display order within the collection; lower = earlier",
    )
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

    group_artifacts: Mapped[List["EnterpriseGroupArtifact"]] = relationship(
        "EnterpriseGroupArtifact",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="EnterpriseGroupArtifact.position",
    )

    __table_args__ = (
        Index("idx_enterprise_groups_tenant_id", "tenant_id"),
        Index("idx_enterprise_groups_collection_id", "collection_id"),
        Index(
            "idx_enterprise_groups_tenant_collection",
            "tenant_id",
            "collection_id",
        ),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseGroup."""
        return (
            f"<EnterpriseGroup("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"name={self.name!r}, "
            f"collection_id={self.collection_id!r}"
            f")>"
        )


# =============================================================================
# EnterpriseGroupArtifact model  (ENT2-2.1 — join table)
# =============================================================================


class EnterpriseGroupArtifact(EnterpriseBase):
    """Junction table recording artifact membership within an enterprise group.

    Each row places one artifact in one group at an explicit ``position``.
    Both FK columns carry ``ON DELETE CASCADE`` so orphaned rows are removed
    automatically when either parent is deleted.

    ``tenant_id`` is denormalized for per-tenant bulk queries.

    Constraints:
        uq_enterprise_group_artifacts_tenant_group_artifact:
            UNIQUE (tenant_id, group_id, artifact_uuid)

    Indexes:
        idx_ent_ga_tenant_id:    (tenant_id)
        idx_ent_ga_group_id:     (group_id)
        idx_ent_ga_artifact_uuid: (artifact_uuid)
        idx_ent_ga_group_position: (group_id, position)
    """

    __tablename__ = "enterprise_group_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique join-row identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Denormalized tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_groups.id",
            ondelete="CASCADE",
            name="fk_enterprise_group_artifacts_group_id",
        ),
        nullable=False,
        comment="Parent group; cascade-deletes this row when group is removed",
    )
    artifact_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_artifacts.id",
            ondelete="CASCADE",
            name="fk_enterprise_group_artifacts_artifact_uuid",
        ),
        nullable=False,
        comment="Member artifact; cascade-deletes this row when artifact is removed",
    )
    position: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=0,
        server_default=text("0"),
        comment="Display order within the group; lower = earlier",
    )

    group: Mapped["EnterpriseGroup"] = relationship(
        "EnterpriseGroup",
        back_populates="group_artifacts",
        lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "group_id",
            "artifact_uuid",
            name="uq_enterprise_group_artifacts_tenant_group_artifact",
        ),
        Index("idx_ent_ga_tenant_id", "tenant_id"),
        Index("idx_ent_ga_group_id", "group_id"),
        Index("idx_ent_ga_artifact_uuid", "artifact_uuid"),
        Index("idx_ent_ga_group_position", "group_id", "position"),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseGroupArtifact."""
        return (
            f"<EnterpriseGroupArtifact("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"group_id={self.group_id!r}, "
            f"artifact_uuid={self.artifact_uuid!r}, "
            f"position={self.position!r}"
            f")>"
        )


# =============================================================================
# EnterpriseSettings model  (ENT2-2.1 — one row per tenant)
# =============================================================================


class EnterpriseSettings(EnterpriseBase):
    """Per-tenant settings record — exactly one row per tenant.

    Stores tenant-level configuration that in local mode is persisted to
    ``~/.skillmeat/config.toml``.  In enterprise mode all settings are stored
    in this DB table so that each tenant has independent configuration.

    The ``extra`` JSONB column provides forward-compatible extension for
    settings not yet promoted to first-class columns.

    Tenant isolation invariant:
        ``tenant_id`` is UNIQUE — one row per tenant enforced at DB level.
        Every query MUST include ``WHERE tenant_id = ?``.

    Attributes:
        id:               UUID PK.
        tenant_id:        Tenant scope; UNIQUE constraint ensures one row per tenant.
        github_token:     Encrypted or plaintext GitHub API token for this tenant.
        collection_path:  Override path for the tenant's local collection root.
        default_scope:    Default artifact scope ('user' or 'local').
        edition:          Active edition string, e.g. 'enterprise'.
        indexing_mode:    Indexing mode for artifact search.
        extra:            JSONB bag for forward-compatible extension.
        updated_at:       Timezone-aware last-modified timestamp.

    Constraints:
        uq_enterprise_settings_tenant: UNIQUE (tenant_id)

    Indexes:
        idx_enterprise_settings_tenant_id: (tenant_id)
    """

    __tablename__ = "enterprise_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique settings-row identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment=(
            "Tenant scope; UNIQUE constraint ensures exactly one settings row per tenant. "
            "Every query MUST include WHERE tenant_id = ?"
        ),
    )
    github_token: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="GitHub API token for this tenant (may be encrypted at rest)",
    )
    collection_path: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Override path for the tenant's local collection root directory",
    )
    default_scope: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Default artifact scope when not specified; 'user' or 'local'",
    )
    edition: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Active edition string for this tenant, e.g. 'enterprise'",
    )
    indexing_mode: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Artifact indexing mode; controls which indexer strategy is used",
    )
    extra: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="JSONB bag for forward-compatible extension; initialized to empty object",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=datetime.utcnow,
        comment="Timezone-aware last-modified timestamp; updated by app on every write",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            name="uq_enterprise_settings_tenant",
        ),
        Index("idx_enterprise_settings_tenant_id", "tenant_id"),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseSettings."""
        return (
            f"<EnterpriseSettings("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"edition={self.edition!r}"
            f")>"
        )


# =============================================================================
# EnterpriseEntityTypeConfig model  (ENT2-2.1)
# =============================================================================


class EnterpriseEntityTypeConfig(EnterpriseBase):
    """Display and behaviour configuration for a specific artifact entity type.

    Stores per-tenant overrides for how each artifact type (skill, command,
    agent, etc.) is displayed and labelled in the UI.  System-supplied defaults
    are rows where ``is_system = True``; tenant customisations use
    ``is_system = False``.

    Tenant isolation invariant:
        Every query MUST include ``WHERE tenant_id = ?``.

    Attributes:
        id:           UUID PK.
        tenant_id:    Tenant scope.
        entity_type:  Artifact type identifier, e.g. 'skill', 'command'.
        display_name: Human-readable label for the type in the UI.
        description:  Optional description shown in type selectors.
        icon:         Optional icon identifier or URL.
        color:        Optional hex or CSS colour for UI badges.
        is_system:    True = shipped default; False = tenant customisation.

    Constraints:
        uq_enterprise_entity_type_configs_tenant_type:
            UNIQUE (tenant_id, entity_type)

    Indexes:
        idx_enterprise_etc_tenant_id:   (tenant_id)
        idx_enterprise_etc_tenant_type: (tenant_id, entity_type)
    """

    __tablename__ = "enterprise_entity_type_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique config row identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    entity_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Artifact type identifier, e.g. 'skill', 'command', 'agent'",
    )
    display_name: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable label for this type in the UI",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description shown in type selector dropdowns",
    )
    icon: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional icon identifier or URL for UI display",
    )
    color: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional hex or CSS colour for type badges in the UI",
    )
    is_system: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        default=False,
        server_default=text("false"),
        comment="True = shipped default config; False = tenant override",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "entity_type",
            name="uq_enterprise_entity_type_configs_tenant_type",
        ),
        Index("idx_enterprise_etc_tenant_id", "tenant_id"),
        Index("idx_enterprise_etc_tenant_type", "tenant_id", "entity_type"),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseEntityTypeConfig."""
        return (
            f"<EnterpriseEntityTypeConfig("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"entity_type={self.entity_type!r}, "
            f"is_system={self.is_system!r}"
            f")>"
        )


# =============================================================================
# EnterpriseEntityCategory model  (ENT2-2.1)
# =============================================================================


class EnterpriseEntityCategory(EnterpriseBase):
    """Category taxonomy entry for classifying context entities.

    Categories group context entities (CLAUDE.md files, rule files, spec files,
    etc.) into named buckets for filtering and display.  Each category optionally
    targets a specific ``entity_type`` and ``platform``.

    Tenant isolation invariant:
        Every query MUST include ``WHERE tenant_id = ?``.

    Attributes:
        id:          UUID PK.
        tenant_id:   Tenant scope.
        name:        Human-readable category name.
        slug:        URL-safe normalised identifier; unique per tenant.
        entity_type: Optional entity type this category applies to.
        description: Optional free-text description.
        color:       Optional hex or CSS colour for UI display.
        platform:    Optional platform filter, e.g. 'claude', 'cursor'.
        sort_order:  Display order; lower = earlier.

    Constraints:
        uq_enterprise_entity_categories_tenant_slug: UNIQUE (tenant_id, slug)

    Indexes:
        idx_enterprise_ec_tenant_id:   (tenant_id)
        idx_enterprise_ec_tenant_slug: (tenant_id, slug)
        idx_enterprise_ec_entity_type: (tenant_id, entity_type)
    """

    __tablename__ = "enterprise_entity_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique category identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable category name displayed in the UI",
    )
    slug: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="URL-safe normalised identifier; unique within a tenant",
    )
    entity_type: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional entity type this category applies to, e.g. 'rule_file'",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional free-text description of the category",
    )
    color: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional hex or CSS colour for category badges in the UI",
    )
    platform: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional platform filter, e.g. 'claude', 'cursor', 'windsurf'",
    )
    sort_order: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=0,
        server_default=text("0"),
        comment="Display order; lower = earlier",
    )

    entity_category_associations: Mapped[List["EnterpriseEntityCategoryAssociation"]] = relationship(
        "EnterpriseEntityCategoryAssociation",
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "slug",
            name="uq_enterprise_entity_categories_tenant_slug",
        ),
        Index("idx_enterprise_ec_tenant_id", "tenant_id"),
        Index("idx_enterprise_ec_tenant_slug", "tenant_id", "slug"),
        Index("idx_enterprise_ec_entity_type", "tenant_id", "entity_type"),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseEntityCategory."""
        return (
            f"<EnterpriseEntityCategory("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"name={self.name!r}, "
            f"slug={self.slug!r}"
            f")>"
        )


# =============================================================================
# EnterpriseContextEntity model  (ENT2-2.2)
# =============================================================================


class EnterpriseContextEntity(EnterpriseBase):
    """Tenant-scoped context entity stored in the enterprise database.

    Context entities represent files like CLAUDE.md, rule files, spec files, and
    other configuration entities that the Claude Code agent loads at runtime.
    In local mode these are stored as ``Artifact`` rows in SQLite; in enterprise
    mode they are stored here with richer metadata and multi-tenant isolation.

    The ``deploy()`` operation writes content to a caller-supplied
    ``project_path`` on the local filesystem; all other operations are pure DB.

    Tenant isolation invariant:
        Every query MUST include ``WHERE tenant_id = ?``.

    Attributes:
        id:               UUID PK.
        tenant_id:        Tenant scope.
        name:             Human-readable entity name, e.g. 'CLAUDE.md'.
        entity_type:      Entity type discriminator, e.g. 'context_file', 'rule_file'.
        content:          Entity file content; NULL until content is loaded.
        path_pattern:     Target path pattern for deployment, e.g. '.claude/rules/*.md'.
        description:      Optional free-text description.
        category:         Optional category label string.
        auto_load:        Whether this entity should be auto-loaded by the agent.
        version:          Optional version label.
        target_platforms: JSONB array of platform identifiers, e.g. ['claude', 'cursor'].
        created_at:       Timezone-aware creation timestamp.
        updated_at:       Timezone-aware last-modified timestamp.
        category_associations: Back-reference to EnterpriseEntityCategoryAssociation rows.

    Indexes:
        idx_enterprise_ce_tenant_id:      (tenant_id)
        idx_enterprise_ce_tenant_type:    (tenant_id, entity_type)
        idx_enterprise_ce_tenant_autoload: (tenant_id, auto_load) WHERE auto_load = TRUE
    """

    __tablename__ = "enterprise_context_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique context entity identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable entity name, e.g. 'CLAUDE.md', 'debugging-rule'",
    )
    entity_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Entity type discriminator, e.g. 'context_file', 'rule_file', 'spec_file'",
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Entity file content; NULL when only metadata has been loaded",
    )
    path_pattern: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Target path pattern for deployment, e.g. '.claude/rules/*.md'",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional free-text description of this entity's purpose",
    )
    category: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional category label string; use category_associations for structured FK refs",
    )
    auto_load: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        default=False,
        server_default=text("false"),
        comment="When TRUE, the agent should auto-load this entity at startup",
    )
    version: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional version label, e.g. 'v1.0.0' or a SHA prefix",
    )
    target_platforms: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="JSONB array of platform identifiers this entity targets, e.g. ['claude', 'cursor']",
    )
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

    category_associations: Mapped[List["EnterpriseEntityCategoryAssociation"]] = relationship(
        "EnterpriseEntityCategoryAssociation",
        back_populates="entity",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="EnterpriseEntityCategoryAssociation.position",
    )

    __table_args__ = (
        Index("idx_enterprise_ce_tenant_id", "tenant_id"),
        Index("idx_enterprise_ce_tenant_type", "tenant_id", "entity_type"),
        Index(
            "idx_enterprise_ce_tenant_autoload",
            "tenant_id",
            "auto_load",
            postgresql_where=text("auto_load = TRUE"),
        ),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseContextEntity."""
        return (
            f"<EnterpriseContextEntity("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"name={self.name!r}, "
            f"entity_type={self.entity_type!r}"
            f")>"
        )


# =============================================================================
# EnterpriseEntityCategoryAssociation model  (ENT2-2.2 — join table)
# =============================================================================


class EnterpriseEntityCategoryAssociation(EnterpriseBase):
    """Junction table linking context entities to entity categories.

    Each row places one context entity in one category at an optional
    ``position`` for display ordering.  Both FK columns carry
    ``ON DELETE CASCADE``.

    Note: this table is distinct from any future settings-domain association
    table.  It links ``enterprise_context_entities`` to
    ``enterprise_entity_categories`` only.

    ``tenant_id`` is denormalized for per-tenant bulk queries.

    Constraints:
        uq_ent_eca_tenant_entity_category:
            UNIQUE (tenant_id, entity_id, category_id)

    Indexes:
        idx_ent_eca_tenant_id:   (tenant_id)
        idx_ent_eca_entity_id:   (entity_id)
        idx_ent_eca_category_id: (category_id)
    """

    __tablename__ = "enterprise_entity_category_associations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique join-row identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Denormalized tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_context_entities.id",
            ondelete="CASCADE",
            name="fk_ent_eca_entity_id",
        ),
        nullable=False,
        comment="Parent context entity; cascade-deletes this row when entity is removed",
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_entity_categories.id",
            ondelete="CASCADE",
            name="fk_ent_eca_category_id",
        ),
        nullable=False,
        comment="Parent category; cascade-deletes this row when category is removed",
    )
    position: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=0,
        server_default=text("0"),
        comment="Display order within the category; lower = earlier",
    )

    entity: Mapped["EnterpriseContextEntity"] = relationship(
        "EnterpriseContextEntity",
        back_populates="category_associations",
        lazy="joined",
    )
    category: Mapped["EnterpriseEntityCategory"] = relationship(
        "EnterpriseEntityCategory",
        back_populates="entity_category_associations",
        lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "entity_id",
            "category_id",
            name="uq_ent_eca_tenant_entity_category",
        ),
        Index("idx_ent_eca_tenant_id", "tenant_id"),
        Index("idx_ent_eca_entity_id", "entity_id"),
        Index("idx_ent_eca_category_id", "category_id"),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseEntityCategoryAssociation."""
        return (
            f"<EnterpriseEntityCategoryAssociation("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"entity_id={self.entity_id!r}, "
            f"category_id={self.category_id!r}"
            f")>"
        )


# =============================================================================
# EnterpriseProject model  (ENT2-2.3)
# =============================================================================


class EnterpriseProject(EnterpriseBase):
    """Enterprise project record — DB-backed, informational filesystem path.

    Projects represent named Claude Code project workspaces.  In enterprise mode
    the ``path`` column is informational: it records where the project *was* when
    registered, but repository methods that require live filesystem access are
    treated as caller-driven side effects and do not scan disk within repository
    methods.

    Path uniqueness invariant:
        ``path`` is unique per tenant (one tenant cannot register the same path
        twice; two tenants may share the same path string).

    Tenant isolation invariant:
        Every query MUST include ``WHERE tenant_id = ?``.

    Attributes:
        id:          UUID PK.
        tenant_id:   Tenant scope.
        name:        Human-readable project name.
        path:        Filesystem path at registration time (informational only).
        status:      Project status string, e.g. 'active', 'archived'.
        description: Optional free-text description.
        created_at:  Timezone-aware creation timestamp.
        updated_at:  Timezone-aware last-modified timestamp.
        project_artifacts: Back-reference to EnterpriseProjectArtifact join rows.
        deployments:       Back-reference to EnterpriseDeployment rows.

    Constraints:
        uq_enterprise_projects_tenant_path: UNIQUE (tenant_id, path)

    Indexes:
        idx_enterprise_projects_tenant_id:   (tenant_id)
        idx_enterprise_projects_tenant_path: (tenant_id, path)
    """

    __tablename__ = "enterprise_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique project identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable project name",
    )
    path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Filesystem path at registration time — INFORMATIONAL ONLY in enterprise mode. "
            "The enterprise IProjectRepository never scans this path directly; "
            "FS operations remain in the CLI layer and are synced via write-through."
        ),
    )
    status: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Project status string, e.g. 'active', 'archived', 'initializing'",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional free-text description of this project",
    )
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

    project_artifacts: Mapped[List["EnterpriseProjectArtifact"]] = relationship(
        "EnterpriseProjectArtifact",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
    )
    deployments: Mapped[List["EnterpriseDeployment"]] = relationship(
        "EnterpriseDeployment",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "path",
            name="uq_enterprise_projects_tenant_path",
        ),
        Index("idx_enterprise_projects_tenant_id", "tenant_id"),
        Index("idx_enterprise_projects_tenant_path", "tenant_id", "path"),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseProject."""
        return (
            f"<EnterpriseProject("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"name={self.name!r}, "
            f"path={self.path!r}, "
            f"status={self.status!r}"
            f")>"
        )


# =============================================================================
# EnterpriseProjectArtifact model  (ENT2-2.3 — join table)
# =============================================================================


class EnterpriseProjectArtifact(EnterpriseBase):
    """Junction table tracking artifacts deployed to an enterprise project.

    Each row records that one artifact has been deployed to one project, along
    with deployment metadata (when, content hash, local modification flag).

    Both FK columns carry ``ON DELETE CASCADE``.  ``tenant_id`` is denormalized
    for per-tenant bulk queries.

    Constraints:
        uq_enterprise_project_artifacts_tenant_project_artifact:
            UNIQUE (tenant_id, project_id, artifact_uuid)

    Indexes:
        idx_ent_pa_tenant_id:    (tenant_id)
        idx_ent_pa_project_id:   (project_id)
        idx_ent_pa_artifact_uuid: (artifact_uuid)
    """

    __tablename__ = "enterprise_project_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique join-row identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Denormalized tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_projects.id",
            ondelete="CASCADE",
            name="fk_enterprise_project_artifacts_project_id",
        ),
        nullable=False,
        comment="Parent project; cascade-deletes this row when project is removed",
    )
    artifact_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_artifacts.id",
            ondelete="CASCADE",
            name="fk_enterprise_project_artifacts_artifact_uuid",
        ),
        nullable=False,
        comment="Deployed artifact; cascade-deletes this row when artifact is removed",
    )
    deployed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timezone-aware timestamp when this artifact was deployed to the project",
    )
    content_hash: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="SHA256 hex digest of the artifact content at deployment time",
    )
    local_modifications: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        default=False,
        server_default=text("false"),
        comment="True when local project file has been modified since deployment",
    )

    project: Mapped["EnterpriseProject"] = relationship(
        "EnterpriseProject",
        back_populates="project_artifacts",
        lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "project_id",
            "artifact_uuid",
            name="uq_enterprise_project_artifacts_tenant_project_artifact",
        ),
        Index("idx_ent_pa_tenant_id", "tenant_id"),
        Index("idx_ent_pa_project_id", "project_id"),
        Index("idx_ent_pa_artifact_uuid", "artifact_uuid"),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseProjectArtifact."""
        return (
            f"<EnterpriseProjectArtifact("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"project_id={self.project_id!r}, "
            f"artifact_uuid={self.artifact_uuid!r}"
            f")>"
        )


# =============================================================================
# EnterpriseDeployment model  (ENT2-2.3)
# =============================================================================


class EnterpriseDeployment(EnterpriseBase):
    """Per-deployment record tracking artifact deployment to a project.

    Each row records one deployment event: which artifact was deployed, to which
    project, and the resulting state.  The ``artifact_id`` column stores the
    text-format artifact identifier (e.g. ``"skill:canvas-design"``) for
    compatibility with the existing ``sync_deployment_cache()`` interface.
    ``artifact_uuid`` is the FK to ``enterprise_artifacts.id`` and is the
    preferred reference in enterprise-mode queries.

    Tenant isolation invariant:
        Every query MUST include ``WHERE tenant_id = ?``.

    Attributes:
        id:                    UUID PK.
        tenant_id:             Tenant scope.
        artifact_id:           Text-format artifact identifier (type:name) for
                               backward compatibility with sync interfaces.
        artifact_uuid:         UUID FK to enterprise_artifacts.id (preferred ref).
        project_id:            Optional FK to enterprise_projects.id.
        status:                Deployment status, e.g. 'deployed', 'undeployed'.
        deployed_at:           Timestamp of the deployment event.
        content_hash:          SHA256 hash of content at deployment time.
        deployment_profile_id: Optional FK UUID for the deployment profile used.
        local_modifications:   True when local file has diverged from deployed content.
        platform:              Target platform, e.g. 'claude', 'cursor'.
        created_at:            Timezone-aware creation timestamp.
        updated_at:            Timezone-aware last-modified timestamp.
        project:               Many-to-one back-reference to EnterpriseProject.

    Indexes:
        idx_enterprise_deployments_tenant_id:       (tenant_id)
        idx_enterprise_deployments_artifact_id:     (artifact_id)
        idx_enterprise_deployments_artifact_uuid:   (artifact_uuid)
        idx_enterprise_deployments_project_id:      (project_id)
        idx_enterprise_deployments_tenant_status:   (tenant_id, status)
    """

    __tablename__ = "enterprise_deployments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique deployment record identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    artifact_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Text-format artifact identifier, e.g. 'skill:canvas-design'. "
            "Preserved for backward compatibility with sync_deployment_cache() callers. "
            "In enterprise mode prefer artifact_uuid for FK-backed queries."
        ),
    )
    artifact_uuid: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_artifacts.id",
            ondelete="SET NULL",
            name="fk_enterprise_deployments_artifact_uuid",
        ),
        nullable=True,
        comment=(
            "UUID FK to enterprise_artifacts.id — preferred reference in enterprise queries. "
            "NULL for deployments recorded before the artifact was indexed in enterprise DB."
        ),
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_projects.id",
            ondelete="SET NULL",
            name="fk_enterprise_deployments_project_id",
        ),
        nullable=True,
        comment="Optional parent project; SET NULL when project is removed",
    )
    status: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Deployment status string, e.g. 'deployed', 'undeployed', 'pending'",
    )
    deployed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timezone-aware timestamp of the deployment event",
    )
    content_hash: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="SHA256 hex digest of artifact content at deployment time",
    )
    deployment_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Optional UUID reference to the deployment profile used; no FK enforced",
    )
    local_modifications: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        default=False,
        server_default=text("false"),
        comment="True when the local project file has diverged from the deployed content",
    )
    platform: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Target platform for this deployment, e.g. 'claude', 'cursor', 'windsurf'",
    )
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

    project: Mapped[Optional["EnterpriseProject"]] = relationship(
        "EnterpriseProject",
        back_populates="deployments",
        lazy="joined",
    )

    __table_args__ = (
        Index("idx_enterprise_deployments_tenant_id", "tenant_id"),
        Index("idx_enterprise_deployments_artifact_id", "artifact_id"),
        Index("idx_enterprise_deployments_artifact_uuid", "artifact_uuid"),
        Index("idx_enterprise_deployments_project_id", "project_id"),
        Index("idx_enterprise_deployments_tenant_status", "tenant_id", "status"),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseDeployment."""
        return (
            f"<EnterpriseDeployment("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"artifact_id={self.artifact_id!r}, "
            f"project_id={self.project_id!r}, "
            f"status={self.status!r}"
            f")>"
        )


# =============================================================================
# EnterpriseDeploymentSet model  (ENT2-2.3)
# =============================================================================


class EnterpriseDeploymentSet(EnterpriseBase):
    """Named group of artifacts for coordinated deployment (IDP provisioning).

    Deployment sets represent a curated bundle of artifacts that are deployed
    together, e.g. for an IDP (Internal Developer Platform) provisioning
    workflow.  The ``provisioned_by`` column records the system or user that
    created the set.

    Tenant isolation invariant:
        Every query MUST include ``WHERE tenant_id = ?``.

    Attributes:
        id:              UUID PK.
        tenant_id:       Tenant scope.
        name:            Human-readable set name; unique within a tenant.
        remote_url:      Optional URL linking to the canonical definition.
        provisioned_by:  System or user that provisioned this set.
        description:     Optional free-text description.
        tags_json:       Serialized tag list (TEXT, not JSONB) for compatibility
                         with the local DeploymentSetRepository tag filter.
        created_at:      Timezone-aware creation timestamp.
        updated_at:      Timezone-aware last-modified timestamp.
        members:         Back-reference to EnterpriseDeploymentSetMember rows.
        set_tags:        Back-reference to EnterpriseDeploymentSetTag rows.

    Constraints:
        uq_enterprise_deployment_sets_tenant_name: UNIQUE (tenant_id, name)

    Indexes:
        idx_enterprise_dsets_tenant_id:   (tenant_id)
        idx_enterprise_dsets_tenant_name: (tenant_id, name)
    """

    __tablename__ = "enterprise_deployment_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique deployment set identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable set name; unique within a tenant",
    )
    remote_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional URL linking to the canonical definition of this set",
    )
    provisioned_by: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="System or user identifier that provisioned this deployment set",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional free-text description of the set's purpose",
    )
    tags_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Serialized tag list as TEXT (e.g. JSON array string). "
            "Kept as TEXT for compatibility with the local DeploymentSetRepository "
            "tag-filter pattern. Prefer EnterpriseDeploymentSetTag rows for structured access."
        ),
    )
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

    members: Mapped[List["EnterpriseDeploymentSetMember"]] = relationship(
        "EnterpriseDeploymentSetMember",
        back_populates="deployment_set",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="EnterpriseDeploymentSetMember.position",
    )
    set_tags: Mapped[List["EnterpriseDeploymentSetTag"]] = relationship(
        "EnterpriseDeploymentSetTag",
        back_populates="deployment_set",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_enterprise_deployment_sets_tenant_name",
        ),
        Index("idx_enterprise_dsets_tenant_id", "tenant_id"),
        Index("idx_enterprise_dsets_tenant_name", "tenant_id", "name"),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseDeploymentSet."""
        return (
            f"<EnterpriseDeploymentSet("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"name={self.name!r}"
            f")>"
        )


# =============================================================================
# EnterpriseDeploymentSetMember model  (ENT2-2.3 — join table)
# =============================================================================


class EnterpriseDeploymentSetMember(EnterpriseBase):
    """Junction table linking artifacts to an enterprise deployment set.

    Each row places one artifact (by text identifier) in one deployment set
    at an explicit ``position``.  The FK to ``enterprise_deployment_sets``
    carries ``ON DELETE CASCADE``.

    Note: ``artifact_id`` is a text-format identifier (e.g. ``"skill:canvas"``)
    matching the local ``DeploymentSetMember`` pattern; no FK to
    ``enterprise_artifacts`` is required here since the identifier may refer
    to artifacts not yet indexed in the enterprise DB.

    ``tenant_id`` is denormalized for per-tenant bulk queries.

    Constraints:
        uq_enterprise_dsm_tenant_set_artifact:
            UNIQUE (tenant_id, set_id, artifact_id)

    Indexes:
        idx_ent_dsm_tenant_id: (tenant_id)
        idx_ent_dsm_set_id:    (set_id)
    """

    __tablename__ = "enterprise_deployment_set_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique join-row identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Denormalized tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_deployment_sets.id",
            ondelete="CASCADE",
            name="fk_enterprise_dsm_set_id",
        ),
        nullable=False,
        comment="Parent deployment set; cascade-deletes this row when set is removed",
    )
    artifact_id: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Text-format artifact identifier, e.g. 'skill:canvas-design'",
    )
    position: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=0,
        server_default=text("0"),
        comment="Ordering position within the deployment set; lower = earlier",
    )

    deployment_set: Mapped["EnterpriseDeploymentSet"] = relationship(
        "EnterpriseDeploymentSet",
        back_populates="members",
        lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "set_id",
            "artifact_id",
            name="uq_enterprise_dsm_tenant_set_artifact",
        ),
        Index("idx_ent_dsm_tenant_id", "tenant_id"),
        Index("idx_ent_dsm_set_id", "set_id"),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseDeploymentSetMember."""
        return (
            f"<EnterpriseDeploymentSetMember("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"set_id={self.set_id!r}, "
            f"artifact_id={self.artifact_id!r}, "
            f"position={self.position!r}"
            f")>"
        )


# =============================================================================
# EnterpriseDeploymentSetTag model  (ENT2-2.3 — join table)
# =============================================================================


class EnterpriseDeploymentSetTag(EnterpriseBase):
    """String tags for enterprise deployment sets.

    Each row associates one string tag with one deployment set.  This mirrors
    the local ``DeploymentSetTag`` model and supports tag-based filtering in
    the deployment set repository.

    The ``tag`` column holds a plain string (not a FK to ``enterprise_tags``)
    to remain consistent with the local implementation's string-based tag
    model.  ``tenant_id`` is denormalized for per-tenant bulk queries.

    Constraints:
        uq_enterprise_dst_set_tag: UNIQUE (set_id, tag)

    Indexes:
        idx_ent_dst_tenant_id: (tenant_id)
        idx_ent_dst_set_id:    (set_id)
        idx_ent_dst_tag:       (tag)
    """

    __tablename__ = "enterprise_deployment_set_tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique tag-row identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Denormalized tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_deployment_sets.id",
            ondelete="CASCADE",
            name="fk_enterprise_dst_set_id",
        ),
        nullable=False,
        comment="Parent deployment set; cascade-deletes this row when set is removed",
    )
    tag: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="String tag for filtering and grouping deployment sets",
    )

    deployment_set: Mapped["EnterpriseDeploymentSet"] = relationship(
        "EnterpriseDeploymentSet",
        back_populates="set_tags",
        lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint(
            "set_id",
            "tag",
            name="uq_enterprise_dst_set_tag",
        ),
        Index("idx_ent_dst_tenant_id", "tenant_id"),
        Index("idx_ent_dst_set_id", "set_id"),
        Index("idx_ent_dst_tag", "tag"),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseDeploymentSetTag."""
        return (
            f"<EnterpriseDeploymentSetTag("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"set_id={self.set_id!r}, "
            f"tag={self.tag!r}"
            f")>"
        )


# =============================================================================
# EnterpriseDeploymentProfile model  (ENT2-2.3)
# =============================================================================


class EnterpriseDeploymentProfile(EnterpriseBase):
    """Deployment configuration profile governing how artifacts are deployed.

    A deployment profile captures the configuration for a deployment operation:
    target scope, destination path, overwrite rules, and platform targeting.
    Each profile belongs to one tenant.

    Tenant isolation invariant:
        Every query MUST include ``WHERE tenant_id = ?``.

    Attributes:
        id:         UUID PK.
        tenant_id:  Tenant scope.
        name:       Human-readable profile name; unique within a tenant.
        scope:      Deployment scope, e.g. 'user', 'local', 'project'.
        dest_path:  Destination path template for deployed artifacts.
        overwrite:  When True, existing files are overwritten without prompt.
        platform:   Target platform, e.g. 'claude', 'cursor', 'windsurf'.
        metadata:   JSONB bag for forward-compatible extension.
        created_at: Timezone-aware creation timestamp.
        updated_at: Timezone-aware last-modified timestamp.

    Constraints:
        uq_enterprise_deployment_profiles_tenant_name: UNIQUE (tenant_id, name)

    Indexes:
        idx_enterprise_dp_tenant_id:   (tenant_id)
        idx_enterprise_dp_tenant_name: (tenant_id, name)
    """

    __tablename__ = "enterprise_deployment_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique deployment profile identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable profile name; unique within a tenant",
    )
    scope: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Deployment scope, e.g. 'user', 'local', 'project'",
    )
    dest_path: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Destination path template; may contain placeholders like {artifact_name}",
    )
    overwrite: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        default=False,
        server_default=text("false"),
        comment="When TRUE, existing destination files are overwritten without prompt",
    )
    platform: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Target platform for deployments using this profile, e.g. 'claude', 'cursor'",
    )
    # Named extra_metadata (not metadata) to avoid shadowing
    # SQLAlchemy's reserved DeclarativeBase.metadata attribute.
    extra_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="JSONB bag for forward-compatible extension; NULL until explicitly set",
    )
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

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_enterprise_deployment_profiles_tenant_name",
        ),
        Index("idx_enterprise_dp_tenant_id", "tenant_id"),
        Index("idx_enterprise_dp_tenant_name", "tenant_id", "name"),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseDeploymentProfile."""
        return (
            f"<EnterpriseDeploymentProfile("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"name={self.name!r}, "
            f"scope={self.scope!r}"
            f")>"
        )


# =============================================================================
# EnterpriseMarketplaceSource model  (ENT2-2.4)
# =============================================================================


class EnterpriseMarketplaceSource(EnterpriseBase):
    """Registered GitHub repository available as a marketplace artifact source.

    Each row represents a GitHub repo that a tenant has registered for artifact
    discovery scanning.  The scanner populates ``artifact_count`` and
    ``last_sync_at`` after each scan run.

    Tenant isolation invariant:
        Every query MUST include ``WHERE tenant_id = ?``.

    Attributes:
        id:             UUID PK.
        tenant_id:      Tenant scope.
        repo_url:       Full GitHub repository URL (required).
        owner:          GitHub repository owner (org or username).
        repo_name:      GitHub repository name.
        ref:            Git ref to scan, e.g. 'main', 'v1.2.0'.
        scan_status:    Current scan state, e.g. 'pending', 'scanning', 'done', 'error'.
        artifact_count: Number of artifacts discovered in the last scan.
        last_sync_at:   Timestamp of the last completed scan.
        created_at:     Timezone-aware creation timestamp.
        updated_at:     Timezone-aware last-modified timestamp.
        catalog_entries: Back-reference to EnterpriseMarketplaceCatalogEntry rows.

    Constraints:
        uq_enterprise_marketplace_sources_tenant_url: UNIQUE (tenant_id, repo_url)

    Indexes:
        idx_enterprise_ms_tenant_id:  (tenant_id)
        idx_enterprise_ms_tenant_url: (tenant_id, repo_url)
        idx_enterprise_ms_scan_status: (tenant_id, scan_status)
    """

    __tablename__ = "enterprise_marketplace_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique marketplace source identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    repo_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full GitHub repository URL, e.g. 'https://github.com/owner/repo'",
    )
    owner: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="GitHub repository owner (organisation or username)",
    )
    repo_name: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="GitHub repository name",
    )
    ref: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Git ref to scan, e.g. 'main', 'master', 'v1.2.0'",
    )
    scan_status: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Current scan state: 'pending', 'scanning', 'done', 'error'",
    )
    artifact_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of artifacts discovered in the most recent scan run",
    )
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timezone-aware timestamp of the last completed scan run",
    )
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

    catalog_entries: Mapped[List["EnterpriseMarketplaceCatalogEntry"]] = relationship(
        "EnterpriseMarketplaceCatalogEntry",
        back_populates="source",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "repo_url",
            name="uq_enterprise_marketplace_sources_tenant_url",
        ),
        Index("idx_enterprise_ms_tenant_id", "tenant_id"),
        Index("idx_enterprise_ms_tenant_url", "tenant_id", "repo_url"),
        Index("idx_enterprise_ms_scan_status", "tenant_id", "scan_status"),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseMarketplaceSource."""
        return (
            f"<EnterpriseMarketplaceSource("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"repo_url={self.repo_url!r}, "
            f"scan_status={self.scan_status!r}"
            f")>"
        )


# =============================================================================
# EnterpriseMarketplaceCatalogEntry model  (ENT2-2.4)
# =============================================================================


class EnterpriseMarketplaceCatalogEntry(EnterpriseBase):
    """Discovered artifact listing from a scanned marketplace source.

    Each row represents one artifact found during a scan of an
    ``EnterpriseMarketplaceSource``.  The ``search_vector`` column is a
    PostgreSQL ``TSVECTOR`` pre-computed from the artifact's name and path for
    full-text search.  It must be populated by a trigger or application-level
    update — it is not auto-computed by this model.

    Tenant isolation invariant:
        Every query MUST include ``WHERE tenant_id = ?``.

    Attributes:
        id:               UUID PK.
        tenant_id:        Tenant scope.
        source_id:        FK to enterprise_marketplace_sources.id (CASCADE).
        artifact_type:    Artifact type string, e.g. 'skill', 'command'.
        name:             Artifact name from the source repository.
        path:             Relative path within the source repository.
        upstream_url:     Full URL to the artifact in the source repository.
        status:           Catalog entry status, e.g. 'available', 'imported', 'deprecated'.
        confidence_score: Integer confidence score (0-100) from the scanner.
        detected_sha:     Git commit SHA at the time of detection.
        search_vector:    PostgreSQL TSVECTOR for full-text search.
        created_at:       Timezone-aware creation timestamp.
        updated_at:       Timezone-aware last-modified timestamp.
        source:           Many-to-one back-reference to EnterpriseMarketplaceSource.

    Indexes:
        idx_enterprise_mce_tenant_id:      (tenant_id)
        idx_enterprise_mce_source_id:      (source_id)
        idx_enterprise_mce_tenant_type:    (tenant_id, artifact_type)
        idx_enterprise_mce_search_vector:  GIN (search_vector) — full-text search
    """

    __tablename__ = "enterprise_marketplace_catalog_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Globally unique catalog entry identifier",
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "enterprise_marketplace_sources.id",
            ondelete="CASCADE",
            name="fk_enterprise_mce_source_id",
        ),
        nullable=False,
        comment="Parent marketplace source; cascade-deletes entries when source is removed",
    )
    artifact_type: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Artifact type string detected by the scanner, e.g. 'skill', 'command'",
    )
    name: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Artifact name as detected in the source repository",
    )
    path: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Relative path to the artifact within the source repository",
    )
    upstream_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Full URL to the artifact in the source repository for direct access",
    )
    status: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Catalog entry status: 'available', 'imported', 'deprecated', 'error'",
    )
    confidence_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Scanner confidence score 0-100; higher = more certain this is an artifact",
    )
    detected_sha: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Git commit SHA at the time of detection for provenance tracking",
    )
    search_vector: Mapped[Optional[Any]] = mapped_column(
        TSVECTOR,
        nullable=True,
        comment=(
            "PostgreSQL TSVECTOR for full-text search over name and path. "
            "Must be populated by application code or a DB trigger — not auto-computed."
        ),
    )
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

    source: Mapped["EnterpriseMarketplaceSource"] = relationship(
        "EnterpriseMarketplaceSource",
        back_populates="catalog_entries",
        lazy="joined",
    )

    __table_args__ = (
        Index("idx_enterprise_mce_tenant_id", "tenant_id"),
        Index("idx_enterprise_mce_source_id", "source_id"),
        Index("idx_enterprise_mce_tenant_type", "tenant_id", "artifact_type"),
        # GIN index for full-text search over search_vector
        # The Alembic migration (ent_008) must create this with CONCURRENTLY:
        #   op.create_index(
        #       "idx_enterprise_mce_search_vector",
        #       "enterprise_marketplace_catalog_entries",
        #       ["search_vector"],
        #       postgresql_using="gin",
        #       postgresql_concurrently=True,
        #   )
        Index(
            "idx_enterprise_mce_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        """Return unambiguous string representation of EnterpriseMarketplaceCatalogEntry."""
        return (
            f"<EnterpriseMarketplaceCatalogEntry("
            f"id={self.id!r}, "
            f"tenant_id={self.tenant_id!r}, "
            f"source_id={self.source_id!r}, "
            f"name={self.name!r}, "
            f"artifact_type={self.artifact_type!r}"
            f")>"
        )
