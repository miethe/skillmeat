/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for a single memory item.
 */
export type AnchorResponse = {
  path: string;
  type: 'code' | 'plan' | 'doc' | 'config' | 'test';
  line_start?: number | null;
  line_end?: number | null;
  commit_sha?: string | null;
  description?: string | null;
};

export type MemoryItemResponse = {
  id: string;
  project_id: string;
  type: string;
  content: string;
  confidence: number;
  status: string;
  share_scope: string;
  project_name?: string | null;
  provenance?: Record<string, any> | null;
  anchors?: Array<(AnchorResponse | string)> | null;
  git_branch?: string | null;
  git_commit?: string | null;
  session_id?: string | null;
  agent_type?: string | null;
  model?: string | null;
  source_type?: string | null;
  ttl_policy?: Record<string, any> | null;
  content_hash?: string | null;
  access_count?: number;
  created_at?: string | null;
  updated_at?: string | null;
  deprecated_at?: string | null;
};
