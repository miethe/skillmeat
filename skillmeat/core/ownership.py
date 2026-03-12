"""Ownership resolution DTOs and types.

Used by OwnershipResolver to express the resolved ownership context
for a request, consumed by repository filters and service-layer writes.

These are pure data classes with no database, web framework, or API layer
dependencies.  They form the contract between the auth/membership lookup
layer (OwnershipResolver) and the data access layer (repository filters).

References:
    skillmeat/cache/auth_types.py  -- OwnerType enum (user/team/enterprise)
    .claude/progress/ownership-resolution-membership-foundation/
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from skillmeat.cache.auth_types import OwnerType


# =============================================================================
# OwnerTarget
# =============================================================================


@dataclass(frozen=True)
class OwnerTarget:
    """An explicit ownership target for write operations.

    Represents the principal (user, team, or enterprise) that will own a
    created or updated resource.

    Attributes:
        owner_type: Discriminator for the owning principal kind.
        owner_id:   String identifier for the owner.  Local mode stores a
                    plain string (e.g. the UUID-derived ``local_admin`` id);
                    enterprise mode stores ``str(uuid.UUID)``.  Using ``str``
                    everywhere avoids type-mismatch errors when comparing
                    against ``Column(String)`` in both ORM backends.

    Example::

        user_target = OwnerTarget(owner_type=OwnerType.user, owner_id="abc-123")
        team_target = OwnerTarget(owner_type=OwnerType.team, owner_id="team-456")
    """

    owner_type: OwnerType
    owner_id: str  # str for DB compat (local=str, enterprise=str(uuid.UUID))


# =============================================================================
# ResolvedOwnership
# =============================================================================


@dataclass(frozen=True)
class ResolvedOwnership:
    """The full resolved ownership context for a request.

    Produced by ``OwnershipResolver`` from ``AuthContext`` + membership
    lookups.  Consumed by repository filters (to scope reads) and
    service-layer operations (to set write ownership).

    Attributes:
        default_owner:       The ownership target that newly created resources
                             will be assigned to.  For local mode and
                             user-initiated enterprise requests this is the
                             user's own ``OwnerTarget``.
        readable_scopes:     All ``OwnerTarget`` values from which this context
                             may read.  Typically includes the user's own
                             target, every team they belong to, and (when
                             applicable) the enterprise-level target.
        writable_scopes:     The subset of ``readable_scopes`` to which this
                             context may write.  Typically: user's own scope
                             plus teams where the user holds ``team_admin`` or
                             ``team_member`` with write permission.
        has_enterprise_scope: ``True`` when the user has enterprise-level
                             access (e.g. ``system_admin`` role in enterprise
                             mode).  Signals that repository filters may skip
                             owner-scoping entirely for global operations.
        tenant_id:           The tenant UUID for enterprise contexts.  ``None``
                             in local (single-tenant) mode.  Used to derive
                             the enterprise ``owner_id`` when constructing
                             write targets.

    Example::

        ownership = ResolvedOwnership(
            default_owner=OwnerTarget(OwnerType.user, "user-abc"),
            readable_scopes=[
                OwnerTarget(OwnerType.user, "user-abc"),
                OwnerTarget(OwnerType.team, "team-xyz"),
            ],
            writable_scopes=[
                OwnerTarget(OwnerType.user, "user-abc"),
                OwnerTarget(OwnerType.team, "team-xyz"),
            ],
        )
        assert ownership.can_read_from(OwnerType.team, "team-xyz")
        assert not ownership.can_write_to(OwnerType.enterprise, "tenant-1")
    """

    # The owner target written to newly created resources.
    default_owner: OwnerTarget

    # All scopes this context may READ from.
    readable_scopes: list[OwnerTarget] = field(default_factory=list)

    # All scopes this context may WRITE to.
    writable_scopes: list[OwnerTarget] = field(default_factory=list)

    # True when the user holds enterprise-level access.
    has_enterprise_scope: bool = False

    # Tenant UUID for enterprise contexts; None in local mode.
    tenant_id: Optional[uuid.UUID] = None

    # ------------------------------------------------------------------
    # Read access helpers
    # ------------------------------------------------------------------

    def can_read_from(self, owner_type: OwnerType, owner_id: str) -> bool:
        """Return True if this context allows reading from the given owner.

        Args:
            owner_type: The ``OwnerType`` of the target owner.
            owner_id:   The string owner identifier to check.

        Returns:
            ``True`` when a matching ``OwnerTarget`` exists in
            ``readable_scopes``; ``False`` otherwise.
        """
        return any(
            s.owner_type == owner_type and s.owner_id == owner_id
            for s in self.readable_scopes
        )

    # ------------------------------------------------------------------
    # Write access helpers
    # ------------------------------------------------------------------

    def can_write_to(self, owner_type: OwnerType, owner_id: str) -> bool:
        """Return True if this context allows writing to the given owner.

        Args:
            owner_type: The ``OwnerType`` of the target owner.
            owner_id:   The string owner identifier to check.

        Returns:
            ``True`` when a matching ``OwnerTarget`` exists in
            ``writable_scopes``; ``False`` otherwise.
        """
        return any(
            s.owner_type == owner_type and s.owner_id == owner_id
            for s in self.writable_scopes
        )
