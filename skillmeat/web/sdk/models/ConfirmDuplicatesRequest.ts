/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DuplicateMatch } from './DuplicateMatch';
/**
 * Request to process duplicate review decisions.
 *
 * Handles three types of decisions:
 * 1. matches: Duplicates to link to existing collection artifacts
 * 2. new_artifacts: Paths to import as new artifacts
 * 3. skipped: Paths the user chose to skip
 */
export type ConfirmDuplicatesRequest = {
  /**
   * Base64-encoded or absolute path to the project being scanned
   */
  project_path: string;
  /**
   * Duplicate artifacts to link to collection entries
   */
  matches?: Array<DuplicateMatch>;
  /**
   * Filesystem paths of artifacts to import as new
   */
  new_artifacts?: Array<string>;
  /**
   * Filesystem paths of artifacts the user chose to skip
   */
  skipped?: Array<string>;
};
