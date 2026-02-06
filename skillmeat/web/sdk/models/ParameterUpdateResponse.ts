/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response from parameter update.
 */
export type ParameterUpdateResponse = {
  /**
   * Whether update succeeded
   */
  success: boolean;
  /**
   * ID of the updated artifact (type:name)
   */
  artifact_id: string;
  /**
   * List of fields that were updated
   */
  updated_fields?: Array<string>;
  /**
   * Human-readable result message
   */
  message: string;
};
