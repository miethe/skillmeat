/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AutoTagRefreshResponse } from '../models/AutoTagRefreshResponse';
import type { AutoTagsResponse } from '../models/AutoTagsResponse';
import type { BulkAutoTagRefreshRequest } from '../models/BulkAutoTagRefreshRequest';
import type { BulkAutoTagRefreshResponse } from '../models/BulkAutoTagRefreshResponse';
import type { BulkSyncRequest } from '../models/BulkSyncRequest';
import type { BulkSyncResponse } from '../models/BulkSyncResponse';
import type { CatalogEntryResponse } from '../models/CatalogEntryResponse';
import type { CatalogListResponse } from '../models/CatalogListResponse';
import type { CreateSourceRequest } from '../models/CreateSourceRequest';
import type { ExcludeArtifactRequest } from '../models/ExcludeArtifactRequest';
import type { FileTreeResponse } from '../models/FileTreeResponse';
import type { ImportRequest } from '../models/ImportRequest';
import type { ImportResultDTO } from '../models/ImportResultDTO';
import type { InferUrlRequest } from '../models/InferUrlRequest';
import type { InferUrlResponse } from '../models/InferUrlResponse';
import type { PathSegmentsResponse } from '../models/PathSegmentsResponse';
import type { ReimportRequest } from '../models/ReimportRequest';
import type { ReimportResponse } from '../models/ReimportResponse';
import type { ScanRequest } from '../models/ScanRequest';
import type { ScanResultDTO } from '../models/ScanResultDTO';
import type { skillmeat__api__schemas__marketplace__FileContentResponse } from '../models/skillmeat__api__schemas__marketplace__FileContentResponse';
import type { SourceListResponse } from '../models/SourceListResponse';
import type { SourceResponse } from '../models/SourceResponse';
import type { UpdateAutoTagRequest } from '../models/UpdateAutoTagRequest';
import type { UpdateAutoTagResponse } from '../models/UpdateAutoTagResponse';
import type { UpdateCatalogEntryNameRequest } from '../models/UpdateCatalogEntryNameRequest';
import type { UpdateSegmentStatusRequest } from '../models/UpdateSegmentStatusRequest';
import type { UpdateSegmentStatusResponse } from '../models/UpdateSegmentStatusResponse';
import type { UpdateSourceRequest } from '../models/UpdateSourceRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class MarketplaceSourcesService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * Infer Github Url
   * Infer GitHub repository structure from a full URL.
   *
   * Parses GitHub URLs to extract repository URL, branch/tag, and subdirectory path.
   * Supports various GitHub URL formats:
   * - https://github.com/owner/repo
   * - https://github.com/owner/repo/tree/branch
   * - https://github.com/owner/repo/tree/branch/path/to/dir
   * - https://github.com/owner/repo/blob/ref/path/to/file
   *
   * Args:
   * request: URL to parse
   *
   * Returns:
   * Inferred repository structure or error message
   *
   * Example:
   * Input: https://github.com/davila7/claude-code-templates/tree/main/cli-tool/components
   * Output: {
   * "success": true,
   * "repo_url": "https://github.com/davila7/claude-code-templates",
   * "ref": "main",
   * "root_hint": "cli-tool/components"
   * }
   * @returns InferUrlResponse Successful Response
   * @throws ApiError
   */
  public inferGithubUrlApiV1MarketplaceSourcesInferUrlPost({
    requestBody,
  }: {
    requestBody: InferUrlRequest;
  }): CancelablePromise<InferUrlResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/marketplace/sources/infer-url',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Create new GitHub source
   * Add a new GitHub repository as a marketplace source for artifact scanning.
   *
   * The repository URL must be a valid GitHub URL (https://github.com/owner/repo).
   * An initial scan is automatically triggered upon creation. The response includes
   * the scan status and artifact count.
   *
   * **Manual Directory Mappings** (Optional):
   * You can provide manual_map during creation to override automatic type detection.
   * This is useful when you know the repository structure in advance.
   *
   * **Example Request**:
   * ```json
   * {
   * "repo_url": "https://github.com/user/claude-templates",
   * "ref": "main",
   * "root_hint": "artifacts",
   * "trust_level": "trusted",
   * "manual_map": {
   * "skills/advanced": "skill",
   * "tools/cli": "command",
   * "agents/research": "agent"
   * },
   * "enable_frontmatter_detection": true
   * }
   * ```
   *
   * **Validation**: All manual_map directory paths are validated against the repository
   * tree during creation. Invalid paths will cause a 422 error.
   *
   * If the initial scan fails, the source is still created with scan_status="error".
   * You can retry scanning using the /rescan endpoint.
   *
   * Authentication: TODO - Add authentication when multi-user support is implemented.
   * @returns SourceResponse Source created and initial scan triggered
   * @throws ApiError
   */
  public createSourceApiV1MarketplaceSourcesPost({
    requestBody,
  }: {
    requestBody: CreateSourceRequest;
  }): CancelablePromise<SourceResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/marketplace/sources',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Bad request - invalid repository URL format`,
        409: `Conflict - repository URL already exists`,
        422: `Validation error - invalid manual_map directory paths`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * List all GitHub sources
   * List all GitHub repository sources with cursor-based pagination and optional filtering.
   *
   * Returns sources ordered by ID for stable pagination. Use the `cursor`
   * parameter from the previous response to fetch the next page.
   *
   * **Filters** (all use AND logic - source must match all provided filters):
   * - `artifact_type`: Filter sources containing artifacts of this type
   * - `tags`: Filter by tags (repeated param, e.g., `?tags=ui&tags=ux`)
   * - `trust_level`: Filter by trust level
   * - `search`: Search in repo name, description, and tags
   *
   * Authentication: TODO - Add authentication when multi-user support is implemented.
   * @returns SourceListResponse Successful Response
   * @throws ApiError
   */
  public listSourcesApiV1MarketplaceSourcesGet({
    limit = 50,
    cursor,
    artifactType,
    tags,
    trustLevel,
    search,
  }: {
    /**
     * Maximum items per page
     */
    limit?: number;
    /**
     * Cursor for next page
     */
    cursor?: string | null;
    /**
     * Filter by artifact type (skill, command, agent, hook, mcp-server)
     */
    artifactType?: string | null;
    /**
     * Filter by tags (AND logic - must match all)
     */
    tags?: Array<string> | null;
    /**
     * Filter by trust level (untrusted, basic, verified, official)
     */
    trustLevel?: string | null;
    /**
     * Search in repo name, description, tags
     */
    search?: string | null;
  }): CancelablePromise<SourceListResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/marketplace/sources',
      query: {
        limit: limit,
        cursor: cursor,
        artifact_type: artifactType,
        tags: tags,
        trust_level: trustLevel,
        search: search,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Get source by ID
   * Retrieve a specific GitHub repository source by its unique identifier.
   *
   * Returns all source configuration including manual_map if configured.
   *
   * **Response Example**:
   * ```json
   * {
   * "id": "src-abc123",
   * "repo_url": "https://github.com/user/templates",
   * "owner": "user",
   * "repo_name": "templates",
   * "ref": "main",
   * "root_hint": "claude-artifacts",
   * "trust_level": "trusted",
   * "visibility": "public",
   * "scan_status": "success",
   * "artifact_count": 42,
   * "manual_map": {
   * "advanced-skills/python-backend": "skill",
   * "cli-tools/scaffold": "command"
   * },
   * "enable_frontmatter_detection": true,
   * "last_sync_at": "2025-01-06T12:00:00Z",
   * "created_at": "2025-01-06T10:00:00Z",
   * "updated_at": "2025-01-06T11:30:00Z"
   * }
   * ```
   *
   * **manual_map field**: Dictionary mapping directory paths to artifact types.
   * Empty dictionary or null if no manual mappings configured.
   *
   * Authentication: TODO - Add authentication when multi-user support is implemented.
   * @returns SourceResponse Source details retrieved successfully
   * @throws ApiError
   */
  public getSourceApiV1MarketplaceSourcesSourceIdGet({
    sourceId,
  }: {
    sourceId: string;
  }): CancelablePromise<SourceResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/marketplace/sources/{source_id}',
      path: {
        source_id: sourceId,
      },
      errors: {
        404: `Source not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Update source
   * Update a GitHub repository source configuration.
   *
   * Allows updating ref (branch/tag/SHA), root_hint, manual_map, trust_level,
   * description, notes, and frontmatter detection settings.
   * Changes take effect on the next scan.
   *
   * **Manual Directory Mappings**:
   * Use `manual_map` to override automatic artifact type detection for specific directories.
   * This is useful when heuristic detection fails or when you want to force a directory
   * to be treated as a specific artifact type.
   *
   * **Supported artifact types**: `skill`, `command`, `agent`, `mcp_server`, `hook`
   *
   * **Example Request with manual_map**:
   * ```json
   * {
   * "manual_map": {
   * "advanced-skills/python-backend": "skill",
   * "cli-tools/scaffold": "command",
   * "research-agents/market-analysis": "agent"
   * }
   * }
   * ```
   *
   * **Validation**:
   * - All directory paths must exist in the repository (validated against GitHub tree)
   * - Artifact types must be one of: skill, command, agent, mcp_server, hook
   * - Invalid paths or types will return 422 Unprocessable Entity
   *
   * **Clear Mapping**:
   * To remove all manual mappings, send an empty dictionary:
   * ```json
   * {
   * "manual_map": {}
   * }
   * ```
   *
   * Authentication: TODO - Add authentication when multi-user support is implemented.
   * @returns SourceResponse Source updated successfully
   * @throws ApiError
   */
  public updateSourceApiV1MarketplaceSourcesSourceIdPatch({
    sourceId,
    requestBody,
  }: {
    sourceId: string;
    requestBody: UpdateSourceRequest;
  }): CancelablePromise<SourceResponse> {
    return this.httpRequest.request({
      method: 'PATCH',
      url: '/api/v1/marketplace/sources/{source_id}',
      path: {
        source_id: sourceId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Bad request - no update parameters provided`,
        404: `Source not found`,
        422: `Validation error - invalid directory path or artifact type`,
        500: `Internal server error - GitHub API failure or database error`,
      },
    });
  }
  /**
   * Delete source
   * Delete a GitHub repository source and all its associated catalog entries.
   *
   * This operation cannot be undone. All discovered artifacts from this source
   * will be removed from the catalog.
   *
   * Authentication: TODO - Add authentication when multi-user support is implemented.
   * @returns void
   * @throws ApiError
   */
  public deleteSourceApiV1MarketplaceSourcesSourceIdDelete({
    sourceId,
  }: {
    sourceId: string;
  }): CancelablePromise<void> {
    return this.httpRequest.request({
      method: 'DELETE',
      url: '/api/v1/marketplace/sources/{source_id}',
      path: {
        source_id: sourceId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Trigger repository rescan
   * Trigger a rescan of the GitHub repository to discover new or updated artifacts.
   *
   * This operation is currently synchronous (runs in the request lifecycle).
   * For large repositories, this may take several seconds. Future versions may
   * support asynchronous background jobs.
   *
   * **Scan Process**:
   * 1. Fetch the repository tree from GitHub
   * 2. Apply heuristic detection to identify artifacts
   * 3. **Apply manual_map overrides** (if configured on source)
   * 4. Deduplicate artifacts within the source (same content, different paths)
   * 5. Deduplicate artifacts against existing collection (already imported)
   * 6. Update the catalog with discovered unique artifacts
   * 7. Update source metadata (artifact_count, last_sync_at, etc.)
   *
   * **Manual Mappings**:
   * The scan uses any manual_map configured on the source to override automatic type
   * detection. For example, if manual_map contains `{"advanced-skills": "skill"}`,
   * all artifacts in the `advanced-skills` directory will be treated as skills
   * regardless of heuristic detection results.
   *
   * **Response includes deduplication statistics**:
   * - `duplicates_within_source`: Duplicate artifacts found in this repo scan
   * - `duplicates_cross_source`: Artifacts already in collection from other sources
   * - `total_detected`: Total artifacts before deduplication
   * - `total_unique`: Unique artifacts added to catalog
   *
   * **Example Response**:
   * ```json
   * {
   * "source_id": "src-abc123",
   * "status": "success",
   * "artifacts_found": 42,
   * "new_count": 5,
   * "updated_count": 2,
   * "removed_count": 1,
   * "unchanged_count": 34,
   * "scan_duration_ms": 3421,
   * "scanned_at": "2025-01-06T12:00:00Z",
   * "duplicates_within_source": 3,
   * "duplicates_cross_source": 2,
   * "total_detected": 52,
   * "total_unique": 47
   * }
   * ```
   *
   * Authentication: TODO - Add authentication when multi-user support is implemented.
   * @returns ScanResultDTO Scan completed successfully
   * @throws ApiError
   */
  public rescanSourceApiV1MarketplaceSourcesSourceIdRescanPost({
    sourceId,
    requestBody,
  }: {
    sourceId: string;
    requestBody?: ScanRequest;
  }): CancelablePromise<ScanResultDTO> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/marketplace/sources/{source_id}/rescan',
      path: {
        source_id: sourceId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        404: `Source not found`,
        422: `Validation Error`,
        500: `Scan failed - check error message in response`,
      },
    });
  }
  /**
   * Sync imported artifacts from source
   * Sync one or more imported artifacts from this source with their upstream versions.
   *
   * This endpoint is used after a rescan detects that imported artifacts have upstream
   * changes (SHA mismatch). It fetches the latest version from GitHub and updates the
   * artifacts in the collection.
   *
   * **Prerequisites**:
   * - Artifacts must have status="imported" in the catalog
   * - Artifacts must have a valid import_id linking to the collection artifact
   *
   * **Sync behavior**:
   * - Fetches the latest version from the upstream GitHub source
   * - Applies changes using "overwrite" strategy (upstream wins)
   * - Reports conflicts if merge is not possible
   *
   * **Example**:
   * ```bash
   * curl -X POST "http://localhost:8080/api/v1/marketplace/sources/src-abc123/sync-imported" \
   * -H "Content-Type: application/json" \
   * -d '{"artifact_ids": ["cat_canvas_design", "cat_my_skill"]}'
   * ```
   *
   * Authentication: TODO - Add authentication when multi-user support is implemented.
   * @returns BulkSyncResponse Successful Response
   * @throws ApiError
   */
  public syncImportedArtifacts({
    sourceId,
    requestBody,
  }: {
    sourceId: string;
    requestBody: BulkSyncRequest;
  }): CancelablePromise<BulkSyncResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/marketplace/sources/{source_id}/sync-imported',
      path: {
        source_id: sourceId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * List artifacts from source
   * List all artifacts discovered from a specific source with optional filtering and sorting.
   *
   * By default, excluded artifacts are hidden from results. Use `include_excluded=true`
   * to include them in listings (useful for reviewing or restoring excluded entries).
   *
   * Supports filtering by:
   * - `artifact_type`: skill, command, agent, etc.
   * - `status`: new, updated, removed, imported, excluded
   * - `min_confidence`: Minimum confidence score (0-100)
   * - `max_confidence`: Maximum confidence score (0-100)
   * - `include_below_threshold`: Include artifacts below 30% confidence threshold (default: false)
   * - `include_excluded`: Include excluded artifacts in results (default: false)
   *
   * Supports sorting by:
   * - `sort_by`: Field to sort by - confidence, name, or date (detected_at). Default: confidence
   * - `sort_order`: Sort order - asc or desc. Default: desc (highest confidence first)
   *
   * Results are paginated using cursor-based pagination for efficiency.
   *
   * **Examples**:
   *
   * List only non-excluded artifacts (default):
   * ```bash
   * curl -X GET "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts"
   * ```
   *
   * List including excluded artifacts:
   * ```bash
   * curl -X GET "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts?include_excluded=true"
   * ```
   *
   * Filter by artifact type with minimum confidence:
   * ```bash
   * curl -X GET "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts?artifact_type=skill&min_confidence=70"
   * ```
   *
   * Sort by name ascending:
   * ```bash
   * curl -X GET "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts?sort_by=name&sort_order=asc"
   * ```
   *
   * Pagination example:
   * ```bash
   * curl -X GET "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts?limit=25&cursor=abc123"
   * ```
   *
   * Authentication: TODO - Add authentication when multi-user support is implemented.
   * @returns CatalogListResponse Successful Response
   * @throws ApiError
   */
  public listSourceArtifacts({
    sourceId,
    artifactType,
    status,
    minConfidence,
    maxConfidence,
    includeBelowThreshold = false,
    includeExcluded = false,
    sortBy,
    sortOrder,
    limit = 50,
    cursor,
  }: {
    sourceId: string;
    /**
     * Filter by artifact type (skill, command, agent, etc.)
     */
    artifactType?: string | null;
    /**
     * Filter by status (new, updated, removed, imported, excluded)
     */
    status?: string | null;
    /**
     * Minimum confidence score (0-100)
     */
    minConfidence?: number | null;
    /**
     * Maximum confidence score (0-100)
     */
    maxConfidence?: number | null;
    /**
     * Include artifacts below 30% confidence threshold (default: false)
     */
    includeBelowThreshold?: boolean;
    /**
     * Include excluded artifacts in results (default: false)
     */
    includeExcluded?: boolean;
    /**
     * Sort field: confidence, name, date (detected_at)
     */
    sortBy?: string | null;
    /**
     * Sort order: asc or desc
     */
    sortOrder?: string | null;
    /**
     * Maximum items per page (1-100)
     */
    limit?: number;
    /**
     * Cursor for pagination (from previous response)
     */
    cursor?: string | null;
  }): CancelablePromise<CatalogListResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/marketplace/sources/{source_id}/artifacts',
      path: {
        source_id: sourceId,
      },
      query: {
        artifact_type: artifactType,
        status: status,
        min_confidence: minConfidence,
        max_confidence: maxConfidence,
        include_below_threshold: includeBelowThreshold,
        include_excluded: includeExcluded,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: limit,
        cursor: cursor,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Update catalog entry name
   * Update the display name for a catalog entry.
   *
   * The updated name is used when importing the artifact into the user's collection
   * and persists until the next rescan of the source.
   *
   * **Request Body**:
   * - `name` (string, required): New artifact name (1-100 chars, no path separators)
   *
   * **Response**: Updated catalog entry
   *
   * Authentication: TODO - Add authentication when multi-user support is implemented.
   * @returns CatalogEntryResponse Successful Response
   * @throws ApiError
   */
  public updateCatalogEntryName({
    sourceId,
    entryId,
    requestBody,
  }: {
    sourceId: string;
    entryId: string;
    requestBody: UpdateCatalogEntryNameRequest;
  }): CancelablePromise<CatalogEntryResponse> {
    return this.httpRequest.request({
      method: 'PATCH',
      url: '/api/v1/marketplace/sources/{source_id}/artifacts/{entry_id}',
      path: {
        source_id: sourceId,
        entry_id: entryId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Import artifacts to collection
   * Import selected artifacts from the catalog to the user's local collection.
   *
   * Specify which catalog entries to import and how to handle conflicts with
   * existing artifacts:
   * - skip: Skip conflicting artifacts (default)
   * - overwrite: Replace existing artifacts
   * - rename: Rename imported artifacts with suffix
   *
   * The import operation will:
   * 1. Validate all entry IDs belong to this source
   * 2. Check for conflicts with existing collection artifacts
   * 3. Download artifacts from upstream URLs (placeholder for now)
   * 4. Update catalog entry statuses to "imported"
   * 5. Return summary of imported, skipped, and failed entries
   *
   * Authentication: TODO - Add authentication when multi-user support is implemented.
   * @returns ImportResultDTO Successful Response
   * @throws ApiError
   */
  public importArtifactsApiV1MarketplaceSourcesSourceIdImportPost({
    sourceId,
    requestBody,
  }: {
    sourceId: string;
    requestBody: ImportRequest;
  }): CancelablePromise<ImportResultDTO> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/marketplace/sources/{source_id}/import',
      path: {
        source_id: sourceId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Force re-import artifact
   * Force re-import an artifact from upstream, resetting its catalog entry status.
   *
   * This endpoint handles several scenarios:
   * - Artifacts with status="imported" that need to be refreshed from upstream
   * - Artifacts that were deleted but catalog entry still shows "imported"
   * - Broken or missing artifacts in the collection
   *
   * **Workflow**:
   * 1. Validates the catalog entry exists and belongs to this source
   * 2. If `keep_deployments=True` and artifact exists in collection:
   * - Saves deployment records
   * - Deletes the existing artifact
   * - Re-imports from upstream
   * - Restores deployment records
   * 3. If `keep_deployments=False` or artifact is missing:
   * - Resets catalog entry status to "new"
   * - Performs a fresh import from upstream
   *
   * **Request Body**:
   * - `keep_deployments` (bool, optional): Whether to preserve deployment records (default: false)
   *
   * **Response**: Result with success flag, new artifact ID, and restoration count
   *
   * **Example**:
   * ```bash
   * curl -X POST "http://localhost:8080/api/v1/marketplace/sources/src-abc123/entries/cat-def456/reimport" \
   * -H "Content-Type: application/json" \
   * -d '{"keep_deployments": true}'
   * ```
   *
   * Authentication: TODO - Add authentication when multi-user support is implemented.
   * @returns ReimportResponse Re-import completed successfully
   * @throws ApiError
   */
  public reimportCatalogEntry({
    sourceId,
    entryId,
    requestBody,
  }: {
    sourceId: string;
    entryId: string;
    requestBody: ReimportRequest;
  }): CancelablePromise<ReimportResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/marketplace/sources/{source_id}/entries/{entry_id}/reimport',
      path: {
        source_id: sourceId,
        entry_id: entryId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        404: `Source or catalog entry not found`,
        422: `Validation Error`,
        500: `Re-import failed - check error message`,
      },
    });
  }
  /**
   * Mark or restore catalog artifact
   * Mark a catalog entry as excluded from the catalog or restore a previously excluded entry.
   *
   * Use this endpoint to mark artifacts that are false positives (not actually Claude artifacts),
   * documentation-only files, or other entries that shouldn't appear in the default catalog view.
   * Excluded artifacts are hidden unless explicitly requested with `include_excluded=True` when
   * listing artifacts.
   *
   * This operation is idempotent - calling it multiple times with the same parameters will
   * return success with the current state.
   *
   * **Request Body**:
   * - `excluded` (bool, required): True to mark as excluded, False to restore
   * - `reason` (string, optional): User-provided reason (max 500 chars)
   *
   * **Response**: Updated catalog entry with `excluded_at` and `excluded_reason` fields
   *
   * **Examples**:
   *
   * Mark as excluded with reason:
   * ```bash
   * curl -X PATCH "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts/cat-def456/exclude" \
   * -H "Content-Type: application/json" \
   * -d '{
   * "excluded": true,
   * "reason": "Not a valid skill - documentation only"
   * }'
   * ```
   *
   * Restore previously excluded:
   * ```bash
   * curl -X PATCH "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts/cat-def456/exclude" \
   * -H "Content-Type: application/json" \
   * -d '{"excluded": false}'
   * ```
   *
   * Authentication: TODO - Add authentication when multi-user support is implemented.
   * @returns CatalogEntryResponse Successful Response
   * @throws ApiError
   */
  public excludeOrRestoreArtifact({
    sourceId,
    entryId,
    requestBody,
  }: {
    sourceId: string;
    entryId: string;
    requestBody: ExcludeArtifactRequest;
  }): CancelablePromise<CatalogEntryResponse> {
    return this.httpRequest.request({
      method: 'PATCH',
      url: '/api/v1/marketplace/sources/{source_id}/artifacts/{entry_id}/exclude',
      path: {
        source_id: sourceId,
        entry_id: entryId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Restore excluded catalog artifact
   * Remove the exclusion status from a catalog entry, restoring it to the catalog.
   *
   * This is a convenience endpoint that performs the same operation as calling
   * PATCH with `excluded=False`. It is idempotent - calling it on a non-excluded
   * entry will return success with the current state.
   *
   * Restored entries will be visible in the default catalog view and can be
   * imported to collections.
   *
   * **Examples**:
   *
   * Restore an excluded artifact:
   * ```bash
   * curl -X DELETE "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts/cat-def456/exclude"
   * ```
   *
   * List artifacts including excluded (before restoring):
   * ```bash
   * curl -X GET "http://localhost:8080/api/v1/marketplace/sources/src-abc123/artifacts?include_excluded=true"
   * ```
   *
   * After restore, the artifact will appear in both filtered and unfiltered listings.
   *
   * Authentication: TODO - Add authentication when multi-user support is implemented.
   * @returns CatalogEntryResponse Successful Response
   * @throws ApiError
   */
  public restoreExcludedArtifact({
    sourceId,
    entryId,
  }: {
    sourceId: string;
    entryId: string;
  }): CancelablePromise<CatalogEntryResponse> {
    return this.httpRequest.request({
      method: 'DELETE',
      url: '/api/v1/marketplace/sources/{source_id}/artifacts/{entry_id}/exclude',
      path: {
        source_id: sourceId,
        entry_id: entryId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Get path-based tag suggestions for catalog entry
   * Retrieve extracted path segments and their approval status for a catalog entry.
   *
   * Returns all extracted segments with their current approval status (pending, approved,
   * rejected, excluded). Only includes entries that have been scanned with path extraction
   * enabled.
   *
   * The path_segments field contains a JSON object with:
   * - raw_path: Original artifact path
   * - extracted: Array of {segment, normalized, status, reason} objects
   * - extracted_at: ISO timestamp of extraction
   *
   * Path Parameters:
   * - source_id: Marketplace source identifier
   * - entry_id: Catalog entry identifier
   *
   * Example: GET /marketplace/sources/src-123/catalog/cat-456/path-tags
   * @returns PathSegmentsResponse Successful Response
   * @throws ApiError
   */
  public getPathTagsApiV1MarketplaceSourcesSourceIdCatalogEntryIdPathTagsGet({
    sourceId,
    entryId,
  }: {
    sourceId: string;
    entryId: string;
  }): CancelablePromise<PathSegmentsResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/marketplace/sources/{source_id}/catalog/{entry_id}/path-tags',
      path: {
        source_id: sourceId,
        entry_id: entryId,
      },
      errors: {
        400: `Entry has no path_segments (not extracted yet)`,
        404: `Source or entry not found`,
        422: `Validation Error`,
      },
    });
  }
  /**
   * Update approval status of a path segment
   * Approve or reject a suggested path-based tag.
   *
   * Updates the status field in path_segments JSON for a single segment.
   * Only "pending" status segments can be changed. Cannot modify "excluded"
   * segments (filtered by extraction rules).
   *
   * Status values:
   * - "pending": Segment awaiting approval/rejection (default)
   * - "approved": Segment will be applied as tag during import
   * - "rejected": Segment will not be applied as tag
   * - "excluded": Segment filtered by rules (cannot be changed)
   *
   * Path Parameters:
   * - source_id: Marketplace source identifier
   * - entry_id: Catalog entry identifier
   *
   * Request Body:
   * - segment: Original segment value to update (e.g., "ui-ux")
   * - status: New status ("approved" or "rejected")
   *
   * Example: PATCH /marketplace/sources/src-123/catalog/cat-456/path-tags
   * @returns UpdateSegmentStatusResponse Successful Response
   * @throws ApiError
   */
  public updatePathTagStatusApiV1MarketplaceSourcesSourceIdCatalogEntryIdPathTagsPatch({
    sourceId,
    entryId,
    requestBody,
  }: {
    sourceId: string;
    entryId: string;
    requestBody: UpdateSegmentStatusRequest;
  }): CancelablePromise<UpdateSegmentStatusResponse> {
    return this.httpRequest.request({
      method: 'PATCH',
      url: '/api/v1/marketplace/sources/{source_id}/catalog/{entry_id}/path-tags',
      path: {
        source_id: sourceId,
        entry_id: entryId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        404: `Source, entry, or segment not found`,
        409: `Segment already approved/rejected or is excluded`,
        422: `Validation Error`,
        500: `Malformed path_segments JSON`,
      },
    });
  }
  /**
   * Get file tree for artifact
   * Retrieve the file tree for a marketplace artifact.
   *
   * Returns a list of files and directories within the artifact, suitable
   * for displaying in a file browser UI. Each entry includes the path,
   * type (blob/tree), size (for files), and SHA.
   *
   * Results are cached for 1 hour to reduce GitHub API calls.
   *
   * Path Parameters:
   * - source_id: Marketplace source identifier
   * - artifact_path: Path to the artifact within the repository (e.g., "skills/canvas")
   *
   * Example: GET /marketplace/sources/src-123/artifacts/skills/canvas/files
   * @returns FileTreeResponse Successful Response
   * @throws ApiError
   */
  public getArtifactFileTreeApiV1MarketplaceSourcesSourceIdArtifactsArtifactPathFilesGet({
    sourceId,
    artifactPath,
  }: {
    sourceId: string;
    artifactPath: string;
  }): CancelablePromise<FileTreeResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/marketplace/sources/{source_id}/artifacts/{artifact_path}/files',
      path: {
        source_id: sourceId,
        artifact_path: artifactPath,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Get file content from artifact
   * Retrieve the content of a specific file within a marketplace artifact.
   *
   * Returns the file content with metadata including encoding, size, and SHA.
   * For binary files, content is base64-encoded with is_binary=True.
   *
   * Results are cached for 2 hours to reduce GitHub API calls.
   *
   * Path Parameters:
   * - source_id: Marketplace source identifier
   * - artifact_path: Path to the artifact within the repository (e.g., "skills/canvas")
   * - file_path: Path to the file within the artifact (e.g., "SKILL.md" or "src/index.ts")
   *
   * Example: GET /marketplace/sources/src-123/artifacts/skills/canvas/files/SKILL.md
   * @returns skillmeat__api__schemas__marketplace__FileContentResponse Successful Response
   * @throws ApiError
   */
  public getArtifactFileContentApiV1MarketplaceSourcesSourceIdArtifactsArtifactPathFilesFilePathGet({
    sourceId,
    artifactPath,
    filePath,
  }: {
    sourceId: string;
    artifactPath: string;
    filePath: string;
  }): CancelablePromise<skillmeat__api__schemas__marketplace__FileContentResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/marketplace/sources/{source_id}/artifacts/{artifact_path}/files/{file_path}',
      path: {
        source_id: sourceId,
        artifact_path: artifactPath,
        file_path: filePath,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Get auto-tag suggestions from GitHub topics
   * Retrieve extracted GitHub repository topics and their approval status.
   *
   * Topics are extracted from the repository metadata and stored as auto-tags
   * that can be approved or rejected. Approved auto-tags are added to the
   * source's tags list.
   *
   * This endpoint returns all auto-tags with their current status (pending,
   * approved, or rejected) and indicates whether any tags are still pending.
   * @returns AutoTagsResponse Successful Response
   * @throws ApiError
   */
  public getSourceAutoTagsApiV1MarketplaceSourcesSourceIdAutoTagsGet({
    sourceId,
  }: {
    sourceId: string;
  }): CancelablePromise<AutoTagsResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/marketplace/sources/{source_id}/auto-tags',
      path: {
        source_id: sourceId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Update approval status of an auto-tag
   * Approve or reject a suggested auto-tag from GitHub topics.
   *
   * When a tag is approved, it is automatically added to the source's
   * regular tags list. When rejected, it is marked as rejected and
   * will not be suggested again.
   *
   * Note: Auto-tags are source-level only. They do NOT propagate to
   * imported artifacts. Use path_tags for artifact-level tagging.
   * @returns UpdateAutoTagResponse Successful Response
   * @throws ApiError
   */
  public updateSourceAutoTagApiV1MarketplaceSourcesSourceIdAutoTagsPatch({
    sourceId,
    requestBody,
  }: {
    sourceId: string;
    requestBody: UpdateAutoTagRequest;
  }): CancelablePromise<UpdateAutoTagResponse> {
    return this.httpRequest.request({
      method: 'PATCH',
      url: '/api/v1/marketplace/sources/{source_id}/auto-tags',
      path: {
        source_id: sourceId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Refresh auto-tags from GitHub topics
   * Fetches the current GitHub topics for the source repository and updates
   * the auto_tags field. Existing tag approval status is preserved.
   *
   * This is useful for:
   * - Sources created before auto-tags feature was added
   * - Syncing with updated GitHub topics after repository changes
   * @returns AutoTagRefreshResponse Successful Response
   * @throws ApiError
   */
  public refreshSourceAutoTagsApiV1MarketplaceSourcesSourceIdRefreshAutoTagsPost({
    sourceId,
  }: {
    sourceId: string;
  }): CancelablePromise<AutoTagRefreshResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/marketplace/sources/{source_id}/refresh-auto-tags',
      path: {
        source_id: sourceId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Refresh auto-tags for multiple sources
   * Fetches GitHub topics for multiple sources in a single request.
   * Each source is processed independently, so failures for one source
   * do not affect others.
   *
   * Rate limiting is handled gracefully - if rate limited during bulk
   * operation, remaining sources will be marked as failed with the
   * rate limit error.
   * @returns BulkAutoTagRefreshResponse Successful Response
   * @throws ApiError
   */
  public bulkRefreshAutoTagsApiV1MarketplaceSourcesBulkRefreshAutoTagsPost({
    requestBody,
  }: {
    requestBody: BulkAutoTagRefreshRequest;
  }): CancelablePromise<BulkAutoTagRefreshResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/marketplace/sources/bulk-refresh-auto-tags',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    });
  }
}
