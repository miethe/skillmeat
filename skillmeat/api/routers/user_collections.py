"""User Collections API endpoints.

Provides REST API for managing database-backed user collections (organizational).
Distinct from file-based collections in collections.py router.
"""

import base64
import json
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Body, HTTPException, Query, status

from skillmeat.api.dependencies import (
    ArtifactManagerDep,
    ArtifactRepoDep,
    CollectionManagerDep,
    DbCollectionArtifactRepoDep,
    DbSessionDep,
    DbUserCollectionRepoDep,
    GroupRepoDep,
    ProjectRepoDep,
    get_auth_context,
    require_auth,
)
from skillmeat.core.interfaces.dtos import UserCollectionDTO
from skillmeat.core.interfaces.repositories import (
    IDbCollectionArtifactRepository,
    IDbUserCollectionRepository,
    IGroupRepository,
    IProjectRepository,
)
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.auth import AuthContext
from skillmeat.api.schemas.collections import (
    RefreshModeEnum,
    RefreshRequest,
    RefreshResponse,
    UpdateCheckResponse,
)
from skillmeat.api.schemas.common import ErrorResponse, PageInfo
from skillmeat.api.schemas.user_collections import (
    AddArtifactsRequest,
    ArtifactGroupMembership,
    ArtifactSummary,
    CollectionArtifactsResponse,
    GroupSummary,
    UserCollectionCreateRequest,
    UserCollectionListResponse,
    UserCollectionResponse,
    UserCollectionUpdateRequest,
    UserCollectionWithGroupsResponse,
)
from skillmeat.api.services import get_artifact_metadata
from skillmeat.api.services.artifact_cache_service import (
    invalidate_collection_artifacts,
    parse_deployments,
)
from skillmeat.api.services.artifact_metadata_service import _get_artifact_collections
from skillmeat.cache import get_collection_count_cache
from skillmeat.core.artifact import ArtifactType as CoreArtifactType
from skillmeat.core.refresher import CollectionRefresher, RefreshMode, validate_fields
from skillmeat.cache.models import (
    DEFAULT_COLLECTION_ID,
    Project,
)

logger = logging.getLogger(__name__)

# Sentinel project ID for filesystem collection artifacts.
# Satisfies the artifacts.project_id FK constraint for Artifact rows that
# represent collection-level (non-deployed) artifacts.
COLLECTION_ARTIFACTS_PROJECT_ID = "collection_artifacts_global"

router = APIRouter(
    prefix="/user-collections",
    tags=["user-collections"],
)


# =============================================================================
# Helper Functions
# =============================================================================
# Helper functions have been migrated to use repository DI
# (IDbUserCollectionRepository, IDbCollectionArtifactRepository, IGroupRepository)
# in place of direct SQLAlchemy session access.
#
# Remaining direct session/ORM usage is confined to functions that have no
# repository ABC counterpart yet (e.g. _ensure_collection_project_sentinel uses
# Project ORM directly because IProjectRepository.ensure_sentinel() is not yet
# defined).  Those cases carry explicit TODO comments.
#
# CRUD endpoint bodies (list, create, get, update, delete) were migrated to
# repository DI in TASK-4.1 and TASK-4.2.  Non-CRUD endpoints (artifact ops,
# cache/sync, entity management) still use DbSessionDep directly — that
# migration is Phase 5 work (TASK-5.1, TASK-5.2).


def encode_cursor(value: str) -> str:
    """Encode a cursor value to base64.

    Args:
        value: Value to encode

    Returns:
        Base64 encoded cursor string
    """
    return base64.b64encode(value.encode()).decode()


def decode_cursor(cursor: str) -> str:
    """Decode a base64 cursor value.

    Args:
        cursor: Base64 encoded cursor

    Returns:
        Decoded cursor value

    Raises:
        HTTPException: If cursor is invalid
    """
    try:
        return base64.b64decode(cursor.encode()).decode()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cursor format: {str(e)}",
        )


def collection_to_response(
    collection_dto: UserCollectionDTO,
    collection_repo: IDbUserCollectionRepository,
) -> UserCollectionResponse:
    """Convert a UserCollectionDTO to an API response model.

    Uses the repository to compute live group and artifact counts rather than
    relying on cached values embedded in the DTO, which may be stale.

    Args:
        collection_dto: DTO representation of the collection.
        collection_repo: Repository used to query live group and artifact counts.

    Returns:
        UserCollectionResponse Pydantic model ready for serialisation.

    Note:
        The previous signature ``(collection: Collection, session: Session)``
        accepted ORM models and a raw SQLAlchemy session.  All CRUD endpoints
        were updated to the repository-based call pattern in TASK-4.1/TASK-4.2.
    """
    group_count = len(collection_repo.get_groups(collection_dto.id))
    artifact_count = collection_repo.get_artifact_count(collection_dto.id)

    def _parse_dt(value: Optional[str]) -> datetime:
        """Parse ISO-8601 string to datetime; fall back to utcnow on failure."""
        if value:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        return datetime.utcnow()

    return UserCollectionResponse(
        id=collection_dto.id,
        name=collection_dto.name,
        description=collection_dto.description,
        created_by=collection_dto.created_by,
        collection_type=collection_dto.collection_type,
        context_category=collection_dto.context_category,
        created_at=_parse_dt(collection_dto.created_at),
        updated_at=_parse_dt(collection_dto.updated_at),
        group_count=group_count,
        artifact_count=artifact_count,
    )


def collection_to_response_with_groups(
    collection_dto: UserCollectionDTO,
    collection_repo: IDbUserCollectionRepository,
    group_repo: IGroupRepository,
) -> UserCollectionWithGroupsResponse:
    """Convert a UserCollectionDTO to an API response model with nested groups.

    Args:
        collection_dto: DTO representation of the collection.
        collection_repo: Repository used to compute live group/artifact counts.
        group_repo: Repository used to list groups belonging to this collection.

    Returns:
        UserCollectionWithGroupsResponse Pydantic model with nested group list.
    """
    base_response = collection_to_response(collection_dto, collection_repo)

    group_dtos = sorted(group_repo.list(collection_dto.id), key=lambda g: g.position)
    groups = [
        GroupSummary(
            id=g.id,
            name=g.name,
            description=g.description,
            position=g.position,
            artifact_count=g.artifact_count,
        )
        for g in group_dtos
    ]

    return UserCollectionWithGroupsResponse(
        **base_response.model_dump(),
        groups=groups,
    )


def ensure_default_collection(
    collection_repo: IDbUserCollectionRepository,
) -> UserCollectionDTO:
    """Ensure the default collection exists, creating it if necessary.

    This function should be called during server startup to guarantee
    the default collection exists for artifact assignments.

    Delegates to :meth:`IDbUserCollectionRepository.ensure_default` which is
    idempotent: concurrent callers will not produce duplicate collections.

    Args:
        collection_repo: Repository used to find or create the default
            collection.

    Returns:
        UserCollectionDTO for the default collection (existing or newly created).
    """
    dto = collection_repo.ensure_default()
    logger.info(
        "ensure_default_collection: verified/created default collection id=%r",
        dto.id,
    )
    return dto


def _ensure_collection_project_sentinel(
    collection_repo: IDbUserCollectionRepository,
) -> None:
    """Ensure the sentinel Project row for collection artifacts exists.

    Artifact rows require a project_id FK. Collection-level (filesystem)
    artifacts are not tied to any real deployed project, so we use a
    sentinel project to satisfy the constraint.

    Delegates to :meth:`IDbUserCollectionRepository.ensure_sentinel_project`
    which manages its own session and transaction.
    """
    collection_repo.ensure_sentinel_project()
    logger.debug(f"Ensured sentinel project '{COLLECTION_ARTIFACTS_PROJECT_ID}'")


def _ensure_artifacts_in_cache(
    artifact_mgr,
    collection_mgr,
    collection_repo: IDbUserCollectionRepository,
    artifact_repo_ca: IDbCollectionArtifactRepository,
) -> int:
    """Ensure every filesystem artifact has a corresponding Artifact ORM row.

    The collection_artifacts table uses artifact_uuid as a FK to artifacts.uuid.
    If no Artifact row exists for a given type:name id, _resolve_artifact_uuid()
    returns None and the artifact is skipped during migrate/populate phases.

    This function must be called before populate_collection_artifact_metadata()
    and migrate_artifacts_to_default_collection() process their artifacts.

    Args:
        artifact_mgr: ArtifactManager for listing filesystem artifacts
        collection_mgr: CollectionManager for enumerating collections
        collection_repo: IDbUserCollectionRepository for sentinel project bootstrap
        artifact_repo_ca: IDbCollectionArtifactRepository for artifact row creation

    Returns:
        Number of Artifact rows created

    """
    _ensure_collection_project_sentinel(collection_repo)

    # Gather all filesystem artifacts across all collections
    all_artifacts: list = []
    for coll_name in collection_mgr.list_collections():
        try:
            artifacts = artifact_mgr.list_artifacts(collection_name=coll_name)
            all_artifacts.extend(artifacts)
        except Exception as e:
            logger.warning(
                f"_ensure_artifacts_in_cache: failed to list '{coll_name}': {e}"
            )
            continue

    # Batch-insert missing artifact rows via the repository
    created_count = artifact_repo_ca.ensure_artifact_rows(
        all_artifacts,
        project_id=COLLECTION_ARTIFACTS_PROJECT_ID,
    )

    if created_count > 0:
        logger.info(
            f"_ensure_artifacts_in_cache: created {created_count} Artifact rows"
        )

    return created_count


