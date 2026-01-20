/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for a GitHub repository source.
 *
 * Contains source metadata, scan status, and artifact statistics.
 */
export type SourceResponse = {
  /**
   * Unique identifier for the source
   */
  id: string;
  /**
   * Full GitHub repository URL
   */
  repo_url: string;
  /**
   * Repository owner username
   */
  owner: string;
  /**
   * Repository name
   */
  repo_name: string;
  /**
   * Branch, tag, or SHA being tracked
   */
  ref: string;
  /**
   * Subdirectory path for scanning
   */
  root_hint?: string | null;
  /**
   * Trust level for artifacts from this source
   */
  trust_level: string;
  /**
   * Repository visibility (public/private)
   */
  visibility: string;
  /**
   * Current scan status
   */
  scan_status: 'pending' | 'scanning' | 'success' | 'error';
  /**
   * Number of artifacts detected in this source
   */
  artifact_count: number;
  /**
   * Timestamp of last successful scan
   */
  last_sync_at?: string | null;
  /**
   * Last error message if scan failed
   */
  last_error?: string | null;
  /**
   * Timestamp when source was added
   */
  created_at: string;
  /**
   * Timestamp when source was last modified
   */
  updated_at: string;
  /**
   * User-provided description for this source
   */
  description?: string | null;
  /**
   * Internal notes/documentation for this source
   */
  notes?: string | null;
  /**
   * Whether frontmatter detection is enabled for this source
   */
  enable_frontmatter_detection: boolean;
  /**
   * Manual directory-to-type mappings (directory path → artifact_type). None if no manual mapping configured.
   */
  manual_map?: Record<string, string> | null;
  /**
   * Repository description from GitHub API
   */
  repo_description?: string | null;
  /**
   * README content from GitHub (up to 50KB)
   */
  repo_readme?: string | null;
  /**
   * Source tags for categorization
   */
  tags?: Array<string>;
  /**
   * Artifact counts by type (e.g., {'skill': 5, 'command': 3})
   */
  counts_by_type?: Record<string, number>;
};
