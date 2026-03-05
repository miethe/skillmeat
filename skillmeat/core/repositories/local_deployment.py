"""Local filesystem implementation of the IDeploymentRepository interface.

Delegates to :class:`~skillmeat.core.deployment.DeploymentManager` for all
deployment operations and converts the resulting
:class:`~skillmeat.core.deployment.Deployment` domain objects into the
:class:`~skillmeat.core.interfaces.dtos.DeploymentDTO` contract expected by
callers in the hexagonal architecture layer.

Design notes:
- The repository does *not* own the ``DeploymentManager``; callers provide it
  via constructor injection so the dependency can be substituted in tests.
- Project IDs used externally are base64-encoded project paths (matching the
  DB cache convention).  Internally the resolver decodes them to ``pathlib.Path``
  objects before calling ``DeploymentManager`` methods.
- All exceptions from ``DeploymentManager`` propagate unchanged; this layer
  does not swallow them so callers can handle errors at the right boundary.
- Python 3.9+ compatible (no ``X | Y`` union syntax in runtime code).
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from skillmeat.core.artifact import ArtifactType
from skillmeat.core.deployment import Deployment, DeploymentManager
from skillmeat.core.interfaces.context import RequestContext
from skillmeat.core.interfaces.dtos import DeploymentDTO
from skillmeat.core.interfaces.repositories import IDeploymentRepository
from skillmeat.core.path_resolver import ProjectPathResolver

logger = logging.getLogger(__name__)

__all__ = ["LocalDeploymentRepository"]


def _decode_project_id(project_id: str) -> Path:
    """Decode a base64-encoded project path back to a filesystem path.

    Args:
        project_id: Base64-encoded absolute project path.

    Returns:
        Decoded :class:`pathlib.Path`.

    Raises:
        ValueError: If *project_id* cannot be base64-decoded.
    """
    try:
        return Path(base64.b64decode(project_id.encode()).decode())
    except Exception as exc:
        raise ValueError(
            f"Could not decode project_id '{project_id}' as a base64 path"
        ) from exc


def _encode_project_path(project_path: Path) -> str:
    """Encode an absolute project path as a base64 project ID.

    Args:
        project_path: Absolute filesystem path to the project directory.

    Returns:
        Base64-encoded string.
    """
    return base64.b64encode(str(project_path).encode()).decode()


def _deployment_to_dto(
    deployment: Deployment,
    project_path: Optional[Path] = None,
) -> DeploymentDTO:
    """Convert a :class:`Deployment` domain object to a :class:`DeploymentDTO`.

    Args:
        deployment: Source domain object from ``DeploymentManager``.
        project_path: Optional absolute path to the owning project; used to
            populate ``project_id`` and ``project_path`` on the DTO.

    Returns:
        Immutable :class:`DeploymentDTO`.
    """
    artifact_id = f"{deployment.artifact_type}:{deployment.artifact_name}"
    project_id = _encode_project_path(project_path) if project_path else None
    project_path_str = str(project_path) if project_path else None
    project_name = project_path.name if project_path else None

    # Resolve source and target paths from the artifact_path field.  The
    # ``artifact_path`` on ``Deployment`` is relative to the profile root dir
    # (e.g. ``skills/my-skill`` or ``commands/review.md``).
    target_path: Optional[str] = None
    if project_path and deployment.artifact_path:
        try:
            target_path = str(
                project_path / ".claude" / deployment.artifact_path
            )
        except Exception:
            target_path = str(deployment.artifact_path)

    return DeploymentDTO(
        id=artifact_id,
        artifact_id=artifact_id,
        artifact_name=deployment.artifact_name,
        artifact_type=deployment.artifact_type,
        project_id=project_id,
        project_path=project_path_str,
        project_name=project_name,
        from_collection=deployment.from_collection,
        scope=None,
        status="modified" if deployment.local_modifications else "deployed",
        deployed_at=deployment.deployed_at.isoformat() if deployment.deployed_at else None,
        source_path=None,
        target_path=target_path,
        collection_sha=deployment.content_hash,
        local_modifications=deployment.local_modifications,
        deployment_profile_id=deployment.deployment_profile_id,
        platform=(
            deployment.platform.value
            if deployment.platform is not None
            else None
        ),
    )


class LocalDeploymentRepository(IDeploymentRepository):
    """``IDeploymentRepository`` backed by the local filesystem.

    Delegates CRUD-like operations to
    :class:`~skillmeat.core.deployment.DeploymentManager`, which reads and
    writes the TOML-based deployment tracking files found in each project's
    ``.claude/`` directory.

    Args:
        deployment_manager: Pre-configured ``DeploymentManager`` instance.
        path_resolver: ``ProjectPathResolver`` used for path construction
            (currently informational; the manager resolves paths internally).
    """

    def __init__(
        self,
        deployment_manager: DeploymentManager,
        path_resolver: ProjectPathResolver,
    ) -> None:
        self._mgr = deployment_manager
        self._resolver = path_resolver

    # ------------------------------------------------------------------
    # IDeploymentRepository — single-item lookup
    # ------------------------------------------------------------------

    def get(
        self,
        id: str,
        ctx: Optional[RequestContext] = None,
    ) -> Optional[DeploymentDTO]:
        """Return a deployment record by its ``"type:name"`` identifier.

        Searches all projects known to the deployment manager.  Returns the
        first match.

        Args:
            id: Deployment identifier in ``"type:name"`` format.
            ctx: Optional per-request metadata (unused in this backend).

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.DeploymentDTO` when
            found, ``None`` otherwise.
        """
        for dto in self.list(ctx=ctx):
            if dto.id == id:
                return dto
        return None

    # ------------------------------------------------------------------
    # IDeploymentRepository — collection queries
    # ------------------------------------------------------------------

    def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        ctx: Optional[RequestContext] = None,
    ) -> List[DeploymentDTO]:
        """Return deployment records matching optional filter criteria.

        Supported filter keys:
        - ``project_id``: base64-encoded project path; restricts results to
          a single project.
        - ``artifact_type``: string artifact type (e.g. ``"skill"``).
        - ``artifact_id``: ``"type:name"`` string; exact-match filter.

        Args:
            filters: Optional filter map.
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.DeploymentDTO`.
        """
        filters = filters or {}
        project_id: Optional[str] = filters.get("project_id")

        if project_id:
            try:
                project_path = _decode_project_id(project_id)
            except ValueError:
                logger.warning("list: invalid project_id '%s' — returning empty", project_id)
                return []
            raw = self._mgr.list_deployments(project_path=project_path)
            dtos = [_deployment_to_dto(d, project_path) for d in raw]
        else:
            # No project scoping — return deployments for CWD as fallback.
            raw = self._mgr.list_deployments()
            dtos = [_deployment_to_dto(d) for d in raw]

        # Apply optional secondary filters.
        artifact_type_filter: Optional[str] = filters.get("artifact_type")
        artifact_id_filter: Optional[str] = filters.get("artifact_id")

        if artifact_type_filter:
            dtos = [d for d in dtos if d.artifact_type == artifact_type_filter]
        if artifact_id_filter:
            dtos = [d for d in dtos if d.artifact_id == artifact_id_filter]

        return dtos

    # ------------------------------------------------------------------
    # IDeploymentRepository — mutations
    # ------------------------------------------------------------------

    def deploy(
        self,
        artifact_id: str,
        project_id: str,
        options: Optional[Dict[str, Any]] = None,
        ctx: Optional[RequestContext] = None,
    ) -> DeploymentDTO:
        """Deploy an artifact to a project.

        Args:
            artifact_id: Artifact primary key in ``"type:name"`` format.
            project_id: Base64-encoded project path.
            options: Optional dict supporting keys: ``overwrite`` (bool),
                ``profile_id`` (str), ``collection_name`` (str).
            ctx: Optional per-request metadata.

        Returns:
            The created :class:`~skillmeat.core.interfaces.dtos.DeploymentDTO`.

        Raises:
            ValueError: If *artifact_id* cannot be parsed or *project_id* is
                invalid.
        """
        options = options or {}
        project_path = _decode_project_id(project_id)

        # Parse "type:name" artifact ID.
        if ":" not in artifact_id:
            raise ValueError(
                f"artifact_id must be in 'type:name' format, got '{artifact_id}'"
            )
        artifact_type_str, artifact_name = artifact_id.split(":", 1)

        try:
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            artifact_type = None  # type: ignore[assignment]

        results = self._mgr.deploy_artifacts(
            artifact_names=[artifact_name],
            collection_name=options.get("collection_name"),
            project_path=project_path,
            artifact_type=artifact_type,
            overwrite=bool(options.get("overwrite", False)),
            profile_id=options.get("profile_id"),
        )

        # deploy_artifacts returns a list of Deployment objects.
        if results:
            return _deployment_to_dto(results[0], project_path)

        # Fallback: reload from tracker.
        raw = self._mgr.list_deployments(project_path=project_path)
        for dep in raw:
            if dep.artifact_name == artifact_name and dep.artifact_type == artifact_type_str:
                return _deployment_to_dto(dep, project_path)

        raise KeyError(f"Deployment for '{artifact_id}' not found after deploy operation")

    def undeploy(
        self,
        id: str,
        ctx: Optional[RequestContext] = None,
    ) -> bool:
        """Remove a deployed artifact from its project.

        This implementation requires the artifact to be undeployed from the
        current working directory context.  For project-specific undeployment,
        use ``list()`` with a ``project_id`` filter to locate the deployment
        first, then call this method.

        Args:
            id: Deployment identifier in ``"type:name"`` format.
            ctx: Optional per-request metadata.

        Returns:
            ``True`` when successfully undeployed, ``False`` if not found.
        """
        if ":" not in id:
            logger.warning("undeploy: id '%s' is not in 'type:name' format", id)
            return False

        artifact_type_str, artifact_name = id.split(":", 1)
        try:
            artifact_type = ArtifactType(artifact_type_str)
        except ValueError:
            logger.warning("undeploy: unknown artifact type '%s'", artifact_type_str)
            return False

        try:
            self._mgr.undeploy(
                artifact_name=artifact_name,
                artifact_type=artifact_type,
            )
            return True
        except Exception as exc:
            logger.debug("undeploy: failed for '%s': %s", id, exc)
            return False

    # ------------------------------------------------------------------
    # IDeploymentRepository — status & artifact lookup
    # ------------------------------------------------------------------

    def get_status(
        self,
        id: str,
        ctx: Optional[RequestContext] = None,
    ) -> str:
        """Return the current deployment status for a deployment record.

        Args:
            id: Deployment identifier in ``"type:name"`` format.
            ctx: Optional per-request metadata.

        Returns:
            Status string: ``"deployed"``, ``"modified"``, or ``"outdated"``.

        Raises:
            KeyError: If no deployment with *id* exists.
        """
        dto = self.get(id, ctx=ctx)
        if dto is None:
            raise KeyError(f"No deployment found with id '{id}'")
        return dto.status

    def get_by_artifact(
        self,
        artifact_id: str,
        ctx: Optional[RequestContext] = None,
    ) -> List[DeploymentDTO]:
        """Return all deployments for a given artifact.

        Args:
            artifact_id: Artifact primary key in ``"type:name"`` format.
            ctx: Optional per-request metadata.

        Returns:
            List of matching :class:`~skillmeat.core.interfaces.dtos.DeploymentDTO`.
        """
        return self.list(filters={"artifact_id": artifact_id}, ctx=ctx)

    # ------------------------------------------------------------------
    # IDeploymentRepository — IDP DeploymentSet upsert
    # ------------------------------------------------------------------

    def upsert_idp_deployment_set(
        self,
        *,
        remote_url: str,
        name: str,
        provisioned_by: str,
        description: Optional[str] = None,
        ctx: Optional[RequestContext] = None,
    ) -> tuple:
        """Idempotently create or update a DeploymentSet for an IDP registration.

        Delegates to :class:`~skillmeat.cache.repositories.DeploymentSetRepository`
        for the actual DB interaction.  The lookup key is the ``(remote_url, name)``
        pair; if a record already exists it is updated in place, otherwise a
        new record is created with ``owner_id="idp"``.

        Args:
            remote_url: Remote Git repository URL from the IDP caller.
            name: Artifact target identifier used as the set name.
            provisioned_by: Audit field (e.g. ``"idp"``).
            description: Optional JSON-serialised metadata string.
            ctx: Optional per-request metadata (unused).

        Returns:
            A ``(deployment_set_id, created)`` tuple where *created* is
            ``True`` when a new record was inserted and ``False`` when an
            existing record was updated.
        """
        from datetime import datetime

        from skillmeat.cache.models import DeploymentSet, get_session

        session = get_session()
        try:
            existing = (
                session.query(DeploymentSet)
                .filter(
                    DeploymentSet.remote_url == remote_url,
                    DeploymentSet.name == name,
                )
                .first()
            )

            if existing is not None:
                existing.provisioned_by = provisioned_by
                existing.updated_at = datetime.utcnow()
                if description is not None:
                    existing.description = description
                session.commit()
                logger.debug(
                    "upsert_idp_deployment_set: updated id=%s remote_url=%s name=%s",
                    existing.id,
                    remote_url,
                    name,
                )
                return (existing.id, False)

            import uuid as _uuid

            new_set = DeploymentSet(
                id=_uuid.uuid4().hex,
                name=name,
                remote_url=remote_url,
                provisioned_by=provisioned_by,
                owner_id="idp",
                description=description,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(new_set)
            session.commit()
            logger.debug(
                "upsert_idp_deployment_set: created id=%s remote_url=%s name=%s",
                new_set.id,
                remote_url,
                name,
            )
            return (new_set.id, True)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