def migrate_artifacts_to_default_collection(
    artifact_mgr,
    collection_mgr,
    collection_repo: Optional[IDbUserCollectionRepository] = None,
    artifact_repo_ca: Optional[IDbCollectionArtifactRepository] = None,
    project_repo: Optional[IProjectRepository] = None,
    session=None,
) -> dict:
    """Migrate all existing artifacts to the default collection.

    This function ensures all artifacts from file-system collections
    are also registered in the default database collection, enabling
    them to use Groups and other collection features. Also populates
    the metadata cache for efficient artifact card rendering.

    Args:
        artifact_mgr: Artifact manager for listing artifacts
        collection_mgr: Collection manager for listing collections
        collection_repo: Optional injected IDbUserCollectionRepository.
            When provided (e.g. from an endpoint's DI), used directly.
            Falls back to constructing DbUserCollectionRepository() if None.
        artifact_repo_ca: Optional injected IDbCollectionArtifactRepository.
            When provided, used for batch artifact adds.
            Falls back to constructing DbCollectionArtifactRepository() if None.
        project_repo: Optional injected IProjectRepository for listing project
            paths during deployment scanning.  Falls back to
            constructing LocalProjectRepository() if None.
        session: Optional SQLAlchemy Session forwarded to
            ``_recover_default_collection_metadata``, which delegates to
            ``recover_collection_metadata`` in the service layer.  When None
            a fresh session is obtained internally.

    Returns:
        dict with migration stats: migrated_count, already_present_count,
        total_artifacts, and metadata_cache stats

    """
    # 1. Ensure default collection exists first (prefer injected repo)
    if collection_repo is None:
        from skillmeat.cache.repositories import DbUserCollectionRepository as _CollRepo

        collection_repo = _CollRepo()

    ensure_default_collection(collection_repo)

    # 2. Ensure artifact_repo_ca is initialised before _ensure_artifacts_in_cache.
    if artifact_repo_ca is None:
        from skillmeat.cache.repositories import (
            DbCollectionArtifactRepository as _CaRepo,
        )

        artifact_repo_ca = _CaRepo()

    # 3. Ensure every filesystem artifact has an Artifact ORM row.
    # populate_collection_artifact_metadata() and the migration loop both
    # skip artifacts that are not yet in the artifacts table, so this step
    # must come first.
    ensure_count = _ensure_artifacts_in_cache(
        artifact_mgr, collection_mgr, collection_repo, artifact_repo_ca
    )
    logger.info(f"Artifact cache bootstrap: {ensure_count} new Artifact rows created")

    # 4. Populate metadata cache from file-based artifacts
    # This creates/updates CollectionArtifact rows with full metadata
    # enabling the /collection page to render without N file reads
    metadata_stats = populate_collection_artifact_metadata(
        artifact_mgr,
        collection_mgr,
        collection_repo=collection_repo,
        artifact_repo_ca=artifact_repo_ca,
        project_repo=project_repo,
    )

    # 5. Get all artifacts from all file-system collections
    all_artifact_ids = set()
    for coll_name in collection_mgr.list_collections():
        try:
            artifacts = artifact_mgr.list_artifacts(collection_name=coll_name)
            for artifact in artifacts:
                artifact_id = f"{artifact.type.value}:{artifact.name}"
                all_artifact_ids.add(artifact_id)
        except Exception as e:
            logger.warning(
                f"Failed to load artifacts from collection '{coll_name}': {e}"
            )
            continue

    logger.info(
        f"Found {len(all_artifact_ids)} unique artifacts across all collections"
    )

    # 6. Get existing associations for the default collection via the repository.
    existing_artifact_ids = artifact_repo_ca.list_artifact_ids_in_collection(
        DEFAULT_COLLECTION_ID
    )

    # 7. Find artifacts not yet in default collection
    missing_artifact_ids = all_artifact_ids - existing_artifact_ids

    # 8. Add missing artifacts to default collection.
    # Resolve UUIDs for all missing artifact IDs, then batch-add via repo.
    uuids_to_migrate: list[str] = []
    for artifact_id in missing_artifact_ids:
        try:
            artifact_uuid = artifact_repo_ca.resolve_uuid_by_id(artifact_id)
            if not artifact_uuid:
                logger.debug(
                    f"Skipping migration for '{artifact_id}': not yet in artifacts cache"
                )
                continue
            uuids_to_migrate.append(artifact_uuid)
        except Exception as e:
            logger.warning(f"Failed to resolve UUID for '{artifact_id}': {e}")
            continue

    migrated_count = 0
    if uuids_to_migrate:
        try:
            artifact_repo_ca.add_artifacts(DEFAULT_COLLECTION_ID, uuids_to_migrate)
            migrated_count = len(uuids_to_migrate)
            logger.info(f"Migrated {migrated_count} artifacts to default collection")
        except Exception as e:
            logger.warning(f"Failed to batch-add artifacts to default collection: {e}")

    # 9. Sync tags from CollectionArtifact cache to Tag ORM tables.
    tag_sync_count = _sync_all_tags_to_orm(artifact_repo=artifact_repo_ca)

    # 10. FS → DB Recovery: restore tag definitions and groups from collection.toml
    # This runs AFTER artifacts are populated so that group member resolution works.
    recovery_stats = _recover_default_collection_metadata(session, collection_mgr)

    # 11. Return combined stats including metadata cache results
    return {
        "migrated_count": migrated_count,
        "already_present_count": len(existing_artifact_ids),
        "total_artifacts": len(all_artifact_ids),
        "metadata_cache": metadata_stats,
        "tag_sync_count": tag_sync_count,
        "recovery": recovery_stats,
    }


def _sync_all_tags_to_orm(
    artifact_repo: Optional[IDbCollectionArtifactRepository] = None,
) -> int:
    """Sync all CollectionArtifact tags to the Tag ORM tables.

    Iterates all CollectionArtifact rows with tags_json and calls
    TagService.sync_artifact_tags() for each. Tag sync failure does
    NOT block the caller.

    Args:
        artifact_repo: Optional injected IDbCollectionArtifactRepository.
            When provided, uses list_all_with_tags() to retrieve tagged
            artifacts across all collections.  When None, a fresh
            DbCollectionArtifactRepository is constructed internally.

    Returns:
        Number of artifacts successfully synced.
    """
    try:
        from skillmeat.core.services import TagService

        tag_service = TagService()
    except Exception as e:
        logger.warning(f"Failed to initialize TagService for bulk tag sync: {e}")
        return 0

    # Resolve repository; fall back to constructing one if not injected.
    if artifact_repo is None:
        from skillmeat.cache.repositories import (
            DbCollectionArtifactRepository as _CaRepo,
        )

        artifact_repo = _CaRepo()

    try:
        all_cas = artifact_repo.list_all_with_tags()
    except Exception as e:
        logger.warning(
            f"_sync_all_tags_to_orm: list_all_with_tags() failed ({e}); "
            "skipping tag sync"
        )
        return 0

    synced = 0
    for ca in all_cas:
        try:
            artifact_uuid = getattr(ca, "artifact_uuid", None)
            if not artifact_uuid:
                continue

            # DTOs expose a pre-parsed ``tags`` list.
            tags: list
            if hasattr(ca, "tags") and isinstance(getattr(ca, "tags"), list):
                tags = ca.tags
            else:
                tags_json_val = getattr(ca, "tags_json", None)
                if not tags_json_val:
                    continue
                tags = json.loads(tags_json_val)

            if tags:
                tag_service.sync_artifact_tags(artifact_uuid, tags)
                synced += 1
        except Exception as e:
            artifact_uuid_str = getattr(ca, "artifact_uuid", "<unknown>")
            logger.warning(f"Tag ORM sync failed for {artifact_uuid_str}: {e}")

    logger.info(f"Synced tags for {synced} artifacts to Tag ORM")
    return synced


def _recover_default_collection_metadata(
    session,
    collection_mgr,
) -> dict:
    """Trigger FS → DB recovery for the default (active) collection.

    Resolves the filesystem path for the active collection and calls
    ``recover_collection_metadata()`` from ``artifact_cache_service``.

    Non-fatal: any errors are logged and an empty stats dict returned.

    Args:
        session: Active SQLAlchemy session (may be None; a fresh session is
            obtained internally in that case via
            ``skillmeat.cache.models.get_session``).
        collection_mgr: CollectionManager used to resolve the collection path.

    Returns:
        Recovery statistics dict (see ``recover_collection_metadata`` docstring).
    """
    try:
        from skillmeat.api.services.artifact_cache_service import (
            recover_collection_metadata,
        )

        # Lazily obtain a session when the caller does not supply one
        if session is None:
            from skillmeat.cache.models import get_session as _get_session

            session = _get_session()

        active_name = collection_mgr.get_active_collection_name()
        collection_path = collection_mgr.config.get_collection_path(active_name)

        stats = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_path,
        )

        if stats.get("tags_recovered", 0) > 0 or stats.get("groups_recovered", 0) > 0:
            logger.info(
                "_recover_default_collection_metadata: recovery complete — "
                "tags=%d groups=%d members=%d skipped=%d",
                stats["tags_recovered"],
                stats["groups_recovered"],
                stats["members_recovered"],
                stats["members_skipped"],
            )
        else:
            logger.debug(
                "_recover_default_collection_metadata: nothing to recover "
                "(reason=%r, tags=%d, groups=%d)",
                stats.get("skipped_reason"),
                stats.get("tags_recovered", 0),
                stats.get("groups_recovered", 0),
            )
        return stats
    except Exception as exc:
        logger.warning("_recover_default_collection_metadata: recovery failed: %s", exc)
        return {}


