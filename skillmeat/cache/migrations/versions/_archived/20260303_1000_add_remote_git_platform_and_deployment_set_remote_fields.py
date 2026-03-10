"""Add remote_git platform type and remote fields to deployment_sets.

Revision ID: 20260303_1000_add_remote_git_platform_and_deployment_set_remote_fields
Revises: 20260301_1300_add_color_to_entity_type_configs
Create Date: 2026-03-03 10:00:00.000000+00:00

Background
----------
This migration supports the Backstage / IDP integration feature.  When a
context pack is deployed to a remote Git repository (e.g. via an IDP), the
deployment must be recorded with ``platform='remote_git'`` and an optional
target repository URL.

Changes
-------
1. ``deployment_profiles`` — extend the ``ck_deployment_profiles_platform``
   CHECK constraint to include the new ``'remote_git'`` value.  Because SQLite
   does not support ``ALTER TABLE ... ADD/DROP CONSTRAINT``, the table is
   rebuilt via ``batch_alter_table`` with ``recreate="always"``.

2. ``deployment_sets`` — add two nullable columns:

   ``remote_url`` (TEXT, nullable)
       The URL of the remote Git repository where the set was deployed.
       ``NULL`` for all local deployment sets.

   ``provisioned_by`` (VARCHAR(128), nullable)
       Audit field that records which agent or system provisioned the
       deployment (e.g. ``'idp'``, ``'backstage'``).  ``NULL`` for sets
       created through standard local workflows.

Backward Compatibility
----------------------
All new columns are nullable with no server defaults other than ``NULL``.
All existing rows are unaffected.  Code that creates DeploymentSet or
DeploymentProfile records without the new fields continues to work unchanged.

Rollback
--------
* Drop ``remote_url`` and ``provisioned_by`` from ``deployment_sets``.
* Rebuild ``deployment_profiles`` with the original CHECK constraint
  (without ``'remote_git'``).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision: str = (
    "20260303_1000_add_remote_git_platform_and_deployment_set_remote_fields"
)
down_revision: Union[str, None] = "20260301_1300_add_color_to_entity_type_configs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Extend platform CHECK constraint and add remote columns to deployment_sets.

    Both operations are idempotent: column additions are skipped when the
    column already exists (e.g. when ``Base.metadata.create_all()`` was called
    before Alembic migrations ran).  The ``deployment_profiles`` table rebuild
    is always performed so that the CHECK constraint is up-to-date.
    """
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    # ------------------------------------------------------------------
    # 1. Update ck_deployment_profiles_platform to include 'remote_git'.
    #    SQLite does not support in-place constraint changes; batch_alter_table
    #    with recreate="always" rebuilds the table with the new definition.
    # ------------------------------------------------------------------
    with op.batch_alter_table("deployment_profiles", recreate="always") as batch_op:
        batch_op.drop_constraint(
            "ck_deployment_profiles_platform", type_="check"
        )
        batch_op.create_check_constraint(
            "ck_deployment_profiles_platform",
            "platform IN ('claude_code', 'codex', 'gemini', 'cursor', 'remote_git', 'other')",
        )

    # ------------------------------------------------------------------
    # 2. Add remote_url and provisioned_by to deployment_sets.
    # ------------------------------------------------------------------
    existing_ds_columns = {
        col["name"] for col in inspector.get_columns("deployment_sets")
    }

    if "remote_url" not in existing_ds_columns:
        op.add_column(
            "deployment_sets",
            sa.Column(
                "remote_url",
                sa.Text(),
                nullable=True,
                comment=(
                    "Remote Git repository URL for remote_git platform deployments"
                ),
            ),
        )

    if "provisioned_by" not in existing_ds_columns:
        op.add_column(
            "deployment_sets",
            sa.Column(
                "provisioned_by",
                sa.String(128),
                nullable=True,
                comment=(
                    "Audit field: provisioning agent/system "
                    "(e.g. 'idp', 'backstage')"
                ),
            ),
        )


def downgrade() -> None:
    """Reverse the migration.

    * Drops ``remote_url`` and ``provisioned_by`` from ``deployment_sets``.
    * Rebuilds ``deployment_profiles`` with the original CHECK constraint
      (without ``'remote_git'``).
    """
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    # ------------------------------------------------------------------
    # 1. Drop remote_url and provisioned_by from deployment_sets.
    # ------------------------------------------------------------------
    existing_ds_columns = {
        col["name"] for col in inspector.get_columns("deployment_sets")
    }

    if "provisioned_by" in existing_ds_columns:
        op.drop_column("deployment_sets", "provisioned_by")

    if "remote_url" in existing_ds_columns:
        op.drop_column("deployment_sets", "remote_url")

    # ------------------------------------------------------------------
    # 2. Restore the original CHECK constraint (without 'remote_git').
    # ------------------------------------------------------------------
    with op.batch_alter_table("deployment_profiles", recreate="always") as batch_op:
        batch_op.drop_constraint(
            "ck_deployment_profiles_platform", type_="check"
        )
        batch_op.create_check_constraint(
            "ck_deployment_profiles_platform",
            "platform IN ('claude_code', 'codex', 'gemini', 'cursor', 'other')",
        )
