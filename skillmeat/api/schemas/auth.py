"""Auth context and RBAC schemas for SkillMeat AAA/RBAC system.

Defines the AuthContext dataclass (SVR-001) and RBAC enums (SVR-002) used
across API request handling, middleware, and dependency injection.

The enums delegate to or re-export from ``skillmeat.cache.auth_types`` where
the canonical definitions already exist (OwnerType, Visibility, UserRole).
Role and Scope are API-layer additions that live here because they are
consumed primarily by the API surface rather than the DB layer.

References:
    .claude/progress/aaa-rbac-foundation/  SVR-001, SVR-002
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict

# Re-export storage-layer enums so callers only need one import path.
from skillmeat.cache.auth_types import OwnerType, UserRole as _UserRole, Visibility
from skillmeat.cache.constants import LOCAL_ADMIN_USER_ID


# =============================================================================
# RBAC Enums (SVR-002)
# =============================================================================


class Role(str, Enum):
    """System-wide and team-level role assignments.

    Maps 1-to-1 with ``skillmeat.cache.auth_types.UserRole`` so that
    API code can reference ``Role`` without importing from the cache layer.

    Values:
        system_admin:  Full administrative access across the tenant.
        team_admin:    Administrative access within a specific team.
        team_member:   Standard member access within a specific team.
        viewer:        Read-only access; default for newly created users.

    Hierarchy (most -> least privileged):
        system_admin > team_admin > team_member > viewer
    """

    system_admin = "system_admin"
    team_admin = "team_admin"
    team_member = "team_member"
    viewer = "viewer"


class Scope(str, Enum):
    """Fine-grained permission scopes using ``resource:action`` naming.

    Scopes gate individual API operations independently of role assignments,
    allowing future token-scoped access patterns (e.g. CLI tokens that can
    only read artifacts).

    Values:
        artifact_read:    Read artifact metadata and content.
        artifact_write:   Create, update, and delete artifacts.
        collection_read:  Read collection metadata and membership.
        collection_write: Create, update, and delete collections.
        deployment_read:  Read deployment records and status.
        deployment_write: Create and remove deployments.
        admin_wildcard:   Wildcard scope granting all admin operations.
    """

    artifact_read = "artifact:read"
    artifact_write = "artifact:write"
    collection_read = "collection:read"
    collection_write = "collection:write"
    deployment_read = "deployment:read"
    deployment_write = "deployment:write"
    admin_wildcard = "admin:*"


# Re-export OwnerType and Visibility so consumers only need ``auth.py``.
__all__ = [
    "AuthContext",
    "LOCAL_ADMIN_CONTEXT",
    "OwnerScopeFilter",
    "OwnerTargetInput",
    "OwnerType",
    "Role",
    "Scope",
    "Visibility",
    "str_owner_id",
]


# =============================================================================
# AuthContext (SVR-001)
# =============================================================================


@dataclass(frozen=True)
class AuthContext:
    """Immutable authentication and authorisation context for a request.

    Constructed once per request by authentication middleware (or dependency
    injection) and passed through to service and router layers.  The frozen
    dataclass guarantees that auth state cannot be mutated after construction.

    Attributes:
        user_id:   UUID of the authenticated user.
        tenant_id: UUID of the tenant; ``None`` in local (single-tenant) mode.
        roles:     List of role strings held by this user.
        scopes:    List of permission scope strings granted for this request.

    Example::

        ctx = AuthContext(
            user_id=uuid.UUID("..."),
            roles=[Role.team_member],
            scopes=[Scope.artifact_read.value, Scope.collection_read.value],
        )
        assert ctx.has_role(Role.team_member)
        assert ctx.has_scope("artifact:read")
    """

    user_id: uuid.UUID
    tenant_id: uuid.UUID | None = None
    roles: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Role helpers
    # ------------------------------------------------------------------

    def has_role(self, role: str | Role) -> bool:
        """Return True if this context carries the given role.

        Args:
            role: A ``Role`` enum member or its string value.

        Returns:
            True when the role is present; False otherwise.
        """
        value = role.value if isinstance(role, Role) else role
        return value in self.roles

    def is_admin(self) -> bool:
        """Return True if this context carries the ``system_admin`` role."""
        return self.has_role(Role.system_admin)

    # ------------------------------------------------------------------
    # Scope helpers
    # ------------------------------------------------------------------

    def has_scope(self, scope: str | Scope) -> bool:
        """Return True if this context carries the given scope.

        A context that holds the ``admin:*`` wildcard scope is treated as
        having every scope.

        Args:
            scope: A ``Scope`` enum member or its string value.

        Returns:
            True when the scope (or admin wildcard) is present; False otherwise.
        """
        if Scope.admin_wildcard.value in self.scopes:
            return True
        value = scope.value if isinstance(scope, Scope) else scope
        return value in self.scopes

    def has_any_scope(self, *scopes: str | Scope) -> bool:
        """Return True if this context carries at least one of the given scopes.

        Args:
            *scopes: One or more ``Scope`` enum members or string values.

        Returns:
            True when at least one scope is present (or admin wildcard held).
        """
        return any(self.has_scope(s) for s in scopes)


# =============================================================================
# Type conversion helpers
# =============================================================================


def str_owner_id(auth_context: AuthContext) -> str:
    """Convert AuthContext.user_id (uuid.UUID) to a plain string for DB queries.

    Type mismatch pattern: ``cache/models.py`` stores ``owner_id`` as
    ``Column(String)``, while ``AuthContext.user_id`` is typed as
    ``uuid.UUID`` (the API layer UUID).  Callers must not compare them
    directly — always use this helper so the conversion is explicit and
    centralised.

    Args:
        auth_context: The authenticated request context.

    Returns:
        String representation of ``auth_context.user_id`` (lowercase,
        hyphenated UUID format, e.g. ``"550e8400-e29b-41d4-a716-446655440000"``).
    """
    return str(auth_context.user_id)


# =============================================================================
# Built-in contexts
# =============================================================================

#: Pre-built AuthContext for the implicit local admin user.
#: Used by local-mode middleware where no explicit authentication is required.
#: Carries all scopes and the system_admin role so that all permission checks
#: pass transparently in single-user local deployments.
LOCAL_ADMIN_CONTEXT: AuthContext = AuthContext(
    user_id=LOCAL_ADMIN_USER_ID,
    tenant_id=None,
    roles=[Role.system_admin.value],
    scopes=[s.value for s in Scope],
)


# =============================================================================
# Owner scope / target schemas (Phase 4 — ownership-resolution)
# =============================================================================


class OwnerScopeFilter(str, Enum):
    """Filter list results by owner scope.

    Used as a query parameter on collection / artifact list endpoints to
    restrict results to resources owned by a specific principal kind.

    Values:
        user:       Return only resources owned by the requesting user.
        team:       Return only resources owned by one of the user's teams.
        enterprise: Return only resources owned at the enterprise/tenant level.
        all:        Default — return all resources readable by this context.

    Note:
        The ``all`` value does *not* bypass visibility filtering; it returns
        the union of all scopes the authenticated context may read, as
        determined by :class:`~skillmeat.core.ownership.ResolvedOwnership`.
    """

    user = "user"
    team = "team"
    enterprise = "enterprise"
    all = "all"


class OwnerTargetInput(BaseModel):
    """Explicit owner selection for write mutations.

    When omitted from request bodies the service layer defaults to
    user-owned resources.  Team ownership requires an explicit ``team_id``
    to be present in ``owner_id``.  Enterprise ownership requires explicit
    selection and the caller must hold the ``system_admin`` role.

    Attributes:
        owner_type: Discriminator for the target principal kind.
                    Defaults to ``OwnerType.user``.
        owner_id:   String identifier of the owning principal.  For
                    ``owner_type=user`` this is auto-populated from the
                    auth context when omitted.  For ``team`` and
                    ``enterprise`` it must be supplied explicitly.

    Example::

        # User-owned (default — owner_id omitted, resolved from auth context)
        body = OwnerTargetInput()

        # Team-owned
        body = OwnerTargetInput(owner_type=OwnerType.team, owner_id="<team-uuid>")

        # Enterprise-owned (system_admin only)
        body = OwnerTargetInput(owner_type=OwnerType.enterprise, owner_id="<tenant-uuid>")
    """

    owner_type: OwnerType = OwnerType.user
    owner_id: Optional[str] = None  # Auto-filled for user; required for team/enterprise

    model_config = ConfigDict(use_enum_values=True)
