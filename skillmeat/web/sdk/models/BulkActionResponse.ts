/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for bulk lifecycle operations.
 */
export type BulkActionResponse = {
  succeeded: Array<string>;
  failed: Array<Record<string, string>>;
};
