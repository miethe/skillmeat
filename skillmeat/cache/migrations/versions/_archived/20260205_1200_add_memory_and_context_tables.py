"""Add memory_items, context_modules, and module_memory_items tables

Revision ID: 20260205_1200_add_memory_and_context_tables
Revises: 20260202_1100_add_deployments_json_to_collection_artifacts
Create Date: 2026-02-05 12:00:00.000000+00:00

This migration adds the database foundation for the Memory & Context Intelligence
System. Three tables are created:

- memory_items: Stores project-scoped memory items (decisions, constraints, gotchas,
  style_rules, learnings) with confidence scores, provenance tracking, and TTL policies.
- context_modules: Named groupings of memory items with selector criteria for
  automatic assembly of contextual knowledge.
- module_memory_items: Join table linking context modules to memory items with ordering.

Part of the memory-context-system-v1 feature.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260205_1200_add_memory_and_context_tables"
down_revision: Union[str, None] = (
    "20260202_1100_add_deployments_json_to_collection_artifacts"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create memory_items, context_modules, and module_memory_items tables.

    Creates the three core tables for the Memory & Context Intelligence System:

    1. memory_items - Project-scoped memory items with confidence scoring,
       status lifecycle, provenance tracking, and TTL policies.
    2. context_modules - Named groupings with selector criteria for assembling
       contextual knowledge from memory items.
    3. module_memory_items - Association table linking modules to memory items
       with explicit ordering.

    Indexes are created for common query patterns: project+status filtering,
    project+type filtering, and chronological ordering.
    """
    # 1. Create memory_items table
    op.create_table(
        "memory_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="candidate"),
        sa.Column("provenance_json", sa.Text(), nullable=True),
        sa.Column("anchors_json", sa.Text(), nullable=True),
        sa.Column("ttl_policy_json", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(), nullable=False, unique=True),
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.Column("deprecated_at", sa.String(), nullable=True),
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_memory_items_confidence",
        ),
        sa.CheckConstraint(
            "type IN ('decision', 'constraint', 'gotcha', 'style_rule', 'learning')",
            name="ck_memory_items_type",
        ),
        sa.CheckConstraint(
            "status IN ('candidate', 'active', 'stable', 'deprecated')",
            name="ck_memory_items_status",
        ),
    )

    # Indexes for memory_items
    op.create_index(
        "idx_memory_items_project_status",
        "memory_items",
        ["project_id", "status"],
    )
    op.create_index(
        "idx_memory_items_project_type",
        "memory_items",
        ["project_id", "type"],
    )
    op.create_index(
        "idx_memory_items_created_at",
        "memory_items",
        ["created_at"],
    )

    # 2. Create context_modules table
    op.create_table(
        "context_modules",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("selectors_json", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )

    # Indexes for context_modules
    op.create_index(
        "idx_context_modules_project",
        "context_modules",
        ["project_id"],
    )

    # 3. Create module_memory_items join table
    op.create_table(
        "module_memory_items",
        sa.Column(
            "module_id",
            sa.String(),
            sa.ForeignKey("context_modules.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "memory_id",
            sa.String(),
            sa.ForeignKey("memory_items.id", ondelete="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("ordering", sa.Integer(), nullable=False, server_default="0"),
    )

    # Index for reverse lookups on module_memory_items
    op.create_index(
        "idx_module_memory_items_memory",
        "module_memory_items",
        ["memory_id"],
    )


def downgrade() -> None:
    """Drop memory_items, context_modules, and module_memory_items tables.

    Tables are dropped in reverse dependency order to respect foreign key
    constraints. All memory data, context module configurations, and their
    associations will be permanently lost.
    """
    # Drop in reverse dependency order
    op.drop_table("module_memory_items")
    op.drop_table("context_modules")
    op.drop_table("memory_items")
