/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for updating a project.
 */
export type ProjectUpdateRequest = {
  /**
   * New project name (1-100 characters, letters, numbers, hyphens, underscores only)
   */
  name?: string | null;
  /**
   * New project description
   */
  description?: string | null;
};
