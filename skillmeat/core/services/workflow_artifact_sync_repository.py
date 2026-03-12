"""Repository for syncing workflow records to the artifacts table.

This module bridges the ``workflows`` table and the ``artifacts`` table so
that workflow definitions appear in the unified artifact collection alongside
skills, commands, agents, etc.

Design:
    - Artifact ``id`` follows the project-wide ``type:name`` convention,
      so a workflow named "deploy-pipeline" maps to ``workflow:deploy-pipeline``.
    - The ``workflow_id`` (workflows DB primary key) is stored in
      ``ArtifactMetadata.metadata_json`` under the key ``"workflow_id"`` so
      that reverse-lookup is possible without a separate join table.
    - Both naming-convention look-up *and* metadata look-up are supported for
      robustness; the naming convention is the primary fast path.
    - Only the local (SQLite / SQLAlchemy 1.x ``session.query()``) dialect is
      implemented here, consistent with the project-wide architecture decision
      that workflows currently live only in the local cache.

Usage::

    repo = WorkflowArtifactSyncRepository()
    artifact_uuid = repo.upsert_artifact_from_workflow(
        workflow_id="abc123",
        name="deploy-pipeline",
        description="Runs the deployment pipeline",
        version="1.0.0",
        project_id=None,
    )
    artifact = repo.get_artifact_by_workflow_id("abc123")
    deleted = repo.delete_artifact_for_workflow("abc123")
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker as _sessionmaker

from skillmeat.cache.models import (
    Artifact,
    ArtifactMetadata,
    Project,
    create_db_engine,
    create_tables,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentinel project used when no real project_id is supplied
# ---------------------------------------------------------------------------

_WORKFLOW_PROJECT_ID = "workflow_artifacts_global"
"""Sentinel project ID for workflow-derived artifact rows.

