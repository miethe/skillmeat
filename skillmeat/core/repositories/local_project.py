"""Local filesystem + DB-cache implementation of IProjectRepository.

This module provides ``LocalProjectRepository``, the concrete implementation
of the :class:`~skillmeat.core.interfaces.repositories.IProjectRepository` ABC
that backs the ``/api/v1/projects`` router.

Architecture overview
---------------------
Projects in SkillMeat are directories on disk that have one or more artifacts
deployed into them (signalled by the presence of a ``.skillmeat-deployed.toml``
file inside a ``.<platform>`` subdirectory).  The DB cache (``skillmeat/cache/``)
stores a denormalised mirror of the filesystem state so the web UI can query it
efficiently without touching disk on every request.

Design decisions
----------------
* **Graceful degradation without DB**: when no ``CacheManager`` is available
  (e.g. in lightweight CLI invocations) the repository falls back to
  filesystem-only discovery.  This keeps the contract satisfied even outside
  the full API server.
* **Write-through on mutations**: ``create`` / ``update`` / ``delete`` operations
  synchronise to the DB cache via ``CacheManager`` so the web UI sees changes
  immediately, without needing a full cache refresh.
* **ID encoding**: project IDs are base64-encoded absolute paths, matching the
  encoding used by the existing ``/api/v1/projects`` router.
* **No Pydantic / SQLAlchemy in this file**: all DB work goes through
  ``CacheRepository`` and ``CacheManager``; all returned types are
  :class:`~skillmeat.core.interfaces.dtos.ProjectDTO` and
  :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`.

Python 3.9+ compatible.
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from skillmeat.core.interfaces.context import RequestContext
from skillmeat.core.interfaces.dtos import ArtifactDTO, ProjectDTO
from skillmeat.core.interfaces.repositories import IProjectRepository
from skillmeat.core.path_resolver import ProjectPathResolver
from skillmeat.storage.deployment import DeploymentTracker

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ID helpers (mirrors encode_project_id / decode_project_id in the router)
# ---------------------------------------------------------------------------


def _encode_project_id(path: str) -> str:
    """Return the base64-encoded project ID for an absolute path.

    Args:
        path: Absolute filesystem path string.

    Returns:
        URL-safe base64 string.
    """
    return base64.b64encode(path.encode()).decode()


def _decode_project_id(project_id: str) -> Optional[str]:
    """Decode a base64 project ID back to a filesystem path.

    Args:
        project_id: Base64-encoded project ID.

    Returns:
        Decoded absolute path string, or ``None`` when the ID is invalid.
    """
    try:
        return base64.b64decode(project_id.encode()).decode()
    except Exception:
        return None


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Helpers for mapping ORM / dict objects → ProjectDTO / ArtifactDTO
# ---------------------------------------------------------------------------


def _project_orm_to_dto(project: Any) -> ProjectDTO:
    """Convert a ``Project`` ORM instance to :class:`ProjectDTO`.

    Accepts any object with the same attribute names as the SQLAlchemy
    ``Project`` model so this helper is easy to unit-test without a DB.

    Args:
        project: A ``Project`` ORM instance (or duck-typed equivalent).

    Returns:
        Immutable :class:`ProjectDTO`.
    """
    artifact_count = 0
    artifacts = getattr(project, "artifacts", None)
    if artifacts is not None:
        artifact_count = len(artifacts)

    return ProjectDTO(
        id=project.id,
        name=project.name,
        path=project.path,
        description=getattr(project, "description", None),
        status=getattr(project, "status", "active"),
        artifact_count=artifact_count,
        created_at=_to_iso(getattr(project, "created_at", None)),
        updated_at=_to_iso(getattr(project, "updated_at", None)),
        last_fetched=_to_iso(getattr(project, "last_fetched", None)),
    )


def _artifact_orm_to_dto(artifact: Any) -> ArtifactDTO:
    """Convert a cached ``Artifact`` ORM instance to :class:`ArtifactDTO`.

    Args:
        artifact: A ``cache.models.Artifact`` ORM instance.

    Returns:
        Immutable :class:`ArtifactDTO`.
    """
    return ArtifactDTO(
        id=artifact.id,
        name=artifact.name,
        artifact_type=getattr(artifact, "type", ""),
        uuid=getattr(artifact, "uuid", None),
        source=getattr(artifact, "source", None),
        version=getattr(artifact, "deployed_version", None),
        scope=getattr(artifact, "scope", None),
        description=getattr(artifact, "description", None),
        content_path=getattr(artifact, "content_path", None),
        is_outdated=bool(getattr(artifact, "is_outdated", False)),
        local_modified=bool(getattr(artifact, "local_modified", False)),
        project_id=getattr(artifact, "project_id", None),
        created_at=_to_iso(getattr(artifact, "created_at", None)),
        updated_at=_to_iso(getattr(artifact, "updated_at", None)),
    )


def _to_iso(value: Any) -> Optional[str]:
    """Coerce *value* to ISO-8601 string or ``None``."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


