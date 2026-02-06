/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConflictMetadataResponse } from './ConflictMetadataResponse';
/**
 * Response schema for merge safety analysis.
 *
 * Provides detailed information about merge safety including conflicts
 * and warnings.
 */
export type MergeSafetyResponse = {
  /**
   * Whether merge can be performed automatically
   */
  can_auto_merge: boolean;
  /**
   * Number of files that can auto-merge
   */
  auto_mergeable_count: number;
  /**
   * Number of files with conflicts
   */
  conflict_count: number;
  /**
   * List of conflict metadata for files requiring resolution
   */
  conflicts?: Array<ConflictMetadataResponse>;
  /**
   * List of warning messages about the merge
   */
  warnings?: Array<string>;
};
