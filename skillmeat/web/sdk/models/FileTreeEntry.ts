/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A single entry in a file tree (file or directory).
 *
 * Represents a file or directory from the GitHub repository tree,
 * used for browsing artifact file structures in the catalog modal.
 */
export type FileTreeEntry = {
  /**
   * File path relative to artifact root
   */
  path: string;
  /**
   * Entry type: 'file' for files, 'tree' for directories
   */
  type: 'file' | 'tree';
  /**
   * File size in bytes (only for blobs/files)
   */
  size?: number | null;
  /**
   * Git SHA for the blob or tree
   */
  sha: string;
};
