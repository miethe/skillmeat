/**
 * Project template type definitions
 *
 * Templates are reusable collections of context entities that can be deployed
 * together to initialize Claude Code project structures. They support variable
 * substitution for customization and selective entity deployment.
 */

/**
 * Template entity within a project template
 *
 * Represents a context entity that is part of a template, with deployment
 * metadata like order and required status.
 */
export interface TemplateEntity {
  /** Artifact ID of the context entity */
  artifact_id: string;
  /** Name of the entity */
  name: string;
  /** Entity type (project_config, spec_file, rule_file, etc.) */
  type: string;
  /** Path pattern where this entity will be deployed */
  path_pattern: string | null;
  /** Deployment order (lower numbers deployed first) */
  deploy_order: number;
  /** Whether this entity is required for the template */
  required: boolean;
}

/**
 * Project template
 *
 * A reusable collection of context entities with deployment configuration
 */
export interface ProjectTemplate {
  /** Unique identifier for the template */
  id: string;
  /** Template name */
  name: string;
  /** Optional description */
  description: string | null;
  /** Number of entities in the template */
  entity_count: number;
  /** Optional source collection ID */
  collection_id: string | null;
  /** List of template entities (included in detail view) */
  entities: TemplateEntity[];
  /** Timestamp when template was created (ISO 8601) */
  created_at: string;
  /** Timestamp when template was last updated (ISO 8601) */
  updated_at: string;
}

/**
 * Simplified template for list views (card display)
 */
export interface TemplateSummary {
  /** Unique identifier for the template */
  id: string;
  /** Template name */
  name: string;
  /** Optional description */
  description: string | null;
  /** Number of entities in the template */
  entity_count: number;
  /** Optional source collection ID */
  collection_id: string | null;
}

/**
 * Request to create a new project template
 */
export interface CreateTemplateRequest {
  /** Template name (1-255 characters) */
  name: string;
  /** Optional description */
  description?: string;
  /** List of entity configurations */
  entities: {
    /** Artifact ID of the context entity */
    artifact_id: string;
    /** Deployment order (lower numbers deployed first) */
    deploy_order: number;
    /** Whether this entity is required */
    required: boolean;
  }[];
  /** Optional source collection ID */
  collection_id?: string;
}

/**
 * Request to update an existing project template
 */
export interface UpdateTemplateRequest {
  /** Updated name */
  name?: string;
  /** Updated description */
  description?: string;
  /** Updated entity list */
  entities?: {
    artifact_id: string;
    deploy_order: number;
    required: boolean;
  }[];
  /** Updated collection ID */
  collection_id?: string;
}

/**
 * Request to deploy a template to a project
 */
export interface DeployTemplateRequest {
  /** Target project path */
  project_path: string;
  /** Optional list of artifact IDs to deploy (deploys all if not provided) */
  artifact_ids?: string[];
  /** Optional variable substitutions for template content */
  variables?: Record<string, string>;
}

/**
 * Response from template deployment
 */
export interface DeployTemplateResponse {
  /** Template ID that was deployed */
  template_id: string;
  /** Project path where template was deployed */
  project_path: string;
  /** List of successfully deployed artifact IDs */
  deployed_artifacts: string[];
  /** Number of entities deployed */
  deployed_count: number;
  /** Optional message */
  message?: string;
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
 * Paginated template list response
 */
export interface TemplateListResponse {
  /** List of templates */
  items: ProjectTemplate[];
  /** Cursor-based pagination information */
  page_info: PageInfo;
}

/**
 * Filter options for template queries
 */
export interface TemplateFilters {
  /** Search query for name/description */
  search?: string;
  /** Filter by collection ID */
  collection_id?: string;
  /** Maximum number of items to return */
  limit?: number;
  /** Cursor for pagination (start after this cursor) */
  after?: string;
}
