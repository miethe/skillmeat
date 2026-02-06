/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response for project deletion.
 */
export type ProjectDeleteResponse = {
  /**
   * Whether the deletion was successful
   */
  success: boolean;
  /**
   * Human-readable status message
   */
  message: string;
  /**
   * Whether project files were deleted from disk
   */
  deleted_files?: boolean;
};
