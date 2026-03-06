"""Auth type enums for SkillMeat AAA/RBAC foundation.

Defines Python enums for ownership, visibility, and role concepts used across
both local (SQLite) and enterprise (PostgreSQL) auth models.  These enums are
standalone — they import nothing from the cache layer — so they can be safely
imported by models.py, models_enterprise.py, repositories, API schemas, and
anywhere else without creating circular dependencies.

Enums:
    OwnerType   — discriminates between user-owned and team-owned resources
    Visibility  — controls who can see a resource
    UserRole    — system-wide and team-level role assignments

Usage:
    >>> from skillmeat.cache.auth_types import OwnerType, Visibility, UserRole
    >>> column = sa.Column(sa.Enum(UserRole), nullable=False, default=UserRole.viewer)

Storage note:
    SQLAlchemy stores enum values as their string ``.value`` in the database.
    All values are lowercase ASCII so they round-trip cleanly through both
    SQLite TEXT columns and PostgreSQL native ENUM types.

References:
    .claude/progress/aaa-rbac-foundation/phase-1-progress.md  DB-001
"""

import enum


# =============================================================================
# OwnerType
# =============================================================================


class OwnerType(str, enum.Enum):
    """Discriminator for the owning principal of a resource.

    Used as the value for ``owner_type`` columns on resources that support
    both user-level and team-level ownership.

    Values:
        user: Resource is owned by a single user.
        team: Resource is owned by a team (shared among team members).
    """

    user = "user"
    team = "team"


# =============================================================================
# Visibility
# =============================================================================


class Visibility(str, enum.Enum):
    """Access-visibility level for a resource.

    Controls who is allowed to discover and read a resource.  Write/manage
    access is determined separately by role checks.

    Values:
        private: Only the owner (user or team members) can see the resource.
        team:    All members of the owning team can see the resource.
        public:  Any authenticated user (within the tenant) can see the resource.
    """

    private = "private"
    team = "team"
    public = "public"


# =============================================================================
# UserRole
# =============================================================================


class UserRole(str, enum.Enum):
    """Role assigned to a user, either system-wide or within a team.

    When stored on an ``enterprise_users`` or ``users`` row the role applies
    system-wide.  When stored on a ``team_members`` / ``enterprise_team_members``
    row the role is scoped to that team only.

    Values:
        system_admin:  Full administrative access across the tenant.
        team_admin:    Administrative access within a specific team.
        team_member:   Standard member access within a specific team.
        viewer:        Read-only access; the default for newly created users.

    Hierarchy (most → least privileged):
        system_admin > team_admin > team_member > viewer
    """

    system_admin = "system_admin"
    team_admin = "team_admin"
    team_member = "team_member"
    viewer = "viewer"
