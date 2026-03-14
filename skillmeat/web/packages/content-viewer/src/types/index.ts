/**
 * @skillmeat/content-viewer — Shared Type Definitions
 *
 * Canonical type definitions for file tree and content viewer APIs.
 * These types are intentionally free of any `@/` path imports so the
 * package can be consumed outside the main Next.js application.
 */

// ============================================================
// File Tree Types (from web/types/files.ts)
// ============================================================

/**
 * A node in the file tree — either a file or a directory.
 * `size` is present for file nodes; `children` is present for directory nodes.
 */
export interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;
  children?: FileNode[];
}

// ============================================================
// Catalog API Response Types (from web/lib/api/catalog.ts)
// ============================================================

/**
 * A single entry in a catalog artifact's file tree.
 * `type` uses GitHub tree conventions: 'file' | 'tree' (directory).
 */
export interface FileTreeEntry {
  /** Relative path within the artifact */
  path: string;
  /** Entry type: 'file' for files, 'tree' for directories */
  type: 'file' | 'tree';
  /** File size in bytes (only present for file entries) */
  size?: number;
}

/**
 * Response from the marketplace source artifact file-tree endpoint.
 */
export interface FileTreeResponse {
  /** List of files and directories in the artifact */
  entries: FileTreeEntry[];
  /** Whether the response was served from cache */
  cached: boolean;
  /** Age of cached data in seconds (only present when cached) */
  cache_age_seconds?: number;
}

/**
 * Response from the marketplace source artifact file-content endpoint.
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
  /** Age of cached data in seconds (only present when cached) */
  cache_age_seconds?: number;
}
