"""Ownership resolution service for SkillMeat AAA/RBAC system.

Derives the resolved ownership context (readable/writable scopes and default
write target) from an :class:`~skillmeat.api.schemas.auth.AuthContext` plus
membership lookups via :class:`~skillmeat.core.interfaces.repositories.IMembershipRepository`.

This module is intentionally free of FastAPI, SQLAlchemy, and filesystem
dependencies.  It depends only on pure-Python DTOs and interfaces so that it
can be unit-tested without any I/O.

Design constraints:
    - Request-scoped, stateless: instantiate once per request (or inject via DI).
    - Local/no-auth stays user-owned: ``tenant_id is None`` → no enterprise scope.
    - Enterprise scope is additive, not mandatory: only ``system_admin`` in
      enterprise mode receives enterprise-level write access.
    - Team lookups always run; in local mode the membership repository returns
      empty lists (no teams exist).

References:
    skillmeat/core/ownership.py                  -- OwnerTarget, ResolvedOwnership
    skillmeat/api/schemas/auth.py                -- AuthContext, Role
    skillmeat/core/interfaces/repositories.py    -- IMembershipRepository
    skillmeat/cache/auth_types.py                -- OwnerType
    .claude/progress/ownership-resolution-membership-foundation/
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from skillmeat.cache.auth_types import OwnerType
from skillmeat.core.interfaces.repositories import IMembershipRepository
from skillmeat.core.ownership import OwnerTarget, ResolvedOwnership

if TYPE_CHECKING:
    from skillmeat.api.schemas.auth import AuthContext

logger = logging.getLogger(__name__)

# Role strings that grant write access within a team.
_TEAM_WRITABLE_ROLES: frozenset[str] = frozenset(
    {"owner", "team_admin", "team_member"}
)


class OwnershipResolver:
    """Request-scoped ownership resolver.

    Takes an :class:`~skillmeat.api.schemas.auth.AuthContext` and an
    :class:`~skillmeat.core.interfaces.repositories.IMembershipRepository`
    and produces the full :class:`~skillmeat.core.ownership.ResolvedOwnership`
    context: which owner scopes are readable, which are writable, and which
    single target newly created resources should be assigned to.

    This class is stateless — there is no mutable state after construction.
    Instantiate it once per request or inject it via FastAPI's dependency
    injection machinery.

    Args:
        membership_repo: Concrete membership repository implementation.
            In local mode the implementation returns empty lists (no teams).
            In enterprise mode it queries ``enterprise_team_members``.

    Example::

        resolver = OwnershipResolver(membership_repo=repo)
        ownership = resolver.resolve(auth_context)

        if ownership.can_write_to(OwnerType.team, str(team_id)):
            artifact_repo.create(dto, owner=team_target)
    """

    def __init__(self, membership_repo: IMembershipRepository) -> None:
        self._membership = membership_repo

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, auth_context: AuthContext) -> ResolvedOwnership:
        """Resolve the full ownership context for a request.

        The resolution algorithm is:

        1. Always start with the requesting user as the sole default owner
           and the only initial member of both readable and writable scopes.
        2. Expand readable and writable scopes with every team the user
           belongs to, subject to the team role check for write access.
        3. When ``auth_context.tenant_id`` is not ``None`` (enterprise mode):
           - All enterprise users get the enterprise target added to
             ``readable_scopes``.
           - Only ``system_admin`` users additionally get it in
             ``writable_scopes`` and have ``has_enterprise_scope`` set.

        Args:
            auth_context: The immutable auth context for the current request.

        Returns:
            A :class:`~skillmeat.core.ownership.ResolvedOwnership` instance
            capturing all readable/writable scopes and the default write owner.
        """
        user_owner = OwnerTarget(
            owner_type=OwnerType.user,
            owner_id=str(auth_context.user_id),
        )

        readable: list[OwnerTarget] = [user_owner]
        writable: list[OwnerTarget] = [user_owner]
        has_enterprise = False

        # ------------------------------------------------------------------
        # Team membership expansion
        # ------------------------------------------------------------------
        team_ids = self._membership.get_team_ids_for_user(auth_context.user_id)
        for team_id in team_ids:
            team_target = OwnerTarget(
                owner_type=OwnerType.team,
                owner_id=str(team_id),
            )
            readable.append(team_target)

            role = self._membership.get_team_role(auth_context.user_id, team_id)
            if role in _TEAM_WRITABLE_ROLES:
                writable.append(team_target)
            else:
                logger.debug(
                    "User %s has read-only role %r in team %s; "
                    "team not added to writable_scopes.",
                    auth_context.user_id,
                    role,
                    team_id,
                )

        # ------------------------------------------------------------------
        # Enterprise scope (only when tenant_id is present)
        # ------------------------------------------------------------------
        if auth_context.tenant_id is not None:
            enterprise_target = OwnerTarget(
                owner_type=OwnerType.enterprise,
                owner_id=str(auth_context.tenant_id),
            )
            readable.append(enterprise_target)

            if auth_context.is_admin():
                # system_admin users can write enterprise-owned resources.
                writable.append(enterprise_target)
                has_enterprise = True
                logger.debug(
                    "User %s is system_admin in tenant %s; "
                    "enterprise scope added to both readable and writable.",
                    auth_context.user_id,
                    auth_context.tenant_id,
                )
            else:
                logger.debug(
                    "User %s is non-admin in tenant %s; "
                    "enterprise scope added to readable only.",
                    auth_context.user_id,
                    auth_context.tenant_id,
                )

        return ResolvedOwnership(
            default_owner=user_owner,
            readable_scopes=readable,
            writable_scopes=writable,
            has_enterprise_scope=has_enterprise,
            tenant_id=auth_context.tenant_id,
        )
