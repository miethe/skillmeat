"""Service layer for composite artifact membership operations.

This module bridges the external API (where artifact identity is expressed
as ``type:name`` strings) and the internal DB layer (where child artifacts are
referenced by their stable UUID per ADR-007).

Responsibilities
----------------
- Resolve ``type:name`` → UUID via a single DB lookup before delegating to the
  repository.
- Raise domain-appropriate exceptions (``ArtifactNotFoundError``) so callers
  never need to understand the UUID resolution concern.
- Provide ``get_associations()`` as a unified read surface returning both the
  composite's children and the artifact's parent composites.

No circular imports
-------------------
This module imports only from:
- ``skillmeat.cache.composite_repository`` (data access)
- ``skillmeat.cache.models`` (ORM models for UUID lookup only)
- ``skillmeat.cache.repositories`` (shared exception types)

Usage
-----
>>> from skillmeat.core.services.composite_service import CompositeService
>>>
>>> svc = CompositeService()
>>>
>>> # Add a member by type:name (UUID resolved internally)
>>> record = svc.add_composite_member(
...     collection_id="collection-abc",
...     composite_id="composite:my-plugin",
...     child_artifact_id="skill:canvas",
...     pinned_version_hash=None,
... )
>>>
>>> # Get all associations for any artifact
>>> result = svc.get_associations("composite:my-plugin", "collection-abc")
>>> print(result["children"])
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from skillmeat.cache.composite_repository import (
    CompositeMembershipRepository,
    CompositeRecord,
    MembershipRecord,
)
from skillmeat.cache.repositories import ConstraintError, NotFoundError

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class ArtifactNotFoundError(NotFoundError):
    """Raised when a ``type:name`` artifact cannot be resolved to a UUID.

    This wraps the lower-level ``NotFoundError`` from the repository layer so
    that callers have a clear, named exception for the "child not in cache"
    scenario.

    Args:
        artifact_id: The ``type:name`` string that could not be resolved.

    Example:
        >>> raise ArtifactNotFoundError("skill:unknown-skill")
        ArtifactNotFoundError: Artifact not found in cache: 'skill:unknown-skill'
    """

    def __init__(self, artifact_id: str) -> None:
        self.artifact_id = artifact_id
        super().__init__(
            f"Artifact not found in cache: {artifact_id!r}. "
            "The artifact must be imported into the collection before it can be "
            "added as a composite member."
        )


# ---------------------------------------------------------------------------
# AssociationResult type alias
# ---------------------------------------------------------------------------

AssociationResult = Dict[str, List[MembershipRecord]]
"""Return type for ``get_associations``.

.. code-block:: python

    {
        "parents": [MembershipRecord, ...],  # composites that contain this artifact
        "children": [MembershipRecord, ...], # children of this composite
    }
