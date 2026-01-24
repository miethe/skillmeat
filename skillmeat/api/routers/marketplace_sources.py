"""Marketplace sources API router for GitHub repository ingestion.

This router provides endpoints for managing GitHub repository sources that can be
scanned for Claude Code artifacts. It integrates with the service layer for scanning,
repository layer for data access, and transaction handler for atomic updates.

API Endpoints:
    POST /marketplace/sources - Create new GitHub source
    GET /marketplace/sources - List all sources (paginated)
    GET /marketplace/sources/{id} - Get source by ID
    PATCH /marketplace/sources/{id} - Update source
    DELETE /marketplace/sources/{id} - Delete source
    POST /marketplace/sources/{id}/rescan - Trigger rescan
    GET /marketplace/sources/{id}/artifacts - List artifacts with filters
    PATCH /marketplace/sources/{id}/artifacts/{entry_id} - Update artifact name
    POST /marketplace/sources/{id}/import - Import artifacts to collection
    PATCH /marketplace/sources/{id}/artifacts/{entry_id}/exclude - Mark artifact as excluded
    DELETE /marketplace/sources/{id}/artifacts/{entry_id}/exclude - Restore excluded artifact
    GET /marketplace/sources/{id}/catalog/{entry_id}/path-tags - Get path-based tag suggestions
    PATCH /marketplace/sources/{id}/catalog/{entry_id}/path-tags - Update path segment approval status
    GET /marketplace/sources/{id}/artifacts/{path}/files - Get file tree
    GET /marketplace/sources/{id}/artifacts/{path}/files/{file_path} - Get file content
    GET /marketplace/sources/{id}/auto-tags - Get auto-tags from GitHub topics
    PATCH /marketplace/sources/{id}/auto-tags - Approve/reject auto-tags
"""

import json
import logging
import re
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Literal, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from skillmeat.api.dependencies import ArtifactManagerDep, CollectionManagerDep
from skillmeat.cache.models import (
    DEFAULT_COLLECTION_ID,
    CollectionArtifact,
    get_session,
)
from skillmeat.api.schemas.common import PageInfo
from skillmeat.api.schemas.discovery import (
    BulkSyncItemResult,
    BulkSyncRequest,
    BulkSyncResponse,
)
from skillmeat.api.schemas.marketplace import (
    AutoTagSegment,
    AutoTagsResponse,
    CatalogEntryResponse,
    CatalogListResponse,
    CreateSourceRequest,
    DetectedArtifact,
    ExcludeArtifactRequest,
    ExtractedSegmentResponse,
    FileContentResponse,
    FileTreeEntry,
    FileTreeResponse,
    ImportRequest,
    ImportResultDTO,
    InferUrlRequest,
    InferUrlResponse,
    PathSegmentsResponse,
    ReimportRequest,
    ReimportResponse,
    ScanRequest,
    ScanResultDTO,
    SourceListResponse,
    SourceResponse,
    UpdateAutoTagRequest,
    UpdateAutoTagResponse,
    UpdateCatalogEntryNameRequest,
    UpdateSegmentStatusRequest,
    UpdateSegmentStatusResponse,
    UpdateSourceRequest,
)
from skillmeat.api.utils.github_cache import (
    DEFAULT_CONTENT_TTL,
    DEFAULT_TREE_TTL,
    build_content_key,
    build_tree_key,
    get_github_file_cache,
)
from skillmeat.cache.models import MarketplaceCatalogEntry, MarketplaceSource
from skillmeat.cache.repositories import (
    MarketplaceCatalogRepository,
    MarketplaceSourceRepository,
    MarketplaceTransactionHandler,
    MergeResult,
    NotFoundError,
)
from skillmeat.core.artifact import ArtifactType
from skillmeat.core.marketplace.github_scanner import (
    GitHubScanner,
    RateLimitError,
    scan_github_source,
)
from skillmeat.core.marketplace.import_coordinator import (
    ConflictStrategy,
    ImportCoordinator,
)
from skillmeat.core.marketplace.source_manager import SourceManager
from skillmeat.core.path_tags import PathSegmentExtractor, PathTagConfig
from skillmeat.core.validation import validate_artifact_name
from skillmeat.utils.metadata import extract_frontmatter

logger = logging.getLogger(__name__)

# Confidence threshold for hiding low-quality entries
CONFIDENCE_THRESHOLD = 30


# =============================================================================
# Database Session Dependency
# =============================================================================


def get_db_session():
    """Dependency that provides a database session.

    Yields a SQLAlchemy session and ensures cleanup on exit.
    """
    session = get_session()
    try:
        yield session
    finally:
        session.close()


DbSessionDep = Annotated[Session, Depends(get_db_session)]


def ensure_default_collection(session: Session) -> None:
    """Ensure the default collection exists in the database.

    Creates the default collection if it doesn't exist. This is a simplified
    version that doesn't return the collection object (not needed here).
    """
    from skillmeat.cache.models import Collection, DEFAULT_COLLECTION_NAME

    existing = session.query(Collection).filter_by(id=DEFAULT_COLLECTION_ID).first()
    if not existing:
        default_collection = Collection(
            id=DEFAULT_COLLECTION_ID,
            name=DEFAULT_COLLECTION_NAME,
            description="Default collection for all artifacts.",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(default_collection)
        session.commit()
        logger.info(f"Created default collection '{DEFAULT_COLLECTION_ID}'")


router = APIRouter(
    prefix="/marketplace/sources",
    tags=["marketplace-sources"],
)


# =============================================================================
# Helper Functions
# =============================================================================


def validate_file_path(path: str) -> str:
    """Validate and sanitize file path to prevent path traversal attacks.

    This function checks for common path traversal attack vectors including:
    - Parent directory references (..)
    - Absolute paths (starting with / or \\)
    - Null byte injection
    - URL-encoded traversal attempts

    Args:
        path: File path to validate

    Returns:
        Normalized, validated path with forward slashes

    Raises:
        HTTPException 400: If path contains traversal attempts or invalid characters
    """
    # Reject null bytes (can bypass validation in some systems)
    if "\x00" in path:
        logger.warning(f"Null byte injection attempt in path: {repr(path)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path: null bytes not allowed",
        )

    # Normalize path separators (Windows to Unix)
    normalized = path.replace("\\", "/")

    # Reject absolute paths
    if normalized.startswith("/"):
        logger.warning(f"Absolute path attempt: {path}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path: absolute paths not allowed",
        )

    # Reject path traversal attempts
    # Check for ".." in various forms that could bypass basic checks
    traversal_patterns = [
        "..",  # Direct parent reference
        "./.",  # Hidden traversal via current dir
    ]

    for pattern in traversal_patterns:
        if pattern in normalized:
            logger.warning(f"Path traversal attempt: {path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path: path traversal not allowed",
            )

    # Additional check: split by / and verify no segment is ".."
    segments = normalized.split("/")
    for segment in segments:
        if segment == "..":
            logger.warning(f"Path traversal via segment: {path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path: path traversal not allowed",
            )

    # Reject paths with URL-encoded traversal (e.g., %2e%2e)
    # This handles cases where the framework might not have decoded yet
    if re.search(r"%2e%2e|%252e%252e", path, re.IGNORECASE):
        logger.warning(f"URL-encoded traversal attempt: {path}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path: encoded traversal not allowed",
        )

    return normalized


def validate_source_id(source_id: str) -> str:
    """Validate source ID format.

    Args:
        source_id: Source identifier to validate

    Returns:
        Validated source ID

    Raises:
        HTTPException 400: If source ID format is invalid
    """
    # UUID format or alphanumeric with dashes
    if not re.match(r"^[a-zA-Z0-9\-]+$", source_id):
        logger.warning(f"Invalid source ID format: {source_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid source ID format",
        )
    return source_id


def parse_repo_url(repo_url: str) -> tuple[str, str]:
    """Parse GitHub repository URL to extract owner and repo name.

    Args:
        repo_url: Full GitHub repository URL

    Returns:
        Tuple of (owner, repo_name)

    Raises:
        ValueError: If URL format is invalid
    """
    # Remove trailing slash and .git
    url = repo_url.rstrip("/").replace(".git", "")

    # Match https://github.com/{owner}/{repo}
    match = re.match(r"^https://github\.com/([^/]+)/([^/]+)$", url)
    if not match:
        raise ValueError(
            f"Invalid GitHub repository URL format. "
            f"Expected: https://github.com/owner/repo, got: {repo_url}"
        )

    return match.group(1), match.group(2)


async def _validate_manual_map_paths(
    manual_map: dict[str, str],
    owner: str,
    repo: str,
    ref: str,
) -> None:
    """Validate that directory paths in manual_map exist in the repository.

    Fetches the repository tree from GitHub and verifies each directory path
    exists. Uses cached tree data when available to avoid extra API calls.

    Args:
        manual_map: Dictionary mapping directory paths to artifact types
        owner: Repository owner
        repo: Repository name
        ref: Git reference (branch, tag, SHA)

    Raises:
        HTTPException 422: If any directory path doesn't exist in repository
        HTTPException 500: If GitHub API call fails
    """
    if not manual_map:
        return

    try:
        # Initialize scanner to fetch tree (reuses cached data if available)
        scanner = GitHubScanner()
        tree, _actual_ref = scanner._fetch_tree(owner, repo, ref)

        # Extract all directory paths from tree
        # Tree items have "type": "tree" for directories, "type": "blob" for files
        dir_paths = {item["path"] for item in tree if item.get("type") == "tree"}

        # Validate each directory path in manual_map
        invalid_paths = []
        for dir_path in manual_map.keys():
            if dir_path not in dir_paths:
                invalid_paths.append(dir_path)

        if invalid_paths:
            # Format error message with all invalid paths
            paths_str = ", ".join(f"'{p}'" for p in sorted(invalid_paths))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid directory path(s) not found in repository: {paths_str}",
            )

        logger.debug(
            f"Validated {len(manual_map)} manual_map paths in {owner}/{repo}@{ref}"
        )

    except HTTPException:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(
            f"Failed to validate manual_map paths for {owner}/{repo}@{ref}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate directory paths: {str(e)}",
        ) from e


def source_to_response(source: MarketplaceSource) -> SourceResponse:
    """Convert MarketplaceSource ORM model to API response.

    Args:
        source: MarketplaceSource ORM instance

    Returns:
        SourceResponse DTO for API
    """
    return SourceResponse(
        id=source.id,
        repo_url=source.repo_url,
        owner=source.owner,
        repo_name=source.repo_name,
        ref=source.ref,
        root_hint=source.root_hint,
        trust_level=source.trust_level,
        visibility=source.visibility,
        scan_status=source.scan_status,
        artifact_count=source.artifact_count,
        last_sync_at=source.last_sync_at,
        last_error=source.last_error,
        created_at=source.created_at,
        updated_at=source.updated_at,
        description=source.description,
        notes=source.notes,
        enable_frontmatter_detection=source.enable_frontmatter_detection,
        manual_map=source.get_manual_map_dict(),
        repo_description=source.repo_description,
        repo_readme=source.repo_readme,
        tags=source.get_tags_list() or [],
        counts_by_type=source.get_counts_by_type_dict(),
    )


def get_collection_artifact_keys(collection_mgr) -> Set[str]:
    """Get set of 'type:name' keys for all artifacts in active collection.

    Used for efficient lookup when enriching catalog entries with in_collection status.

    Args:
        collection_mgr: CollectionManager instance

    Returns:
        Set of strings in format 'artifact_type:name' for each artifact in collection.
        Returns empty set if collection artifacts cannot be retrieved.
    """
    try:
        from skillmeat.core.artifact import ArtifactManager

        artifact_mgr = ArtifactManager(collection_mgr)
        artifacts = artifact_mgr.list_artifacts()
        return {f"{a.type.value}:{a.name}" for a in artifacts}
    except Exception as e:
        logger.warning(f"Failed to get collection artifacts: {e}")
        return set()


def entry_to_response(
    entry: MarketplaceCatalogEntry,
    collection_artifact_keys: Optional[Set[str]] = None,
) -> CatalogEntryResponse:
    """Convert MarketplaceCatalogEntry ORM model to API response.

    Args:
        entry: MarketplaceCatalogEntry ORM instance
        collection_artifact_keys: Optional set of 'type:name' keys for collection artifacts.
            Used to determine if the entry exists in the user's collection.

    Returns:
        CatalogEntryResponse DTO for API
    """
    # Compute is_duplicate based on excluded_reason
    is_duplicate = (
        entry.excluded_reason
        in (
            "duplicate_within_source",
            "duplicate_cross_source",
        )
        if entry.excluded_reason
        else False
    )

    # Check if artifact exists in collection
    in_collection = False
    if collection_artifact_keys is not None:
        # Key format: "artifact_type:name"
        key = f"{entry.artifact_type}:{entry.name}"
        in_collection = key in collection_artifact_keys

    return CatalogEntryResponse(
        id=entry.id,
        source_id=entry.source_id,
        artifact_type=entry.artifact_type,
        name=entry.name,
        path=entry.path,
        upstream_url=entry.upstream_url,
        detected_version=entry.detected_version,
        detected_sha=entry.detected_sha,
        detected_at=entry.detected_at,
        confidence_score=entry.confidence_score,
        raw_score=entry.raw_score,
        score_breakdown=entry.score_breakdown,
        status=entry.status,
        import_date=entry.import_date,
        import_id=entry.import_id,
        excluded_at=entry.excluded_at,
        excluded_reason=entry.excluded_reason,
        is_duplicate=is_duplicate,
        in_collection=in_collection,
    )


def parse_rate_limit_retry_after(error: RateLimitError) -> int:
    """Extract retry-after seconds from RateLimitError message.

    The RateLimitError message contains the wait time in seconds.
    Examples:
        - "Rate limited, reset in 45s"
        - "Rate limited for 60s"

    Args:
        error: RateLimitError exception

    Returns:
        Number of seconds to wait before retrying. Defaults to 60 if
        the time cannot be parsed from the error message.
    """
    import re

    message = str(error)
    # Match patterns like "45s" or "60s" in the message
    match = re.search(r"(\d+)s", message)
    if match:
        return int(match.group(1))
    return 60  # Default to 60 seconds if parsing fails


