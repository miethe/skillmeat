/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type Body_preview_bundle_api_v1_bundles_preview_post = {
  /**
   * Bundle ZIP file to preview
   */
  bundle_file: Blob;
  /**
   * Target collection (uses active if None)
   */
  collection_name?: string | null;
  /**
   * Expected SHA-256 hash for verification
   */
  expected_hash?: string | null;
};
