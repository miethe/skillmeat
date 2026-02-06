/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request body for updating an existing context module.
 *
 * All fields are optional. Only provided fields will be updated.
 *
 * Attributes:
 * name: Updated module name (1-255 characters).
 * description: Updated description.
 * selectors: Updated selector criteria dict.
 * priority: Updated priority (0-100).
 */
export type ContextModuleUpdateRequest = {
  name?: string | null;
  description?: string | null;
  selectors?: Record<string, any> | null;
  priority?: number | null;
};