def get_effective_indexing_state(indexing_enabled: Optional[bool], mode: str) -> bool:
    """Resolve effective indexing state from global mode and per-source flag.

    This function implements the indexing state resolution logic based on the
    global marketplace indexing mode and per-source override flag:

    - "off" mode: Global disable overrides all per-source settings
    - "on" mode: Default enabled, sources can opt-out by setting indexing_enabled=False
    - "opt_in" mode: Default disabled, sources must opt-in by setting indexing_enabled=True

    Args:
        indexing_enabled: Per-source flag (None = use mode default, True/False = override)
        mode: Global indexing mode ("off", "on", or "opt_in")

    Returns:
        bool: Whether indexing should be enabled for this source

    Examples:
        >>> get_effective_indexing_state(None, "off")
        False
        >>> get_effective_indexing_state(True, "off")  # Global disable overrides
        False
        >>> get_effective_indexing_state(None, "on")
        True
        >>> get_effective_indexing_state(False, "on")  # Can opt-out
        False
        >>> get_effective_indexing_state(None, "opt_in")
        False
        >>> get_effective_indexing_state(True, "opt_in")  # Can opt-in
        True
    """
    if mode == "off":
        # Global disable overrides all per-source settings
        return False
    elif mode == "on":
        # Default enabled, can opt-out per-source
        return indexing_enabled if indexing_enabled is not None else True
    else:  # opt_in
        # Default disabled, can opt-in per-source
        return indexing_enabled if indexing_enabled is not None else False


# =============================================================================
# Frontmatter Extraction for Search Indexing
# =============================================================================


def _extract_frontmatter_for_artifact(
    scanner: GitHubScanner,
    source: MarketplaceSource,
    artifact: DetectedArtifact,
) -> Dict[str, Any]:
    """Extract frontmatter from artifact's manifest file for search indexing.

    For skill artifacts, fetches SKILL.md and extracts frontmatter fields.
    Returns empty dict for non-skill artifacts or on failure.

    Args:
        scanner: GitHubScanner instance for fetching file content
        source: MarketplaceSource with owner/repo_name info
        artifact: DetectedArtifact with path and type info

    Returns:
        Dict with keys: title, description, search_tags (list), search_text
        All values may be None if extraction fails or not applicable.
    """
    result: Dict[str, Optional[str]] = {
        "title": None,
        "description": None,
        "search_tags": None,
        "search_text": None,
    }

    # Only extract frontmatter for skill artifacts
    if artifact.artifact_type != "skill":
        return result

    # Build path to SKILL.md
    artifact_path = artifact.path.rstrip("/")
    skill_md_path = f"{artifact_path}/SKILL.md" if artifact_path else "SKILL.md"

    try:
        # Fetch SKILL.md content
        file_result = scanner.get_file_content(
            owner=source.owner,
            repo=source.repo_name,
            path=skill_md_path,
            ref=source.ref,
        )

        if not file_result or file_result.get("is_binary"):
            logger.debug(f"SKILL.md not found or binary: {skill_md_path}")
            return result

        content = file_result.get("content", "")
        if not content:
            return result

        # Extract frontmatter
        frontmatter = extract_frontmatter(content)
        if not frontmatter:
            return result

        # Extract title (try 'title' then 'name')
        title = frontmatter.get("title") or frontmatter.get("name")
        if title:
            # Truncate to 200 chars (model field limit)
            result["title"] = str(title)[:200]

        # Extract description
        description = frontmatter.get("description")
        if description:
            result["description"] = str(description)

        # Extract tags
        tags = frontmatter.get("tags", [])
        if tags:
            if isinstance(tags, list):
                result["search_tags"] = [str(t) for t in tags if t]
            elif isinstance(tags, str):
                result["search_tags"] = [t.strip() for t in tags.split(",") if t.strip()]

        # Build search_text from all fields
        search_parts = [artifact.name]
        if result["title"]:
            search_parts.append(result["title"])
        if result["description"]:
            search_parts.append(result["description"])
        if result["search_tags"]:
            search_parts.extend(result["search_tags"])

        result["search_text"] = " ".join(search_parts)

        logger.debug(
            f"Extracted frontmatter for {artifact_path}: "
            f"title={result['title']}, tags={result['search_tags']}"
        )

    except Exception as e:
        logger.warning(
            f"Failed to extract frontmatter for {skill_md_path}: {e}",
            exc_info=False,
        )
        # Return empty result on failure - non-blocking

    return result


# =============================================================================
# Shared Scan Logic
# =============================================================================


async def _perform_scan(
    source: MarketplaceSource,
    source_repo: MarketplaceSourceRepository,
    catalog_repo: MarketplaceCatalogRepository,
    transaction_handler: MarketplaceTransactionHandler,
) -> ScanResultDTO:
    """Perform repository scan and update source + catalog atomically.

    Shared by create_source() and rescan_source() endpoints.

    Args:
        source: MarketplaceSource ORM instance
        source_repo: Source repository for updates
        catalog_repo: Catalog repository (unused currently, for future)
        transaction_handler: Transaction handler for atomic updates

    Returns:
        ScanResultDTO with scan statistics

    Note:
        Handles scan errors gracefully - sets source status to "error"
        and returns error result instead of raising.
    """
    source_id = source.id

    # Mark as scanning
    source.scan_status = "scanning"
    source_repo.update(source)

    # Perform scan
    logger.info(f"Scanning repository: {source.repo_url} (ref={source.ref})")
    scanner = GitHubScanner()

    # Retrieve manual_map from source for artifact type override
    manual_map = source.get_manual_map_dict()
    if manual_map:
        logger.debug(
            f"Using manual_map with {len(manual_map)} mapping(s) for source {source_id}"
        )

    try:
        # Check for single artifact mode - bypass normal scanning
        if source.single_artifact_mode and source.single_artifact_type:
            logger.info(
                f"Single artifact mode enabled for {source.repo_url}, "
                f"type={source.single_artifact_type}"
            )

            # Create synthetic artifact for the entire repo/root_hint
            artifact_path = source.root_hint if source.root_hint else ""
            artifact_name = (
                source.repo_name
                if not source.root_hint
                else source.root_hint.split("/")[-1]
            )
            base_url = f"https://github.com/{source.owner}/{source.repo_name}"

            # Get commit SHA for versioning
            from skillmeat.core.github_client import get_github_client

            client = get_github_client()
            try:
                commit_sha = client.resolve_version(
                    f"{source.owner}/{source.repo_name}", source.ref
                )
            except Exception:
                commit_sha = source.ref  # Fallback to ref if resolution fails

            # Build upstream URL
            upstream_url = f"{base_url}/tree/{source.ref}"
            if artifact_path:
                upstream_url = f"{upstream_url}/{artifact_path}"

            # Create synthetic scan result with 100% confidence
            scan_result = ScanResultDTO(
                source_id=source_id,
                status="success",
                artifacts_found=1,
                new_count=1,
                updated_count=0,
                removed_count=0,
                unchanged_count=0,
                scan_duration_ms=0,
                errors=[],
                scanned_at=datetime.now(timezone.utc),
                artifacts=[
                    DetectedArtifact(
                        artifact_type=source.single_artifact_type,
                        name=artifact_name,
                        path=artifact_path or ".",
                        upstream_url=upstream_url,
                        confidence_score=100,
                        detected_version=None,
                        detected_sha=commit_sha,
                        raw_score=100,
                        score_breakdown=None,
                        metadata={"single_artifact_mode": True},
                    )
                ],
            )
        else:
            # Normal scanning path
            # Get database session for cross-source deduplication
            session = catalog_repo._get_session()

            scan_result = scanner.scan_repository(
                owner=source.owner,
                repo=source.repo_name,
                ref=source.ref,
                root_hint=source.root_hint,
                session=session,
                manual_mappings=manual_map,
            )

        # Load path tag config from source (or use defaults)
        config = PathTagConfig.defaults()
        if source.path_tag_config:
            try:
                config = PathTagConfig.from_json(source.path_tag_config)
            except ValueError as e:
                logger.warning(
                    f"Invalid path_tag_config for source {source.id}: {e}. "
                    "Using defaults."
                )
                config = PathTagConfig.defaults()

        # Create extractor if enabled
        extractor = PathSegmentExtractor(config) if config.enabled else None

        # Compute counts_by_type from scan results
        counts_by_type: Dict[str, int] = {}
        for artifact in scan_result.artifacts:
            artifact_type = artifact.artifact_type
            counts_by_type[artifact_type] = counts_by_type.get(artifact_type, 0) + 1

        # Update source and catalog atomically
        with transaction_handler.scan_update_transaction(source_id) as ctx:
            # Update source status
            ctx.update_source_status(
                status="success",
                artifact_count=scan_result.artifacts_found,
                error_message=None,
            )

            # Update counts_by_type on source
            source_in_session = (
                ctx.session.query(MarketplaceSource).filter_by(id=source_id).first()
            )
            if source_in_session:
                source_in_session.set_counts_by_type_dict(counts_by_type)

            # Determine if frontmatter indexing is enabled for this source
            indexing_enabled = source.indexing_enabled is True
            if indexing_enabled:
                logger.info(
                    f"Frontmatter indexing enabled for source {source_id}, "
                    f"extracting search metadata from artifacts"
                )

            # Convert detected artifacts to catalog entries
            new_entries = []
            for artifact in scan_result.artifacts:
                # Extract path segments if enabled
                path_segments_json = None
                if extractor:
                    try:
                        segments = extractor.extract(artifact.path)
                        path_segments_json = json.dumps(
                            {
                                "raw_path": artifact.path,
                                "extracted": [asdict(s) for s in segments],
                                "extracted_at": datetime.utcnow().isoformat(),
                            }
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to extract path segments for {artifact.path}: {e}"
                        )
                        # Continue without path_segments; extraction is non-blocking

                # Extract frontmatter for search indexing if enabled
                search_metadata: Dict[str, Any] = {
                    "title": None,
                    "description": None,
                    "search_tags": None,
                    "search_text": None,
                }
                if indexing_enabled:
                    search_metadata = _extract_frontmatter_for_artifact(
                        scanner, source, artifact
                    )

                # Serialize search_tags as JSON if present
                search_tags_json = None
                if search_metadata.get("search_tags"):
                    search_tags_json = json.dumps(search_metadata["search_tags"])

                entry = MarketplaceCatalogEntry(
                    id=str(uuid.uuid4()),
                    source_id=source_id,
                    artifact_type=artifact.artifact_type,
                    name=artifact.name,
                    path=artifact.path,
                    upstream_url=artifact.upstream_url,
                    confidence_score=artifact.confidence_score,
                    raw_score=artifact.raw_score,
                    score_breakdown=artifact.score_breakdown,
                    detected_sha=artifact.detected_sha,
                    detected_at=datetime.utcnow(),
                    # Copy exclusion status from deduplication engine
                    status=artifact.status if artifact.status else "new",
                    excluded_at=(
                        datetime.fromisoformat(artifact.excluded_at)
                        if artifact.excluded_at
                        else None
                    ),
                    excluded_reason=artifact.excluded_reason,
                    path_segments=path_segments_json,
                    # Cross-source search fields from frontmatter
                    title=search_metadata.get("title"),
                    description=search_metadata.get("description"),
                    search_tags=search_tags_json,
                    search_text=search_metadata.get("search_text"),
                )
                new_entries.append(entry)

            # Merge new entries with existing (preserves import metadata)
            merge_result = ctx.merge_catalog_entries(new_entries)

        # Set source_id in result
        scan_result.source_id = source_id

        # Add merge result info to scan result
        scan_result.updated_imports = merge_result.updated_imports
        scan_result.preserved_count = merge_result.preserved_count

        logger.info(
            f"Scan completed for {source.repo_url}: "
            f"{scan_result.artifacts_found} artifacts found, "
            f"{merge_result.preserved_count} preserved, "
            f"{len(merge_result.updated_imports)} imports with upstream changes"
        )
        return scan_result

    except Exception as scan_error:
        # Mark as error
        with transaction_handler.scan_update_transaction(source_id) as ctx:
            ctx.update_source_status(
                status="error",
                error_message=str(scan_error),
            )

        logger.error(f"Scan failed for {source.repo_url}: {scan_error}", exc_info=True)

        # Return error result (don't raise - let caller decide)
        return ScanResultDTO(
            source_id=source_id,
            status="error",
            artifacts_found=0,
            new_count=0,
            updated_count=0,
            removed_count=0,
            unchanged_count=0,
            scan_duration_ms=0,
            errors=[str(scan_error)],
            scanned_at=datetime.utcnow(),
        )


# =============================================================================
# API-000: URL Inference Utility
# =============================================================================


@router.post("/infer-url", response_model=InferUrlResponse)
async def infer_github_url(request: InferUrlRequest) -> InferUrlResponse:
    """Infer GitHub repository structure from a full URL.

    Parses GitHub URLs to extract repository URL, branch/tag, and subdirectory path.
    Supports various GitHub URL formats:
    - https://github.com/owner/repo
    - https://github.com/owner/repo/tree/branch
    - https://github.com/owner/repo/tree/branch/path/to/dir
    - https://github.com/owner/repo/blob/ref/path/to/file

    Args:
        request: URL to parse

    Returns:
        Inferred repository structure or error message

    Example:
        Input: https://github.com/davila7/claude-code-templates/tree/main/cli-tool/components
        Output: {
            "success": true,
            "repo_url": "https://github.com/davila7/claude-code-templates",
            "ref": "main",
            "root_hint": "cli-tool/components"
        }
    """
    url = request.url.strip()

    # Pattern for GitHub URLs
    # Matches: github.com/owner/repo[.git][/(tree|blob)/ref[/path...]]
    github_pattern = re.compile(
        r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/(tree|blob)/([^/]+)(?:/(.*))?)?$"
    )

    match = github_pattern.match(url)

    if not match:
        logger.info(f"Failed to parse GitHub URL: {url}")
        return InferUrlResponse(
            success=False,
            error="Invalid GitHub URL format. Expected: https://github.com/owner/repo[/tree/branch[/path]]",
        )

    owner, repo, url_type, ref, path = match.groups()

    # Build base repo URL (without .git suffix)
    repo_url = f"https://github.com/{owner}/{repo}"

    # Default ref to "main" if not specified
    ref = ref or "main"

    # For blob URLs (file links), extract directory path by removing filename
    root_hint = None
    if path:
        if url_type == "blob":
            # Remove filename from path (e.g., "path/to/file.py" -> "path/to")
            path_parts = path.rsplit("/", 1)
            root_hint = path_parts[0] if len(path_parts) > 1 else None
        else:
            # Tree URL - use path as-is
            root_hint = path

    logger.info(
        f"Successfully parsed GitHub URL: {url} -> repo={repo_url}, ref={ref}, root_hint={root_hint}"
    )

    return InferUrlResponse(
        success=True,
        repo_url=repo_url,
        ref=ref,
        root_hint=root_hint,
        error=None,
    )


# =============================================================================
# API-001: Sources CRUD
# =============================================================================


