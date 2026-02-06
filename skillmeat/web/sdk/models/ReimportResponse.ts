/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response from a re-import operation.
 *
 * Contains the result of the re-import including the new artifact ID
 * and count of restored deployments.
 */
export type ReimportResponse = {
  /**
   * Whether the re-import succeeded
   */
  success: boolean;
  /**
   * ID of the newly imported artifact (format: 'type:name')
   */
  artifact_id?: string | null;
  /**
   * Human-readable description of the result
   */
  message: string;
  /**
   * Number of deployment records restored (when keep_deployments=True)
   */
  deployments_restored?: number;
};
