"""Local DB-backed implementation of IMarketplaceSourceRepository.

Wraps the low-level :class:`~skillmeat.cache.repositories.MarketplaceSourceRepository`
and :class:`~skillmeat.cache.repositories.MarketplaceCatalogRepository` ORM
repositories, converting ORM models to the DTO types required by the
:class:`~skillmeat.core.interfaces.repositories.IMarketplaceSourceRepository`
interface contract.

Design notes
------------
* No business logic lives here — only data access and DTO conversion.
* The ``import_item`` method delegates to
  :class:`~skillmeat.core.marketplace.import_coordinator.ImportCoordinator`
  which handles filesystem writes, DB population, and conflict resolution.
* ``get_composite_members`` queries ``CompositeMembership`` + ``Artifact``
  tables directly to return child members of a composite artifact.
* All DB access goes through short-lived SQLAlchemy sessions (matching the
  ``BaseRepository`` pattern in ``cache/repositories.py``).
* Errors from the ORM layer (``NotFoundError``, ``ConstraintError``) are
  re-raised as ``KeyError`` / ``ValueError`` to match the interface contract.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from skillmeat.core.interfaces.context import RequestContext

if TYPE_CHECKING:
    from skillmeat.api.schemas.auth import AuthContext
from skillmeat.core.interfaces.dtos import ArtifactDTO, CatalogItemDTO, MarketplaceSourceDTO
from skillmeat.core.interfaces.repositories import IMarketplaceSourceRepository

# ---------------------------------------------------------------------------
# Optional DB imports — graceful degradation when cache module is absent.
# ---------------------------------------------------------------------------
try:
    from skillmeat.cache.models import (
        Artifact as _DBArtifact,
        CompositeMembership as _DBCompositeMembership,
        MarketplaceCatalogEntry as _DBCatalogEntry,
        MarketplaceSource as _DBSource,
        get_session as _get_db_session,
    )
    from skillmeat.cache.repositories import (
        ConstraintError as _ConstraintError,
        MarketplaceCatalogRepository as _CatalogRepo,
        MarketplaceSourceRepository as _SourceRepo,
        NotFoundError as _NotFoundError,
    )

    _db_available = True
except ImportError:  # pragma: no cover
    _get_db_session = None  # type: ignore[assignment]
    _DBArtifact = None  # type: ignore[assignment]
    _DBCompositeMembership = None  # type: ignore[assignment]
    _DBCatalogEntry = None  # type: ignore[assignment]
    _DBSource = None  # type: ignore[assignment]
    _SourceRepo = None  # type: ignore[assignment]
    _CatalogRepo = None  # type: ignore[assignment]
    _ConstraintError = Exception  # type: ignore[assignment,misc]
    _NotFoundError = Exception  # type: ignore[assignment,misc]
    _db_available = False

# ---------------------------------------------------------------------------
# Optional ImportCoordinator — only required for import_item.
# ---------------------------------------------------------------------------
try:
    from skillmeat.core.marketplace.import_coordinator import (
        ConflictStrategy as _ConflictStrategy,
        ImportCoordinator as _ImportCoordinator,
    )

    _import_available = True
except ImportError:  # pragma: no cover
    _ImportCoordinator = None  # type: ignore[assignment,misc]
    _ConflictStrategy = None  # type: ignore[assignment,misc]
    _import_available = False

logger = logging.getLogger(__name__)

__all__ = ["LocalMarketplaceSourceRepository"]

# ---------------------------------------------------------------------------
# DTO conversion helpers
# ---------------------------------------------------------------------------

_VALID_UPDATE_FIELDS = frozenset(
    {"enabled", "endpoint", "description", "supports_publish"}
)


def _source_orm_to_dto(source: Any) -> MarketplaceSourceDTO:
    """Convert a :class:`~skillmeat.cache.models.MarketplaceSource` ORM row to DTO.

    The ORM model is a GitHub-repo–centric object.  We map its fields onto the
    broker-centric :class:`~skillmeat.core.interfaces.dtos.MarketplaceSourceDTO`
    contract as follows:

    * ``id``              → ``id``
    * ``description``     → ``name``  (user description is the human label; fall
                             back to ``repo_name`` when absent)
    * ``enabled`` field   → ``enabled`` (derived from ``scan_status != 'error'``
                             since the ORM has no dedicated enabled boolean)
    * ``repo_url``        → ``endpoint``
    * ``description``     → ``description``
    * ``supports_publish``→ always ``False`` (ORM has no publish flag)

    Args:
        source: A :class:`~skillmeat.cache.models.MarketplaceSource` ORM instance.

    Returns:
        A populated :class:`~skillmeat.core.interfaces.dtos.MarketplaceSourceDTO`.
    """
    # Derive a human-readable name: prefer user-provided description, else repo_name.
    name = (
        source.description
        or getattr(source, "repo_name", None)
        or source.id
    )
    # There is no "enabled" boolean on the ORM; treat non-error sources as enabled.
    scan_status = getattr(source, "scan_status", "pending")
    enabled = scan_status != "error"

    created_at = None
    updated_at = None
    if getattr(source, "created_at", None) is not None:
        try:
            created_at = source.created_at.isoformat()
        except AttributeError:
            created_at = str(source.created_at)
    if getattr(source, "updated_at", None) is not None:
        try:
            updated_at = source.updated_at.isoformat()
        except AttributeError:
            updated_at = str(source.updated_at)

    return MarketplaceSourceDTO(
        id=source.id,
        name=name,
        enabled=enabled,
        endpoint=getattr(source, "repo_url", "") or "",
        description=getattr(source, "description", None),
        supports_publish=False,
        created_at=created_at,
        updated_at=updated_at,
    )


def _catalog_orm_to_dto(entry: Any) -> CatalogItemDTO:
    """Convert a :class:`~skillmeat.cache.models.MarketplaceCatalogEntry` ORM row to DTO.

    Args:
        entry: A :class:`~skillmeat.cache.models.MarketplaceCatalogEntry` ORM instance.

    Returns:
        A populated :class:`~skillmeat.core.interfaces.dtos.CatalogItemDTO`.
    """
    # Parse tags from search_tags JSON column
    tags: List[str] = []
    raw_tags = getattr(entry, "search_tags", None)
    if raw_tags:
        try:
            tags = list(json.loads(raw_tags))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    detected_at = None
    if getattr(entry, "detected_at", None) is not None:
        try:
            detected_at = entry.detected_at.isoformat()
        except AttributeError:
            detected_at = str(entry.detected_at)

    return CatalogItemDTO(
        listing_id=entry.id,
        name=entry.name,
        source_id=getattr(entry, "source_id", None),
        publisher=None,
        description=getattr(entry, "description", None),
        license=None,
        version=getattr(entry, "detected_version", None),
        artifact_count=1,
        tags=tags,
        source_url=getattr(entry, "upstream_url", None),
        bundle_url=None,
        signature=None,
        downloads=0,
        rating=None,
        price=None,
        created_at=detected_at,
    )


def _db_artifact_to_dto(artifact: Any) -> ArtifactDTO:
    """Convert a :class:`~skillmeat.cache.models.Artifact` ORM row to :class:`ArtifactDTO`.

    Args:
        artifact: A :class:`~skillmeat.cache.models.Artifact` ORM instance.

    Returns:
        A populated :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`.
    """
    created_at = None
    updated_at = None
    if getattr(artifact, "created_at", None) is not None:
        try:
            created_at = artifact.created_at.isoformat()
        except AttributeError:
            created_at = str(artifact.created_at)
    if getattr(artifact, "updated_at", None) is not None:
        try:
            updated_at = artifact.updated_at.isoformat()
        except AttributeError:
            updated_at = str(artifact.updated_at)

    return ArtifactDTO(
        id=artifact.id,
        name=artifact.name,
        artifact_type=artifact.type,
        uuid=getattr(artifact, "uuid", None),
        source=getattr(artifact, "source", None),
        version=getattr(artifact, "deployed_version", None),
        scope=None,
        description=None,
        content_path=None,
        metadata={},
        tags=[],
        is_outdated=bool(getattr(artifact, "is_outdated", False)),
        local_modified=bool(getattr(artifact, "local_modified", False)),
        project_id=getattr(artifact, "project_id", None),
        created_at=created_at,
        updated_at=updated_at,
    )


# ---------------------------------------------------------------------------
# Repository implementation
# ---------------------------------------------------------------------------


class LocalMarketplaceSourceRepository(IMarketplaceSourceRepository):
    """SQLite-DB-backed :class:`IMarketplaceSourceRepository` implementation.

    Wraps :class:`~skillmeat.cache.repositories.MarketplaceSourceRepository`
    and :class:`~skillmeat.cache.repositories.MarketplaceCatalogRepository`
    to provide the full interface contract, converting ORM rows to DTOs at
    the boundary.

    Args:
        db_path: Optional filesystem path to the SQLite database.  Passed
            through to the underlying ORM repositories.  When ``None`` the
            repositories use the default path configured via
            ``skillmeat.cache.models.get_session``.

    Example::

        repo = LocalMarketplaceSourceRepository()
        sources = repo.list_sources()
        for src in sources:
            print(src.id, src.endpoint)
    """

    def __init__(self, db_path: Optional[Any] = None) -> None:
        self._db_path = db_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _source_repo(self) -> Any:
        """Return a fresh :class:`~skillmeat.cache.repositories.MarketplaceSourceRepository`."""
        if not _db_available:
            raise RuntimeError(
                "skillmeat.cache is not available — cannot use LocalMarketplaceSourceRepository"
            )
        return _SourceRepo(self._db_path)

    def _catalog_repo(self) -> Any:
        """Return a fresh :class:`~skillmeat.cache.repositories.MarketplaceCatalogRepository`."""
        if not _db_available:
            raise RuntimeError(
                "skillmeat.cache is not available — cannot use LocalMarketplaceSourceRepository"
            )
        return _CatalogRepo(self._db_path)

    # ------------------------------------------------------------------
    # Source CRUD
    # ------------------------------------------------------------------

    def list_sources(
        self,
        filters: Optional[Dict[str, Any]] = None,
        ctx: Optional[RequestContext] = None,
        auth_context: Optional[AuthContext] = None,
    ) -> List[MarketplaceSourceDTO]:
        """Return all configured marketplace sources.

        Args:
            filters: Optional filter map.  Supported keys:
                ``"enabled"`` (bool) — when ``True`` return only non-error
                sources; when ``False`` return only error sources.
            ctx: Optional per-request metadata (unused in local backend).

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.MarketplaceSourceDTO`
            objects.
        """
        repo = self._source_repo()
        sources = repo.list_all()
        dtos = [_source_orm_to_dto(s) for s in sources]

        if filters:
            enabled_filter = filters.get("enabled")
            if enabled_filter is not None:
                wanted = bool(enabled_filter)
                dtos = [d for d in dtos if d.enabled == wanted]

        logger.debug("list_sources: returning %d sources", len(dtos))
        return dtos

    def get_source(
        self,
        source_id: str,
        ctx: Optional[RequestContext] = None,
        auth_context: Optional[AuthContext] = None,
    ) -> Optional[MarketplaceSourceDTO]:
        """Return a marketplace source by its identifier.

        Args:
            source_id: Source unique identifier.
            ctx: Optional per-request metadata.

        Returns:
            A :class:`~skillmeat.core.interfaces.dtos.MarketplaceSourceDTO`
            when found, ``None`` otherwise.
        """
        repo = self._source_repo()
        source = repo.get_by_id(source_id)
        if source is None:
            return None
        return _source_orm_to_dto(source)

    def create_source(
        self,
        name: str,
        endpoint: str,
        enabled: bool = True,
        description: Optional[str] = None,
        supports_publish: bool = False,
        ctx: Optional[RequestContext] = None,
        auth_context: Optional[AuthContext] = None,
    ) -> MarketplaceSourceDTO:
        """Register a new marketplace source.

        The ``endpoint`` is treated as the GitHub repository URL.  A unique
        identifier is generated automatically.

        Args:
            name: Human-readable source name (used as ``description``).
            endpoint: Base URL for the broker API / GitHub repository URL.
            enabled: Whether to activate the source immediately.  When
                ``False`` the source is created with ``scan_status="error"``
                so that ``list_sources(filters={"enabled": True})`` excludes it.
            description: Optional description (stored in the ORM
                ``description`` field).
            supports_publish: Ignored — the local ORM has no publish flag.
            ctx: Optional per-request metadata.

        Returns:
            The created :class:`~skillmeat.core.interfaces.dtos.MarketplaceSourceDTO`.

        Raises:
            ValueError: If a source with the same *endpoint* (repo URL) already
                exists (maps ``ConstraintError`` → ``ValueError``).
        """
        if not _db_available:
            raise RuntimeError("skillmeat.cache unavailable")

        # Derive owner/repo_name from the endpoint URL when possible.
        repo_url = endpoint or ""
        owner = ""
        repo_name = name
        if "/github.com/" in repo_url:
            parts = repo_url.rstrip("/").split("/github.com/", 1)[-1].split("/")
            if len(parts) >= 2:
                owner = parts[0]
                repo_name = parts[1]

        source_orm = _DBSource(
            id=str(uuid.uuid4()),
            repo_url=repo_url,
            owner=owner,
            repo_name=repo_name,
            ref="main",
            description=description or name,
            scan_status="pending" if enabled else "error",
        )

        repo = self._source_repo()
        try:
            created = repo.create(source_orm)
        except _ConstraintError as exc:
            raise ValueError(str(exc)) from exc

        logger.info("create_source: created source %s (%s)", created.id, endpoint)
        return _source_orm_to_dto(created)

    def update_source(
        self,
        source_id: str,
        updates: Dict[str, Any],
        ctx: Optional[RequestContext] = None,
        auth_context: Optional[AuthContext] = None,
    ) -> MarketplaceSourceDTO:
        """Apply a partial update to a marketplace source configuration.

        Supported keys in ``updates``:
        - ``"enabled"`` (bool): Changes ``scan_status`` between
          ``"pending"`` and ``"error"`` to reflect enabled/disabled state.
        - ``"endpoint"`` (str): Updates ``repo_url``.
        - ``"description"`` (str): Updates the ``description`` field.
        - ``"supports_publish"`` (bool): No-op (ORM has no publish flag).

        Args:
            source_id: Source unique identifier.
            updates: Partial field map.
            ctx: Optional per-request metadata.

        Returns:
            The updated :class:`~skillmeat.core.interfaces.dtos.MarketplaceSourceDTO`.

        Raises:
            KeyError: If no source with *source_id* exists.
        """
        repo = self._source_repo()
        source_orm = repo.get_by_id(source_id)
        if source_orm is None:
            raise KeyError(f"Marketplace source '{source_id}' not found")

        kwargs: Dict[str, Any] = {}

        if "enabled" in updates:
            # Map enabled boolean to scan_status heuristic
            source_orm.scan_status = "pending" if updates["enabled"] else "error"

        if "endpoint" in updates:
            source_orm.repo_url = updates["endpoint"]
            # Re-derive owner/repo_name
            new_url = updates["endpoint"] or ""
            if "/github.com/" in new_url:
                parts = new_url.rstrip("/").split("/github.com/", 1)[-1].split("/")
                if len(parts) >= 2:
                    source_orm.owner = parts[0]
                    source_orm.repo_name = parts[1]

        if "description" in updates:
            kwargs["description"] = updates["description"]

        if kwargs:
            try:
                updated = repo.update_fields(source_id, **kwargs)
                return _source_orm_to_dto(updated)
            except _NotFoundError as exc:
                raise KeyError(str(exc)) from exc

        # If only non-kwarg fields were changed, save via update().
        try:
            updated = repo.update(source_orm)
        except _NotFoundError as exc:
            raise KeyError(str(exc)) from exc

        logger.info("update_source: updated source %s", source_id)
        return _source_orm_to_dto(updated)

    def delete_source(
        self,
        source_id: str,
        ctx: Optional[RequestContext] = None,
        auth_context: Optional[AuthContext] = None,
    ) -> None:
        """Remove a marketplace source configuration.

        Args:
            source_id: Source unique identifier.
            ctx: Optional per-request metadata.

        Raises:
            KeyError: If no source with *source_id* exists.
        """
        repo = self._source_repo()
        deleted = repo.delete(source_id)
        if not deleted:
            raise KeyError(f"Marketplace source '{source_id}' not found")
        logger.info("delete_source: deleted source %s", source_id)

    # ------------------------------------------------------------------
    # Catalog operations
    # ------------------------------------------------------------------

    def list_catalog_items(
        self,
        source_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        limit: int = 50,
        ctx: Optional[RequestContext] = None,
        auth_context: Optional[AuthContext] = None,
    ) -> List[CatalogItemDTO]:
        """Return paginated catalog listings from one or all sources.

        Args:
            source_id: When provided, restrict results to this broker.
                When ``None``, aggregate listings from all enabled sources.
            filters: Optional key/value filter map.  Supported keys:
                ``"query"`` (str) — substring match on ``name``/``description``;
                ``"tags"`` (list[str]) — entries must include at least one tag;
                ``"status"`` (str) — match on the ORM ``status`` field.
            page: One-based page number for pagination.
            limit: Maximum items per page (1-100).
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.CatalogItemDTO` objects.
        """
        catalog = self._catalog_repo()

        # Fetch raw ORM entries
        if source_id is not None:
            entries = catalog.list_by_source(source_id)
        else:
            # Aggregate from all sources.
            source_repo = self._source_repo()
            all_sources = source_repo.list_all()
            entries = []
            for src in all_sources:
                entries.extend(catalog.list_by_source(src.id))

        # Apply optional filters
        if filters:
            query_term = (filters.get("query") or "").lower()
            tag_filter: List[str] = [t.lower() for t in (filters.get("tags") or [])]
            status_filter: Optional[str] = filters.get("status")

            filtered = []
            for entry in entries:
                if query_term:
                    name = (entry.name or "").lower()
                    desc = (getattr(entry, "description", None) or "").lower()
                    if query_term not in name and query_term not in desc:
                        continue
                if tag_filter:
                    raw_tags = getattr(entry, "search_tags", None)
                    try:
                        entry_tags = [t.lower() for t in json.loads(raw_tags or "[]")]
                    except (json.JSONDecodeError, TypeError):
                        entry_tags = []
                    if not any(t in entry_tags for t in tag_filter):
                        continue
                if status_filter is not None:
                    if getattr(entry, "status", None) != status_filter:
                        continue
                filtered.append(entry)
            entries = filtered

        # Paginate
        offset = (page - 1) * limit
        page_entries = entries[offset : offset + limit]

        dtos = [_catalog_orm_to_dto(e) for e in page_entries]
        logger.debug(
            "list_catalog_items source=%s page=%d limit=%d -> %d items",
            source_id,
            page,
            limit,
            len(dtos),
        )
        return dtos

    def import_item(
        self,
        listing_id: str,
        source_id: Optional[str] = None,
        strategy: str = "keep",
        ctx: Optional[RequestContext] = None,
        auth_context: Optional[AuthContext] = None,
    ) -> List[ArtifactDTO]:
        """Download and import a marketplace listing into the local collection.

        Delegates to :class:`~skillmeat.core.marketplace.import_coordinator.ImportCoordinator`
        which handles filesystem writes, DB cache population, and conflict
        resolution.  Requires ``skillmeat.core.marketplace.import_coordinator``
        to be importable.

        Args:
            listing_id: Unique identifier of the catalog entry within its
                broker (maps to ``MarketplaceCatalogEntry.id``).
            source_id: Optional broker identifier.  When ``None`` the
                implementation looks up the entry and derives the source.
            strategy: Conflict resolution strategy (``"keep"``, ``"replace"``,
                or ``"fork"``).
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`
            objects representing all imported artifacts.

        Raises:
            KeyError: If *listing_id* is not found in any enabled source.
            ValueError: If *strategy* is not a recognised value or
                ``ImportCoordinator`` is unavailable.
            RuntimeError: If the DB cache is not available.
        """
        if not _import_available or _ImportCoordinator is None:
            raise ValueError(
                "ImportCoordinator is not available — cannot import from marketplace"
            )
        if not _db_available:
            raise RuntimeError("skillmeat.cache unavailable")

        # Validate strategy
        valid_strategies = {"keep", "replace", "fork"}
        if strategy not in valid_strategies:
            raise ValueError(
                f"Invalid conflict strategy '{strategy}'. "
                f"Expected one of: {', '.join(sorted(valid_strategies))}"
            )

        catalog = self._catalog_repo()
        entry = catalog.get_by_id(listing_id)
        if entry is None:
            raise KeyError(f"Catalog entry '{listing_id}' not found")

        # Resolve / validate source_id
        entry_source_id = getattr(entry, "source_id", None)
        if source_id is not None and entry_source_id != source_id:
            raise KeyError(
                f"Catalog entry '{listing_id}' does not belong to source '{source_id}'"
            )
        resolved_source_id = source_id or entry_source_id

        source_repo = self._source_repo()
        source = source_repo.get_by_id(resolved_source_id) if resolved_source_id else None
        source_ref = getattr(source, "ref", "main") if source else "main"

        # Build entry dict for ImportCoordinator
        tags: List[str] = []
        raw_tags = getattr(entry, "search_tags", None)
        if raw_tags:
            try:
                tags = list(json.loads(raw_tags))
            except (json.JSONDecodeError, TypeError):
                pass

        entry_dict = {
            "id": entry.id,
            "artifact_type": entry.artifact_type,
            "name": entry.name,
            "upstream_url": entry.upstream_url,
            "path": entry.path,
            "description": getattr(entry, "description", None),
            "tags": tags,
        }

        coordinator = _ImportCoordinator(
            collection_name="default",
            collection_mgr=None,  # ImportCoordinator constructs its own when None
        )
        conflict_strategy = _ConflictStrategy(strategy)
        import_result = coordinator.import_entries(
            entries=[entry_dict],
            source_id=resolved_source_id or "",
            strategy=conflict_strategy,
            source_ref=source_ref,
        )

        # Collect successfully imported artifact IDs from the result
        result_dtos: List[ArtifactDTO] = []
        if hasattr(import_result, "imported") and import_result.imported:
            for imported_entry in import_result.imported:
                artifact_id = (
                    imported_entry.get("artifact_id")
                    or imported_entry.get("id")
                )
                if not artifact_id:
                    continue
                # Try to look up from DB cache
                if _get_db_session is not None:
                    session = _get_db_session()
                    try:
                        db_artifact = (
                            session.query(_DBArtifact)
                            .filter(_DBArtifact.id == artifact_id)
                            .first()
                        )
                        if db_artifact is not None:
                            result_dtos.append(_db_artifact_to_dto(db_artifact))
                            continue
                    finally:
                        session.close()
                # Fallback: build a minimal DTO from import result dict
                result_dtos.append(
                    ArtifactDTO(
                        id=artifact_id,
                        name=imported_entry.get("name", ""),
                        artifact_type=imported_entry.get("artifact_type", ""),
                        uuid=None,
                        source=imported_entry.get("upstream_url"),
                        version=None,
                        scope=None,
                        description=imported_entry.get("description"),
                        content_path=None,
                        metadata={},
                        tags=list(imported_entry.get("tags", []) or []),
                        is_outdated=False,
                        local_modified=False,
                        project_id=None,
                        created_at=None,
                        updated_at=None,
                    )
                )

        logger.info(
            "import_item: imported listing_id=%s -> %d artifact(s)",
            listing_id,
            len(result_dtos),
        )
        return result_dtos

    def get_composite_members(
        self,
        composite_id: str,
        ctx: Optional[RequestContext] = None,
        auth_context: Optional[AuthContext] = None,
    ) -> List[ArtifactDTO]:
        """Return the child artifacts that make up a composite listing.

        Queries the ``composite_memberships`` join table to find all child
        artifact UUIDs, then hydrates full ``Artifact`` rows ordered by the
        ``position`` field.

        Args:
            composite_id: Artifact primary key of the composite artifact
                (``"composite:<name>"``).
            ctx: Optional per-request metadata.

        Returns:
            List of :class:`~skillmeat.core.interfaces.dtos.ArtifactDTO`
            objects for each member artifact, ordered by ``position``.

        Raises:
            KeyError: If *composite_id* does not exist or is not a composite
                artifact.
            RuntimeError: If the DB cache is not available.
        """
        if not _db_available or _get_db_session is None:
            raise RuntimeError("skillmeat.cache unavailable")

        session = _get_db_session()
        try:
            # Verify the composite artifact exists
            composite_artifact = (
                session.query(_DBArtifact)
                .filter(_DBArtifact.id == composite_id)
                .first()
            )
            if composite_artifact is None:
                raise KeyError(f"Composite artifact '{composite_id}' not found")

            artifact_type = getattr(composite_artifact, "type", "")
            if artifact_type != "composite":
                raise KeyError(
                    f"Artifact '{composite_id}' is not a composite "
                    f"(type={artifact_type!r})"
                )

            # Query memberships ordered by position
            memberships = (
                session.query(_DBCompositeMembership)
                .filter(_DBCompositeMembership.composite_id == composite_id)
                .order_by(_DBCompositeMembership.position)
                .all()
            )

            if not memberships:
                logger.debug(
                    "get_composite_members: no members for composite '%s'", composite_id
                )
                return []

            # Collect child UUIDs in order
            child_uuids = [m.child_artifact_uuid for m in memberships]

            # Hydrate Artifact rows preserving position order
            artifact_map: Dict[str, Any] = {}
            rows = (
                session.query(_DBArtifact)
                .filter(_DBArtifact.uuid.in_(child_uuids))
                .all()
            )
            for row in rows:
                artifact_map[row.uuid] = row

            result: List[ArtifactDTO] = []
            for child_uuid in child_uuids:
                artifact = artifact_map.get(child_uuid)
                if artifact is None:
                    logger.warning(
                        "get_composite_members: child uuid %s not found in artifacts table",
                        child_uuid,
                    )
                    continue
                result.append(_db_artifact_to_dto(artifact))

            logger.debug(
                "get_composite_members: composite '%s' -> %d members",
                composite_id,
                len(result),
            )
            return result
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Catalog entry mutations (encapsulate direct session access)
    # ------------------------------------------------------------------

    def get_catalog_entry_raw(
        self,
        entry_id: str,
        source_id: Optional[str] = None,
        ctx: Optional[RequestContext] = None,
        auth_context: Optional[AuthContext] = None,
    ) -> Optional[Any]:
        """Return the raw ORM ``MarketplaceCatalogEntry`` object.

        Delegates to :meth:`MarketplaceCatalogRepository.get_with_path_segments`
        when *source_id* is provided (validates ownership), or falls back to
        :meth:`MarketplaceCatalogRepository.get_by_id`.

        Args:
            entry_id: Catalog entry primary key.
            source_id: When provided, verifies the entry belongs to this source.
            ctx: Optional per-request metadata.

        Returns:
            The ORM entry object when found, ``None`` otherwise.
        """
        catalog = self._catalog_repo()
        if source_id is not None:
            return catalog.get_with_path_segments(entry_id, source_id)
        return catalog.get_by_id(entry_id)

    def update_catalog_entry_exclusion(
        self,
        entry_id: str,
        source_id: str,
        excluded: bool,
        reason: Optional[str] = None,
        ctx: Optional[RequestContext] = None,
        auth_context: Optional[AuthContext] = None,
    ) -> Any:
        """Toggle exclusion status on a catalog entry.

        Delegates to :meth:`MarketplaceCatalogRepository.set_exclusion`.

        Args:
            entry_id: Catalog entry primary key.
            source_id: Source the entry must belong to.
            excluded: ``True`` to exclude, ``False`` to restore.
            reason: Optional reason text (only used when *excluded* is ``True``).
            ctx: Optional per-request metadata.

        Returns:
            The updated ORM ``MarketplaceCatalogEntry`` object.

        Raises:
            KeyError: If *entry_id* not found.
            ValueError: If the entry does not belong to *source_id*.
        """
        catalog = self._catalog_repo()
        entry = catalog.set_exclusion(entry_id, source_id, excluded, reason)
        if entry is None:
            raise KeyError(f"Catalog entry '{entry_id}' not found")
        return entry

    def update_catalog_entry_path_tags(
        self,
        entry_id: str,
        source_id: str,
        path_segments_json: str,
        ctx: Optional[RequestContext] = None,
        auth_context: Optional[AuthContext] = None,
    ) -> Any:
        """Persist updated ``path_segments`` JSON for a catalog entry.

        Delegates to :meth:`MarketplaceCatalogRepository.update_path_segments`.

        Args:
            entry_id: Catalog entry primary key.
            source_id: Source the entry must belong to.
            path_segments_json: Serialised JSON string.
            ctx: Optional per-request metadata.

        Returns:
            The updated ORM ``MarketplaceCatalogEntry`` object.

        Raises:
            KeyError: If *entry_id* not found or does not belong to *source_id*.
        """
        catalog = self._catalog_repo()
        entry = catalog.update_path_segments(entry_id, source_id, path_segments_json)
        if entry is None:
            raise KeyError(
                f"Catalog entry '{entry_id}' not found in source '{source_id}'"
            )
        return entry

    def get_artifact_row(
        self,
        artifact_id: str,
        ctx: Optional[RequestContext] = None,
        auth_context: Optional[AuthContext] = None,
    ) -> Optional[Any]:
        """Return the raw ORM ``Artifact`` row for the given ``type:name`` id.

        Args:
            artifact_id: Artifact primary key in ``"type:name"`` format.
            ctx: Optional per-request metadata.

        Returns:
            The ORM ``Artifact`` object (expunged) when found, ``None`` otherwise.
        """
        if not _db_available or _get_db_session is None:
            raise RuntimeError("skillmeat.cache unavailable")
        session = _get_db_session()
        try:
            artifact = (
                session.query(_DBArtifact)
                .filter(_DBArtifact.id == artifact_id)
                .first()
            )
            if artifact is None:
                return None
            session.expunge(artifact)
            return artifact
        finally:
            session.close()

    def upsert_composite_memberships(
        self,
        composite_id: str,
        child_artifact_ids: List[str],
        collection_id: str,
        ctx: Optional[RequestContext] = None,
        auth_context: Optional[AuthContext] = None,
    ) -> int:
        """Create or update ``CompositeMembership`` rows.

        For each child artifact ID the method resolves the ``Artifact.uuid``
        and inserts a ``CompositeMembership`` row when one does not exist.
        Existing rows are updated to reflect the current position.

        Args:
            composite_id: Primary key of the composite (``"composite:<name>"``).
            child_artifact_ids: Ordered list of child ``type:name`` IDs.
            collection_id: Collection the composite belongs to.
            ctx: Optional per-request metadata.

        Returns:
            Number of new membership rows created.
        """
        if not _db_available or _get_db_session is None:
            raise RuntimeError("skillmeat.cache unavailable")
        session = _get_db_session()
        membership_count = 0
        try:
            for idx, child_artifact_id in enumerate(child_artifact_ids):
                artifact_row = (
                    session.query(_DBArtifact)
                    .filter(_DBArtifact.id == child_artifact_id)
                    .first()
                )
                if artifact_row is None:
                    logger.debug(
                        "upsert_composite_memberships: artifact row not found for '%s', skipping",
                        child_artifact_id,
                    )
                    continue

                existing = (
                    session.query(_DBCompositeMembership)
                    .filter(
                        _DBCompositeMembership.collection_id == collection_id,
                        _DBCompositeMembership.composite_id == composite_id,
                        _DBCompositeMembership.child_artifact_uuid == artifact_row.uuid,
                    )
                    .first()
                )
                if existing is None:
                    membership = _DBCompositeMembership(
                        collection_id=collection_id,
                        composite_id=composite_id,
                        child_artifact_uuid=artifact_row.uuid,
                        relationship_type="contains",
                        pinned_version_hash=None,
                        position=idx,
                    )
                    session.add(membership)
                    membership_count += 1
                else:
                    existing.position = idx

            session.commit()
            logger.info(
                "upsert_composite_memberships: created %d row(s) for composite '%s' "
                "(%d child target(s))",
                membership_count,
                composite_id,
                len(child_artifact_ids),
            )
            return membership_count
        except Exception as err:
            session.rollback()
            logger.warning(
                "upsert_composite_memberships: failed for '%s': %s", composite_id, err
            )
            raise
        finally:
            session.close()

    def commit_source_session(
        self,
        ctx: Optional[RequestContext] = None,
        auth_context: Optional[AuthContext] = None,
    ) -> None:
        """Flush pending changes on the underlying source repository session.

        Opens a fresh session via the source repository and commits it.
        Intended for workflows that mutate ORM objects obtained from
        ``_source_repo()`` directly (e.g. setting ``auto_tags``).

        Args:
            ctx: Optional per-request metadata.
        """
        if not _db_available or _get_db_session is None:
            raise RuntimeError("skillmeat.cache unavailable")
        session = _get_db_session()
        try:
            session.commit()
        finally:
            session.close()
