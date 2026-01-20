/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for template deployment operation.
 *
 * Provides deployment results including deployed files, skipped files,
 * and overall status.
 */
export type DeployTemplateResponse = {
  /**
   * Whether deployment completed successfully
   */
  success: boolean;
  /**
   * Target project path where template was deployed
   */
  project_path: string;
  /**
   * List of files successfully deployed (relative paths)
   */
  deployed_files: Array<string>;
  /**
   * List of files skipped (already exist, overwrite=False)
   */
  skipped_files: Array<string>;
  /**
   * Human-readable deployment status message
   */
  message: string;
};
