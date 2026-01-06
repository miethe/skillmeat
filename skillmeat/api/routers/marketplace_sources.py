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
    POST /marketplace/sources/{id}/import - Import artifacts to collection
    PATCH /marketplace/sources/{id}/artifacts/{entry_id}/exclude - Mark artifact as excluded
    DELETE /marketplace/sources/{id}/artifacts/{entry_id}/exclude - Restore excluded artifact
    GET /marketplace/sources/{id}/catalog/{entry_id}/path-tags - Get path-based tag suggestions
    PATCH /marketplace/sources/{id}/catalog/{entry_id}/path-tags - Update path segment approval status
    GET /marketplace/sources/{id}/artifacts/{path}/files - Get file tree
    GET /marketplace/sources/{id}/artifacts/{path}/files/{file_path} - Get file content
"""

import json
import logging
import re
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from skillmeat.api.schemas.common import PageInfo
from skillmeat.api.schemas.marketplace import (
    CatalogEntryResponse,
    CatalogListResponse,
    CreateSourceRequest,
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
    ScanRequest,
    ScanResultDTO,
    SourceListResponse,
    SourceResponse,
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
    NotFoundError,
)
from skillmeat.core.marketplace.github_scanner import (
    GitHubScanner,
    RateLimitError,
    scan_github_source,
)
from skillmeat.core.marketplace.import_coordinator import (
    ConflictStrategy,
    ImportCoordinator,
)
from skillmeat.core.path_tags import PathSegmentExtractor, PathTagConfig

logger = logging.getLogger(__name__)

# Confidence threshold for hiding low-quality entries
CONFIDENCE_THRESHOLD = 30

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
        tree = scanner._fetch_tree(owner, repo, ref)

        # Extract all directory paths from tree
        # Tree items have "type": "tree" for directories, "type": "blob" for files
        dir_paths = {
            item["path"]
            for item in tree
            if item.get("type") == "tree"
        }

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
    )


def entry_to_response(entry: MarketplaceCatalogEntry) -> CatalogEntryResponse:
    """Convert MarketplaceCatalogEntry ORM model to API response.

    Args:
        entry: MarketplaceCatalogEntry ORM instance

    Returns:
        CatalogEntryResponse DTO for API
    """
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

    try:
        scan_result = scanner.scan_repository(
            owner=source.owner,
            repo=source.repo_name,
            ref=source.ref,
            root_hint=source.root_hint,
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

        # Update source and catalog atomically
        with transaction_handler.scan_update_transaction(source_id) as ctx:
            # Update source status
            ctx.update_source_status(
                status="success",
                artifact_count=scan_result.artifacts_found,
                error_message=None,
            )

            # Convert detected artifacts to catalog entries
            new_entries = []
            for artifact in scan_result.artifacts:
                # Extract path segments if enabled
                path_segments_json = None
                if extractor:
                    try:
                        segments = extractor.extract(artifact.path)
                        path_segments_json = json.dumps({
                            "raw_path": artifact.path,
                            "extracted": [asdict(s) for s in segments],
                            "extracted_at": datetime.utcnow().isoformat()
                        })
                    except Exception as e:
                        logger.error(
                            f"Failed to extract path segments for {artifact.path}: {e}"
                        )
                        # Continue without path_segments; extraction is non-blocking

                entry = MarketplaceCatalogEntry(
                    id=str(uuid.uuid4()),
                    source_id=source_id,
                    artifact_type=artifact.artifact_type,
                    name=artifact.name,
                    path=artifact.path,
                    upstream_url=artifact.upstream_url,
                    confidence_score=artifact.confidence_score,
                    detected_sha=artifact.detected_sha,
                    detected_at=datetime.utcnow(),
                    status="new",
                    path_segments=path_segments_json,
                )
                new_entries.append(entry)

            # Replace with new entries (full replacement for now)
            # TODO: Implement incremental diff updates in future
            ctx.replace_catalog_entries(new_entries)

        # Set source_id in result
        scan_result.source_id = source_id

        logger.info(
            f"Scan completed for {source.repo_url}: "
            f"{scan_result.artifacts_found} artifacts found"
        )
        return scan_result

    except Exception as scan_error:
        # Mark as error
        with transaction_handler.scan_update_transaction(source_id) as ctx:
            ctx.update_source_status(
                status="error",
                error_message=str(scan_error),
            )

        logger.error(
            f"Scan failed for {source.repo_url}: {scan_error}", exc_info=True
        )

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

    If the initial scan fails, the source is still created with scan_status="error".
    You can retry scanning using the /rescan endpoint.

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
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
    )

    # Store manual_map if provided
    if request.manual_map:
        source.set_manual_map_dict(request.manual_map)

    try:
        created = source_repo.create(source)
        logger.info(f"Created marketplace source: {created.id} ({created.repo_url})")

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
    List all GitHub repository sources with cursor-based pagination.

    Returns sources ordered by ID for stable pagination. Use the `cursor`
    parameter from the previous response to fetch the next page.

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
)
async def list_sources(
    limit: int = Query(50, ge=1, le=100, description="Maximum items per page"),
    cursor: Optional[str] = Query(None, description="Cursor for next page"),
) -> SourceListResponse:
    """List all marketplace sources with pagination.

    Args:
        limit: Maximum number of items per page (1-100)
        cursor: Cursor for pagination (from previous response)

    Returns:
        Paginated list of sources with page info

    Raises:
        HTTPException 500: If database operation fails
    """
    source_repo = MarketplaceSourceRepository()

    try:
        result = source_repo.list_paginated(limit=limit, cursor=cursor)

        # Convert ORM models to API responses
        items = [source_to_response(source) for source in result.items]

        # Build page info
        page_info = PageInfo(
            has_next_page=result.has_more,
            has_previous_page=cursor is not None,
            start_cursor=items[0].id if items else None,
            end_cursor=items[-1].id if items else None,
            total_count=None,  # Not computed for efficiency
        )

        logger.debug(
            f"Listed {len(items)} sources (cursor={cursor}, has_more={result.has_more})"
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

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
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

    **Manual Mapping**: Use `manual_map` to override automatic artifact type detection
    for specific directories. Provide a dictionary mapping directory paths to artifact types.

    Example PATCH request with manual_map:
    ```json
    {
        "manual_map": {
            "skills/python": "skill",
            "commands/dev": "command",
            "agents/qa": "agent"
        }
    }
    ```

    **Path Validation**: All directory paths in `manual_map` are validated against the
    repository tree. If a path doesn't exist, the request will fail with 422 status.

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
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

        # Save updates
        updated = source_repo.update(source)
        logger.info(f"Updated marketplace source: {source_id}")
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

    The scan will:
    1. Fetch the repository tree from GitHub
    2. Apply heuristic detection to identify artifacts
    3. Update the catalog with discovered artifacts
    4. Update source metadata (artifact_count, last_sync_at, etc.)

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
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
# API-003: Artifacts Listing
# =============================================================================


@router.get(
    "/{source_id}/artifacts",
    response_model=CatalogListResponse,
    summary="List artifacts from source",
    operation_id="list_source_artifacts",
    description="""
    List all artifacts discovered from a specific source with optional filtering.

    By default, excluded artifacts are hidden from results. Use `include_excluded=true`
    to include them in listings (useful for reviewing or restoring excluded entries).

    Supports filtering by:
    - `artifact_type`: skill, command, agent, etc.
    - `status`: new, updated, removed, imported, excluded
    - `min_confidence`: Minimum confidence score (0-100)
    - `max_confidence`: Maximum confidence score (0-100)
    - `include_below_threshold`: Include artifacts below 30% confidence threshold (default: false)
    - `include_excluded`: Include excluded artifacts in results (default: false)

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
    status: Optional[str] = Query(
        None, description="Filter by status (new, updated, removed, imported, excluded)"
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
    limit: int = Query(50, ge=1, le=100, description="Maximum items per page (1-100)"),
    cursor: Optional[str] = Query(
        None, description="Cursor for pagination (from previous response)"
    ),
) -> CatalogListResponse:
    """List artifacts from a source with optional filters.

    Retrieves catalog entries from a source with support for filtering and pagination.
    By default, excluded artifacts are filtered out; set include_excluded=true to see them.

    Args:
        source_id: Unique source identifier
        artifact_type: Optional artifact type filter
        status: Optional status filter (new, updated, removed, imported, excluded)
        min_confidence: Filter entries with confidence >= this value (0-100)
        max_confidence: Filter entries with confidence <= this value (0-100)
        include_below_threshold: If True, include entries <30% that are normally hidden
        include_excluded: If True, include entries with status="excluded" (default: False)
        limit: Maximum items per page (1-100)
        cursor: Pagination cursor from previous response

    Returns:
        Paginated list of catalog entries with counts_by_status and counts_by_type statistics

    Raises:
        HTTPException 404: If source not found
        HTTPException 500: If database operation fails

    Example:
        >>> # List artifacts including excluded
        >>> response = await list_artifacts(
        ...     source_id="src-123",
        ...     include_excluded=True,
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
        if status:
            # User specified a status filter - use it directly
            effective_statuses = [status]

        # Determine if we need filtered query
        # When include_excluded=False and no status filter, we still need to filter
        needs_filtered_query = (
            artifact_type
            or status
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
            if not include_excluded and not status:
                entries = [e for e in entries if e.status != "excluded"]

            # Manual pagination for filtered results
            # Convert to list and apply cursor
            if cursor:
                # Find cursor position
                cursor_idx = next(
                    (i for i, e in enumerate(entries) if e.id > cursor),
                    len(entries),
                )
                entries = entries[cursor_idx:]

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
            items = result.items
            has_more = result.has_more

        # Convert to response DTOs
        response_items = [entry_to_response(entry) for entry in items]

        # Build page info
        page_info = PageInfo(
            has_next_page=has_more,
            has_previous_page=cursor is not None,
            start_cursor=response_items[0].id if response_items else None,
            end_cursor=response_items[-1].id if response_items else None,
            total_count=None,
        )

        # Get aggregated counts
        counts_by_status = catalog_repo.count_by_status(source_id=source_id)
        counts_by_type = catalog_repo.count_by_type(source_id=source_id)

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
) -> ImportResultDTO:
    """Import catalog entries to local collection.

    Args:
        source_id: Unique source identifier
        request: Import request with entry IDs and conflict strategy

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

            # Convert to dict for ImportCoordinator
            entries_data.append(
                {
                    "id": entry.id,
                    "artifact_type": entry.artifact_type,
                    "name": entry.name,
                    "upstream_url": entry.upstream_url,
                    "path": entry.path,
                }
            )

        # Perform import using ImportCoordinator
        coordinator = ImportCoordinator()
        strategy = ConflictStrategy(request.conflict_strategy)

        import_result = coordinator.import_entries(
            entries=entries_data,
            source_id=source_id,
            strategy=strategy,
        )

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
) -> CatalogEntryResponse:
    """Mark or restore a catalog entry as excluded.

    Marks artifacts that are false positives or not actual Claude artifacts as excluded.
    Excluded artifacts are filtered from default catalog listings but can be restored.
    This operation is idempotent - calling it on already excluded entries succeeds.

    Args:
        source_id: Unique source identifier
        entry_id: Unique catalog entry identifier
        request: Exclusion request with excluded flag and optional reason

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

            return entry_to_response(entry)

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
) -> CatalogEntryResponse:
    """Restore an excluded catalog entry to the catalog.

    Removes exclusion status and makes the artifact visible in default catalog views.
    This is idempotent - restoring a non-excluded entry succeeds without changes.

    Args:
        source_id: Unique source identifier
        entry_id: Unique catalog entry identifier

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

            return entry_to_response(entry)

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
            for seg in segments_data["extracted"]:
                if seg["segment"] == request.segment:
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
                        f"Updated segment '{request.segment}' to status '{request.status}' "
                        f"in entry '{entry_id}'"
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
