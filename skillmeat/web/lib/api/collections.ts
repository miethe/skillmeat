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
  const response = await fetch(buildUrl('/collections'));
  if (!response.ok) {
    throw new Error(`Failed to fetch collections: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch single collection by ID
 */
export async function fetchCollection(id: string): Promise<Collection> {
  const response = await fetch(buildUrl(`/collections/${id}`));
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
  const response = await fetch(buildUrl(`/collections/${id}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error(`Failed to update collection: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Delete collection
 */
export async function deleteCollection(id: string): Promise<void> {
  const response = await fetch(buildUrl(`/collections/${id}`), {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to delete collection: ${response.statusText}`);
  }
}

/**
 * Add artifact to collection
 * @param collectionId - Collection ID
 * @param artifactId - Artifact ID to add
 * @param data - Optional metadata for the artifact link
 */
export async function addArtifactToCollection(
  collectionId: string,
  artifactId: string,
  data?: Record<string, unknown>
): Promise<{ artifact_id: string; collection_id: string; added_at: string }> {
  const response = await fetch(buildUrl(`/collections/${collectionId}/artifacts/${artifactId}`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data || {}),
  });
  if (!response.ok) {
    throw new Error(`Failed to add artifact to collection: ${response.statusText}`);
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
  const response = await fetch(buildUrl(`/collections/${collectionId}/artifacts/${artifactId}`), {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to remove artifact from collection: ${response.statusText}`);
  }
}

/**
 * Copy artifact to another collection
 * @param sourceCollectionId - Source collection ID
 * @param artifactId - Artifact ID to copy
 * @param data - Target collection information
 */
export async function copyArtifactToCollection(
  sourceCollectionId: string,
  artifactId: string,
  data: { target_collection_id: string }
): Promise<{ artifact_id: string; collection_id: string; added_at: string }> {
  const response = await fetch(
    buildUrl(`/collections/${sourceCollectionId}/artifacts/${artifactId}/copy`),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to copy artifact: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Move artifact to another collection
 * @param sourceCollectionId - Source collection ID
 * @param artifactId - Artifact ID to move
 * @param data - Target collection information
 */
export async function moveArtifactToCollection(
  sourceCollectionId: string,
  artifactId: string,
  data: { target_collection_id: string }
): Promise<{ artifact_id: string; collection_id: string; added_at: string }> {
  const response = await fetch(
    buildUrl(`/collections/${sourceCollectionId}/artifacts/${artifactId}/move`),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to move artifact: ${response.statusText}`);
  }
  return response.json();
}
