/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MergeFileAction } from './MergeFileAction';
/**
 * Details of a merge deployment operation.
 */
export type MergeDeployDetails = {
  /**
   * Number of files copied from collection to project (new files)
   */
  files_copied?: number;
  /**
   * Number of identical files skipped (no action needed)
   */
  files_skipped?: number;
  /**
   * Number of project-only files preserved (not deleted)
   */
  files_preserved?: number;
  /**
   * Number of files modified on both sides (conflicts)
   */
  conflicts?: number;
  /**
   * Per-file action details
   */
  file_actions?: Array<MergeFileAction>;
};
