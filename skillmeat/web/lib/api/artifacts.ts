/**
 * Artifact API service functions
 *
 * Provides functions for managing artifacts in the collection
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Build API URL with versioned path
 */
function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

/**
 * Delete artifact from collection
 *
 * Removes an artifact from the collection permanently
 *
 * @param artifactId - Artifact ID to delete
 * @throws Error if deletion fails
 */
export async function deleteArtifactFromCollection(artifactId: string): Promise<void> {
  const response = await fetch(buildUrl(`/artifacts/${encodeURIComponent(artifactId)}`), {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to delete artifact: ${response.statusText}`);
  }
  // DELETE typically returns 204 No Content (no body)
}

/**
 * Response type for paginated artifacts list
 */
export interface ArtifactsPaginatedResponse {
  items: Array<{
    id: string;
    name: string;
    type: string;
    source: string;
    origin?: string;
    origin_source?: string | null;
    version?: string;
    tags?: string[];
    aliases?: string[];
    metadata?: {
      title?: string;
      description?: string;
      license?: string;
      author?: string;
      version?: string;
      tags?: string[];
    };
    target_platforms?: string[] | null;
    upstream?: {
      tracking_enabled: boolean;
      current_sha?: string;
      upstream_sha?: string;
      update_available: boolean;
      has_local_modifications: boolean;
    };
    added: string;
    updated: string;
    collection?: {
      id: string;
      name: string;
    };
    collections?: Array<{
      id: string;
      name: string;
      artifact_count?: number;
    }>;
  }>;
  page_info: {
    has_next_page: boolean;
    has_previous_page: boolean;
    start_cursor: string | null;
    end_cursor: string | null;
    total_count: number;
  };
}

/**
 * Fetch paginated artifacts from collection
 *
 * Used for infinite scroll implementation in "All Collections" view.
 * Returns cursor-based pagination info.
 *
 * @param options - Pagination and filter options
 * @returns Paginated response with items and page_info
 *
 * @example
 * ```ts
 * const page1 = await fetchArtifactsPaginated({ limit: 20 });
 * if (page1.page_info.has_next_page) {
 *   const page2 = await fetchArtifactsPaginated({
 *     limit: 20,
 *     after: page1.page_info.end_cursor
 *   });
 * }
 * ```
 */
export async function fetchArtifactsPaginated(options?: {
  limit?: number;
  after?: string;
  artifact_type?: string;
  status?: string;
  scope?: string;
  search?: string;
  tools?: string[];
  import_id?: string;
}): Promise<ArtifactsPaginatedResponse> {
  const params = new URLSearchParams();
  if (options?.limit) params.set('limit', options.limit.toString());
  if (options?.after) params.set('after', options.after);
  if (options?.artifact_type) params.set('artifact_type', options.artifact_type);
  if (options?.status) params.set('status', options.status);
  if (options?.scope) params.set('scope', options.scope);
  if (options?.search) params.set('search', options.search);
  if (options?.tools && options.tools.length > 0) {
    params.set('tools', options.tools.join(','));
  }
  if (options?.import_id) params.set('import_id', options.import_id);

  const queryString = params.toString();
  const path = queryString ? `/artifacts?${queryString}` : '/artifacts';

  const response = await fetch(buildUrl(path));
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch artifacts: ${response.statusText}`);
  }
  return response.json();
}
