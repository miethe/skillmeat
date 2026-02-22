"""Repository CRUD operations for CompositeArtifact and CompositeMembership.

This module provides the ``CompositeMembershipRepository`` class, which handles
all data-access operations for the composite-artifact infrastructure introduced
in ``composite-artifact-infrastructure-v1``.

Design notes
------------
- All public methods return plain dicts (DTO boundary) — raw ORM objects never
  leave this module.  Callers receive serialisable data so they are decoupled
  from SQLAlchemy object lifecycle.
- ``selectinload`` / ``joinedload`` hints are applied where relationships are
  needed to avoid N+1 round-trips.
- ``IntegrityError`` from SQLAlchemy is caught and re-raised as the domain
  ``ConstraintError`` so callers never need to import SQLAlchemy exceptions.
- Session management follows the pattern established in
  ``skillmeat/cache/repositories.py`` (``BaseRepository``):
  ``_get_session()`` for read-only convenience and ``transaction()`` context
  manager for writes.

Usage
-----
>>> from skillmeat.cache.composite_repository import CompositeMembershipRepository
>>>
>>> repo = CompositeMembershipRepository()
>>>
>>> # List child memberships of a composite
>>> children = repo.get_children_of("composite:my-plugin", "collection-abc")
>>>
>>> # Add a new membership
>>> record = repo.create_membership(
...     collection_id="collection-abc",
...     composite_id="composite:my-plugin",
...     child_artifact_uuid="a1b2c3d4...",
...     relationship_type="contains",
...     pinned_version_hash=None,
... )
>>>
>>> # Reverse lookup — all composites containing a child
>>> parents = repo.get_parents_of("a1b2c3d4...", "collection-abc")
>>>
>>> # Combined association view
>>> assocs = repo.get_associations("skill:canvas", "collection-abc")
>>> # assocs == {"parents": [...], "children": [...]}
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from skillmeat.cache.models import (
    Artifact,
    CompositeArtifact,
    CompositeMembership,
    create_db_engine,
    create_tables,
)
from skillmeat.cache.repositories import ConstraintError, NotFoundError

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DTO type aliases
# ---------------------------------------------------------------------------
MembershipRecord = Dict[str, Any]
"""A plain dict describing one membership edge (``CompositeMembership`` row)."""

CompositeRecord = Dict[str, Any]
"""A plain dict describing one composite artifact (``CompositeArtifact`` row)."""


# ---------------------------------------------------------------------------
# Repository class
# ---------------------------------------------------------------------------


class CompositeMembershipRepository:
    """Data-access layer for CompositeMembership records.

    All public methods return plain dicts (``MembershipRecord``) and never
    expose raw SQLAlchemy ORM objects to callers.

    Attributes:
        db_path: Path to the SQLite cache database file.
        engine: SQLAlchemy engine created for ``db_path``.

    Example:
        >>> repo = CompositeMembershipRepository()
        >>> repo.get_children_of("composite:my-plugin", "collection-abc")
        [{"composite_id": "composite:my-plugin", ...}, ...]
    """

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        """Initialise the repository with a database path.

        Args:
            db_path: Optional path to the SQLite database file.  Defaults to
                ``~/.skillmeat/cache/cache.db`` when omitted.
        """
        if db_path is None:
            self.db_path = Path.home() / ".skillmeat" / "cache" / "cache.db"
        else:
            self.db_path = Path(db_path)

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_db_engine(self.db_path)

        # Run Alembic migrations then create any missing base tables
        from skillmeat.cache.migrations import run_migrations

        run_migrations(self.db_path)
        create_tables(self.db_path)

        logger.debug(
            "Initialised CompositeMembershipRepository with database: %s", self.db_path
        )

    # ------------------------------------------------------------------
    # Session helpers (mirrors BaseRepository pattern)
    # ------------------------------------------------------------------

    def _get_session(self) -> Session:
        """Create a new database session (caller is responsible for closing).

        Returns:
            A fresh ``Session`` bound to this repository's engine.
        """
        from sqlalchemy.orm import sessionmaker

        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        return SessionLocal()

    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """Context manager for transactional writes.

        Commits on success, rolls back on any exception, and always closes
        the session.

        Yields:
            Active ``Session`` for the duration of the block.

        Raises:
            ConstraintError: Re-raised from ``IntegrityError`` for domain callers.
        """
        session = self._get_session()
        try:
            yield session
            session.commit()
            logger.debug("Transaction committed successfully")
        except ConstraintError:
            session.rollback()
            raise
        except IntegrityError as exc:
            session.rollback()
            logger.warning("Integrity constraint violated: %s", exc)
            raise ConstraintError(f"Database constraint violation: {exc}") from exc
        except Exception as exc:
            session.rollback()
            logger.error("Transaction rolled back due to error: %s", exc)
            raise
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _membership_to_dict(membership: CompositeMembership) -> MembershipRecord:
        """Convert a ``CompositeMembership`` ORM row to a plain dict.

        Uses ``CompositeMembership.to_dict()`` for consistency with the model's
        own serialisation logic.

        Args:
            membership: Loaded ORM instance.

        Returns:
            Plain dictionary safe to return to callers.
        """
        return membership.to_dict()

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_children_of(
        self, composite_id: str, collection_id: str
    ) -> List[MembershipRecord]:
        """Return all membership records where ``composite_id`` is the parent.

        Eager-loads the ``child_artifact`` relationship to avoid N+1 queries
        when callers need the child's ``type:name`` id.

        Args:
            composite_id: ``type:name`` identifier of the composite artifact
                (e.g. ``"composite:my-plugin"``).
            collection_id: Owning collection identifier.

        Returns:
            List of membership dicts, each including a ``"child_artifact"``
            summary sub-dict.  Empty list when no memberships exist.

        Example:
            >>> repo.get_children_of("composite:my-plugin", "col-abc")
            [{"composite_id": "composite:my-plugin", "child_artifact_uuid": "...", ...}]
        """
        session = self._get_session()
        try:
            rows = (
                session.query(CompositeMembership)
                .options(joinedload(CompositeMembership.child_artifact))
                .filter(
                    CompositeMembership.composite_id == composite_id,
                    CompositeMembership.collection_id == collection_id,
                )
                .all()
            )
            return [self._membership_to_dict(r) for r in rows]
        finally:
            session.close()

    def get_parents_of(
        self, child_artifact_uuid: str, collection_id: str
    ) -> List[MembershipRecord]:
        """Return all membership records where the given UUID is the child.

        Provides the reverse lookup — "which composites contain this artifact?"
        Eager-loads the ``composite`` relationship so callers can inspect
        parent metadata without additional queries.

        Args:
            child_artifact_uuid: Stable UUID of the child artifact (hex string,
                32 chars, as stored in ``artifacts.uuid``).
            collection_id: Owning collection identifier.

        Returns:
            List of membership dicts ordered by ``composite_id``.  Empty list
            when the artifact is not a member of any composite.

        Example:
            >>> repo.get_parents_of("a1b2c3d4e5f6...", "col-abc")
            [{"composite_id": "composite:my-plugin", ...}]
        """
        session = self._get_session()
        try:
            rows = (
                session.query(CompositeMembership)
                .options(joinedload(CompositeMembership.composite))
                .filter(
                    CompositeMembership.child_artifact_uuid == child_artifact_uuid,
                    CompositeMembership.collection_id == collection_id,
                )
                .order_by(CompositeMembership.composite_id)
                .all()
            )
            return [self._membership_to_dict(r) for r in rows]
        finally:
            session.close()

    def get_associations(
        self, artifact_id: str, collection_id: str
    ) -> Dict[str, List[MembershipRecord]]:
        """Return both parent and child associations for a ``type:name`` artifact.

        Looks up the artifact's UUID from the ``artifacts`` table (using the
        ``type:name`` primary key), then queries:
        - ``parents``: composites that contain this artifact as a child.
        - ``children``: artifacts that this composite contains (only populated
          when ``artifact_id`` refers to a composite).

        Args:
            artifact_id: ``type:name`` primary key (e.g. ``"skill:canvas"``).
            collection_id: Owning collection identifier.

        Returns:
            Dictionary with two keys:

            .. code-block:: python

                {
                    "parents": [MembershipRecord, ...],  # composites containing this
                    "children": [MembershipRecord, ...], # children of this composite
                }

            Both lists may be empty.

        Note:
            When ``artifact_id`` is not found in the ``artifacts`` table the
            method returns ``{"parents": [], "children": []}`` (no UUID means
            no memberships).

        Example:
            >>> repo.get_associations("composite:my-plugin", "col-abc")
            {"parents": [], "children": [{...}, ...]}
        """
        session = self._get_session()
        try:
            # Resolve artifact_id → uuid for parent lookup
            artifact = (
                session.query(Artifact).filter(Artifact.id == artifact_id).first()
            )
            parents: List[MembershipRecord] = []
            if artifact is not None:
                parent_rows = (
                    session.query(CompositeMembership)
                    .options(joinedload(CompositeMembership.composite))
                    .filter(
                        CompositeMembership.child_artifact_uuid == artifact.uuid,
                        CompositeMembership.collection_id == collection_id,
                    )
                    .order_by(CompositeMembership.composite_id)
                    .all()
                )
                parents = [self._membership_to_dict(r) for r in parent_rows]

            # Children: this artifact as parent composite
            child_rows = (
                session.query(CompositeMembership)
                .options(joinedload(CompositeMembership.child_artifact))
                .filter(
                    CompositeMembership.composite_id == artifact_id,
                    CompositeMembership.collection_id == collection_id,
                )
                .all()
            )
            children = [self._membership_to_dict(r) for r in child_rows]

            return {"parents": parents, "children": children}
        finally:
            session.close()

    def get_skill_composite_children(
        self, skill_artifact_uuid: str, collection_id: str
    ) -> List[MembershipRecord]:
        """Return membership rows for the skill-type composite that wraps a skill artifact.

        Skill artifacts can be wrapped as a ``CompositeArtifact`` of
        ``composite_type='skill'`` whose ``metadata_json`` stores the
        originating skill's UUID as ``{"artifact_uuid": "<skill-uuid>"}``.
        This method performs the lookup and returns the composite's children.

        Args:
            skill_artifact_uuid: Stable UUID of the skill ``Artifact`` row.
            collection_id: Owning collection identifier.

        Returns:
            List of membership dicts for the companion composite's children.
            Empty list when no companion composite exists or when it has no
            members.

        Example:
            >>> repo.get_skill_composite_children("a1b2c3d4...", "col-abc")
            [{"composite_id": "composite:my-skill", "child_artifact_uuid": "...", ...}]
        """
        import json as _json  # noqa: PLC0415

        session = self._get_session()
        try:
            # Find the CompositeArtifact whose metadata_json encodes this
            # skill's UUID as the originating artifact.
            target_json = _json.dumps({"artifact_uuid": skill_artifact_uuid})
            composite = (
                session.query(CompositeArtifact)
                .filter(
                    CompositeArtifact.composite_type == "skill",
                    CompositeArtifact.collection_id == collection_id,
                    CompositeArtifact.metadata_json == target_json,
                )
                .first()
            )
            if composite is None:
                return []

            rows = (
                session.query(CompositeMembership)
                .options(joinedload(CompositeMembership.child_artifact))
                .filter(
                    CompositeMembership.composite_id == composite.id,
                    CompositeMembership.collection_id == collection_id,
                )
                .all()
            )
            return [self._membership_to_dict(r) for r in rows]
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def create_membership(
        self,
        collection_id: str,
        composite_id: str,
        child_artifact_uuid: str,
        relationship_type: str = "contains",
        pinned_version_hash: Optional[str] = None,
    ) -> MembershipRecord:
        """Insert a new membership edge between a composite and a child artifact.

        The triplet ``(collection_id, composite_id, child_artifact_uuid)`` must
        be unique — a duplicate insert raises ``ConstraintError``.

        Args:
            collection_id: Owning collection identifier.
            composite_id: ``type:name`` id of the parent composite.
            child_artifact_uuid: Stable UUID of the child artifact.
            relationship_type: Semantic edge label, default ``"contains"``.
            pinned_version_hash: Optional content hash to pin the child; pass
                ``None`` to track latest.

        Returns:
            ``MembershipRecord`` dict for the newly created membership.

        Raises:
            ConstraintError: When the membership already exists or a foreign-key
                constraint is violated (e.g. unknown ``composite_id`` or
                ``child_artifact_uuid``).

        Example:
            >>> repo.create_membership(
            ...     "col-abc", "composite:my-plugin", "a1b2c3d4...",
            ... )
            {"collection_id": "col-abc", "composite_id": "composite:my-plugin", ...}
        """
        with self.transaction() as session:
            membership = CompositeMembership(
                collection_id=collection_id,
                composite_id=composite_id,
                child_artifact_uuid=child_artifact_uuid,
                relationship_type=relationship_type,
                pinned_version_hash=pinned_version_hash,
            )
            session.add(membership)
            # Flush so that the child_artifact relationship can be loaded
            session.flush()

            # Eagerly load child_artifact before the session closes
            session.refresh(membership)
            child = (
                session.query(Artifact)
                .filter(Artifact.uuid == child_artifact_uuid)
                .first()
            )
            # Attach manually so to_dict() can include child summary
            membership.child_artifact = child

            result = self._membership_to_dict(membership)
            logger.info(
                "Created CompositeMembership: composite=%s child_uuid=%s collection=%s",
                composite_id,
                child_artifact_uuid,
                collection_id,
            )
            return result

    def delete_membership(self, composite_id: str, child_artifact_uuid: str) -> bool:
        """Delete a specific membership edge.

        The ``collection_id`` is intentionally omitted from the delete key
        because ``(composite_id, child_artifact_uuid)`` already uniquely
        identifies the edge within the composite table (collection_id is part
        of the composite PK but composites are scoped to one collection).

        Args:
            composite_id: ``type:name`` id of the parent composite.
            child_artifact_uuid: Stable UUID of the child artifact.

        Returns:
            ``True`` if a row was deleted, ``False`` if no matching row existed.

        Example:
            >>> repo.delete_membership("composite:my-plugin", "a1b2c3d4...")
            True
        """
        with self.transaction() as session:
            deleted_count = (
                session.query(CompositeMembership)
                .filter(
                    CompositeMembership.composite_id == composite_id,
                    CompositeMembership.child_artifact_uuid == child_artifact_uuid,
                )
                .delete(synchronize_session=False)
            )
            if deleted_count:
                logger.info(
                    "Deleted CompositeMembership: composite=%s child_uuid=%s",
                    composite_id,
                    child_artifact_uuid,
                )
            else:
                logger.debug(
                    "delete_membership: no row found for composite=%s child_uuid=%s",
                    composite_id,
                    child_artifact_uuid,
                )
            return deleted_count > 0

    # ------------------------------------------------------------------
    # CompositeArtifact CRUD operations
    # ------------------------------------------------------------------

    @staticmethod
    def _composite_to_dict(composite: CompositeArtifact) -> CompositeRecord:
        """Convert a ``CompositeArtifact`` ORM row to a plain dict.

        Args:
            composite: Loaded ORM instance.

        Returns:
            Plain dictionary safe to return to callers.
        """
        return composite.to_dict()

    def get_composite(self, composite_id: str) -> Optional[CompositeRecord]:
        """Fetch a single CompositeArtifact by its ``type:name`` primary key.

        Args:
            composite_id: ``type:name`` primary key (e.g. ``"composite:my-plugin"``).

        Returns:
            ``CompositeRecord`` dict, or ``None`` when not found.

        Example:
            >>> repo.get_composite("composite:my-plugin")
            {"id": "composite:my-plugin", "composite_type": "plugin", ...}
        """
        session = self._get_session()
        try:
            composite = (
                session.query(CompositeArtifact)
                .filter(CompositeArtifact.id == composite_id)
                .first()
            )
            if composite is None:
                return None
            return self._composite_to_dict(composite)
        finally:
            session.close()

    def list_composites(self, collection_id: str) -> List[CompositeRecord]:
        """Return all CompositeArtifacts for a collection, ordered by id.

        Args:
            collection_id: Owning collection identifier.

        Returns:
            List of ``CompositeRecord`` dicts ordered by ``id``.

        Example:
            >>> repo.list_composites("col-abc")
            [{"id": "composite:my-plugin", ...}, ...]
        """
        session = self._get_session()
        try:
            rows = (
                session.query(CompositeArtifact)
                .filter(CompositeArtifact.collection_id == collection_id)
                .order_by(CompositeArtifact.id)
                .all()
            )
            return [self._composite_to_dict(r) for r in rows]
        finally:
            session.close()

    def create_composite(
        self,
        collection_id: str,
        composite_id: str,
        composite_type: str = "plugin",
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        initial_member_uuids: Optional[List[str]] = None,
        pinned_version_hash: Optional[str] = None,
    ) -> CompositeRecord:
        """Create a new ``CompositeArtifact`` row, optionally with member edges.

        Args:
            collection_id: Owning collection identifier.
            composite_id: ``type:name`` primary key for the new composite.
            composite_type: Variant classifier — ``"plugin"``, ``"stack"``,
                or ``"suite"``.  Defaults to ``"plugin"``.
            display_name: Optional human-readable label.
            description: Optional free-text description.
            initial_member_uuids: Optional list of stable artifact UUIDs to
                add as membership edges immediately.
            pinned_version_hash: Optional version pin applied to every initial
                membership edge.

        Returns:
            ``CompositeRecord`` dict for the newly created composite, including
            its initial ``memberships`` list.

        Raises:
            ConstraintError: When a composite with ``composite_id`` already
                exists (UNIQUE/PK violation).

        Note:
            **Transaction boundary**: the ``CompositeArtifact`` row and ALL
            ``CompositeMembership`` edges are created inside a single
            ``self.transaction()`` block.  Any failure — including an FK
            violation on a child UUID or a duplicate-composite constraint — will
            roll back the entire unit of work, leaving no orphaned composite
            rows or dangling membership edges.  UUID pre-validation in
            ``CompositeService.create_composite()`` ensures unknown member
            ``type:name`` ids are rejected before the transaction even opens.
        """
        with self.transaction() as session:
            composite = CompositeArtifact(
                id=composite_id,
                collection_id=collection_id,
                composite_type=composite_type,
                display_name=display_name,
                description=description,
            )
            session.add(composite)
            session.flush()

            for child_uuid in initial_member_uuids or []:
                membership = CompositeMembership(
                    collection_id=collection_id,
                    composite_id=composite_id,
                    child_artifact_uuid=child_uuid,
                    relationship_type="contains",
                    pinned_version_hash=pinned_version_hash,
                )
                session.add(membership)

            session.flush()
            session.refresh(composite)
            result = self._composite_to_dict(composite)
            logger.info(
                "Created CompositeArtifact: id=%s type=%s collection=%s members=%d",
                composite_id,
                composite_type,
                collection_id,
                len(initial_member_uuids or []),
            )
            return result

    def update_composite(
        self,
        composite_id: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        composite_type: Optional[str] = None,
    ) -> CompositeRecord:
        """Update mutable fields on an existing ``CompositeArtifact``.

        Only fields whose argument is not ``None`` are updated, allowing
        callers to perform partial updates.

        Args:
            composite_id: ``type:name`` primary key of the composite.
            display_name: New display name (``None`` = leave unchanged).
            description: New description (``None`` = leave unchanged).
            composite_type: New composite type (``None`` = leave unchanged).

        Returns:
            Updated ``CompositeRecord`` dict.

        Raises:
            NotFoundError: When no row with ``composite_id`` exists.
        """
        with self.transaction() as session:
            composite = (
                session.query(CompositeArtifact)
                .filter(CompositeArtifact.id == composite_id)
                .first()
            )
            if composite is None:
                raise NotFoundError(f"CompositeArtifact not found: {composite_id!r}")

            if display_name is not None:
                composite.display_name = display_name
            if description is not None:
                composite.description = description
            if composite_type is not None:
                composite.composite_type = composite_type

            session.flush()
            session.refresh(composite)
            result = self._composite_to_dict(composite)
            logger.info("Updated CompositeArtifact: id=%s", composite_id)
            return result

    def delete_composite(
        self,
        composite_id: str,
        cascade_delete_children: bool = False,
    ) -> bool:
        """Delete a ``CompositeArtifact`` and optionally its child Artifact rows.

        Membership rows are removed automatically via ``ON DELETE CASCADE`` on
        ``composite_memberships.composite_id``.  When
        ``cascade_delete_children=True`` the service additionally deletes the
        ``Artifact`` rows referenced by the memberships.

        Args:
            composite_id: ``type:name`` primary key to delete.
            cascade_delete_children: When ``True``, also hard-delete the child
                ``Artifact`` rows.  Defaults to ``False``.

        Returns:
            ``True`` if a row was deleted; ``False`` if not found.
        """
        with self.transaction() as session:
            composite = (
                session.query(CompositeArtifact)
                .filter(CompositeArtifact.id == composite_id)
                .first()
            )
            if composite is None:
                logger.debug(
                    "delete_composite: no composite found for id=%s",
                    composite_id,
                )
                return False

            # Collect child UUIDs before cascade removes memberships
            child_uuids: List[str] = [
                m.child_artifact_uuid for m in composite.memberships
            ]

            session.delete(composite)

            if cascade_delete_children and child_uuids:
                session.query(Artifact).filter(Artifact.uuid.in_(child_uuids)).delete(
                    synchronize_session=False
                )
                logger.info(
                    "delete_composite: also deleted %d child Artifact rows",
                    len(child_uuids),
                )

            logger.info(
                "Deleted CompositeArtifact: id=%s cascade=%s",
                composite_id,
                cascade_delete_children,
            )
            return True

    def reorder_members(
        self,
        composite_id: str,
        reorder: List[Dict[str, Any]],
    ) -> List[MembershipRecord]:
        """Update the ``position`` field on membership edges in bulk.

        Each entry in ``reorder`` must be a dict with:
        - ``"child_artifact_uuid"``: Stable artifact UUID.
        - ``"position"``: New integer position (0-based).

        Args:
            composite_id: ``type:name`` id of the parent composite.
            reorder: List of ``{"child_artifact_uuid": str, "position": int}``
                dicts.

        Returns:
            Updated list of ``MembershipRecord`` dicts for the composite,
            ordered by the new positions.
        """
        with self.transaction() as session:
            for item in reorder:
                updated = (
                    session.query(CompositeMembership)
                    .filter(
                        CompositeMembership.composite_id == composite_id,
                        CompositeMembership.child_artifact_uuid
                        == item["child_artifact_uuid"],
                    )
                    .first()
                )
                if updated is not None:
                    updated.position = item["position"]

            session.flush()
            # Re-query ordered results
            rows = (
                session.query(CompositeMembership)
                .filter(CompositeMembership.composite_id == composite_id)
                .order_by(CompositeMembership.position.asc().nullslast())
                .all()
            )
            logger.info(
                "reorder_members: updated %d positions for composite=%s",
                len(reorder),
                composite_id,
            )
            return [self._membership_to_dict(r) for r in rows]
