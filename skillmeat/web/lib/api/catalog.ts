/**
 * Catalog Files API service functions
 *
 * Functions for fetching file trees and file content from marketplace catalog artifacts.
 * Uses the marketplace sources API endpoints.
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
 * File entry in the file tree
 */
export interface FileTreeEntry {
  /** Relative path within the artifact */
  path: string;
  /** Entry type: 'file' for files, 'tree' for directories */
  type: 'file' | 'tree';
  /** File size in bytes (only for files) */
  size?: number;
}

/**
 * Response from the file tree endpoint
 */
export interface FileTreeResponse {
  /** List of files and directories */
  files: FileTreeEntry[];
  /** Whether the response was served from cache */
  cached: boolean;
  /** Age of cached data in seconds (if cached) */
  cache_age_seconds?: number;
}

/**
 * Response from the file content endpoint
 */
export interface FileContentResponse {
  /** File content (decoded from base64 by backend) */
  content: string;
  /** Content encoding (typically 'utf-8' after decoding) */
  encoding: string;
  /** File size in bytes */
  size: number;
  /** Git blob SHA for the file */
  sha: string;
  /** Whether content was truncated due to size limits */
  truncated?: boolean;
  /** Original file size in bytes (present when truncated) */
  original_size?: number;
  /** Whether the response was served from cache */
  cached: boolean;
  /** Age of cached data in seconds (if cached) */
  cache_age_seconds?: number;
}

/**
 * Fetch file tree for a catalog artifact
 *
 * @param sourceId - Marketplace source ID
 * @param artifactPath - Path to the artifact within the repository
 * @returns File tree response with list of files and directories
 *
 * @example
 * ```typescript
 * const tree = await fetchCatalogFileTree(1, 'skills/canvas-design');
 * tree.files.forEach(entry => {
 *   console.log(`${entry.type}: ${entry.path}`);
 * });
 * ```
 */
export async function fetchCatalogFileTree(
  sourceId: number,
  artifactPath: string
): Promise<FileTreeResponse> {
  // Encode the artifact path for URL safety
  const encodedPath = encodeURIComponent(artifactPath);
  const response = await fetch(
    buildUrl(`/marketplace/sources/${sourceId}/artifacts/${encodedPath}/files`)
  );

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to fetch file tree: ${response.statusText}`
    );
  }

  return response.json();
}

/**
 * Fetch content of a specific file from a catalog artifact
 *
 * @param sourceId - Marketplace source ID
 * @param artifactPath - Path to the artifact within the repository
 * @param filePath - Path to the file within the artifact
 * @returns File content response with decoded content
 *
 * @example
 * ```typescript
 * const content = await fetchCatalogFileContent(1, 'skills/canvas-design', 'skill.md');
 * console.log(content.content);
 * ```
 */
export async function fetchCatalogFileContent(
  sourceId: number,
  artifactPath: string,
  filePath: string
): Promise<FileContentResponse> {
  // Encode both paths for URL safety
  const encodedArtifactPath = encodeURIComponent(artifactPath);
  const encodedFilePath = encodeURIComponent(filePath);
  const response = await fetch(
    buildUrl(
      `/marketplace/sources/${sourceId}/artifacts/${encodedArtifactPath}/files/${encodedFilePath}`
    )
  );

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to fetch file content: ${response.statusText}`
    );
  }

  return response.json();
}