@router.post(
    "",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new GitHub source",
    description="""
    Add a new GitHub repository as a marketplace source for artifact scanning.

    The repository URL must be a valid GitHub URL (https://github.com/owner/repo).
    An initial scan is automatically triggered upon creation. The response includes
    the scan status and artifact count.

    **Manual Directory Mappings** (Optional):
    You can provide manual_map during creation to override automatic type detection.
    This is useful when you know the repository structure in advance.

    **Example Request**:
    ```json
    {
        "repo_url": "https://github.com/user/claude-templates",
        "ref": "main",
        "root_hint": "artifacts",
        "trust_level": "trusted",
        "manual_map": {
            "skills/advanced": "skill",
            "tools/cli": "command",
            "agents/research": "agent"
        },
        "enable_frontmatter_detection": true
    }
    ```

    **Validation**: All manual_map directory paths are validated against the repository
    tree during creation. Invalid paths will cause a 422 error.

    If the initial scan fails, the source is still created with scan_status="error".
    You can retry scanning using the /rescan endpoint.

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
    responses={
        201: {"description": "Source created and initial scan triggered"},
        400: {"description": "Bad request - invalid repository URL format"},
        409: {"description": "Conflict - repository URL already exists"},
        422: {"description": "Validation error - invalid manual_map directory paths"},
        500: {"description": "Internal server error"},
    },
)
async def create_source(request: CreateSourceRequest) -> SourceResponse:
    """Create a new GitHub repository source.

    Args:
        request: Source creation request with repository details

    Returns:
        Created source with metadata

    Raises:
        HTTPException 400: If repository URL format is invalid
        HTTPException 409: If repository URL already exists
        HTTPException 500: If database operation fails
    """
    try:
        # Validate and parse repository URL
        owner, repo_name = parse_repo_url(request.repo_url)
    except ValueError as e:
        logger.warning(f"Invalid repository URL: {request.repo_url}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Initialize repository
    source_repo = MarketplaceSourceRepository()

    # Check if source already exists
    existing = source_repo.get_by_repo_url(request.repo_url)
    if existing:
        logger.warning(f"Source already exists: {request.repo_url}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Source with repository URL '{request.repo_url}' already exists",
        )

    # Create new source
    source_id = str(uuid.uuid4())
    source = MarketplaceSource(
        id=source_id,
        repo_url=request.repo_url,
        owner=owner,
        repo_name=repo_name,
        ref=request.ref,
        root_hint=request.root_hint,
        trust_level=request.trust_level,
        visibility="public",  # TODO: Detect from GitHub API
        scan_status="pending",
        artifact_count=0,
        description=request.description,
        notes=request.notes,
        enable_frontmatter_detection=request.enable_frontmatter_detection,
        indexing_enabled=request.indexing_enabled,
    )

    # Store manual_map if provided
    if request.manual_map:
        source.set_manual_map_dict(request.manual_map)

    # Store single artifact mode settings
    if request.single_artifact_mode:
        source.single_artifact_mode = True
        source.single_artifact_type = request.single_artifact_type

    # Store tags if provided
    if request.tags:
        source.set_tags_list(request.tags)

    # Handle import_repo_description: fetch from GitHub if True
    # Also extract GitHub topics as auto-tags
    if request.import_repo_description:
        try:
            from skillmeat.core.github_client import get_github_client

            client = get_github_client()
            metadata = client.get_repo_metadata(f"{owner}/{repo_name}")
            source.repo_description = metadata.get("description")
            logger.info(f"Fetched repo description for {owner}/{repo_name}")

            # Extract GitHub topics as auto-tags
            topics = metadata.get("topics", [])
            if topics:
                auto_tags_data = {
                    "extracted": [
                        {
                            "value": topic,
                            "normalized": topic.lower().replace("_", "-"),
                            "status": "pending",
                            "source": "github_topic",
                        }
                        for topic in topics
                    ]
                }
                source.set_auto_tags_dict(auto_tags_data)
                logger.info(
                    f"Extracted {len(topics)} GitHub topics as auto-tags for {owner}/{repo_name}"
                )
        except Exception as e:
            logger.warning(
                f"Failed to fetch repo description for {owner}/{repo_name}: {e}"
            )
            # Don't fail creation - continue without repo_description

    # Handle import_repo_readme: fetch from GitHub if True
    if request.import_repo_readme:
        try:
            from skillmeat.core.github_client import get_github_client

            client = get_github_client()
            # Try common README filenames
            readme_content = None
            for readme_name in ["README.md", "README.rst", "README.txt", "README"]:
                try:
                    content_bytes = client.get_file_content(
                        f"{owner}/{repo_name}",
                        readme_name,
                        ref=request.ref,
                    )
                    readme_content = content_bytes.decode("utf-8")
                    # Truncate to 50KB if needed
                    if len(readme_content) > 50000:
                        readme_content = readme_content[:50000] + "\n... [truncated]"
                    break
                except Exception:
                    continue

            source.repo_readme = readme_content
            if readme_content:
                logger.info(f"Fetched README for {owner}/{repo_name}")
            else:
                logger.info(f"No README found for {owner}/{repo_name}")
        except Exception as e:
            logger.warning(f"Failed to fetch README for {owner}/{repo_name}: {e}")
            # Don't fail creation - continue without repo_readme

    try:
        created = source_repo.create(source)

        # Structured logging for source creation
        logger.info(
            "create_source_request",
            extra={
                "source_id": created.id,
                "repo_url": created.repo_url,
                "ref": created.ref,
                "root_hint": created.root_hint,
                "trust_level": created.trust_level,
                "has_manual_map": bool(request.manual_map),
                "manual_map_count": (
                    len(request.manual_map) if request.manual_map else 0
                ),
                "has_description": bool(request.description),
            },
        )

        # Trigger initial scan
        logger.info(f"Triggering initial scan for source: {created.id}")
        catalog_repo = MarketplaceCatalogRepository()
        transaction_handler = MarketplaceTransactionHandler()

        scan_result = await _perform_scan(
            source=created,
            source_repo=source_repo,
            catalog_repo=catalog_repo,
            transaction_handler=transaction_handler,
        )

        # Refresh source to get updated scan_status and artifact_count
        created = source_repo.get_by_id(created.id)

        logger.info(
            f"Initial scan completed for {created.id}: "
            f"status={scan_result.status}, artifacts={scan_result.artifacts_found}"
        )

        return source_to_response(created)
    except Exception as e:
        logger.error(f"Failed to create source: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create marketplace source",
        ) from e


@router.get(
    "",
    response_model=SourceListResponse,
    summary="List all GitHub sources",
    description="""
    List all GitHub repository sources with cursor-based pagination and optional filtering.

    Returns sources ordered by ID for stable pagination. Use the `cursor`
    parameter from the previous response to fetch the next page.

    **Filters** (all use AND logic - source must match all provided filters):
    - `artifact_type`: Filter sources containing artifacts of this type
    - `tags`: Filter by tags (repeated param, e.g., `?tags=ui&tags=ux`)
    - `trust_level`: Filter by trust level
    - `search`: Search in repo name, description, and tags

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
)
async def list_sources(
    limit: int = Query(50, ge=1, le=100, description="Maximum items per page"),
    cursor: Optional[str] = Query(None, description="Cursor for next page"),
    artifact_type: Optional[str] = Query(
        None,
        description="Filter by artifact type (skill, command, agent, hook, mcp-server)",
    ),
    tags: Optional[List[str]] = Query(
        None, description="Filter by tags (AND logic - must match all)"
    ),
    trust_level: Optional[str] = Query(
        None, description="Filter by trust level (untrusted, basic, verified, official)"
    ),
    search: Optional[str] = Query(
        None, description="Search in repo name, description, tags"
    ),
) -> SourceListResponse:
    """List all marketplace sources with pagination and filtering.

    Args:
        limit: Maximum number of items per page (1-100)
        cursor: Cursor for pagination (from previous response)
        artifact_type: Filter by artifact type (skill, command, agent, hook, mcp-server)
        tags: Filter by tags (AND logic - must match all provided tags)
        trust_level: Filter by trust level (untrusted, basic, verified, official)
        search: Search in repo name, description, tags

    Returns:
        Paginated list of sources with page info including total_count

    Raises:
        HTTPException 500: If database operation fails
    """
    source_repo = MarketplaceSourceRepository()
    source_manager = SourceManager()

    try:
        # Check if any filters are provided
        has_filters = any([artifact_type, tags, trust_level, search])

        if has_filters:
            # With filters: fetch all sources, filter in-memory, then paginate
            all_sources = source_repo.list_all()

            # Apply filters using SourceManager
            filtered_sources = source_manager.apply_filters(
                sources=all_sources,
                artifact_type=artifact_type,
                tags=tags,
                trust_level=trust_level,
                search=search,
            )

            # Sort by ID for stable pagination
            filtered_sources.sort(key=lambda s: s.id)

            total_count = len(filtered_sources)

            # Apply cursor-based pagination manually
            start_idx = 0
            if cursor:
                # Find the index after the cursor
                for idx, source in enumerate(filtered_sources):
                    if source.id == cursor:
                        start_idx = idx + 1
                        break

            # Slice for current page
            end_idx = start_idx + limit
            page_sources = filtered_sources[start_idx:end_idx]
            has_more = end_idx < len(filtered_sources)

            # Convert ORM models to API responses
            items = [source_to_response(source) for source in page_sources]

            # Build page info
            page_info = PageInfo(
                has_next_page=has_more,
                has_previous_page=cursor is not None,
                start_cursor=items[0].id if items else None,
                end_cursor=items[-1].id if items else None,
                total_count=total_count,
            )

            # Structured logging for filtered list request
            logger.info(
                "list_sources_request",
                extra={
                    "filters": {
                        "artifact_type": artifact_type,
                        "tags": tags,
                        "trust_level": trust_level,
                        "search": search,
                    },
                    "result_count": len(items),
                    "total_count": total_count,
                    "has_more": has_more,
                    "cursor": cursor,
                },
            )
        else:
            # Without filters: use repository's paginated query for efficiency
            result = source_repo.list_paginated(limit=limit, cursor=cursor)

            # Convert ORM models to API responses
            items = [source_to_response(source) for source in result.items]

            # Build page info
            page_info = PageInfo(
                has_next_page=result.has_more,
                has_previous_page=cursor is not None,
                start_cursor=items[0].id if items else None,
                end_cursor=items[-1].id if items else None,
                total_count=None,  # Not computed for efficiency without filters
            )

            # Structured logging for unfiltered list request
            logger.info(
                "list_sources_request",
                extra={
                    "filters": None,
                    "result_count": len(items),
                    "total_count": None,
                    "has_more": result.has_more,
                    "cursor": cursor,
                },
            )

        return SourceListResponse(items=items, page_info=page_info)
    except Exception as e:
        logger.error(f"Failed to list sources: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list marketplace sources",
        ) from e


