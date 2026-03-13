"""Ownership resolution and attestation scope filtering for SkillBOM.

Provides two collaborating classes:

``OwnershipResolver``
    Resolves the effective ``(owner_type, owner_id)`` tuple from an auth
    context or from explicit ID kwargs.  Acts as the single place where
    precedence rules are encoded — enterprise > team > user > anonymous.

``AttestationScopeResolver``
    Enforces owner-scoped visibility rules for ``AttestationRecord`` rows.
    Callers use it to filter lists of records or to generate DB query
    filter criteria that respect the viewer's role hierarchy.

Role hierarchy (most → least privileged):
    system_admin > enterprise_admin > team_admin > team_member > viewer

Visibility levels (from ``OwnerType`` / ``Visibility`` enums):
    public  — any authenticated user may see the record
    team    — team members (and above) of the owning team may see it
    private — only the owner (matching owner_id) may see it

These classes are intentionally framework-agnostic; they import only from
``skillmeat.cache.auth_types`` and ``skillmeat.cache.models``.

Example::

    resolver = OwnershipResolver()
    owner_type, owner_id = resolver.resolve(user_id="u-123")
    # → ("user", "u-123")

    scope_resolver = AttestationScopeResolver(resolver)
    visible = scope_resolver.filter_visible(
        records,
        viewer_owner_type="team",
        viewer_owner_id="t-456",
        viewer_roles=["team_admin"],
    )
"""

from __future__ import annotations

from typing import Any

from skillmeat.cache.auth_types import OwnerType, Visibility
from skillmeat.cache.models import AttestationRecord

# ---------------------------------------------------------------------------
# Role constants
# ---------------------------------------------------------------------------

_ROLE_SYSTEM_ADMIN = "system_admin"
_ROLE_ENTERPRISE_ADMIN = "enterprise_admin"
_ROLE_TEAM_ADMIN = "team_admin"
_ROLE_TEAM_MEMBER = "team_member"


# =============================================================================
# OwnershipResolver
# =============================================================================


class OwnershipResolver:
    """Resolves effective owner_type/owner_id from an auth context.

    This class encodes the single canonical place where ownership precedence
    is decided.  All code that needs to determine "who owns this resource"
    should go through this resolver rather than reimplementing the precedence
    logic inline.

    Precedence order (highest wins):
        1. enterprise — ``tenant_id`` is set
        2. team       — ``team_id`` is set
        3. user       — ``user_id`` is set
        4. anonymous  — no identifiers provided (fallback: ``"user"/"anonymous"``)

    The resolver is intentionally stateless so the same instance can be shared
    across requests without synchronisation concerns.
    """

    def resolve(
        self,
        user_id: str | None = None,
        team_id: str | None = None,
        tenant_id: str | None = None,
    ) -> tuple[str, str]:
        """Return ``(owner_type, owner_id)`` based on precedence rules.

        Args:
            user_id:   Opaque user identifier string (e.g. UUID as str).
            team_id:   Opaque team identifier string.
            tenant_id: Opaque enterprise/tenant identifier string.

        Returns:
            A ``(owner_type, owner_id)`` 2-tuple where ``owner_type`` is one
            of ``"enterprise"``, ``"team"``, or ``"user"``.

        Examples::

            resolver = OwnershipResolver()

            # Enterprise context wins
            resolver.resolve(user_id="u1", team_id="t1", tenant_id="e1")
            # → ("enterprise", "e1")

            # Team wins over user
            resolver.resolve(user_id="u1", team_id="t1")
            # → ("team", "t1")

            # User only
            resolver.resolve(user_id="u1")
            # → ("user", "u1")

            # Nothing provided → anonymous fallback
            resolver.resolve()
            # → ("user", "anonymous")
        """
        if tenant_id is not None:
            return (OwnerType.enterprise.value, str(tenant_id))
        if team_id is not None:
            return (OwnerType.team.value, str(team_id))
        if user_id is not None:
            return (OwnerType.user.value, str(user_id))
        return (OwnerType.user.value, "anonymous")

    def resolve_from_auth_context(self, auth_context: Any) -> tuple[str, str]:
        """Extract ownership from an AuthContext object.

        Uses ``getattr`` with ``None`` defaults throughout so that this method
        works safely against any object that has a subset of the expected
        attributes (e.g. ``LocalAuthProvider``'s context omits ``tenant_id``).

        Args:
            auth_context: Any object with optional ``user_id``, ``team_id``,
                and/or ``tenant_id`` attributes.  The attributes may be absent
                or ``None``; both are treated as "not set".

        Returns:
            A ``(owner_type, owner_id)`` 2-tuple, same as :meth:`resolve`.
        """
        # tenant_id and team_id may be UUID objects; normalise to str via resolve()
        tenant_id = getattr(auth_context, "tenant_id", None)
        team_id = getattr(auth_context, "team_id", None)
        user_id = getattr(auth_context, "user_id", None)

        # Convert UUID objects to strings before handing to resolve()
        return self.resolve(
            user_id=str(user_id) if user_id is not None else None,
            team_id=str(team_id) if team_id is not None else None,
            tenant_id=str(tenant_id) if tenant_id is not None else None,
        )


# =============================================================================
# AttestationScopeResolver
# =============================================================================


