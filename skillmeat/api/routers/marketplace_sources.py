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
"""

import logging
import re
import uuid
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, status

from skillmeat.api.schemas.common import PageInfo
from skillmeat.api.schemas.marketplace import (
    CatalogEntryResponse,
    CatalogListResponse,
    CreateSourceRequest,
    ImportRequest,
    ImportResultDTO,
    ScanRequest,
    ScanResultDTO,
    SourceListResponse,
    SourceResponse,
    UpdateSourceRequest,
)
from skillmeat.cache.models import MarketplaceCatalogEntry, MarketplaceSource
from skillmeat.cache.repositories import (
    MarketplaceCatalogRepository,
    MarketplaceSourceRepository,
    MarketplaceTransactionHandler,
    NotFoundError,
)
from skillmeat.core.marketplace.github_scanner import GitHubScanner, scan_github_source
from skillmeat.core.marketplace.import_coordinator import (
    ConflictStrategy,
    ImportCoordinator,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/marketplace/sources",
    tags=["marketplace-sources"],
)


# =============================================================================
# Helper Functions
# =============================================================================


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
        status=entry.status,
        import_date=entry.import_date,
        import_id=entry.import_id,
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
    After creation, use the /rescan endpoint to trigger the initial scan.

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

    Allows updating ref (branch/tag/SHA), root_hint, trust_level, description, and notes.
    Changes take effect on the next scan.

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
)
async def update_source(
    source_id: str,
    request: UpdateSourceRequest,
) -> SourceResponse:
    """Update a marketplace source.

    Args:
        source_id: Unique source identifier
        request: Update request with fields to modify

    Returns:
        Updated source details

    Raises:
        HTTPException 400: If no update parameters provided
        HTTPException 404: If source not found
        HTTPException 500: If database operation fails
    """
    # Check if any update parameters provided
    if all(v is None for v in [request.ref, request.root_hint, request.trust_level, request.description, request.notes]):
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

        # Apply updates
        if request.ref is not None:
            source.ref = request.ref
        if request.root_hint is not None:
            source.root_hint = request.root_hint
        if request.trust_level is not None:
            source.trust_level = request.trust_level
        if request.description is not None:
            source.description = request.description
        if request.notes is not None:
            source.notes = request.notes

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

            # Return error result
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
    description="""
    List all artifacts discovered from a specific source with optional filtering.

    Supports filtering by:
    - artifact_type: skill, command, agent, etc.
    - status: new, updated, removed, imported
    - min_confidence: Minimum confidence score (0-100)

    Results are paginated using cursor-based pagination for efficiency.

    Authentication: TODO - Add authentication when multi-user support is implemented.
    """,
)
async def list_artifacts(
    source_id: str,
    artifact_type: Optional[str] = Query(
        None, description="Filter by artifact type (skill, command, etc.)"
    ),
    status: Optional[str] = Query(
        None, description="Filter by status (new, updated, removed, imported)"
    ),
    min_confidence: Optional[int] = Query(
        None, ge=0, le=100, description="Minimum confidence score"
    ),
    limit: int = Query(50, ge=1, le=100, description="Maximum items per page"),
    cursor: Optional[str] = Query(None, description="Cursor for next page"),
) -> CatalogListResponse:
    """List artifacts from a source with optional filters.

    Args:
        source_id: Unique source identifier
        artifact_type: Optional artifact type filter
        status: Optional status filter
        min_confidence: Optional minimum confidence score
        limit: Maximum items per page
        cursor: Pagination cursor

    Returns:
        Paginated list of catalog entries with statistics

    Raises:
        HTTPException 404: If source not found
        HTTPException 500: If database operation fails
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

        # Apply filters using get_source_catalog for combined filtering
        if artifact_type or status or min_confidence:
            # Get filtered entries
            entries = catalog_repo.get_source_catalog(
                source_id=source_id,
                artifact_types=[artifact_type] if artifact_type else None,
                statuses=[status] if status else None,
                min_confidence=min_confidence,
            )

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
            # Use efficient paginated query
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
