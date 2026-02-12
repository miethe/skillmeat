"""Add promoted memory provenance columns and structured anchors.

Revision ID: 20260209_1700_add_memory_anchor_and_provenance_columns
Revises: 20260207_1400_add_deployment_profiles_and_target_platforms
Create Date: 2026-02-09 17:00:00.000000+00:00
"""

from __future__ import annotations

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260209_1700_add_memory_anchor_and_provenance_columns"
down_revision: Union[str, None] = "20260207_1400_add_deployment_profiles_and_target_platforms"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _to_anchor_objects(raw: object) -> object:
    """Convert legacy anchor strings into structured anchor objects."""
    if not isinstance(raw, list):
        return raw

    converted = []
    for entry in raw:
        if isinstance(entry, str):
            converted.append({"path": entry, "type": "code"})
        elif isinstance(entry, dict):
            if "path" in entry:
                converted.append(entry)
        else:
            # Preserve unknown values as-is to avoid destructive migrations.
            converted.append(entry)
    return converted


def _to_anchor_strings(raw: object) -> object:
    """Convert structured anchor objects back into legacy string anchors."""
    if not isinstance(raw, list):
        return raw

    converted = []
    for entry in raw:
        if isinstance(entry, dict):
            path = entry.get("path")
            if isinstance(path, str):
                converted.append(path)
        elif isinstance(entry, str):
            converted.append(entry)
    return converted


def _migrate_anchors(forward: bool) -> None:
    """Migrate anchors_json payloads between legacy and structured formats."""
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, anchors_json FROM memory_items "
            "WHERE anchors_json IS NOT NULL AND anchors_json != ''"
        )
    ).fetchall()

    for row in rows:
        try:
            parsed = json.loads(row.anchors_json)
        except json.JSONDecodeError:
            continue

        migrated = _to_anchor_objects(parsed) if forward else _to_anchor_strings(parsed)
        if migrated == parsed:
            continue

        connection.execute(
            sa.text("UPDATE memory_items SET anchors_json = :anchors_json WHERE id = :id"),
            {"id": row.id, "anchors_json": json.dumps(migrated)},
        )


def upgrade() -> None:
    """Add promoted columns, indexes, and migrate anchors_json."""
    with op.batch_alter_table("memory_items", schema=None) as batch_op:
        batch_op.add_column(sa.Column("git_branch", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("git_commit", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("session_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("agent_type", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("model", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column("source_type", sa.String(), nullable=True, server_default="manual")
        )
        batch_op.create_index("idx_memory_items_git_branch", ["git_branch"], unique=False)
        batch_op.create_index("idx_memory_items_git_commit", ["git_commit"], unique=False)
        batch_op.create_index("idx_memory_items_session_id", ["session_id"], unique=False)
        batch_op.create_index("idx_memory_items_agent_type", ["agent_type"], unique=False)
        batch_op.create_index("idx_memory_items_model", ["model"], unique=False)
        batch_op.create_index("idx_memory_items_source_type", ["source_type"], unique=False)

    _migrate_anchors(forward=True)


def downgrade() -> None:
    """Revert promoted columns/indexes and unwrap anchors_json objects."""
    _migrate_anchors(forward=False)

    with op.batch_alter_table("memory_items", schema=None) as batch_op:
        batch_op.drop_index("idx_memory_items_source_type")
        batch_op.drop_index("idx_memory_items_model")
        batch_op.drop_index("idx_memory_items_agent_type")
        batch_op.drop_index("idx_memory_items_session_id")
        batch_op.drop_index("idx_memory_items_git_commit")
        batch_op.drop_index("idx_memory_items_git_branch")
        batch_op.drop_column("source_type")
        batch_op.drop_column("model")
        batch_op.drop_column("agent_type")
        batch_op.drop_column("session_id")
        batch_op.drop_column("git_commit")
        batch_op.drop_column("git_branch")
