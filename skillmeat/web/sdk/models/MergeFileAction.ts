/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Describes an action taken on a single file during merge deployment.
 */
export type MergeFileAction = {
  /**
   * Relative file path within the artifact directory
   */
  file_path: string;
  /**
   * 'copied' = new file from collection copied to project, 'skipped' = file identical on both sides (no action), 'preserved' = file exists only in project (kept as-is), 'conflict' = file modified on both sides (left unchanged in project)
   */
  action: 'copied' | 'skipped' | 'preserved' | 'conflict';
  /**
   * Additional detail about the action (e.g., conflict description)
   */
  detail?: string | null;
};
