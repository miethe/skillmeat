/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MemoryStatus } from './MemoryStatus';
import type { MemoryType } from './MemoryType';
/**
 * Request body for updating a memory item. All fields optional.
 */
export type MemoryItemUpdateRequest = {
  type?: MemoryType | null;
  content?: string | null;
  confidence?: number | null;
  status?: MemoryStatus | null;
  provenance?: Record<string, any> | null;
  anchors?: Array<string> | null;
  ttl_policy?: Record<string, any> | null;
};