class AttestationScopeResolver:
    """Enforces owner-scoped visibility rules for attestation records.

    Works in tandem with :class:`OwnershipResolver` to determine which
    ``AttestationRecord`` rows a given viewer principal is allowed to see.

    Visibility rules (checked in order, first match wins):

    1. ``system_admin`` role → can see **every** record regardless of owner,
       visibility, or tenant.
    2. ``enterprise_admin`` role → can see all records whose ``owner_type``
       is ``"enterprise"`` (i.e. all tenant-level records).
    3. ``team_admin`` role → can see all records owned by the same team
       (``owner_type == "team"`` and ``owner_id`` matches ``viewer_owner_id``).
    4. ``team_member`` role → can see team records owned by the same team
       where visibility is *not* ``"private"``.
    5. Default (user) → can only see records where ``owner_id`` matches the
       viewer's own ``owner_id``.
    6. ``visibility == "public"`` → any authenticated viewer may see the record.

    Args:
        ownership_resolver: An :class:`OwnershipResolver` instance used
            internally when ownership derivation is delegated.
    """

    def __init__(self, ownership_resolver: OwnershipResolver) -> None:
        self._resolver = ownership_resolver

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def can_view(
        self,
        record: AttestationRecord,
        viewer_owner_type: str,
        viewer_owner_id: str,
        viewer_roles: list[str] | None = None,
    ) -> bool:
        """Return ``True`` if the viewer is allowed to see ``record``.

        Args:
            record: The ``AttestationRecord`` to check.
            viewer_owner_type: The resolved owner type of the viewer
                (``"user"``, ``"team"``, or ``"enterprise"``).
            viewer_owner_id: The resolved owner identifier of the viewer.
            viewer_roles: Optional list of role strings held by the viewer.
                An empty list or ``None`` is equivalent to no elevated roles.

        Returns:
            ``True`` when the viewer may read ``record``; ``False`` otherwise.
        """
        roles: list[str] = viewer_roles or []

        # Rule 1: system_admin sees everything.
        if _ROLE_SYSTEM_ADMIN in roles:
            return True

        # Rule 6: public records are visible to all authenticated users.
        if record.visibility == Visibility.public.value:
            return True

        # Rule 2: enterprise_admin sees all enterprise-owned records.
        if _ROLE_ENTERPRISE_ADMIN in roles:
            if record.owner_type == OwnerType.enterprise.value:
                return True

        # Team-based rules — only relevant when viewing a team-owned record.
        if record.owner_type == OwnerType.team.value:
            same_team = record.owner_id == viewer_owner_id

            # Rule 3: team_admin sees all records for their own team.
            if _ROLE_TEAM_ADMIN in roles and same_team:
                return True

            # Rule 4: team_member sees non-private records for their own team.
            if _ROLE_TEAM_MEMBER in roles and same_team:
                if record.visibility != Visibility.private.value:
                    return True

        # Rule 5: principals can see their own non-team records.
        # For user-owned records this means owner_id match is sufficient.
        # Team records are fully governed by the team rules above; the
        # owner_id match alone must NOT bypass the visibility check for team
        # records (otherwise team_member could read private team records just
        # because the team's owner_id matches their own viewer_owner_id).
        if record.owner_type != OwnerType.team.value and record.owner_id == viewer_owner_id:
            return True

        return False

    def filter_visible(
        self,
        records: list[AttestationRecord],
        viewer_owner_type: str,
        viewer_owner_id: str,
        viewer_roles: list[str] | None = None,
    ) -> list[AttestationRecord]:
        """Return the subset of ``records`` visible to the viewer.

        This is a pure in-memory filter; it does not touch the database.
        Use :meth:`build_query_filters` to generate DB-level filtering
        criteria for large datasets where loading all rows first is
        impractical.

        Args:
            records: Full list of ``AttestationRecord`` objects to filter.
            viewer_owner_type: Resolved owner type of the viewer.
            viewer_owner_id: Resolved owner identifier of the viewer.
            viewer_roles: Optional list of role strings for the viewer.

        Returns:
            A new list containing only those records the viewer may see,
            in the same order as the input.
        """
        return [
            r
            for r in records
            if self.can_view(r, viewer_owner_type, viewer_owner_id, viewer_roles)
        ]

    def build_query_filters(
        self,
        owner_type: str,
        owner_id: str,
        roles: list[str] | None = None,
    ) -> dict[str, str]:
        """Return filter criteria dict suitable for repository query methods.

        The returned dict can be passed directly to repository query helpers
        as keyword filters.  For privileged roles the ``owner_id`` filter is
        intentionally omitted so that callers see all records matching the
        broader scope.

        Args:
            owner_type: The resolved owner type of the requesting principal.
            owner_id: The resolved owner identifier of the requesting principal.
            roles: Optional list of role strings held by the principal.

        Returns:
            A dict of filter criteria.  Examples::

                # system_admin — no filtering, returns empty dict
                {}

                # enterprise_admin — filter to enterprise-owned records only
                {"owner_type": "enterprise"}

                # team_admin / team_member — filter to their team's records
                {"owner_type": "team", "owner_id": "<team-id>"}

                # regular user — filter to own records
                {"owner_type": "user", "owner_id": "<user-id>"}

        Note:
            The dict does not encode a ``visibility`` filter.  Callers that
            want to honour visibility at the DB level should extend the
            returned dict with an ``OR (visibility == 'public')`` clause
            appropriate to their query builder.
        """
        roles_list: list[str] = roles or []

        # system_admin: no restriction — let the caller retrieve everything.
        if _ROLE_SYSTEM_ADMIN in roles_list:
            return {}

        # enterprise_admin: all enterprise-scoped records for the tenant.
        if _ROLE_ENTERPRISE_ADMIN in roles_list:
            return {"owner_type": OwnerType.enterprise.value}

        # team_admin / team_member: records owned by their specific team.
        if owner_type == OwnerType.team.value and (
            _ROLE_TEAM_ADMIN in roles_list or _ROLE_TEAM_MEMBER in roles_list
        ):
            return {"owner_type": OwnerType.team.value, "owner_id": owner_id}

        # Default: the requester's own records.
        return {"owner_type": owner_type, "owner_id": owner_id}