@router.get(
    "/{source_id}",
    response_model=SourceResponse,
    summary="Get source by ID",
    description="""
    Retrieve a specific GitHub repository source by its unique identifier.

    Returns all source configuration including manual_map if configured.

    **Response Example**:
    ```json
    {
        "id": "src-abc123",
        "repo_url": "https://github.com/user/templates",
        "owner": "user",
        "repo_name": "templates",
        "ref": "main",
        "root_hint": "claude-artifacts",
        "trust_level": "trusted",
        "visibility": "public",
        "scan_status": "success",
        "artifact_count": 42,
        "manual_map": {
            "advanced-skills/python-backend": "skill",
            "cli-tools/scaffold": "command"
        },
        "enable_frontmatter_detection": true,
        "last_sync_at": "2025-01-06T12:00:00Z",
        "created_at": "2025-01-06T10:00:00Z",
        "updated_at": "2025-01-06T11:30:00Z"
    }
    ```

    **manual_map field**: Dictionary mapping directory paths to artifact types.
    Empty dictionary or null if no manual mappings configured.

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
    responses={
        200: {"description": "Source details retrieved successfully"},
        404: {"description": "Source not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_source(source_id: str) -> SourceResponse:
    """Get a marketplace source by ID.

    Args:
        source_id: Unique source identifier

    Returns:
        Source details

    Raises:
        HTTPException 404: If source not found
        HTTPException 500: If database operation fails
    """
    source_repo = MarketplaceSourceRepository()

    try:
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source not found: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        return source_to_response(source)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source {source_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve marketplace source",
        ) from e


@router.patch(
    "/{source_id}",
    response_model=SourceResponse,
    summary="Update source",
    description="""
    Update a GitHub repository source configuration.

    Allows updating ref (branch/tag/SHA), root_hint, manual_map, trust_level,
    description, notes, and frontmatter detection settings.
    Changes take effect on the next scan.

    **Manual Directory Mappings**:
    Use `manual_map` to override automatic artifact type detection for specific directories.
    This is useful when heuristic detection fails or when you want to force a directory
    to be treated as a specific artifact type.

    **Supported artifact types**: `skill`, `command`, `agent`, `mcp_server`, `hook`

    **Example Request with manual_map**:
    ```json
    {
        "manual_map": {
            "advanced-skills/python-backend": "skill",
            "cli-tools/scaffold": "command",
            "research-agents/market-analysis": "agent"
        }
    }
    ```

    **Validation**:
    - All directory paths must exist in the repository (validated against GitHub tree)
    - Artifact types must be one of: skill, command, agent, mcp_server, hook
    - Invalid paths or types will return 422 Unprocessable Entity

    **Clear Mapping**:
    To remove all manual mappings, send an empty dictionary:
    ```json
    {
        "manual_map": {}
    }
    ```

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
    responses={
        200: {"description": "Source updated successfully"},
        400: {"description": "Bad request - no update parameters provided"},
        404: {"description": "Source not found"},
        422: {
            "description": "Validation error - invalid directory path or artifact type"
        },
        500: {
            "description": "Internal server error - GitHub API failure or database error"
        },
    },
)
async def update_source(
    source_id: str,
    request: UpdateSourceRequest,
) -> SourceResponse:
    """Update a marketplace source.

    Supports partial updates to source configuration including:
    - ref: Change branch/tag/SHA to scan
    - root_hint: Modify subdirectory to scan
    - manual_map: Override artifact type detection for specific directories
    - trust_level: Update trust level
    - description: Update user description
    - notes: Update internal notes
    - enable_frontmatter_detection: Toggle frontmatter parsing

    Args:
        source_id: Unique source identifier
        request: Update request with fields to modify

    Returns:
        Updated source details

    Raises:
        HTTPException 400: If no update parameters provided
        HTTPException 404: If source not found
        HTTPException 422: If manual_map contains invalid directory paths or artifact types
        HTTPException 500: If database operation fails or GitHub API fails

    Example:
        Update manual mapping to override type detection:

        >>> request = UpdateSourceRequest(
        ...     manual_map={
        ...         "skills/python": "skill",
        ...         "commands/dev": "command"
        ...     }
        ... )
        >>> response = await update_source("src-123", request)
        >>> # Next scan will use manual_map for these directories
    """
    # Check if any update parameters provided
    if all(
        v is None
        for v in [
            request.ref,
            request.root_hint,
            request.manual_map,
            request.trust_level,
            request.description,
            request.notes,
            request.enable_frontmatter_detection,
            request.indexing_enabled,
            request.import_repo_description,
            request.import_repo_readme,
            request.tags,
        ]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one update parameter must be provided",
        )

    source_repo = MarketplaceSourceRepository()

    try:
        # Fetch existing source
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source not found: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        # Validate manual_map paths if provided
        if request.manual_map is not None:
            await _validate_manual_map_paths(
                manual_map=request.manual_map,
                owner=source.owner,
                repo=source.repo_name,
                ref=request.ref or source.ref,  # Use new ref if updating, else existing
            )

        # Apply updates
        if request.ref is not None:
            source.ref = request.ref
        if request.root_hint is not None:
            source.root_hint = request.root_hint
        if request.manual_map is not None:
            # Store as JSON string in database (use set_manual_map_dict helper)
            if request.manual_map:
                source.set_manual_map_dict(request.manual_map)
            else:
                # Clear mapping if empty dict or None
                source.manual_map = None
        if request.trust_level is not None:
            source.trust_level = request.trust_level
        if request.description is not None:
            source.description = request.description
        if request.notes is not None:
            source.notes = request.notes
        if request.enable_frontmatter_detection is not None:
            source.enable_frontmatter_detection = request.enable_frontmatter_detection
        if request.indexing_enabled is not None:
            source.indexing_enabled = request.indexing_enabled
        if request.tags is not None:
            source.set_tags_list(request.tags)

        # Handle import_repo_description: fetch from GitHub if True
        # Also refresh GitHub topics as auto-tags
        if request.import_repo_description is True:
            try:
                from skillmeat.core.github_client import get_github_client

                client = get_github_client()
                metadata = client.get_repo_metadata(
                    f"{source.owner}/{source.repo_name}"
                )
                source.repo_description = metadata.get("description")
                logger.info(
                    f"Fetched repo description for {source.owner}/{source.repo_name}"
                )

                # Extract/refresh GitHub topics as auto-tags
                # Preserve existing approval status for known tags
                topics = metadata.get("topics", [])
                if topics:
                    existing_auto_tags = source.get_auto_tags_dict() or {
                        "extracted": []
                    }
                    existing_status = {
                        seg["value"]: seg["status"]
                        for seg in existing_auto_tags.get("extracted", [])
                    }

                    auto_tags_data = {
                        "extracted": [
                            {
                                "value": topic,
                                "normalized": topic.lower().replace("_", "-"),
                                "status": existing_status.get(topic, "pending"),
                                "source": "github_topic",
                            }
                            for topic in topics
                        ]
                    }
                    source.set_auto_tags_dict(auto_tags_data)
                    logger.info(
                        f"Refreshed {len(topics)} GitHub topics as auto-tags for {source.owner}/{source.repo_name}"
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to fetch repo description for {source.owner}/{source.repo_name}: {e}"
                )
                # Don't fail the update - continue with other fields

        # Handle import_repo_readme: fetch from GitHub if True
        if request.import_repo_readme is True:
            try:
                from skillmeat.core.github_client import get_github_client

                client = get_github_client()
                # Try common README filenames
                readme_content = None
                for readme_name in ["README.md", "README.rst", "README.txt", "README"]:
                    try:
                        content_bytes = client.get_file_content(
                            f"{source.owner}/{source.repo_name}",
                            readme_name,
                            ref=source.ref,
                        )
                        readme_content = content_bytes.decode("utf-8")
                        # Truncate to 50KB if needed
                        if len(readme_content) > 50000:
                            readme_content = (
                                readme_content[:50000] + "\n... [truncated]"
                            )
                        break
                    except Exception:
                        continue

                source.repo_readme = readme_content
                if readme_content:
                    logger.info(f"Fetched README for {source.owner}/{source.repo_name}")
                else:
                    logger.info(
                        f"No README found for {source.owner}/{source.repo_name}"
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to fetch README for {source.owner}/{source.repo_name}: {e}"
                )
                # Don't fail the update - continue with other fields

        # Save updates
        updated = source_repo.update(source)

        # Structured logging for source update
        logger.info(
            "update_source_request",
            extra={
                "source_id": source_id,
                "repo_url": updated.repo_url,
                "updated_fields": [
                    field
                    for field, value in [
                        ("ref", request.ref),
                        ("root_hint", request.root_hint),
                        ("manual_map", request.manual_map),
                        ("trust_level", request.trust_level),
                        ("description", request.description),
                        ("notes", request.notes),
                        (
                            "enable_frontmatter_detection",
                            request.enable_frontmatter_detection,
                        ),
                        ("indexing_enabled", request.indexing_enabled),
                        ("import_repo_description", request.import_repo_description),
                        ("import_repo_readme", request.import_repo_readme),
                        ("tags", request.tags),
                    ]
                    if value is not None
                ],
                "has_manual_map": bool(request.manual_map),
                "manual_map_count": (
                    len(request.manual_map) if request.manual_map else 0
                ),
            },
        )

        return source_to_response(updated)
    except HTTPException:
        raise
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Failed to update source {source_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update marketplace source",
        ) from e


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete source",
    description="""
    Delete a GitHub repository source and all its associated catalog entries.

    This operation cannot be undone. All discovered artifacts from this source
    will be removed from the catalog.

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
)
async def delete_source(source_id: str) -> None:
    """Delete a marketplace source.

    Args:
        source_id: Unique source identifier

    Raises:
        HTTPException 404: If source not found
        HTTPException 500: If database operation fails
    """
    source_repo = MarketplaceSourceRepository()

    try:
        deleted = source_repo.delete(source_id)
        if not deleted:
            logger.warning(f"Source not found for deletion: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        logger.info(f"Deleted marketplace source: {source_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete source {source_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete marketplace source",
        ) from e


# =============================================================================
# API-002: Rescan Endpoint
# =============================================================================


@router.post(
    "/{source_id}/rescan",
    response_model=ScanResultDTO,
    summary="Trigger repository rescan",
    description="""
    Trigger a rescan of the GitHub repository to discover new or updated artifacts.

    This operation is currently synchronous (runs in the request lifecycle).
    For large repositories, this may take several seconds. Future versions may
    support asynchronous background jobs.

    **Scan Process**:
    1. Fetch the repository tree from GitHub
    2. Apply heuristic detection to identify artifacts
    3. **Apply manual_map overrides** (if configured on source)
    4. Deduplicate artifacts within the source (same content, different paths)
    5. Deduplicate artifacts against existing collection (already imported)
    6. Update the catalog with discovered unique artifacts
    7. Update source metadata (artifact_count, last_sync_at, etc.)

    **Manual Mappings**:
    The scan uses any manual_map configured on the source to override automatic type
    detection. For example, if manual_map contains `{"advanced-skills": "skill"}`,
    all artifacts in the `advanced-skills` directory will be treated as skills
    regardless of heuristic detection results.

    **Response includes deduplication statistics**:
    - `duplicates_within_source`: Duplicate artifacts found in this repo scan
    - `duplicates_cross_source`: Artifacts already in collection from other sources
    - `total_detected`: Total artifacts before deduplication
    - `total_unique`: Unique artifacts added to catalog

    **Example Response**:
    ```json
    {
        "source_id": "src-abc123",
        "status": "success",
        "artifacts_found": 42,
        "new_count": 5,
        "updated_count": 2,
        "removed_count": 1,
        "unchanged_count": 34,
        "scan_duration_ms": 3421,
        "scanned_at": "2025-01-06T12:00:00Z",
        "duplicates_within_source": 3,
        "duplicates_cross_source": 2,
        "total_detected": 52,
        "total_unique": 47
    }
    ```

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
    responses={
        200: {"description": "Scan completed successfully"},
        404: {"description": "Source not found"},
        500: {"description": "Scan failed - check error message in response"},
    },
)
async def rescan_source(source_id: str, request: ScanRequest = None) -> ScanResultDTO:
    """Trigger a rescan of a marketplace source.

    Args:
        source_id: Unique source identifier
        request: Optional scan configuration (force rescan, etc.)

    Returns:
        Scan result with statistics

    Raises:
        HTTPException 404: If source not found
        HTTPException 500: If scan fails
    """
    if request is None:
        request = ScanRequest()

    source_repo = MarketplaceSourceRepository()
    catalog_repo = MarketplaceCatalogRepository()
    transaction_handler = MarketplaceTransactionHandler()

    try:
        # Fetch source
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source not found: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        # Perform scan using shared helper
        scan_result = await _perform_scan(
            source=source,
            source_repo=source_repo,
            catalog_repo=catalog_repo,
            transaction_handler=transaction_handler,
        )

        return scan_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rescan source {source_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rescan source: {str(e)}",
        ) from e


# =============================================================================
# API-002a: Bulk Sync Imported Artifacts
# =============================================================================


