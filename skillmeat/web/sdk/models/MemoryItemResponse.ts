/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for a single memory item.
 */
export type MemoryItemResponse = {
  id: string;
  project_id: string;
  type: string;
  content: string;
  confidence: number;
  status: string;
  provenance?: Record<string, any> | null;
  anchors?: Array<string> | null;
  ttl_policy?: Record<string, any> | null;
  content_hash?: string | null;
  access_count?: number;
  created_at?: string | null;
  updated_at?: string | null;
  deprecated_at?: string | null;
};
