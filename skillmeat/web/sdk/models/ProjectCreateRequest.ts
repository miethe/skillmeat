/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for creating a project.
 */
export type ProjectCreateRequest = {
  /**
   * Project name (1-100 characters, letters, numbers, hyphens, underscores only)
   */
  name: string;
  /**
   * Absolute path to project directory
   */
  path: string;
  /**
   * Project description
   */
  description?: string | null;
};