@router.post(
    "/{source_id}/sync-imported",
    response_model=BulkSyncResponse,
    summary="Sync imported artifacts from source",
    operation_id="sync_imported_artifacts",
    description="""
    Sync one or more imported artifacts from this source with their upstream versions.

    This endpoint is used after a rescan detects that imported artifacts have upstream
    changes (SHA mismatch). It fetches the latest version from GitHub and updates the
    artifacts in the collection.

    **Prerequisites**:
    - Artifacts must have status="imported" in the catalog
    - Artifacts must have a valid import_id linking to the collection artifact

    **Sync behavior**:
    - Fetches the latest version from the upstream GitHub source
    - Applies changes using "overwrite" strategy (upstream wins)
    - Reports conflicts if merge is not possible

    **Example**:
    ```bash
    curl -X POST "http://localhost:8080/api/v1/marketplace/sources/src-abc123/sync-imported" \\
        -H "Content-Type: application/json" \\
        -d '{"artifact_ids": ["cat_canvas_design", "cat_my_skill"]}'
    ```

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
)
async def sync_imported_artifacts(
    source_id: str,
    request: BulkSyncRequest,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
) -> BulkSyncResponse:
    """Sync imported artifacts from a marketplace source with upstream.

    Args:
        source_id: Unique source identifier
        request: Sync request with artifact entry IDs

    Returns:
        Bulk sync response with per-artifact results

    Raises:
        HTTPException 400: If artifact_ids is empty or invalid
        HTTPException 404: If source not found or entry IDs invalid
        HTTPException 500: If sync operation fails
    """
    if not request.artifact_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="artifact_ids cannot be empty",
        )

    source_repo = MarketplaceSourceRepository()
    catalog_repo = MarketplaceCatalogRepository()

    try:
        # Verify source exists
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source not found: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        # Track results
        results: List[BulkSyncItemResult] = []
        synced_count = 0
        skipped_count = 0
        failed_count = 0

        # Get collection name for sync operations
        collection_name = collection_mgr.get_active_collection_name()

        # Process each artifact
        for entry_id in request.artifact_ids:
            entry = catalog_repo.get_by_id(entry_id)

            # Verify entry exists
            if not entry:
                logger.warning(f"Catalog entry not found: {entry_id}")
                results.append(
                    BulkSyncItemResult(
                        entry_id=entry_id,
                        artifact_name="unknown",
                        success=False,
                        message=f"Catalog entry '{entry_id}' not found",
                        has_conflicts=False,
                        conflicts=None,
                    )
                )
                failed_count += 1
                continue

            # Verify entry belongs to this source
            if entry.source_id != source_id:
                logger.warning(
                    f"Entry {entry_id} does not belong to source {source_id}"
                )
                results.append(
                    BulkSyncItemResult(
                        entry_id=entry_id,
                        artifact_name=entry.name,
                        success=False,
                        message=f"Entry does not belong to source '{source_id}'",
                        has_conflicts=False,
                        conflicts=None,
                    )
                )
                failed_count += 1
                continue

            # Verify entry is imported
            if entry.status != "imported":
                logger.info(
                    f"Entry {entry_id} is not imported (status={entry.status}), skipping"
                )
                results.append(
                    BulkSyncItemResult(
                        entry_id=entry_id,
                        artifact_name=entry.name,
                        success=True,
                        message=f"Skipped: entry status is '{entry.status}', not 'imported'",
                        has_conflicts=False,
                        conflicts=None,
                    )
                )
                skipped_count += 1
                continue

            # Verify entry has import_id linking to collection artifact
            if not entry.import_id:
                logger.warning(f"Entry {entry_id} has no import_id")
                results.append(
                    BulkSyncItemResult(
                        entry_id=entry_id,
                        artifact_name=entry.name,
                        success=False,
                        message="Entry has no import_id linking to collection artifact",
                        has_conflicts=False,
                        conflicts=None,
                    )
                )
                failed_count += 1
                continue

            # Parse artifact type
            try:
                artifact_type = ArtifactType(entry.artifact_type)
            except ValueError:
                logger.error(
                    f"Invalid artifact type for entry {entry_id}: {entry.artifact_type}"
                )
                results.append(
                    BulkSyncItemResult(
                        entry_id=entry_id,
                        artifact_name=entry.name,
                        success=False,
                        message=f"Invalid artifact type: {entry.artifact_type}",
                        has_conflicts=False,
                        conflicts=None,
                    )
                )
                failed_count += 1
                continue

            # Perform sync using ArtifactManager
            try:
                # Fetch update from upstream
                fetch_result = artifact_mgr.fetch_update(
                    artifact_name=entry.name,
                    artifact_type=artifact_type,
                    collection_name=collection_name,
                )

                # Check if fetch was successful
                if fetch_result.error:
                    results.append(
                        BulkSyncItemResult(
                            entry_id=entry_id,
                            artifact_name=entry.name,
                            success=False,
                            message=f"Failed to fetch update: {fetch_result.error}",
                            has_conflicts=False,
                            conflicts=None,
                        )
                    )
                    failed_count += 1
                    continue

                # If no update available
                if not fetch_result.has_update:
                    results.append(
                        BulkSyncItemResult(
                            entry_id=entry_id,
                            artifact_name=entry.name,
                            success=True,
                            message="Already up to date with upstream",
                            has_conflicts=False,
                            conflicts=None,
                        )
                    )
                    synced_count += 1
                    continue

                # Apply update using "overwrite" strategy (upstream wins)
                update_result = artifact_mgr.apply_update_strategy(
                    fetch_result=fetch_result,
                    strategy="overwrite",
                    interactive=False,
                    auto_resolve="theirs",
                    collection_name=collection_name,
                )

                # Check result
                if update_result.updated:
                    logger.info(
                        f"Successfully synced artifact '{entry.name}' from source {source_id}"
                    )
                    results.append(
                        BulkSyncItemResult(
                            entry_id=entry_id,
                            artifact_name=entry.name,
                            success=True,
                            message="Successfully synced with upstream",
                            has_conflicts=False,
                            conflicts=None,
                        )
                    )
                    synced_count += 1
                else:
                    # Update may have conflicts
                    conflict_files = (
                        update_result.conflicted_files
                        if hasattr(update_result, "conflicted_files")
                        else None
                    )
                    results.append(
                        BulkSyncItemResult(
                            entry_id=entry_id,
                            artifact_name=entry.name,
                            success=False,
                            message="Sync failed: conflicts detected or update rejected",
                            has_conflicts=bool(conflict_files),
                            conflicts=conflict_files,
                        )
                    )
                    failed_count += 1

            except Exception as sync_error:
                logger.error(
                    f"Failed to sync artifact '{entry.name}': {sync_error}",
                    exc_info=True,
                )
                results.append(
                    BulkSyncItemResult(
                        entry_id=entry_id,
                        artifact_name=entry.name,
                        success=False,
                        message=f"Sync error: {str(sync_error)}",
                        has_conflicts=False,
                        conflicts=None,
                    )
                )
                failed_count += 1

        return BulkSyncResponse(
            total=len(request.artifact_ids),
            synced=synced_count,
            skipped=skipped_count,
            failed=failed_count,
            results=results,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to sync imported artifacts from source {source_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync imported artifacts: {str(e)}",
        ) from e


# =============================================================================
# API-003: Artifacts Listing
# =============================================================================


@router.get(
    "/{source_id}/artifacts",
    response_model=CatalogListResponse,
    summary="List artifacts from source",
    operation_id="list_source_artifacts",
    description="""
    List all artifacts discovered from a specific source with optional filtering and sorting.

    By default, excluded artifacts are hidden from results. Use `include_excluded=true`
    to include them in listings (useful for reviewing or restoring excluded entries).

    Supports filtering by:
    - `artifact_type`: skill, command, agent, etc.
    - `status`: new, updated, removed, imported, excluded
    - `min_confidence`: Minimum confidence score (0-100)
    - `max_confidence`: Maximum confidence score (0-100)
    - `include_below_threshold`: Include artifacts below 30% confidence threshold (default: false)
    - `include_excluded`: Include excluded artifacts in results (default: false)

    Supports sorting by:
    - `sort_by`: Field to sort by - confidence, name, or date (detected_at). Default: confidence
    - `sort_order`: Sort order - asc or desc. Default: desc (highest confidence first)

    Results are paginated using cursor-based pagination for efficiency.

    **Examples**:

    List only non-excluded artifacts (default):
    ```bash
    curl -X GET "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts"
    ```

    List including excluded artifacts:
    ```bash
    curl -X GET "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts?include_excluded=true"
    ```

    Filter by artifact type with minimum confidence:
    ```bash
    curl -X GET "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts?artifact_type=skill&min_confidence=70"
    ```

    Sort by name ascending:
    ```bash
    curl -X GET "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts?sort_by=name&sort_order=asc"
    ```

    Pagination example:
    ```bash
    curl -X GET "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts?limit=25&cursor=abc123"
    ```

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
)
async def list_artifacts(
    source_id: str,
    artifact_type: Optional[str] = Query(
        None, description="Filter by artifact type (skill, command, agent, etc.)"
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status (new, updated, removed, imported, excluded)",
    ),
    min_confidence: Optional[int] = Query(
        None, ge=0, le=100, description="Minimum confidence score (0-100)"
    ),
    max_confidence: Optional[int] = Query(
        None, ge=0, le=100, description="Maximum confidence score (0-100)"
    ),
    include_below_threshold: bool = Query(
        False,
        description="Include artifacts below 30% confidence threshold (default: false)",
    ),
    include_excluded: bool = Query(
        False, description="Include excluded artifacts in results (default: false)"
    ),
    sort_by: Optional[str] = Query(
        "confidence",
        description="Sort field: confidence, name, date (detected_at)",
        regex="^(confidence|name|date)$",
    ),
    sort_order: Optional[str] = Query(
        "desc",
        description="Sort order: asc or desc",
        regex="^(asc|desc)$",
    ),
    limit: int = Query(50, ge=1, le=100, description="Maximum items per page (1-100)"),
    cursor: Optional[str] = Query(
        None, description="Cursor for pagination (from previous response)"
    ),
    collection_mgr: CollectionManagerDep = None,
) -> CatalogListResponse:
    """List artifacts from a source with optional filters and sorting.

    Retrieves catalog entries from a source with support for filtering, sorting, and pagination.
    By default, excluded artifacts are filtered out; set include_excluded=true to see them.

    Args:
        source_id: Unique source identifier
        artifact_type: Optional artifact type filter
        status: Optional status filter (new, updated, removed, imported, excluded)
        min_confidence: Filter entries with confidence >= this value (0-100)
        max_confidence: Filter entries with confidence <= this value (0-100)
        include_below_threshold: If True, include entries <30% that are normally hidden
        include_excluded: If True, include entries with status="excluded" (default: False)
        sort_by: Field to sort by - confidence, name, or date (detected_at). Default: confidence
        sort_order: Sort order - asc or desc. Default: desc (highest first)
        limit: Maximum items per page (1-100)
        cursor: Pagination cursor from previous response

    Returns:
        Paginated list of catalog entries with counts_by_status and counts_by_type statistics

    Raises:
        HTTPException 404: If source not found
        HTTPException 500: If database operation fails

    Example:
        >>> # List artifacts sorted by name ascending
        >>> response = await list_artifacts(
        ...     source_id="src-123",
        ...     sort_by="name",
        ...     sort_order="asc",
        ...     limit=50
        ... )
        >>> # Count by status shows excluded entries
        >>> assert response.counts_by_status.get("excluded", 0) >= 0
    """
    source_repo = MarketplaceSourceRepository()
    catalog_repo = MarketplaceCatalogRepository()

    try:
        # Verify source exists
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source not found: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        # Calculate effective minimum confidence based on threshold toggle
        # Default behavior (include_below_threshold=False): hide entries below 30%
        # When include_below_threshold=True: show ALL entries including those <30%
        effective_min_confidence = min_confidence
        if not include_below_threshold:
            # Apply the 30% threshold by default
            if effective_min_confidence is None:
                effective_min_confidence = CONFIDENCE_THRESHOLD
            else:
                # If user provided min_confidence, take the stricter of the two
                # Examples:
                # - min=20, threshold=30 → effective=30 (threshold wins)
                # - min=40, threshold=30 → effective=40 (min is stricter)
                effective_min_confidence = max(
                    effective_min_confidence, CONFIDENCE_THRESHOLD
                )

        # Build status filter list
        # When include_excluded=False (default), we exclude entries with status="excluded"
        effective_statuses: Optional[List[str]] = None
        if status_filter:
            # User specified a status filter - use it directly
            effective_statuses = [status_filter]

        # Determine if we need filtered query
        # When include_excluded=False and no status filter, we still need to filter
        needs_filtered_query = (
            artifact_type
            or status_filter
            or effective_min_confidence
            or max_confidence
            or not include_excluded
        )

        if needs_filtered_query:
            # Get filtered entries using get_source_catalog
            entries = catalog_repo.get_source_catalog(
                source_id=source_id,
                artifact_types=[artifact_type] if artifact_type else None,
                statuses=effective_statuses,
                min_confidence=effective_min_confidence,
                max_confidence=max_confidence,
            )

            # Filter out excluded entries if not explicitly requested
            # This handles the case where no status filter was provided
            if not include_excluded and not status_filter:
                entries = [e for e in entries if e.status != "excluded"]

            # Apply sorting before pagination
            if sort_by:
                reverse = sort_order == "desc"
                if sort_by == "confidence":
                    entries.sort(key=lambda e: e.confidence_score, reverse=reverse)
                elif sort_by == "name":
                    entries.sort(key=lambda e: e.name.lower(), reverse=reverse)
                elif sort_by == "date":
                    entries.sort(key=lambda e: e.detected_at or "", reverse=reverse)

            # Manual pagination for filtered results
            # Convert to list and apply cursor
            if cursor:
                # Find cursor position - cursor is the last item ID from previous page
                # We need to find it and start from the NEXT item
                cursor_idx = next(
                    (i for i, e in enumerate(entries) if str(e.id) == cursor),
                    -1,
                )
                if cursor_idx >= 0:
                    entries = entries[
                        cursor_idx + 1 :
                    ]  # Skip cursor item, start from next

            # Apply limit
            has_more = len(entries) > limit
            items = entries[:limit]
        else:
            # Use efficient paginated query (only when include_excluded=True and no other filters)
            result = catalog_repo.list_paginated(
                source_id=source_id,
                limit=limit,
                cursor=cursor,
            )
            entries = result.items
            has_more = result.has_more

            # Apply sorting (note: this loads all into memory but only happens when no filters applied)
            if sort_by:
                reverse = sort_order == "desc"
                if sort_by == "confidence":
                    entries.sort(key=lambda e: e.confidence_score, reverse=reverse)
                elif sort_by == "name":
                    entries.sort(key=lambda e: e.name.lower(), reverse=reverse)
                elif sort_by == "date":
                    entries.sort(key=lambda e: e.detected_at or "", reverse=reverse)

            items = entries

        # Get collection artifact keys for in_collection check
        collection_keys = (
            get_collection_artifact_keys(collection_mgr) if collection_mgr else set()
        )

        # Convert to response DTOs
        response_items = [entry_to_response(entry, collection_keys) for entry in items]

        # Get aggregated counts (needed for total_count in page_info)
        counts_by_status = catalog_repo.count_by_status(source_id=source_id)
        counts_by_type = catalog_repo.count_by_type(source_id=source_id)

        # Build page info
        page_info = PageInfo(
            has_next_page=has_more,
            has_previous_page=cursor is not None,
            start_cursor=response_items[0].id if response_items else None,
            end_cursor=response_items[-1].id if response_items else None,
            total_count=sum(counts_by_status.values()),
        )

        logger.debug(f"Listed {len(response_items)} artifacts for source {source_id}")
        return CatalogListResponse(
            items=response_items,
            page_info=page_info,
            counts_by_status=counts_by_status,
            counts_by_type=counts_by_type,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to list artifacts for source {source_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list artifacts",
        ) from e


# =============================================================================
# API-003b: Update Catalog Entry Name
# =============================================================================


@router.patch(
    "/{source_id}/artifacts/{entry_id}",
    response_model=CatalogEntryResponse,
    summary="Update catalog entry name",
    operation_id="update_catalog_entry_name",
    description="""
    Update the display name for a catalog entry.

    The updated name is used when importing the artifact into the user's collection
    and persists until the next rescan of the source.

    **Request Body**:
    - `name` (string, required): New artifact name (1-100 chars, no path separators)

    **Response**: Updated catalog entry

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
)
async def update_catalog_entry_name(
    source_id: str,
    entry_id: str,
    request: UpdateCatalogEntryNameRequest,
    collection_mgr: CollectionManagerDep = None,
) -> CatalogEntryResponse:
    """Update the name for a catalog entry."""
    source_repo = MarketplaceSourceRepository()
    catalog_repo = MarketplaceCatalogRepository()
    collection_keys = (
        get_collection_artifact_keys(collection_mgr) if collection_mgr else set()
    )

    normalized_name = request.name.strip()
    is_valid, error = validate_artifact_name(normalized_name)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error or "Invalid artifact name",
        )

    try:
        # Verify source exists
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source not found: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        session = catalog_repo._get_session()
        try:
            entry = (
                session.query(MarketplaceCatalogEntry).filter_by(id=entry_id).first()
            )
            if not entry:
                logger.warning(f"Catalog entry not found: {entry_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Catalog entry with ID '{entry_id}' not found",
                )

            # Verify entry belongs to this source
            if entry.source_id != source_id:
                logger.warning(
                    f"Entry {entry_id} does not belong to source {source_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Entry '{entry_id}' does not belong to source '{source_id}'",
                )

            entry.name = normalized_name
            session.commit()
            session.refresh(entry)

            logger.info(f"Updated catalog entry name: {entry_id} -> {normalized_name}")
            return entry_to_response(entry, collection_keys)

        except HTTPException:
            session.rollback()
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to update catalog entry name {entry_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update catalog entry name: {str(e)}",
        ) from e


# =============================================================================
# API-004: Import Endpoint
# =============================================================================


@router.post(
    "/{source_id}/import",
    response_model=ImportResultDTO,
    summary="Import artifacts to collection",
    description="""
    Import selected artifacts from the catalog to the user's local collection.

    Specify which catalog entries to import and how to handle conflicts with
    existing artifacts:
    - skip: Skip conflicting artifacts (default)
    - overwrite: Replace existing artifacts
    - rename: Rename imported artifacts with suffix

    The import operation will:
    1. Validate all entry IDs belong to this source
    2. Check for conflicts with existing collection artifacts
    3. Download artifacts from upstream URLs (placeholder for now)
    4. Update catalog entry statuses to "imported"
    5. Return summary of imported, skipped, and failed entries

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
)
async def import_artifacts(
    source_id: str,
    request: ImportRequest,
    collection_mgr: CollectionManagerDep,
    session: DbSessionDep,
) -> ImportResultDTO:
    """Import catalog entries to local collection.

    Args:
        source_id: Unique source identifier
        request: Import request with entry IDs and conflict strategy
        session: Database session for adding artifacts to default collection

    Returns:
        Import result with statistics

    Raises:
        HTTPException 400: If entry_ids is empty or invalid
        HTTPException 404: If source not found or entry IDs invalid
        HTTPException 500: If import operation fails
    """
    if not request.entry_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="entry_ids cannot be empty",
        )

    source_repo = MarketplaceSourceRepository()
    catalog_repo = MarketplaceCatalogRepository()
    transaction_handler = MarketplaceTransactionHandler()

    try:
        # Verify source exists
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source not found: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        # Fetch catalog entries
        entries_data = []
        for entry_id in request.entry_ids:
            entry = catalog_repo.get_by_id(entry_id)
            if not entry:
                logger.warning(f"Catalog entry not found: {entry_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Catalog entry with ID '{entry_id}' not found",
                )

            # Verify entry belongs to this source
            if entry.source_id != source_id:
                logger.warning(
                    f"Entry {entry_id} does not belong to source {source_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Entry '{entry_id}' does not belong to source '{source_id}'",
                )

            # Extract description from metadata_json if available
            entry_metadata = entry.get_metadata_dict() or {}
            description = entry_metadata.get("description")

            # Extract approved tags from path_segments
            tags = []
            if entry.path_segments:
                try:
                    segments_data = json.loads(entry.path_segments)
                    extracted = segments_data.get("extracted", [])
                    # Only include approved tags
                    tags = [
                        seg["normalized"]
                        for seg in extracted
                        if seg.get("status") == "approved"
                    ]
                except (json.JSONDecodeError, KeyError):
                    logger.warning(
                        f"Failed to parse path_segments for entry {entry.id}"
                    )
                    tags = []

            # Convert to dict for ImportCoordinator
            entries_data.append(
                {
                    "id": entry.id,
                    "artifact_type": entry.artifact_type,
                    "name": entry.name,
                    "upstream_url": entry.upstream_url,
                    "path": entry.path,
                    "description": description,
                    "tags": tags,
                }
            )

        # Perform import using ImportCoordinator
        # Always import to "default" collection - other collections not supported yet
        coordinator = ImportCoordinator(
            collection_name="default",
            collection_mgr=collection_mgr,
        )
        strategy = ConflictStrategy(request.conflict_strategy)

        import_result = coordinator.import_entries(
            entries=entries_data,
            source_id=source_id,
            strategy=strategy,
            source_ref=source.ref,
        )

        # Add imported artifacts to default database collection
        try:
            ensure_default_collection(session)
            db_added_count = 0
            for entry in import_result.entries:
                if entry.status.value == "success":
                    artifact_id = f"{entry.artifact_type}:{entry.name}"
                    # Use merge to handle duplicates gracefully (idempotent)
                    association = CollectionArtifact(
                        collection_id=DEFAULT_COLLECTION_ID,
                        artifact_id=artifact_id,
                        added_at=datetime.utcnow(),
                    )
                    session.merge(association)
                    db_added_count += 1
            session.commit()
            logger.info(
                f"Added {db_added_count} artifacts to default database collection"
            )
        except Exception as e:
            logger.error(f"Failed to add artifacts to database collection: {e}")
            session.rollback()
            # Don't fail the entire import - file-system import already succeeded

        # Update catalog entry statuses atomically
        with transaction_handler.import_transaction(source_id) as ctx:
            # Get list of successfully imported entry IDs
            imported_ids = [
                entry.catalog_entry_id
                for entry in import_result.entries
                if entry.status.value == "success"
            ]

            if imported_ids:
                ctx.mark_imported(imported_ids, import_result.import_id)

            # Mark failed entries
            failed_entries = [
                entry
                for entry in import_result.entries
                if entry.status.value == "error"
            ]
            for entry in failed_entries:
                ctx.mark_failed(
                    [entry.catalog_entry_id],
                    entry.error_message or "Unknown error",
                )

        # Build response DTO
        result_dto = ImportResultDTO(
            imported_count=import_result.success_count,
            skipped_count=import_result.skipped_count,
            error_count=import_result.error_count,
            imported_ids=imported_ids,
            skipped_ids=[
                e.catalog_entry_id
                for e in import_result.entries
                if e.status.value == "skipped"
            ],
            errors=[
                {
                    "entry_id": e.catalog_entry_id,
                    "error": e.error_message or "Unknown error",
                }
                for e in failed_entries
            ],
        )

        logger.info(
            f"Import completed for source {source_id}: "
            f"{result_dto.imported_count} imported, "
            f"{result_dto.skipped_count} skipped, "
            f"{result_dto.error_count} errors"
        )
        return result_dto

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to import artifacts from source {source_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import artifacts: {str(e)}",
        ) from e


