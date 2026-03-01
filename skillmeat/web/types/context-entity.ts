/**
 * Context entity type definitions for Claude Code project configuration
 *
 * Context entities represent artifacts with special roles in Claude Code projects:
 * - PROJECT_CONFIG: Configuration files (e.g., .claude/config.toml)
 * - SPEC_FILE: Specification documents (e.g., .claude/specs/*.md)
 * - RULE_FILE: Path-scoped rules (e.g., .claude/rules/web/*.md)
 * - CONTEXT_FILE: Knowledge documents (e.g., .claude/context/*.md)
 * - PROGRESS_TEMPLATE: Progress tracking templates
 *
 * These entities support path-pattern matching for auto-loading and categorization
 * for progressive disclosure patterns.
 */
import { Platform } from './enums';

/**
 * Type of context entity
 *
 * Defines the role and purpose of the context entity within a project.
 * Each type has specific conventions for path patterns and content structure.
 */
export type ContextEntityType =
  | 'project_config'
  | 'spec_file'
  | 'rule_file'
  | 'context_file'
  | 'progress_template';

/**
 * Represents a context entity in the collection
 *
 * Provides complete context entity information including metadata,
 * path pattern, and auto-load settings.
 */
export interface ContextEntity {
  /** Unique identifier for the context entity */
  id: string;
  /** Human-readable name */
  name: string;
  /** Type of context entity */
  entity_type: ContextEntityType;
  /** Path pattern within .claude/ directory */
  path_pattern: string;
  /** Detailed description */
  description?: string;
  /** Category for progressive disclosure (e.g., 'api', 'frontend', 'debugging') */
  category?: string;
  /** Whether to auto-load when path pattern matches edited files */
  auto_load: boolean;
  /** Version identifier (semantic versioning recommended) */
  version?: string;
  /** Optional deployment platform restrictions (undefined means deployable on all platforms) */
  target_platforms?: Platform[];
  /** SHA-256 hash of content (for change detection) */
  content_hash?: string;
  /** IDs of entity categories associated with this entity */
  category_ids?: number[];
  /** Timestamp when entity was created (ISO 8601) */
  created_at: string;
  /** Timestamp when entity was last updated (ISO 8601) */
  updated_at: string;
}

/**
 * Request to create a new context entity
 *
 * Context entities are artifacts with special roles in Claude Code projects.
 * They support path-pattern matching for auto-loading and categorization.
 *
 * Path Pattern Security:
 * - Must start with '.claude/' (enforced via validation)
 * - Cannot contain '..' for path traversal prevention
 *
 * @example
 * ```typescript
 * // Rule file that auto-loads for web path edits
 * const request: CreateContextEntityRequest = {
 *   name: "web-hooks-rules",
 *   entity_type: "rule_file",
 *   content: "# Web Hooks Patterns\n...",
 *   path_pattern: ".claude/rules/web/hooks.md",
 *   category: "web",
 *   auto_load: true
 * };
 * ```
 */
export interface CreateContextEntityRequest {
  /** Human-readable name for the context entity (1-255 characters) */
  name: string;
  /** Type of context entity (determines role and conventions) */
  entity_type: ContextEntityType;
  /** Markdown content of the context entity */
  content: string;
  /** Path pattern within .claude/ directory (must start with '.claude/', no '..') */
  path_pattern: string;
  /** Optional detailed description */
  description?: string;
  /** Category for progressive disclosure (e.g., 'api', 'frontend', 'debugging') */
  category?: string;
  /** Whether to auto-load when path pattern matches edited files (default: false) */
  auto_load?: boolean;
  /** Version identifier (semantic versioning recommended) */
  version?: string;
  /** Optional deployment profile used during profile-aware validation */
  deployment_profile_id?: string;
  /** Optional platform restrictions */
  target_platforms?: Platform[];
  /** Optional list of ContextEntityCategory IDs to associate */
  category_ids?: number[];
}

/**
 * Request to update an existing context entity
 *
 * All fields are optional - only provided fields will be updated.
 * Path pattern validation applies when provided.
 */
export interface UpdateContextEntityRequest {
  /** Updated name (1-255 characters if provided) */
  name?: string;
  /** Updated entity type */
  entity_type?: ContextEntityType;
  /** Updated markdown content */
  content?: string;
  /** Updated path pattern (must start with '.claude/', no '..') */
  path_pattern?: string;
  /** Updated description */
  description?: string;
  /** Updated category */
  category?: string;
  /** Updated auto-load setting */
  auto_load?: boolean;
  /** Updated version */
  version?: string;
  /** Updated deployment profile id */
  deployment_profile_id?: string;
  /** Updated platform restrictions */
  target_platforms?: Platform[];
  /** When provided, replaces all existing category associations */
  category_ids?: number[];
}

/**
 * Filter options for context entity queries
 */
