/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Categorization of artifacts in bundle.
 */
export type BundlePreviewCategorization = {
  /**
   * Number of artifacts that don't exist in collection
   */
  new_artifacts?: number;
  /**
   * Number of artifacts that conflict with existing ones
   */
  existing_artifacts?: number;
  /**
   * Number of artifacts that will be imported (new)
   */
  will_import?: number;
  /**
   * Number of artifacts that will require conflict resolution
   */
  will_require_resolution?: number;
};
