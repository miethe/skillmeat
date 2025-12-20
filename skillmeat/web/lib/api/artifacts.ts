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
export async function deleteArtifactFromCollection(
  artifactId: string
): Promise<void> {
  const response = await fetch(buildUrl(`/artifacts/${artifactId}`), {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to delete artifact: ${response.statusText}`);
  }
  // DELETE typically returns 204 No Content (no body)
}