def populate_collection_artifact_metadata(
    artifact_mgr,
    collection_mgr,
    collection_repo: Optional[IDbUserCollectionRepository] = None,
    artifact_repo_ca: Optional[IDbCollectionArtifactRepository] = None,
    project_repo: Optional[IProjectRepository] = None,
) -> dict:
    """Populate CollectionArtifact metadata cache from file-based artifacts.

    For each file-based artifact, create or update CollectionArtifact rows with
    full metadata from YAML frontmatter and manifest entries. This enables the
    /collection page to render artifact cards without N file reads.

    Args:
        artifact_mgr: ArtifactManager for listing and reading artifacts
        collection_mgr: CollectionManager for collection access
        collection_repo: Optional injected IDbUserCollectionRepository.
            Falls back to constructing DbUserCollectionRepository() if None.
        artifact_repo_ca: Optional injected IDbCollectionArtifactRepository.
            When provided, used for upsert_metadata() calls.
            Falls back to constructing DbCollectionArtifactRepository() if None.
        project_repo: Optional injected IProjectRepository used to list
            project paths for deployment scanning.  Falls back to
            constructing DbProjectRepository() if None.

    Returns:
        dict with stats: created_count, updated_count, skipped_count, errors

    """
    import json
    import time

    logger.info("Starting CollectionArtifact metadata cache population...")
    start_time = time.time()

    created_count = 0
    updated_count = 0
    skipped_count = 0
    errors = []

    # Ensure default collection exists (prefer injected repo)
    if collection_repo is None:
        from skillmeat.cache.repositories import DbUserCollectionRepository as _CollRepo

        collection_repo = _CollRepo()

    ensure_default_collection(collection_repo)

    # Ensure artifact_repo_ca is available for upsert_metadata calls
    if artifact_repo_ca is None:
        from skillmeat.cache.repositories import (
            DbCollectionArtifactRepository as _CaRepo2,
        )

        artifact_repo_ca = _CaRepo2()

    # Iterate all file-based collections
    for coll_name in collection_mgr.list_collections():
        try:
            artifacts = artifact_mgr.list_artifacts(collection_name=coll_name)
            logger.debug(
                f"Processing collection '{coll_name}': {len(artifacts)} artifacts"
            )
        except Exception as e:
            error_msg = f"Failed to load artifacts from collection '{coll_name}': {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            continue

        for artifact in artifacts:
            try:
                # Build artifact_id: "{type}:{name}"
                artifact_id = f"{artifact.type.value}:{artifact.name}"

                # Extract metadata fields from artifact
                metadata = artifact.metadata
                description = metadata.description if metadata else None
                author = metadata.author if metadata else None
                license_val = metadata.license if metadata else None
                version = metadata.version if metadata else None

                # Convert tags list to JSON string
                tags_json = json.dumps(artifact.tags) if artifact.tags else None

                # Convert tools list to JSON string
                tools_json = None
                if metadata and metadata.tools:
                    tools_json = json.dumps(metadata.tools)

                # Source and origin fields
                source = artifact.upstream
                origin = artifact.origin
                origin_source = artifact.origin_source
                resolved_sha = getattr(artifact, "resolved_sha", None)
                resolved_version = getattr(artifact, "resolved_version", None)

                # Resolve artifact_id → artifact_uuid via the repository.
                # CollectionArtifact PK is (collection_id, artifact_uuid) since
                # the CAI-P5-01 migration; filter_by(artifact_id=) is no longer valid.
                artifact_uuid_val = artifact_repo_ca.resolve_uuid_by_id(artifact_id)
                if not artifact_uuid_val:
                    # Artifact not yet in the DB cache — skip for now
                    logger.debug(
                        f"Skipping metadata populate for '{artifact_id}': "
                        "not yet in artifacts cache"
                    )
                    continue

                # Determine if this is a create or update for stats tracking.
                existing = artifact_repo_ca.get_by_pk(
                    DEFAULT_COLLECTION_ID, artifact_uuid_val
                )

                # Upsert via repository (handles both create and update internally).
                artifact_repo_ca.upsert_metadata(
                    DEFAULT_COLLECTION_ID,
                    artifact_uuid_val,
                    description=description,
                    author=author,
                    license=license_val,
                    tags=json.loads(tags_json) if tags_json else [],
                    tools=json.loads(tools_json) if tools_json else [],
                    source=source,
                    origin=origin,
                    resolved_sha=resolved_sha,
                    resolved_version=resolved_version,
                )

                if existing:
                    updated_count += 1
                else:
                    created_count += 1

            except Exception as e:
                error_msg = (
                    f"Failed to populate metadata for artifact "
                    f"'{artifact.name}' ({artifact.type.value}): {e}"
                )
                logger.warning(error_msg)
                errors.append(error_msg)
                skipped_count += 1
                continue

    # Populate deployments from DeploymentManager (scan ALL known projects)
    try:
        import os
        from pathlib import Path
        from skillmeat.core.deployment import DeploymentManager

        deployment_mgr = DeploymentManager()

        # Build project_paths: prefer injected repo, fall back to direct DB query
        project_paths = []
        if project_repo is not None:
            for proj_dto in project_repo.list():
                proj_path = Path(proj_dto.path)
                if proj_path.exists():
                    project_paths.append((proj_dto.name, proj_path))
                else:
                    logger.debug(
                        f"Skipping project '{proj_dto.name}' — path does not exist: {proj_dto.path}"
                    )
        else:
            # Fallback: query Project table directly (no path_resolver needed)
            from skillmeat.cache.models import get_session as _get_db_session

            _db_sess = _get_db_session()
            try:
                _proj_rows: list[Project] = _db_sess.query(Project).all()
            finally:
                _db_sess.close()
            for _row in _proj_rows:
                _proj_path = Path(_row.path)
                if _proj_path.exists():
                    project_paths.append((_row.name, _proj_path))
                else:
                    logger.debug(
                        f"Skipping project '{_row.name}' — path does not exist: {_row.path}"
                    )

        # Fallback: if no projects in DB, at least scan cwd
        if not project_paths:
            cwd = Path.cwd()
            project_paths.append((os.path.basename(str(cwd)), cwd))

        logger.debug(
            f"Scanning deployments across {len(project_paths)} project(s): "
            f"{[name for name, _ in project_paths]}"
        )

        # Aggregate deployments across all projects
        deployments_by_artifact = {}
        for project_name, project_path in project_paths:
            try:
                project_deployments = deployment_mgr.list_deployments(
                    project_path=project_path
                )
            except Exception as e:
                logger.debug(
                    f"Failed to scan deployments for project '{project_name}': {e}"
                )
                continue

            for deployment in project_deployments:
                artifact_name = deployment.artifact_name
                if artifact_name not in deployments_by_artifact:
                    deployments_by_artifact[artifact_name] = []

                deployments_by_artifact[artifact_name].append(
                    {
                        "project_path": str(project_path),
                        "project_name": project_name,
                        "deployed_at": (
                            deployment.deployed_at.isoformat()
                            if hasattr(deployment.deployed_at, "isoformat")
                            else str(deployment.deployed_at)
                        ),
                    }
                )

        # Update cache entries with deployment data via repository DI.
        deployment_update_count = 0
        for artifact_name, deployments_list in deployments_by_artifact.items():
            updated = artifact_repo_ca.update_deployments_by_name(
                DEFAULT_COLLECTION_ID,
                artifact_name,
                json.dumps(deployments_list),
            )
            deployment_update_count += updated

        if deployment_update_count > 0:
            logger.info(
                f"Updated deployment data for {deployment_update_count} artifact(s) "
                f"across {len(project_paths)} project(s)"
            )

    except Exception as e:
        logger.warning(f"Failed to populate deployment data: {e}")
        # Non-fatal: cache still works without deployment data

    # All writes were committed by the repository methods; no explicit flush needed.
    duration = time.time() - start_time
    logger.info(
        f"CollectionArtifact metadata cache: created={created_count}, "
        f"updated={updated_count}, skipped={skipped_count}, errors={len(errors)}"
    )
    logger.info(f"Metadata cache population completed in {duration:.2f}s")

    return {
        "created_count": created_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "errors": errors,
    }


# =============================================================================
# Migration Endpoint
# =============================================================================


