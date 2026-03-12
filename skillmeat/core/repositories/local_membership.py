"""Local DB-backed implementation of IMembershipRepository.

Delegates to the SQLAlchemy cache layer (``skillmeat.cache.models``) for all
team-membership lookups.

Design notes
------------
* Local models use integer primary keys for both ``User`` and ``Team``.  The
  ``IMembershipRepository`` interface uses ``uuid.UUID`` for all IDs to match
  the enterprise contract.
* **User UUID → int PK mapping**: The ``User`` row created for local mode
  stores the deterministic UUID as its ``external_id`` column.  We resolve an
  incoming ``user_id: uuid.UUID`` by querying
  ``User.external_id == str(user_id)``.  If no row matches the external_id
  we return empty results — this is correct for local mode where no real
  membership records exist.
* **Team int PK → UUID mapping**: Team rows do not carry a UUID column.  We
  convert the integer PK to a ``uuid.UUID`` via ``uuid.UUID(int=team_id)`` on
  the way out, and reverse with ``team_uuid.int`` on the way in.
* Local mode typically has no team memberships at all (single implicit admin
  user, no teams created by default), so every method degrades gracefully to
  empty / ``None`` / ``False`` when the tables are unpopulated.
* The session is obtained via ``_get_db_session()`` (module-level singleton)
  following the same lifecycle as other local repositories.  An optional
  ``session`` constructor argument is accepted for test injection.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from skillmeat.core.interfaces.repositories import IMembershipRepository

# ---------------------------------------------------------------------------
# Optional DB imports — graceful degradation when the cache module is absent.
# ---------------------------------------------------------------------------
try:
    from skillmeat.cache.models import (
        TeamMember as _DBTeamMember,
        User as _DBUser,
        get_session as _get_db_session,
    )

    _db_available = True
except ImportError:  # pragma: no cover
    _get_db_session = None  # type: ignore[assignment]
    _DBTeamMember = None  # type: ignore[assignment,misc]
    _DBUser = None  # type: ignore[assignment,misc]
    _db_available = False

logger = logging.getLogger(__name__)

__all__ = ["LocalMembershipRepository"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_user_int_id(session: object, user_id: uuid.UUID) -> Optional[int]:
    """Look up the integer PK for a user given their UUID external identity.

    The local ``User`` row stores the UUID as a plain string in the
    ``external_id`` column.  Returns ``None`` when no matching row is found.

    Args:
        session: Active SQLAlchemy session.
        user_id: UUID to resolve (compared against ``User.external_id``).

    Returns:
        Integer primary key of the matching ``User`` row, or ``None``.
    """
    assert _DBUser is not None  # narrowing; guarded by _db_available
    user = (
        session.query(_DBUser)  # type: ignore[union-attr]
        .filter(_DBUser.external_id == str(user_id))
        .first()
    )
    return user.id if user is not None else None


# ---------------------------------------------------------------------------
# Repository implementation
# ---------------------------------------------------------------------------


class LocalMembershipRepository(IMembershipRepository):
    """Local DB-backed implementation of :class:`IMembershipRepository`.

    Suitable for single-tenant SQLite deployments.  In a freshly initialised
    local environment no team records exist, so all methods will return empty
    results — this is the expected behaviour and not an error condition.

    Args:
        session: Optional pre-existing SQLAlchemy session.  When supplied it
            is used directly and the caller is responsible for closing it.
            When omitted, each method opens its own session via
            ``skillmeat.cache.models.get_session()``.
    """

    def __init__(self, session: Optional[object] = None) -> None:
        self._injected_session = session

    # ------------------------------------------------------------------
    # Internal session management
    # ------------------------------------------------------------------

    def _get_session(self) -> object:
        """Return the session to use for this operation.

        If a session was injected at construction time it is returned
        directly.  Otherwise a new session is obtained from the module-level
        singleton factory.
        """
        if self._injected_session is not None:
            return self._injected_session
        return _get_db_session()  # type: ignore[misc]

    def _should_close_session(self) -> bool:
        """Return ``True`` when the session was created internally."""
        return self._injected_session is None

    # ------------------------------------------------------------------
    # IMembershipRepository
    # ------------------------------------------------------------------

    def get_team_ids_for_user(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        """Return UUIDs of every team the user belongs to.

        Resolves ``user_id`` (a UUID) to the local integer PK via
        ``User.external_id``, then returns all ``TeamMember.team_id`` values
        converted to UUIDs via ``uuid.UUID(int=team_id)``.

        Args:
            user_id: UUID of the user to look up.

        Returns:
            Possibly-empty list of team UUIDs.  Returns an empty list when the
            user is not found in the DB or has no memberships.
        """
        if not _db_available:
            logger.debug("DB not available — get_team_ids_for_user returning []")
            return []

        session = self._get_session()
        try:
            user_int_id = _resolve_user_int_id(session, user_id)
            if user_int_id is None:
                logger.debug(
                    "get_team_ids_for_user: user %s not found in local DB", user_id
                )
                return []

            assert _DBTeamMember is not None  # narrowing; guarded by _db_available
            rows = (
                session.query(_DBTeamMember.team_id)  # type: ignore[union-attr]
                .filter(_DBTeamMember.user_id == user_int_id)
                .all()
            )
            result = [uuid.UUID(int=row.team_id) for row in rows]
            logger.debug(
                "get_team_ids_for_user: user=%s → %d team(s)", user_id, len(result)
            )
            return result
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "get_team_ids_for_user failed for user %s: %s",
                user_id,
                exc,
                exc_info=True,
            )
            return []
        finally:
            if self._should_close_session():
                session.close()  # type: ignore[union-attr]

    def get_team_role(
        self, user_id: uuid.UUID, team_id: uuid.UUID
    ) -> str | None:
        """Return the user's role in a specific team, or ``None``.

        Args:
            user_id: UUID of the user.
            team_id: UUID of the team (converted from ``uuid.UUID(int=...)``).

        Returns:
            Role string (e.g. ``"team_admin"``, ``"team_member"``) when the
            user belongs to the team, ``None`` otherwise.
        """
        if not _db_available:
            logger.debug("DB not available — get_team_role returning None")
            return None

        session = self._get_session()
        try:
            user_int_id = _resolve_user_int_id(session, user_id)
            if user_int_id is None:
                return None

            # Convert UUID back to integer PK for the teams table.
            team_int_id: int = team_id.int

            assert _DBTeamMember is not None  # narrowing; guarded by _db_available
            row = (
                session.query(_DBTeamMember)  # type: ignore[union-attr]
                .filter(
                    _DBTeamMember.user_id == user_int_id,
                    _DBTeamMember.team_id == team_int_id,
                )
                .first()
            )
            return row.role if row is not None else None
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "get_team_role failed for user=%s team=%s: %s",
                user_id,
                team_id,
                exc,
                exc_info=True,
            )
            return None
        finally:
            if self._should_close_session():
                session.close()  # type: ignore[union-attr]

    def is_member_of(self, user_id: uuid.UUID, team_id: uuid.UUID) -> bool:
        """Check whether a user is a member of the given team.

        Args:
            user_id: UUID of the user.
            team_id: UUID of the team.

        Returns:
            ``True`` when a ``TeamMember`` row exists for this (user, team)
            pair, ``False`` otherwise.
        """
        if not _db_available:
            logger.debug("DB not available — is_member_of returning False")
            return False

        session = self._get_session()
        try:
            user_int_id = _resolve_user_int_id(session, user_id)
            if user_int_id is None:
                return False

            team_int_id: int = team_id.int

            assert _DBTeamMember is not None  # narrowing; guarded by _db_available
            exists = (
                session.query(_DBTeamMember)  # type: ignore[union-attr]
                .filter(
                    _DBTeamMember.user_id == user_int_id,
                    _DBTeamMember.team_id == team_int_id,
                )
                .first()
            )
            return exists is not None
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "is_member_of failed for user=%s team=%s: %s",
                user_id,
                team_id,
                exc,
                exc_info=True,
            )
            return False
        finally:
            if self._should_close_session():
                session.close()  # type: ignore[union-attr]
