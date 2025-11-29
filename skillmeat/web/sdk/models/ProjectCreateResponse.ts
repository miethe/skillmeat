/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response for project creation.
 */
export type ProjectCreateResponse = {
  /**
   * Base64-encoded project path (unique identifier)
   */
  id: string;
  /**
   * Absolute filesystem path to project
   */
  path: string;
  /**
   * Project name
   */
  name: string;
  /**
   * Project description
   */
  description?: string | null;
  /**
   * Project creation timestamp
   */
  created_at: string;
};
