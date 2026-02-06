/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request body for creating a new context module.
 *
 * Attributes:
 * name: Human-readable module name (1-255 characters).
 * description: Optional description of the module's purpose.
 * selectors: Optional selector criteria dict. Allowed keys:
 * memory_types (list), min_confidence (float),
 * file_patterns (list), workflow_stages (list).
 * priority: Module priority for ordering (0-100, default 5).
 */
export type ContextModuleCreateRequest = {
  name: string;
  description?: string | null;
  selectors?: Record<string, any> | null;
  priority?: number;
};
