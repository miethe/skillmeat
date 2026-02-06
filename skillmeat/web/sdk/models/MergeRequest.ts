/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request body for merging two memory items.
 */
export type MergeRequest = {
  source_id: string;
  target_id: string;
  strategy?: string;
  merged_content?: string | null;
};