Workflow definitions are not tied to any real filesystem project, so their
``Artifact`` rows reference this virtual project row to satisfy the FK
constraint on ``artifacts.project_id``.
"""

_ARTIFACT_TYPE = "workflow"


class WorkflowArtifactSyncRepository:
    """Local-dialect repository that syncs workflow records to the artifacts table.

    Uses SQLAlchemy 1.x ``session.query()`` style, consistent with other local
    repositories in ``skillmeat/cache/repositories.py``.

    Attributes:
        db_path: Absolute path to the SQLite cache database file.
    """

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        """Initialise repository.

        Args:
            db_path: Path to the SQLite database file.  Defaults to
                ``~/.skillmeat/cache/cache.db``.
        """
        if db_path is None:
            self.db_path = Path.home() / ".skillmeat" / "cache" / "cache.db"
        else:
            self.db_path = Path(db_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._engine = create_db_engine(self.db_path)
        self._session_factory = _sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self._engine,
        )

        # Ensure all ORM tables exist (idempotent)
        create_tables(self.db_path)

        logger.debug(
            "WorkflowArtifactSyncRepository initialised: db=%s", self.db_path
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_session(self) -> Session:
        """Return a new SQLAlchemy session bound to this repository's engine."""
        return self._session_factory()

    def _artifact_id(self, name: str) -> str:
        """Return the canonical artifact primary key for a workflow name.

        Args:
            name: Workflow name (from ``Workflow.name``).

        Returns:
            String in ``"workflow:<name>"`` format.
        """
        return f"{_ARTIFACT_TYPE}:{name}"

    def _ensure_sentinel_project(self, session: Session, project_id: str) -> None:
        """Ensure a sentinel Project row exists to satisfy the FK constraint.

        If ``project_id`` is a real project the caller already manages that row;
        this helper only creates the row when it doesn't exist (idempotent).

        Args:
            session: Active SQLAlchemy session (caller manages commit/rollback).
            project_id: The ``project_id`` value that will be stored on the
                ``Artifact`` row.
        """
        existing = session.query(Project).filter_by(id=project_id).first()
        if not existing:
            sentinel = Project(
                id=project_id,
                name="Workflow Artifacts",
                path=str(Path.home() / ".skillmeat" / "workflows"),
                description="Virtual project for workflow artifact rows",
                status="active",
            )
            session.add(sentinel)
            logger.info(
                "WorkflowArtifactSyncRepository: created sentinel project row '%s'",
                project_id,
            )

    def _build_metadata_json(
        self,
        workflow_id: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Serialise metadata payload to JSON string.

        Args:
            workflow_id: The workflows DB primary key to embed in metadata.
            extra: Additional caller-supplied metadata dict (merged in).

        Returns:
            JSON string suitable for ``ArtifactMetadata.metadata_json``.
        """
        payload: Dict[str, Any] = {"workflow_id": workflow_id}
        if extra:
            payload.update(extra)
        return json.dumps(payload)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upsert_artifact_from_workflow(
        self,
        workflow_id: str,
        name: str,
        description: Optional[str] = None,
        version: Optional[str] = None,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create or update an Artifact row that mirrors a Workflow record.

        The operation is idempotent: if an Artifact with the canonical
        ``workflow:<name>`` ID already exists it is updated in-place while its
        stable ``uuid`` is preserved.  Concurrent calls for the same workflow
        are safe because the primary key uniqueness constraint prevents
        duplicate rows and any ``IntegrityError`` is caught and re-tried as an
        update.

        Args:
            workflow_id: Primary key from the ``workflows`` table (used as
                the linking key stored in metadata).
            name: Human-readable workflow name (``Workflow.name``).
            description: Optional workflow description.
            version: Optional version string (e.g. ``"1.0.0"``).
            project_id: Optional real project ID to associate the artifact
                with.  Defaults to the internal sentinel project.
            metadata: Extra key-value pairs to store in ``ArtifactMetadata``.

        Returns:
            The stable ``Artifact.uuid`` (32-char hex string).

        Raises:
            RuntimeError: If the upsert fails after exhausting retries.
        """
        effective_project_id = project_id or _WORKFLOW_PROJECT_ID
        artifact_id = self._artifact_id(name)
        metadata_json = self._build_metadata_json(workflow_id, extra=metadata)

        session = self._get_session()
        try:
            # Ensure the project FK target exists
            self._ensure_sentinel_project(session, effective_project_id)

            existing: Optional[Artifact] = (
                session.query(Artifact).filter_by(id=artifact_id).first()
            )

            if existing is not None:
                # --- UPDATE path ---
                existing.name = name
                existing.description = description
                existing.deployed_version = version
                existing.upstream_version = version
                existing.updated_at = datetime.utcnow()

                # Upsert metadata row
                if existing.artifact_metadata is not None:
                    existing.artifact_metadata.description = description
                    existing.artifact_metadata.metadata_json = metadata_json
                else:
                    session.add(
                        ArtifactMetadata(
                            artifact_id=artifact_id,
                            description=description,
                            metadata_json=metadata_json,
                        )
                    )

                session.commit()
                artifact_uuid: str = existing.uuid
                logger.info(
                    "WorkflowArtifactSyncRepository.upsert: updated artifact '%s' "
                    "(uuid=%s) for workflow_id=%s",
                    artifact_id,
                    artifact_uuid,
                    workflow_id,
                )
                return artifact_uuid

            # --- INSERT path ---
            artifact_uuid = uuid.uuid4().hex
            new_artifact = Artifact(
                id=artifact_id,
                uuid=artifact_uuid,
                project_id=effective_project_id,
                name=name,
                type=_ARTIFACT_TYPE,
                description=description,
                deployed_version=version,
                upstream_version=version,
                is_outdated=False,
                local_modified=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(new_artifact)
            # Flush to obtain the FK for ArtifactMetadata
            session.flush()

            session.add(
                ArtifactMetadata(
                    artifact_id=artifact_id,
                    description=description,
                    metadata_json=metadata_json,
                )
            )

            session.commit()
            logger.info(
                "WorkflowArtifactSyncRepository.upsert: created artifact '%s' "
                "(uuid=%s) for workflow_id=%s",
                artifact_id,
                artifact_uuid,
                workflow_id,
            )
            return artifact_uuid

        except IntegrityError:
            # Race condition: another caller inserted between our SELECT and
            # INSERT.  Roll back and fall through to the update path.
            session.rollback()
            logger.debug(
                "WorkflowArtifactSyncRepository.upsert: IntegrityError on insert "
                "for '%s' — retrying as update",
                artifact_id,
            )
            try:
                existing = (
                    session.query(Artifact).filter_by(id=artifact_id).first()
                )
                if existing is None:
                    raise RuntimeError(
                        f"Artifact '{artifact_id}' missing after IntegrityError"
                    )

                existing.name = name
                existing.description = description
                existing.deployed_version = version
                existing.upstream_version = version
                existing.updated_at = datetime.utcnow()

                if existing.artifact_metadata is not None:
                    existing.artifact_metadata.description = description
                    existing.artifact_metadata.metadata_json = metadata_json
                else:
                    session.add(
                        ArtifactMetadata(
                            artifact_id=artifact_id,
                            description=description,
                            metadata_json=metadata_json,
                        )
                    )

                session.commit()
                return existing.uuid
            except Exception as retry_exc:
                session.rollback()
                raise RuntimeError(
                    f"WorkflowArtifactSyncRepository.upsert retry failed: {retry_exc}"
                ) from retry_exc

        except OperationalError as exc:
            session.rollback()
            logger.error(
                "WorkflowArtifactSyncRepository.upsert: DB operational error: %s", exc
            )
            raise RuntimeError(
                f"WorkflowArtifactSyncRepository.upsert failed: {exc}"
            ) from exc

        finally:
            session.close()

    def delete_artifact_for_workflow(self, workflow_id: str) -> bool:
        """Delete the Artifact row associated with a workflow.

        The ``ArtifactMetadata`` row is removed automatically via cascade
        (``ondelete="CASCADE"`` on ``artifact_metadata.artifact_id``).

        Looks up the artifact using the metadata JSON ``workflow_id`` field so
        that the link is robust even if the workflow was renamed (though
        renaming would produce a new ``type:name`` id anyway).

        Args:
            workflow_id: Primary key of the ``workflows`` row.

        Returns:
            ``True`` if a row was found and deleted, ``False`` otherwise.
        """
        session = self._get_session()
        try:
            artifact = self._query_by_workflow_id(session, workflow_id)
            if artifact is None:
                logger.debug(
                    "WorkflowArtifactSyncRepository.delete: no artifact for "
                    "workflow_id=%s",
                    workflow_id,
                )
                return False

            artifact_id = artifact.id
            session.delete(artifact)
            session.commit()
            logger.info(
                "WorkflowArtifactSyncRepository.delete: removed artifact '%s' "
                "for workflow_id=%s",
                artifact_id,
                workflow_id,
            )
            return True

        except OperationalError as exc:
            session.rollback()
            logger.error(
                "WorkflowArtifactSyncRepository.delete: DB error: %s", exc
            )
            return False

        finally:
            session.close()

    def get_artifact_by_workflow_id(self, workflow_id: str) -> Optional[Artifact]:
        """Return the Artifact ORM instance linked to a workflow, or None.

        The lookup first queries ``ArtifactMetadata`` for a JSON payload
        containing ``"workflow_id": workflow_id``.  This is the authoritative
        link even when the workflow has been renamed.

        Args:
            workflow_id: Primary key of the ``workflows`` row.

        Returns:
            The matching ``Artifact`` ORM instance (with ``artifact_metadata``
            eagerly loaded), or ``None`` if not found.
        """
        session = self._get_session()
        try:
            return self._query_by_workflow_id(session, workflow_id)
        except OperationalError as exc:
            logger.error(
                "WorkflowArtifactSyncRepository.get: DB error: %s", exc
            )
            return None
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Private query helpers
    # ------------------------------------------------------------------

    def _query_by_workflow_id(
        self, session: Session, workflow_id: str
    ) -> Optional[Artifact]:
        """Look up an Artifact by scanning ArtifactMetadata JSON.

        Iterates over all ``workflow``-type artifacts and checks the parsed
        ``metadata_json`` for a matching ``workflow_id`` key.  This is an
        O(n) scan over workflow artifacts only, which is expected to be a
        small set.

        For the common case where the artifact was created by this repository
        the name-convention fast path (``workflow:<name>``) could also be
        used, but we rely on metadata to handle any renaming or edge cases.

        Args:
            session: Active SQLAlchemy session (caller owns lifecycle).
            workflow_id: The ``workflow_id`` value to search for.

        Returns:
            Matching ``Artifact`` instance or ``None``.
        """
        # Fetch all workflow-type artifact metadata rows in one query
        rows: list[ArtifactMetadata] = (
            session.query(ArtifactMetadata)
            .join(Artifact, ArtifactMetadata.artifact_id == Artifact.id)
            .filter(Artifact.type == _ARTIFACT_TYPE)
            .all()
        )

        for row in rows:
            if not row.metadata_json:
                continue
            try:
                payload = json.loads(row.metadata_json)
            except (json.JSONDecodeError, TypeError):
                continue

            if payload.get("workflow_id") == workflow_id:
                # The ``artifact_metadata`` relationship is ``lazy="selectin"``
                # so ``row.artifact`` is already loaded.
                return row.artifact

        return None
