/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for creating a new project template.
 *
 * Templates can be created from a collection or by specifying individual
 * entity IDs. They support variable substitution and selective deployment.
 *
 * Examples:
 * >>> # Create template from specific entities
 * >>> request = ProjectTemplateCreateRequest(
 * ...     name="web-fullstack-starter",
 * ...     description="Full-stack web application starter",
 * ...     entity_ids=["ctx_abc123", "ctx_def456"],
 * ... )
 */
export type ProjectTemplateCreateRequest = {
  /**
   * Template name (must be unique)
   */
  name: string;
  /**
   * Template description
   */
  description?: string | null;
  /**
   * Source collection ID (optional, for template from collection)
   */
  collection_id?: string | null;
  /**
   * List of context entity IDs to include in template
   */
  entity_ids: Array<string>;
  /**
   * Default project config entity ID (optional)
   */
  default_project_config_id?: string | null;
};
