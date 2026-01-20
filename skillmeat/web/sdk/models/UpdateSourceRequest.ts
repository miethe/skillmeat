/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request to update a GitHub repository source.
 *
 * All fields are optional - only provided fields will be updated.
 * Uses PATCH semantics for partial updates.
 */
export type UpdateSourceRequest = {
  /**
   * Branch, tag, or SHA to scan
   */
  ref?: string | null;
  /**
   * Subdirectory path within repository to start scanning
   */
  root_hint?: string | null;
  /**
   * Manual directory-to-type mappings (directory path → artifact_type). Example: {"path/to/dir": "skill", "other/path": "command"}
   */
  manual_map?: Record<string, string> | null;
  /**
   * Trust level for artifacts from this source
   */
  trust_level?: 'untrusted' | 'basic' | 'verified' | 'official' | null;
  /**
   * User-provided description for this source (max 500 chars)
   */
  description?: string | null;
  /**
   * Internal notes/documentation for this source (max 2000 chars)
   */
  notes?: string | null;
  /**
   * Enable parsing markdown frontmatter for artifact type hints
   */
  enable_frontmatter_detection?: boolean | null;
  /**
   * Fetch repository description from GitHub
   */
  import_repo_description?: boolean | null;
  /**
   * Fetch README content from GitHub
   */
  import_repo_readme?: boolean | null;
  /**
   * Tags to apply to source (max 20)
   */
  tags?: Array<string> | null;
};
