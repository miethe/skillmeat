"""document enterprise owner_type: add 'enterprise' to OwnerType enum (app-layer only)

Revision ID: ent_007_enterprise_owner_type
Revises: ent_006_auth_indexes
Create Date: 2026-03-12 00:07:00.000000+00:00

Background
----------
PRD-2 AAA/RBAC Foundation.  The ``OwnerType`` Python enum in
``skillmeat/cache/auth_types.py`` has been extended with a third value:

    class OwnerType(str, enum.Enum):
        user       = "user"
        team       = "team"
        enterprise = "enterprise"   # <-- added

The ``enterprise`` owner type represents organization-level ownership where
a resource belongs to the entire enterprise tenant rather than a specific
user or team.

Why no DDL is required
----------------------
The ``owner_type`` column on every ownership-bearing table is defined as
``sa.String(20)`` — a plain VARCHAR — in both the local (SQLite) schema
and the enterprise (PostgreSQL) schema.  It is **not** a database-level
ENUM type (e.g. PostgreSQL ``CREATE TYPE owner_type AS ENUM (...)``).

Allowed values are validated exclusively at the application layer via the
``OwnerType`` enum.  Adding a new enum member therefore requires:

  ✓  A Python source change (``auth_types.py``)          — already done
  ✗  A database schema change (``ALTER TYPE`` / DDL)     — not needed

This migration exists solely as a documentation marker so that the
Alembic revision chain remains accurate and reviewers can trace the
``enterprise`` owner type back to the migration that "blessed" it.

Affected columns (context — no DDL change)
------------------------------------------
Local (SQLite):
  - artifacts.owner_type          VARCHAR(20) server_default='user'
  - collections.owner_type        VARCHAR(20) server_default='user'
  - projects.owner_type           VARCHAR(20) server_default='user'
  - groups.owner_type             VARCHAR(20) server_default='user'

Enterprise (PostgreSQL):
  - enterprise_artifacts.owner_type    VARCHAR(20) server_default='user'
  - enterprise_collections.owner_type  VARCHAR(20) server_default='user'

Schema reference
----------------
skillmeat/cache/auth_types.py                              (OwnerType enum)
docs/project_plans/architecture/enterprise-db-schema-v1.md  (PRD-2 §3)
.claude/progress/aaa-rbac-foundation/                        (ownership work)
"""

from __future__ import annotations

from typing import Sequence, Union

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------

revision: str = "ent_007_enterprise_owner_type"
down_revision: Union[str, None] = "waw_001_add_workflow_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """No-op: owner_type is a String column; 'enterprise' is validated at the app layer.

    No DDL change is required.  The ``owner_type`` column stores its value as a
    plain VARCHAR(20) string on all affected tables in both the SQLite (local) and
    PostgreSQL (enterprise) schemas.  The extended ``OwnerType.enterprise`` value is
    accepted by the column without any schema modification.

    See module docstring for full rationale.
    """
    pass  # intentional no-op — documentation marker only


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """No-op: nothing was added to the database schema in upgrade().

    Rows already written with owner_type='enterprise' will remain in the database
    after a downgrade of this migration.  Application code rolled back to a version
    that does not recognise the 'enterprise' owner type should treat such rows as
    unknown/invalid and handle them defensively (e.g. filter or raise).
    """
    pass  # intentional no-op — documentation marker only