export interface ContextEntityFilters {
  /** Filter by entity type */
  entity_type?: ContextEntityType;
  /** Filter by category */
  category?: string;
  /** Filter by auto-load setting */
  auto_load?: boolean;
  /** Search query for name/description/content */
  search?: string;
  /** Maximum number of items to return */
  limit?: number;
  /** Cursor for pagination (start after this cursor) */
  after?: string;
}

/**
 * Pagination metadata for cursor-based pagination
 */
export interface PageInfo {
  /** Whether there are more items after the current page */
  has_next_page: boolean;
  /** Whether there are items before the current page */
  has_previous_page: boolean;
  /** Cursor pointing to the start of the current page */
  start_cursor: string | null;
  /** Cursor pointing to the end of the current page */
  end_cursor: string | null;
  /** Total number of items (optional, may be expensive to compute) */
  total_count?: number;
}

/**
 * Paginated context entity list response
 *
 * Uses cursor-based pagination for efficient querying.
 */
export interface ContextEntityListResponse {
  /** List of context entities */
  items: ContextEntity[];
  /** Cursor-based pagination information */
  page_info: PageInfo;
}

export interface ContextEntityDeployRequest {
  project_path: string;
  overwrite?: boolean;
  deployment_profile_id?: string;
  all_profiles?: boolean;
  force?: boolean;
}

export interface ContextEntityDeployResponse {
  success: boolean;
  entity_id: string;
  project_path: string;
  deployed_paths: string[];
  deployed_profiles: string[];
  message: string;
}

// ============================================================================
// Entity Type Config Types
// ============================================================================

/**
 * Represents an entity type configuration from the API.
 * Mirrors EntityTypeConfigResponse Pydantic schema.
 */
export interface EntityTypeConfig {
  /** Auto-incrementing integer primary key */
  id: number;
  /** Machine-readable unique identifier (e.g. "skill", "command") */
  slug: string;
  /** Human-readable name shown in the UI */
  display_name: string;
  /** Optional long-form description */
  description?: string;
  /** Optional icon identifier for UI rendering */
  icon?: string;
  /** Default filesystem path prefix (e.g. ".claude/skills") */
  path_prefix?: string;
  /** Frontmatter keys that MUST be present */
  required_frontmatter_keys?: string[];
  /** Frontmatter keys that MAY be present */
  optional_frontmatter_keys?: string[];
  /** Additional validation configuration */
  validation_rules?: Record<string, unknown>;
  /** Default Markdown template used when creating a new entity */
  content_template?: string;
  /** Platform slugs this type applies to. null means all platforms. */
  applicable_platforms: string[] | null;
  /** JSON Schema subset for custom type frontmatter validation. null means no schema validation. */
  frontmatter_schema: Record<string, unknown> | null;
  /** True for the five shipped types; false for user-created types */
  is_builtin: boolean;
  /** Display ordering in the UI (ascending) */
  sort_order: number;
  /** Row creation timestamp (UTC) */
  created_at: string;
  /** Row last-modified timestamp (UTC) */
  updated_at: string;
}

/**
 * Request to create a new entity type configuration.
 * Mirrors EntityTypeConfigCreateRequest Pydantic schema.
 * Slug must match ^[a-z][a-z0-9_]{0,63}$
 */
export interface EntityTypeConfigCreate {
  /** Machine-readable unique identifier — must match ^[a-z][a-z0-9_]{0,63}$ */
  slug: string;
  /** Human-readable display name */
  label: string;
  /** Optional long-form description */
  description?: string;
  /** Optional icon identifier */
  icon?: string;
  /** Default filesystem path prefix */
  path_prefix?: string;
  /** Frontmatter keys that MUST be present */
  required_frontmatter_keys?: string[];
  /** An example path illustrating this entity type */
  example_path?: string;
  /** Default Markdown content template */
  content_template?: string;
  /** Platform slugs this type applies to. Omit or null for all platforms. */
  applicable_platforms?: string[] | null;
  /** JSON Schema subset for custom type frontmatter validation. */
  frontmatter_schema?: Record<string, unknown> | null;
}

/**
 * Request to update an existing entity type configuration.
 * All fields are optional; only supplied fields are updated.
 */
export interface EntityTypeConfigUpdate {
  /** Updated human-readable display name */
  label?: string;
  /** Updated description */
  description?: string;
  /** Updated icon identifier */
  icon?: string;
  /** Updated filesystem path prefix */
  path_prefix?: string;
  /** Updated required frontmatter keys */
  required_frontmatter_keys?: string[];
  /** Updated example path */
  example_path?: string;
  /** Updated content template */
  content_template?: string;
  /** Platform slugs this type applies to. Omit or null for all platforms. */
  applicable_platforms?: string[] | null;
  /** JSON Schema subset for custom type frontmatter validation. */
  frontmatter_schema?: Record<string, unknown> | null;
}
