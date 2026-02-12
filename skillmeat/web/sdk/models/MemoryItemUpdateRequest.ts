/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MemoryStatus } from './MemoryStatus';
import type { MemoryType } from './MemoryType';
/**
 * Request body for updating a memory item. All fields optional.
 */
export type AnchorUpdate = {
  path: string;
  type: 'code' | 'plan' | 'doc' | 'config' | 'test';
  line_start?: number | null;
  line_end?: number | null;
  commit_sha?: string | null;
  description?: string | null;
};

export type MemoryItemUpdateRequest = {
  type?: MemoryType | null;
  content?: string | null;
  confidence?: number | null;
  status?: MemoryStatus | null;
  provenance?: Record<string, any> | null;
  anchors?: Array<(AnchorUpdate | string)> | null;
  git_branch?: string | null;
  git_commit?: string | null;
  session_id?: string | null;
  agent_type?: string | null;
  model?: string | null;
  source_type?: string | null;
  ttl_policy?: Record<string, any> | null;
};
