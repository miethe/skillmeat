/**
 * File API Types
 *
 * Type definitions for file-related API responses
 */

export interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;
  children?: FileNode[];
}

export interface FileListResponse {
  artifact_id: string;
  artifact_name: string;
  artifact_type: string;
  collection_name: string;
  files: FileNode[];
}

export interface FileContentResponse {
  artifact_id: string;
  artifact_name: string;
  artifact_type: string;
  collection_name: string;
  path: string;
  content: string;
  size: number;
  mime_type?: string;
}

export interface FileUpdateRequest {
  content: string;
}