# ---------------------------------------------------------------------------
# Filesystem discovery helpers
# ---------------------------------------------------------------------------


def _build_project_dto_from_path(project_path: Path) -> ProjectDTO:
    """Build a :class:`ProjectDTO` from a filesystem project directory.

    Uses ``DeploymentTracker.read_deployments`` to count deployed artifacts.
    Called as a fallback when no DB cache is available.

    Args:
        project_path: Absolute path to a project root directory.

    Returns:
        A :class:`ProjectDTO` populated from filesystem metadata.
    """
    path_str = str(project_path.resolve())
    project_id = _encode_project_id(path_str)

    deployments = []
    try:
        deployments = DeploymentTracker.read_deployments(project_path) or []
    except Exception as exc:
        logger.debug("Could not read deployments for %s: %s", path_str, exc)

    return ProjectDTO(
        id=project_id,
        name=project_path.name,
        path=path_str,
        status="active",
        artifact_count=len(deployments),
        last_fetched=_now_iso(),
    )


def _discover_project_paths() -> List[Path]:
    """Discover known project directories by scanning common locations.

    Mirrors the discovery logic used in the projects router.

    Returns:
        Deduplicated list of absolute project ``Path`` objects.
    """
    home = Path.home()
    search_paths: List[Path] = [
        home / "projects",
        home / "dev",
        home / "workspace",
        home / "src",
        Path.cwd(),
    ]

    MAX_DEPTH = 3
    deployment_filename = DeploymentTracker.DEPLOYMENT_FILE

    discovered: List[Path] = []
    seen: set = set()

    for search_path in search_paths:
        if not search_path.exists() or not search_path.is_dir():
            continue
        try:
            resolved_search = search_path.resolve()
        except (RuntimeError, OSError) as exc:
            logger.debug("Skipping search path %s: %s", search_path, exc)
            continue

        try:
            for deployment_file in resolved_search.rglob(f"*/{deployment_filename}"):
                # The deployment file lives inside .<platform>/ which is
                # a direct child of the project root.
                project_path = deployment_file.parent.parent
                try:
                    project_path = project_path.resolve()
                    project_path.relative_to(resolved_search)
                except (ValueError, RuntimeError, OSError):
                    continue

                depth = len(project_path.relative_to(resolved_search).parts)
                if depth > MAX_DEPTH:
                    continue

                key = str(project_path)
                if key not in seen:
                    seen.add(key)
                    discovered.append(project_path)
        except (PermissionError, OSError) as exc:
            logger.debug("Error scanning %s: %s", search_path, exc)

    return discovered


# ---------------------------------------------------------------------------
# LocalProjectRepository
# ---------------------------------------------------------------------------


