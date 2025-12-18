/**
 * Tags API service functions
 */
export interface Tag {
  id: string;
  name: string;
  slug: string;
  color?: string;
  created_at: string;
  updated_at: string;
  artifact_count?: number;
}

export interface TagCreateRequest {
  name: string;
  slug: string;
  color?: string;
}

export interface TagUpdateRequest {
  name?: string;
  slug?: string;
  color?: string;
}

export interface TagListResponse {
  items: Tag[];
  page_info: {
    has_next: boolean;
    next_cursor?: string;
    total?: number;
  };
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Build API URL with versioned path
 */
function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

/**
 * Fetch all tags with pagination
 */
export async function fetchTags(limit?: number, after?: string): Promise<TagListResponse> {
  const params = new URLSearchParams();
  if (limit) params.set('limit', limit.toString());
  if (after) params.set('after', after);

  const url = buildUrl(`/tags${params.toString() ? `?${params.toString()}` : ''}`);
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch tags: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Search tags by query string
 */
export async function searchTags(query: string, limit?: number): Promise<Tag[]> {
  const params = new URLSearchParams({ q: query });
  if (limit) params.set('limit', limit.toString());

  const response = await fetch(buildUrl(`/tags/search?${params.toString()}`));
  if (!response.ok) {
    throw new Error(`Failed to search tags: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Create new tag
 */
export async function createTag(data: TagCreateRequest): Promise<Tag> {
  const response = await fetch(buildUrl('/tags'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to create tag: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Update existing tag
 */
export async function updateTag(id: string, data: TagUpdateRequest): Promise<Tag> {
  const response = await fetch(buildUrl(`/tags/${id}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to update tag: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Delete tag
 */
export async function deleteTag(id: string): Promise<void> {
  const response = await fetch(buildUrl(`/tags/${id}`), {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to delete tag: ${response.statusText}`);
  }
}

/**
 * Get all tags for an artifact
 */
export async function getArtifactTags(artifactId: string): Promise<Tag[]> {
  const response = await fetch(buildUrl(`/artifacts/${artifactId}/tags`));
  if (!response.ok) {
    throw new Error(`Failed to get artifact tags: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Add tag to artifact
 */
export async function addTagToArtifact(artifactId: string, tagId: string): Promise<void> {
  const response = await fetch(buildUrl(`/artifacts/${artifactId}/tags/${tagId}`), {
    method: 'POST',
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to add tag to artifact: ${response.statusText}`);
  }
}

/**
 * Remove tag from artifact
 */
export async function removeTagFromArtifact(artifactId: string, tagId: string): Promise<void> {
  const response = await fetch(buildUrl(`/artifacts/${artifactId}/tags/${tagId}`), {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to remove tag from artifact: ${response.statusText}`);
  }
}
