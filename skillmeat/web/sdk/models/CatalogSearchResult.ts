/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Individual search result from cross-source catalog search.
 *
 * Includes artifact metadata and source context (owner/repo) for display
 * and navigation purposes.
 */
export type CatalogSearchResult = {
  /**
   * Unique catalog entry identifier
   */
  id: string;
  /**
   * Artifact name
   */
  name: string;
  /**
   * Type of artifact
   */
  artifact_type: 'skill' | 'command' | 'agent' | 'mcp' | 'mcp_server' | 'hook';
  /**
   * Artifact title from frontmatter
   */
  title?: string | null;
  /**
   * Artifact description from frontmatter
   */
  description?: string | null;
  /**
   * Confidence score of detection (0-100)
   */
  confidence_score: number;
  /**
   * GitHub repository owner/organization
   */
  source_owner: string;
  /**
   * GitHub repository name
   */
  source_repo: string;
  /**
   * ID of the source this artifact belongs to
   */
  source_id: string;
  /**
   * Path to artifact within repository
   */
  path: string;
  /**
   * Full URL to artifact in source repository
   */
  upstream_url?: string | null;
  /**
   * Lifecycle status of the catalog entry
   */
  status: 'new' | 'updated' | 'removed' | 'imported' | 'excluded';
  /**
   * Tags from frontmatter for filtering
   */
  search_tags?: Array<string> | null;
  /**
   * Highlighted title snippet with <mark> tags around matched terms (FTS5 search only)
   */
  title_snippet?: string | null;
  /**
   * Highlighted description snippet with <mark> tags around matched terms (FTS5 search only)
   */
  description_snippet?: string | null;
  /**
   * True if this result matched from deep-indexed content rather than title/description metadata. Deep matches come from full artifact file content.
   */
  deep_match?: boolean;
  /**
   * Relative file path where the search match was found. Only populated for deep index matches (when deep_match=True).
   */
  matched_file?: string | null;
};
