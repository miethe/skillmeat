"""Enterprise implementation of IMembershipRepository.

Fulfils the :class:`~skillmeat.core.interfaces.repositories.IMembershipRepository`
interface using the enterprise (PostgreSQL) data tier.

All queries target ``enterprise_team_members`` and are automatically scoped to
the tenant currently stored in ``TenantContext`` — callers never pass a
``tenant_id`` directly.

References
----------
- Interface: ``skillmeat/core/interfaces/repositories.py`` (``IMembershipRepository``)
- Models: ``skillmeat/cache/models_enterprise.py`` (``EnterpriseTeamMember``)
- Base pattern: ``skillmeat/cache/enterprise_repositories.py``
  (``EnterpriseRepositoryBase``)
"""

from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from skillmeat.cache.constants import DEFAULT_TENANT_ID
from skillmeat.cache.enterprise_repositories import TenantContext
from skillmeat.cache.models_enterprise import EnterpriseTeamMember
from skillmeat.core.interfaces.repositories import IMembershipRepository

logger = logging.getLogger(__name__)


class EnterpriseMembershipRepository(IMembershipRepository):
    """IMembershipRepository backed by the enterprise PostgreSQL database.

    Tenant scoping is applied automatically to every query via the
    ``TenantContext`` ContextVar — mirroring the convention established by
    :class:`~skillmeat.cache.enterprise_repositories.EnterpriseRepositoryBase`.

    Parameters
    ----------
    session:
        An open SQLAlchemy ``Session`` bound to the enterprise PostgreSQL
        database.  Transaction management (commit / rollback / close) is the
        caller's responsibility.

    Examples
    --------
    ::

        from skillmeat.cache.enterprise_repositories import tenant_scope

        with tenant_scope(tenant_uuid):
            repo = EnterpriseMembershipRepository(db_session)
            team_ids = repo.get_team_ids_for_user(user_uuid)
    """

    def __init__(self, session: Session) -> None:
        self.session: Session = session

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_tenant_id(self) -> uuid.UUID:
        """Return the active tenant UUID.

        Resolution order:

        1. ``TenantContext`` ContextVar — set per-request by middleware or
           ``tenant_scope()`` in tests.
        2. ``DEFAULT_TENANT_ID`` — safe fallback for single-tenant mode.
        """
        tenant_id: Optional[uuid.UUID] = TenantContext.get(None)
        if tenant_id is None:
            logger.debug(
                "TenantContext not set; falling back to DEFAULT_TENANT_ID (%s)",
                DEFAULT_TENANT_ID,
            )
            return DEFAULT_TENANT_ID
        return tenant_id

    # ------------------------------------------------------------------
    # IMembershipRepository implementation
    # ------------------------------------------------------------------

    def get_team_ids_for_user(self, user_id: uuid.UUID) -> List[uuid.UUID]:
        """Return the IDs of every team the user belongs to within the current tenant.

        Parameters
        ----------
        user_id:
            The UUID of the user whose team memberships are queried.

        Returns
        -------
        list[uuid.UUID]
            A (possibly empty) list of team UUIDs.
        """
        tenant_id = self._get_tenant_id()
        stmt = select(EnterpriseTeamMember.team_id).where(
            EnterpriseTeamMember.user_id == user_id,
            EnterpriseTeamMember.tenant_id == tenant_id,
        )
        rows = self.session.execute(stmt).scalars().all()
        return list(rows)

    def get_team_role(
        self, user_id: uuid.UUID, team_id: uuid.UUID
    ) -> Optional[str]:
        """Return the user's role in the given team, or ``None`` if not a member.

        Parameters
        ----------
        user_id:
            The UUID of the user.
        team_id:
            The UUID of the team.

        Returns
        -------
        str or None
            The role string (e.g. ``"owner"``, ``"team_member"``) when the
            user belongs to the team within the current tenant, ``None``
            otherwise.
        """
        tenant_id = self._get_tenant_id()
        stmt = select(EnterpriseTeamMember.role).where(
            EnterpriseTeamMember.user_id == user_id,
            EnterpriseTeamMember.team_id == team_id,
            EnterpriseTeamMember.tenant_id == tenant_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def is_member_of(self, user_id: uuid.UUID, team_id: uuid.UUID) -> bool:
        """Check whether the user is a member of the given team.

        Uses an existence sub-query to avoid fetching the full membership row.

        Parameters
        ----------
        user_id:
            The UUID of the user.
        team_id:
            The UUID of the team.

        Returns
        -------
        bool
            ``True`` when the user has a membership row for the team within
            the current tenant, ``False`` otherwise.
        """
        tenant_id = self._get_tenant_id()
        stmt = select(
            exists().where(
                EnterpriseTeamMember.user_id == user_id,
                EnterpriseTeamMember.team_id == team_id,
                EnterpriseTeamMember.tenant_id == tenant_id,
            )
        )
        result: Optional[bool] = self.session.execute(stmt).scalar()
        return bool(result)