# =============================================================================
# API-004a: Re-import Endpoint
# =============================================================================


@router.post(
    "/{source_id}/entries/{entry_id}/reimport",
    response_model=ReimportResponse,
    summary="Force re-import artifact",
    operation_id="reimport_catalog_entry",
    description="""
    Force re-import an artifact from upstream, resetting its catalog entry status.

    This endpoint handles several scenarios:
    - Artifacts with status="imported" that need to be refreshed from upstream
    - Artifacts that were deleted but catalog entry still shows "imported"
    - Broken or missing artifacts in the collection

    **Workflow**:
    1. Validates the catalog entry exists and belongs to this source
    2. If `keep_deployments=True` and artifact exists in collection:
       - Saves deployment records
       - Deletes the existing artifact
       - Re-imports from upstream
       - Restores deployment records
    3. If `keep_deployments=False` or artifact is missing:
       - Resets catalog entry status to "new"
       - Performs a fresh import from upstream

    **Request Body**:
    - `keep_deployments` (bool, optional): Whether to preserve deployment records (default: false)

    **Response**: Result with success flag, new artifact ID, and restoration count

    **Example**:
    ```bash
    curl -X POST "http://localhost:8080/api/v1/marketplace/sources/src-abc123/entries/cat-def456/reimport" \\
         -H "Content-Type: application/json" \\
         -d '{"keep_deployments": true}'
    ```

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
    responses={
        200: {"description": "Re-import completed successfully"},
        404: {"description": "Source or catalog entry not found"},
        500: {"description": "Re-import failed - check error message"},
    },
)
async def reimport_catalog_entry(
    source_id: str,
    entry_id: str,
    request: ReimportRequest,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    session: DbSessionDep,
) -> ReimportResponse:
    """Force re-import a catalog entry from upstream.

    Works for:
    - Artifacts with status="imported"
    - Artifacts that were deleted but catalog entry still shows "imported"
    - Broken/missing artifacts in collection

    Args:
        source_id: Unique source identifier
        entry_id: Unique catalog entry identifier
        request: Re-import request with keep_deployments flag
        artifact_mgr: Artifact manager dependency
        collection_mgr: Collection manager dependency
        session: Database session

    Returns:
        ReimportResponse with success status and details

    Raises:
        HTTPException 404: If source or entry not found
        HTTPException 500: If re-import operation fails
    """
    source_repo = MarketplaceSourceRepository()
    catalog_repo = MarketplaceCatalogRepository()
    transaction_handler = MarketplaceTransactionHandler()

    try:
        # Verify source exists
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source not found for reimport: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        # Fetch catalog entry
        entry = catalog_repo.get_by_id(entry_id)
        if not entry:
            logger.warning(f"Catalog entry not found for reimport: {entry_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Catalog entry with ID '{entry_id}' not found",
            )

        # Verify entry belongs to this source
        if entry.source_id != source_id:
            logger.warning(f"Entry {entry_id} does not belong to source {source_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Entry '{entry_id}' does not belong to source '{source_id}'",
            )

        # Check if artifact exists in collection
        artifact_type_str = entry.artifact_type
        artifact_name = entry.name
        artifact_id = f"{artifact_type_str}:{artifact_name}"

        # Try to find existing artifact
        existing_artifact = None
        saved_deployments: List[Dict[str, str]] = []
        collection_name = collection_mgr.get_active_collection_name()

        try:
            from skillmeat.core.artifact import ArtifactType as CoreArtifactType

            artifact_type = CoreArtifactType(artifact_type_str)
            collection = collection_mgr.load_collection(collection_name)
            existing_artifact = collection.find_artifact(artifact_name, artifact_type)
        except (ValueError, Exception) as e:
            logger.debug(
                f"Artifact not found in collection (may be deleted): {artifact_id}, error: {e}"
            )

        # If artifact exists and keep_deployments is True, save deployments
        if existing_artifact and request.keep_deployments:
            # TODO: Implement deployment record saving when deployment tracking is available
            # For now, log a message indicating this feature is planned
            logger.info(
                f"keep_deployments=True but deployment tracking not yet implemented "
                f"for artifact {artifact_id}"
            )
            # saved_deployments = artifact_mgr.get_deployments(artifact_name, artifact_type)

        # Delete existing artifact if present
        if existing_artifact:
            try:
                artifact_mgr.remove(
                    artifact_name,
                    CoreArtifactType(artifact_type_str),
                    collection_name,
                )
                logger.info(f"Deleted existing artifact for reimport: {artifact_id}")
            except Exception as e:
                logger.warning(f"Failed to delete existing artifact: {e}")
                # Continue anyway - artifact might be partially deleted or corrupted

        # Reset catalog entry status to allow re-import
        reset_entry = catalog_repo.reset_import_status(entry_id, source_id)
        if not reset_entry:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset catalog entry status",
            )

        # Extract description and tags from catalog entry metadata
        entry_metadata = entry.get_metadata_dict() or {}
        description = entry_metadata.get("description")

        tags = []
        if entry.path_segments:
            try:
                segments_data = json.loads(entry.path_segments)
                extracted = segments_data.get("extracted", [])
                tags = [
                    seg["normalized"]
                    for seg in extracted
                    if seg.get("status") == "approved"
                ]
            except (json.JSONDecodeError, KeyError):
                tags = []

        # Perform the import
        entries_data = [
            {
                "id": entry.id,
                "artifact_type": entry.artifact_type,
                "name": entry.name,
                "upstream_url": entry.upstream_url,
                "path": entry.path,
                "description": description,
                "tags": tags,
            }
        ]

        coordinator = ImportCoordinator(
            collection_name=collection_name,
            collection_mgr=collection_mgr,
        )

        import_result = coordinator.import_entries(
            entries=entries_data,
            source_id=source_id,
            strategy=ConflictStrategy.OVERWRITE,  # Force overwrite for reimport
            source_ref=source.ref,
        )

        # Check import result
        if import_result.error_count > 0:
            error_msg = (
                import_result.entries[0].error_message
                if import_result.entries
                else "Unknown error"
            )
            logger.error(f"Re-import failed for {artifact_id}: {error_msg}")
            return ReimportResponse(
                success=False,
                artifact_id=None,
                message=f"Re-import failed: {error_msg}",
                deployments_restored=0,
            )

        # Update catalog entry status to imported
        with transaction_handler.import_transaction(source_id) as ctx:
            ctx.mark_imported([entry_id], import_result.import_id)

        # Add to default database collection
        try:
            ensure_default_collection(session)
            association = CollectionArtifact(
                collection_id=DEFAULT_COLLECTION_ID,
                artifact_id=artifact_id,
                added_at=datetime.utcnow(),
            )
            session.merge(association)
            session.commit()
        except Exception as e:
            logger.warning(f"Failed to add artifact to database collection: {e}")
            session.rollback()

        # Restore deployments if requested
        deployments_restored = 0
        if request.keep_deployments and saved_deployments:
            # TODO: Implement deployment restoration when deployment tracking is available
            pass

        logger.info(f"Successfully re-imported artifact: {artifact_id}")
        return ReimportResponse(
            success=True,
            artifact_id=artifact_id,
            message="Successfully re-imported artifact from upstream",
            deployments_restored=deployments_restored,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to re-import artifact from source {source_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to re-import artifact: {str(e)}",
        ) from e


# =============================================================================
# API-004b: Exclude Artifact Endpoint
# =============================================================================


@router.patch(
    "/{source_id}/artifacts/{entry_id}/exclude",
    response_model=CatalogEntryResponse,
    summary="Mark or restore catalog artifact",
    operation_id="exclude_or_restore_artifact",
    description="""
    Mark a catalog entry as excluded from the catalog or restore a previously excluded entry.

    Use this endpoint to mark artifacts that are false positives (not actually Claude artifacts),
    documentation-only files, or other entries that shouldn't appear in the default catalog view.
    Excluded artifacts are hidden unless explicitly requested with `include_excluded=True` when
    listing artifacts.

    This operation is idempotent - calling it multiple times with the same parameters will
    return success with the current state.

    **Request Body**:
    - `excluded` (bool, required): True to mark as excluded, False to restore
    - `reason` (string, optional): User-provided reason (max 500 chars)

    **Response**: Updated catalog entry with `excluded_at` and `excluded_reason` fields

    **Examples**:

    Mark as excluded with reason:
    ```bash
    curl -X PATCH "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts/cat-def456/exclude" \\
         -H "Content-Type: application/json" \\
         -d '{
           "excluded": true,
           "reason": "Not a valid skill - documentation only"
         }'
    ```

    Restore previously excluded:
    ```bash
    curl -X PATCH "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts/cat-def456/exclude" \\
         -H "Content-Type: application/json" \\
         -d '{"excluded": false}'
    ```

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
)
async def exclude_artifact(
    source_id: str,
    entry_id: str,
    request: ExcludeArtifactRequest,
    collection_mgr: CollectionManagerDep = None,
) -> CatalogEntryResponse:
    """Mark or restore a catalog entry as excluded.

    Marks artifacts that are false positives or not actual Claude artifacts as excluded.
    Excluded artifacts are filtered from default catalog listings but can be restored.
    This operation is idempotent - calling it on already excluded entries succeeds.

    Args:
        source_id: Unique source identifier
        entry_id: Unique catalog entry identifier
        request: Exclusion request with excluded flag and optional reason
        collection_mgr: Collection manager for in_collection lookup

    Returns:
        Updated catalog entry with exclusion metadata

    Raises:
        HTTPException 404: If source or entry not found
        HTTPException 400: If entry does not belong to source
        HTTPException 500: If database operation fails

    Example:
        >>> # Mark as excluded
        >>> request = ExcludeArtifactRequest(
        ...     excluded=True,
        ...     reason="Documentation file, not a skill"
        ... )
        >>> response = await exclude_artifact("src-123", "cat-456", request)
        >>> assert response.excluded_at is not None
        >>> assert response.status == "excluded"
    """
    source_repo = MarketplaceSourceRepository()
    catalog_repo = MarketplaceCatalogRepository()
    collection_keys = (
        get_collection_artifact_keys(collection_mgr) if collection_mgr else set()
    )

    try:
        # Verify source exists
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source not found: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        # Use catalog_repo's session for atomic update
        session = catalog_repo._get_session()
        try:
            # Fetch catalog entry within same session for update
            entry = (
                session.query(MarketplaceCatalogEntry).filter_by(id=entry_id).first()
            )
            if not entry:
                logger.warning(f"Catalog entry not found: {entry_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Catalog entry with ID '{entry_id}' not found",
                )

            # Verify entry belongs to this source
            if entry.source_id != source_id:
                logger.warning(
                    f"Entry {entry_id} does not belong to source {source_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Entry '{entry_id}' does not belong to source '{source_id}'",
                )

            # Apply exclusion or restoration
            if request.excluded:
                # Mark as excluded (idempotent - skip if already excluded)
                if entry.excluded_at is None:
                    entry.excluded_at = datetime.now(timezone.utc)
                entry.excluded_reason = request.reason
                entry.status = "excluded"
                logger.info(
                    f"Marked catalog entry as excluded: {entry_id} "
                    f"(reason: {request.reason or 'none provided'})"
                )
            else:
                # Restore from exclusion
                entry.excluded_at = None
                entry.excluded_reason = None
                # Restore to "new" status (or could check import_date to set "imported")
                entry.status = "new" if entry.import_date is None else "imported"
                logger.info(f"Restored catalog entry from exclusion: {entry_id}")

            # Commit changes
            session.commit()

            # Refresh to get updated timestamps
            session.refresh(entry)

            return entry_to_response(entry, collection_keys)

        except HTTPException:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to update exclusion status for entry {entry_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update exclusion status: {str(e)}",
        ) from e