@router.post(
    "/migrate-to-default",
    summary="Migrate all artifacts to default collection",
    description=(
        "Ensures all existing artifacts from file-system collections are registered "
        "in the default database collection. This enables Groups and other collection "
        "features for all artifacts. Safe to run multiple times - only adds missing entries."
    ),
    responses={
        200: {"description": "Migration completed successfully"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def migrate_to_default_collection(
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    collection_repo: DbUserCollectionRepoDep,
    artifact_repo_ca: DbCollectionArtifactRepoDep,
    project_repo: ProjectRepoDep,
    token: TokenDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> dict:
    """Migrate all artifacts to the default collection.

    This endpoint ensures all artifacts from file-system collections are
    registered in the default database collection, enabling them to use
    Groups and other collection features.

    Args:
        artifact_mgr: Artifact manager for listing artifacts
        collection_mgr: Collection manager for listing collections
        collection_repo: DB user collection repository (injected)
        artifact_repo_ca: DB collection artifact repository (injected)
        project_repo: Project repository for deployment scanning (injected)
        token: Authentication token

    Returns:
        Migration statistics with counts

    Note:
        This operation is idempotent - running it multiple times will not
        create duplicate entries.
    """
    try:
        result = migrate_artifacts_to_default_collection(
            artifact_mgr=artifact_mgr,
            collection_mgr=collection_mgr,
            collection_repo=collection_repo,
            artifact_repo_ca=artifact_repo_ca,
            project_repo=project_repo,
        )

        logger.info(
            f"Migration completed: {result['migrated_count']} migrated, "
            f"{result['already_present_count']} already present"
        )

        return {
            "success": True,
            "message": f"Migrated {result['migrated_count']} artifacts to default collection",
            **result,
        }
    except Exception as e:
        logger.exception(f"Migration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}",
        )


# =============================================================================
# Batch Cache Refresh Endpoint (MUST be before /{collection_id} routes)
# =============================================================================


def _refresh_single_collection_cache(
    collection_id: str,
    artifact_mgr,
    artifact_repo_ca: IDbCollectionArtifactRepository,
) -> dict:
    """Refresh CollectionArtifact metadata cache for a single DB collection.

    This helper extracts the core refresh logic to be reused by both scoped
    and batch refresh endpoints.

    Args:
        collection_id: ID of the collection to refresh.
        artifact_mgr: ArtifactManager for reading file-based artifacts.
        artifact_repo_ca: DB collection artifact repository for reads and
            bulk metadata updates.

    Returns:
        dict with stats:
            - collection_id: str
            - updated: int (artifacts updated)
            - skipped: int (artifacts skipped/unchanged)
            - errors: list of error strings

    """
    updated = 0
    skipped = 0
    errors = []

    try:
        from skillmeat.core.services import TagService

        tag_service = TagService()
    except Exception as e:
        logger.warning(f"Failed to initialize TagService for tag sync: {e}")
        tag_service = None

    logger.debug(f"Refreshing cache for collection '{collection_id}'")

    # Get all CollectionArtifact DTOs for this collection via repository DI.
    ca_dtos = artifact_repo_ca.list_by_collection(collection_id, limit=100_000)

    if not ca_dtos:
        logger.debug(f"Collection '{collection_id}' has no artifacts to refresh")
        return {
            "collection_id": collection_id,
            "updated": 0,
            "skipped": 0,
            "errors": [],
        }

    # Batch-resolve artifact_uuid → type:name id via repository DI.
    ca_uuids = [ca.artifact_uuid for ca in ca_dtos]
    ca_uuid_to_id = artifact_repo_ca.resolve_uuid_to_id_batch(ca_uuids)

    # Build bulk-update list — collect updates then commit in one call.
    bulk_updates: list[dict] = []

    # Process each CollectionArtifact DTO
    for ca in ca_dtos:
        try:
            ca_artifact_id = ca_uuid_to_id.get(ca.artifact_uuid, "")
            # Parse artifact_id (format: "type:name")
            if ":" in ca_artifact_id:
                type_str, artifact_name = ca_artifact_id.split(":", 1)
            else:
                type_str, artifact_name = "unknown", ca_artifact_id

            # Try to get artifact type enum
            artifact_type_enum = None
            try:
                artifact_type_enum = CoreArtifactType(type_str)
            except ValueError:
                # Unknown type - skip
                logger.debug(f"Unknown artifact type '{type_str}' for {ca_artifact_id}")
                skipped += 1
                continue

            # Look up artifact in file system
            file_artifact = None
            try:
                file_artifact = artifact_mgr.show(
                    artifact_name=artifact_name,
                    artifact_type=artifact_type_enum,
                    collection_name=collection_id,
                )
            except Exception as e:
                logger.debug(f"File-based lookup failed for {ca_artifact_id}: {e}")
                skipped += 1
                continue

            if not file_artifact:
                skipped += 1
                continue

            # Extract metadata fields from file-based artifact
            metadata = file_artifact.metadata
            description = metadata.description if metadata else None
            author = metadata.author if metadata else None
            license_val = metadata.license if metadata else None
            version = metadata.version if metadata else None

            # Convert tags list to JSON string
            tags_json = json.dumps(file_artifact.tags) if file_artifact.tags else None

            # Convert tools list to JSON string
            tools_json = None
            if metadata and metadata.tools:
                tools_json = json.dumps(metadata.tools)

            # Source and origin fields
            source = file_artifact.upstream
            origin = file_artifact.origin
            origin_source = file_artifact.origin_source
            resolved_sha = getattr(file_artifact, "resolved_sha", None)
            resolved_version = getattr(file_artifact, "resolved_version", None)

            # Stage update for bulk commit via repository DI
            bulk_updates.append(
                {
                    "artifact_uuid": ca.artifact_uuid,
                    "description": description,
                    "author": author,
                    "license": license_val,
                    "tags_json": tags_json,
                    "tools_json": tools_json,
                    "version": version,
                    "source": source,
                    "origin": origin,
                    "origin_source": origin_source,
                    "resolved_sha": resolved_sha,
                    "resolved_version": resolved_version,
                    "synced_at": datetime.utcnow(),
                }
            )
            updated += 1

            # Sync tags to ORM
            if tag_service and file_artifact.tags:
                try:
                    tag_service.sync_artifact_tags(ca.artifact_uuid, file_artifact.tags)
                except Exception as e:
                    logger.warning(f"Tag ORM sync failed for {ca.artifact_uuid}: {e}")

        except Exception as e:
            error_msg = f"Failed to refresh {ca_uuid_to_id.get(ca.artifact_uuid, ca.artifact_uuid)}: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            skipped += 1

    # Commit all metadata updates in a single repository call
    if bulk_updates:
        artifact_repo_ca.bulk_update_metadata(bulk_updates)

    return {
        "collection_id": collection_id,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


@router.post(
    "/refresh-cache",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Refresh metadata cache for all collections",
    description=(
        "Refresh CollectionArtifact metadata cache across all DB collections. "
        "Iterates all collections in the database and refreshes cached metadata "
        "from file-based artifacts. This is a bulk operation and may take time "
        "for large collections."
    ),
    responses={
        200: {"description": "Cache refresh completed"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["user-collections"],
)
async def refresh_all_collections_cache(
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    collection_repo: DbUserCollectionRepoDep,
    artifact_repo_ca: DbCollectionArtifactRepoDep,
    token: TokenDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> dict:
    """Refresh CollectionArtifact metadata cache across all DB collections.

    Iterates all collections in the database and refreshes cached metadata
    from file-based artifacts.

    Args:
        artifact_mgr: Artifact manager for listing artifacts
        collection_mgr: Collection manager for listing collections
        collection_repo: DB user collection repository (injected)
        artifact_repo_ca: DB collection artifact repository (injected)
        token: Authentication token

    Returns:
        dict with stats:
            - collections_refreshed: int
            - total_updated: int
            - total_skipped: int
            - errors: list of error dicts with collection_id and error messages

    Raises:
        HTTPException: On failure
    """
    import time

    start_time = time.time()
    logger.info("Starting batch cache refresh for all collections")

    try:
        # List all collections via repository DI.
        all_collection_dtos = collection_repo.list(limit=10_000, offset=0)
        logger.info(f"Found {len(all_collection_dtos)} collections to refresh")

        # Handle empty database gracefully
        if not all_collection_dtos:
            logger.info("No collections found in database, cache refresh skipped")
            return {
                "success": True,
                "collections_refreshed": 0,
                "total_updated": 0,
                "total_skipped": 0,
                "errors": [],
                "duration_seconds": 0.0,
            }

        collections_refreshed = 0
        total_updated = 0
        total_skipped = 0
        errors = []

        # Process each collection using repository DI throughout.
        for dto in all_collection_dtos:
            try:
                result = _refresh_single_collection_cache(
                    collection_id=dto.id,
                    artifact_mgr=artifact_mgr,
                    artifact_repo_ca=artifact_repo_ca,
                )

                collections_refreshed += 1
                total_updated += result["updated"]
                total_skipped += result["skipped"]

                if result["errors"]:
                    errors.append(
                        {
                            "collection_id": dto.id,
                            "errors": result["errors"],
                        }
                    )

                logger.debug(
                    f"Collection '{dto.id}': updated={result['updated']}, "
                    f"skipped={result['skipped']}"
                )

            except Exception as e:
                error_msg = f"Failed to refresh collection '{dto.id}': {e}"
                logger.warning(error_msg)
                errors.append(
                    {
                        "collection_id": dto.id,
                        "errors": [str(e)],
                    }
                )

        duration = time.time() - start_time
        logger.info(
            f"Batch cache refresh completed in {duration:.2f}s: "
            f"collections={collections_refreshed}, updated={total_updated}, "
            f"skipped={total_skipped}, errors={len(errors)}"
        )

        return {
            "success": True,
            "collections_refreshed": collections_refreshed,
            "total_updated": total_updated,
            "total_skipped": total_skipped,
            "errors": errors,
            "duration_seconds": round(duration, 2),
        }

    except Exception as e:
        logger.error(f"Batch cache refresh failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "batch_cache_refresh_failed",
                "message": f"Failed to refresh all collections cache: {str(e)}",
            },
        )


# =============================================================================
# CRUD Endpoints
# =============================================================================


@router.get(
    "",
    response_model=UserCollectionListResponse,
    summary="List all user collections",
    description="Retrieve a paginated list of all user-defined collections",
    responses={
        200: {"description": "Successfully retrieved collections"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_user_collections(
    collection_repo: DbUserCollectionRepoDep,
    token: TokenDep,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
    ),
    after: Optional[str] = Query(
        default=None,
        description="Cursor for pagination (next page)",
    ),
    search: Optional[str] = Query(
        default=None,
        description="Filter by collection name (case-insensitive)",
    ),
    collection_type: Optional[str] = Query(
        default=None,
        description="Filter by collection type (e.g., 'context')",
    ),
    auth_context: AuthContext = Depends(get_auth_context),
) -> UserCollectionListResponse:
    """List all user collections with cursor-based pagination.

    Args:
        collection_repo: DB user collection repository (injected)
        token: Authentication token
        limit: Number of items per page
        after: Cursor for next page
        search: Optional name filter
        collection_type: Optional type filter

    Returns:
        Paginated list of collections

    Raises:
        HTTPException: On error
    """
    try:
        logger.info(
            f"Listing user collections (limit={limit}, after={after}, search={search}, "
            f"type={collection_type})"
        )

        # Fetch all collections via repository (large limit to support cursor pagination).
        # The repo list() does not support name search or order-by-id natively, so we
        # fetch a large batch and filter/sort in Python.  For realistic collection counts
        # (<<10k) this is acceptable; a dedicated search method can replace this later.
        all_dtos = collection_repo.list(
            collection_type=collection_type,
            limit=10000,
            offset=0,
        )

        # Apply case-insensitive name search if provided
        if search:
            search_lower = search.lower()
            all_dtos = [d for d in all_dtos if search_lower in d.name.lower()]

        # Sort by id to provide stable cursor-based pagination
        all_dtos.sort(key=lambda d: d.id)

        # Decode cursor if provided
        start_idx = 0
        if after:
            cursor_value = decode_cursor(after)
            try:
                dto_ids = [d.id for d in all_dtos]
                start_idx = dto_ids.index(cursor_value) + 1
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor: collection not found",
                )

        # Paginate
        end_idx = start_idx + limit
        page_dtos = all_dtos[start_idx:end_idx]

        # Convert to response format
        items: List[UserCollectionResponse] = [
            collection_to_response(dto, collection_repo) for dto in page_dtos
        ]

        # Build pagination info
        has_next = end_idx < len(all_dtos)
        has_previous = start_idx > 0

        start_cursor = encode_cursor(page_dtos[0].id) if page_dtos else None
        end_cursor = encode_cursor(page_dtos[-1].id) if page_dtos else None

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=has_previous,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            total_count=len(all_dtos),
        )

        logger.info(f"Retrieved {len(items)} user collections")
        return UserCollectionListResponse(items=items, page_info=page_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing user collections: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list user collections: {str(e)}",
        )


@router.post(
    "",
    response_model=UserCollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user collection",
    description="Create a new user-defined collection",
    responses={
        201: {"description": "Successfully created collection"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        409: {"model": ErrorResponse, "description": "Collection name already exists"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_user_collection(
    request: UserCollectionCreateRequest,
    collection_repo: DbUserCollectionRepoDep,
    token: TokenDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> UserCollectionResponse:
    """Create a new user collection.

    Args:
        request: Collection creation request
        collection_repo: DB user collection repository (injected)
        token: Authentication token

    Returns:
        Created collection details

    Raises:
        HTTPException: If validation fails or name already exists
    """
    try:
        logger.info(f"Creating user collection: {request.name}")

        # Delegate to repository — raises ValueError on duplicate name
        try:
            collection_dto = collection_repo.create(
                name=request.name,
                description=request.description,
                collection_type=request.collection_type,
                context_category=request.context_category,
                created_by=None,  # TODO: Set from authentication context
            )
        except ValueError as exc:
            logger.warning(f"Collection name already exists: {request.name}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Collection with name '{request.name}' already exists",
            ) from exc

        logger.info(f"Created user collection: {collection_dto.id} ({request.name})")
        return collection_to_response(collection_dto, collection_repo)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user collection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user collection: {str(e)}",
        )


@router.get(
    "/{collection_id}",
    response_model=UserCollectionWithGroupsResponse,
    summary="Get user collection details",
    description="Retrieve detailed information about a specific collection including groups",
    responses={
        200: {"description": "Successfully retrieved collection"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_user_collection(
    collection_id: str,
    collection_repo: DbUserCollectionRepoDep,
    group_repo: GroupRepoDep,
    token: TokenDep,
    auth_context: AuthContext = Depends(get_auth_context),
) -> UserCollectionWithGroupsResponse:
    """Get details for a specific user collection.

    Args:
        collection_id: Collection identifier
        collection_repo: DB user collection repository (injected)
        group_repo: Group repository (injected)
        token: Authentication token

    Returns:
        Collection details with nested groups

    Raises:
        HTTPException: If collection not found or on error
    """
    try:
        logger.info(f"Getting user collection: {collection_id}")

        collection_dto = collection_repo.get_by_id(collection_id)
        if not collection_dto:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        return collection_to_response_with_groups(
            collection_dto, collection_repo, group_repo
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting user collection '{collection_id}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user collection: {str(e)}",
        )


@router.put(
    "/{collection_id}",
    response_model=UserCollectionResponse,
    summary="Update user collection",
    description="Update collection metadata (partial update supported)",
    responses={
        200: {"description": "Successfully updated collection"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        409: {"model": ErrorResponse, "description": "Collection name already exists"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_user_collection(
    collection_id: str,
    request: UserCollectionUpdateRequest,
    collection_repo: DbUserCollectionRepoDep,
    token: TokenDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> UserCollectionResponse:
    """Update a user collection.

    Args:
        collection_id: Collection identifier
        request: Update request with fields to modify
        collection_repo: DB user collection repository (injected)
        token: Authentication token

    Returns:
        Updated collection details

    Raises:
        HTTPException: If collection not found, validation fails, or name conflict
    """
    try:
        logger.info(f"Updating user collection: {collection_id}")

        # Check if any update parameters provided
        if (
            request.name is None
            and request.description is None
            and request.collection_type is None
            and request.context_category is None
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one update parameter must be provided",
            )

        # Verify the collection exists before attempting update
        existing_dto = collection_repo.get_by_id(collection_id)
        if not existing_dto:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Check name uniqueness if changing name — the repo.update() will raise
        # KeyError on missing and RuntimeError on DB errors; name conflicts may
        # surface as RuntimeError wrapping an IntegrityError.  We do a pre-check
        # here to return a 409 with a clear message before delegating to the repo.
        if request.name is not None and request.name != existing_dto.name:
            all_dtos = collection_repo.list(limit=10000)
            name_taken = any(
                d.id != collection_id and d.name == request.name for d in all_dtos
            )
            if name_taken:
                logger.warning(f"Collection name already exists: {request.name}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Collection with name '{request.name}' already exists",
                )

        # Build kwargs for partial update
        update_kwargs: dict = {}
        if request.name is not None:
            update_kwargs["name"] = request.name
        if request.description is not None:
            update_kwargs["description"] = request.description
        if request.collection_type is not None:
            update_kwargs["collection_type"] = request.collection_type
        if request.context_category is not None:
            update_kwargs["context_category"] = request.context_category

        try:
            updated_dto = collection_repo.update(collection_id, **update_kwargs)
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            ) from exc

        logger.info(f"Updated user collection: {collection_id}")
        return collection_to_response(updated_dto, collection_repo)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error updating user collection '{collection_id}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user collection: {str(e)}",
        )


@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user collection",
    description="Delete a collection and all its groups and artifact associations",
    responses={
        204: {"description": "Successfully deleted collection"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_user_collection(
    collection_id: str,
    collection_repo: DbUserCollectionRepoDep,
    token: TokenDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> None:
    """Delete a user collection.

    Args:
        collection_id: Collection identifier
        collection_repo: DB user collection repository (injected)
        token: Authentication token

    Raises:
        HTTPException: If collection not found or on error

    Note:
        Cascade deletion is handled by the database (groups and associations)
    """
    try:
        logger.info(f"Deleting user collection: {collection_id}")

        deleted = collection_repo.delete(collection_id)
        if not deleted:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Invalidate cache for deleted collection
        cache = get_collection_count_cache()
        cache.invalidate(collection_id)

        logger.info(f"Deleted user collection: {collection_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error deleting user collection '{collection_id}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user collection: {str(e)}",
        )


@router.get(
    "/{collection_id}/artifacts",
    response_model=CollectionArtifactsResponse,
    summary="List artifacts in collection",
    description="Retrieve paginated list of artifacts in a collection with optional type and group filtering",
    responses={
        200: {"description": "Successfully retrieved artifacts"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_collection_artifacts(
    collection_id: str,
    artifact_mgr: ArtifactManagerDep,
    collection_repo: DbUserCollectionRepoDep,
    artifact_repo_ca: DbCollectionArtifactRepoDep,
    token: TokenDep,
    limit: int = Query(default=20, ge=1, le=100),
    after: Optional[str] = Query(default=None),
    artifact_type: Optional[str] = Query(
        default=None, description="Filter by artifact type"
    ),
    group_id: Optional[str] = Query(
        default=None,
        description="Filter by group membership - only return artifacts belonging to this group",
    ),
    include_groups: bool = Query(
        default=False,
        description="Include group memberships for each artifact in the response",
    ),
    auth_context: AuthContext = Depends(get_auth_context),
) -> CollectionArtifactsResponse:
    """List artifacts in a collection with pagination.

    Args:
        collection_id: Collection identifier
        artifact_mgr: Artifact manager for filesystem metadata fallback
        collection_repo: DB user collection repository (injected)
        artifact_repo_ca: DB collection artifact repository (injected)
        token: Authentication token
        limit: Number of items per page
        after: Cursor for next page
        artifact_type: Optional artifact type filter
        group_id: Optional group filter - when provided, only returns artifacts
            that belong to the specified group
        include_groups: When true, include group membership info for each artifact

    Returns:
        Paginated list of artifacts

    Raises:
        HTTPException: If collection not found or on error
    """
    try:
        logger.info(
            f"Listing artifacts for collection '{collection_id}' "
            f"(limit={limit}, after={after}, type={artifact_type}, "
            f"group_id={group_id}, include_groups={include_groups})"
        )

        # Verify collection exists via repository DI
        collection_dto = collection_repo.get_by_id(collection_id)
        if not collection_dto:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Fetch all memberships ordered by artifact type:name ID via repository DI.
        all_associations = artifact_repo_ca.list_all_ordered(collection_id)

        # Filter by group membership if group_id is provided
        if group_id:
            group_artifact_uuids = artifact_repo_ca.get_group_artifact_uuids(group_id)
            all_associations = [
                assoc
                for assoc in all_associations
                if assoc.artifact_uuid in group_artifact_uuids
            ]

        # Batch-resolve artifact_uuid → type:name id for all associations.
        all_uuids = [a.artifact_uuid for a in all_associations]
        all_uuid_to_id = artifact_repo_ca.resolve_uuid_to_id_batch(all_uuids)

        # Filter by artifact type BEFORE cursor pagination.
        # This keeps page boundaries and total_count consistent with the selected tab.
        if artifact_type:
            type_prefix = f"{artifact_type}:"
            all_associations = [
                assoc
                for assoc in all_associations
                if all_uuid_to_id.get(assoc.artifact_uuid, "").startswith(type_prefix)
            ]

        # Decode cursor if provided
        start_idx = 0
        if after:
            cursor_value = decode_cursor(after)
            try:
                artifact_ids = [
                    all_uuid_to_id.get(assoc.artifact_uuid, "")
                    for assoc in all_associations
                ]
                start_idx = artifact_ids.index(cursor_value) + 1
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor: artifact not found",
                )

        # Paginate
        end_idx = start_idx + limit
        page_associations = all_associations[start_idx:end_idx]

        # Batch fetch sources from DB via repository DI (avoids N+1 queries).
        source_lookup: dict[str, str] = {}
        if page_associations:
            page_artifact_uuids = [assoc.artifact_uuid for assoc in page_associations]
            source_lookup = artifact_repo_ca.get_source_for_uuids(page_artifact_uuids)

        # Batch fetch group memberships if requested via repository DI.
        artifact_groups_map: dict[str, list[ArtifactGroupMembership]] = {}
        if include_groups and page_associations:
            page_artifact_uuids = [assoc.artifact_uuid for assoc in page_associations]
            membership_rows = artifact_repo_ca.get_group_memberships_batch(
                page_artifact_uuids, collection_id
            )
            for row in membership_rows:
                artifact_id = row["artifact_id"]
                if artifact_id not in artifact_groups_map:
                    artifact_groups_map[artifact_id] = []
                artifact_groups_map[artifact_id].append(
                    ArtifactGroupMembership(
                        id=row["group_id"],
                        name=row["group_name"],
                        position=row["position"],
                    )
                )

        # Build UUID → artifact_id lookup for the page items.
        # all_uuid_to_id already contains all association UUIDs; re-use it.
        uuid_to_artifact_id = {
            uuid: all_uuid_to_id[uuid]
            for uuid in (a.artifact_uuid for a in page_associations)
            if uuid in all_uuid_to_id
        }

        # Acquire a session for legacy helpers that still require one
        # (_get_artifact_collections, get_artifact_metadata).  These have not
        # yet been migrated to repository DI; a single shared session per
        # request is safe here because the helpers are read-only.
        from skillmeat.cache.models import get_session as _get_session_for_lookup

        _lookup_session = _get_session_for_lookup()

        # Fetch artifact metadata for each association
        # Priority: 1. DB cache (if synced_at is set), 2. File system, 3. Marketplace
        items: List[ArtifactSummary] = []
        for assoc in page_associations:
            # Resolve artifact_id (format: "type:name") from pre-built lookup
            resolved_artifact_id = uuid_to_artifact_id.get(assoc.artifact_uuid, "")
            # Parse artifact_id (format: "type:name")
            if ":" in resolved_artifact_id:
                type_str, artifact_name = resolved_artifact_id.split(":", 1)
            else:
                type_str, artifact_name = "unknown", resolved_artifact_id

            artifact_summary = None

            # 1. Primary: Try to build from DB cache (check synced_at)
            if assoc.synced_at is not None:
                # Cache hit - use cached fields from CollectionArtifact DTO.
                # assoc.tags is already a List[str] (parsed from tags_json by DTO).
                tags = assoc.tags or None

                # Resolve source: DB lookup > filesystem > artifact_id fallback
                db_source = source_lookup.get(resolved_artifact_id)
                resolved_source = db_source or assoc.source
                if not resolved_source:
                    # Last resort: read from filesystem
                    try:
                        artifact_type_enum = None
                        try:
                            artifact_type_enum = CoreArtifactType(type_str)
                        except ValueError:
                            pass

                        file_artifact = artifact_mgr.show(
                            artifact_name=artifact_name,
                            artifact_type=artifact_type_enum,
                        )
                        if file_artifact and file_artifact.upstream:
                            resolved_source = file_artifact.upstream
                    except Exception as e:
                        logger.debug(
                            f"Failed to read filesystem source for {resolved_artifact_id}: {e}"
                        )

                # Use artifact_id as absolute last resort
                if not resolved_source:
                    resolved_source = resolved_artifact_id

                artifact_summary = ArtifactSummary(
                    id=resolved_artifact_id,
                    name=artifact_name,
                    type=type_str,
                    version=assoc.version,
                    source=resolved_source,
                    description=assoc.description,
                    author=assoc.author,
                    tags=tags,
                    tools=assoc.tools or None,
                    origin=assoc.origin,
                    origin_source=assoc.origin_source,
                    collections=_get_artifact_collections(
                        _lookup_session, resolved_artifact_id
                    ),
                    deployments=parse_deployments(
                        json.dumps(assoc.deployments) if assoc.deployments else None
                    ),
                )
                logger.debug(f"Cache hit for {resolved_artifact_id}")

            # 2. Fallback: Try file-based ArtifactManager on cache miss
            if artifact_summary is None:
                try:
                    # Convert type string to ArtifactType enum
                    artifact_type_enum = None
                    try:
                        artifact_type_enum = CoreArtifactType(type_str)
                    except ValueError:
                        pass

                    file_artifact = artifact_mgr.show(
                        artifact_name=artifact_name,
                        artifact_type=artifact_type_enum,
                    )

                    if file_artifact:
                        # Build ArtifactSummary from file-based artifact
                        artifact_summary = ArtifactSummary(
                            id=resolved_artifact_id,
                            name=file_artifact.name,
                            type=(
                                file_artifact.type.value
                                if hasattr(file_artifact.type, "value")
                                else str(file_artifact.type)
                            ),
                            version=(
                                file_artifact.metadata.version
                                if file_artifact.metadata
                                else None
                            ),
                            source=file_artifact.upstream or resolved_artifact_id,
                            description=(
                                file_artifact.metadata.description
                                if file_artifact.metadata
                                else None
                            ),
                            author=(
                                file_artifact.metadata.author
                                if file_artifact.metadata
                                else None
                            ),
                            tags=file_artifact.tags or None,
                            tools=(
                                [
                                    tool.value if hasattr(tool, "value") else str(tool)
                                    for tool in file_artifact.metadata.tools
                                ]
                                if file_artifact.metadata
                                and file_artifact.metadata.tools
                                else None
                            ),
                            origin=getattr(file_artifact, "origin", None),
                            origin_source=getattr(file_artifact, "origin_source", None),
                            collections=_get_artifact_collections(
                                _lookup_session, resolved_artifact_id
                            ),
                            deployments=parse_deployments(
                                json.dumps(assoc.deployments)
                                if assoc.deployments
                                else None
                            ),
                        )
                        logger.debug(f"File-based lookup for {resolved_artifact_id}")
                except (ValueError, Exception) as e:
                    # Artifact not found in file system, fall through to fallback
                    logger.debug(
                        f"File-based lookup failed for {resolved_artifact_id}: {e}"
                    )

            # 3. Last resort: Fallback to marketplace/database service
            if artifact_summary is None:
                artifact_summary = get_artifact_metadata(
                    _lookup_session, resolved_artifact_id
                )
                logger.debug(f"Marketplace fallback for {resolved_artifact_id}")

            # Add deployments from cache to all artifact summaries.
            # assoc.deployments is already a List[str] parsed from deployments_json by DTO.
            if artifact_summary and not artifact_summary.deployments:
                artifact_summary.deployments = parse_deployments(
                    json.dumps(assoc.deployments) if assoc.deployments else None
                )

            if include_groups:
                # Add groups field to artifact summary while preserving all metadata
                groups = artifact_groups_map.get(resolved_artifact_id, [])
                items.append(
                    ArtifactSummary(
                        id=resolved_artifact_id,
                        name=artifact_summary.name,
                        type=artifact_summary.type,
                        version=artifact_summary.version,
                        source=artifact_summary.source,
                        description=artifact_summary.description,
                        author=artifact_summary.author,
                        tags=artifact_summary.tags,
                        tools=artifact_summary.tools,
                        origin=artifact_summary.origin,
                        origin_source=artifact_summary.origin_source,
                        collections=artifact_summary.collections,
                        groups=groups,
                        deployments=artifact_summary.deployments,
                    )
                )
            else:
                items.append(artifact_summary)

        # Close the lookup session opened for legacy helper functions above.
        try:
            _lookup_session.close()
        except Exception:
            pass

        # Build pagination info
        has_next = end_idx < len(all_associations)
        has_previous = start_idx > 0

        start_cursor = (
            encode_cursor(
                uuid_to_artifact_id.get(page_associations[0].artifact_uuid, "")
            )
            if page_associations
            else None
        )
        end_cursor = (
            encode_cursor(
                uuid_to_artifact_id.get(page_associations[-1].artifact_uuid, "")
            )
            if page_associations
            else None
        )

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=has_previous,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            total_count=len(all_associations),
        )

        logger.info(
            f"Retrieved {len(items)} artifacts for collection '{collection_id}'"
        )
        return CollectionArtifactsResponse(items=items, page_info=page_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error listing artifacts for collection '{collection_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collection artifacts: {str(e)}",
        )


# =============================================================================
# Artifact Management Endpoints
# =============================================================================


@router.post(
    "/{collection_id}/artifacts",
    status_code=status.HTTP_201_CREATED,
    summary="Add artifacts to collection",
    description="Add one or more artifacts to a collection (idempotent)",
    responses={
        201: {"description": "Successfully added artifacts"},
        200: {"description": "Artifacts already in collection (idempotent)"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def add_artifacts_to_collection(
    collection_id: str,
    request: AddArtifactsRequest,
    collection_repo: DbUserCollectionRepoDep,
    artifact_repo_ca: DbCollectionArtifactRepoDep,
    session: DbSessionDep,
    artifact_repo: ArtifactRepoDep,
    token: TokenDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> dict:
    """Add artifacts to a collection.

    Args:
        collection_id: Collection identifier
        request: Request with artifact IDs
        collection_repo: DB user collection repository (injected)
        artifact_repo_ca: DB collection artifact repository (injected)
        session: Database session (used for idempotency check join query pending
            IDbCollectionArtifactRepository.list_artifact_ids_for_collection())
        artifact_repo: Artifact repository for UUID resolution (injected)
        token: Authentication token

    Returns:
        Result with count of added artifacts

    Raises:
        HTTPException: If collection not found or validation fails

    Note:
        This operation is idempotent - re-adding existing artifacts returns 200
    """
    try:
        logger.info(
            f"Adding {len(request.artifact_ids)} artifacts to collection: {collection_id}"
        )

        # Verify collection exists via repository
        collection_dto = collection_repo.get_by_id(collection_id)
        if not collection_dto:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Get existing associations for idempotency check.
        # list_by_collection() with a large limit avoids direct ORM query usage.
        existing_ca_dtos = artifact_repo_ca.list_by_collection(
            collection_id, limit=100_000
        )
        # Resolve UUIDs → type:name ids via batch lookup on the artifact repo.
        existing_uuids = [dto.artifact_uuid for dto in existing_ca_dtos]
        existing_artifact_ids: set[str] = set()
        if existing_uuids:
            uuid_to_id_map = artifact_repo.get_ids_by_uuids(existing_uuids)
            existing_artifact_ids = set(uuid_to_id_map.values())

        # Resolve each artifact_id (format: "type:name") → artifact_uuid via
        # the ArtifactRepository to avoid direct ORM access here.
        uuids_to_add: list[str] = []
        skipped_count = 0
        for artifact_id in request.artifact_ids:
            if artifact_id not in existing_artifact_ids:
                # Resolve UUID via repository (delegates to DB cache internally).
                if ":" in artifact_id:
                    type_str, art_name = artifact_id.split(":", 1)
                    artifact_uuid = artifact_repo.resolve_uuid_by_type_name(
                        type_str, art_name
                    )
                else:
                    artifact_uuid = None
                if not artifact_uuid:
                    logger.warning(
                        f"Skipping add: artifact '{artifact_id}' not found in cache"
                    )
                    skipped_count += 1
                    continue
                uuids_to_add.append(artifact_uuid)

        # Delegate batch add to repository (handles commit internally)
        if uuids_to_add:
            try:
                artifact_repo_ca.add_artifacts(collection_id, uuids_to_add)
            except (KeyError, ValueError) as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )

        added_count = len(uuids_to_add)

        # Invalidate collection count cache
        cache = get_collection_count_cache()
        cache.invalidate(collection_id)

        # Invalidate metadata cache for newly added artifacts
        # This ensures they will be refreshed with current metadata
        if added_count > 0:
            invalidate_collection_artifacts(session, collection_id)

        logger.info(
            f"Added {added_count} new artifacts to collection {collection_id} "
            f"({len(request.artifact_ids) - added_count - skipped_count} already present, "
            f"{skipped_count} skipped/not found)"
        )

        already_present_count = len(request.artifact_ids) - added_count - skipped_count

        # Return 200 if all were already present (idempotent), 201 if any added
        status_code = (
            status.HTTP_200_OK if added_count == 0 else status.HTTP_201_CREATED
        )

        return {
            "collection_id": collection_id,
            "added_count": added_count,
            "already_present_count": already_present_count,
            "total_artifacts": len(existing_artifact_ids) + added_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error adding artifacts to collection '{collection_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add artifacts to collection: {str(e)}",
        )


@router.delete(
    "/{collection_id}/artifacts/{artifact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove artifact from collection",
    description="Remove an artifact from a collection (idempotent)",
    responses={
        204: {"description": "Successfully removed artifact"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def remove_artifact_from_collection(
    collection_id: str,
    artifact_id: str,
    collection_repo: DbUserCollectionRepoDep,
    artifact_repo_ca: DbCollectionArtifactRepoDep,
    artifact_repo: ArtifactRepoDep,
    token: TokenDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> None:
    """Remove an artifact from a collection.

    Args:
        collection_id: Collection identifier
        artifact_id: Artifact identifier (type:name format)
        collection_repo: DB user collection repository (injected)
        artifact_repo_ca: DB collection artifact repository (injected)
        artifact_repo: Artifact repository for UUID resolution (injected)
        token: Authentication token

    Raises:
        HTTPException: If collection not found or on error

    Note:
        This operation is idempotent - removing non-existent artifacts returns 204
    """
    try:
        logger.info(f"Removing artifact {artifact_id} from collection: {collection_id}")

        # Verify collection exists via repository
        collection_dto = collection_repo.get_by_id(collection_id)
        if not collection_dto:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Resolve artifact_id (type:name) → artifact_uuid via repository.
        artifact_uuid: str | None = None
        if ":" in artifact_id:
            type_str, art_name = artifact_id.split(":", 1)
            artifact_uuid = artifact_repo.resolve_uuid_by_type_name(type_str, art_name)
        else:
            artifact_dto = artifact_repo.get(artifact_id)
            if artifact_dto:
                artifact_uuid = artifact_dto.uuid

        if artifact_uuid:
            # Delegate removal to repository (handles commit internally)
            removed = artifact_repo_ca.remove_artifact(collection_id, artifact_uuid)
            if removed:
                # Invalidate cache for this collection
                cache = get_collection_count_cache()
                cache.invalidate(collection_id)
                logger.info(
                    f"Removed artifact {artifact_id} from collection {collection_id}"
                )
            else:
                logger.info(
                    f"Artifact {artifact_id} not in collection {collection_id} (idempotent)"
                )
        else:
            logger.info(
                f"Artifact {artifact_id} not found in cache (idempotent remove)"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error removing artifact from collection '{collection_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove artifact from collection: {str(e)}",
        )


# =============================================================================
# Entity Management Endpoints (Context Entities)
# =============================================================================


@router.post(
    "/{collection_id}/entities/{entity_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Add entity to collection",
    description="Add a context entity to a collection (idempotent)",
    responses={
        201: {"description": "Successfully added entity"},
        200: {"description": "Entity already in collection (idempotent)"},
        404: {
            "model": ErrorResponse,
            "description": "Collection or entity not found",
        },
        409: {
            "model": ErrorResponse,
            "description": "Entity already exists in collection",
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def add_entity_to_collection(
    collection_id: str,
    entity_id: str,
    collection_repo: DbUserCollectionRepoDep,
    artifact_repo_ca: DbCollectionArtifactRepoDep,
    artifact_repo: ArtifactRepoDep,
    token: TokenDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> dict:
    """Add a context entity to a collection.

    Args:
        collection_id: Collection identifier
        entity_id: Entity (artifact) identifier
        collection_repo: DB user collection repository (injected)
        artifact_repo_ca: DB collection artifact repository (injected)
        artifact_repo: Artifact repository for entity UUID resolution (injected)
        token: Authentication token

    Returns:
        Result with status information

    Raises:
        HTTPException: If collection not found or entity doesn't exist

    Note:
        This operation is idempotent - re-adding existing entities returns 200
    """
    try:
        logger.info(f"Adding entity {entity_id} to collection: {collection_id}")

        # Verify collection exists via repository DI
        collection_dto = collection_repo.get_by_id(collection_id)
        if not collection_dto:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Check if entity exists and retrieve its UUID via repository.
        entity_dto = artifact_repo.get(entity_id)
        if not entity_dto:
            logger.warning(f"Entity not found: {entity_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity '{entity_id}' not found",
            )
        entity_uuid = entity_dto.uuid
        if not entity_uuid:
            logger.warning(f"Entity {entity_id} has no UUID in cache — cannot add")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Entity '{entity_id}' is not yet cached (no UUID); run a cache refresh first",
            )

        # Check if association already exists via repository
        existing = artifact_repo_ca.get_by_pk(collection_id, entity_uuid)

        if existing:
            logger.info(
                f"Entity {entity_id} already in collection {collection_id} (idempotent)"
            )
            return {
                "collection_id": collection_id,
                "entity_id": entity_id,
                "status": "already_present",
            }

        # Delegate add to repository (handles commit internally)
        try:
            artifact_repo_ca.add_artifacts(collection_id, [entity_uuid])
        except (KeyError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        logger.info(f"Added entity {entity_id} to collection {collection_id}")
        return {
            "collection_id": collection_id,
            "entity_id": entity_id,
            "status": "added",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error adding entity to collection '{collection_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add entity to collection: {str(e)}",
        )


@router.delete(
    "/{collection_id}/entities/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove entity from collection",
    description="Remove a context entity from a collection (idempotent)",
    responses={
        204: {"description": "Successfully removed entity"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def remove_entity_from_collection(
    collection_id: str,
    entity_id: str,
    collection_repo: DbUserCollectionRepoDep,
    artifact_repo_ca: DbCollectionArtifactRepoDep,
    artifact_repo: ArtifactRepoDep,
    token: TokenDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> None:
    """Remove a context entity from a collection.

    Args:
        collection_id: Collection identifier
        entity_id: Entity (artifact) identifier
        collection_repo: DB user collection repository (injected)
        artifact_repo_ca: DB collection artifact repository (injected)
        artifact_repo: Artifact repository for UUID resolution (injected)
        token: Authentication token

    Raises:
        HTTPException: If collection not found or on error

    Note:
        This operation is idempotent - removing non-existent entities returns 204
    """
    try:
        logger.info(f"Removing entity {entity_id} from collection: {collection_id}")

        # Verify collection exists via repository DI
        collection_dto = collection_repo.get_by_id(collection_id)
        if not collection_dto:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Resolve entity_id (type:name) → artifact_uuid via repository.
        artifact_uuid: str | None = None
        if ":" in entity_id:
            type_str, art_name = entity_id.split(":", 1)
            artifact_uuid = artifact_repo.resolve_uuid_by_type_name(type_str, art_name)
        else:
            entity_dto = artifact_repo.get(entity_id)
            if entity_dto:
                artifact_uuid = entity_dto.uuid

        if artifact_uuid:
            # Delegate removal to repository (handles commit internally)
            removed = artifact_repo_ca.remove_artifact(collection_id, artifact_uuid)
            if removed:
                logger.info(
                    f"Removed entity {entity_id} from collection {collection_id}"
                )
            else:
                logger.info(
                    f"Entity {entity_id} not in collection {collection_id} (idempotent)"
                )
        else:
            logger.info(f"Entity {entity_id} not found in cache (idempotent remove)")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error removing entity from collection '{collection_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove entity from collection: {str(e)}",
        )


@router.get(
    "/{collection_id}/entities",
    response_model=CollectionArtifactsResponse,
    summary="List entities in collection",
    description="Retrieve paginated list of context entities in a collection",
    responses={
        200: {"description": "Successfully retrieved entities"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_collection_entities(
    collection_id: str,
    collection_repo: DbUserCollectionRepoDep,
    artifact_repo_ca: DbCollectionArtifactRepoDep,
    session: DbSessionDep,
    token: TokenDep,
    limit: int = Query(default=20, ge=1, le=100),
    after: Optional[str] = Query(default=None),
    auth_context: AuthContext = Depends(get_auth_context),
) -> CollectionArtifactsResponse:
    """List context entities in a collection with pagination.

    Args:
        collection_id: Collection identifier
        collection_repo: DB user collection repository (injected)
        artifact_repo_ca: DB collection artifact repository (injected)
        session: Database session (passed to get_artifact_metadata service)
        token: Authentication token
        limit: Number of items per page
        after: Cursor for next page

    Returns:
        Paginated list of entities (artifacts)

    Raises:
        HTTPException: If collection not found or on error
    """
    try:
        logger.info(
            f"Listing entities for collection '{collection_id}' "
            f"(limit={limit}, after={after})"
        )

        # Verify collection exists via repository DI
        collection_dto = collection_repo.get_by_id(collection_id)
        if not collection_dto:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Fetch all memberships ordered by artifact type:name ID via repository DI.
        all_associations = artifact_repo_ca.list_all_ordered(collection_id)

        # Batch-resolve artifact_uuid → type:name ids via repository DI.
        ent_all_uuids = [a.artifact_uuid for a in all_associations]
        ent_uuid_to_id = artifact_repo_ca.resolve_uuid_to_id_batch(ent_all_uuids)

        # Decode cursor if provided
        start_idx = 0
        if after:
            cursor_value = decode_cursor(after)
            try:
                artifact_ids = [
                    ent_uuid_to_id.get(assoc.artifact_uuid, "")
                    for assoc in all_associations
                ]
                start_idx = artifact_ids.index(cursor_value) + 1
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor: entity not found",
                )

        # Paginate
        end_idx = start_idx + limit
        page_associations = all_associations[start_idx:end_idx]

        # Fetch artifact metadata for each association using fallback service
        # This ensures consistent metadata including description, tags, and collections
        items: List[ArtifactSummary] = []
        for assoc in page_associations:
            ent_artifact_id = ent_uuid_to_id.get(assoc.artifact_uuid, "")
            artifact_summary = get_artifact_metadata(session, ent_artifact_id)
            items.append(artifact_summary)

        # Build pagination info
        has_next = end_idx < len(all_associations)
        has_previous = start_idx > 0

        start_cursor = (
            encode_cursor(ent_uuid_to_id.get(page_associations[0].artifact_uuid, ""))
            if page_associations
            else None
        )
        end_cursor = (
            encode_cursor(ent_uuid_to_id.get(page_associations[-1].artifact_uuid, ""))
            if page_associations
            else None
        )

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=has_previous,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            total_count=len(all_associations),
        )

        logger.info(f"Retrieved {len(items)} entities for collection '{collection_id}'")
        return CollectionArtifactsResponse(items=items, page_info=page_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error listing entities for collection '{collection_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collection entities: {str(e)}",
        )


# =============================================================================
# Cache Refresh Endpoints
# =============================================================================


@router.post(
    "/{collection_id}/refresh-cache",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["user-collections"],
    summary="Refresh collection metadata cache (DB-backed)",
    description=(
        "Refresh CollectionArtifact metadata cache for a specific DB collection. "
        "This is separate from /{collection_id}/refresh, which refreshes file-based "
        "collections. This endpoint targets only the DB cache, reading current "
        "file-based artifact metadata and updating CollectionArtifact cache rows."
    ),
    responses={
        200: {"description": "Cache refresh completed successfully"},
        404: {
            "model": ErrorResponse,
            "description": "Collection not found in database",
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def refresh_collection_cache(
    collection_id: str,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    collection_repo: DbUserCollectionRepoDep,
    artifact_repo_ca: DbCollectionArtifactRepoDep,
    token: TokenDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> dict:
    """Refresh CollectionArtifact metadata cache for a specific DB collection.

    IMPORTANT: This is separate from /{collection_id}/refresh, which refreshes
    file-based collections. This endpoint targets only the DB cache.

    Reads current file-based artifact metadata and updates CollectionArtifact
    cache rows for all artifacts in the specified collection.

    Args:
        collection_id: UUID or name of the collection
        artifact_mgr: Artifact manager for reading file-based metadata
        collection_mgr: Collection manager for file-based collection access
        collection_repo: DB user collection repository (injected)
        artifact_repo_ca: DB collection artifact repository (injected)
        token: Authentication token

    Returns:
        dict with refresh stats: updated_count, skipped_count, errors

    Raises:
        HTTPException: If collection not found in database
    """
    import time

    logger.info(f"Starting DB cache refresh for collection '{collection_id}'")
    start_time = time.time()

    # 1. Validate collection exists via repository DI.
    collection_dto = collection_repo.get_by_id(collection_id)
    if not collection_dto:
        logger.error(f"Collection not found in database: {collection_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "collection_not_found",
                "collection_id": collection_id,
                "message": f"Collection '{collection_id}' not found in database",
            },
        )

    # 2. Delegate to the refactored helper which uses repository DI throughout.
    result = _refresh_single_collection_cache(
        collection_id=collection_id,
        artifact_mgr=artifact_mgr,
        artifact_repo_ca=artifact_repo_ca,
    )

    duration = time.time() - start_time
    logger.info(
        f"DB cache refresh for collection '{collection_id}' completed: "
        f"updated={result['updated']}, skipped={result['skipped']}, "
        f"errors={len(result['errors'])}, duration={duration:.2f}s"
    )

    # 3. Return stats
    return {
        "collection_id": collection_id,
        "updated_count": result["updated"],
        "skipped_count": result["skipped"],
        "errors": result["errors"],
    }


# =============================================================================
# File-Based Refresh Endpoint
# =============================================================================


@router.post(
    "/{collection_id}/refresh",
    status_code=status.HTTP_200_OK,
    summary="Refresh collection artifact metadata",
    description="Refresh metadata for artifacts in a collection from their upstream GitHub sources. Use mode=check to detect updates without applying changes.",
    responses={
        200: {
            "description": "Refresh completed successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "metadata_refresh": {
                            "summary": "Metadata refresh (default)",
                            "value": {
                                "collection_id": "default",
                                "status": "completed",
                                "mode": "metadata_only",
                                "summary": {
                                    "refreshed_count": 5,
                                    "unchanged_count": 10,
                                },
                            },
                        },
                        "check_updates": {
                            "summary": "Check for updates (mode=check)",
                            "value": {
                                "collection_id": "default",
                                "updates_available": 3,
                                "up_to_date": 12,
                                "results": [],
                            },
                        },
                    }
                }
            },
        },
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {
            "model": ErrorResponse,
            "description": "Internal server error during refresh",
        },
    },
)
async def refresh_collection(
    collection_id: str,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    request: RefreshRequest = Body(...),
    mode: Optional[RefreshModeEnum] = Query(
        None, description="Override request body mode"
    ),
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
):
    """Refresh artifact metadata for a collection from upstream GitHub sources.

    Supports three modes:
    - metadata_only: Update metadata fields without version changes (default)
    - check_only: Detect available updates without applying changes
    - sync: Full synchronization including version updates (reserved)

    Args:
        collection_id: Collection identifier
        request: Refresh request with mode, filters, and dry_run options
        mode: Optional query param to override request body mode
        collection_mgr: Collection manager dependency
        token: Authentication token

    Returns:
        RefreshResponse (for metadata_only/sync) or UpdateCheckResponse (for check_only)

    Raises:
        HTTPException: If collection not found or on error
    """
    try:
        logger.info(f"Starting refresh for collection {collection_id}")

        # Validate field names if provided
        if request.fields is not None:
            try:
                validated_fields, invalid_fields = validate_fields(
                    request.fields, strict=False
                )
                if invalid_fields:
                    # Return 422 with details about invalid fields
                    from skillmeat.core.refresher import REFRESHABLE_FIELDS

                    valid_list = ", ".join(sorted(REFRESHABLE_FIELDS))
                    logger.warning(
                        f"Invalid field names in refresh request: {invalid_fields}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Invalid field name(s): {', '.join(invalid_fields)}. "
                            f"Valid fields: {valid_list}"
                        ),
                    )
                # Use validated (case-normalized) fields
                request.fields = validated_fields
            except ValueError as e:
                # This shouldn't happen with strict=False, but handle it anyway
                logger.error(f"Unexpected validation error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(e),
                )

        # Check if collection exists in collection manager
        if collection_id not in collection_mgr.list_collections():
            logger.warning(f"Collection not found for refresh: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Determine refresh mode - query param overrides request body
        effective_mode = mode if mode is not None else request.mode

        # Map RefreshModeEnum to core RefreshMode
        mode_mapping = {
            RefreshModeEnum.METADATA_ONLY: RefreshMode.METADATA_ONLY,
            RefreshModeEnum.CHECK_ONLY: RefreshMode.CHECK_ONLY,
            RefreshModeEnum.SYNC: RefreshMode.SYNC,
        }
        core_mode = mode_mapping[effective_mode]

        # Create CollectionRefresher
        refresher = CollectionRefresher(collection_mgr)

        # Branch based on mode
        if effective_mode == RefreshModeEnum.CHECK_ONLY:
            # Check mode - detect updates without applying changes
            logger.info(f"Running update check for collection {collection_id}")
            update_results = refresher.check_updates(
                collection_name=collection_id,
                artifact_filter=request.artifact_filter,
            )

            logger.info(
                f"Update check completed: "
                f"{sum(1 for r in update_results if r.update_available)} updates available"
            )

            # Return UpdateCheckResponse
            return UpdateCheckResponse.from_update_results(
                collection_id=collection_id,
                results=update_results,
            )
        else:
            # Metadata or sync mode - execute refresh
            result = refresher.refresh_collection(
                collection_name=collection_id,
                mode=core_mode,
                dry_run=request.dry_run,
                fields=request.fields,
                artifact_filter=request.artifact_filter,
            )

            logger.info(
                f"Refresh completed: {result.refreshed_count} refreshed, "
                f"{result.unchanged_count} unchanged"
            )

            # Return RefreshResponse
            return RefreshResponse.from_refresh_result(
                collection_id=collection_id,
                result=result,
                mode=effective_mode,
                dry_run=request.dry_run,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error refreshing collection '{collection_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh collection: {str(e)}",
        )


# =============================================================================
# Cache Statistics Endpoint (TASK-3.4)
# =============================================================================


@router.get(
    "/cache-stats",
    response_model=dict,
    tags=["user-collections"],
    summary="Get artifact cache statistics",
    description="Get statistics about artifact metadata cache health including "
    "total artifacts, fresh/stale counts, and staleness percentage.",
)
async def get_cache_stats(
    db_session: DbSessionDep,
    artifact_repo_ca: DbCollectionArtifactRepoDep,
    ttl_seconds: int = Query(
        default=None,
        description="Custom TTL in seconds for staleness calculation. "
        "Default is 30 minutes (1800 seconds).",
        ge=60,
        le=86400,
    ),
    collection_id: Optional[str] = Query(
        default=None,
        description="Filter stats to a specific collection ID. "
        "If not provided, stats are for all collections.",
    ),
    auth_context: AuthContext = Depends(get_auth_context),
) -> dict:
    """Get statistics about artifact metadata cache health.

    This endpoint returns metrics about the CollectionArtifact cache,
    useful for monitoring cache freshness and identifying performance issues.

    Returns:
        Dictionary with cache statistics:
        - total_artifacts: Total number of cached artifacts
        - fresh_count: Artifacts with synced_at within TTL
        - stale_count: Artifacts needing refresh (synced_at older than TTL or NULL)
        - percentage_stale: Percentage of stale artifacts (0-100)
        - oldest_sync_age_seconds: Age of oldest cached metadata in seconds
        - ttl_seconds: The TTL used for calculation
        - collection_id: The collection filter if provided

    Example response:
        {
            "total_artifacts": 42,
            "fresh_count": 40,
            "stale_count": 2,
            "percentage_stale": 4.8,
            "oldest_sync_age_seconds": 1234,
            "ttl_seconds": 1800
        }
    """
    from skillmeat.api.services.artifact_cache_service import (
        DEFAULT_METADATA_TTL_SECONDS,
        get_staleness_stats,
    )

    # Use default TTL if not provided
    effective_ttl = (
        ttl_seconds if ttl_seconds is not None else DEFAULT_METADATA_TTL_SECONDS
    )

    try:
        if collection_id:
            # Per-collection stats via repository DI (no raw session needed).
            stats = artifact_repo_ca.get_staleness_stats(collection_id, effective_ttl)
        else:
            # Global stats delegated to service (uses db_session internally).
            stats = get_staleness_stats(db_session, effective_ttl)

        logger.debug(
            f"Cache stats requested: total={stats['total_artifacts']}, "
            f"stale={stats['stale_count']} ({stats['percentage_stale']}%)"
        )

        return stats

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache statistics: {str(e)}",
        )
