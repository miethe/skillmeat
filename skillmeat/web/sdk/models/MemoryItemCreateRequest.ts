/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MemoryStatus } from './MemoryStatus';
import type { MemoryType } from './MemoryType';
/**
 * Request body for creating a new memory item.
 */
export type MemoryItemCreateRequest = {
  type: MemoryType;
  content: string;
  confidence?: number;
  status?: MemoryStatus;
  provenance?: Record<string, any> | null;
  anchors?: Array<string> | null;
  ttl_policy?: Record<string, any> | null;
};