"""


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------


class CompositeService:
    """Business logic for composite artifact membership.

    Sits between API routers and ``CompositeMembershipRepository``.  Handles
    ``type:name`` → UUID resolution so that callers always work with the
    human-readable ``type:name`` identifiers.

    Attributes:
        _repo: Underlying repository instance.

    Example:
        >>> svc = CompositeService()
        >>> svc.add_composite_member("col-abc", "composite:my-plugin", "skill:canvas")
        {"composite_id": "composite:my-plugin", "child_artifact_uuid": "...", ...}
    """

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        """Initialise the service with an optional database path.

        Args:
            db_path: Path to the SQLite cache database.  When ``None`` the
                repository uses ``~/.skillmeat/cache/cache.db``.
        """
        self._repo = CompositeMembershipRepository(db_path=db_path)
        self._db_path = self._repo.db_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_uuid(self, session: Session, artifact_id: str) -> str:
        """Resolve a ``type:name`` artifact id to its stable UUID.

        Args:
            session: Active SQLAlchemy session to use for the query.
            artifact_id: ``type:name`` primary key (e.g. ``"skill:canvas"``).

        Returns:
            The 32-character hex UUID string from ``artifacts.uuid``.

        Raises:
            ArtifactNotFoundError: When no artifact with ``id == artifact_id``
                exists in the cache.
        """
        # Import here to avoid circular imports at module load time
        from skillmeat.cache.models import Artifact

        artifact = session.query(Artifact).filter(Artifact.id == artifact_id).first()
        if artifact is None:
            raise ArtifactNotFoundError(artifact_id)
        return artifact.uuid

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def add_composite_member(
        self,
        collection_id: str,
        composite_id: str,
        child_artifact_id: str,
        pinned_version_hash: Optional[str] = None,
        relationship_type: str = "contains",
    ) -> MembershipRecord:
        """Add a child artifact to a composite by ``type:name``.

        Resolves ``child_artifact_id`` (``type:name``) to the artifact's stable
        UUID, then delegates to the repository to create the membership edge.

        Args:
            collection_id: Owning collection identifier.
            composite_id: ``type:name`` id of the parent composite
                (e.g. ``"composite:my-plugin"``).
            child_artifact_id: ``type:name`` id of the child artifact
                (e.g. ``"skill:canvas"``).  Must exist in the ``artifacts``
                table or ``ArtifactNotFoundError`` is raised.
            pinned_version_hash: Optional content hash to pin the child to a
                specific version snapshot.  ``None`` means "track latest".
            relationship_type: Semantic edge label, default ``"contains"``.

        Returns:
            ``MembershipRecord`` dict for the new membership edge.

        Raises:
            ArtifactNotFoundError: When ``child_artifact_id`` cannot be
                resolved to a cached artifact.
            ConstraintError: When the membership already exists or another DB
                constraint is violated.

        Example:
            >>> svc.add_composite_member(
            ...     "col-abc", "composite:my-plugin", "skill:canvas"
            ... )
            {"collection_id": "col-abc", "composite_id": "composite:my-plugin",
             "child_artifact_uuid": "a1b2c3d4...", ...}
        """
        # Open a temporary session just for UUID resolution, keeping it
        # separate from the repository's internal transaction session to
        # avoid session-sharing issues across the boundary.
        session = self._repo._get_session()
        try:
            child_uuid = self._resolve_uuid(session, child_artifact_id)
        finally:
            session.close()

        logger.info(
            "add_composite_member: resolved %r → uuid=%s (composite=%s, collection=%s)",
            child_artifact_id,
            child_uuid,
            composite_id,
            collection_id,
        )

        return self._repo.create_membership(
            collection_id=collection_id,
            composite_id=composite_id,
            child_artifact_uuid=child_uuid,
            relationship_type=relationship_type,
            pinned_version_hash=pinned_version_hash,
        )

    def remove_composite_member(
        self,
        composite_id: str,
        child_artifact_id: str,
    ) -> bool:
        """Remove a child artifact from a composite by ``type:name``.

        Resolves ``child_artifact_id`` to a UUID and then delegates to
        ``CompositeMembershipRepository.delete_membership()``.

        Args:
            composite_id: ``type:name`` id of the parent composite.
            child_artifact_id: ``type:name`` id of the child artifact to remove.

        Returns:
            ``True`` if the membership was found and deleted; ``False`` if no
            matching membership existed.

        Raises:
            ArtifactNotFoundError: When ``child_artifact_id`` cannot be
                resolved to a cached artifact.
        """
        session = self._repo._get_session()
        try:
            child_uuid = self._resolve_uuid(session, child_artifact_id)
        finally:
            session.close()

        logger.info(
            "remove_composite_member: resolved %r → uuid=%s (composite=%s)",
            child_artifact_id,
            child_uuid,
            composite_id,
        )

        return self._repo.delete_membership(
            composite_id=composite_id,
            child_artifact_uuid=child_uuid,
        )

    def reorder_composite_members(
        self,
        composite_id: str,
        reorder: List[Dict[str, Any]],
    ) -> List[MembershipRecord]:
        """Reorder members within a composite.

        Each entry in ``reorder`` must be a dict with ``"artifact_id"``
        (``type:name``) and ``"position"`` (int ≥ 0).  The service resolves
        ``artifact_id`` → UUID and delegates to the repository.

        Args:
            composite_id: ``type:name`` id of the parent composite.
            reorder: List of ``{"artifact_id": str, "position": int}`` dicts.

        Returns:
            Updated list of membership records for the composite.

        Raises:
            ArtifactNotFoundError: When any ``artifact_id`` cannot be resolved.
        """
        session = self._repo._get_session()
        try:
            resolved = [
                {"child_artifact_uuid": self._resolve_uuid(session, item["artifact_id"]),
                 "position": item["position"]}
                for item in reorder
            ]
        finally:
            session.close()

        logger.info(
            "reorder_composite_members: composite=%s count=%d",
            composite_id,
            len(resolved),
        )

        return self._repo.reorder_members(
            composite_id=composite_id,
            reorder=resolved,
        )

    def create_composite(
        self,
        collection_id: str,
        composite_id: str,
        composite_type: str = "plugin",
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        initial_members: Optional[List[str]] = None,
        pinned_version_hash: Optional[str] = None,
    ) -> "CompositeRecord":
        """Create a new CompositeArtifact, optionally with initial members.

        Args:
            collection_id: Owning collection identifier.
            composite_id: ``type:name`` id for the new composite
                (e.g. ``"composite:my-plugin"``).
            composite_type: Variant — ``"plugin"``, ``"stack"``, or
                ``"suite"``.  Defaults to ``"plugin"``.
            display_name: Optional human-readable label.
            description: Optional free-text description.
            initial_members: Optional list of child ``type:name`` ids to add
                immediately.  Each is resolved to a UUID before insertion.
            pinned_version_hash: Optional version pin applied to every
                initial member.

        Returns:
            ``CompositeRecord`` dict for the newly created composite.

        Raises:
            ArtifactNotFoundError: When any ``initial_members`` entry cannot
                be resolved to a cached artifact.
            ConstraintError: When a composite with the same ``composite_id``
                already exists in the collection.
        """
        # Resolve initial members → UUIDs before touching the DB
        resolved_uuids: List[str] = []
        if initial_members:
            session = self._repo._get_session()
            try:
                for child_id in initial_members:
                    resolved_uuids.append(self._resolve_uuid(session, child_id))
            finally:
                session.close()

        logger.info(
            "create_composite: id=%s type=%s collection=%s members=%d",
            composite_id,
            composite_type,
            collection_id,
            len(resolved_uuids),
        )

        return self._repo.create_composite(
            collection_id=collection_id,
            composite_id=composite_id,
            composite_type=composite_type,
            display_name=display_name,
            description=description,
            initial_member_uuids=resolved_uuids,
            pinned_version_hash=pinned_version_hash,
        )

    def create_skill_composite(
        self,
        skill_artifact: Any,
        embedded_list: List[Any],
        collection_id: str = "default",
        display_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> "CompositeRecord":
        """Create a CompositeArtifact of type 'skill' wrapping a skill artifact.

        Registers the given skill as a skill-type composite in the DB cache.
        Member creation (dedup logic) is deferred to Phase 2 (TASK-2.1) and
        is intentionally not implemented here.

        The ``metadata_json`` field carries the originating skill's stable UUID
        so that callers can correlate the composite back to the source artifact
        without a separate join:

        .. code-block:: json

            {"artifact_uuid": "<skill-artifact-uuid>"}

        Args:
            skill_artifact: Artifact ORM instance (or any object exposing
                ``.id`` and ``.uuid`` attributes) for the skill being
                wrapped as a composite.
            embedded_list: List of embedded child artifact objects discovered
                inside the skill directory.  **Not used in Phase 1** — member
                rows will be created in Phase 2 (TASK-2.1).  Accepted here so
                the call-site signature is stable across both phases.
            collection_id: Owning collection identifier.  Defaults to
                ``"default"`` when not specified.
            display_name: Optional human-readable label for the composite.
                When ``None``, the skill's ``id`` is used as a fallback label
                by callers.
            description: Optional free-text description.

        Returns:
            ``CompositeRecord`` dict for the newly created composite.

        Raises:
            ConstraintError: When a composite with the derived ``composite_id``
                already exists in the collection.

        Note:
            **Phase 2 (TASK-2.1)**: Member creation with dedup logic is
            intentionally omitted here.  Once TASK-2.1 is complete, call
            ``add_composite_member()`` for each entry in ``embedded_list``
            after creating the composite.

        Example:
            >>> svc = CompositeService()
            >>> record = svc.create_skill_composite(
            ...     skill_artifact=my_skill,
            ...     embedded_list=[cmd_artifact, agent_artifact],
            ...     collection_id="my-collection",
            ... )
            >>> record["composite_type"]
            'skill'
        """
        composite_id = f"composite:{skill_artifact.id.split(':', 1)[-1]}"
        artifact_uuid = str(skill_artifact.uuid)
        metadata = json.dumps({"artifact_uuid": artifact_uuid})

        logger.info(
            "create_skill_composite: skill=%r composite_id=%s uuid=%s "
            "embedded_count=%d collection=%s",
            skill_artifact.id,
            composite_id,
            artifact_uuid,
            len(embedded_list),
            collection_id,
        )

        # TODO (TASK-2.1): iterate over embedded_list and call
        #   add_composite_member() for each entry after applying dedup logic.
        logger.debug(
            "create_skill_composite: member creation deferred to Phase 2 "
            "(TASK-2.1) — %d embedded artifact(s) will be added later",
            len(embedded_list),
        )

        with self._repo.transaction() as session:
            from skillmeat.cache.models import CompositeArtifact

            composite = CompositeArtifact(
                id=composite_id,
                collection_id=collection_id,
                composite_type="skill",
                display_name=display_name,
                description=description,
                metadata_json=metadata,
            )
            session.add(composite)
            session.flush()
            session.refresh(composite)
            result = self._repo._composite_to_dict(composite)

        logger.info(
            "create_skill_composite: created CompositeArtifact id=%s type=skill "
            "collection=%s",
            composite_id,
            collection_id,
        )
        return result

    def update_composite(
        self,
        composite_id: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        composite_type: Optional[str] = None,
    ) -> "CompositeRecord":
        """Update mutable fields on an existing CompositeArtifact.

        Args:
            composite_id: ``type:name`` primary key of the composite to update.
            display_name: New display name, or ``None`` to leave unchanged.
            description: New description, or ``None`` to leave unchanged.
            composite_type: New composite type, or ``None`` to leave unchanged.

        Returns:
            Updated ``CompositeRecord`` dict.

        Raises:
            NotFoundError: When no composite with ``composite_id`` exists.
        """
        logger.info(
            "update_composite: id=%s display_name=%r description=%r type=%r",
            composite_id,
            display_name,
            description,
            composite_type,
        )

        return self._repo.update_composite(
            composite_id=composite_id,
            display_name=display_name,
            description=description,
            composite_type=composite_type,
        )

    def delete_composite(
        self,
        composite_id: str,
        cascade_delete_children: bool = False,
    ) -> bool:
        """Delete a CompositeArtifact and optionally its child Artifacts.

        The membership rows are always removed via the ``ON DELETE CASCADE``
        constraint on ``composite_memberships.composite_id``.  When
        ``cascade_delete_children=True`` the child ``Artifact`` rows themselves
        are also deleted.

        Args:
            composite_id: ``type:name`` primary key of the composite to delete.
            cascade_delete_children: When ``True``, also delete child Artifact
                rows.  Defaults to ``False``.

        Returns:
            ``True`` if the composite was found and deleted; ``False`` when no
            composite with ``composite_id`` existed.
        """
        logger.info(
            "delete_composite: id=%s cascade_children=%s",
            composite_id,
            cascade_delete_children,
        )

        return self._repo.delete_composite(
            composite_id=composite_id,
            cascade_delete_children=cascade_delete_children,
        )

    def get_composite(
        self,
        composite_id: str,
    ) -> Optional["CompositeRecord"]:
        """Fetch a single CompositeArtifact by its ``type:name`` id.

        Args:
            composite_id: ``type:name`` primary key.

        Returns:
            ``CompositeRecord`` dict, or ``None`` when not found.
        """
        return self._repo.get_composite(composite_id=composite_id)

    def list_composites(
        self,
        collection_id: str,
    ) -> List["CompositeRecord"]:
        """Return all CompositeArtifacts for a collection.

        Args:
            collection_id: Owning collection identifier.

        Returns:
            List of ``CompositeRecord`` dicts, ordered by ``id``.
        """
        return self._repo.list_composites(collection_id=collection_id)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_associations(
        self, artifact_type_name: str, collection_id: str
    ) -> AssociationResult:
        """Return parent and child associations for an artifact.

        Delegates directly to
        ``CompositeMembershipRepository.get_associations()``.  No UUID
        resolution is required here because the repository handles the
        ``type:name`` → UUID lookup internally for the parents query.

        Args:
            artifact_type_name: ``type:name`` primary key
                (e.g. ``"composite:my-plugin"`` or ``"skill:canvas"``).
            collection_id: Owning collection identifier.

        Returns:
            :data:`AssociationResult` with two keys:

            .. code-block:: python

                {
                    "parents": [MembershipRecord, ...],
                    "children": [MembershipRecord, ...],
                }

            Both lists are empty when the artifact has no associations in the
            requested collection.

        Example:
            >>> svc.get_associations("composite:my-plugin", "col-abc")
            {"parents": [], "children": [{...}, ...]}
        """
        return self._repo.get_associations(artifact_type_name, collection_id)
