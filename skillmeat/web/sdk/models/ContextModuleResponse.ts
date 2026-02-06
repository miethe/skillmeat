/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response body for a single context module.
 *
 * Attributes:
 * id: Unique module identifier.
 * project_id: Project this module belongs to.
 * name: Human-readable module name.
 * description: Module purpose description.
 * selectors: Selector criteria dict (parsed from JSON).
 * priority: Module priority for ordering.
 * content_hash: SHA-256 hash for change detection.
 * created_at: ISO 8601 creation timestamp.
 * updated_at: ISO 8601 last-update timestamp.
 * memory_items: Associated memory items (only when include_items=true).
 */
export type ContextModuleResponse = {
  id: string;
  project_id: string;
  name: string;
  description?: string | null;
  selectors?: Record<string, any> | null;
  priority?: number;
  content_hash?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  memory_items?: null;
};
