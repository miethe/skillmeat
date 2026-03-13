"""Service for orchestrating BOM snapshot creation with attestation records.

Provides a thin service layer that wraps BomGenerator output with owner context,
creating both a BomSnapshot and an optional AttestationRecord in a single
transactional unit.  The caller is responsible for committing the session.

Usage::

    from skillmeat.core.services.bom_service import BomAttestationService

    service = BomAttestationService(session)
    snapshot, attestation = service.create_bom_with_attestation(
        bom_json=bom_json,
        project_id="my-project",
        artifact_id="skill:canvas",
        owner_type="user",
        owner_id="alice",
        roles=["team_member"],
        scopes=["read", "write"],
    )
    session.commit()
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from skillmeat.cache.models import AttestationRecord, BomSnapshot

logger = logging.getLogger(__name__)


class BomAttestationService:
    """Orchestrates BOM snapshot creation with attestation record population.

    Accepts a SQLAlchemy session and writes both a :class:`BomSnapshot` and,
    when an ``artifact_id`` is supplied, an :class:`AttestationRecord` to the
    database.  All writes are flushed but **not committed** — the caller owns
    the transaction boundary.

    Args:
        session: An active SQLAlchemy session used for all DB operations.
    """

    def __init__(self, session: "Session") -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_bom_with_attestation(
        self,
        bom_json: str,
        project_id: Optional[str] = None,
        commit_sha: Optional[str] = None,
        artifact_id: Optional[str] = None,
        owner_type: str = "user",
        owner_id: str = "anonymous",
        roles: Optional[List[str]] = None,
        scopes: Optional[List[str]] = None,
        visibility: str = "private",
    ) -> Tuple[BomSnapshot, Optional[AttestationRecord]]:
        """Create a BomSnapshot and corresponding AttestationRecord.

        Steps:

        1. Create :class:`BomSnapshot` with ``bom_json``, ``project_id``,
           ``commit_sha``, and ``owner_type``.
        2. If ``artifact_id`` is provided, create :class:`AttestationRecord`
           linked to the artifact with ``owner_type``, ``owner_id``, ``roles``,
           ``scopes``, and ``visibility``.
        3. Flush both to the DB (caller owns the commit).
        4. Return ``(snapshot, attestation_record_or_none)``.

        Args:
            bom_json: Serialised BOM payload (JSON string produced by
                :class:`~skillmeat.core.bom.generator.BomSerializer`).
            project_id: Opaque project identifier; ``None`` for
                collection-level BOMs.
            commit_sha: Optional git commit SHA associated with this snapshot.
            artifact_id: If supplied, an :class:`AttestationRecord` is created
                linking this artifact to the snapshot's owner context.
            owner_type: Ownership discriminator — ``"user"``, ``"team"``, or
                ``"enterprise"``.  Defaults to ``"user"``.
            owner_id: Opaque identifier for the owning principal.  Defaults
                to ``"anonymous"``.
            roles: Optional list of RBAC role strings to store on the
                attestation record.
            scopes: Optional list of permission scope strings to store on the
                attestation record.
            visibility: Visibility level — ``"private"``, ``"team"``, or
                ``"public"``.  Defaults to ``"private"``.

        Returns:
            A two-tuple ``(snapshot, attestation)`` where ``attestation`` is
            ``None`` when ``artifact_id`` was not provided.
        """
        snapshot = BomSnapshot(
            bom_json=bom_json,
            project_id=project_id,
            commit_sha=commit_sha,
            owner_type=owner_type,
        )
        self._session.add(snapshot)
        logger.debug(
            "Created BomSnapshot: project_id=%s commit_sha=%s owner_type=%s",
            project_id,
            commit_sha,
            owner_type,
        )

        attestation: Optional[AttestationRecord] = None
        if artifact_id is not None:
            attestation = self.create_attestation_for_artifact(
                artifact_id=artifact_id,
                owner_type=owner_type,
                owner_id=owner_id,
                roles=roles,
                scopes=scopes,
                visibility=visibility,
            )

        self._session.flush()
        return snapshot, attestation

    def create_attestation_for_artifact(
        self,
        artifact_id: str,
        owner_type: str,
        owner_id: str,
        roles: Optional[List[str]] = None,
        scopes: Optional[List[str]] = None,
        visibility: str = "private",
    ) -> AttestationRecord:
        """Create a standalone AttestationRecord for an artifact.

        The record is added to the session but **not flushed or committed** so
        it can be batched with other writes.

        Args:
            artifact_id: Foreign key referencing ``artifacts.id``.
            owner_type: Ownership discriminator (``"user"``, ``"team"``, or
                ``"enterprise"``).
            owner_id: Opaque identifier for the owning principal.
            roles: Optional list of RBAC role strings.
            scopes: Optional list of permission scope strings.
            visibility: Visibility level (``"private"``, ``"team"``, or
                ``"public"``).  Defaults to ``"private"``.

        Returns:
            The newly created (and session-tracked) :class:`AttestationRecord`.
        """
        attestation = AttestationRecord(
            artifact_id=artifact_id,
            owner_type=owner_type,
            owner_id=owner_id,
            roles=roles,
            scopes=scopes,
            visibility=visibility,
        )
        self._session.add(attestation)
        logger.debug(
            "Created AttestationRecord: artifact_id=%s owner_type=%s owner_id=%s",
            artifact_id,
            owner_type,
            owner_id,
        )
        return attestation
