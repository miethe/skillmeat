"""DeploymentSetService — resolves a deployment set into a flat artifact list.

Resolution semantics
--------------------
Each :class:`~skillmeat.cache.models.DeploymentSetMember` row carries exactly
one of three references (enforced by a DB CHECK constraint):

* ``artifact_uuid`` — emit the UUID directly.
* ``group_id`` — look up all ``GroupArtifact`` rows for the group and emit
  their ``artifact_uuid`` values in position order.
* ``member_set_id`` — recurse into the nested :class:`DeploymentSet`.

Deduplication preserves *first-seen* order: if the same ``artifact_uuid``
would appear more than once (either directly or via group/nested-set
expansion) only the first occurrence is kept.

Depth guard
-----------
To prevent run-away recursion on misconfigured data the resolver enforces a
configurable depth limit (default **20**).  Exceeding the limit raises
:class:`~skillmeat.core.exceptions.DeploymentSetResolutionError` that carries
the full traversal path so callers can surface a meaningful error message.

Testability
-----------
The heavy-lifting DFS logic lives in :meth:`DeploymentSetService._resolve_dfs`
which accepts *in-memory maps* instead of a live DB session.  This makes unit
tests fast and hermetic — see ``tests/test_deployment_set_service.py`` for
examples that never touch a real database.

Typical usage (FastAPI endpoint)::

    from sqlalchemy.orm import Session
    from skillmeat.core.deployment_sets import DeploymentSetService
    from skillmeat.core.exceptions import DeploymentSetResolutionError

    def get_resolved_uuids(session: Session, set_id: str) -> list[str]:
        svc = DeploymentSetService(session)
        try:
            return svc.resolve(set_id)
        except DeploymentSetResolutionError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set

from sqlalchemy.orm import Session

from skillmeat.core.exceptions import DeploymentSetResolutionError

logger = logging.getLogger(__name__)

# Maximum allowed nesting depth (number of recursive set expansions).
_DEFAULT_DEPTH_LIMIT: int = 20


class DeploymentSetService:
    """Service that resolves a DeploymentSet into a flat list of artifact UUIDs.

    The service can be used with a real SQLAlchemy session (production) or
    with in-memory mock data structures (unit tests).

    Args:
        session: Active SQLAlchemy session used to query
            ``DeploymentSetMember`` and ``GroupArtifact`` rows.
            Pass ``None`` only when calling :meth:`_resolve_dfs` directly
            with pre-built member maps (test scenarios).
        depth_limit: Maximum recursion depth before
            :class:`~skillmeat.core.exceptions.DeploymentSetResolutionError`
            is raised.  Defaults to 20.
    """

    def __init__(
        self,
        session: Optional[Session] = None,
        depth_limit: int = _DEFAULT_DEPTH_LIMIT,
    ) -> None:
        self._session = session
        self._depth_limit = depth_limit

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, set_id: str) -> List[str]:
        """Resolve *set_id* into an ordered, deduplicated list of artifact UUIDs.

        Performs a depth-first traversal of the set hierarchy:

        * Artifact members → emit ``artifact_uuid`` directly.
        * Group members → expand via ``GroupArtifact`` rows (ordered by
          ``position``).
        * Nested set members → recurse.

        Args:
            set_id: Primary key of the root :class:`DeploymentSet` to resolve.

        Returns:
            Ordered list of unique artifact UUID strings.  Empty list if the
            set does not exist or has no members.

        Raises:
            DeploymentSetResolutionError: If the recursion depth exceeds
                :attr:`depth_limit`.
            RuntimeError: If called without a session (programming error).
        """
        if self._session is None:
            raise RuntimeError(
                "DeploymentSetService.resolve() requires a session. "
                "Pass session= to the constructor."
            )

        member_map = self._build_member_map_from_db(set_id)
        group_map = self._build_group_map_from_db(member_map)

        return self._resolve_dfs(
            root_set_id=set_id,
            member_map=member_map,
            group_map=group_map,
        )

    # ------------------------------------------------------------------
    # Core DFS logic (session-free — injectable for unit tests)
    # ------------------------------------------------------------------

    def _resolve_dfs(
        self,
        root_set_id: str,
        member_map: Dict[str, List[Dict]],
        group_map: Dict[str, List[str]],
    ) -> List[str]:
        """Run the DFS resolution using pre-built in-memory maps.

        This method contains the entire traversal logic without any DB
        access, making it directly testable with synthetic data.

        Args:
            root_set_id: The set ID to start traversal from.
            member_map: Mapping of ``set_id`` → list of member dicts.
                Each dict has exactly one non-None key among:
                ``artifact_uuid``, ``group_id``, ``member_set_id``.
            group_map: Mapping of ``group_id`` → ordered list of
                ``artifact_uuid`` strings belonging to that group.

        Returns:
            Ordered, deduplicated list of artifact UUID strings.

        Raises:
            DeploymentSetResolutionError: Depth limit breached.
        """
        seen: Set[str] = set()
        result: List[str] = []

        def _dfs(set_id: str, path: List[str]) -> None:
            if len(path) > self._depth_limit:
                raise DeploymentSetResolutionError(
                    set_id=set_id,
                    path=path,
                    depth_limit=self._depth_limit,
                )

            members = member_map.get(set_id, [])
            for member in members:
                artifact_uuid: Optional[str] = member.get("artifact_uuid")
                group_id: Optional[str] = member.get("group_id")
                nested_set_id: Optional[str] = member.get("member_set_id")

                if artifact_uuid is not None:
                    if artifact_uuid not in seen:
                        seen.add(artifact_uuid)
                        result.append(artifact_uuid)

                elif group_id is not None:
                    for uuid in group_map.get(group_id, []):
                        if uuid not in seen:
                            seen.add(uuid)
                            result.append(uuid)

                elif nested_set_id is not None:
                    _dfs(nested_set_id, path + [nested_set_id])

        _dfs(root_set_id, [root_set_id])
        return result

    # ------------------------------------------------------------------
    # DB query helpers
    # ------------------------------------------------------------------

    def _build_member_map_from_db(self, root_set_id: str) -> Dict[str, List[Dict]]:
        """Fetch all DeploymentSetMember rows reachable from *root_set_id*.

        Performs a BFS to collect every set ID in the hierarchy so only a
        minimal set of rows are loaded, then builds the in-memory map used by
        :meth:`_resolve_dfs`.

        Returns:
            Mapping of ``set_id`` → list of member dicts (same structure as
            expected by :meth:`_resolve_dfs`).
        """
        # Lazy import to avoid circular imports at module load time.
        from skillmeat.cache.models import DeploymentSetMember

        session = self._session
        assert session is not None  # guarded by resolve()

        # BFS to collect all reachable set IDs.
        all_set_ids: Set[str] = set()
        frontier = {root_set_id}
        while frontier:
            all_set_ids.update(frontier)
            rows = (
                session.query(
                    DeploymentSetMember.set_id,
                    DeploymentSetMember.member_set_id,
                )
                .filter(
                    DeploymentSetMember.set_id.in_(list(frontier)),
                    DeploymentSetMember.member_set_id.isnot(None),
                )
                .all()
            )
            next_frontier: Set[str] = set()
            for _, child_id in rows:
                if child_id is not None and child_id not in all_set_ids:
                    next_frontier.add(child_id)
            frontier = next_frontier

        # Load all members for the collected set IDs.
        all_members = (
            session.query(DeploymentSetMember)
            .filter(DeploymentSetMember.set_id.in_(list(all_set_ids)))
            .order_by(DeploymentSetMember.set_id, DeploymentSetMember.position)
            .all()
        )

        member_map: Dict[str, List[Dict]] = {}
        for m in all_members:
            member_map.setdefault(m.set_id, []).append(
                {
                    "artifact_uuid": m.artifact_uuid,
                    "group_id": m.group_id,
                    "member_set_id": m.member_set_id,
                }
            )

        return member_map

    def _build_group_map_from_db(
        self, member_map: Dict[str, List[Dict]]
    ) -> Dict[str, List[str]]:
        """Fetch GroupArtifact rows for all group IDs referenced in *member_map*.

        Returns:
            Mapping of ``group_id`` → ordered list of ``artifact_uuid`` strings.
        """
        # Lazy import to avoid circular imports at module load time.
        from skillmeat.cache.models import GroupArtifact

        session = self._session
        assert session is not None  # guarded by resolve()

        # Collect all unique group IDs referenced across all sets.
        group_ids: Set[str] = set()
        for members in member_map.values():
            for m in members:
                gid = m.get("group_id")
                if gid is not None:
                    group_ids.add(gid)

        if not group_ids:
            return {}

        rows = (
            session.query(GroupArtifact.group_id, GroupArtifact.artifact_uuid)
            .filter(GroupArtifact.group_id.in_(list(group_ids)))
            .order_by(GroupArtifact.group_id, GroupArtifact.position)
            .all()
        )

        group_map: Dict[str, List[str]] = {}
        for gid, uuid in rows:
            group_map.setdefault(gid, []).append(uuid)

        return group_map
