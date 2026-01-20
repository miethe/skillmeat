/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FileTreeEntry } from './FileTreeEntry';
/**
 * Response containing file tree entries for an artifact.
 *
 * Returns the list of files and directories within a marketplace
 * artifact, used for file browsing in the catalog entry modal.
 */
export type FileTreeResponse = {
  /**
   * List of file and directory entries
   */
  entries: Array<FileTreeEntry>;
  /**
   * Path to artifact within repository
   */
  artifact_path: string;
  /**
   * Marketplace source ID
   */
  source_id: string;
};
