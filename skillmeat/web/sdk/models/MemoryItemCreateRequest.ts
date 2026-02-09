/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MemoryStatus } from './MemoryStatus';
import type { MemoryType } from './MemoryType';
/**
 * Request body for creating a new memory item.
 */
export type AnchorCreate = {
  path: string;
  type: 'code' | 'plan' | 'doc' | 'config' | 'test';
  line_start?: number | null;
  line_end?: number | null;
  commit_sha?: string | null;
  description?: string | null;
};

export type MemoryItemCreateRequest = {
  type: MemoryType;
  content: string;
  confidence?: number;
  status?: MemoryStatus;
  provenance?: Record<string, any> | null;
  anchors?: Array<(AnchorCreate | string)> | null;
  git_branch?: string | null;
  git_commit?: string | null;
  session_id?: string | null;
  agent_type?: string | null;
  model?: string | null;
  source_type?: string | null;
  ttl_policy?: Record<string, any> | null;
};
