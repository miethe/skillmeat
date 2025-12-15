"""Add project_templates and template_entities tables

Revision ID: 20251215_1200_add_project_templates
Revises: 20251214_0900_add_context_entity_columns
Create Date: 2025-12-15 12:00:00.000000

This migration creates the database schema for Project Templates,
enabling reusable artifact deployment patterns with ordering and
configuration management.

Tables Created:
- project_templates: Reusable project templates with artifact deployment patterns
- template_entities: M2M association ProjectTemplate <-> Artifact with deploy order

Key Features:
- Cascade delete: Deleting a template removes its entity associations
- Deploy order: Artifacts within templates have explicit deployment ordering
- Required flag: Mark artifacts as required vs optional in templates
- Default config: Templates can specify a default project config artifact
- Name uniqueness: Template names must be unique across all collections

Schema Version: 1.2.0
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251215_1200_add_project_templates"
down_revision: Union[str, None] = "20251214_0900_add_context_entity_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create project_templates and template_entities tables.

    Creates the complete schema for project template management:

    1. project_templates - Reusable templates with artifact deployment patterns
    2. template_entities - Links templates to artifacts with deployment metadata

    All tables use TEXT/VARCHAR for IDs (UUID hex format) and include
    proper foreign key constraints with appropriate CASCADE/SET NULL actions
    for data integrity.
    """
    # ==========================================================================
    # Project Templates Table
    # ==========================================================================
    # Reusable templates defining standardized project setups
    op.create_table(
        "project_templates",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("collection_id", sa.Text(), nullable=False),
        sa.Column("default_project_config_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collections.id"],
            name="fk_project_templates_collection_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["default_project_config_id"],
            ["artifacts.id"],
            name="fk_project_templates_default_config",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "length(name) > 0 AND length(name) <= 255",
            name="check_template_name_length",
        ),
    )

    # Project templates indexes
    op.create_index(
        "idx_templates_name",
        "project_templates",
        ["name"],
        unique=True,
    )
    op.create_index(
        "idx_templates_collection_id",
        "project_templates",
        ["collection_id"],
    )
    op.create_index(
        "idx_templates_created_at",
        "project_templates",
        ["created_at"],
    )

    # ==========================================================================
    # Template Entities Association Table
    # ==========================================================================
    # Many-to-many: ProjectTemplate <-> Artifact with deployment metadata
    op.create_table(
        "template_entities",
        sa.Column("template_id", sa.Text(), nullable=False),
        sa.Column("artifact_id", sa.Text(), nullable=False),
        sa.Column("deploy_order", sa.Integer(), nullable=False),
        sa.Column(
            "required",
            sa.Boolean(),
            nullable=False,
            server_default="1",
        ),
        sa.PrimaryKeyConstraint("template_id", "artifact_id"),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["project_templates.id"],
            name="fk_template_entities_template_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["artifacts.id"],
            name="fk_template_entities_artifact_id",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "deploy_order >= 0",
            name="check_deploy_order",
        ),
    )

    # Template entities indexes
    op.create_index(
        "idx_template_entities_template_id",
        "template_entities",
        ["template_id"],
    )
    op.create_index(
        "idx_template_entities_artifact_id",
        "template_entities",
        ["artifact_id"],
    )
    op.create_index(
        "idx_template_entities_deploy_order",
        "template_entities",
        ["template_id", "deploy_order"],
    )

    # ==========================================================================
    # Triggers for automatic updated_at maintenance
    # ==========================================================================

    # Project templates updated_at trigger
    op.execute(
        """
        CREATE TRIGGER project_templates_updated_at
        AFTER UPDATE ON project_templates
        FOR EACH ROW
        BEGIN
            UPDATE project_templates SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
        """
    )

    # ==========================================================================
    # Update schema version
    # ==========================================================================
    op.execute(
        """
        UPDATE cache_metadata SET value = '1.2.0'
        WHERE key = 'schema_version'
        """
    )


def downgrade() -> None:
    """Remove project_templates and template_entities tables.

    This reverts the migration by dropping all created triggers and tables.
    Tables are dropped in reverse dependency order:

    1. template_entities (depends on project_templates and artifacts)
    2. project_templates (depends on collections and artifacts)

    WARNING: This is a destructive operation. All project template
    data will be permanently lost.
    """
    # Drop trigger first (SQLite requires explicit trigger drops)
    op.execute("DROP TRIGGER IF EXISTS project_templates_updated_at")

    # Drop tables in reverse dependency order
    # Note: Indexes are automatically dropped when tables are dropped
    op.drop_table("template_entities")
    op.drop_table("project_templates")

    # Revert schema version
    op.execute(
        """
        UPDATE cache_metadata SET value = '1.1.0'
        WHERE key = 'schema_version'
        """
    )
