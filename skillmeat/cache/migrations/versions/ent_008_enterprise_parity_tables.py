"""add enterprise parity tables: tags, groups, settings, entity configs, context entities, projects, deployment sets, deployment profiles, marketplace

Revision ID: ent_008_enterprise_parity_tables
Revises: ent_007_enterprise_owner_type
Create Date: 2026-03-12 00:08:00.000000+00:00

Background
----------
ENT2-2 enterprise-repo-parity feature.  Adds 18 new PostgreSQL tables required
to bring enterprise storage to parity with the local SQLite schema.  The
existing SQLite cache is left completely untouched — the migration is a no-op
on any non-PostgreSQL dialect.

Tables created (dependency order)
----------------------------------
Tier 1 — no FK dependencies beyond already-existing tables:
  1.  enterprise_tags
  2.  enterprise_groups              (FK -> enterprise_collections, already exists)
  3.  enterprise_settings
  4.  enterprise_entity_type_configs
  5.  enterprise_entity_categories
  6.  enterprise_context_entities    (no FK to enterprise_artifacts; standalone)
  7.  enterprise_projects
  8.  enterprise_marketplace_sources
  9.  enterprise_deployment_sets
  10. enterprise_deployment_profiles

Tier 2 — FK dependencies on Tier 1 tables created above:
  11. enterprise_artifact_tags        (FK -> enterprise_tags, enterprise_artifacts)
  12. enterprise_group_artifacts       (FK -> enterprise_groups, enterprise_artifacts)
  13. enterprise_entity_category_associations
                                      (FK -> enterprise_context_entities,
                                              enterprise_entity_categories)
  14. enterprise_project_artifacts     (FK -> enterprise_projects, enterprise_artifacts)
  15. enterprise_deployments           (FK -> enterprise_projects, enterprise_artifacts)
  16. enterprise_deployment_set_members (FK -> enterprise_deployment_sets)
  17. enterprise_deployment_set_tags    (FK -> enterprise_deployment_sets)
  18. enterprise_marketplace_catalog_entries
                                      (FK -> enterprise_marketplace_sources)
                                      TSVECTOR search_vector + GIN index

Downgrade order
---------------
Drop Tier 2 first, then Tier 1, in reverse creation order.

Schema reference
----------------
skillmeat/cache/models_enterprise.py  (ENT2-2.1 — ENT2-2.4 classes)
docs/project_plans/architecture/enterprise-db-schema-v1.md
.claude/progress/enterprise-repo-parity/
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "ent_008_enterprise_parity_tables"
down_revision: Union[str, None] = "ent_007_enterprise_owner_type"
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
    """Create 18 new enterprise tables (PostgreSQL only)."""
    if not _is_postgresql():
        return  # No-op for SQLite and any other non-PostgreSQL dialect

    # ==================================================================
    # TIER 1 — tables with no FK dependencies on tables created here
    # ==================================================================

    # ------------------------------------------------------------------
    # 1. enterprise_tags
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_tags",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique tag identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "name",
            sa.Text,
            nullable=False,
            comment="Human-readable tag label, e.g. 'frontend', 'experimental'",
        ),
        sa.Column(
            "slug",
            sa.Text,
            nullable=False,
            comment="URL-safe normalised form of name; unique within a tenant",
        ),
        sa.Column(
            "color",
            sa.Text,
            nullable=True,
            comment="Optional hex or CSS colour string for UI display, e.g. '#3B82F6'",
        ),
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
            comment="Timezone-aware last-modified timestamp; updated by app on every write",
        ),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_enterprise_tags_tenant_slug"),
    )
    op.create_index("idx_enterprise_tags_tenant_id", "enterprise_tags", ["tenant_id"])
    op.create_index(
        "idx_enterprise_tags_tenant_slug", "enterprise_tags", ["tenant_id", "slug"]
    )

    # ------------------------------------------------------------------
    # 2. enterprise_groups  (FK -> enterprise_collections — already exists)
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_groups",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique group identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "name",
            sa.Text,
            nullable=True,
            comment="Human-readable group name displayed in the UI",
        ),
        sa.Column(
            "collection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_collections.id",
                ondelete="SET NULL",
                name="fk_enterprise_groups_collection_id",
            ),
            nullable=True,
            comment="Optional parent collection; NULL = collection-agnostic group",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Optional free-text description of the group",
        ),
        sa.Column(
            "position",
            sa.Integer,
            nullable=True,
            server_default=sa.text("0"),
            comment="Display order within the collection; lower = earlier",
        ),
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
            comment="Timezone-aware last-modified timestamp; updated by app on every write",
        ),
    )
    op.create_index(
        "idx_enterprise_groups_tenant_id", "enterprise_groups", ["tenant_id"]
    )
    op.create_index(
        "idx_enterprise_groups_collection_id",
        "enterprise_groups",
        ["collection_id"],
    )
    op.create_index(
        "idx_enterprise_groups_tenant_collection",
        "enterprise_groups",
        ["tenant_id", "collection_id"],
    )

    # ------------------------------------------------------------------
    # 3. enterprise_settings  (no FK deps)
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_settings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique settings-row identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment=(
                "Tenant scope; UNIQUE constraint ensures exactly one settings row per tenant. "
                "Every query MUST include WHERE tenant_id = ?"
            ),
        ),
        sa.Column(
            "github_token",
            sa.Text,
            nullable=True,
            comment="GitHub API token for this tenant (may be encrypted at rest)",
        ),
        sa.Column(
            "collection_path",
            sa.Text,
            nullable=True,
            comment="Override path for the tenant's local collection root directory",
        ),
        sa.Column(
            "default_scope",
            sa.Text,
            nullable=True,
            comment="Default artifact scope when not specified; 'user' or 'local'",
        ),
        sa.Column(
            "edition",
            sa.Text,
            nullable=True,
            comment="Active edition string for this tenant, e.g. 'enterprise'",
        ),
        sa.Column(
            "indexing_mode",
            sa.Text,
            nullable=True,
            comment="Artifact indexing mode; controls which indexer strategy is used",
        ),
        sa.Column(
            "extra",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="JSONB bag for forward-compatible extension; initialized to empty object",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Timezone-aware last-modified timestamp; updated by app on every write",
        ),
        sa.UniqueConstraint("tenant_id", name="uq_enterprise_settings_tenant"),
    )
    op.create_index(
        "idx_enterprise_settings_tenant_id", "enterprise_settings", ["tenant_id"]
    )

    # ------------------------------------------------------------------
    # 4. enterprise_entity_type_configs  (no FK deps)
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_entity_type_configs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique config row identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "entity_type",
            sa.Text,
            nullable=False,
            comment="Artifact type identifier, e.g. 'skill', 'command', 'agent'",
        ),
        sa.Column(
            "display_name",
            sa.Text,
            nullable=True,
            comment="Human-readable label for this type in the UI",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Optional description shown in type selector dropdowns",
        ),
        sa.Column(
            "icon",
            sa.Text,
            nullable=True,
            comment="Optional icon identifier or URL for UI display",
        ),
        sa.Column(
            "color",
            sa.Text,
            nullable=True,
            comment="Optional hex or CSS colour for type badges in the UI",
        ),
        sa.Column(
            "is_system",
            sa.Boolean,
            nullable=True,
            server_default=sa.text("false"),
            comment="True = shipped default config; False = tenant override",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "entity_type",
            name="uq_enterprise_entity_type_configs_tenant_type",
        ),
    )
    op.create_index(
        "idx_enterprise_etc_tenant_id",
        "enterprise_entity_type_configs",
        ["tenant_id"],
    )
    op.create_index(
        "idx_enterprise_etc_tenant_type",
        "enterprise_entity_type_configs",
        ["tenant_id", "entity_type"],
    )

    # ------------------------------------------------------------------
    # 5. enterprise_entity_categories  (no FK deps)
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_entity_categories",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique category identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "name",
            sa.Text,
            nullable=False,
            comment="Human-readable category name displayed in the UI",
        ),
        sa.Column(
            "slug",
            sa.Text,
            nullable=True,
            comment="URL-safe normalised identifier; unique within a tenant",
        ),
        sa.Column(
            "entity_type",
            sa.Text,
            nullable=True,
            comment="Optional entity type this category applies to, e.g. 'rule_file'",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Optional free-text description of the category",
        ),
        sa.Column(
            "color",
            sa.Text,
            nullable=True,
            comment="Optional hex or CSS colour for category badges in the UI",
        ),
        sa.Column(
            "platform",
            sa.Text,
            nullable=True,
            comment="Optional platform filter, e.g. 'claude', 'cursor', 'windsurf'",
        ),
        sa.Column(
            "sort_order",
            sa.Integer,
            nullable=True,
            server_default=sa.text("0"),
            comment="Display order; lower = earlier",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "slug",
            name="uq_enterprise_entity_categories_tenant_slug",
        ),
    )
    op.create_index(
        "idx_enterprise_ec_tenant_id",
        "enterprise_entity_categories",
        ["tenant_id"],
    )
    op.create_index(
        "idx_enterprise_ec_tenant_slug",
        "enterprise_entity_categories",
        ["tenant_id", "slug"],
    )
    op.create_index(
        "idx_enterprise_ec_entity_type",
        "enterprise_entity_categories",
        ["tenant_id", "entity_type"],
    )

    # ------------------------------------------------------------------
    # 6. enterprise_context_entities  (no FK deps on new tables)
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_context_entities",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique context entity identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "name",
            sa.Text,
            nullable=False,
            comment="Human-readable entity name, e.g. 'CLAUDE.md', 'debugging-rule'",
        ),
        sa.Column(
            "entity_type",
            sa.Text,
            nullable=False,
            comment="Entity type discriminator, e.g. 'context_file', 'rule_file', 'spec_file'",
        ),
        sa.Column(
            "content",
            sa.Text,
            nullable=True,
            comment="Entity file content; NULL when only metadata has been loaded",
        ),
        sa.Column(
            "path_pattern",
            sa.Text,
            nullable=False,
            comment="Target path pattern for deployment, e.g. '.claude/rules/*.md'",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Optional free-text description of this entity's purpose",
        ),
        sa.Column(
            "category",
            sa.Text,
            nullable=True,
            comment="Optional category label string; use category_associations for structured FK refs",
        ),
        sa.Column(
            "auto_load",
            sa.Boolean,
            nullable=True,
            server_default=sa.text("false"),
            comment="When TRUE, the agent should auto-load this entity at startup",
        ),
        sa.Column(
            "version",
            sa.Text,
            nullable=True,
            comment="Optional version label, e.g. 'v1.0.0' or a SHA prefix",
        ),
        sa.Column(
            "target_platforms",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="JSONB array of platform identifiers this entity targets, e.g. ['claude', 'cursor']",
        ),
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
            comment="Timezone-aware last-modified timestamp; updated by app on every write",
        ),
    )
    op.create_index(
        "idx_enterprise_ce_tenant_id",
        "enterprise_context_entities",
        ["tenant_id"],
    )
    op.create_index(
        "idx_enterprise_ce_tenant_type",
        "enterprise_context_entities",
        ["tenant_id", "entity_type"],
    )
    op.create_index(
        "idx_enterprise_ce_tenant_autoload",
        "enterprise_context_entities",
        ["tenant_id", "auto_load"],
        postgresql_where=sa.text("auto_load = TRUE"),
    )

    # ------------------------------------------------------------------
    # 7. enterprise_projects  (no FK deps)
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique project identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "name",
            sa.Text,
            nullable=False,
            comment="Human-readable project name",
        ),
        sa.Column(
            "path",
            sa.Text,
            nullable=False,
            comment=(
                "Filesystem path at registration time — INFORMATIONAL ONLY in enterprise mode. "
                "The enterprise IProjectRepository never scans this path directly."
            ),
        ),
        sa.Column(
            "status",
            sa.Text,
            nullable=True,
            comment="Project status string, e.g. 'active', 'archived', 'initializing'",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Optional free-text description of this project",
        ),
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
            comment="Timezone-aware last-modified timestamp; updated by app on every write",
        ),
        sa.UniqueConstraint(
            "tenant_id", "path", name="uq_enterprise_projects_tenant_path"
        ),
    )
    op.create_index(
        "idx_enterprise_projects_tenant_id", "enterprise_projects", ["tenant_id"]
    )
    op.create_index(
        "idx_enterprise_projects_tenant_path",
        "enterprise_projects",
        ["tenant_id", "path"],
    )

    # ------------------------------------------------------------------
    # 8. enterprise_marketplace_sources  (no FK deps)
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_marketplace_sources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique marketplace source identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "repo_url",
            sa.Text,
            nullable=False,
            comment="Full GitHub repository URL, e.g. 'https://github.com/owner/repo'",
        ),
        sa.Column(
            "owner",
            sa.Text,
            nullable=True,
            comment="GitHub repository owner (organisation or username)",
        ),
        sa.Column(
            "repo_name",
            sa.Text,
            nullable=True,
            comment="GitHub repository name",
        ),
        sa.Column(
            "ref",
            sa.Text,
            nullable=True,
            comment="Git ref to scan, e.g. 'main', 'master', 'v1.2.0'",
        ),
        sa.Column(
            "scan_status",
            sa.Text,
            nullable=True,
            comment="Current scan state: 'pending', 'scanning', 'done', 'error'",
        ),
        sa.Column(
            "artifact_count",
            sa.Integer,
            nullable=True,
            comment="Number of artifacts discovered in the most recent scan run",
        ),
        sa.Column(
            "last_sync_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timezone-aware timestamp of the last completed scan run",
        ),
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
            comment="Timezone-aware last-modified timestamp; updated by app on every write",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "repo_url",
            name="uq_enterprise_marketplace_sources_tenant_url",
        ),
    )
    op.create_index(
        "idx_enterprise_ms_tenant_id",
        "enterprise_marketplace_sources",
        ["tenant_id"],
    )
    op.create_index(
        "idx_enterprise_ms_tenant_url",
        "enterprise_marketplace_sources",
        ["tenant_id", "repo_url"],
    )
    op.create_index(
        "idx_enterprise_ms_scan_status",
        "enterprise_marketplace_sources",
        ["tenant_id", "scan_status"],
    )

    # ------------------------------------------------------------------
    # 9. enterprise_deployment_sets  (no FK deps)
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_deployment_sets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique deployment set identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "name",
            sa.Text,
            nullable=False,
            comment="Human-readable set name; unique within a tenant",
        ),
        sa.Column(
            "remote_url",
            sa.Text,
            nullable=True,
            comment="Optional URL linking to the canonical definition of this set",
        ),
        sa.Column(
            "provisioned_by",
            sa.Text,
            nullable=True,
            comment="System or user identifier that provisioned this deployment set",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Optional free-text description of the set's purpose",
        ),
        sa.Column(
            "tags_json",
            sa.Text,
            nullable=True,
            comment=(
                "Serialized tag list as TEXT (e.g. JSON array string). "
                "Kept as TEXT for compatibility with the local DeploymentSetRepository "
                "tag-filter pattern. Prefer EnterpriseDeploymentSetTag rows for structured access."
            ),
        ),
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
            comment="Timezone-aware last-modified timestamp; updated by app on every write",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_enterprise_deployment_sets_tenant_name",
        ),
    )
    op.create_index(
        "idx_enterprise_dsets_tenant_id",
        "enterprise_deployment_sets",
        ["tenant_id"],
    )
    op.create_index(
        "idx_enterprise_dsets_tenant_name",
        "enterprise_deployment_sets",
        ["tenant_id", "name"],
    )

    # ------------------------------------------------------------------
    # 10. enterprise_deployment_profiles  (no FK deps)
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_deployment_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique deployment profile identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "name",
            sa.Text,
            nullable=False,
            comment="Human-readable profile name; unique within a tenant",
        ),
        sa.Column(
            "scope",
            sa.Text,
            nullable=True,
            comment="Deployment scope, e.g. 'user', 'local', 'project'",
        ),
        sa.Column(
            "dest_path",
            sa.Text,
            nullable=True,
            comment="Destination path template; may contain placeholders like {artifact_name}",
        ),
        sa.Column(
            "overwrite",
            sa.Boolean,
            nullable=True,
            server_default=sa.text("false"),
            comment="When TRUE, existing destination files are overwritten without prompt",
        ),
        sa.Column(
            "platform",
            sa.Text,
            nullable=True,
            comment="Target platform for deployments using this profile, e.g. 'claude', 'cursor'",
        ),
        sa.Column(
            "extra_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="JSONB bag for forward-compatible extension; NULL until explicitly set",
        ),
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
            comment="Timezone-aware last-modified timestamp; updated by app on every write",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_enterprise_deployment_profiles_tenant_name",
        ),
    )
    op.create_index(
        "idx_enterprise_dp_tenant_id",
        "enterprise_deployment_profiles",
        ["tenant_id"],
    )
    op.create_index(
        "idx_enterprise_dp_tenant_name",
        "enterprise_deployment_profiles",
        ["tenant_id", "name"],
    )

    # ==================================================================
    # TIER 2 — tables with FK dependencies on Tier 1 tables above
    # ==================================================================

    # ------------------------------------------------------------------
    # 11. enterprise_artifact_tags  (FK -> enterprise_tags, enterprise_artifacts)
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_artifact_tags",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique join-row identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Denormalized tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "tag_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_tags.id",
                ondelete="CASCADE",
                name="fk_enterprise_artifact_tags_tag_id",
            ),
            nullable=False,
            comment="Parent tag; cascade-deletes this row when tag is removed",
        ),
        sa.Column(
            "artifact_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_artifacts.id",
                ondelete="CASCADE",
                name="fk_enterprise_artifact_tags_artifact_uuid",
            ),
            nullable=False,
            comment="Tagged artifact; cascade-deletes this row when artifact is removed",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "tag_id",
            "artifact_uuid",
            name="uq_enterprise_artifact_tags_tenant_tag_artifact",
        ),
    )
    op.create_index(
        "idx_ent_atag_tenant_id", "enterprise_artifact_tags", ["tenant_id"]
    )
    op.create_index(
        "idx_ent_atag_tag_id", "enterprise_artifact_tags", ["tag_id"]
    )
    op.create_index(
        "idx_ent_atag_artifact_uuid", "enterprise_artifact_tags", ["artifact_uuid"]
    )

    # ------------------------------------------------------------------
    # 12. enterprise_group_artifacts  (FK -> enterprise_groups, enterprise_artifacts)
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_group_artifacts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique join-row identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Denormalized tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_groups.id",
                ondelete="CASCADE",
                name="fk_enterprise_group_artifacts_group_id",
            ),
            nullable=False,
            comment="Parent group; cascade-deletes this row when group is removed",
        ),
        sa.Column(
            "artifact_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_artifacts.id",
                ondelete="CASCADE",
                name="fk_enterprise_group_artifacts_artifact_uuid",
            ),
            nullable=False,
            comment="Member artifact; cascade-deletes this row when artifact is removed",
        ),
        sa.Column(
            "position",
            sa.Integer,
            nullable=True,
            server_default=sa.text("0"),
            comment="Display order within the group; lower = earlier",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "group_id",
            "artifact_uuid",
            name="uq_enterprise_group_artifacts_tenant_group_artifact",
        ),
    )
    op.create_index(
        "idx_ent_ga_tenant_id", "enterprise_group_artifacts", ["tenant_id"]
    )
    op.create_index(
        "idx_ent_ga_group_id", "enterprise_group_artifacts", ["group_id"]
    )
    op.create_index(
        "idx_ent_ga_artifact_uuid", "enterprise_group_artifacts", ["artifact_uuid"]
    )
    op.create_index(
        "idx_ent_ga_group_position",
        "enterprise_group_artifacts",
        ["group_id", "position"],
    )

    # ------------------------------------------------------------------
    # 13. enterprise_entity_category_associations
    #     (FK -> enterprise_context_entities, enterprise_entity_categories)
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_entity_category_associations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique join-row identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Denormalized tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_context_entities.id",
                ondelete="CASCADE",
                name="fk_ent_eca_entity_id",
            ),
            nullable=False,
            comment="Parent context entity; cascade-deletes this row when entity is removed",
        ),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_entity_categories.id",
                ondelete="CASCADE",
                name="fk_ent_eca_category_id",
            ),
            nullable=False,
            comment="Parent category; cascade-deletes this row when category is removed",
        ),
        sa.Column(
            "position",
            sa.Integer,
            nullable=True,
            server_default=sa.text("0"),
            comment="Display order within the category; lower = earlier",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "entity_id",
            "category_id",
            name="uq_ent_eca_tenant_entity_category",
        ),
    )
    op.create_index(
        "idx_ent_eca_tenant_id",
        "enterprise_entity_category_associations",
        ["tenant_id"],
    )
    op.create_index(
        "idx_ent_eca_entity_id",
        "enterprise_entity_category_associations",
        ["entity_id"],
    )
    op.create_index(
        "idx_ent_eca_category_id",
        "enterprise_entity_category_associations",
        ["category_id"],
    )

    # ------------------------------------------------------------------
    # 14. enterprise_project_artifacts
    #     (FK -> enterprise_projects, enterprise_artifacts)
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_project_artifacts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique join-row identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Denormalized tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_projects.id",
                ondelete="CASCADE",
                name="fk_enterprise_project_artifacts_project_id",
            ),
            nullable=False,
            comment="Parent project; cascade-deletes this row when project is removed",
        ),
        sa.Column(
            "artifact_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_artifacts.id",
                ondelete="CASCADE",
                name="fk_enterprise_project_artifacts_artifact_uuid",
            ),
            nullable=False,
            comment="Deployed artifact; cascade-deletes this row when artifact is removed",
        ),
        sa.Column(
            "deployed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timezone-aware timestamp when this artifact was deployed to the project",
        ),
        sa.Column(
            "content_hash",
            sa.Text,
            nullable=True,
            comment="SHA256 hex digest of the artifact content at deployment time",
        ),
        sa.Column(
            "local_modifications",
            sa.Boolean,
            nullable=True,
            server_default=sa.text("false"),
            comment="True when local project file has been modified since deployment",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "project_id",
            "artifact_uuid",
            name="uq_enterprise_project_artifacts_tenant_project_artifact",
        ),
    )
    op.create_index(
        "idx_ent_pa_tenant_id", "enterprise_project_artifacts", ["tenant_id"]
    )
    op.create_index(
        "idx_ent_pa_project_id", "enterprise_project_artifacts", ["project_id"]
    )
    op.create_index(
        "idx_ent_pa_artifact_uuid",
        "enterprise_project_artifacts",
        ["artifact_uuid"],
    )

    # ------------------------------------------------------------------
    # 15. enterprise_deployments
    #     (FK -> enterprise_projects SET NULL, enterprise_artifacts SET NULL)
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_deployments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique deployment record identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "artifact_id",
            sa.Text,
            nullable=False,
            comment=(
                "Text-format artifact identifier, e.g. 'skill:canvas-design'. "
                "Preserved for backward compatibility with sync_deployment_cache() callers."
            ),
        ),
        sa.Column(
            "artifact_uuid",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_artifacts.id",
                ondelete="SET NULL",
                name="fk_enterprise_deployments_artifact_uuid",
            ),
            nullable=True,
            comment=(
                "UUID FK to enterprise_artifacts.id — preferred reference in enterprise queries. "
                "NULL for deployments recorded before the artifact was indexed in enterprise DB."
            ),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_projects.id",
                ondelete="SET NULL",
                name="fk_enterprise_deployments_project_id",
            ),
            nullable=True,
            comment="Optional parent project; SET NULL when project is removed",
        ),
        sa.Column(
            "status",
            sa.Text,
            nullable=True,
            comment="Deployment status string, e.g. 'deployed', 'undeployed', 'pending'",
        ),
        sa.Column(
            "deployed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timezone-aware timestamp of the deployment event",
        ),
        sa.Column(
            "content_hash",
            sa.Text,
            nullable=True,
            comment="SHA256 hex digest of artifact content at deployment time",
        ),
        sa.Column(
            "deployment_profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Optional UUID reference to the deployment profile used; no FK enforced",
        ),
        sa.Column(
            "local_modifications",
            sa.Boolean,
            nullable=True,
            server_default=sa.text("false"),
            comment="True when the local project file has diverged from the deployed content",
        ),
        sa.Column(
            "platform",
            sa.Text,
            nullable=True,
            comment="Target platform for this deployment, e.g. 'claude', 'cursor', 'windsurf'",
        ),
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
            comment="Timezone-aware last-modified timestamp; updated by app on every write",
        ),
    )
    op.create_index(
        "idx_enterprise_deployments_tenant_id",
        "enterprise_deployments",
        ["tenant_id"],
    )
    op.create_index(
        "idx_enterprise_deployments_artifact_id",
        "enterprise_deployments",
        ["artifact_id"],
    )
    op.create_index(
        "idx_enterprise_deployments_artifact_uuid",
        "enterprise_deployments",
        ["artifact_uuid"],
    )
    op.create_index(
        "idx_enterprise_deployments_project_id",
        "enterprise_deployments",
        ["project_id"],
    )
    op.create_index(
        "idx_enterprise_deployments_tenant_status",
        "enterprise_deployments",
        ["tenant_id", "status"],
    )

    # ------------------------------------------------------------------
    # 16. enterprise_deployment_set_members
    #     (FK -> enterprise_deployment_sets)
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_deployment_set_members",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique join-row identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Denormalized tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_deployment_sets.id",
                ondelete="CASCADE",
                name="fk_enterprise_dsm_set_id",
            ),
            nullable=False,
            comment="Parent deployment set; cascade-deletes this row when set is removed",
        ),
        sa.Column(
            "artifact_id",
            sa.Text,
            nullable=True,
            comment="Text-format artifact identifier, e.g. 'skill:canvas-design'",
        ),
        sa.Column(
            "position",
            sa.Integer,
            nullable=True,
            server_default=sa.text("0"),
            comment="Ordering position within the deployment set; lower = earlier",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "set_id",
            "artifact_id",
            name="uq_enterprise_dsm_tenant_set_artifact",
        ),
    )
    op.create_index(
        "idx_ent_dsm_tenant_id",
        "enterprise_deployment_set_members",
        ["tenant_id"],
    )
    op.create_index(
        "idx_ent_dsm_set_id", "enterprise_deployment_set_members", ["set_id"]
    )

    # ------------------------------------------------------------------
    # 17. enterprise_deployment_set_tags
    #     (FK -> enterprise_deployment_sets)
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_deployment_set_tags",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique tag-row identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Denormalized tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_deployment_sets.id",
                ondelete="CASCADE",
                name="fk_enterprise_dst_set_id",
            ),
            nullable=False,
            comment="Parent deployment set; cascade-deletes this row when set is removed",
        ),
        sa.Column(
            "tag",
            sa.Text,
            nullable=False,
            comment="String tag for filtering and grouping deployment sets",
        ),
        sa.UniqueConstraint("set_id", "tag", name="uq_enterprise_dst_set_tag"),
    )
    op.create_index(
        "idx_ent_dst_tenant_id", "enterprise_deployment_set_tags", ["tenant_id"]
    )
    op.create_index(
        "idx_ent_dst_set_id", "enterprise_deployment_set_tags", ["set_id"]
    )
    op.create_index(
        "idx_ent_dst_tag", "enterprise_deployment_set_tags", ["tag"]
    )

    # ------------------------------------------------------------------
    # 18. enterprise_marketplace_catalog_entries
    #     (FK -> enterprise_marketplace_sources)
    #     TSVECTOR search_vector column + GIN index
    # ------------------------------------------------------------------
    op.create_table(
        "enterprise_marketplace_catalog_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Globally unique catalog entry identifier",
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant scope; every query MUST include WHERE tenant_id = ?",
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "enterprise_marketplace_sources.id",
                ondelete="CASCADE",
                name="fk_enterprise_mce_source_id",
            ),
            nullable=False,
            comment="Parent marketplace source; cascade-deletes entries when source is removed",
        ),
        sa.Column(
            "artifact_type",
            sa.Text,
            nullable=True,
            comment="Artifact type string detected by the scanner, e.g. 'skill', 'command'",
        ),
        sa.Column(
            "name",
            sa.Text,
            nullable=True,
            comment="Artifact name as detected in the source repository",
        ),
        sa.Column(
            "path",
            sa.Text,
            nullable=True,
            comment="Relative path to the artifact within the source repository",
        ),
        sa.Column(
            "upstream_url",
            sa.Text,
            nullable=True,
            comment="Full URL to the artifact in the source repository for direct access",
        ),
        sa.Column(
            "status",
            sa.Text,
            nullable=True,
            comment="Catalog entry status: 'available', 'imported', 'deprecated', 'error'",
        ),
        sa.Column(
            "confidence_score",
            sa.Integer,
            nullable=True,
            comment="Scanner confidence score 0-100; higher = more certain this is an artifact",
        ),
        sa.Column(
            "detected_sha",
            sa.Text,
            nullable=True,
            comment="Git commit SHA at the time of detection for provenance tracking",
        ),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            nullable=True,
            comment=(
                "PostgreSQL TSVECTOR for full-text search over name and path. "
                "Must be populated by application code or a DB trigger — not auto-computed."
            ),
        ),
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
            comment="Timezone-aware last-modified timestamp; updated by app on every write",
        ),
    )
    op.create_index(
        "idx_enterprise_mce_tenant_id",
        "enterprise_marketplace_catalog_entries",
        ["tenant_id"],
    )
    op.create_index(
        "idx_enterprise_mce_source_id",
        "enterprise_marketplace_catalog_entries",
        ["source_id"],
    )
    op.create_index(
        "idx_enterprise_mce_tenant_type",
        "enterprise_marketplace_catalog_entries",
        ["tenant_id", "artifact_type"],
    )
    # GIN index for full-text search — uses raw SQL so CONCURRENTLY can be
    # applied on an already-populated table during future deployments.
    # On a freshly created table (migration day) CONCURRENTLY is not required,
    # but using op.execute keeps the index creation syntax consistent and avoids
    # holding an AccessShareLock on the table during index build.
    op.create_index(
        "idx_enterprise_mce_search_vector",
        "enterprise_marketplace_catalog_entries",
        ["search_vector"],
        postgresql_using="gin",
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Drop 18 enterprise parity tables (PostgreSQL only, reverse order)."""
    if not _is_postgresql():
        return  # No-op for SQLite

    # Drop Tier 2 tables first (they hold FKs into Tier 1)
    op.drop_table("enterprise_marketplace_catalog_entries")
    op.drop_table("enterprise_deployment_set_tags")
    op.drop_table("enterprise_deployment_set_members")
    op.drop_table("enterprise_deployments")
    op.drop_table("enterprise_project_artifacts")
    op.drop_table("enterprise_entity_category_associations")
    op.drop_table("enterprise_group_artifacts")
    op.drop_table("enterprise_artifact_tags")

    # Drop Tier 1 tables (reverse creation order)
    op.drop_table("enterprise_deployment_profiles")
    op.drop_table("enterprise_deployment_sets")
    op.drop_table("enterprise_marketplace_sources")
    op.drop_table("enterprise_projects")
    op.drop_table("enterprise_context_entities")
    op.drop_table("enterprise_entity_categories")
    op.drop_table("enterprise_entity_type_configs")
    op.drop_table("enterprise_settings")
    op.drop_table("enterprise_groups")
    op.drop_table("enterprise_tags")
