/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Variable values for template deployment.
 *
 * These variables are substituted into entity content during deployment,
 * allowing customization of generated files.
 *
 * Common Variables:
 * - PROJECT_NAME: Name of the project being initialized
 * - PROJECT_DESCRIPTION: Brief project description
 * - AUTHOR: Project author name
 * - DATE: Current date (defaults to current date if not provided)
 * - ARCHITECTURE_DESCRIPTION: Architecture overview
 */
export type TemplateVariableValue = {
  /**
   * Name of the project
   */
  PROJECT_NAME: string;
  /**
   * Brief description of the project
   */
  PROJECT_DESCRIPTION?: string | null;
  /**
   * Project author name
   */
  AUTHOR?: string | null;
  /**
   * Date string (defaults to current date if not provided)
   */
  DATE?: string | null;
  /**
   * High-level architecture description
   */
  ARCHITECTURE_DESCRIPTION?: string | null;
};
