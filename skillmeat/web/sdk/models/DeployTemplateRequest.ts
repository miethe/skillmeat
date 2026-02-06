/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TemplateVariableValue } from './TemplateVariableValue';
/**
 * Request schema for deploying a project template.
 *
 * Deploys template entities to a target project path with variable substitution.
 * Supports selective entity deployment and overwrite control.
 */
export type DeployTemplateRequest = {
  /**
   * Path to target project directory (must be valid filesystem path)
   */
  project_path: string;
  /**
   * Variable values for template substitution
   */
  variables: TemplateVariableValue;
  /**
   * Subset of entity IDs to deploy (deploys all if not specified)
   */
  selected_entity_ids?: Array<string> | null;
  /**
   * Whether to overwrite existing files at target paths
   */
  overwrite?: boolean;
};
