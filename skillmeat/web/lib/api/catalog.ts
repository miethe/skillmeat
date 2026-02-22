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
 * File extensions that indicate a path is a single-file artifact (not a directory).
 * Used for defensive URL construction when artifact.path is already a file path.
 */
const FILE_EXTENSIONS = ['.md', '.py', '.yaml', '.yml', '.json', '.toml', '.txt'];

/**
 * Detect whether a given artifact path is a file path rather than a directory.
 * Returns true if the path ends with a known file extension.
 */
function isFilePath(artifactPath: string): boolean {
  const lower = artifactPath.toLowerCase();
  return FILE_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

/**
 * Derive the effective artifact directory and file path from an artifact path.
 *
 * For directory-based artifacts (e.g., "skills/canvas-design"), returns the
 * path as-is with null filePath — callers supply their own filePath.
 *
 * For file-path artifacts (e.g., "skills/my-skill/commands/add-animation.md"),
 * splits the path into:
 *   - artifactDir: the parent directory ("skills/my-skill/commands")
 *   - derivedFilePath: the filename ("add-animation.md")
 *
 * This prevents double-path URLs like:
 *   .../artifacts/skills/my-skill/commands/add-animation.md/files/add-animation.md
 */
function resolveArtifactPaths(artifactPath: string): {
  artifactDir: string;
  derivedFilePath: string | null;
} {
  if (!isFilePath(artifactPath)) {
    return { artifactDir: artifactPath, derivedFilePath: null };
  }
  const lastSlash = artifactPath.lastIndexOf('/');
  if (lastSlash < 0) {
    // Root-level file: use empty dir and the file as derived path
    return { artifactDir: '', derivedFilePath: artifactPath };
  }
  return {
    artifactDir: artifactPath.substring(0, lastSlash),
    derivedFilePath: artifactPath.substring(lastSlash + 1),
  };
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
  entries: FileTreeEntry[];
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
 * const tree = await fetchCatalogFileTree('source-uuid-123', 'skills/canvas-design');
 * tree.entries.forEach(entry => {
 *   console.log(`${entry.type}: ${entry.path}`);
 * });
 * ```
 */
export async function fetchCatalogFileTree(
  sourceId: string,
  artifactPath: string
): Promise<FileTreeResponse> {
  // Normalize "." (repository root) to empty string to prevent URL issues
  // "." gets normalized away in URLs: "/artifacts/./files" -> "/artifacts/files"
  // which would match the wrong route
  const rawPath = artifactPath === '.' ? '' : artifactPath;

  // Defensive: when artifactPath is already a file path (e.g., "skills/foo/commands/bar.md"),
  // derive the parent directory so the /files listing is for the containing directory.
  const { artifactDir } = resolveArtifactPaths(rawPath);

  // Encode the artifact path for URL safety
  const encodedPath = encodeURIComponent(artifactDir);
  const response = await fetch(
    buildUrl(`/marketplace/sources/${sourceId}/artifacts/${encodedPath}/files`)
  );

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch file tree: ${response.statusText}`);
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
 * const content = await fetchCatalogFileContent('source-uuid-123', 'skills/canvas-design', 'skill.md');
 * console.log(content.content);
 * ```
 */
export async function fetchCatalogFileContent(
  sourceId: string,
  artifactPath: string,
  filePath: string
): Promise<FileContentResponse> {
  // Normalize "." (repository root) to empty string to prevent URL issues
  // "." gets normalized away in URLs: "/artifacts/./files" -> "/artifacts/files"
  // which would match the wrong route
  const rawPath = artifactPath === '.' ? '' : artifactPath;

  // Defensive: when artifactPath is already a file path (e.g., "skills/foo/commands/bar.md"),
  // use the parent directory as the artifact path and the filename as the file path.
  // This prevents double-path URLs like:
  //   .../artifacts/skills/.../bar.md/files/bar.md
  const { artifactDir, derivedFilePath } = resolveArtifactPaths(rawPath);
  const effectiveFilePath = derivedFilePath ?? filePath;

  // Encode both paths for URL safety
  const encodedArtifactPath = encodeURIComponent(artifactDir);
  const encodedFilePath = encodeURIComponent(effectiveFilePath);
  const response = await fetch(
    buildUrl(
      `/marketplace/sources/${sourceId}/artifacts/${encodedArtifactPath}/files/${encodedFilePath}`
    )
  );

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch file content: ${response.statusText}`);
  }

  return response.json();
}
