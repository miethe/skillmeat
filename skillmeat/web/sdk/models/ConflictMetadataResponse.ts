/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Conflict information for a single file.
 *
 * Describes the type and nature of a merge conflict detected
 * during rollback analysis.
 */
export type ConflictMetadataResponse = {
  /**
   * Relative path to the conflicting file
   */
  file_path: string;
  /**
   * Type of conflict: content, deletion, add_add, both_modified
   */
  conflict_type: string;
  /**
   * Whether the conflict can be automatically merged
   */
  auto_mergeable: boolean;
  /**
   * Whether the file is binary (cannot be text-merged)
   */
  is_binary: boolean;
};
