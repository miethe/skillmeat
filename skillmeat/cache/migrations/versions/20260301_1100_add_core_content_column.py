"""Add core_content column to artifacts table.

Revision ID: 20260301_1100_add_core_content_column
Revises: 20260301_1000_add_custom_type_fields
Create Date: 2026-03-01 11:00:00.000000+00:00

Background
----------
CECO-4.1 (Modular Content Architecture) introduces a split between
platform-agnostic content and the assembled/cached output that gets
written to disk on deploy.

``core_content``
    The raw, platform-agnostic content supplied by the author.  When the
    ``modular_content_architecture`` feature flag is enabled, create/update
    endpoints store the incoming content here and populate ``content`` with
    the assembled result for the default target platform.  The deploy
    endpoint assembles platform-specific output from ``core_content`` at
    deploy time using ``skillmeat.core.content_assembly.assemble_content``.

    When the flag is disabled (default) this column remains NULL and the
    existing ``content`` column is used unchanged, so there is no
    behavioural change for deployments that have not opted in.

Tables modified
---------------
``artifacts``
  - ADD ``core_content``  Text  nullable  (platform-agnostic content)

Rollback
--------
Drop the column.  No other tables are affected.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision: str = "20260301_1100_add_core_content_column"
down_revision: Union[str, None] = "20260301_1000_add_custom_type_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add core_content column to artifacts.

    Uses ``sa_inspect`` to check for column existence before adding so the
    migration is idempotent on databases that already have the column (e.g.
    when ``Base.metadata.create_all()`` was called before migration).
    """
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("artifacts")}

    if "core_content" not in existing_columns:
        op.add_column(
            "artifacts",
            sa.Column(
                "core_content",
                sa.Text(),
                nullable=True,
                comment=(
                    "Platform-agnostic content before assembly. "
                    "When modular_content_architecture is enabled, stores the raw "
                    "author-supplied content; `content` holds the assembled output "
                    "for the default target platform."
                ),
            ),
        )


def downgrade() -> None:
    """Drop core_content column from artifacts.

    Any platform-agnostic content stored in this column will be permanently
    lost.  No other tables are affected.
    """
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("artifacts")}

    if "core_content" in existing_columns:
        op.drop_column("artifacts", "core_content")
