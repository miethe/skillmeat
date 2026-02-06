/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * File or directory node in artifact file tree.
 */
export type FileNode = {
  /**
   * File or directory name
   */
  name: string;
  /**
   * Relative path from artifact root
   */
  path: string;
  /**
   * Node type
   */
  type: 'file' | 'directory';
  /**
   * File size in bytes (only for files)
   */
  size?: number | null;
  /**
   * Child nodes (only for directories)
   */
  children?: Array<FileNode> | null;
};
