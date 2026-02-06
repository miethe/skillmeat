/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BulkImportArtifact } from './BulkImportArtifact';
/**
 * Request to import multiple artifacts.
 */
export type BulkImportRequest = {
  /**
   * List of artifacts to import
   */
  artifacts: Array<BulkImportArtifact>;
  /**
   * Automatically resolve conflicts (overwrite existing artifacts)
   */
  auto_resolve_conflicts?: boolean;
  /**
   * List of artifact keys to mark as skipped (format: type:name)
   */
  skip_list?: Array<string> | null;
  /**
   * Apply approved path-based tags to imported artifacts. If true, segments with status='approved' in entry.path_segments will be created/found and linked as tags to the imported artifact.
   */
  apply_path_tags?: boolean;
};
