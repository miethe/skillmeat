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
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from skillmeat.core.exceptions import (
    DeploymentSetCycleError,
    DeploymentSetResolutionError,
)

if TYPE_CHECKING:
    from skillmeat.core.deployment import DeploymentManager

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
        db_path: Optional path to the SQLite database file.  Used by the
            repository layer when constructing ``DeploymentSetRepository``.
        deployment_manager: Optional :class:`~skillmeat.core.deployment.DeploymentManager`
            instance injected for :meth:`batch_deploy`.  When ``None`` a
            ``ValueError`` is raised if ``batch_deploy`` is called.
    """

    def __init__(
        self,
        session: Optional[Session] = None,
        depth_limit: int = _DEFAULT_DEPTH_LIMIT,
        db_path: Optional[str] = None,
        deployment_manager: Optional["DeploymentManager"] = None,
    ) -> None:
        self._session = session
        self._depth_limit = depth_limit
        self._db_path = db_path
        self._deployment_manager = deployment_manager

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

    def add_member_with_cycle_check(
        self,
        set_id: str,
        owner_id: str,
        *,
        member_set_id: Optional[str] = None,
        artifact_uuid: Optional[str] = None,
        group_id: Optional[str] = None,
        position: Optional[int] = None,
    ):
        """Add a member to *set_id*, performing cycle detection for set-type members.

        For set-type members (``member_set_id`` is provided) this method calls
        :meth:`_check_cycle` before delegating to the repository.  Artifact and
        group members cannot form cycles so they bypass the check.

        Args:
            set_id: Primary key of the parent deployment set.
            owner_id: Owner scope passed through to the repository.
            member_set_id: Nested deployment set to add.  Triggers cycle check.
            artifact_uuid: Collection artifact UUID.  No cycle check.
            group_id: Artifact group id.  No cycle check.
            position: Explicit 0-based ordering position.  Auto-assigned when
                omitted.

        Returns:
            Newly created ``DeploymentSetMember`` instance.

        Raises:
            DeploymentSetCycleError: If adding *member_set_id* would create a
                circular reference.
            ValueError: Propagated from the repository if the exactly-one-ref
                constraint is violated.
            RuntimeError: If called without a session.
        """
        if self._session is None:
            raise RuntimeError(
                "DeploymentSetService.add_member_with_cycle_check() requires a "
                "session.  Pass session= to the constructor."
            )

        if member_set_id is not None:
            self._check_cycle(set_id, member_set_id)

        from skillmeat.cache.repositories import DeploymentSetRepository

        repo = DeploymentSetRepository(self._db_path)
        return repo.add_member(
            set_id,
            owner_id,
            artifact_uuid=artifact_uuid,
            group_id=group_id,
            member_set_id=member_set_id,
            position=position,
        )

    def batch_deploy(
        self,
        set_id: str,
        project_id: str,
        profile_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Resolve *set_id* and deploy all artifacts to *project_id*.

        Resolves the deployment set into a flat, deduplicated list of artifact
        UUIDs, looks up each UUID in the ``CollectionArtifact``/``Artifact``
        tables to obtain ``name`` and ``type``, constructs the canonical
        ``type:name`` artifact identifier, then invokes
        :meth:`~skillmeat.core.deployment.DeploymentManager.deploy_artifacts`
        for each artifact individually.

        Per-artifact exceptions are caught and recorded as ``"error"`` results
        so the loop never aborts prematurely.  If the project or a UUID mapping
        cannot be found, the method raises early (project) or records an error
        result (missing UUID).

        Args:
            set_id: Primary key of the :class:`~skillmeat.cache.models.DeploymentSet`
                to deploy.
            project_id: ``Project.id`` of the target project.
            profile_id: Optional deployment profile identifier passed through to
                :meth:`~skillmeat.core.deployment.DeploymentManager.deploy_artifacts`.

        Returns:
            List of result dicts, one per resolved artifact UUID.  Each dict
            contains:

            * ``artifact_uuid`` (str) — the UUID that was processed.
            * ``status`` (str) — ``"success"``, ``"skip"``, or ``"error"``.
            * ``error`` (str | None) — human-readable error message, or
              ``None`` when status is ``"success"`` or ``"skip"``.

        Raises:
            RuntimeError: If called without a session.
            ValueError: If no :class:`~skillmeat.core.deployment.DeploymentManager`
                was provided at construction time.
            LookupError: If *project_id* does not exist in the ``projects`` table.
        """
        if self._session is None:
            raise RuntimeError(
                "DeploymentSetService.batch_deploy() requires a session. "
                "Pass session= to the constructor."
            )
        if self._deployment_manager is None:
            raise ValueError(
                "DeploymentSetService.batch_deploy() requires a DeploymentManager. "
                "Pass deployment_manager= to the constructor."
            )

        # Lazy imports to avoid circular imports at module load time.
        from skillmeat.cache.models import Artifact, CollectionArtifact, Project

        session = self._session

        # ------------------------------------------------------------------
        # 1. Resolve project path (fail-fast if not found).
        # ------------------------------------------------------------------
        project_row = session.query(Project).filter(Project.id == project_id).first()
        if project_row is None:
            raise LookupError(
                f"Project {project_id!r} not found in the cache database. "
                "Ensure the project has been registered before deploying."
            )
        project_path = Path(project_row.path)

        # ------------------------------------------------------------------
        # 2. Resolve the set into a flat, deduplicated list of artifact UUIDs.
        # ------------------------------------------------------------------
        resolved_uuids: List[str] = self.resolve(set_id)

        logger.info(
            "batch_deploy: starting deployment",
            extra={
                "set_id": set_id,
                "project_id": project_id,
                "profile_id": profile_id,
                "resolved_count": len(resolved_uuids),
            },
        )

        # ------------------------------------------------------------------
        # 3. Build a UUID → (name, type) map via a single JOIN query.
        # ------------------------------------------------------------------
        if resolved_uuids:
            uuid_rows = (
                session.query(
                    Artifact.uuid,
                    Artifact.name,
                    Artifact.type,
                )
                .join(
                    CollectionArtifact,
                    CollectionArtifact.artifact_uuid == Artifact.uuid,
                )
                .filter(Artifact.uuid.in_(resolved_uuids))
                .all()
            )
        else:
            uuid_rows = []

        uuid_to_artifact: Dict[str, tuple] = {
            row.uuid: (row.name, row.type) for row in uuid_rows
        }

        # ------------------------------------------------------------------
        # 4. Deploy each artifact, collecting per-artifact results.
        # ------------------------------------------------------------------
        results: List[Dict[str, Any]] = []

        for artifact_uuid in resolved_uuids:
            if artifact_uuid not in uuid_to_artifact:
                logger.warning(
                    "batch_deploy: artifact UUID not found in collection cache; "
                    "skipping — set_id=%s project_id=%s artifact_uuid=%s",
                    set_id,
                    project_id,
                    artifact_uuid,
                )
                results.append(
                    {
                        "artifact_uuid": artifact_uuid,
                        "status": "error",
                        "error": (
                            f"Artifact UUID {artifact_uuid!r} not found in "
                            "collection_artifacts / artifacts tables."
                        ),
                    }
                )
                continue

            artifact_name, artifact_type = uuid_to_artifact[artifact_uuid]
            artifact_id = f"{artifact_type}:{artifact_name}"

            try:
                self._deployment_manager.deploy_artifacts(
                    artifact_names=[artifact_name],
                    project_path=project_path,
                    profile_id=profile_id,
                )
                logger.info(
                    "batch_deploy: deployed artifact — set_id=%s artifact_id=%s",
                    set_id,
                    artifact_id,
                )
                results.append(
                    {
                        "artifact_uuid": artifact_uuid,
                        "status": "success",
                        "error": None,
                    }
                )
            except Exception as exc:  # noqa: BLE001 — intentional broad catch
                logger.warning(
                    "batch_deploy: deploy failed for artifact — "
                    "set_id=%s artifact_id=%s error=%s",
                    set_id,
                    artifact_id,
                    exc,
                )
                results.append(
                    {
                        "artifact_uuid": artifact_uuid,
                        "status": "error",
                        "error": str(exc),
                    }
                )

        logger.info(
            "batch_deploy: completed — set_id=%s project_id=%s total=%d "
            "success=%d error=%d",
            set_id,
            project_id,
            len(results),
            sum(1 for r in results if r["status"] == "success"),
            sum(1 for r in results if r["status"] == "error"),
        )

        return results

    def _check_cycle(self, set_id: str, candidate_member_set_id: str) -> None:
        """Raise :class:`~skillmeat.core.exceptions.DeploymentSetCycleError` if
        adding *candidate_member_set_id* as a member of *set_id* would create a
        circular reference.

        A cycle exists when *set_id* is reachable by traversing the descendants
        of *candidate_member_set_id* — that is, when the proposed edge would
        close a path back to the parent.  A self-reference (``set_id ==
        candidate_member_set_id``) is also rejected.

        The check uses a BFS over set-type members only (artifact/group members
        can never form cycles).

        Args:
            set_id: The set that would *receive* the new member.
            candidate_member_set_id: The set that would become a nested member.

        Raises:
            DeploymentSetCycleError: Cycle detected; the exception carries the
                traversal path showing the chain that would close the loop.
            RuntimeError: If called without a session (programming error).
        """
        if self._session is None:
            raise RuntimeError(
                "DeploymentSetService._check_cycle() requires a session."
            )

        # Lazy import to avoid circular imports at module load time.
        from skillmeat.cache.models import DeploymentSetMember

        session = self._session

        # Self-reference is an immediate cycle.
        if candidate_member_set_id == set_id:
            raise DeploymentSetCycleError(
                set_id=set_id,
                path=[set_id, set_id],
            )

        # BFS: traverse descendants of candidate_member_set_id.
        # If we ever reach set_id, a cycle would be created.
        #
        # visited maps each visited set_id → the path used to reach it from
        # candidate_member_set_id (inclusive).  This lets us reconstruct the
        # full cycle path for the error message.
        visited: Dict[str, List[str]] = {
            candidate_member_set_id: [candidate_member_set_id]
        }
        frontier: List[str] = [candidate_member_set_id]

        while frontier:
            rows = (
                session.query(
                    DeploymentSetMember.set_id,
                    DeploymentSetMember.member_set_id,
                )
                .filter(
                    DeploymentSetMember.set_id.in_(frontier),
                    DeploymentSetMember.member_set_id.isnot(None),
                )
                .all()
            )

            next_frontier: List[str] = []
            for parent_id, child_id in rows:
                if child_id is None or child_id in visited:
                    continue

                path_to_child = visited[parent_id] + [child_id]

                if child_id == set_id:
                    # Cycle detected: the full cycle path is the proposed edge
                    # (set_id → candidate_member_set_id) plus the path back.
                    cycle_path = [set_id] + path_to_child
                    raise DeploymentSetCycleError(
                        set_id=set_id,
                        path=cycle_path,
                    )

                visited[child_id] = path_to_child
                next_frontier.append(child_id)

            frontier = next_frontier

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
