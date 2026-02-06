/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CatalogSearchResponse } from '../models/CatalogSearchResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';
export class MarketplaceCatalogService {
  constructor(public readonly httpRequest: BaseHttpRequest) {}
  /**
   * Search artifacts across all marketplace sources
   * Search for artifacts across all configured marketplace sources using text matching
   * and various filters. Results are ordered by confidence score descending.
   *
   * **Text Search**: The `q` parameter performs full-text search (FTS5) against:
   * - Artifact name
   * - Title (from frontmatter)
   * - Description (from frontmatter)
   * - Search tags (from frontmatter)
   * - Deep-indexed content (full artifact file text, when available)
   *
   * Matches in title/description rank higher than deep-indexed content matches.
   * Results include `deep_match=true` and `matched_file` when a match came from
   * deep-indexed content rather than the artifact metadata.
   *
   * **Filtering Options**:
   * - `type`: Filter by artifact type (skill, command, agent, etc.)
   * - `source_id`: Limit search to a specific source
   * - `min_confidence`: Only return entries with confidence >= this value
   * - `tags`: Comma-separated list of tags to filter by (OR logic)
   *
   * **Pagination**: Uses cursor-based pagination for efficient traversal of large result sets.
   * The `cursor` value from a previous response can be used to fetch the next page.
   * @returns CatalogSearchResponse Successfully retrieved search results
   * @throws ApiError
   */
  public searchCatalogApiV1MarketplaceCatalogSearchGet({
    q,
    type,
    sourceId,
    minConfidence,
    tags,
    limit = 50,
    cursor,
  }: {
    /**
     * Search query for full-text matching on name, title, description, tags, and deep-indexed content
     */
    q?: string | null;
    /**
     * Filter by artifact type
     */
    type?: string | null;
    /**
     * Limit search to a specific source ID
     */
    sourceId?: string | null;
    /**
     * Minimum confidence score (0-100)
     */
    minConfidence?: number;
    /**
     * Comma-separated list of tags to filter by (OR logic)
     */
    tags?: string | null;
    /**
     * Maximum number of results per page
     */
    limit?: number;
    /**
     * Pagination cursor from previous response
     */
    cursor?: string | null;
  }): CancelablePromise<CatalogSearchResponse> {
    return this.httpRequest.request({
      method: 'GET',
      url: '/api/v1/marketplace/catalog/search',
      query: {
        q: q,
        type: type,
        source_id: sourceId,
        min_confidence: minConfidence,
        tags: tags,
        limit: limit,
        cursor: cursor,
      },
      errors: {
        422: `Validation Error`,
        500: `Database operation failed`,
      },
    });
  }
}
