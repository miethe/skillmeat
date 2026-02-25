"""Add deployment_set_tags junction table and migrate tags_json data.

Revision ID: 20260225_1000_add_deployment_set_tags_junction
Revises: 20260224_1000_add_deployment_set_tables
Create Date: 2026-02-25 10:00:00.000000+00:00

Background
----------
Deployment sets previously stored tags as a JSON text column (``tags_json``).
This migration introduces a proper many-to-many junction table
``deployment_set_tags`` that links ``deployment_sets`` to the shared ``tags``
table — exactly mirroring the ``artifact_tags`` pattern.

Existing ``tags_json`` data is migrated: for each deployment set, each tag
name string is resolved to an existing ``tags`` row (matched by name,
case-insensitive) or a new ``tags`` row is created, and a
``deployment_set_tags`` junction row is inserted.

The ``tags_json`` column is NOT dropped in this migration (backward
compatibility during rollout).  A future migration can remove it once all
callers read from the junction table.

Tables created
--------------
``deployment_set_tags``
    - ``deployment_set_id`` (String, FK → deployment_sets.id ON DELETE CASCADE,
      part of composite PK)
    - ``tag_id`` (String, FK → tags.id ON DELETE CASCADE, part of composite PK)
    - ``created_at`` (DateTime, non-null)
    - Indexes: ``idx_deployment_set_tags_set_id``,
               ``idx_deployment_set_tags_tag_id``

Data migration
--------------
For every deployment set row with a non-empty ``tags_json``:
    1. Parse the JSON array of tag name strings.
    2. For each name: find existing tag by name (lower-case comparison) or
       create a new tag with a generated UUID hex id and slug.
    3. Insert a ``deployment_set_tags`` row for the (set_id, tag_id) pair,
       skipping duplicates.

Rollback
--------
Drop ``deployment_set_tags``.  The ``tags_json`` column is untouched so data
is fully preserved on downgrade.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect, text


# revision identifiers, used by Alembic.
revision: str = "20260225_1000_add_deployment_set_tags_junction"
down_revision: Union[str, None] = "20260224_1000_add_deployment_set_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _slugify(name: str) -> str:
    """Convert a tag name to a kebab-case slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or uuid.uuid4().hex[:8]


def upgrade() -> None:
    """Create deployment_set_tags table and migrate existing tags_json data."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_tables = inspector.get_table_names()

    # -------------------------------------------------------------------------
    # 1. Create deployment_set_tags junction table
    # -------------------------------------------------------------------------
    if "deployment_set_tags" not in existing_tables:
        op.create_table(
            "deployment_set_tags",
            sa.Column(
                "deployment_set_id",
                sa.String(),
                sa.ForeignKey("deployment_sets.id", ondelete="CASCADE"),
                primary_key=True,
                nullable=False,
                comment="FK to deployment_sets.id — CASCADE DELETE",
            ),
            sa.Column(
                "tag_id",
                sa.String(),
                sa.ForeignKey("tags.id", ondelete="CASCADE"),
                primary_key=True,
                nullable=False,
                comment="FK to tags.id — CASCADE DELETE",
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

        op.create_index(
            "idx_deployment_set_tags_set_id",
            "deployment_set_tags",
            ["deployment_set_id"],
        )
        op.create_index(
            "idx_deployment_set_tags_tag_id",
            "deployment_set_tags",
            ["tag_id"],
        )

    # -------------------------------------------------------------------------
    # 2. Migrate existing tags_json data into the junction table
    # -------------------------------------------------------------------------
    # Only run if deployment_sets table exists (might be a fresh DB)
    if "deployment_sets" not in existing_tables or "tags" not in existing_tables:
        return

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Fetch all deployment sets that have non-empty tags_json
    rows = bind.execute(
        text("SELECT id, tags_json FROM deployment_sets WHERE tags_json IS NOT NULL")
    ).fetchall()

    for set_id, tags_json_value in rows:
        if not tags_json_value:
            continue

        try:
            tag_names = json.loads(tags_json_value)
        except (json.JSONDecodeError, TypeError):
            continue

        if not isinstance(tag_names, list):
            continue

        for raw_name in tag_names:
            if not isinstance(raw_name, str):
                continue
            name = raw_name.strip()
            if not name:
                continue

            # Find existing tag by name (case-insensitive)
            existing = bind.execute(
                text("SELECT id FROM tags WHERE lower(name) = lower(:name)"),
                {"name": name},
            ).fetchone()

            if existing:
                tag_id = existing[0]
            else:
                # Create a new tag
                tag_id = uuid.uuid4().hex
                slug = _slugify(name)

                # Ensure slug uniqueness
                base_slug = slug
                counter = 1
                while bind.execute(
                    text("SELECT 1 FROM tags WHERE slug = :slug"), {"slug": slug}
                ).fetchone():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                bind.execute(
                    text(
                        "INSERT INTO tags (id, name, slug, color, created_at, updated_at) "
                        "VALUES (:id, :name, :slug, NULL, :now, :now)"
                    ),
                    {"id": tag_id, "name": name, "slug": slug, "now": now},
                )

            # Insert junction row (skip if already exists)
            existing_assoc = bind.execute(
                text(
                    "SELECT 1 FROM deployment_set_tags "
                    "WHERE deployment_set_id = :set_id AND tag_id = :tag_id"
                ),
                {"set_id": set_id, "tag_id": tag_id},
            ).fetchone()

            if not existing_assoc:
                bind.execute(
                    text(
                        "INSERT INTO deployment_set_tags "
                        "(deployment_set_id, tag_id, created_at) "
                        "VALUES (:set_id, :tag_id, :now)"
                    ),
                    {"set_id": set_id, "tag_id": tag_id, "now": now},
                )


def downgrade() -> None:
    """Drop deployment_set_tags junction table.

    tags_json column is preserved, so existing data survives the downgrade.
    """
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_tables = inspector.get_table_names()

    if "deployment_set_tags" in existing_tables:
        # Drop indexes first (SQLite may require this explicitly)
        existing_indexes = {
            idx["name"] for idx in inspector.get_indexes("deployment_set_tags")
        }
        if "idx_deployment_set_tags_set_id" in existing_indexes:
            op.drop_index(
                "idx_deployment_set_tags_set_id", table_name="deployment_set_tags"
            )
        if "idx_deployment_set_tags_tag_id" in existing_indexes:
            op.drop_index(
                "idx_deployment_set_tags_tag_id", table_name="deployment_set_tags"
            )
        op.drop_table("deployment_set_tags")