class LocalProjectRepository(IProjectRepository):
    """Filesystem + DB-cache implementation of :class:`IProjectRepository`.

    Attributes
    ----------
    _path_resolver:
        Provides collection-level path helpers used when constructing new
        project structures.
    _cache_manager:
        Optional ``CacheManager`` instance.  When present, all reads and
        write-through syncs use it.  When absent the repository falls back
        to pure filesystem operations.

    Parameters
    ----------
    path_resolver:
        A :class:`~skillmeat.core.path_resolver.ProjectPathResolver` instance.
    cache_manager:
        Optional ``skillmeat.cache.manager.CacheManager``.  Pass ``None``
        (the default) to run in filesystem-only mode.
    """

    def __init__(
        self,
        path_resolver: ProjectPathResolver,
        cache_manager: Optional[Any] = None,
    ) -> None:
        self._path_resolver = path_resolver
        self._cache_manager = cache_manager

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_cache_repository(self) -> Optional[Any]:
        """Return the underlying ``CacheRepository`` if a manager is available."""
        if self._cache_manager is None:
            return None
        return getattr(self._cache_manager, "repository", None)

    def _dto_from_path(self, project_path: Path) -> ProjectDTO:
        """Build a DTO by preferring DB cache over filesystem scan.

        Args:
            project_path: Resolved absolute path to the project root.

        Returns:
            :class:`ProjectDTO` from cache when available, filesystem scan
            otherwise.
        """
        path_str = str(project_path.resolve())
        project_id = _encode_project_id(path_str)

        repo = self._get_cache_repository()
        if repo is not None:
            try:
                orm_project = repo.get_project(project_id)
                if orm_project is not None:
                    return _project_orm_to_dto(orm_project)
            except Exception as exc:
                logger.debug(
                    "DB lookup for %s failed, falling back to FS: %s",
                    project_id,
                    exc,
                )

        return _build_project_dto_from_path(project_path)

    # ------------------------------------------------------------------
    # IProjectRepository — single-item lookup
    # ------------------------------------------------------------------

    def get(
        self,
        id: str,
        ctx: Optional[RequestContext] = None,
    ) -> Optional[ProjectDTO]:
        """Return the project identified by *id*.

        Tries DB cache first; falls back to filesystem resolution.

        Args:
            id: Base64-encoded project path.
            ctx: Optional per-request metadata (unused here).

        Returns:
            :class:`ProjectDTO` when found, ``None`` otherwise.
        """
        path_str = _decode_project_id(id)
        if path_str is None:
            logger.warning("get(): invalid project ID %r", id)
            return None

        # Try DB cache first
        repo = self._get_cache_repository()
        if repo is not None:
            try:
                orm_project = repo.get_project(id)
                if orm_project is not None:
                    return _project_orm_to_dto(orm_project)
            except Exception as exc:
                logger.debug("DB lookup failed for %r: %s", id, exc)

        # Filesystem fallback
        project_path = Path(path_str)
        if project_path.is_dir():
            return _build_project_dto_from_path(project_path)

        return None

    # ------------------------------------------------------------------
    # IProjectRepository — collection queries
    # ------------------------------------------------------------------

    def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        ctx: Optional[RequestContext] = None,
    ) -> List[ProjectDTO]:
        """Return all known projects, optionally filtered.

        Reads from DB cache when available.  Falls back to filesystem
        discovery otherwise.

        Args:
            filters: Optional filter map.  Recognised key: ``"status"``.
            ctx: Optional per-request metadata (unused here).

        Returns:
            List of :class:`ProjectDTO` objects.
        """
        filters = filters or {}
        status_filter: Optional[str] = filters.get("status")

        repo = self._get_cache_repository()
        if repo is not None:
            try:
                if status_filter:
                    orm_projects = repo.get_projects_by_status(status_filter)
                else:
                    orm_projects = repo.list_projects()
                return [_project_orm_to_dto(p) for p in orm_projects]
            except Exception as exc:
                logger.warning(
                    "DB list_projects failed, falling back to FS discovery: %s",
                    exc,
                )

        # Filesystem-only path
        paths = _discover_project_paths()
        dtos = [_build_project_dto_from_path(p) for p in paths]
        if status_filter:
            dtos = [d for d in dtos if d.status == status_filter]
        return dtos

    # ------------------------------------------------------------------
    # IProjectRepository — mutations
    # ------------------------------------------------------------------

    def create(
        self,
        dto: ProjectDTO,
        ctx: Optional[RequestContext] = None,
    ) -> ProjectDTO:
        """Register a new project and persist it to the DB cache.

        Args:
            dto: Project data including at minimum ``id``, ``name``, and
                ``path``.
            ctx: Optional per-request metadata (unused here).

        Returns:
            The persisted :class:`ProjectDTO` (may have server-set timestamps).

        Raises:
            ValueError: If a project with the same ID already exists.
        """
        if self.get(dto.id, ctx) is not None:
            raise ValueError(f"A project with ID '{dto.id}' already exists.")

        project_data: Dict[str, Any] = {
            "id": dto.id,
            "name": dto.name,
            "path": dto.path,
            "description": dto.description,
            "artifacts": [],
        }

        if self._cache_manager is not None:
            try:
                self._cache_manager.upsert_project(project_data)
                logger.debug("create(): upserted project %r to DB cache", dto.id)
            except Exception as exc:
                logger.warning("create(): DB upsert failed for %r: %s", dto.id, exc)

        # Return a DTO with the current timestamp populated
        return ProjectDTO(
            id=dto.id,
            name=dto.name,
            path=dto.path,
            description=dto.description,
            status=dto.status,
            artifact_count=dto.artifact_count,
            created_at=_now_iso(),
            updated_at=_now_iso(),
            last_fetched=_now_iso(),
        )

    def update(
        self,
        id: str,
        updates: Dict[str, Any],
        ctx: Optional[RequestContext] = None,
    ) -> ProjectDTO:
        """Apply a partial update to an existing project.

        Supported update keys: ``name``, ``description``, ``status``.

        Args:
            id: Base64-encoded project path.
            updates: Map of field names to new values.
            ctx: Optional per-request metadata (unused here).

        Returns:
            The updated :class:`ProjectDTO`.

        Raises:
            KeyError: If no project with *id* exists.
        """
        existing = self.get(id, ctx)
        if existing is None:
            raise KeyError(f"Project '{id}' not found.")

        repo = self._get_cache_repository()
        if repo is not None:
            allowed_fields = {"name", "description", "status"}
            db_updates = {k: v for k, v in updates.items() if k in allowed_fields}
            if db_updates:
                try:
                    repo.update_project(id, **db_updates)
                    logger.debug(
                        "update(): applied %r to project %r in DB cache",
                        db_updates,
                        id,
                    )
                except Exception as exc:
                    logger.warning("update(): DB update failed for %r: %s", id, exc)

        # Re-fetch to return a consistent DTO
        refreshed = self.get(id, ctx)
        if refreshed is not None:
            return refreshed

        # Construct manually from updates as a fallback
        return ProjectDTO(
            id=existing.id,
            name=updates.get("name", existing.name),
            path=existing.path,
            description=updates.get("description", existing.description),
            status=updates.get("status", existing.status),
            artifact_count=existing.artifact_count,
            created_at=existing.created_at,
            updated_at=_now_iso(),
            last_fetched=existing.last_fetched,
        )

    def delete(
        self,
        id: str,
        ctx: Optional[RequestContext] = None,
    ) -> bool:
        """Remove a project record from the DB cache.

        Does **not** delete anything on disk.

        Args:
            id: Base64-encoded project path.
            ctx: Optional per-request metadata (unused here).

        Returns:
            ``True`` when found and deleted, ``False`` when not found.
        """
        repo = self._get_cache_repository()
        if repo is None:
            logger.debug("delete(): no DB cache — nothing to delete for %r", id)
            return False

        try:
            return repo.delete_project(id)
        except Exception as exc:
            logger.warning("delete(): DB deletion failed for %r: %s", id, exc)
            return False

    # ------------------------------------------------------------------
    # IProjectRepository — artifact listing
    # ------------------------------------------------------------------

    def get_artifacts(
        self,
        project_id: str,
        ctx: Optional[RequestContext] = None,
    ) -> List[ArtifactDTO]:
        """Return all artifacts deployed to a project.

        Reads from DB cache when available; falls back to
        ``DeploymentTracker.read_deployments`` when not.

        Args:
            project_id: Base64-encoded project path.
            ctx: Optional per-request metadata (unused here).

        Returns:
            List of :class:`ArtifactDTO` objects for every deployed artifact.
        """
        repo = self._get_cache_repository()
        if repo is not None:
            try:
                orm_artifacts = repo.list_artifacts_by_project(project_id)
                return [_artifact_orm_to_dto(a) for a in orm_artifacts]
            except Exception as exc:
                logger.debug(
                    "get_artifacts(): DB lookup failed for %r, falling back: %s",
                    project_id,
                    exc,
                )

        # Filesystem fallback: build minimal ArtifactDTOs from deployment records
        path_str = _decode_project_id(project_id)
        if path_str is None:
            return []

        project_path = Path(path_str)
        if not project_path.is_dir():
            return []

        try:
            deployments = DeploymentTracker.read_deployments(project_path) or []
        except Exception as exc:
            logger.debug(
                "get_artifacts(): DeploymentTracker failed for %r: %s",
                path_str,
                exc,
            )
            return []

        result: List[ArtifactDTO] = []
        for dep in deployments:
            raw_type = dep.artifact_type
            artifact_type = (
                raw_type.value  # type: ignore[union-attr]
                if hasattr(raw_type, "value")
                else str(raw_type)
            )
            artifact_name = getattr(dep, "name", "")
            artifact_id = (
                f"{artifact_type}:{artifact_name}" if artifact_name else artifact_type
            )

            result.append(
                ArtifactDTO(
                    id=artifact_id,
                    name=artifact_name,
                    artifact_type=artifact_type,
                    version=getattr(dep, "version", None),
                    project_id=project_id,
                    deployed_at=_to_iso(getattr(dep, "deployed_at", None)),
                )
                if hasattr(ArtifactDTO, "deployed_at")
                else ArtifactDTO(
                    id=artifact_id,
                    name=artifact_name,
                    artifact_type=artifact_type,
                    version=getattr(dep, "version", None),
                    project_id=project_id,
                )
            )
        return result

    # ------------------------------------------------------------------
    # IProjectRepository — refresh
    # ------------------------------------------------------------------

    def refresh(
        self,
        id: str,
        ctx: Optional[RequestContext] = None,
    ) -> ProjectDTO:
        """Re-scan a project's deployment files and sync to the DB cache.

        Rescans the deployment tracking TOML file on disk and updates the
        cached artifact count and ``last_fetched`` timestamp.

        Args:
            id: Base64-encoded project path.
            ctx: Optional per-request metadata (unused here).

        Returns:
            The refreshed :class:`ProjectDTO`.

        Raises:
            KeyError: If the project directory does not exist on disk.
        """
        path_str = _decode_project_id(id)
        if path_str is None:
            raise KeyError(f"Project ID '{id}' is not a valid base64-encoded path.")

        project_path = Path(path_str)
        if not project_path.is_dir():
            raise KeyError(f"Project directory '{path_str}' does not exist on disk.")

        # Re-read deployments from filesystem
        deployments: List[Any] = []
        try:
            deployments = DeploymentTracker.read_deployments(project_path) or []
        except Exception as exc:
            logger.warning(
                "refresh(): could not read deployments for %s: %s", path_str, exc
            )

        artifact_count = len(deployments)
        name = project_path.name

        # Sync to DB cache if available
        if self._cache_manager is not None:
            project_data: Dict[str, Any] = {
                "id": id,
                "name": name,
                "path": path_str,
                "artifacts": [],
            }
            try:
                self._cache_manager.upsert_project(project_data)
                logger.debug(
                    "refresh(): synced project %r to DB cache (%d artifacts)",
                    id,
                    artifact_count,
                )
            except Exception as exc:
                logger.warning("refresh(): DB sync failed for %r: %s", id, exc)

        # Return a fresh DTO.  Prefer reading from the DB so timestamps
        # reflect the actual committed values.
        fresh = self.get(id, ctx)
        if fresh is not None:
            # artifact_count from DB may lag if upsert did not populate
            # individual artifacts; override with what we counted above.
            if fresh.artifact_count != artifact_count:
                return ProjectDTO(
                    id=fresh.id,
                    name=fresh.name,
                    path=fresh.path,
                    description=fresh.description,
                    status=fresh.status,
                    artifact_count=artifact_count,
                    created_at=fresh.created_at,
                    updated_at=fresh.updated_at,
                    last_fetched=_now_iso(),
                )
            return fresh

        # Fallback: build from filesystem
        return ProjectDTO(
            id=id,
            name=name,
            path=path_str,
            status="active",
            artifact_count=artifact_count,
            last_fetched=_now_iso(),
        )

    # ------------------------------------------------------------------
    # IProjectRepository — path-based lookup and upsert
    # ------------------------------------------------------------------

    def get_by_path(
        self,
        path: str,
        ctx: Optional[RequestContext] = None,
    ) -> Optional[ProjectDTO]:
        """Return the project whose filesystem path matches *path*.

        Tries DB cache first (via ``CacheManager.get_project_by_path``);
        falls back to filesystem existence check.

        Args:
            path: Absolute filesystem path (will be resolved).
            ctx: Optional per-request metadata (unused here).

        Returns:
            :class:`ProjectDTO` when found, ``None`` otherwise.
        """
        resolved = str(Path(path).expanduser().resolve())

        if self._cache_manager is not None:
            try:
                orm_project = self._cache_manager.get_project_by_path(resolved)
                if orm_project is not None:
                    return _project_orm_to_dto(orm_project)
            except Exception as exc:
                logger.debug(
                    "get_by_path(): DB lookup failed for %r: %s", resolved, exc
                )

        # Filesystem fallback
        project_path = Path(resolved)
        if project_path.is_dir():
            return _build_project_dto_from_path(project_path)

        return None

    def get_or_create_by_path(
        self,
        path: str,
        ctx: Optional[RequestContext] = None,
    ) -> ProjectDTO:
        """Return the project for *path*, creating a DB record if absent.

        Resolves *path* to an absolute string, looks up an existing project,
        and calls :meth:`create` if none is found.

        Args:
            path: Absolute filesystem path (will be resolved).
            ctx: Optional per-request metadata (unused here).

        Returns:
            A :class:`ProjectDTO` (existing or newly created).
        """
        resolved = str(Path(path).expanduser().resolve())
        existing = self.get_by_path(resolved, ctx)
        if existing is not None:
            return existing

        project_id = _encode_project_id(resolved)
        dto = ProjectDTO(
            id=project_id,
            name=Path(resolved).name,
            path=resolved,
            status="active",
        )
        return self.create(dto, ctx)
