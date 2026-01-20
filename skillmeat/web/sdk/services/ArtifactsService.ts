/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ArtifactCreateRequest } from '../models/ArtifactCreateRequest';
import type { ArtifactCreateResponse } from '../models/ArtifactCreateResponse';
import type { ArtifactDeployRequest } from '../models/ArtifactDeployRequest';
import type { ArtifactDeployResponse } from '../models/ArtifactDeployResponse';
import type { ArtifactDiffResponse } from '../models/ArtifactDiffResponse';
import type { ArtifactListResponse } from '../models/ArtifactListResponse';
import type { ArtifactResponse } from '../models/ArtifactResponse';
import type { ArtifactSyncRequest } from '../models/ArtifactSyncRequest';
import type { ArtifactSyncResponse } from '../models/ArtifactSyncResponse';
import type { ArtifactUpdateRequest } from '../models/ArtifactUpdateRequest';
import type { ArtifactUpstreamDiffResponse } from '../models/ArtifactUpstreamDiffResponse';
import type { ArtifactUpstreamResponse } from '../models/ArtifactUpstreamResponse';
import type { Body_undeploy_artifact_api_v1_artifacts__artifact_id__undeploy_post } from '../models/Body_undeploy_artifact_api_v1_artifacts__artifact_id__undeploy_post';
import type { BulkImportRequest } from '../models/BulkImportRequest';
import type { BulkImportResult } from '../models/BulkImportResult';
import type { ConfirmDuplicatesRequest } from '../models/ConfirmDuplicatesRequest';
import type { ConfirmDuplicatesResponse } from '../models/ConfirmDuplicatesResponse';
import type { DiscoveryRequest } from '../models/DiscoveryRequest';
import type { DiscoveryResult } from '../models/DiscoveryResult';
import type { FileListResponse } from '../models/FileListResponse';
import type { FileUpdateRequest } from '../models/FileUpdateRequest';
import type { MetadataFetchResponse } from '../models/MetadataFetchResponse';
import type { ParameterUpdateRequest } from '../models/ParameterUpdateRequest';
import type { ParameterUpdateResponse } from '../models/ParameterUpdateResponse';
import type { skillmeat__api__schemas__artifacts__FileContentResponse } from '../models/skillmeat__api__schemas__artifacts__FileContentResponse';
import type { SkipClearResponse } from '../models/SkipClearResponse';
import type { SkipPreferenceAddRequest } from '../models/SkipPreferenceAddRequest';
import type { SkipPreferenceListResponse } from '../models/SkipPreferenceListResponse';
import type { SkipPreferenceResponse } from '../models/SkipPreferenceResponse';
import type { TagResponse } from '../models/TagResponse';
import type { VersionGraphResponse } from '../models/VersionGraphResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class ArtifactsService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * Discover artifacts in collection
   * Scan collection for existing artifacts that can be imported
   * @returns DiscoveryResult Discovery scan completed successfully
   * @throws ApiError
   */
  public discoverArtifactsApiV1ArtifactsDiscoverPost({
    requestBody,
    collection,
  }: {
    requestBody: DiscoveryRequest;
    /**
     * Collection name (uses default if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<DiscoveryResult> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/artifacts/discover',
      query: {
        collection: collection,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid scan path`,
        401: `Unauthorized`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Discover artifacts in a project
   * Scan a project's .claude/ directory for existing artifacts that can be imported
   * @returns DiscoveryResult Discovery scan completed successfully
   * @throws ApiError
   */
  public discoverProjectArtifactsApiV1ArtifactsDiscoverProjectProjectIdPost({
    projectId,
    collection,
  }: {
    /**
     * URL-encoded project path
     */
    projectId: string;
    /**
     * Collection name (uses default if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<DiscoveryResult> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/artifacts/discover/project/{project_id}',
      path: {
        project_id: projectId,
      },
      query: {
        collection: collection,
      },
      errors: {
        400: `Invalid project path`,
        401: `Unauthorized`,
        404: `Project not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Bulk import artifacts
   * Import multiple artifacts from discovered artifacts or external sources with atomic transaction
   * @returns BulkImportResult Bulk import completed (check results for per-artifact status)
   * @throws ApiError
   */
  public bulkImportArtifactsApiV1ArtifactsDiscoverImportPost({
    requestBody,
    collection,
    projectId,
  }: {
    requestBody: BulkImportRequest;
    /**
     * Collection name (uses default if not specified)
     */
    collection?: string | null;
    /**
     * Base64-encoded project path to also record deployments for the imports
     */
    projectId?: string | null;
  }): CancelablePromise<BulkImportResult> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/artifacts/discover/import',
      query: {
        collection: collection,
        project_id: projectId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request`,
        401: `Unauthorized`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Process duplicate review decisions
   * Process user decisions from the duplicate review modal.
   *
   * Handles three types of decisions:
   * 1. **matches**: Link discovered duplicates to existing collection artifacts
   * 2. **new_artifacts**: Import selected paths as new artifacts
   * 3. **skipped**: Acknowledge paths the user chose to skip (logged for audit)
   *
   * All operations are atomic - if any operation fails, the response will
   * indicate partial success with error details.
   *
   * This endpoint is idempotent for link operations - calling multiple times
   * with the same matches will not create duplicate links.
   * @returns ConfirmDuplicatesResponse Duplicate decisions processed successfully
   * @throws ApiError
   */
  public confirmDuplicatesApiV1ArtifactsConfirmDuplicatesPost({
    requestBody,
    collection,
  }: {
    requestBody: ConfirmDuplicatesRequest;
    /**
     * Collection name (uses default if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<ConfirmDuplicatesResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/artifacts/confirm-duplicates',
      query: {
        collection: collection,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request`,
        401: `Unauthorized`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Create new artifact
   * Create a new artifact from GitHub URL or local path
   * @returns ArtifactCreateResponse Artifact created successfully
   * @throws ApiError
   */
  public createArtifactApiV1ArtifactsPost({
    requestBody,
  }: {
    requestBody: ArtifactCreateRequest;
  }): CancelablePromise<ArtifactCreateResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/artifacts',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request`,
        401: `Unauthorized`,
        404: `Source not found`,
        409: `Artifact already exists`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * List all artifacts
   * Retrieve a paginated list of artifacts across all collections
   * @returns ArtifactListResponse Successfully retrieved artifacts
   * @throws ApiError
   */
  public listArtifactsApiV1ArtifactsGet({
    limit = 20,
    after,
    artifactType,
    collection,
    tags,
    checkDrift = false,
    projectPath,
  }: {
    /**
     * Number of items per page (max 100)
     */
    limit?: number;
    /**
     * Cursor for pagination (next page)
     */
    after?: string | null;
    /**
     * Filter by artifact type (skill, command, agent)
     */
    artifactType?: string | null;
    /**
     * Filter by collection name
     */
    collection?: string | null;
    /**
     * Filter by tags (comma-separated)
     */
    tags?: string | null;
    /**
     * Check for local modifications and drift status (may impact performance)
     */
    checkDrift?: boolean;
    /**
     * Project path for drift detection (required if check_drift=true)
     */
    projectPath?: string | null;
  }): CancelablePromise<ArtifactListResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/artifacts',
      query: {
        limit: limit,
        after: after,
        artifact_type: artifactType,
        collection: collection,
        tags: tags,
        check_drift: checkDrift,
        project_path: projectPath,
      },
      errors: {
        401: `Unauthorized`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Get artifact details
   * Retrieve detailed information about a specific artifact
   * @returns ArtifactResponse Successfully retrieved artifact
   * @throws ApiError
   */
  public getArtifactApiV1ArtifactsArtifactIdGet({
    artifactId,
    collection,
    includeDeployments = false,
  }: {
    artifactId: string;
    /**
     * Collection name (searches all if not specified)
     */
    collection?: string | null;
    /**
     * Include deployment statistics across all projects
     */
    includeDeployments?: boolean;
  }): CancelablePromise<ArtifactResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/artifacts/{artifact_id}',
      path: {
        artifact_id: artifactId,
      },
      query: {
        collection: collection,
        include_deployments: includeDeployments,
      },
      errors: {
        401: `Unauthorized`,
        404: `Artifact not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Update artifact
   * Update artifact metadata, tags, and aliases
   * @returns ArtifactResponse Successfully updated artifact
   * @throws ApiError
   */
  public updateArtifactApiV1ArtifactsArtifactIdPut({
    artifactId,
    requestBody,
    collection,
  }: {
    artifactId: string;
    requestBody: ArtifactUpdateRequest;
    /**
     * Collection name (searches all if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<ArtifactResponse> {
    return this.httpRequest.request({
      method: 'PUT',
      url: '/api/v1/artifacts/{artifact_id}',
      path: {
        artifact_id: artifactId,
      },
      query: {
        collection: collection,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request`,
        401: `Unauthorized`,
        404: `Artifact not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Delete artifact
   * Remove an artifact from the collection
   * @returns void
   * @throws ApiError
   */
  public deleteArtifactApiV1ArtifactsArtifactIdDelete({
    artifactId,
    collection,
  }: {
    artifactId: string;
    /**
     * Collection name (searches all if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<void> {
    return this.httpRequest.request({
      method: 'DELETE',
      url: '/api/v1/artifacts/{artifact_id}',
      path: {
        artifact_id: artifactId,
      },
      query: {
        collection: collection,
      },
      errors: {
        400: `Invalid request`,
        401: `Unauthorized`,
        404: `Artifact not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Check upstream status
   * Check for updates and upstream status for an artifact
   * @returns ArtifactUpstreamResponse Successfully checked upstream status
   * @throws ApiError
   */
  public checkArtifactUpstreamApiV1ArtifactsArtifactIdUpstreamGet({
    artifactId,
    collection,
  }: {
    artifactId: string;
    /**
     * Collection name (searches all if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<ArtifactUpstreamResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/artifacts/{artifact_id}/upstream',
      path: {
        artifact_id: artifactId,
      },
      query: {
        collection: collection,
      },
      errors: {
        401: `Unauthorized`,
        404: `Artifact not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Update artifact parameters
   * Update artifact parameters (source, version, scope, tags, aliases) after import
   * @returns ParameterUpdateResponse Successfully updated parameters
   * @throws ApiError
   */
  public updateArtifactParametersApiV1ArtifactsArtifactIdParametersPut({
    artifactId,
    requestBody,
    collection,
  }: {
    artifactId: string;
    requestBody: ParameterUpdateRequest;
    /**
     * Collection name (searches all if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<ParameterUpdateResponse> {
    return this.httpRequest.request({
      method: 'PUT',
      url: '/api/v1/artifacts/{artifact_id}/parameters',
      path: {
        artifact_id: artifactId,
      },
      query: {
        collection: collection,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request`,
        401: `Unauthorized`,
        404: `Artifact not found`,
        422: `Validation error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Deploy artifact to project
   * Deploy artifact from collection to project's .claude/ directory
   * @returns ArtifactDeployResponse Artifact deployed successfully
   * @throws ApiError
   */
  public deployArtifactApiV1ArtifactsArtifactIdDeployPost({
    artifactId,
    requestBody,
    collection,
  }: {
    artifactId: string;
    requestBody: ArtifactDeployRequest;
    /**
     * Collection name (uses default if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<ArtifactDeployResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/artifacts/{artifact_id}/deploy',
      path: {
        artifact_id: artifactId,
      },
      query: {
        collection: collection,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request`,
        404: `Artifact not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Sync artifact from project to collection
   * Pull changes from project back to collection, with conflict resolution
   * @returns ArtifactSyncResponse Artifact synced successfully
   * @throws ApiError
   */
  public syncArtifactApiV1ArtifactsArtifactIdSyncPost({
    artifactId,
    requestBody,
    collection,
  }: {
    artifactId: string;
    requestBody: ArtifactSyncRequest;
    /**
     * Collection name (uses default if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<ArtifactSyncResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/artifacts/{artifact_id}/sync',
      path: {
        artifact_id: artifactId,
      },
      query: {
        collection: collection,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request`,
        404: `Artifact not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Undeploy artifact from project
   * Remove deployed artifact from project's .claude/ directory
   * @returns ArtifactDeployResponse Artifact undeployed successfully
   * @throws ApiError
   */
  public undeployArtifactApiV1ArtifactsArtifactIdUndeployPost({
    artifactId,
    requestBody,
    collection,
  }: {
    artifactId: string;
    requestBody: Body_undeploy_artifact_api_v1_artifacts__artifact_id__undeploy_post;
    /**
     * Collection name (uses default if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<ArtifactDeployResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/artifacts/{artifact_id}/undeploy',
      path: {
        artifact_id: artifactId,
      },
      query: {
        _collection: collection,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        404: `Artifact not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Get artifact version graph
   * Build and return version graph showing deployment hierarchy across all projects
   * @returns VersionGraphResponse Successfully retrieved version graph
   * @throws ApiError
   */
  public getVersionGraphApiV1ArtifactsArtifactIdVersionGraphGet({
    artifactId,
    collection,
  }: {
    artifactId: string;
    /**
     * Filter to specific collection
     */
    collection?: string | null;
  }): CancelablePromise<VersionGraphResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/artifacts/{artifact_id}/version-graph',
      path: {
        artifact_id: artifactId,
      },
      query: {
        collection: collection,
      },
      errors: {
        401: `Unauthorized`,
        404: `Artifact not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Get artifact diff
   * Compare artifact versions between collection and deployed project
   * @returns ArtifactDiffResponse Successfully retrieved diff
   * @throws ApiError
   */
  public getArtifactDiffApiV1ArtifactsArtifactIdDiffGet({
    artifactId,
    projectPath,
    collection,
  }: {
    artifactId: string;
    /**
     * Path to project for comparison
     */
    projectPath: string;
    /**
     * Collection name (searches all if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<ArtifactDiffResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/artifacts/{artifact_id}/diff',
      path: {
        artifact_id: artifactId,
      },
      query: {
        project_path: projectPath,
        collection: collection,
      },
      errors: {
        400: `Invalid request`,
        401: `Unauthorized`,
        404: `Artifact not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Get artifact upstream diff
   * Compare collection artifact with its GitHub upstream source
   * @returns ArtifactUpstreamDiffResponse Successfully retrieved upstream diff
   * @throws ApiError
   */
  public getArtifactUpstreamDiffApiV1ArtifactsArtifactIdUpstreamDiffGet({
    artifactId,
    collection,
  }: {
    artifactId: string;
    /**
     * Collection name (searches all if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<ArtifactUpstreamDiffResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/artifacts/{artifact_id}/upstream-diff',
      path: {
        artifact_id: artifactId,
      },
      query: {
        collection: collection,
      },
      errors: {
        400: `Invalid request or no upstream source`,
        401: `Unauthorized`,
        404: `Artifact not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * List artifact files
   * List all files and directories in an artifact
   * @returns FileListResponse Successfully retrieved file list
   * @throws ApiError
   */
  public listArtifactFilesApiV1ArtifactsArtifactIdFilesGet({
    artifactId,
    collection,
  }: {
    artifactId: string;
    /**
     * Collection name (searches all if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<FileListResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/artifacts/{artifact_id}/files',
      path: {
        artifact_id: artifactId,
      },
      query: {
        collection: collection,
      },
      errors: {
        400: `Invalid request`,
        401: `Unauthorized`,
        404: `Artifact not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Get artifact file content
   * Get the content of a specific file within an artifact
   * @returns skillmeat__api__schemas__artifacts__FileContentResponse Successfully retrieved file content
   * @throws ApiError
   */
  public getArtifactFileContentApiV1ArtifactsArtifactIdFilesFilePathGet({
    artifactId,
    filePath,
    collection,
  }: {
    artifactId: string;
    filePath: string;
    /**
     * Collection name (searches all if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<skillmeat__api__schemas__artifacts__FileContentResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/artifacts/{artifact_id}/files/{file_path}',
      path: {
        artifact_id: artifactId,
        file_path: filePath,
      },
      query: {
        collection: collection,
      },
      errors: {
        400: `Invalid request or path traversal attempt`,
        401: `Unauthorized`,
        404: `Artifact or file not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Update artifact file content
   * Update the content of a specific file within an artifact
   * @returns skillmeat__api__schemas__artifacts__FileContentResponse Successfully updated file content
   * @throws ApiError
   */
  public updateArtifactFileContentApiV1ArtifactsArtifactIdFilesFilePathPut({
    artifactId,
    filePath,
    requestBody,
    collection,
  }: {
    artifactId: string;
    filePath: string;
    requestBody: FileUpdateRequest;
    /**
     * Collection name (searches all if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<skillmeat__api__schemas__artifacts__FileContentResponse> {
    return this.httpRequest.request({
      method: 'PUT',
      url: '/api/v1/artifacts/{artifact_id}/files/{file_path}',
      path: {
        artifact_id: artifactId,
        file_path: filePath,
      },
      query: {
        collection: collection,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request, path traversal attempt, or directory path`,
        401: `Unauthorized`,
        404: `Artifact or file not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Create new artifact file
   * Create a new file within an artifact
   * @returns skillmeat__api__schemas__artifacts__FileContentResponse Successfully created file
   * @throws ApiError
   */
  public createArtifactFileApiV1ArtifactsArtifactIdFilesFilePathPost({
    artifactId,
    filePath,
    requestBody,
    collection,
  }: {
    artifactId: string;
    filePath: string;
    requestBody: FileUpdateRequest;
    /**
     * Collection name (searches all if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<skillmeat__api__schemas__artifacts__FileContentResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/artifacts/{artifact_id}/files/{file_path}',
      path: {
        artifact_id: artifactId,
        file_path: filePath,
      },
      query: {
        collection: collection,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request, path traversal attempt, or file already exists`,
        401: `Unauthorized`,
        404: `Artifact not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Delete artifact file
   * Delete a specific file within an artifact
   * @returns void
   * @throws ApiError
   */
  public deleteArtifactFileApiV1ArtifactsArtifactIdFilesFilePathDelete({
    artifactId,
    filePath,
    collection,
  }: {
    artifactId: string;
    filePath: string;
    /**
     * Collection name (searches all if not specified)
     */
    collection?: string | null;
  }): CancelablePromise<void> {
    return this.httpRequest.request({
      method: 'DELETE',
      url: '/api/v1/artifacts/{artifact_id}/files/{file_path}',
      path: {
        artifact_id: artifactId,
        file_path: filePath,
      },
      query: {
        collection: collection,
      },
      errors: {
        400: `Invalid request, path traversal attempt, or directory path`,
        401: `Unauthorized`,
        404: `Artifact or file not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Fetch Github Metadata
   * Fetch metadata from GitHub for a given source.
   *
   * Parses the source URL, fetches repository metadata and
   * frontmatter from the artifact's markdown file. Results
   * are cached to reduce GitHub API calls (configurable TTL).
   *
   * Args:
   * source: GitHub source in format user/repo/path[@version]
   * request: FastAPI request object for accessing app state
   * config_mgr: Config manager dependency for GitHub token
   *
   * Returns:
   * MetadataFetchResponse with metadata or error details
   *
   * Raises:
   * HTTPException: On internal errors or if feature is disabled
   * @returns MetadataFetchResponse Successful Response
   * @throws ApiError
   */
  public fetchGithubMetadataApiV1ArtifactsMetadataGithubGet({
    source,
  }: {
    /**
     * GitHub source: user/repo/path[@version]
     */
    source: string;
  }): CancelablePromise<MetadataFetchResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/artifacts/metadata/github',
      query: {
        source: source,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Get discovery feature metrics
   * Get metrics and statistics for discovery features including:
   * - Total discovery scans performed
   * - Total artifacts discovered
   * - Total bulk imports
   * - GitHub metadata fetch statistics
   * - Cache hit/miss rates
   * - Error counts
   * - Last scan information
   *
   * This endpoint provides simple metrics without requiring Prometheus infrastructure.
   * For production monitoring, use the /metrics endpoint exposed by the Prometheus client.
   * @returns any Discovery metrics and statistics
   * @throws ApiError
   */
  public getDiscoveryMetricsApiV1ArtifactsMetricsDiscoveryGet(): CancelablePromise<any> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/artifacts/metrics/discovery',
    });
  }
  /**
   * Discovery feature health check
   * Check the health status of discovery features including:
   * - Discovery service availability
   * - Auto-population feature status
   * - Cache configuration
   * - Current metrics
   *
   * Returns 200 OK if all discovery features are operational.
   * @returns any Discovery health status
   * @throws ApiError
   */
  public discoveryHealthCheckApiV1ArtifactsHealthDiscoveryGet(): CancelablePromise<any> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/artifacts/health/discovery',
    });
  }
  /**
   * Add skip preference
   * Add a skip preference for an artifact in the project
   * @returns SkipPreferenceResponse Skip preference added successfully
   * @throws ApiError
   */
  public addSkipPreferenceApiV1ArtifactsProjectsProjectIdSkipPreferencesPost({
    projectId,
    requestBody,
  }: {
    /**
     * URL-encoded project path
     */
    projectId: string;
    requestBody: SkipPreferenceAddRequest;
  }): CancelablePromise<SkipPreferenceResponse> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/artifacts/projects/{project_id}/skip-preferences',
      path: {
        project_id: projectId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Invalid request`,
        401: `Unauthorized`,
        404: `Project not found`,
        422: `Validation error (duplicate or invalid artifact_key)`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Clear all skip preferences
   * Clear all skip preferences for a project
   * @returns SkipClearResponse Skip preferences cleared successfully
   * @throws ApiError
   */
  public clearSkipPreferencesApiV1ArtifactsProjectsProjectIdSkipPreferencesDelete({
    projectId,
  }: {
    /**
     * URL-encoded project path
     */
    projectId: string;
  }): CancelablePromise<SkipClearResponse> {
    return this.httpRequest.request({
      method: 'DELETE',
      url: '/api/v1/artifacts/projects/{project_id}/skip-preferences',
      path: {
        project_id: projectId,
      },
      errors: {
        400: `Invalid request`,
        401: `Unauthorized`,
        404: `Project not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * List skip preferences
   * List all skip preferences for a project
   * @returns SkipPreferenceListResponse Skip preferences retrieved successfully
   * @throws ApiError
   */
  public listSkipPreferencesApiV1ArtifactsProjectsProjectIdSkipPreferencesGet({
    projectId,
  }: {
    /**
     * URL-encoded project path
     */
    projectId: string;
  }): CancelablePromise<SkipPreferenceListResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/artifacts/projects/{project_id}/skip-preferences',
      path: {
        project_id: projectId,
      },
      errors: {
        400: `Invalid request`,
        401: `Unauthorized`,
        404: `Project not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Remove skip preference
   * Remove a single skip preference by artifact key
   * @returns SkipClearResponse Skip preference removed successfully
   * @throws ApiError
   */
  public removeSkipPreferenceApiV1ArtifactsProjectsProjectIdSkipPreferencesArtifactKeyDelete({
    projectId,
    artifactKey,
  }: {
    /**
     * URL-encoded project path
     */
    projectId: string;
    /**
     * Artifact key to remove (e.g., 'skill:canvas')
     */
    artifactKey: string;
  }): CancelablePromise<SkipClearResponse> {
    return this.httpRequest.request({
      method: 'DELETE',
      url: '/api/v1/artifacts/projects/{project_id}/skip-preferences/{artifact_key}',
      path: {
        project_id: projectId,
        artifact_key: artifactKey,
      },
      errors: {
        400: `Invalid request`,
        401: `Unauthorized`,
        404: `Project or skip preference not found`,
        422: `Validation Error`,
        500: `Internal server error`,
      },
    });
  }
  /**
   * Get artifact tags
   * Get all tags assigned to an artifact
   * @returns TagResponse Successful Response
   * @throws ApiError
   */
  public getArtifactTagsApiV1ArtifactsArtifactIdTagsGet({
    artifactId,
  }: {
    artifactId: string;
  }): CancelablePromise<Array<TagResponse>> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/artifacts/{artifact_id}/tags',
      path: {
        artifact_id: artifactId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Add tag to artifact
   * Associate a tag with an artifact
   * @returns any Successful Response
   * @throws ApiError
   */
  public addTagToArtifactApiV1ArtifactsArtifactIdTagsTagIdPost({
    artifactId,
    tagId,
  }: {
    artifactId: string;
    tagId: string;
  }): CancelablePromise<Record<string, any>> {
    return this.httpRequest.request({
      method: 'POST',
      url: '/api/v1/artifacts/{artifact_id}/tags/{tag_id}',
      path: {
        artifact_id: artifactId,
        tag_id: tagId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Remove tag from artifact
   * Remove a tag from an artifact
   * @returns void
   * @throws ApiError
   */
  public removeTagFromArtifactApiV1ArtifactsArtifactIdTagsTagIdDelete({
    artifactId,
    tagId,
  }: {
    artifactId: string;
    tagId: string;
  }): CancelablePromise<void> {
    return this.httpRequest.request({
      method: 'DELETE',
      url: '/api/v1/artifacts/{artifact_id}/tags/{tag_id}',
      path: {
        artifact_id: artifactId,
        tag_id: tagId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
}
