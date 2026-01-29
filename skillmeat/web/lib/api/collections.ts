/**
 * Collection API service functions
 */
import type {
  Collection,
  CreateCollectionRequest,
  UpdateCollectionRequest,
} from '@/types/collections';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Build API URL with versioned path
 */
function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

/**
 * Fetch all collections
 */
export async function fetchCollections(): Promise<Collection[]> {
  const response = await fetch(buildUrl('/user-collections'));
  if (!response.ok) {
    throw new Error(`Failed to fetch collections: ${response.statusText}`);
  }
  const data = await response.json();
  // Handle paginated response - backend returns { items: [], page_info: {} }
  return data.items || data;
}

/**
 * Fetch single collection by ID
 */
export async function fetchCollection(id: string): Promise<Collection> {
  const response = await fetch(buildUrl(`/user-collections/${id}`));
  if (!response.ok) {
    throw new Error(`Failed to fetch collection: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Create new collection
 */
export async function createCollection(data: CreateCollectionRequest): Promise<Collection> {
  const response = await fetch(buildUrl('/user-collections'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to create collection: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Update existing collection
 */
export async function updateCollection(
  id: string,
  data: UpdateCollectionRequest
): Promise<Collection> {
  const response = await fetch(buildUrl(`/user-collections/${id}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to update collection: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Delete collection
 */
export async function deleteCollection(id: string): Promise<void> {
  const response = await fetch(buildUrl(`/user-collections/${id}`), {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to delete collection: ${response.statusText}`);
  }
}

/**
 * Add artifact to collection
 * @param collectionId - Collection ID
 * @param artifactId - Artifact ID to add
 * @param _data - Optional metadata (kept for backward compatibility but unused)
 */
export async function addArtifactToCollection(
  collectionId: string,
  artifactId: string,
  _data?: Record<string, unknown>
): Promise<{
  collection_id: string;
  added_count: number;
  already_present_count: number;
  total_artifacts: number;
}> {
  const response = await fetch(buildUrl(`/user-collections/${collectionId}/artifacts`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ artifact_ids: [artifactId] }),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to add artifact to collection: ${response.statusText}`
    );
  }
  return response.json();
}

/**
 * Remove artifact from collection
 */
export async function removeArtifactFromCollection(
  collectionId: string,
  artifactId: string
): Promise<void> {
  const response = await fetch(
    buildUrl(`/user-collections/${encodeURIComponent(collectionId)}/artifacts/${encodeURIComponent(artifactId)}`),
    {
      method: 'DELETE',
    }
  );
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to remove artifact from collection: ${response.statusText}`
    );
  }
}

/**
 * Copy artifact to another collection
 * @param _sourceCollectionId - Source collection ID (unused)
 * @param _artifactId - Artifact ID to copy (unused)
 * @param data - Target collection information (unused)
 * @deprecated Not yet implemented - use addArtifactToCollection on target collection instead
 */
export async function copyArtifactToCollection(
  _sourceCollectionId: string,
  _artifactId: string,
  _data: { target_collection_id: string }
): Promise<{ artifact_id: string; collection_id: string; added_at: string }> {
  // TODO: Backend endpoint not implemented. As workaround, use addArtifactToCollection
  // on the target collection directly
  throw new Error(
    'Copy artifact not implemented. Use addArtifactToCollection on target collection.'
  );
}

/**
 * Move artifact to another collection
 * @param _sourceCollectionId - Source collection ID (unused)
 * @param _artifactId - Artifact ID to move (unused)
 * @param data - Target collection information (unused)
 * @deprecated Not yet implemented - use addArtifactToCollection + removeArtifactFromCollection instead
 */
export async function moveArtifactToCollection(
  _sourceCollectionId: string,
  _artifactId: string,
  _data: { target_collection_id: string }
): Promise<{ artifact_id: string; collection_id: string; added_at: string }> {
  // TODO: Backend endpoint not implemented. As workaround, add to target and remove from source
  throw new Error('Move artifact not implemented. Use add + remove as workaround.');
}

/**
 * Response type for paginated collection artifacts
 */
export interface CollectionArtifactsPaginatedResponse {
  items: Array<{
    name: string;
    type: string;
    version?: string | null;
    source: string;
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
 * Fetch paginated artifacts in a collection
 *
 * Used for infinite scroll implementation. Returns cursor-based pagination info.
 *
 * @param collectionId - Collection ID to fetch artifacts from
 * @param options - Pagination and filter options
 * @returns Paginated response with items and page_info
 *
 * @example
 * ```ts
 * const page1 = await fetchCollectionArtifactsPaginated('col-123', { limit: 20 });
 * if (page1.page_info.has_next_page) {
 *   const page2 = await fetchCollectionArtifactsPaginated('col-123', {
 *     limit: 20,
 *     after: page1.page_info.end_cursor
 *   });
 * }
 * ```
 */
export async function fetchCollectionArtifactsPaginated(
  collectionId: string,
  options?: {
    limit?: number;
    after?: string;
    artifact_type?: string;
  }
): Promise<CollectionArtifactsPaginatedResponse> {
  const params = new URLSearchParams();
  if (options?.limit) params.set('limit', options.limit.toString());
  if (options?.after) params.set('after', options.after);
  if (options?.artifact_type) params.set('artifact_type', options.artifact_type);

  const queryString = params.toString();
  const path = queryString
    ? `/user-collections/${collectionId}/artifacts?${queryString}`
    : `/user-collections/${collectionId}/artifacts`;

  const response = await fetch(buildUrl(path));
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch artifacts: ${response.statusText}`);
  }
  return response.json();
}
