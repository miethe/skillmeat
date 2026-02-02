"""Add deployments_json column to collection_artifacts table

Revision ID: 20260202_1100_add_deployments_json_to_collection_artifacts
Revises: 20260202_1000_add_tools_json_to_collection_artifacts
Create Date: 2026-02-02 11:00:00.000000+00:00

This migration adds a deployments_json column to the collection_artifacts table to
track where artifacts are deployed in projects. This enables:
- Tracking deployment locations without scanning filesystem
- Fast lookup of which projects use which artifacts
- API endpoints to query deployment status

Field added:
- deployments_json: TEXT - JSON array of deployment paths

The column is nullable for backward compatibility. Existing entries will have
NULL values until populated by deployment operations.

Part of SCHEMA-0.2 implementation.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260202_1100_add_deployments_json_to_collection_artifacts"
down_revision: Union[str, None] = "20260202_1000_add_tools_json_to_collection_artifacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add deployments_json column to collection_artifacts table.

    Adds a TEXT column for storing JSON array of deployment paths where the
    artifact has been deployed. This enables:
    - Fast lookup of deployment status without filesystem scanning
    - Tracking which projects use which artifacts
    - API endpoints to query deployments across the collection

    The column is nullable for backward compatibility. Existing entries will
    have NULL values until populated by deployment operations.
    """
    # Add deployments_json column (JSON array of deployment paths)
    op.add_column(
        "collection_artifacts",
        sa.Column(
            "deployments_json",
            sa.Text(),
            nullable=True,
            comment="JSON array of deployment paths",
        ),
    )


def downgrade() -> None:
    """Remove deployments_json column from collection_artifacts table.

    This reverts the migration by dropping the deployments_json column.
    Any cached deployment metadata will be permanently lost.

    WARNING: This is a destructive operation. Deployment metadata must be
    re-scanned from the filesystem if the migration is later re-applied.
    """
    # Drop the deployments_json column
    op.drop_column("collection_artifacts", "deployments_json")
