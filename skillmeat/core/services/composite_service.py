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

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from skillmeat.cache.composite_repository import (
    CompositeMembershipRepository,
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