@router.delete(
    "/{source_id}/artifacts/{entry_id}/exclude",
    response_model=CatalogEntryResponse,
    summary="Restore excluded catalog artifact",
    operation_id="restore_excluded_artifact",
    description="""
    Remove the exclusion status from a catalog entry, restoring it to the catalog.

    This is a convenience endpoint that performs the same operation as calling
    PATCH with `excluded=False`. It is idempotent - calling it on a non-excluded
    entry will return success with the current state.

    Restored entries will be visible in the default catalog view and can be
    imported to collections.

    **Examples**:

    Restore an excluded artifact:
    ```bash
    curl -X DELETE "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts/cat-def456/exclude"
    ```

    List artifacts including excluded (before restoring):
    ```bash
    curl -X GET "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts?include_excluded=true"
    ```

    After restore, the artifact will appear in both filtered and unfiltered listings.

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
)
async def restore_excluded_artifact(
    source_id: str,
    entry_id: str,
    collection_mgr: CollectionManagerDep = None,
) -> CatalogEntryResponse:
    """Restore an excluded catalog entry to the catalog.

    Removes exclusion status and makes the artifact visible in default catalog views.
    This is idempotent - restoring a non-excluded entry succeeds without changes.

    Args:
        source_id: Unique source identifier
        entry_id: Unique catalog entry identifier
        collection_mgr: Collection manager for in_collection lookup

    Returns:
        Updated catalog entry with exclusion removed (excluded_at=None, excluded_reason=None)

    Raises:
        HTTPException 404: If source or entry not found
        HTTPException 400: If entry does not belong to source
        HTTPException 500: If database operation fails

    Example:
        >>> # Restore previously excluded entry
        >>> response = await restore_excluded_artifact("src-123", "cat-456")
        >>> assert response.excluded_at is None
        >>> assert response.excluded_reason is None
        >>> assert response.status == "new"  # or "imported" if previously imported
    """
    source_repo = MarketplaceSourceRepository()
    catalog_repo = MarketplaceCatalogRepository()
    collection_keys = (
        get_collection_artifact_keys(collection_mgr) if collection_mgr else set()
    )

    try:
        # Verify source exists
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source not found: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        # Use catalog_repo's session for atomic update
        session = catalog_repo._get_session()
        try:
            # Fetch catalog entry within same session for update
            entry = (
                session.query(MarketplaceCatalogEntry).filter_by(id=entry_id).first()
            )
            if not entry:
                logger.warning(f"Catalog entry not found: {entry_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Catalog entry with ID '{entry_id}' not found",
                )

            # Verify entry belongs to this source
            if entry.source_id != source_id:
                logger.warning(
                    f"Entry {entry_id} does not belong to source {source_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Entry '{entry_id}' does not belong to source '{source_id}'",
                )

            # Restore from exclusion (idempotent - no-op if not excluded)
            if entry.excluded_at is not None:
                entry.excluded_at = None
                entry.excluded_reason = None
                # Restore to "new" status if never imported, otherwise "imported"
                entry.status = "new" if entry.import_date is None else "imported"
                logger.info(f"Restored catalog entry from exclusion: {entry_id}")
            else:
                logger.debug(f"Entry {entry_id} was not excluded, no-op")

            # Commit changes
            session.commit()

            # Refresh to get updated timestamps
            session.refresh(entry)

            return entry_to_response(entry, collection_keys)

        except HTTPException:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to restore excluded entry {entry_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore excluded entry: {str(e)}",
        ) from e


# =============================================================================
# API-004c: Path Tags Endpoint
# =============================================================================


@router.get(
    "/{source_id}/catalog/{entry_id}/path-tags",
    response_model=PathSegmentsResponse,
    summary="Get path-based tag suggestions for catalog entry",
    description="""
    Retrieve extracted path segments and their approval status for a catalog entry.

    Returns all extracted segments with their current approval status (pending, approved,
    rejected, excluded). Only includes entries that have been scanned with path extraction
    enabled.

    The path_segments field contains a JSON object with:
    - raw_path: Original artifact path
    - extracted: Array of {segment, normalized, status, reason} objects
    - extracted_at: ISO timestamp of extraction

    Path Parameters:
    - source_id: Marketplace source identifier
    - entry_id: Catalog entry identifier

    Example: GET /marketplace/sources/src-123/catalog/cat-456/path-tags
    """,
    responses={
        404: {"description": "Source or entry not found"},
        400: {"description": "Entry has no path_segments (not extracted yet)"},
    },
)
async def get_path_tags(
    source_id: str,
    entry_id: str,
) -> PathSegmentsResponse:
    """Get extracted path segments for a catalog entry.

    Returns all extracted segments with their current approval status.
    Only includes entries that have been scanned with path extraction enabled.

    Args:
        source_id: Unique source identifier
        entry_id: Unique catalog entry identifier

    Returns:
        PathSegmentsResponse with raw_path and extracted segments

    Raises:
        HTTPException 404: If source or entry not found
        HTTPException 400: If entry has no path_segments (not extracted yet)
        HTTPException 500: If path_segments JSON is malformed

    Example:
        >>> response = await get_path_tags("src-123", "cat-456")
        >>> assert response.raw_path == "skills/ui-ux/canvas-design"
        >>> assert len(response.extracted) == 2
        >>> assert response.extracted[0].segment == "ui-ux"
    """
    source_repo = MarketplaceSourceRepository()
    catalog_repo = MarketplaceCatalogRepository()

    try:
        # Verify source exists
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source not found: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        # Use catalog_repo's session for query
        session = catalog_repo._get_session()
        try:
            # Find the catalog entry
            entry = (
                session.query(MarketplaceCatalogEntry)
                .filter(
                    MarketplaceCatalogEntry.source_id == source_id,
                    MarketplaceCatalogEntry.id == entry_id,
                )
                .first()
            )

            if not entry:
                logger.warning(
                    f"Catalog entry '{entry_id}' not found in source '{source_id}'"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Catalog entry '{entry_id}' not found in source '{source_id}'",
                )

            # Check if path_segments exists
            if not entry.path_segments:
                logger.info(
                    f"Entry '{entry_id}' has no path_segments (not extracted yet)"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Entry '{entry_id}' has no path_segments (not extracted yet)",
                )

            # Parse path_segments JSON
            try:
                data = json.loads(entry.path_segments)

                # Build ExtractedSegmentResponse list
                extracted_segments = [
                    ExtractedSegmentResponse(
                        segment=seg["segment"],
                        normalized=seg["normalized"],
                        status=seg["status"],
                        reason=seg.get("reason"),
                    )
                    for seg in data["extracted"]
                ]

                return PathSegmentsResponse(
                    entry_id=entry_id,
                    raw_path=data["raw_path"],
                    extracted=extracted_segments,
                    extracted_at=datetime.fromisoformat(data["extracted_at"]),
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Malformed path_segments for entry {entry_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal error parsing path_segments",
                ) from e

        except HTTPException:
            raise
        except Exception as e:
            raise e
        finally:
            session.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get path tags for entry {entry_id} in source {source_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve path tags: {str(e)}",
        ) from e


@router.patch(
    "/{source_id}/catalog/{entry_id}/path-tags",
    response_model=UpdateSegmentStatusResponse,
    summary="Update approval status of a path segment",
    description="""
    Approve or reject a suggested path-based tag.

    Updates the status field in path_segments JSON for a single segment.
    Only "pending" status segments can be changed. Cannot modify "excluded"
    segments (filtered by extraction rules).

    Status values:
    - "pending": Segment awaiting approval/rejection (default)
    - "approved": Segment will be applied as tag during import
    - "rejected": Segment will not be applied as tag
    - "excluded": Segment filtered by rules (cannot be changed)

    Path Parameters:
    - source_id: Marketplace source identifier
    - entry_id: Catalog entry identifier

    Request Body:
    - segment: Original segment value to update (e.g., "ui-ux")
    - status: New status ("approved" or "rejected")

    Example: PATCH /marketplace/sources/src-123/catalog/cat-456/path-tags
    """,
    responses={
        404: {"description": "Source, entry, or segment not found"},
        409: {"description": "Segment already approved/rejected or is excluded"},
        500: {"description": "Malformed path_segments JSON"},
    },
)
async def update_path_tag_status(
    source_id: str,
    entry_id: str,
    request: UpdateSegmentStatusRequest,
    collection_mgr: CollectionManagerDep,
) -> UpdateSegmentStatusResponse:
    """Update approval status of a single path segment.

    Modifies the status field in path_segments JSON for the specified segment.
    Only "pending" segments can be updated. Attempting to change an already
    approved/rejected segment or an excluded segment will raise a 409 Conflict.

    Args:
        source_id: Unique source identifier
        entry_id: Unique catalog entry identifier
        request: Request body with segment name and new status

    Returns:
        UpdateSegmentStatusResponse with updated segments and timestamp

    Raises:
        HTTPException 404: If source, entry, or segment not found
        HTTPException 409: If segment already has status or is excluded
        HTTPException 500: If path_segments JSON is malformed

    Example:
        >>> request = UpdateSegmentStatusRequest(segment="ui-ux", status="approved")
        >>> response = await update_path_tag_status("src-123", "cat-456", request)
        >>> assert response.extracted[0].status == "approved"
    """
    source_repo = MarketplaceSourceRepository()
    catalog_repo = MarketplaceCatalogRepository()

    try:
        # Verify source exists
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source not found: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        # Use catalog_repo's session for atomic update
        session = catalog_repo._get_session()
        try:
            # Find the catalog entry
            entry = (
                session.query(MarketplaceCatalogEntry)
                .filter(
                    MarketplaceCatalogEntry.source_id == source_id,
                    MarketplaceCatalogEntry.id == entry_id,
                )
                .first()
            )

            if not entry:
                logger.warning(
                    f"Catalog entry '{entry_id}' not found in source '{source_id}'"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Catalog entry '{entry_id}' not found in source '{source_id}'",
                )

            # Check if path_segments exists
            if not entry.path_segments:
                logger.info(
                    f"Entry '{entry_id}' has no path_segments (not extracted yet)"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Entry '{entry_id}' has no path_segments (not extracted yet)",
                )

            # Parse path_segments JSON
            try:
                segments_data = json.loads(entry.path_segments)
            except json.JSONDecodeError:
                logger.error(f"Malformed path_segments for entry {entry_id}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal error: malformed path_segments JSON",
                )

            # Find and update the segment
            segment_found = False
            request_lower = request.segment.lower()
            for seg in segments_data["extracted"]:
                if (
                    seg["segment"].lower() == request_lower
                    or seg.get("normalized", "").lower() == request_lower
                ):
                    segment_found = True

                    # Cannot change "excluded" segments
                    if seg["status"] == "excluded":
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"Cannot change status of excluded segment '{request.segment}'",
                        )

                    # Cannot double-approve/reject
                    if seg["status"] in ["approved", "rejected"]:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"Segment '{request.segment}' already has status '{seg['status']}'",
                        )

                    # Update status
                    seg["status"] = request.status
                    logger.info(
                        f"Updated segment '{request.segment}' (matched '{seg['segment']}') "
                        f"to status '{request.status}' in entry '{entry_id}'"
                    )
                    break

            if not segment_found:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Segment '{request.segment}' not found in entry '{entry_id}'",
                )

            # Save back to DB
            entry.path_segments = json.dumps(segments_data)
            session.commit()

            # Sync approved tag to collection artifact if already imported
            if request.status == "approved":
                try:
                    # Check if artifact is in collection
                    in_collection, artifact_id, _ = (
                        collection_mgr.artifact_in_collection(
                            name=entry.name,
                            artifact_type=entry.artifact_type,
                        )
                    )

                    if in_collection:
                        # Get the normalized tag value to add
                        normalized_tag = None
                        for seg in segments_data["extracted"]:
                            if (
                                seg["segment"].lower() == request_lower
                                or seg.get("normalized", "").lower() == request_lower
                            ):
                                normalized_tag = seg.get("normalized") or seg["segment"]
                                break

                        if normalized_tag:
                            # Load collection, find artifact, add tag
                            collection = collection_mgr.load_collection()
                            for artifact in collection.artifacts:
                                if (
                                    f"{artifact.type.value}:{artifact.name}"
                                    == artifact_id
                                ):
                                    # Add tag if not already present
                                    if normalized_tag not in artifact.tags:
                                        artifact.tags.append(normalized_tag)
                                        collection_mgr.save_collection(collection)
                                        logger.info(
                                            f"Synced tag '{normalized_tag}' to collection "
                                            f"artifact '{artifact_id}'"
                                        )
                                    break
                except Exception as e:
                    # Log but don't fail - source tag update already succeeded
                    logger.warning(f"Failed to sync tag to collection artifact: {e}")

            # Build response
            extracted_segments = [
                ExtractedSegmentResponse(
                    segment=seg["segment"],
                    normalized=seg["normalized"],
                    status=seg["status"],
                    reason=seg.get("reason"),
                )
                for seg in segments_data["extracted"]
            ]

            return UpdateSegmentStatusResponse(
                entry_id=entry_id,
                raw_path=segments_data["raw_path"],
                extracted=extracted_segments,
                updated_at=datetime.utcnow(),
            )

        except HTTPException:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to update path tag status for entry {entry_id} in source {source_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update path tag status: {str(e)}",
        ) from e


# =============================================================================
# API-005: File Tree Endpoint
# =============================================================================


@router.get(
    "/{source_id}/artifacts/{artifact_path:path}/files",
    response_model=FileTreeResponse,
    summary="Get file tree for artifact",
    description="""
    Retrieve the file tree for a marketplace artifact.

    Returns a list of files and directories within the artifact, suitable
    for displaying in a file browser UI. Each entry includes the path,
    type (blob/tree), size (for files), and SHA.

    Results are cached for 1 hour to reduce GitHub API calls.

    Path Parameters:
    - source_id: Marketplace source identifier
    - artifact_path: Path to the artifact within the repository (e.g., "skills/canvas")

    Example: GET /marketplace/sources/src-123/artifacts/skills/canvas/files
    """,
)
async def get_artifact_file_tree(
    source_id: str,
    artifact_path: str,
) -> FileTreeResponse:
    """Get file tree for a marketplace artifact.

    Args:
        source_id: Unique source identifier
        artifact_path: Path to the artifact within the repository

    Returns:
        File tree with entries for all files and directories

    Raises:
        HTTPException 400: If path validation fails (traversal, null bytes, etc.)
        HTTPException 404: If source or artifact path not found
        HTTPException 500: If GitHub API call fails
    """
    # Security: Validate inputs to prevent path traversal attacks
    validate_source_id(source_id)
    artifact_path = validate_file_path(artifact_path)

    # Normalize "." (repository root) to empty string
    # When artifacts are at repository root, their path is stored as "." in the database
    # but empty string is the canonical representation for API operations
    if artifact_path == ".":
        artifact_path = ""

    source_repo = MarketplaceSourceRepository()

    try:
        # Get marketplace source
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source not found: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        # Get cache and build cache key
        cache = get_github_file_cache()

        # Use source ref as SHA for cache key (or "HEAD" if not specified)
        cache_sha = source.ref or "HEAD"
        cache_key = build_tree_key(source_id, artifact_path, cache_sha)

        # Check cache first
        cached_tree = cache.get(cache_key)
        if cached_tree is not None:
            logger.debug(f"Cache hit for file tree: {artifact_path}")
            # Strip artifact path prefix from file paths
            path_prefix = f"{artifact_path}/" if artifact_path else ""
            prefix_len = len(path_prefix)
            entries = [
                FileTreeEntry(
                    path=(
                        entry["path"][prefix_len:]
                        if entry["path"].startswith(path_prefix)
                        else entry["path"]
                    ),
                    type="file" if entry["type"] == "blob" else entry["type"],
                    size=entry.get("size"),
                    sha=entry["sha"],
                )
                for entry in cached_tree
                # Exclude the artifact directory itself
                if entry["path"] != artifact_path
            ]

            # Handle single-file artifacts (Commands, Agents, Hooks)
            # If no child entries but path looks like a single file, return the file itself
            if not entries and artifact_path.endswith(".md"):
                from pathlib import PurePosixPath

                for entry in cached_tree:
                    if entry["path"] == artifact_path and entry["type"] == "blob":
                        filename = PurePosixPath(artifact_path).name
                        entries = [
                            FileTreeEntry(
                                path=filename,
                                type="file",
                                size=entry.get("size"),
                                sha=entry["sha"],
                            )
                        ]
                        break

            return FileTreeResponse(
                entries=entries,
                artifact_path=artifact_path,
                source_id=source_id,
            )

        # Cache miss - fetch from GitHub
        logger.debug(f"Cache miss, fetching file tree: {artifact_path}")
        scanner = GitHubScanner()

        tree_entries = scanner.get_file_tree(
            owner=source.owner,
            repo=source.repo_name,
            path=artifact_path,
            sha=None,  # Will fetch default branch SHA
        )

        if not tree_entries:
            logger.warning(
                f"Artifact path not found: {artifact_path} in source {source_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact path '{artifact_path}' not found in source",
            )

        # Cache the result
        cache.set(cache_key, tree_entries, ttl_seconds=DEFAULT_TREE_TTL)
        logger.debug(f"Cached file tree: {artifact_path} ({len(tree_entries)} entries)")

        # Strip artifact path prefix from file paths
        path_prefix = f"{artifact_path}/" if artifact_path else ""
        prefix_len = len(path_prefix)

        # Build entries list, excluding the artifact directory/file itself
        entries = [
            FileTreeEntry(
                path=(
                    entry["path"][prefix_len:]
                    if entry["path"].startswith(path_prefix)
                    else entry["path"]
                ),
                type="file" if entry["type"] == "blob" else entry["type"],
                size=entry.get("size"),
                sha=entry["sha"],
            )
            for entry in tree_entries
            # Exclude the artifact directory itself (exact match with no remaining path)
            if entry["path"] != artifact_path
        ]

        # Handle single-file artifacts (Commands, Agents, Hooks)
        # If no child entries but path looks like a single file, return the file itself
        if not entries and artifact_path.endswith(".md"):
            # Find the file entry in tree_entries (should be exact match)
            for entry in tree_entries:
                if entry["path"] == artifact_path and entry["type"] == "blob":
                    # Extract just the filename for the entry path
                    from pathlib import PurePosixPath

                    filename = PurePosixPath(artifact_path).name
                    entries = [
                        FileTreeEntry(
                            path=filename,
                            type="file",
                            size=entry.get("size"),
                            sha=entry["sha"],
                        )
                    ]
                    logger.debug(
                        f"Single-file artifact detected: {artifact_path} -> {filename}"
                    )
                    break

        return FileTreeResponse(
            entries=entries,
            artifact_path=artifact_path,
            source_id=source_id,
        )

    except HTTPException:
        raise
    except RateLimitError as e:
        retry_after = parse_rate_limit_retry_after(e)
        logger.warning(
            f"GitHub rate limit exceeded for file tree {artifact_path} "
            f"from source {source_id}: {e}"
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": f"GitHub rate limit exceeded. Please retry after {retry_after} seconds."
            },
            headers={"Retry-After": str(retry_after)},
        )
    except Exception as e:
        logger.error(
            f"Failed to get file tree for artifact {artifact_path} "
            f"from source {source_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve file tree: {str(e)}",
        ) from e


# =============================================================================
# API-006: File Content Endpoint
# =============================================================================


@router.get(
    "/{source_id}/artifacts/{artifact_path:path}/files/{file_path:path}",
    response_model=FileContentResponse,
    summary="Get file content from artifact",
    description="""
    Retrieve the content of a specific file within a marketplace artifact.

    Returns the file content with metadata including encoding, size, and SHA.
    For binary files, content is base64-encoded with is_binary=True.

    Results are cached for 2 hours to reduce GitHub API calls.

    Path Parameters:
    - source_id: Marketplace source identifier
    - artifact_path: Path to the artifact within the repository (e.g., "skills/canvas")
    - file_path: Path to the file within the artifact (e.g., "SKILL.md" or "src/index.ts")

    Example: GET /marketplace/sources/src-123/artifacts/skills/canvas/files/SKILL.md
    """,
)
async def get_artifact_file_content(
    source_id: str,
    artifact_path: str,
    file_path: str,
) -> FileContentResponse:
    """Get content of a file within a marketplace artifact.

    Args:
        source_id: Unique source identifier
        artifact_path: Path to the artifact within the repository
        file_path: Path to the file within the artifact

    Returns:
        File content with metadata

    Raises:
        HTTPException 400: If path validation fails (traversal, null bytes, etc.)
        HTTPException 404: If source or file not found
        HTTPException 500: If GitHub API call fails
    """
    # Security: Validate all path inputs to prevent path traversal attacks
    validate_source_id(source_id)
    artifact_path = validate_file_path(artifact_path)
    file_path = validate_file_path(file_path)

    # Normalize "." (repository root) to empty string
    # When artifacts are at repository root, their path is stored as "." in the database
    # but empty string is the canonical representation for API operations
    if artifact_path == ".":
        artifact_path = ""

    source_repo = MarketplaceSourceRepository()

    try:
        # Get marketplace source
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source not found: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        # Build full file path within repository
        # Check if this is a single-file artifact (artifact_path ends with file_path)
        # For single-file artifacts like Commands (.claude/commands/use-mcp.md),
        # artifact_path IS the file, so we shouldn't concatenate
        if artifact_path.endswith(f"/{file_path}") or artifact_path == file_path:
            # Single-file artifact: artifact_path IS the file
            full_file_path = artifact_path
        else:
            # Directory-based artifact: concatenate paths
            full_file_path = f"{artifact_path}/{file_path}"

        # Get cache and build cache key
        cache = get_github_file_cache()

        # Use source ref as SHA for cache key (or "HEAD" if not specified)
        cache_sha = source.ref or "HEAD"
        cache_key = build_content_key(source_id, artifact_path, file_path, cache_sha)

        # Check cache first
        cached_content = cache.get(cache_key)
        if cached_content is not None:
            logger.debug(f"Cache hit for file content: {full_file_path}")
            return FileContentResponse(
                content=cached_content["content"],
                encoding=cached_content["encoding"],
                size=cached_content["size"],
                sha=cached_content["sha"],
                name=cached_content["name"],
                path=cached_content["path"],
                is_binary=cached_content["is_binary"],
                artifact_path=artifact_path,
                source_id=source_id,
            )

        # Cache miss - fetch from GitHub
        logger.debug(f"Cache miss, fetching file content: {full_file_path}")
        scanner = GitHubScanner()

        file_content = scanner.get_file_content(
            owner=source.owner,
            repo=source.repo_name,
            path=full_file_path,
            ref=source.ref,
        )

        if file_content is None:
            logger.warning(f"File not found: {full_file_path} in source {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File '{file_path}' not found in artifact '{artifact_path}'",
            )

        # Cache the result
        cache.set(cache_key, file_content, ttl_seconds=DEFAULT_CONTENT_TTL)
        logger.debug(f"Cached file content: {full_file_path}")

        return FileContentResponse(
            content=file_content["content"],
            encoding=file_content["encoding"],
            size=file_content["size"],
            sha=file_content["sha"],
            name=file_content["name"],
            path=file_content["path"],
            is_binary=file_content["is_binary"],
            artifact_path=artifact_path,
            source_id=source_id,
        )

    except HTTPException:
        raise
    except RateLimitError as e:
        retry_after = parse_rate_limit_retry_after(e)
        logger.warning(
            f"GitHub rate limit exceeded for file content {file_path} in {artifact_path} "
            f"from source {source_id}: {e}"
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": f"GitHub rate limit exceeded. Please retry after {retry_after} seconds."
            },
            headers={"Retry-After": str(retry_after)},
        )
    except Exception as e:
        logger.error(
            f"Failed to get file content for {file_path} in {artifact_path} "
            f"from source {source_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve file content: {str(e)}",
        ) from e


# =============================================================================
# Auto-Tags Endpoints (GitHub Topics)
# =============================================================================


@router.get(
    "/{source_id}/auto-tags",
    response_model=AutoTagsResponse,
    summary="Get auto-tag suggestions from GitHub topics",
    description="""
    Retrieve extracted GitHub repository topics and their approval status.

    Topics are extracted from the repository metadata and stored as auto-tags
    that can be approved or rejected. Approved auto-tags are added to the
    source's tags list.

    This endpoint returns all auto-tags with their current status (pending,
    approved, or rejected) and indicates whether any tags are still pending.
    """,
)
async def get_source_auto_tags(
    source_id: str,
) -> AutoTagsResponse:
    """Get auto-tag suggestions for a marketplace source.

    Args:
        source_id: Unique source identifier

    Returns:
        AutoTagsResponse with all auto-tags and their status

    Raises:
        HTTPException 404: If source not found
    """
    source_repo = MarketplaceSourceRepository()

    try:
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source not found for auto-tags: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        segments: List[AutoTagSegment] = []
        has_pending = False

        if source.auto_tags:
            try:
                auto_tags_data = json.loads(source.auto_tags)
                extracted = auto_tags_data.get("extracted", [])
                for seg in extracted:
                    segments.append(
                        AutoTagSegment(
                            value=seg["value"],
                            normalized=seg["normalized"],
                            status=seg["status"],
                            source=seg.get("source", "github_topic"),
                        )
                    )
                    if seg.get("status") == "pending":
                        has_pending = True
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse auto_tags for source {source_id}")

        return AutoTagsResponse(
            source_id=source_id,
            segments=segments,
            has_pending=has_pending,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get auto-tags for source {source_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve auto-tags: {str(e)}",
        ) from e


@router.patch(
    "/{source_id}/auto-tags",
    response_model=UpdateAutoTagResponse,
    summary="Update approval status of an auto-tag",
    description="""
    Approve or reject a suggested auto-tag from GitHub topics.

    When a tag is approved, it is automatically added to the source's
    regular tags list. When rejected, it is marked as rejected and
    will not be suggested again.

    Note: Auto-tags are source-level only. They do NOT propagate to
    imported artifacts. Use path_tags for artifact-level tagging.
    """,
)
async def update_source_auto_tag(
    source_id: str,
    request: UpdateAutoTagRequest,
) -> UpdateAutoTagResponse:
    """Update approval status of an auto-tag.

    Args:
        source_id: Unique source identifier
        request: Request body with tag value and new status

    Returns:
        UpdateAutoTagResponse with updated tag and any tags added

    Raises:
        HTTPException 404: If source or auto-tag not found
        HTTPException 500: If update fails
    """
    source_repo = MarketplaceSourceRepository()

    try:
        source = source_repo.get_by_id(source_id)
        if not source:
            logger.warning(f"Source not found for auto-tag update: {source_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{source_id}' not found",
            )

        if not source.auto_tags:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No auto-tags available for this source",
            )

        try:
            auto_tags_data = json.loads(source.auto_tags)
            extracted = auto_tags_data.get("extracted", [])
        except json.JSONDecodeError:
            logger.error(f"Malformed auto_tags JSON for source {source_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to parse auto-tags data",
            )

        # Find and update the tag
        updated_tag = None
        request_lower = request.value.lower()
        for seg in extracted:
            if (
                seg["value"].lower() == request_lower
                or seg["normalized"].lower() == request_lower
            ):
                seg["status"] = request.status
                updated_tag = AutoTagSegment(
                    value=seg["value"],
                    normalized=seg["normalized"],
                    status=seg["status"],
                    source=seg.get("source", "github_topic"),
                )
                break

        if not updated_tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Auto-tag '{request.value}' not found",
            )

        # Save updated auto_tags
        source.auto_tags = json.dumps(auto_tags_data)

        # If approved, add to source tags
        tags_added: List[str] = []
        if request.status == "approved":
            try:
                normalized = updated_tag.normalized.lower()
                current_tags = source.get_tags_list() or []
                if normalized not in [t.lower() for t in current_tags]:
                    current_tags.append(normalized)
                    source.set_tags_list(current_tags)
                    tags_added.append(normalized)
                    logger.info(
                        f"Added approved auto-tag '{normalized}' to source {source_id}"
                    )
            except Exception as e:
                logger.warning(f"Failed to add approved tag to source {source_id}: {e}")

        # Commit changes
        session = source_repo._get_session()
        session.commit()

        logger.info(
            f"Updated auto-tag '{request.value}' to status '{request.status}' "
            f"for source {source_id}"
        )

        return UpdateAutoTagResponse(
            source_id=source_id,
            updated_tag=updated_tag,
            tags_added=tags_added,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to update auto-tag for source {source_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update auto-tag: {str(e)}",
        ) from e
