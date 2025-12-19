/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CatalogListResponse } from '../models/CatalogListResponse';
import type { CreateSourceRequest } from '../models/CreateSourceRequest';
import type { ImportRequest } from '../models/ImportRequest';
import type { ImportResultDTO } from '../models/ImportResultDTO';
import type { ScanRequest } from '../models/ScanRequest';
import type { ScanResultDTO } from '../models/ScanResultDTO';
import type { SourceListResponse } from '../models/SourceListResponse';
import type { SourceResponse } from '../models/SourceResponse';
import type { UpdateSourceRequest } from '../models/UpdateSourceRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class MarketplaceSourcesService {
    constructor(public readonly httpRequest: BaseHttpRequest) {}
    /**
     * Create new GitHub source
     * Add a new GitHub repository as a marketplace source for artifact scanning.
     *
     * The repository URL must be a valid GitHub URL (https://github.com/owner/repo).
     * After creation, use the /rescan endpoint to trigger the initial scan.
     *
     * Authentication: TODO - Add authentication when multi-user support is implemented.
     * @returns SourceResponse Successful Response
     * @throws ApiError
     */
    public createSourceApiV1MarketplaceSourcesPost({
        requestBody,
    }: {
        requestBody: CreateSourceRequest,
    }): CancelablePromise<SourceResponse> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/marketplace/sources',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List all GitHub sources
     * List all GitHub repository sources with cursor-based pagination.
     *
     * Returns sources ordered by ID for stable pagination. Use the `cursor`
     * parameter from the previous response to fetch the next page.
     *
     * Authentication: TODO - Add authentication when multi-user support is implemented.
     * @returns SourceListResponse Successful Response
     * @throws ApiError
     */
    public listSourcesApiV1MarketplaceSourcesGet({
        limit = 50,
        cursor,
    }: {
        /**
         * Maximum items per page
         */
        limit?: number,
        /**
         * Cursor for next page
         */
        cursor?: (string | null),
    }): CancelablePromise<SourceListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/marketplace/sources',
            query: {
                'limit': limit,
                'cursor': cursor,
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
     * Authentication: TODO - Add authentication when multi-user support is implemented.
     * @returns SourceResponse Successful Response
     * @throws ApiError
     */
    public getSourceApiV1MarketplaceSourcesSourceIdGet({
        sourceId,
    }: {
        sourceId: string,
    }): CancelablePromise<SourceResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/marketplace/sources/{source_id}',
            path: {
                'source_id': sourceId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update source
     * Update a GitHub repository source configuration.
     *
     * Allows updating ref (branch/tag/SHA), root_hint, trust_level, description, and notes.
     * Changes take effect on the next scan.
     *
     * Authentication: TODO - Add authentication when multi-user support is implemented.
     * @returns SourceResponse Successful Response
     * @throws ApiError
     */
    public updateSourceApiV1MarketplaceSourcesSourceIdPatch({
        sourceId,
        requestBody,
    }: {
        sourceId: string,
        requestBody: UpdateSourceRequest,
    }): CancelablePromise<SourceResponse> {
        return this.httpRequest.request({
            method: 'PATCH',
            url: '/api/v1/marketplace/sources/{source_id}',
            path: {
                'source_id': sourceId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
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
        sourceId: string,
    }): CancelablePromise<void> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/api/v1/marketplace/sources/{source_id}',
            path: {
                'source_id': sourceId,
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
     * The scan will:
     * 1. Fetch the repository tree from GitHub
     * 2. Apply heuristic detection to identify artifacts
     * 3. Update the catalog with discovered artifacts
     * 4. Update source metadata (artifact_count, last_sync_at, etc.)
     *
     * Authentication: TODO - Add authentication when multi-user support is implemented.
     * @returns ScanResultDTO Successful Response
     * @throws ApiError
     */
    public rescanSourceApiV1MarketplaceSourcesSourceIdRescanPost({
        sourceId,
        requestBody,
    }: {
        sourceId: string,
        requestBody?: ScanRequest,
    }): CancelablePromise<ScanResultDTO> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/marketplace/sources/{source_id}/rescan',
            path: {
                'source_id': sourceId,
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
     * List all artifacts discovered from a specific source with optional filtering.
     *
     * Supports filtering by:
     * - artifact_type: skill, command, agent, etc.
     * - status: new, updated, removed, imported
     * - min_confidence: Minimum confidence score (0-100)
     *
     * Results are paginated using cursor-based pagination for efficiency.
     *
     * Authentication: TODO - Add authentication when multi-user support is implemented.
     * @returns CatalogListResponse Successful Response
     * @throws ApiError
     */
    public listArtifactsApiV1MarketplaceSourcesSourceIdArtifactsGet({
        sourceId,
        artifactType,
        status,
        minConfidence,
        limit = 50,
        cursor,
    }: {
        sourceId: string,
        /**
         * Filter by artifact type (skill, command, etc.)
         */
        artifactType?: (string | null),
        /**
         * Filter by status (new, updated, removed, imported)
         */
        status?: (string | null),
        /**
         * Minimum confidence score
         */
        minConfidence?: (number | null),
        /**
         * Maximum items per page
         */
        limit?: number,
        /**
         * Cursor for next page
         */
        cursor?: (string | null),
    }): CancelablePromise<CatalogListResponse> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/api/v1/marketplace/sources/{source_id}/artifacts',
            path: {
                'source_id': sourceId,
            },
            query: {
                'artifact_type': artifactType,
                'status': status,
                'min_confidence': minConfidence,
                'limit': limit,
                'cursor': cursor,
            },
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
        sourceId: string,
        requestBody: ImportRequest,
    }): CancelablePromise<ImportResultDTO> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/api/v1/marketplace/sources/{source_id}/import',
            path: {
                'source_id': sourceId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
