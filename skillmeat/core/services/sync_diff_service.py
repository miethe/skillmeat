"""Sync diff service for per-member version comparison rows.

This module provides logic to compute hierarchical version comparison rows for
skill artifacts and their embedded members.  The primary consumer is the sync
status UI (TASK-7.1) which needs a flat list of rows where the parent skill
appears first, followed by one row per ``CompositeMembership`` child.

Row structure
-------------
Each ``VersionComparisonRow`` carries three version strings:

``source_version``
    The ``resolved_version`` stored in ``CollectionArtifact`` — the version
    last resolved from the upstream source (e.g. GitHub tag or SHA).  This
    is ``None`` when the artifact was never imported from a remote source or
    when the collection has no record for it.

``collection_version``
    The ``version`` column of ``CollectionArtifact`` — what the collection
    currently tracks.  Typically a human-readable semver or ``"latest"``.

``deployed_version``
    The ``deployed_version`` column of the ``Artifact`` row in the *project*
    table.  ``None`` when the artifact has never been deployed to the project.

Parent/child linkage
--------------------
``parent_artifact_id`` is ``None`` for the skill row (top-level) and set to
the skill's ``type:name`` identifier string for every member row so callers
can group/sort the flat list.

``is_member``
    Convenience flag: ``False`` on the skill row, ``True`` on member rows.

No N+1 queries
--------------
Member version data is fetched in a single batch query that joins
``composite_memberships`` → ``artifacts`` → ``collection_artifacts`` for all
children of the companion composite in one round-trip.

Usage
-----
>>> from skillmeat.core.services.sync_diff_service import compute_skill_sync_diff
>>>
>>> rows = compute_skill_sync_diff(
...     artifact_id="skill:my-skill",          # type:name
...     collection_id="my-collection",
...     project_id="proj-abc",                 # for deployed_version lookup
...     db_path="/path/to/cache.db",
... )
>>> # skill with 3 members → 4 rows
>>> len(rows)
4
>>> rows[0].is_member
False
>>> rows[1].is_member
True
>>> rows[1].parent_artifact_id
'skill:my-skill'
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.models import (
    Artifact,
    CollectionArtifact,
    CompositeArtifact,
    CompositeMembership,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public data model
# ---------------------------------------------------------------------------


@dataclass
class VersionComparisonRow:
    """One row in the hierarchical sync diff output.

    Attributes:
        artifact_id: ``type:name`` identifier of this artifact.
        artifact_name: Short name portion (after the colon).
        artifact_type: Type portion (before the colon, e.g. ``"skill"``).
        source_version: Version resolved from upstream source.  ``None``
            when no upstream record exists.
        collection_version: Version currently tracked in the collection.
            ``None`` when the artifact is not in the collection.
        deployed_version: Version deployed to the project.  ``None`` when
            not deployed.
        is_member: ``True`` for child/member rows, ``False`` for the parent.
        parent_artifact_id: ``type:name`` of the parent skill; ``None`` for
            the top-level skill row itself.
    """

    artifact_id: str
    artifact_name: str
    artifact_type: str
    source_version: Optional[str] = field(default=None)
    collection_version: Optional[str] = field(default=None)
    deployed_version: Optional[str] = field(default=None)
    is_member: bool = field(default=False)
    parent_artifact_id: Optional[str] = field(default=None)


# ---------------------------------------------------------------------------
# Internal helpers — all operate on an already-open Session
# ---------------------------------------------------------------------------


def _resolve_artifact_row(session: Session, artifact_id: str) -> Optional[Artifact]:
    """Return the ``Artifact`` row for *artifact_id* (``type:name``)."""
    return (
        session.query(Artifact)
        .filter(Artifact.id == artifact_id)
        .first()
    )


def _collection_artifact_versions(
    session: Session,
    artifact_uuid: str,
    collection_id: str,
) -> tuple[Optional[str], Optional[str]]:
    """Return ``(collection_version, source_version)`` for one artifact UUID.

    Args:
        session: Active SQLAlchemy session.
        artifact_uuid: Stable UUID of the artifact.
        collection_id: Owning collection identifier.

    Returns:
        ``(version, resolved_version)`` tuple; both ``None`` when no
        ``CollectionArtifact`` row exists.
    """
    ca = (
        session.query(CollectionArtifact)
        .filter(
            CollectionArtifact.artifact_uuid == artifact_uuid,
            CollectionArtifact.collection_id == collection_id,
        )
        .first()
    )
    if ca is None:
        return None, None
    return ca.version, ca.resolved_version


def _batch_member_versions(
    session: Session,
    member_uuids: Sequence[str],
    collection_id: str,
    project_id: str,
) -> dict[str, dict]:
    """Batch-fetch version data for a list of member artifact UUIDs.

    Performs two IN-queries (no N+1):
    1. ``artifacts`` table filtered by project_id → deployed_version
    2. ``collection_artifacts`` table filtered by collection_id → version fields

    Args:
        session: Active SQLAlchemy session.
        member_uuids: UUIDs of the child artifacts to look up.
        collection_id: Collection to query ``collection_artifacts`` against.
        project_id: Project whose ``Artifact`` rows supply ``deployed_version``.

    Returns:
        ``{artifact_uuid: {"artifact": Artifact|None, "collection_version": str|None,
        "source_version": str|None, "deployed_version": str|None}}``
    """
    if not member_uuids:
        return {}

    # Query 1: Artifact rows in the target project (for deployed_version, id, name, type)
    artifact_rows: list[Artifact] = (
        session.query(Artifact)
        .filter(
            Artifact.uuid.in_(member_uuids),
            Artifact.project_id == project_id,
        )
        .all()
    )
    art_by_uuid: dict[str, Artifact] = {a.uuid: a for a in artifact_rows}

    # Query 2: CollectionArtifact rows (for collection_version and source_version)
    ca_rows: list[CollectionArtifact] = (
        session.query(CollectionArtifact)
        .filter(
            CollectionArtifact.artifact_uuid.in_(member_uuids),
            CollectionArtifact.collection_id == collection_id,
        )
        .all()
    )
    ca_by_uuid: dict[str, CollectionArtifact] = {
        ca.artifact_uuid: ca for ca in ca_rows
    }

    result: dict[str, dict] = {}
    for uid in member_uuids:
        art = art_by_uuid.get(uid)
        ca = ca_by_uuid.get(uid)
        result[uid] = {
            "artifact": art,
            "collection_version": ca.version if ca else None,
            "source_version": ca.resolved_version if ca else None,
            "deployed_version": art.deployed_version if art else None,
        }
    return result


def _find_skill_composite(
    session: Session,
    skill_uuid: str,
    collection_id: str,
) -> Optional[CompositeArtifact]:
    """Return the companion ``CompositeArtifact`` for a skill UUID.

    Skills with embedded members are stored as a ``CompositeArtifact`` of
    ``composite_type='skill'`` whose ``metadata_json`` is
    ``{"artifact_uuid": "<skill-uuid>"}``.

    Args:
        session: Active SQLAlchemy session.
        skill_uuid: Stable UUID of the parent skill artifact.
        collection_id: Owning collection identifier.

    Returns:
        The companion ``CompositeArtifact`` row, or ``None`` if no companion
        exists (i.e. the skill has no embedded members).
    """
    target_json = json.dumps({"artifact_uuid": skill_uuid})
    return (
        session.query(CompositeArtifact)
        .filter(
            CompositeArtifact.composite_type == "skill",
            CompositeArtifact.collection_id == collection_id,
            CompositeArtifact.metadata_json == target_json,
        )
        .first()
    )


def _get_composite_member_uuids(
    session: Session,
    composite_id: str,
    collection_id: str,
) -> list[str]:
    """Return child artifact UUIDs for a composite, ordered by position.

    Args:
        session: Active SQLAlchemy session.
        composite_id: ``type:name`` id of the parent composite.
        collection_id: Owning collection identifier.

    Returns:
        Ordered list of child ``artifact_uuid`` strings.
    """
    rows: list[CompositeMembership] = (
        session.query(CompositeMembership)
        .filter(
            CompositeMembership.composite_id == composite_id,
            CompositeMembership.collection_id == collection_id,
        )
        .order_by(CompositeMembership.position)
        .all()
    )
    return [r.child_artifact_uuid for r in rows]


def _make_session_from_db_path(db_path: str) -> Session:
    """Create a SQLAlchemy session for *db_path*, running migrations first.

    This follows the same pattern as ``CompositeMembershipRepository.__init__``:
    it calls ``run_migrations`` then ``create_tables`` before opening a session.

    Args:
        db_path: Absolute path to the SQLite cache database.

    Returns:
        Open ``Session`` bound to a fresh engine.  Caller must close it.
    """
    from skillmeat.cache.models import create_db_engine, create_tables  # noqa: PLC0415
    from skillmeat.cache.migrations import run_migrations  # noqa: PLC0415

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    run_migrations(path)
    create_tables(path)

    engine = create_db_engine(path)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_skill_sync_diff(
    artifact_id: str,
    collection_id: str,
    project_id: str,
    db_path: str,
    *,
    _session: Optional[Session] = None,
) -> list[VersionComparisonRow]:
    """Compute hierarchical version comparison rows for a skill and its members.

    The returned list always starts with the skill row itself (``is_member=False``)
    followed by zero or more member rows (``is_member=True``), one per
    ``CompositeMembership`` child.  Non-skill artifacts (i.e. skills without a
    companion composite or composites with no members) produce a single-element
    list containing only the parent row.

    Args:
        artifact_id: ``type:name`` identifier of the skill (e.g.
            ``"skill:frontend-design"``).
        collection_id: Collection identifier used to resolve
            ``CollectionArtifact`` rows.
        project_id: Project identifier used to resolve ``Artifact.deployed_version``.
        db_path: Absolute path to the SQLite cache database file.
        _session: Optional pre-opened Session for testing (bypasses
            migration/engine creation when provided).

    Returns:
        Ordered list of ``VersionComparisonRow`` objects:
        - Index 0: parent skill row
        - Index 1+: member rows, each with ``parent_artifact_id == artifact_id``

    Raises:
        ValueError: If *artifact_id* is not found in the artifacts table.
    """
    # Allow callers (tests) to inject a session directly.
    managed_session = _session is None
    session = _session if _session is not None else _make_session_from_db_path(db_path)

    try:
        # ------------------------------------------------------------------
        # 1. Resolve the skill artifact row
        # ------------------------------------------------------------------
        skill_artifact = _resolve_artifact_row(session, artifact_id)
        if skill_artifact is None:
            raise ValueError(
                f"Artifact not found in cache: {artifact_id!r}. "
                "Ensure the cache has been populated before calling compute_skill_sync_diff()."
            )

        skill_uuid = skill_artifact.uuid

        # ------------------------------------------------------------------
        # 2. Fetch collection-side version data for the parent skill
        # ------------------------------------------------------------------
        collection_ver, source_ver = _collection_artifact_versions(
            session, skill_uuid, collection_id
        )

        # ------------------------------------------------------------------
        # 3. Build the parent row
        # ------------------------------------------------------------------
        parent_row = VersionComparisonRow(
            artifact_id=artifact_id,
            artifact_name=skill_artifact.name,
            artifact_type=skill_artifact.type,
            source_version=source_ver,
            collection_version=collection_ver,
            deployed_version=skill_artifact.deployed_version,
            is_member=False,
            parent_artifact_id=None,
        )

        rows: list[VersionComparisonRow] = [parent_row]

        # ------------------------------------------------------------------
        # 4. Find the companion composite (if any)
        # ------------------------------------------------------------------
        composite = _find_skill_composite(session, skill_uuid, collection_id)
        if composite is None:
            logger.debug(
                "No companion composite found for skill %s — returning single row",
                artifact_id,
            )
            return rows

        # ------------------------------------------------------------------
        # 5. Get ordered member UUIDs
        # ------------------------------------------------------------------
        member_uuids = _get_composite_member_uuids(
            session, composite.id, collection_id
        )
        if not member_uuids:
            logger.debug(
                "Companion composite %s has no members — returning single row",
                composite.id,
            )
            return rows

        # ------------------------------------------------------------------
        # 6. Batch-fetch member version data (no N+1)
        # ------------------------------------------------------------------
        member_data = _batch_member_versions(
            session, member_uuids, collection_id, project_id
        )

        # ------------------------------------------------------------------
        # 7. Build member rows in composite order
        # ------------------------------------------------------------------
        for uid in member_uuids:
            data = member_data.get(uid, {})
            art: Optional[Artifact] = data.get("artifact")

            if art is not None:
                member_artifact_id = art.id
                member_name = art.name
                member_type = art.type
            else:
                # Artifact row absent from the target project — still emit a
                # row with a placeholder id so the UI can display "not deployed"
                # state without crashing.
                logger.debug(
                    "Member artifact UUID %s not found in project %s — "
                    "emitting row with unknown id",
                    uid,
                    project_id,
                )
                member_artifact_id = f"unknown:{uid}"
                member_name = uid
                member_type = "unknown"

            rows.append(
                VersionComparisonRow(
                    artifact_id=member_artifact_id,
                    artifact_name=member_name,
                    artifact_type=member_type,
                    source_version=data.get("source_version"),
                    collection_version=data.get("collection_version"),
                    deployed_version=data.get("deployed_version"),
                    is_member=True,
                    parent_artifact_id=artifact_id,
                )
            )

        logger.info(
            "compute_skill_sync_diff: %s → %d rows (%d members)",
            artifact_id,
            len(rows),
            len(rows) - 1,
        )
        return rows

    finally:
        if managed_session:
            session.close()
